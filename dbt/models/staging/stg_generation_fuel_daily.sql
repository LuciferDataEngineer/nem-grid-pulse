select
    region as region_id,
    cast(trading_date as date) as trading_date,
    fuel_tech,
    cast(energy_gwh as double) as energy_gwh,
    units,
    source_url,
    ingested_at
from {{ source('bronze', 'generation_daily') }}
where region in ('NSW1', 'QLD1', 'VIC1', 'SA1', 'TAS1')
    and units = 'GWh'
