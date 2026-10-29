select
    region_id,
    scenario_mw,
    grain,
    window_name,
    peak_operational_demand_mw,
    baseline_peak_operational_demand_mw,
    added_mw_on_series
from {{ ref('mart_datacentre_load_scenarios') }}
where abs(
    peak_operational_demand_mw
    - baseline_peak_operational_demand_mw
    - added_mw_on_series
) > 0.05
