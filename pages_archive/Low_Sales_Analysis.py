import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="カテゴリ内 売上下位商品分析", page_icon="📉", layout="wide")

st.title("カテゴリ内 売上下位商品分析")
st.caption(
    "各カテゴリ内で販売数量（個数）が少ない商品を特定する分析です。"
    "`notebooks/eda_low_sales.ipynb` で行った分析をStreamlitページとして実装しています。"
)


@st.cache_data
def load_orders():
    return pd.read_csv("sample_data/orders.csv", parse_dates=["created_at", "shipped_at"])


orders = load_orders()

st.subheader("キャンセル・返品の扱い")
st.markdown(
    '- `status = "Cancelled"`（取引未成立）の注文は、販売数量の集計から**常に除外**します。\n'
    '- `status = "Returned"`（返品）の注文は、実質的に売上・販売数量に結びついていないため、'
    "デフォルトでは除外しますが、下のチェックボックスで含めることもできます。"
)

include_returned = st.checkbox("返品(Returned)された注文も販売数量に含める", value=False)

excluded_statuses = ["Cancelled"] if include_returned else ["Cancelled", "Returned"]
orders_for_analysis = orders[~orders["status"].isin(excluded_statuses)]

st.caption(
    f"分析対象: 全{len(orders):,}件中 {len(orders_for_analysis):,}件 "
    f"（除外ステータス: {', '.join(excluded_statuses)}）"
)

product_summary = orders_for_analysis.groupby(
    ["product_id", "product_name", "category"], as_index=False
).agg(total_quantity=("quantity", "sum"), total_sales=("sale_price", "sum"))

product_summary["category_size"] = product_summary.groupby("category")["product_id"].transform(
    "count"
)
product_summary["rank_in_category"] = product_summary.groupby("category")["total_quantity"].rank(
    method="min", ascending=True
)
product_summary["percentile_in_category"] = product_summary.groupby("category")[
    "total_quantity"
].rank(pct=True, ascending=True)

st.divider()
st.header("カテゴリ内 販売数量下位商品")

bottom_pct = st.slider("カテゴリ内の下位何%を表示するか", min_value=5, max_value=50, value=20, step=5)

product_summary["category_threshold"] = product_summary.groupby("category")[
    "total_quantity"
].transform(lambda s: s.quantile(bottom_pct / 100))
bottom_products = product_summary[
    product_summary["total_quantity"] <= product_summary["category_threshold"]
].sort_values(["category", "total_quantity"])

st.caption(
    "カテゴリあたりの商品数が少ない場合、下位◯%は実質的にカテゴリ内で最も販売数量が少ない商品のみを"
    "指すことがあります（下表の「カテゴリ商品数」を参照）。"
)

st.dataframe(
    bottom_products.rename(
        columns={
            "category": "カテゴリ",
            "product_name": "商品名",
            "total_quantity": "販売数量",
            "total_sales": "売上 (USD)",
            "rank_in_category": "カテゴリ内順位",
            "category_size": "カテゴリ商品数",
            "percentile_in_category": "カテゴリ内パーセンタイル",
        }
    )[
        [
            "カテゴリ",
            "商品名",
            "販売数量",
            "売上 (USD)",
            "カテゴリ内順位",
            "カテゴリ商品数",
            "カテゴリ内パーセンタイル",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

fig_bottom = px.bar(
    bottom_products.sort_values("total_quantity"),
    x="total_quantity",
    y="product_name",
    color="category",
    orientation="h",
    title=f"カテゴリ内下位{bottom_pct}%の商品（販売数量）",
)
fig_bottom.update_layout(xaxis_title="販売数量", yaxis_title="商品名")
st.plotly_chart(fig_bottom, use_container_width=True)

st.divider()
st.header("カテゴリ内 全商品の販売数量比較（参考）")

selected_category = st.selectbox(
    "カテゴリを選択", options=sorted(product_summary["category"].unique())
)
category_products = product_summary[
    product_summary["category"] == selected_category
].sort_values("total_quantity")

fig_category = px.bar(
    category_products,
    x="total_quantity",
    y="product_name",
    orientation="h",
    title=f"{selected_category} カテゴリ内の販売数量",
)
fig_category.update_layout(xaxis_title="販売数量", yaxis_title="商品名")
st.plotly_chart(fig_category, use_container_width=True)
