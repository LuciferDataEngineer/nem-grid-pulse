select
    region_id,
    trading_date,
    coalesce(sum(case when fuel_tech in {{ fuel_set('renewable') }} then energy_gwh end), 0) as renewable_gwh,
    coalesce(sum(case when fuel_tech in {{ fuel_set('fossil') }} then energy_gwh end), 0) as fossil_gwh,
    coalesce(sum(case when fuel_tech in {{ fuel_set('grid_vre') }} then energy_gwh end), 0) as grid_vre_gwh,
    coalesce(sum(case when fuel_tech = 'solar_rooftop' then energy_gwh end), 0) as rooftop_gwh,
    coalesce(sum(case when fuel_tech = 'hydro' then energy_gwh end), 0) as hydro_gwh,
    coalesce(sum(case when fuel_tech in {{ fuel_set('storage_discharge') }} then energy_gwh end), 0) as battery_discharge_gwh,
    coalesce(sum(case when fuel_tech like 'curtailment%' then energy_gwh end), 0) as curtailment_gwh,
    coalesce(sum(
        case
            when fuel_tech not in {{ fuel_set('renewable') }}
                and fuel_tech not in {{ fuel_set('fossil') }}
                and fuel_tech not in {{ fuel_set('storage_discharge') }}
                and fuel_tech not in {{ fuel_set('storage_load') }}
                and fuel_tech not in {{ fuel_set('interchange') }}
                and fuel_tech not like 'curtailment%'
                then energy_gwh
        end
    ), 0) as other_gwh
from {{ ref('stg_generation_fuel_daily') }}
group by region_id, trading_date
