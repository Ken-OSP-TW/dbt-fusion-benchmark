{{ config(materialized='table') }}

select
    id::bigint as id,
    (id % 10000)::bigint as customer_id,
    (id % 1000)::integer as product_id,
    (id % 100)::integer as customer_group,
    case
        when id % 4 = 0 then 'DE'
        when id % 4 = 1 then 'FR'
        when id % 4 = 2 then 'NL'
        else 'AT'
    end as country,
    cast((id % 10000) / 100.0 as decimal(18, 2)) as amount,
    timestamp '2025-01-01 00:00:00'
        + (id % 31536000) * interval '1 second' as event_timestamp
from range(0, {{ var('rows', 100000) }}) as generated(id)