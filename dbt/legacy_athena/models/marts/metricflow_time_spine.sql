{{
    config(
        materialized = 'table',
    )
}}

with days as (
    {{ dbt.date_spine(
        datepart="day",
        start_date="cast('2000-01-01' as date)",
        end_date="cast('2030-01-01' as date)"
    ) }}
)

select
    date_day,
    date_day as date_day_timestamp
from days
