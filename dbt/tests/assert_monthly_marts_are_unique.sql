select region_id, month_start, count(*) as row_count
from {{ ref('mart_negative_price_events') }}
group by region_id, month_start
having count(*) > 1

union all

select region_id, month_start, count(*) as row_count
from {{ ref('mart_price_volatility') }}
group by region_id, month_start
having count(*) > 1
