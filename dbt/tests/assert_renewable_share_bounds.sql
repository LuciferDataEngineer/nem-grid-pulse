select region_id, trading_date, renewable_share
from {{ ref('mart_daily_region_summary') }}
where renewable_share is not null
    and (renewable_share < 0 or renewable_share > 1.0000001)
