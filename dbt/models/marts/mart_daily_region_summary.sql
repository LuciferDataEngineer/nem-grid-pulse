with regional as (
    select
        region_id,
        trading_date,
        count(*) as interval_count,
        count(*) = 288 as is_complete_day,
        avg(total_demand_mw) as demand_avg_mw,
        min(total_demand_mw) as demand_min_mw,
        max(total_demand_mw) as demand_max_5min_mw,
        sum(total_demand_mw) * 5.0 / 60.0 as demand_mwh,
        avg(rrp) as rrp_time_weighted,
        sum(rrp * total_demand_mw) / nullif(sum(total_demand_mw), 0) as rrp_volume_weighted,
        min(rrp) as rrp_min,
        max(rrp) as rrp_max,
        stddev_samp(rrp) as rrp_stddev,
        count(*) filter (where rrp < 0) as negative_intervals,
        count(*) filter (where rrp < 0) * 5.0 / 60.0 as negative_hours,
        count(*) filter (where rrp <= -900) as floor_intervals,
        count(*) filter (where rrp > 300) as spike_300_intervals
    from {{ ref('stg_aemo_price_demand') }}
    group by region_id, trading_date
),
halfhour as (
    select
        region_id,
        trading_date,
        max(demand_mw) as demand_max_halfhour_mw
    from {{ ref('fct_price_demand_30min') }}
    group by region_id, trading_date
),
regional_daily as (
    select
        regional.region_id,
        regional.trading_date,
        regional.interval_count,
        regional.is_complete_day,
        regional.demand_avg_mw,
        regional.demand_min_mw,
        regional.demand_max_5min_mw,
        halfhour.demand_max_halfhour_mw,
        regional.demand_mwh,
        regional.rrp_time_weighted,
        regional.rrp_volume_weighted,
        regional.rrp_min,
        regional.rrp_max,
        regional.rrp_stddev,
        regional.negative_intervals,
        regional.negative_hours,
        regional.floor_intervals,
        regional.spike_300_intervals,
        fuel.renewable_gwh,
        fuel.fossil_gwh,
        fuel.grid_vre_gwh,
        fuel.rooftop_gwh,
        fuel.hydro_gwh,
        fuel.curtailment_gwh,
        fuel.battery_discharge_gwh,
        fuel.renewable_gwh + fuel.fossil_gwh + fuel.battery_discharge_gwh as generation_gwh,
        greatest(fuel.renewable_gwh, 0) / nullif(
            greatest(fuel.renewable_gwh, 0)
                + greatest(fuel.fossil_gwh, 0)
                + greatest(fuel.battery_discharge_gwh, 0),
            0
        ) as renewable_share,
        case
            when fuel.grid_vre_gwh is null then null
            else regional.demand_mwh / 1000.0 - fuel.grid_vre_gwh
        end as residual_after_grid_vre_gwh
    from regional
    left join halfhour
        on regional.region_id = halfhour.region_id
        and regional.trading_date = halfhour.trading_date
    left join {{ ref('int_generation_daily') }} as fuel
        on regional.region_id = fuel.region_id
        and regional.trading_date = fuel.trading_date
),
nem_price as (
    select
        trading_date,
        count(*) as interval_count,
        count(*) = 288 as is_complete_day,
        avg(total_demand_mw) as demand_avg_mw,
        min(total_demand_mw) as demand_min_mw,
        max(total_demand_mw) as demand_max_5min_mw,
        sum(total_demand_mw) * 5.0 / 60.0 as demand_mwh,
        avg(rrp) as rrp_time_weighted,
        sum(rrp * total_demand_mw) / nullif(sum(total_demand_mw), 0) as rrp_volume_weighted,
        min(rrp) as rrp_min,
        max(rrp) as rrp_max,
        stddev_samp(rrp) as rrp_stddev,
        count(*) filter (where rrp < 0) as negative_intervals,
        count(*) filter (where rrp < 0) * 5.0 / 60.0 as negative_hours,
        count(*) filter (where rrp <= -900) as floor_intervals,
        count(*) filter (where rrp > 300) as spike_300_intervals
    from {{ ref('int_nem_price_demand_5min') }}
    group by trading_date
),
nem_halfhour as (
    select
        trading_date,
        max(demand_mw) as demand_max_halfhour_mw
    from (
        select
            settlement_ts,
            max(trading_date) as trading_date,
            sum(demand_mw) as demand_mw
        from {{ ref('fct_price_demand_30min') }}
        group by settlement_ts
        having count(*) = 5
    ) as nem_intervals
    group by trading_date
),
nem_fuel as (
    select
        trading_date,
        sum(renewable_gwh) as renewable_gwh,
        sum(fossil_gwh) as fossil_gwh,
        sum(grid_vre_gwh) as grid_vre_gwh,
        sum(rooftop_gwh) as rooftop_gwh,
        sum(hydro_gwh) as hydro_gwh,
        sum(curtailment_gwh) as curtailment_gwh,
        sum(battery_discharge_gwh) as battery_discharge_gwh
    from {{ ref('int_generation_daily') }}
    group by trading_date
),
nem_daily as (
    select
        'NEM' as region_id,
        nem_price.trading_date,
        nem_price.interval_count,
        nem_price.is_complete_day,
        nem_price.demand_avg_mw,
        nem_price.demand_min_mw,
        nem_price.demand_max_5min_mw,
        nem_halfhour.demand_max_halfhour_mw,
        nem_price.demand_mwh,
        nem_price.rrp_time_weighted,
        nem_price.rrp_volume_weighted,
        nem_price.rrp_min,
        nem_price.rrp_max,
        nem_price.rrp_stddev,
        nem_price.negative_intervals,
        nem_price.negative_hours,
        nem_price.floor_intervals,
        nem_price.spike_300_intervals,
        nem_fuel.renewable_gwh,
        nem_fuel.fossil_gwh,
        nem_fuel.grid_vre_gwh,
        nem_fuel.rooftop_gwh,
        nem_fuel.hydro_gwh,
        nem_fuel.curtailment_gwh,
        nem_fuel.battery_discharge_gwh,
        nem_fuel.renewable_gwh + nem_fuel.fossil_gwh + nem_fuel.battery_discharge_gwh as generation_gwh,
        greatest(nem_fuel.renewable_gwh, 0) / nullif(
            greatest(nem_fuel.renewable_gwh, 0)
                + greatest(nem_fuel.fossil_gwh, 0)
                + greatest(nem_fuel.battery_discharge_gwh, 0),
            0
        ) as renewable_share,
        case
            when nem_fuel.grid_vre_gwh is null then null
            else nem_price.demand_mwh / 1000.0 - nem_fuel.grid_vre_gwh
        end as residual_after_grid_vre_gwh
    from nem_price
    left join nem_halfhour on nem_price.trading_date = nem_halfhour.trading_date
    left join nem_fuel on nem_price.trading_date = nem_fuel.trading_date
)

select * from regional_daily
union all
select * from nem_daily
