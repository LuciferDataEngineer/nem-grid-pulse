# What the NEM is telling us about flat data-centre load

These figures are computed from the marts in this repository. The study window is 1 November 2023 to 27 October 2026, in NEM time (AEST, year-round). September 2026 is the last complete month. October 2026 is included in the charts and stops at 27 October 2026.

The scenario panel is an illustrative energy balance. It adds a constant megawatt trace to recorded operational demand. It is not a forecast, not a dispatch model, and not an estimate of wholesale prices.

## Headline

Across the full extract, the NEM volume-weighted price was $105.14/MWh and renewables supplied 41.9% of local generation. September 2026 was softer than that history, at $58.83/MWh, with a half-hour peak of 27,864 MW and 79 hours of a negative demand-weighted price.

The shape matters more than the monthly average. Over the last 12 complete months the gap between the NEM evening peak and the middle of the day stayed 8,227 MW. A flat load does not close it. Putting 1 GW in every region at once lifts the 12-month peak from 33,457 MW to 38,457 MW.

## KPI snapshot

Status rules are fixed and documented in the README. Green, amber and red describe stress, not whether a number went up.

- **NEM volume-weighted price:** $58.83 · /MWh (September 2026, Within band). -17.4% vs August 2026. -19.5% vs prior 12-month average.
- **NEM peak half-hour:** 27,864 MW (September 2026, Within band). -10.1% vs August 2026. -6.4% vs prior 12 monthly peaks.
- **Hours with a negative NEM price:** 79 h · 11.0% of intervals (September 2026, High stress). +64 h vs August 2026. +1.8 pp vs prior 12-month average.
- **NEM price volatility:** $39.85 · std. dev. of 5-min RRP (September 2026, Within band). +5.3% vs August 2026. -64.5% vs prior 12-month average.
- **Renewable share of local generation:** 49.2% · NEM, rooftop included, imports excluded (September 2026, Within band). +7.5 pp vs August 2026. +4.1 pp vs prior 12-month generation.
- **Tightest region for a flat +1 GW:** Tasmania · 62.3% of its own peak (Last 12 complete months, High stress). Peak was 1,605 MW. NSW +1 GW is 7.7% of its peak.

## Reading the year

### A flat offtake does not fill the duck curve

Over the last 12 complete months the NEM's average evening peak was 25,767 MW and the midday average was 17,540 MW. The gap is 8,227 MW. Adding 1 GW in every region lifts the evening and the middle of the day by the same 5,000 MW, so the ramp does not shrink. The half-hour peak rises from 33,457 MW to 38,457 MW, and 439 half-hours would sit above the highest half-hour in that window.

### A gigawatt is a different problem in Tasmania than in New South Wales

+1 GW is 7.7% of New South Wales' 13,024 MW peak and would have set a new half-hour record 10 times. The same gigawatt is 62.3% of Tasmania's 1,605 MW peak and would have exceeded that record in 17,212 half-hours, close to every interval in the year. Treat the +1 GW and +2 GW Tasmania cases as scale illustrations.

### South Australia already shows where surplus and scarcity sit in the day

South Australia's midday operational demand averaged 818 MW against an evening average of 1,685 MW. In September 2026 the South Australian spot price was negative for 217 hours, 30.1% of intervals. A flat load sits on the evening peak as heavily as it sits on that trough. Load that can move into the middle of the day is a different physical proposition. This page does not turn that into a price forecast.

### September prices were soft, and that is not the whole story

The NEM volume-weighted price in September 2026 was $58.83/MWh, against $71.22 in August 2026 and a $73.09 average over the twelve months before it. Renewable share of local generation was 49.2% (South Australia 84.1%, Tasmania 91.9%, Queensland 40.5%). Negative NEM-price hours jumped from 15 in August 2026 to 79. That spring pattern is familiar: November 2025 reached 25.7% of intervals. The jumpiest complete month in the prior year was November 2025, with a 5-minute standard deviation of $245.87/MWh. October 2026 is only in the file through 27 October 2026 and is not in the cards above.

### Firming is a megawatt question before it is a dollar question

On 20 October 2026 Minister Chris Bowen asked the AEMC to require qualifying data centres to back their load with firmed energy in the same region. AEMO's 2026 ESOO puts data-centre consumption near 15 TWh (7.8% of NEM operational consumption) by 2029-30 and near 34 TWh (13%) by 2035-36. The Smart Energy Council's separate modelling says a 5 GW 'build first, catch up later' path could add $40 billion to wholesale costs. This warehouse does not reproduce that price result. A flat +1 GW in a single region is 8,760 GWh a year and raises the regional peak by 1,000 MW, one for one. That is the quantity a firming contract would have to cover at the historical peak, not a prediction of the spot price.

## How to reproduce

```bash
make transform
python -m nem_grid_pulse insights
```

The commands read `data/warehouse/nem.duckdb` and rewrite this file from `mart_daily_region_summary`, `mart_price_volatility`, `mart_negative_price_events`, `mart_hourly_profile` and `mart_datacentre_load_scenarios`.
