with months as (
    select
        date_trunc('month', trading_date)::date as month_start,
        max(trading_date) as max_day
    from {{ ref('stg_aemo_price_demand') }}
    group by 1
),
flagged as (
    select
        month_start,
        max_day = (month_start + interval 1 month - interval 1 day)::date as is_complete_month
    from months
),
ranked as (
    select
        month_start,
        is_complete_month,
        row_number() over (
            partition by is_complete_month
            order by month_start desc
        ) as rank_in_partition
    from flagged
)

select
    month_start,
    is_complete_month,
    is_complete_month and rank_in_partition <= 12 as is_last_12_complete
from ranked
