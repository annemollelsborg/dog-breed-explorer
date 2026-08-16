with traits as (

    select * from {{ ref('stg_breed_temperaments') }}

),

total_breeds as (

    select count(*) as total from {{ ref('int_breeds_enriched') }}

)

select
    traits.temperament_trait,
    count(distinct traits.breed_id) as breed_count,
    round(100.0 * count(distinct traits.breed_id) / total_breeds.total, 1) as pct_of_breeds
from traits
cross join total_breeds
group by traits.temperament_trait, total_breeds.total
order by breed_count desc
