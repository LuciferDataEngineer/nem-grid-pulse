with regional as (
    select
        region_id,
        date_trunc('month', trading_date)::date as month_start,
        count(*) filter (where rrp < 0) * 5.0 / 60.0 as negative_hours,
        count(*) * 5.0 / 60.0 as total_hours,
        count(*) filter (where rrp < 0) * 1.0 / count(*) as negative_interval_share,
        avg(rrp) filter (where rrp < 0) as avg_negative_rrp,
        count(*) filter (where rrp <= -900) as floor_intervals,
        sum(case when rrp < 0 then total_demand_mw * 5.0 / 60.0 else 0 end) as negative_price_demand_mwh,
        min(rrp) as rrp_min
    from {{ ref('stg_aemo_price_demand') }}
    group by region_id, date_trunc('month', trading_date)::date
),
nem as (
    select
        'NEM' as region_id,
        date_trunc('month', trading_date)::date as month_start,
        count(*) filter (where rrp < 0) * 5.0 / 60.0 as negative_hours,
        count(*) * 5.0 / 60.0 as total_hours,
        count(*) filter (where rrp < 0) * 1.0 / count(*) as negative_interval_share,
        avg(rrp) filter (where rrp < 0) as avg_negative_rrp,
        count(*) filter (where rrp <= -900) as floor_intervals,
        sum(case when rrp < 0 then total_demand_mw * 5.0 / 60.0 else 0 end) as negative_price_demand_mwh,
        min(rrp) as rrp_min
    from {{ ref('int_nem_price_demand_5min') }}
    group by date_trunc('month', trading_date)::date
),
combined as (
    select * from regional
    union all
    select * from nem
)

select
    combined.*,
    months.is_complete_month
from combined
inner join {{ ref('int_analysis_months') }} as months
    on combined.month_start = months.month_start
