select region_id, trading_date, count(*) as row_count
from {{ ref('mart_daily_region_summary') }}
group by region_id, trading_date
having count(*) > 1
