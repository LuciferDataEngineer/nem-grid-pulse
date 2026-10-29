select
    region_id,
    region_name,
    state_name,
    region_type,
    colour_hex,
    timezone_note
from (
    values
        ('NSW1', 'New South Wales', 'New South Wales', 'region', '#E07A3D', 'Market time is NEM time, AEST (UTC+10), not local daylight saving time.'),
        ('QLD1', 'Queensland', 'Queensland', 'region', '#7C3AED', 'Queensland local time matches NEM time all year.'),
        ('VIC1', 'Victoria', 'Victoria', 'region', '#2563EB', 'Market time is NEM time, AEST (UTC+10), not local daylight saving time.'),
        ('SA1', 'South Australia', 'South Australia', 'region', '#DC2626', 'Market time is NEM time, AEST (UTC+10), not local Adelaide time.'),
        ('TAS1', 'Tasmania', 'Tasmania', 'region', '#0F766E', 'Market time is NEM time, AEST (UTC+10), not local daylight saving time.'),
        ('NEM', 'National Electricity Market', 'NEM', 'market', '#0A2540', 'Demand-weighted rollup of the five NEM regions. Demand is summed because regional net imports cancel.')
) as region(region_id, region_name, state_name, region_type, colour_hex, timezone_note)
