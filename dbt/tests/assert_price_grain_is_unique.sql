select region_id, settlement_ts, count(*) as row_count
from {{ ref('stg_aemo_price_demand') }}
group by region_id, settlement_ts
having count(*) > 1
