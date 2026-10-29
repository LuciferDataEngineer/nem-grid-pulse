select region_id, profile_slice, hour_of_day, count(*) as row_count
from {{ ref('mart_hourly_profile') }}
group by region_id, profile_slice, hour_of_day
having count(*) > 1
