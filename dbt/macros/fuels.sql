{% macro fuel_set(kind) %}
    {%- if kind == 'renewable' -%}
        ('solar_rooftop', 'solar_utility', 'wind', 'hydro', 'bioenergy_biomass')
    {%- elif kind == 'fossil' -%}
        ('coal_black', 'coal_brown', 'distillate', 'gas_ccgt', 'gas_ocgt', 'gas_recip', 'gas_steam', 'gas_wcmg')
    {%- elif kind == 'grid_vre' -%}
        ('solar_utility', 'wind')
    {%- elif kind == 'storage_discharge' -%}
        ('battery_discharging')
    {%- elif kind == 'storage_load' -%}
        ('battery_charging', 'pumps')
    {%- elif kind == 'interchange' -%}
        ('imports', 'exports')
    {%- else -%}
        {{ exceptions.raise_compiler_error('unknown fuel set ' ~ kind) }}
    {%- endif -%}
{% endmacro %}
