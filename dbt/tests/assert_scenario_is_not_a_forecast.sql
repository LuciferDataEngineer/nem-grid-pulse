select scenario_key, model_id, is_forecast
from {{ ref('mart_datacentre_load_scenarios') }}
where is_forecast
    or model_id <> 'illustrative_flat_load_v1'
    or model_note is null
    or abs(added_mw_on_series - scenario_mw * regions_applied) > 0.001
