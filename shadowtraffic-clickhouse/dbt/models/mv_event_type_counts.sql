{{ config(materialized='materialized_view') }}

select
    event_type,
    count() as event_count,
    max(event_time) as latest_event_time
from {{ source('shadowtraffic', 'events') }}
group by event_type
