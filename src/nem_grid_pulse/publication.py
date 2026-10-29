"""Numbers for the dashboard and INSIGHTS.md. Every figure is queried from the marts."""

from __future__ import annotations

import math

import duckdb
import pandas as pd

from nem_grid_pulse.settings import warehouse_path
from nem_grid_pulse.status import (
    STATUS_LABEL,
    headroom_status,
    negative_price_status,
    relative_stress,
    renewable_share_status,
)

MODEL_NOTE = (
    "Illustrative flat-load energy balance on historical demand. Not a dispatch model and not a price forecast."
)


def _connect() -> duckdb.DuckDBPyConnection:
    path = warehouse_path()
    if not path.exists():
        raise FileNotFoundError(f"Warehouse not found at {path}. Run make transform first.")
    return duckdb.connect(str(path), read_only=True)


def _num(value, digits: int = 2):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), digits)


def _month(value) -> str:
    return pd.Timestamp(value).strftime("%b %Y")


def _month_long(value) -> str:
    return pd.Timestamp(value).strftime("%B %Y")


def _day(value) -> str:
    return pd.Timestamp(value).strftime("%-d %B %Y")


def _iso(value) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _aud(value: float) -> str:
    return f"${value:,.2f}"


def _mw(value: float) -> str:
    return f"{value:,.0f} MW"


def _hours(value: float) -> str:
    return f"{value:,.0f} h"


def _signed_pct(value: float) -> str:
    return f"{value * 100:+.1f}%"


def _tone(latest: float, prior: float, *, higher_is_worse: bool) -> str:
    if prior == 0 or latest == prior:
        return "neutral"
    worse = latest > prior if higher_is_worse else latest < prior
    return "bad" if worse else "good"


def _direction(latest: float, prior: float) -> str:
    if latest > prior:
        return "up"
    if latest < prior:
        return "down"
    return "flat"


def build_payload() -> dict:
    con = _connect()
    try:
        return _payload(con)
    finally:
        con.close()


def _payload(con: duckdb.DuckDBPyConnection) -> dict:
    bounds = con.execute(
        """
        select min(trading_date), max(trading_date), min(settlement_ts), max(settlement_ts)
        from marts.fct_price_demand_30min
        """
    ).fetchone()
    latest_month, prior_month = con.execute(
        """
        with complete as (
            select month_start
            from intermediate.int_analysis_months
            where is_complete_month
        )
        select
            (select max(month_start) from complete),
            (
                select max(month_start)
                from complete
                where month_start < (select max(month_start) from complete)
            )
        """
    ).fetchone()

    latest_month = pd.Timestamp(latest_month)
    prior_month = pd.Timestamp(prior_month)

    regions = con.execute(
        """
        select region_id, region_name, colour_hex, region_type
        from marts.dim_region
        order by case region_id
            when 'NSW1' then 1 when 'QLD1' then 2 when 'VIC1' then 3
            when 'SA1' then 4 when 'TAS1' then 5 else 6 end
        """
    ).fetchdf()

    price = con.execute(
        """
        select region_id, month_start, rrp_vw_avg, rrp_stddev, rrp_min, rrp_max,
               intervals_above_300, intervals_above_1000, is_complete_month
        from marts.mart_price_volatility
        order by month_start, region_id
        """
    ).fetchdf()
    negative = con.execute(
        """
        select region_id, month_start, negative_hours, negative_interval_share,
               floor_intervals, is_complete_month
        from marts.mart_negative_price_events
        order by month_start, region_id
        """
    ).fetchdf()
    renewable = con.execute(
        """
        select
            date_trunc('month', trading_date)::date as month_start,
            region_id,
            sum(renewable_gwh) / nullif(sum(generation_gwh), 0) as renewable_share,
            sum(demand_mwh) / 1000.0 as demand_gwh,
            max(demand_max_halfhour_mw) as peak_mw,
            sum(negative_hours) as negative_hours
        from marts.mart_daily_region_summary
        group by 1, 2
        order by 1, 2
        """
    ).fetchdf()
    hourly = con.execute(
        """
        select region_id, profile_slice, hour_of_day, avg_demand_mw, avg_rrp, negative_interval_share
        from marts.mart_hourly_profile
        order by profile_slice, hour_of_day, region_id
        """
    ).fetchdf()
    scenarios = con.execute(
        """
        select region_id, scenario_mw, scenario_label, regions_applied, added_mw_on_series,
               baseline_peak_operational_demand_mw, peak_operational_demand_mw,
               baseline_evening_peak_avg_mw, baseline_midday_avg_mw, baseline_evening_midday_gap_mw,
               intervals_above_historical_peak, intervals_above_historical_p95,
               added_energy_gwh, baseline_residual_gwh, scenario_residual_gwh,
               uplift_pct_of_baseline_peak, model_note
        from marts.mart_datacentre_load_scenarios
        where grain = 'window_summary'
          and window_name = 'last_12_complete_months'
        order by region_id, scenario_mw
        """
    ).fetchdf()
    scenario_hourly = con.execute(
        """
        select region_id, scenario_mw, hour_of_day, avg_demand_mw
        from marts.mart_datacentre_load_scenarios
        where grain = 'hourly' and window_name = 'last_12_complete_months'
        order by region_id, scenario_mw, hour_of_day
        """
    ).fetchdf()
    for frame in (price, negative, renewable):
        frame["month_start"] = pd.to_datetime(frame["month_start"])

    nem_price = price[price.region_id == "NEM"].sort_values("month_start")
    latest_price = nem_price[nem_price.month_start == latest_month].iloc[0]
    prior_price = nem_price[nem_price.month_start == prior_month].iloc[0]
    latest_ts = pd.Timestamp(latest_month)
    prior_floor = latest_ts - pd.DateOffset(months=12)
    baseline_price_months = nem_price[
        nem_price.month_start.map(lambda value: prior_floor <= pd.Timestamp(value) < latest_ts)
        & nem_price.is_complete_month
    ]
    baseline_vwap = float(baseline_price_months.rrp_vw_avg.mean())
    baseline_vol = float(baseline_price_months.rrp_stddev.mean())

    nem_neg = negative[negative.region_id == "NEM"]
    latest_neg = nem_neg[nem_neg.month_start == latest_month].iloc[0]
    prior_neg = nem_neg[nem_neg.month_start == prior_month].iloc[0]
    baseline_neg = nem_neg[nem_neg.month_start.map(lambda value: prior_floor <= pd.Timestamp(value) < latest_ts)]
    baseline_neg_share = float(baseline_neg.negative_interval_share.mean())

    nem_ren = renewable[renewable.region_id == "NEM"]
    latest_ren = nem_ren[nem_ren.month_start == latest_month].iloc[0]
    prior_ren = nem_ren[nem_ren.month_start == prior_month].iloc[0]
    baseline_ren = nem_ren[nem_ren.month_start.map(lambda value: prior_floor <= pd.Timestamp(value) < latest_ts)]
    # Generation-weighted share across the baseline months.
    baseline_share = float(
        con.execute(
            """
            select sum(renewable_gwh) / nullif(sum(generation_gwh), 0)
            from marts.mart_daily_region_summary
            where region_id = 'NEM'
              and trading_date >= ?
              and trading_date < ?
            """,
            [prior_floor.date(), latest_ts.date()],
        ).fetchone()[0]
    )
    latest_peak = float(latest_ren.peak_mw)
    prior_peak = float(prior_ren.peak_mw)
    baseline_peak = float(baseline_ren.peak_mw.mean())

    history_vwap = float(
        con.execute(
            """
            select sum(rrp_volume_weighted * demand_mwh) / nullif(sum(demand_mwh), 0)
            from marts.mart_daily_region_summary
            where region_id = 'NEM'
            """
        ).fetchone()[0]
    )
    history_share = float(
        con.execute(
            """
            select sum(renewable_gwh) / nullif(sum(generation_gwh), 0)
            from marts.mart_daily_region_summary
            where region_id = 'NEM'
            """
        ).fetchone()[0]
    )

    scenario_1gw = scenarios[(scenarios.scenario_mw == 1000)].set_index("region_id")
    tas_fraction = float(scenario_1gw.loc["TAS1", "uplift_pct_of_baseline_peak"])
    nsw_fraction = float(scenario_1gw.loc["NSW1", "uplift_pct_of_baseline_peak"])
    nem_row = scenarios[(scenarios.region_id == "NEM") & (scenarios.scenario_mw == 1000)].iloc[0]
    base_nem = scenarios[(scenarios.region_id == "NEM") & (scenarios.scenario_mw == 0)].iloc[0]
    sa_sep = negative[(negative.region_id == "SA1") & (negative.month_start == latest_month)].iloc[0]
    jumpy = baseline_price_months.loc[baseline_price_months.rrp_stddev.idxmax()]
    neg_peak = baseline_neg.loc[baseline_neg.negative_interval_share.idxmax()]

    latest_label = _month_long(latest_month)
    prior_label = _month_long(prior_month)
    price_now = float(latest_price.rrp_vw_avg)
    price_prev = float(prior_price.rrp_vw_avg)
    vol_now = float(latest_price.rrp_stddev)
    vol_prev = float(prior_price.rrp_stddev)
    neg_now = float(latest_neg.negative_hours)
    neg_prev = float(prior_neg.negative_hours)
    share_now = float(latest_ren.renewable_share)
    share_prev = float(prior_ren.renewable_share)

    kpis = [
        _kpi(
            "price",
            "NEM volume-weighted price",
            _aud(price_now),
            "/MWh",
            latest_label,
            f"{_signed_pct(price_now / price_prev - 1)} vs {prior_label}",
            _direction(price_now, price_prev),
            _tone(price_now, price_prev, higher_is_worse=True),
            f"{_signed_pct(price_now / baseline_vwap - 1)} vs prior 12-month average",
            relative_stress(price_now, baseline_vwap, amber=0.10, red=0.30),
        ),
        _kpi(
            "peak",
            "NEM peak half-hour",
            _mw(latest_peak),
            "",
            latest_label,
            f"{_signed_pct(latest_peak / prior_peak - 1)} vs {prior_label}",
            _direction(latest_peak, prior_peak),
            _tone(latest_peak, prior_peak, higher_is_worse=True),
            f"{_signed_pct(latest_peak / baseline_peak - 1)} vs prior 12 monthly peaks",
            relative_stress(latest_peak, baseline_peak, amber=0.05, red=0.15),
        ),
        _kpi(
            "negative",
            "Hours with a negative NEM price",
            _hours(neg_now),
            _pct(float(latest_neg.negative_interval_share)) + " of intervals",
            latest_label,
            f"{neg_now - neg_prev:+.0f} h vs {prior_label}",
            _direction(neg_now, neg_prev),
            _tone(neg_now, neg_prev, higher_is_worse=True),
            f"{(float(latest_neg.negative_interval_share) - baseline_neg_share) * 100:+.1f} pp vs prior 12-month average",
            negative_price_status(float(latest_neg.negative_interval_share)),
        ),
        _kpi(
            "volatility",
            "NEM price volatility",
            _aud(vol_now),
            "std. dev. of 5-min RRP",
            latest_label,
            f"{_signed_pct(vol_now / vol_prev - 1)} vs {prior_label}",
            _direction(vol_now, vol_prev),
            _tone(vol_now, vol_prev, higher_is_worse=True),
            f"{_signed_pct(vol_now / baseline_vol - 1)} vs prior 12-month average",
            relative_stress(vol_now, baseline_vol, amber=0.10, red=0.30),
        ),
        _kpi(
            "renewables",
            "Renewable share of local generation",
            _pct(share_now),
            "NEM, rooftop included, imports excluded",
            latest_label,
            f"{(share_now - share_prev) * 100:+.1f} pp vs {prior_label}",
            _direction(share_now, share_prev),
            _tone(share_now, share_prev, higher_is_worse=False),
            f"{(share_now - baseline_share) * 100:+.1f} pp vs prior 12-month generation",
            renewable_share_status(share_now),
        ),
        _kpi(
            "headroom",
            "Tightest region for a flat +1 GW",
            "Tasmania",
            _pct(tas_fraction) + " of its own peak",
            "Last 12 complete months",
            f"Peak was {_mw(float(scenario_1gw.loc['TAS1', 'baseline_peak_operational_demand_mw']))}",
            "up",
            "bad",
            f"NSW +1 GW is {_pct(nsw_fraction)} of its peak",
            headroom_status(tas_fraction),
        ),
    ]

    region_shares = {
        row.region_id: float(row.renewable_share)
        for row in renewable[renewable.month_start == latest_month].itertuples()
    }
    recommendations = _recommendations(
        latest_label=latest_label,
        prior_label=prior_label,
        price_now=price_now,
        price_prev=price_prev,
        baseline_vwap=baseline_vwap,
        neg_now=neg_now,
        neg_share=float(latest_neg.negative_interval_share),
        neg_prev=neg_prev,
        sa_hours=float(sa_sep.negative_hours),
        sa_share=float(sa_sep.negative_interval_share),
        share_now=share_now,
        region_shares=region_shares,
        base_nem=base_nem,
        nem_row=nem_row,
        scenario_1gw=scenario_1gw,
        jumpy_month=_month_long(jumpy.month_start),
        jumpy_sd=float(jumpy.rrp_stddev),
        neg_peak_month=_month_long(neg_peak.month_start),
        neg_peak_share=float(neg_peak.negative_interval_share),
        partial_through=_day(bounds[1]),
    )

    def dump(frame: pd.DataFrame, spec: dict[str, int | None]) -> list[dict]:
        output = []
        for raw in frame.itertuples(index=False):
            mapped = raw._asdict()
            item = {}
            for key, digits in spec.items():
                value = mapped[key]
                if key == "month_start":
                    item["month"] = _iso(value)
                    item["month_label"] = _month(value)
                elif key == "is_complete_month":
                    item[key] = bool(value)
                elif isinstance(value, str) or digits is None:
                    item[key] = None if _missing(value) else value
                else:
                    item[key] = _num(value, digits)
            output.append(item)
        return output

    monthly_price = dump(
        price,
        {
            "region_id": None,
            "month_start": None,
            "rrp_vw_avg": 2,
            "rrp_stddev": 2,
            "is_complete_month": None,
        },
    )
    monthly_negative = dump(
        negative,
        {
            "region_id": None,
            "month_start": None,
            "negative_hours": 1,
            "negative_interval_share": 4,
            "is_complete_month": None,
        },
    )
    monthly_renewable = dump(
        renewable,
        {"region_id": None, "month_start": None, "renewable_share": 4, "peak_mw": 1},
    )
    hourly_rows = dump(
        hourly,
        {
            "region_id": None,
            "profile_slice": None,
            "hour_of_day": 0,
            "avg_demand_mw": 1,
            "avg_rrp": 2,
            "negative_interval_share": 4,
        },
    )
    scenario_rows = dump(
        scenarios,
        {
            "region_id": None,
            "scenario_mw": 0,
            "baseline_peak_operational_demand_mw": 1,
            "peak_operational_demand_mw": 1,
            "baseline_evening_peak_avg_mw": 1,
            "baseline_midday_avg_mw": 1,
            "baseline_evening_midday_gap_mw": 1,
            "intervals_above_historical_peak": 0,
            "added_energy_gwh": 1,
            "uplift_pct_of_baseline_peak": 4,
        },
    )
    shape_rows = dump(
        scenario_hourly,
        {"region_id": None, "scenario_mw": 0, "hour_of_day": 0, "avg_demand_mw": 1},
    )

    sources = [
        {
            "name": "AEMO aggregated price and demand",
            "url": "https://www.aemo.com.au/energy-systems/electricity/national-electricity-market-nem/data-nem/aggregated-data",
            "note": "5-minute RRP and TOTALDEMAND. AEMO Material, used with attribution.",
        },
        {
            "name": "AEMO copyright permissions",
            "url": "https://www.aemo.com.au/privacy-and-legal-notices/copyright-permissions",
            "note": "General permission to use public AEMO Material with attribution.",
        },
        {
            "name": "Open Electricity daily energy statistics",
            "url": "https://data.openelectricity.org.au/v4/stats/au/NEM/NSW1/energy/2025.json",
            "note": "Public static files, no API key. Fuel-technology energy by region and day.",
        },
        {
            "name": "AEMC ERC0461 rule change request",
            "url": "https://www.aemc.gov.au/sites/default/files/2026-10/Contract%20obligation%20rule%20change%20request%20%281%29.pdf",
            "note": "Chris Bowen, 20 October 2026. Data centres to contract firmed energy.",
        },
        {
            "name": "AEMO 2026 Electricity Statement of Opportunities",
            "url": "https://www.aemo.com.au/-/media/files/electricity/nem/planning_and_forecasting/nem_esoo/2026/2026-electricity-statement-of-opportunities.pdf",
            "note": "About 15 TWh (7.8%) by 2029-30 and about 34 TWh (13%) by 2035-36.",
        },
        {
            "name": "Smart Energy Council, $40 billion hike",
            "url": "https://smartenergy.org.au/dirty-data-the-40-billion-ai-power-bill-from-fossil-fuel/",
            "note": "External price study of a 5 GW build-first scenario. Not a result of this model.",
        },
    ]

    return {
        "as_of_label": _day(bounds[1]),
        "window_label": f"{_day(bounds[0])} to {_day(bounds[1])}",
        "latest_month_label": latest_label,
        "prior_month_label": prior_label,
        "partial_month_label": "October 2026",
        "banner": (
            f"History runs from {_day(bounds[0])} to {_day(bounds[1])} in NEM time "
            "(AEST, no daylight saving). October 2026 is partial and is excluded from the KPI cards. "
            "The load scenarios add a flat megawatt trace to recorded demand. They do not re-clear the market."
        ),
        "kpis": kpis,
        "regions": [
            {
                "id": row.region_id,
                "name": row.region_name,
                "colour": row.colour_hex,
                "kind": row.region_type,
            }
            for row in regions.itertuples(index=False)
        ],
        "monthly_price": monthly_price,
        "monthly_negative": monthly_negative,
        "monthly_renewable": monthly_renewable,
        "hourly": hourly_rows,
        "scenarios": scenario_rows,
        "scenario_hourly": shape_rows,
        "recommendations": recommendations,
        "sources": sources,
        "generated_for": "nem-grid-pulse",
        "model_note": MODEL_NOTE,
        "narrative": {
            "history_vwap": round(history_vwap, 2),
            "history_share": round(history_share, 4),
            "latest_price": round(price_now, 2),
            "baseline_price": round(baseline_vwap, 2),
            "latest_peak_mw": round(latest_peak, 1),
            "latest_negative_hours": round(neg_now, 1),
            "latest_negative_share": round(float(latest_neg.negative_interval_share), 4),
            "latest_volatility": round(vol_now, 2),
            "latest_renewable_share": round(share_now, 4),
            "tas_plus_1gw_fraction": round(tas_fraction, 4),
            "nsw_plus_1gw_fraction": round(nsw_fraction, 4),
            "nem_gap_mw": round(float(base_nem.baseline_evening_midday_gap_mw), 1),
            "nem_peak_mw": round(float(base_nem.baseline_peak_operational_demand_mw), 1),
            "nem_plus_5gw_peak_mw": round(float(nem_row.peak_operational_demand_mw), 1),
            "nem_new_peaks": int(nem_row.intervals_above_historical_peak),
            "jumpy_month": _month(jumpy.month_start),
            "jumpy_stddev": round(float(jumpy.rrp_stddev), 2),
            "neg_peak_month": _month(neg_peak.month_start),
            "neg_peak_share": round(float(neg_peak.negative_interval_share), 4),
            "sa_negative_hours": round(float(sa_sep.negative_hours), 1),
            "sa_negative_share": round(float(sa_sep.negative_interval_share), 4),
        },
    }


def _missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _kpi(
    kpi_id: str,
    label: str,
    value: str,
    unit: str,
    period: str,
    trend: str,
    direction: str,
    tone: str,
    gap: str,
    status: str,
) -> dict:
    return {
        "id": kpi_id,
        "label": label,
        "value": value,
        "unit": unit,
        "period": period,
        "trend": trend,
        "direction": direction,
        "tone": tone,
        "gap": gap,
        "status": status,
        "status_label": STATUS_LABEL[status],
    }


def _recommendations(**k) -> list[dict]:
    sa = k["scenario_1gw"].loc["SA1"]
    tas = k["scenario_1gw"].loc["TAS1"]
    nsw = k["scenario_1gw"].loc["NSW1"]
    return [
        {
            "title": "A flat offtake does not fill the duck curve",
            "body": (
                f"Over the last 12 complete months the NEM's average evening peak was "
                f"{_mw(float(k['base_nem'].baseline_evening_peak_avg_mw))} and the midday average was "
                f"{_mw(float(k['base_nem'].baseline_midday_avg_mw))}. The gap is "
                f"{_mw(float(k['base_nem'].baseline_evening_midday_gap_mw))}. "
                f"Adding 1 GW in every region lifts the evening and the middle of the day by the same "
                f"5,000 MW, so the ramp does not shrink. The half-hour peak rises from "
                f"{_mw(float(k['base_nem'].baseline_peak_operational_demand_mw))} to "
                f"{_mw(float(k['nem_row'].peak_operational_demand_mw))}, and "
                f"{int(k['nem_row'].intervals_above_historical_peak):,} half-hours would sit above the "
                f"highest half-hour in that window."
            ),
        },
        {
            "title": "A gigawatt is a different problem in Tasmania than in New South Wales",
            "body": (
                f"+1 GW is {_pct(float(nsw.uplift_pct_of_baseline_peak))} of New South Wales' "
                f"{_mw(float(nsw.baseline_peak_operational_demand_mw))} peak and would have set a new "
                f"half-hour record {int(nsw.intervals_above_historical_peak)} times. The same gigawatt is "
                f"{_pct(float(tas.uplift_pct_of_baseline_peak))} of Tasmania's "
                f"{_mw(float(tas.baseline_peak_operational_demand_mw))} peak and would have exceeded that "
                f"record in {int(tas.intervals_above_historical_peak):,} half-hours, close to every interval "
                f"in the year. Treat the +1 GW and +2 GW Tasmania cases as scale illustrations."
            ),
        },
        {
            "title": "South Australia already shows where surplus and scarcity sit in the day",
            "body": (
                f"South Australia's midday operational demand averaged {_mw(float(sa.baseline_midday_avg_mw))} "
                f"against an evening average of {_mw(float(sa.baseline_evening_peak_avg_mw))}. "
                f"In {k['latest_label']} the South Australian spot price was negative for "
                f"{k['sa_hours']:.0f} hours, {_pct(k['sa_share'])} of intervals. "
                f"A flat load sits on the evening peak as heavily as it sits on that trough. "
                f"Load that can move into the middle of the day is a different physical proposition. "
                f"This page does not turn that into a price forecast."
            ),
        },
        {
            "title": "September prices were soft, and that is not the whole story",
            "body": (
                f"The NEM volume-weighted price in {k['latest_label']} was {_aud(k['price_now'])}/MWh, "
                f"against {_aud(k['price_prev'])} in {k['prior_label']} and a "
                f"{_aud(k['baseline_vwap'])} average over the twelve months before it. "
                f"Renewable share of local generation was {_pct(k['share_now'])} "
                f"(South Australia {_pct(k['region_shares']['SA1'])}, Tasmania {_pct(k['region_shares']['TAS1'])}, "
                f"Queensland {_pct(k['region_shares']['QLD1'])}). "
                f"Negative NEM-price hours jumped from {k['neg_prev']:.0f} in {k['prior_label']} to "
                f"{k['neg_now']:.0f}. That spring pattern is familiar: {k['neg_peak_month']} reached "
                f"{_pct(k['neg_peak_share'])} of intervals. The jumpiest complete month in the prior year was "
                f"{k['jumpy_month']}, with a 5-minute standard deviation of {_aud(k['jumpy_sd'])}/MWh. "
                f"October 2026 is only in the file through {k['partial_through']} and is not in the cards above."
            ),
        },
        {
            "title": "Firming is a megawatt question before it is a dollar question",
            "body": (
                "On 20 October 2026 Minister Chris Bowen asked the AEMC to require qualifying data centres "
                "to back their load with firmed energy in the same region. AEMO's 2026 ESOO puts data-centre "
                "consumption near 15 TWh (7.8% of NEM operational consumption) by 2029-30 and near 34 TWh "
                "(13%) by 2035-36. The Smart Energy Council's separate modelling says a 5 GW 'build first, "
                "catch up later' path could add $40 billion to wholesale costs. This warehouse does not "
                "reproduce that price result. A flat +1 GW in a single region is 8,760 GWh a year and raises "
                "the regional peak by 1,000 MW, one for one. That is the quantity a firming contract would "
                "have to cover at the historical peak, not a prediction of the spot price."
            ),
        },
    ]


def render_markdown(payload: dict) -> str:
    n = payload["narrative"]
    recs = "\n\n".join(f"### {item['title']}\n\n{item['body']}" for item in payload["recommendations"])
    cards = "\n".join(
        (
            f"- **{card['label']}:** {card['value']}"
            f"{(' · ' + card['unit']) if card['unit'] else ''} "
            f"({card['period']}, {card['status_label']}). {card['trend']}. {card['gap']}."
        )
        for card in payload["kpis"]
    )
    return f"""# What the NEM is telling us about flat data-centre load

These figures are computed from the marts in this repository. The study window is {payload["window_label"]}, in NEM time (AEST, year-round). {payload["latest_month_label"]} is the last complete month. October 2026 is included in the charts and stops at {payload["as_of_label"]}.

The scenario panel is an illustrative energy balance. It adds a constant megawatt trace to recorded operational demand. It is not a forecast, not a dispatch model, and not an estimate of wholesale prices.

## Headline

Across the full extract, the NEM volume-weighted price was ${n["history_vwap"]:,.2f}/MWh and renewables supplied {n["history_share"] * 100:.1f}% of local generation. {payload["latest_month_label"]} was softer than that history, at ${n["latest_price"]:,.2f}/MWh, with a half-hour peak of {n["latest_peak_mw"]:,.0f} MW and {n["latest_negative_hours"]:.0f} hours of a negative demand-weighted price.

The shape matters more than the monthly average. Over the last 12 complete months the gap between the NEM evening peak and the middle of the day stayed {n["nem_gap_mw"]:,.0f} MW. A flat load does not close it. Putting 1 GW in every region at once lifts the 12-month peak from {n["nem_peak_mw"]:,.0f} MW to {n["nem_plus_5gw_peak_mw"]:,.0f} MW.

## KPI snapshot

Status rules are fixed and documented in the README. Green, amber and red describe stress, not whether a number went up.

{cards}

## Reading the year

{recs}

## How to reproduce

```bash
make transform
python -m nem_grid_pulse insights
```

The commands read `data/warehouse/nem.duckdb` and rewrite this file from `mart_daily_region_summary`, `mart_price_volatility`, `mart_negative_price_events`, `mart_hourly_profile` and `mart_datacentre_load_scenarios`.
"""
