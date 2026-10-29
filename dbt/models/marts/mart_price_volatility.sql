with regional as (
    select
        region_id,
        date_trunc('month', trading_date)::date as month_start,
        stddev_samp(rrp) as rrp_stddev,
        quantile_cont(rrp, 0.75) - quantile_cont(rrp, 0.25) as rrp_iqr,
        avg(rrp) as rrp_avg,
        sum(rrp * total_demand_mw) / nullif(sum(total_demand_mw), 0) as rrp_vw_avg,
        quantile_cont(rrp, 0.05) as rrp_p05,
        quantile_cont(rrp, 0.95) as rrp_p95,
        min(rrp) as rrp_min,
        max(rrp) as rrp_max,
        count(*) filter (where rrp > 300) as intervals_above_300,
        count(*) filter (where rrp > 1000) as intervals_above_1000,
        count(*) as interval_count
    from {{ ref('stg_aemo_price_demand') }}
    group by region_id, date_trunc('month', trading_date)::date
),
nem as (
    select
        'NEM' as region_id,
        date_trunc('month', trading_date)::date as month_start,
        stddev_samp(rrp) as rrp_stddev,
        quantile_cont(rrp, 0.75) - quantile_cont(rrp, 0.25) as rrp_iqr,
        avg(rrp) as rrp_avg,
        sum(rrp * total_demand_mw) / nullif(sum(total_demand_mw), 0) as rrp_vw_avg,
        quantile_cont(rrp, 0.05) as rrp_p05,
        quantile_cont(rrp, 0.95) as rrp_p95,
        min(rrp) as rrp_min,
        max(rrp) as rrp_max,
        count(*) filter (where rrp > 300) as intervals_above_300,
        count(*) filter (where rrp > 1000) as intervals_above_1000,
        count(*) as interval_count
    from {{ ref('int_nem_price_demand_5min') }}
    group by date_trunc('month', trading_date)::date
),
combined as (
    select * from regional
    union all
    select * from nem
)

select
    combined.region_id,
    combined.month_start,
    combined.rrp_stddev,
    combined.rrp_iqr,
    combined.rrp_stddev / nullif(abs(combined.rrp_avg), 0) as rrp_cv,
    combined.rrp_avg,
    combined.rrp_vw_avg,
    combined.rrp_p05,
    combined.rrp_p95,
    combined.rrp_min,
    combined.rrp_max,
    combined.intervals_above_300,
    combined.intervals_above_1000,
    combined.interval_count,
    months.is_complete_month
from combined
inner join {{ ref('int_analysis_months') }} as months
    on combined.month_start = months.month_start
