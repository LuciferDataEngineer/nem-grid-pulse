with priced as (
    select
        region_id,
        trading_date,
        hour_of_day,
        total_demand_mw,
        rrp,
        date_trunc('month', trading_date)::date as month_start
    from {{ ref('stg_aemo_price_demand') }}
    union all
    select
        'NEM' as region_id,
        trading_date,
        hour_of_day,
        total_demand_mw,
        rrp,
        date_trunc('month', trading_date)::date as month_start
    from {{ ref('int_nem_price_demand_5min') }}
),
tagged as (
    select priced.*, 'all_history' as profile_slice
    from priced
    union all
    select priced.*, 'summer' as profile_slice
    from priced
    where extract('month' from trading_date) in (12, 1, 2)
    union all
    select priced.*, 'winter' as profile_slice
    from priced
    where extract('month' from trading_date) in (6, 7, 8)
    union all
    select priced.*, 'last_12_complete_months' as profile_slice
    from priced
    inner join {{ ref('int_analysis_months') }} as months
        on priced.month_start = months.month_start
    where months.is_last_12_complete
)

select
    region_id,
    profile_slice,
    hour_of_day,
    avg(total_demand_mw) as avg_demand_mw,
    avg(rrp) as avg_rrp,
    quantile_cont(total_demand_mw, 0.5) as p50_demand_mw,
    quantile_cont(total_demand_mw, 0.9) as p90_demand_mw,
    avg(case when rrp < 0 then 1.0 else 0.0 end) as negative_interval_share,
    count(*) as interval_count
from tagged
group by region_id, profile_slice, hour_of_day
