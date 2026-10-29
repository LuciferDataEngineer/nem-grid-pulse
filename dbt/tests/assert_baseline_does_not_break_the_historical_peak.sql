select region_id, grain, window_name, intervals_above_historical_peak
from {{ ref('mart_datacentre_load_scenarios') }}
where scenario_mw = 0
    and coalesce(intervals_above_historical_peak, 0) <> 0
