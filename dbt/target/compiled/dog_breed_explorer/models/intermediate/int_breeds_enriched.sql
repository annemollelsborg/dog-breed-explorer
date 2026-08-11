with breeds as (

    select * from "dog_breeds"."main"."stg_breeds"

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
    (life_span_min_years + life_span_max_years) / 2.0 as life_span_avg_years,
    weight_min_kg,
    weight_max_kg,
    (weight_min_kg + weight_max_kg) / 2.0 as weight_avg_kg,
    case
        when (weight_min_kg + weight_max_kg) / 2.0 < 10 then 'Small'
        when (weight_min_kg + weight_max_kg) / 2.0 < 25 then 'Medium'
        else 'Large'
    end as size_class,
    loaded_at
from breeds