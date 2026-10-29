{{ config(
    materialized='incremental',
    unique_key='price_interval_key',
    incremental_strategy='delete+insert',
    on_schema_change='sync_all_columns'
) }}

select
    region_id || '|' || strftime(settlement_ts, '%Y-%m-%d %H:%M:%S') as price_interval_key,
    region_id,
    settlement_ts,
    trading_date,
    hour_of_day,
    demand_mw,
    rrp_time_weighted,
    rrp_volume_weighted,
    interval_count
from {{ ref('int_price_demand_30min') }}
where is_complete
{% if is_incremental() %}
    and settlement_ts >= (
        select coalesce(max(settlement_ts), timestamp '1970-01-01') - interval 2 day
        from {{ this }}
    )
{% endif %}
