# Data Platform: Dog Breed Explorer

[![CI](https://github.com/annemollelsborg/dog-breed-explorer/actions/workflows/ci.yml/badge.svg)](https://github.com/annemollelsborg/dog-breed-explorer/actions/workflows/ci.yml)
[![Daily Pipeline](https://github.com/annemollelsborg/dog-breed-explorer/actions/workflows/daily_pipeline.yml/badge.svg)](https://github.com/annemollelsborg/dog-breed-explorer/actions/workflows/daily_pipeline.yml)

An end-to-end pipeline that pulls breed data from [TheDogAPI](https://www.thedogapi.com/), cleans and models it with dbt on DuckDB, and exposes it through a Streamlit dashboard. Runs daily via GitHub Actions.

[Dashboard PDF export](dashboard/example.pdf) — a snapshot of the dashboard if you'd rather not run it locally.

## How it works

```
ingestion/fetch_breeds.py  ->  raw.raw_breeds (DuckDB)
                            ->  dbt: stg_breeds, stg_breed_temperaments  (staging)
                            ->  dbt: int_breeds_enriched                 (intermediate)
                            ->  dbt: mart_dog_breeds                     (marts)
                            ->  dashboard/app.py (Streamlit)
```

- **Ingestion** pulls the full breed list, stores the raw JSON untouched with a `loaded_at` timestamp, and is idempotent — re-running it the same day replaces that day's rows instead of duplicating them.
- **dbt** parses the messy `life_span` and `weight` text ranges into typed min/max/avg columns, splits the comma-separated `temperament` list into queryable rows, and derives a `size_class` (Small / Medium / Large) from average weight. `mart_dog_breeds` is the final one-row-per-breed table the dashboard reads from.
- **Tests**: not-null and uniqueness on `breed_id`, not-null on `name`, plus a custom check that `life_span_min < life_span_max`.
- **Docs**: run `dbt docs generate && dbt docs serve --profiles-dir .` from `dbt/` for a browsable site with descriptions.
- **CI** (`.github/workflows/ci.yml`) runs ingestion, `dbt run`, and `dbt test` on every push and pull request. **Daily Pipeline** (`.github/workflows/daily_pipeline.yml`) runs the same sequence on a 02:00 UTC schedule to keep the data fresh.

## Running it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# add your TheDogAPI key (free at https://thedogapi.com/signup)
echo "API_KEY=your_key_here" > .env

python ingestion/fetch_breeds.py
cd dbt && dbt run --profiles-dir . && dbt test --profiles-dir . && cd ..

streamlit run dashboard/app.py
```

### Or with Docker

No local Python setup needed — `docker compose up` runs ingestion, `dbt run`, and `dbt test` inside the container, then serves the dashboard.

```bash
# add your TheDogAPI key (free at https://thedogapi.com/signup)
echo "API_KEY=your_key_here" > .env

docker compose up --build
```

Then open http://localhost:8501. `Ctrl+C` (or `docker compose down`) to stop it.

## What the data shows

The data covers breed name, breed group, country of origin, temperament traits, life span (min/max/avg years), weight (min/max/avg kg), and a derived size class (Small/Medium/Large).

Across all 631 breeds, average predicted life span is 12.5 years. There's a real but modest size-longevity gradient: Small breeds average 13.3 years, Medium 13.0, Large 11.8, though it's not a clean rule. The five longest-lived breeds (Denmark Feist, Koolie, Miniature Fox Terrier, Rat Terrier, Silken Windhound, all at 15 years) are a mix of Small, Medium, and even Large dogs.

By weight class, Large breeds are the biggest group (42%), ahead of Medium (40%) and Small (19%).

Temperament is the richest field, with 49 distinct traits recorded. Intelligent (85% of breeds), Loyal (72%), and Alert (60%) are by far the most common. "Friendly" ranks 8th, present in just 26% of breeds.