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

Across all 631 breeds, average predicted life span is **12.5 years**, but small and toy breeds dominate the top of the list — **Denmark Feist, Koolie, Miniature Fox Terrier, Rat Terrier and Silken Windhound** all average **15 years**, consistent with the well-documented inverse relationship between body size and canine longevity.

By weight class, **Large breeds are the single biggest group (42%)**, followed by Medium (40%) and Small (19%) — the dataset leans toward bigger dogs overall, even though the *longest-lived* breeds skew small.