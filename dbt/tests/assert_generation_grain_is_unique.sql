select region_id, trading_date, fuel_tech, count(*) as row_count
from {{ ref('stg_generation_fuel_daily') }}
group by region_id, trading_date, fuel_tech
having count(*) > 1
