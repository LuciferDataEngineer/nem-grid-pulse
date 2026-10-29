with buckets as (
    select
        region_id,
        total_demand_mw,
        rrp,
        case
            when extract('minute' from settlement_ts) = 0 then settlement_ts
            when extract('minute' from settlement_ts) <= 30
                then date_trunc('hour', settlement_ts) + interval 30 minute
            else date_trunc('hour', settlement_ts) + interval 1 hour
        end as settlement_ts
    from {{ ref('stg_aemo_price_demand') }}
),

grouped as (
    select
        region_id,
        settlement_ts,
        avg(total_demand_mw) as demand_mw,
        avg(rrp) as rrp_time_weighted,
        sum(rrp * total_demand_mw) / nullif(sum(total_demand_mw), 0) as rrp_volume_weighted,
        count(*) as interval_count,
        count(*) = 6 as is_complete
    from buckets
    group by region_id, settlement_ts
)

select
    region_id,
    settlement_ts,
    demand_mw,
    rrp_time_weighted,
    rrp_volume_weighted,
    interval_count,
    is_complete,
    case
        when cast(settlement_ts as time) = time '00:00:00'
            then cast(settlement_ts - interval 1 day as date)
        else cast(settlement_ts as date)
    end as trading_date,
    cast(extract('hour' from settlement_ts - interval 1 second) as integer) as hour_of_day
from grouped
