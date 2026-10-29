select region_id, settlement_ts, interval_count
from {{ ref('int_price_demand_30min') }}
where is_complete and interval_count <> 6
