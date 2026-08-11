-- Fails if any breed has life_span_min_years >= life_span_max_years.
-- Rows with a null life_span are excluded (null comparisons don't match).
select breed_id, name, life_span_min_years, life_span_max_years
from {{ ref('stg_breeds') }}
where life_span_min_years >= life_span_max_years
