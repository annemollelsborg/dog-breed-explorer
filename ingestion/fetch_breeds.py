import json
import os
import sys
from datetime import datetime, timezone

import duckdb
import requests
from dotenv import load_dotenv

API_URL = "https://api.thedogapi.com/v1/breeds"
DB_PATH = "dog_breeds.duckdb"


def fetch_breeds():
    load_dotenv()
    api_key = os.environ.get("API_KEY")
    headers = {"x-api-key": api_key} if api_key else {}

    response = requests.get(API_URL, headers=headers, timeout=30)
    response.raise_for_status()
    breeds = response.json()

    if not isinstance(breeds, list) or not breeds:
        raise ValueError(f"Unexpected response from {API_URL}: expected a non-empty list")

    return breeds


def load_raw_breeds(breeds, con):
    loaded_at = datetime.now(timezone.utc)
    today = loaded_at.date()

    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw.raw_breeds (
            breed_id INTEGER,
            raw_json JSON,
            loaded_at TIMESTAMP
        )
    """)

    rows = [(breed.get("id"), json.dumps(breed), loaded_at) for breed in breeds]

    con.begin()
    try:
        con.execute("DELETE FROM raw.raw_breeds WHERE CAST(loaded_at AS DATE) = ?", [today])
        con.executemany("INSERT INTO raw.raw_breeds VALUES (?, ?, ?)", rows)
        con.commit()
    except Exception:
        con.rollback()
        raise

    return len(rows)


def main():
    try:
        breeds = fetch_breeds()
    except (requests.RequestException, ValueError) as exc:
        print(f"Failed to fetch breeds: {exc}", file=sys.stderr)
        sys.exit(1)

    con = duckdb.connect(DB_PATH)
    row_count = load_raw_breeds(breeds, con)
    con.close()

    print(f"Loaded {row_count} rows into raw.raw_breeds")


if __name__ == "__main__":
    main()
