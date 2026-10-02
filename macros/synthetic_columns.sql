{% macro synthetic_columns(table_alias, layer, count) %}

    {% for column_number in range(1, count + 1) %}
        , (
            {{ table_alias }}.amount
            * {{ 1 + (column_number / 1000.0) }}
            + {{ layer }}
            + {{ column_number }}
        ) as calculated_value_{{ "%03d" | format(column_number) }}
    {% endfor %}

{% endmacro %}