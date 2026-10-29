with source as (
    select * from {{ source('bronze', 'price_demand') }}
)

select
    region as region_id,
    settlement_ts,
    cast(total_demand_mw as double) as total_demand_mw,
    cast(rrp as double) as rrp,
    period_type,
    source_url,
    ingested_at,
    case
        when cast(settlement_ts as time) = time '00:00:00'
            then cast(settlement_ts - interval 1 day as date)
        else cast(settlement_ts as date)
    end as trading_date,
    cast(extract('hour' from settlement_ts - interval 1 second) as integer) as hour_of_day
from source
where region in ('NSW1', 'QLD1', 'VIC1', 'SA1', 'TAS1')
    and period_type = 'TRADE'
