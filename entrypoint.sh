#!/bin/sh
set -e

python ingestion/fetch_breeds.py

cd dbt
dbt run --profiles-dir .
dbt test --profiles-dir .
cd ..

exec streamlit run dashboard/app.py --server.address=0.0.0.0 --server.port=8501
