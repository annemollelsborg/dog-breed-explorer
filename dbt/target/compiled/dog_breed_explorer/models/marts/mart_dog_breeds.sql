with breeds as (

    select * from "dog_breeds"."main"."int_breeds_enriched"

)

select
    breed_id,
    name,
    breed_group,
    origin,
    bred_for,
    temperament,
    life_span_min_years,
    life_span_max_years,
    round(life_span_avg_years, 1) as life_span_avg_years,
    weight_min_kg,
    weight_max_kg,
    round(weight_avg_kg, 1) as weight_avg_kg,
    size_class,
    loaded_at
from breeds