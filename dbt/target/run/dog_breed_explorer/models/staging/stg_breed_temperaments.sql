
  
  create view "dog_breeds"."main"."stg_breed_temperaments__dbt_tmp" as (
    with base as (

    select
        breed_id,
        name,
        temperament
    from "dog_breeds"."main"."stg_breeds"
    where temperament is not null

),

split as (

    select
        breed_id,
        name,
        lower(trim(unnest(string_split(temperament, ',')))) as temperament_trait
    from base

)

select
    breed_id,
    name,
    temperament_trait
from split
where temperament_trait != ''
  );
