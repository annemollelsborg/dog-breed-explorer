# Decisions

Every tool chosen is the simplest option that does the job well. The stack is local, free, and fully explainable end to end.

**Extraction and ingestion: Python script (requests).** Easy and fast for accessing API endpoints and moving data around. No volume here that would justify a dedicated ingestion tool. Idempotent by deleting today's rows before inserting, with the raw JSON preserved untouched.

**Database and data warehouse: DuckDB (local).** A light local database that requires no setup or cloud account. Ideal for a project of this scale (631 rows). Allows to use SQL, schemas, and a raw/staging/marts separation. 

Tradeoff: single-writer, file-based, fine for one pipeline and one dashboard reader but not concurrent access. 

Something to do differently: To host the dashboard live, I'd swap the local DuckDB file for MotherDuck (its hosted counterpart, free tier). The daily pipeline would write to it directly and the hosted dashboard would read from the same remote database, with no other changes needed since dbt-duckdb supports MotherDuck connection strings natively.

**Transformation and modeling: dbt Core.** Industry standard for data transformation. Allows SQL models to be organised, tested, and documented in a reproducible way.

- Two dbt targets, `dev` and `prod`, each pointing at a different local DuckDB file, so the same models can run against either without code changes.
- The real API data didn't match the brief's example format (life_span has no "years" suffix, weight is sometimes gendered like "Male: 25-30; Female: 20-25"), so staging was built to handle what the API actually returns.
- Temperament splitting got its own model instead of being done inside `stg_breeds`, since exploding that model to one row per trait would have broken the required `breed_id` uniqueness test.
- Sensible typing: Raw fields come in as text (even `breed_id` is a string in the API), so staging casts them into real types; `breed_id` as integer, life span and weight as integer/decimal, `loaded_at` as timestamp. Backed by four tests: `breed_id` not-null and unique, `name` not-null, and a custom check that `life_span_min` is always less than `life_span_max`.

Next: Extend error handling to catch poor-quality parsed values, not just structural problems. The temperament split currently lets a malformed sentence ("variable depending on ancestry and individual traits") through as if it were a real trait, and keeps near-synonyms (e.g. "energetic", "lively", "spirited") as separate values instead of merging them into one consistent category. Embeddings could be used to normalize the vocabulary and flag non-trait text.

**Version control: GitHub.** Hosts the repository with a meaningful commit history. Keeps CI/CD and orchestration in the same place.

**CI/CD: GitHub Actions.** Does the job, no extra services needed. Runs ingestion, dbt run, and dbt test on every push and pull request, pass/fail visible via a README badge.

**Orchestration and scheduling: GitHub Actions.** Same as above: Fewer new services, one daily job doesn't justify Airflow or Dagster. 

Tradeoff: GitHub's cron is best-effort, not exact (one run fired at 04:09 UTC instead of 02:00). Not an issue here. E.g. traffic data would require a hard deadline and need a dedicated scheduler.

**Dashboard and visualization: Streamlit.** Fast way to turn a DataFrame into an interactive dashboard, reading straight from the DuckDB file the pipeline builds. 

Tradeoff: runs locally (venv or `docker compose up`), not at a hosted URL, since the DuckDB file is a build artifact, not something committed. A PDF export is included instead. 

Next: Host it live on Streamlit Community Cloud, once the daily pipeline can publish its DuckDB output somewhere the hosted app can read from.
