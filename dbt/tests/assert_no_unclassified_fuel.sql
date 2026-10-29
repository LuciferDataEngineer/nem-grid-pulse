select region_id, trading_date, other_gwh
from {{ ref('int_generation_daily') }}
where other_gwh is not null
    and abs(other_gwh) > 0.0001
