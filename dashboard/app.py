import os

import altair as alt
import duckdb
import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()

DB_PATH = "dog_breeds.duckdb"
GEMINI_MODEL = "gemini-2.5-flash"
BLOCKED_SQL_KEYWORDS = (
    "insert", "update", "delete", "drop", "alter",
    "attach", "create", "copy", "pragma", "call",
)

SIZE_ORDER = ["Small", "Medium", "Large"]
SIZE_COLORS = ["#86b6ef", "#2a78d6", "#104281"]  # ordinal ramp, light -> dark


@st.cache_data
def load_breeds():
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("select * from mart_dog_breeds").df()
    con.close()
    return df


# --- Natural-language search helpers -----------------------------------------


@st.cache_resource
def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    return genai.Client(api_key=api_key) if api_key else None


@st.cache_data
def get_schema_text():
    con = duckdb.connect(DB_PATH, read_only=True)
    schema = con.execute("DESCRIBE mart_dog_breeds").df()
    con.close()
    return "\n".join(f"- {row.column_name} ({row.column_type})" for row in schema.itertuples())


def get_temperament_vocab(breeds_df):
    traits = set()
    for value in breeds_df["temperament"].dropna():
        for trait in value.split(","):
            trait = trait.strip().lower()
            if trait:
                traits.add(trait)
    return sorted(traits)


def generate_sql(client, question, schema_text, traits):
    prompt = f"""You write a single DuckDB SELECT statement to answer a question about dog breeds.

Table: mart_dog_breeds
Columns:
{schema_text}

The `temperament` column is a comma-separated free-text list. Known trait values include:
{", ".join(traits)}
Match traits with ILIKE '%trait%', not exact equality.

Rules:
- Output ONLY the SQL query. No explanation, no markdown fences.
- Write exactly one SELECT statement against mart_dog_breeds. Never write INSERT, UPDATE,
  DELETE, DROP, ALTER, or any statement other than SELECT.

Question: {question}
SQL:"""
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    sql = response.text.strip()
    if sql.startswith("```"):
        sql = sql.strip("`")
        sql = sql.removeprefix("sql").strip()
    return sql


def is_safe_select(sql):
    lowered = sql.strip().lower().rstrip(";")
    if not lowered.startswith("select") or ";" in lowered:
        return False
    return not any(word in lowered for word in BLOCKED_SQL_KEYWORDS)


def run_sql(sql):
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


def explain_answer(client, question, result_df):
    display_df = result_df.drop(columns=["breed_id"], errors="ignore")
    rows_text = display_df.head(25).to_markdown(index=False)
    prompt = f"""A user asked: "{question}"

The database returned these rows:
{rows_text}

Write a short, friendly 2-4 sentence answer in plain English based only on this data.
Refer to breeds by name only — never mention breed_id or any other numeric identifier.
Do not invent anything not present in the rows."""
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text.strip()


st.set_page_config(page_title="Dog Breed Explorer", layout="wide")

st.title("Dog Breed Explorer")
st.markdown(
    "A curated look at dog breeds sourced from [TheDogAPI](https://www.thedogapi.com/), "
    "cleaned and modeled through a daily dbt + DuckDB pipeline."
)

df = load_breeds()
as_of = df["loaded_at"].max()
st.caption(f"Data as of {as_of:%Y-%m-%d %H:%M} UTC · {len(df)} breeds")

st.divider()

# --- Natural-language search --------------------------------------------------
st.subheader("Ask a question")
st.caption('Ask in plain English, e.g. "show me calm dogs under 15 kg"')

gemini_client = get_gemini_client()
if gemini_client is None:
    st.info("Add a `GEMINI_API_KEY` to your `.env` file to enable natural-language search.")
else:
    nl_question = st.text_input("Your question", key="nl_question")
    if st.button("Ask") and nl_question:
        with st.spinner("Generating query..."):
            try:
                sql = generate_sql(
                    gemini_client, nl_question, get_schema_text(), get_temperament_vocab(df)
                )
            except Exception as exc:
                st.error(f"Couldn't generate a query: {exc}")
                sql = None

        if sql and not is_safe_select(sql):
            st.error("The generated query didn't pass the safety check — try rephrasing.")
        elif sql:
            with st.expander("Generated SQL"):
                st.code(sql, language="sql")

            with st.spinner("Running query..."):
                try:
                    result = run_sql(sql)
                except Exception as exc:
                    st.error(f"Query failed: {exc}")
                    result = None

            if result is not None:
                if result.empty:
                    st.warning("No breeds matched that question.")
                else:
                    with st.spinner("Writing answer..."):
                        answer = explain_answer(gemini_client, nl_question, result)
                    st.markdown(answer)

st.divider()

# --- Chart 1: longest predicted life span -----------------------------------
st.subheader("Which breeds have the longest predicted life span?")

top10 = df.dropna(subset=["life_span_avg_years"]).nlargest(10, "life_span_avg_years")

chart1 = (
    alt.Chart(top10)
    .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
    .encode(
        x=alt.X("life_span_avg_years:Q", title="Average predicted life span (years)"),
        y=alt.Y("name:N", sort="-x", title=None),
        color=alt.Color(
            "size_class:N",
            sort=SIZE_ORDER,
            scale=alt.Scale(domain=SIZE_ORDER, range=SIZE_COLORS),
            legend=alt.Legend(title="Size class"),
        ),
        tooltip=[
            alt.Tooltip("name:N", title="Breed"),
            alt.Tooltip("life_span_avg_years:Q", title="Avg life span (yrs)"),
            alt.Tooltip("weight_avg_kg:Q", title="Avg weight (kg)"),
            alt.Tooltip("size_class:N", title="Size class"),
        ],
    )
    .properties(height=380)
)
st.altair_chart(chart1, use_container_width=True)

longest = top10.iloc[0]
overall_avg = df["life_span_avg_years"].mean()
top10_size_mix = top10["size_class"].value_counts().reindex(SIZE_ORDER).fillna(0).astype(int)
size_mix_text = ", ".join(f"{count} {size}" for size, count in top10_size_mix.items() if count > 0)
st.markdown(
    f"**{longest['name']}** tops the list at an average predicted life span of "
    f"**{longest['life_span_avg_years']:.1f} years**, against an overall average across "
    f"all {df['life_span_avg_years'].notna().sum()} breeds with life span data of "
    f"**{overall_avg:.1f} years**. The color coding shows size class doesn't cleanly "
    f"predict a spot in this top 10 — the mix is {size_mix_text}, so being small isn't a "
    "requirement for a long predicted life span in this dataset."
)

st.divider()

# --- Chart 2: weight class distribution --------------------------------------
st.subheader("How are breeds distributed across weight classes?")

size_counts = (
    df["size_class"]
    .value_counts()
    .reindex(SIZE_ORDER)
    .fillna(0)
    .astype(int)
    .rename_axis("size_class")
    .reset_index(name="count")
)

chart2 = (
    alt.Chart(size_counts)
    .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
    .encode(
        x=alt.X("size_class:N", sort=SIZE_ORDER, title="Size class"),
        y=alt.Y("count:Q", title="Number of breeds"),
        color=alt.Color(
            "size_class:N",
            sort=SIZE_ORDER,
            scale=alt.Scale(domain=SIZE_ORDER, range=SIZE_COLORS),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("size_class:N", title="Size class"),
            alt.Tooltip("count:Q", title="Breeds"),
        ],
    )
    .properties(height=380)
)
st.altair_chart(chart2, use_container_width=True)

biggest_class = size_counts.loc[size_counts["count"].idxmax()]
share = biggest_class["count"] / size_counts["count"].sum() * 100
st.markdown(
    f"**{biggest_class['size_class']}** breeds (avg weight "
    f"{'< 10kg' if biggest_class['size_class'] == 'Small' else '10-25kg' if biggest_class['size_class'] == 'Medium' else '25kg+'}) "
    f"are the most common group, making up **{share:.0f}%** of all breeds in the dataset. "
    "Size classes are derived from each breed's average weight (midpoint of its min/max "
    "range), split at 10kg and 25kg thresholds."
)
