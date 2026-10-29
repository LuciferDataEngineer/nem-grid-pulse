select
    hour_of_day,
    printf('%02d:00-%02d:00', hour_of_day, (hour_of_day + 1) % 24) as hour_label,
    hour_of_day between 17 and 20 as is_evening_peak,
    hour_of_day between 10 and 14 as is_midday,
    hour_of_day <= 5 as is_overnight,
    case
        when hour_of_day between 17 and 20 then 'evening_peak'
        when hour_of_day between 10 and 14 then 'midday'
        when hour_of_day <= 5 then 'overnight'
        else 'shoulder'
    end as daypart
from range(0, 24) as hours(hour_of_day)
