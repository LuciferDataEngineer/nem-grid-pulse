with bounds as (
    select
        min(trading_date) as min_day,
        max(trading_date) as max_day
    from {{ ref('fct_price_demand_30min') }}
),
spine as (
    select cast(unnest(generate_series(min_day, max_day, interval 1 day)) as date) as date_day
    from bounds
)

select
    date_day,
    cast(extract('year' from date_day) as integer) as calendar_year,
    cast(extract('month' from date_day) as integer) as calendar_month,
    strftime(date_day, '%Y-%m') as year_month,
    date_trunc('month', date_day)::date as month_start,
    cast(extract('isodow' from date_day) as integer) as iso_day_of_week,
    extract('isodow' from date_day) in (6, 7) as is_weekend,
    case
        when extract('month' from date_day) in (12, 1, 2) then 'summer'
        when extract('month' from date_day) in (3, 4, 5) then 'autumn'
        when extract('month' from date_day) in (6, 7, 8) then 'winter'
        else 'spring'
    end as season_name,
    strftime(date_day, '%b %Y') as month_label
from spine
