import altair as alt
import duckdb
import streamlit as st

DB_PATH = "dog_breeds.duckdb"

SIZE_ORDER = ["Small", "Medium", "Large"]
SIZE_COLORS = ["#86b6ef", "#2a78d6", "#104281"]  # ordinal ramp, light -> dark


@st.cache_data
def load_breeds():
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("select * from mart_dog_breeds").df()
    con.close()
    return df


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

# --- Chart 1: longest predicted life span -----------------------------------
st.subheader("Which breeds have the longest predicted life span?")

top10 = df.dropna(subset=["life_span_avg_years"]).nlargest(10, "life_span_avg_years")

chart1 = (
    alt.Chart(top10)
    .mark_bar(color="#2a78d6", cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
    .encode(
        x=alt.X("life_span_avg_years:Q", title="Average predicted life span (years)"),
        y=alt.Y("name:N", sort="-x", title=None),
        tooltip=[
            alt.Tooltip("name:N", title="Breed"),
            alt.Tooltip("life_span_avg_years:Q", title="Avg life span (yrs)"),
            alt.Tooltip("weight_avg_kg:Q", title="Avg weight (kg)"),
        ],
    )
    .properties(height=380)
)
st.altair_chart(chart1, use_container_width=True)

longest = top10.iloc[0]
overall_avg = df["life_span_avg_years"].mean()
st.markdown(
    f"**{longest['name']}** tops the list at an average predicted life span of "
    f"**{longest['life_span_avg_years']:.1f} years**, against an overall average across "
    f"all {df['life_span_avg_years'].notna().sum()} breeds with life span data of "
    f"**{overall_avg:.1f} years**. The top 10 skews toward small/toy breeds, consistent "
    "with the well-documented inverse relationship between body size and canine longevity."
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
