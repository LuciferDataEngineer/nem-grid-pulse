{{ config(materialized='table') }}

with scenarios as (
    select *
    from (
        values
            (0, 'baseline', 'No extra load. Historical operational demand.'),
            (500, 'plus_500mw', 'Flat +500 MW in every interval. Illustrative stress test, not a forecast.'),
            (1000, 'plus_1gw', 'Flat +1 GW in every interval. Illustrative stress test, not a forecast.'),
            (2000, 'plus_2gw', 'Flat +2 GW in every interval. Illustrative stress test, not a forecast.')
    ) as scenario(scenario_mw, scenario_id, scenario_label)
),
intervals as (
    select
        region_id,
        settlement_ts,
        trading_date,
        date_trunc('month', trading_date)::date as month_start,
        hour_of_day,
        demand_mw,
        1 as regions_applied
    from {{ ref('fct_price_demand_30min') }}
),
nem_intervals as (
    select
        'NEM' as region_id,
        settlement_ts,
        max(trading_date) as trading_date,
        max(date_trunc('month', trading_date)::date) as month_start,
        max(hour_of_day) as hour_of_day,
        sum(demand_mw) as demand_mw,
        5 as regions_applied
    from intervals
    group by settlement_ts
    having count(*) = 5
),
all_intervals as (
    select * from intervals
    union all
    select * from nem_intervals
),
peaks as (
    select
        region_id,
        max(demand_mw) as hist_peak_mw,
        quantile_cont(demand_mw, 0.95) as hist_p95_mw
    from all_intervals
    group by region_id
),
months as (
    select month_start, is_complete_month, is_last_12_complete
    from {{ ref('int_analysis_months') }}
),
tagged as (
    select all_intervals.*, 'full_history' as window_name
    from all_intervals
    union all
    select all_intervals.*, 'last_12_complete_months' as window_name
    from all_intervals
    inner join months on all_intervals.month_start = months.month_start
    where months.is_last_12_complete
),
window_summary as (
    select
        'window_summary' as grain,
        tagged.window_name,
        tagged.region_id,
        scenarios.scenario_id,
        scenarios.scenario_mw,
        scenarios.scenario_label,
        max(tagged.regions_applied) as regions_applied,
        scenarios.scenario_mw * max(tagged.regions_applied) as added_mw_on_series,
        cast(null as date) as month_start,
        cast(null as integer) as hour_of_day,
        cast(null as boolean) as is_complete_month,
        max(tagged.demand_mw) as baseline_peak_operational_demand_mw,
        max(tagged.demand_mw) + scenarios.scenario_mw * max(tagged.regions_applied) as peak_operational_demand_mw,
        avg(tagged.demand_mw) as baseline_avg_demand_mw,
        avg(tagged.demand_mw) + scenarios.scenario_mw * max(tagged.regions_applied) as avg_demand_mw,
        quantile_cont(tagged.demand_mw, 0.95) + scenarios.scenario_mw * max(tagged.regions_applied) as p95_demand_mw,
        avg(case when tagged.hour_of_day between 17 and 20 then tagged.demand_mw end) as baseline_evening_peak_avg_mw,
        avg(case when tagged.hour_of_day between 10 and 14 then tagged.demand_mw end) as baseline_midday_avg_mw,
        avg(case when tagged.hour_of_day between 17 and 20 then tagged.demand_mw end)
            + scenarios.scenario_mw * max(tagged.regions_applied) as evening_peak_avg_mw,
        avg(case when tagged.hour_of_day between 10 and 14 then tagged.demand_mw end)
            + scenarios.scenario_mw * max(tagged.regions_applied) as midday_avg_mw,
        sum(
            case
                when tagged.demand_mw + scenarios.scenario_mw * tagged.regions_applied > peaks.hist_peak_mw then 1
                else 0
            end
        ) as intervals_above_historical_peak,
        sum(
            case
                when tagged.demand_mw + scenarios.scenario_mw * tagged.regions_applied > peaks.hist_p95_mw then 1
                else 0
            end
        ) as intervals_above_historical_p95,
        count(*) as interval_count,
        sum(tagged.demand_mw) * 0.5 / 1000.0 as baseline_energy_gwh,
        scenarios.scenario_mw * max(tagged.regions_applied) * count(*) * 0.5 / 1000.0 as added_energy_gwh
    from tagged
    cross join scenarios
    inner join peaks on tagged.region_id = peaks.region_id
    group by
        tagged.window_name,
        tagged.region_id,
        scenarios.scenario_id,
        scenarios.scenario_mw,
        scenarios.scenario_label
),
monthly as (
    select
        'monthly' as grain,
        'calendar_month' as window_name,
        all_intervals.region_id,
        scenarios.scenario_id,
        scenarios.scenario_mw,
        scenarios.scenario_label,
        max(all_intervals.regions_applied) as regions_applied,
        scenarios.scenario_mw * max(all_intervals.regions_applied) as added_mw_on_series,
        all_intervals.month_start,
        cast(null as integer) as hour_of_day,
        max(months.is_complete_month) as is_complete_month,
        max(all_intervals.demand_mw) as baseline_peak_operational_demand_mw,
        max(all_intervals.demand_mw) + scenarios.scenario_mw * max(all_intervals.regions_applied) as peak_operational_demand_mw,
        avg(all_intervals.demand_mw) as baseline_avg_demand_mw,
        avg(all_intervals.demand_mw) + scenarios.scenario_mw * max(all_intervals.regions_applied) as avg_demand_mw,
        quantile_cont(all_intervals.demand_mw, 0.95) + scenarios.scenario_mw * max(all_intervals.regions_applied) as p95_demand_mw,
        avg(case when all_intervals.hour_of_day between 17 and 20 then all_intervals.demand_mw end) as baseline_evening_peak_avg_mw,
        avg(case when all_intervals.hour_of_day between 10 and 14 then all_intervals.demand_mw end) as baseline_midday_avg_mw,
        avg(case when all_intervals.hour_of_day between 17 and 20 then all_intervals.demand_mw end)
            + scenarios.scenario_mw * max(all_intervals.regions_applied) as evening_peak_avg_mw,
        avg(case when all_intervals.hour_of_day between 10 and 14 then all_intervals.demand_mw end)
            + scenarios.scenario_mw * max(all_intervals.regions_applied) as midday_avg_mw,
        sum(
            case
                when all_intervals.demand_mw + scenarios.scenario_mw * all_intervals.regions_applied > peaks.hist_peak_mw then 1
                else 0
            end
        ) as intervals_above_historical_peak,
        sum(
            case
                when all_intervals.demand_mw + scenarios.scenario_mw * all_intervals.regions_applied > peaks.hist_p95_mw then 1
                else 0
            end
        ) as intervals_above_historical_p95,
        count(*) as interval_count,
        sum(all_intervals.demand_mw) * 0.5 / 1000.0 as baseline_energy_gwh,
        scenarios.scenario_mw * max(all_intervals.regions_applied) * count(*) * 0.5 / 1000.0 as added_energy_gwh
    from all_intervals
    cross join scenarios
    inner join peaks on all_intervals.region_id = peaks.region_id
    inner join months on all_intervals.month_start = months.month_start
    group by
        all_intervals.region_id,
        all_intervals.month_start,
        scenarios.scenario_id,
        scenarios.scenario_mw,
        scenarios.scenario_label
),
hourly as (
    select
        'hourly' as grain,
        tagged.window_name,
        tagged.region_id,
        scenarios.scenario_id,
        scenarios.scenario_mw,
        scenarios.scenario_label,
        max(tagged.regions_applied) as regions_applied,
        scenarios.scenario_mw * max(tagged.regions_applied) as added_mw_on_series,
        cast(null as date) as month_start,
        tagged.hour_of_day,
        cast(null as boolean) as is_complete_month,
        max(tagged.demand_mw) as baseline_peak_operational_demand_mw,
        max(tagged.demand_mw) + scenarios.scenario_mw * max(tagged.regions_applied) as peak_operational_demand_mw,
        avg(tagged.demand_mw) as baseline_avg_demand_mw,
        avg(tagged.demand_mw) + scenarios.scenario_mw * max(tagged.regions_applied) as avg_demand_mw,
        quantile_cont(tagged.demand_mw, 0.95) + scenarios.scenario_mw * max(tagged.regions_applied) as p95_demand_mw,
        cast(null as double) as baseline_evening_peak_avg_mw,
        cast(null as double) as baseline_midday_avg_mw,
        cast(null as double) as evening_peak_avg_mw,
        cast(null as double) as midday_avg_mw,
        sum(
            case
                when tagged.demand_mw + scenarios.scenario_mw * tagged.regions_applied > peaks.hist_peak_mw then 1
                else 0
            end
        ) as intervals_above_historical_peak,
        sum(
            case
                when tagged.demand_mw + scenarios.scenario_mw * tagged.regions_applied > peaks.hist_p95_mw then 1
                else 0
            end
        ) as intervals_above_historical_p95,
        count(*) as interval_count,
        sum(tagged.demand_mw) * 0.5 / 1000.0 as baseline_energy_gwh,
        scenarios.scenario_mw * max(tagged.regions_applied) * count(*) * 0.5 / 1000.0 as added_energy_gwh
    from tagged
    cross join scenarios
    inner join peaks on tagged.region_id = peaks.region_id
    group by
        tagged.window_name,
        tagged.region_id,
        tagged.hour_of_day,
        scenarios.scenario_id,
        scenarios.scenario_mw,
        scenarios.scenario_label
),
combined as (
    select * from window_summary
    union all
    select * from monthly
    union all
    select * from hourly
),
residual_days as (
    select
        region_id,
        trading_date,
        date_trunc('month', trading_date)::date as month_start,
        residual_after_grid_vre_gwh,
        interval_count
    from {{ ref('mart_daily_region_summary') }}
    where residual_after_grid_vre_gwh is not null
),
residual_month as (
    select
        region_id,
        month_start,
        sum(residual_after_grid_vre_gwh) as baseline_residual_gwh,
        sum(interval_count) as residual_intervals
    from residual_days
    group by region_id, month_start
),
residual_window as (
    select
        residual_month.region_id,
        'full_history' as window_name,
        sum(residual_month.baseline_residual_gwh) as baseline_residual_gwh,
        sum(residual_month.residual_intervals) as residual_intervals
    from residual_month
    group by residual_month.region_id
    union all
    select
        residual_month.region_id,
        'last_12_complete_months' as window_name,
        sum(residual_month.baseline_residual_gwh) as baseline_residual_gwh,
        sum(residual_month.residual_intervals) as residual_intervals
    from residual_month
    inner join months on residual_month.month_start = months.month_start
    where months.is_last_12_complete
    group by residual_month.region_id
)

select
    combined.grain || '|' || combined.window_name || '|' || combined.region_id || '|'
        || combined.scenario_id || '|' || coalesce(strftime(combined.month_start, '%Y-%m-%d'), '-') || '|'
        || coalesce(cast(combined.hour_of_day as varchar), '-') as scenario_key,
    combined.grain,
    combined.window_name,
    combined.region_id,
    combined.scenario_id,
    combined.scenario_mw,
    combined.scenario_label,
    combined.regions_applied,
    combined.added_mw_on_series,
    combined.month_start,
    combined.hour_of_day,
    combined.is_complete_month,
    combined.baseline_peak_operational_demand_mw,
    combined.peak_operational_demand_mw,
    combined.baseline_avg_demand_mw,
    combined.avg_demand_mw,
    combined.p95_demand_mw,
    combined.baseline_evening_peak_avg_mw,
    combined.baseline_midday_avg_mw,
    combined.evening_peak_avg_mw,
    combined.midday_avg_mw,
    combined.baseline_evening_peak_avg_mw - combined.baseline_midday_avg_mw as baseline_evening_midday_gap_mw,
    combined.evening_peak_avg_mw - combined.midday_avg_mw as scenario_evening_midday_gap_mw,
    combined.intervals_above_historical_peak,
    combined.intervals_above_historical_p95,
    combined.interval_count,
    combined.baseline_energy_gwh,
    combined.added_energy_gwh,
    combined.baseline_energy_gwh + combined.added_energy_gwh as scenario_energy_gwh,
    case
        when combined.grain = 'monthly' then residual_month.baseline_residual_gwh
        when combined.grain = 'window_summary' then residual_window.baseline_residual_gwh
    end as baseline_residual_gwh,
    case
        when combined.grain = 'monthly' then residual_month.baseline_residual_gwh
            + combined.added_mw_on_series * residual_month.residual_intervals * 5.0 / 60.0 / 1000.0
        when combined.grain = 'window_summary' then residual_window.baseline_residual_gwh
            + combined.added_mw_on_series * residual_window.residual_intervals * 5.0 / 60.0 / 1000.0
    end as scenario_residual_gwh,
    combined.added_mw_on_series / nullif(combined.baseline_peak_operational_demand_mw, 0) as uplift_pct_of_baseline_peak,
    'illustrative_flat_load_v1' as model_id,
    false as is_forecast,
    'Illustrative flat-load energy balance on historical demand. Not a dispatch model and not a price forecast.' as model_note
from combined
left join residual_month
    on combined.grain = 'monthly'
    and combined.region_id = residual_month.region_id
    and combined.month_start = residual_month.month_start
left join residual_window
    on combined.grain = 'window_summary'
    and combined.region_id = residual_window.region_id
    and combined.window_name = residual_window.window_name
