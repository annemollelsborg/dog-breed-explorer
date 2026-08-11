with latest_raw as (

    select
        breed_id,
        raw_json,
        loaded_at,
        row_number() over (partition by breed_id order by loaded_at desc) as rn
    from "dog_breeds"."raw"."raw_breeds"

),

deduped as (

    select breed_id, raw_json, loaded_at
    from latest_raw
    where rn = 1

),

extracted as (

    select
        breed_id,
        loaded_at,
        json_extract_string(raw_json, '$.name') as name,
        json_extract_string(raw_json, '$.breed_group') as breed_group,
        json_extract_string(raw_json, '$.origin') as origin,
        json_extract_string(raw_json, '$.bred_for') as bred_for,
        json_extract_string(raw_json, '$.temperament') as temperament,
        json_extract_string(raw_json, '$.life_span') as life_span_raw,
        json_extract_string(raw_json, '$.weight.metric') as weight_metric_raw
    from deduped

)

select
    cast(breed_id as integer) as breed_id,
    name,
    breed_group,
    origin,
    bred_for,
    temperament,

    -- life_span arrives as e.g. "10-16" (years), sometimes null
    cast(
        list_min(list_transform(regexp_extract_all(life_span_raw, '[0-9]+'), x -> cast(x as integer)))
        as integer
    ) as life_span_min_years,
    cast(
        list_max(list_transform(regexp_extract_all(life_span_raw, '[0-9]+'), x -> cast(x as integer)))
        as integer
    ) as life_span_max_years,

    -- weight.metric arrives as either "27-43" or gendered "Male: 25-30; Female: 20-25";
    -- take the true min/max across all numbers found so the range covers the full breed
    list_min(list_transform(regexp_extract_all(weight_metric_raw, '[0-9]+\.?[0-9]*'), x -> cast(x as double))) as weight_min_kg,
    list_max(list_transform(regexp_extract_all(weight_metric_raw, '[0-9]+\.?[0-9]*'), x -> cast(x as double))) as weight_max_kg,

    loaded_at
from extracted