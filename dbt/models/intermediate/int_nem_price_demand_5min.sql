select
    settlement_ts,
    max(trading_date) as trading_date,
    max(hour_of_day) as hour_of_day,
    sum(total_demand_mw) as total_demand_mw,
    sum(rrp * total_demand_mw) / nullif(sum(total_demand_mw), 0) as rrp,
    count(*) as region_count
from {{ ref('stg_aemo_price_demand') }}
group by settlement_ts
having count(*) = 5
