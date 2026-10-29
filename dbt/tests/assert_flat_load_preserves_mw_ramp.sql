select
    region_id,
    scenario_mw,
    grain,
    window_name,
    baseline_evening_midday_gap_mw,
    scenario_evening_midday_gap_mw
from {{ ref('mart_datacentre_load_scenarios') }}
where baseline_evening_midday_gap_mw is not null
    and abs(baseline_evening_midday_gap_mw - scenario_evening_midday_gap_mw) > 0.05
