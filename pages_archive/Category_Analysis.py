import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="カテゴリ別売上分析", page_icon="🗂️", layout="wide")

st.title("カテゴリ別売上分析")
st.caption("商品カテゴリごとの売上を分析します。左のサイドバーで絞り込み条件を変更できます。")


@st.cache_data
def load_orders():
    return pd.read_csv("sample_data/orders.csv", parse_dates=["created_at", "shipped_at"])


orders = load_orders()

st.sidebar.header("絞り込み条件")

min_date = orders["created_at"].min().date()
max_date = orders["created_at"].max().date()
date_range = st.sidebar.date_input(
    "分析対象期間（注文日）",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

category_options = sorted(orders["category"].unique())
selected_categories = st.sidebar.multiselect(
    "商品カテゴリ", options=category_options, default=category_options
)

price_options = sorted(orders["sale_price"].unique())
price_min, price_max = st.sidebar.select_slider(
    "販売価格 (sale_price) の範囲",
    options=price_options,
    value=(price_options[0], price_options[-1]),
)

status_choice = st.sidebar.radio(
    "注文ステータス", options=["すべて", "Completeのみ", "Cancelledのみ"], index=0
)

filtered_orders = orders[
    (orders["created_at"].dt.date >= start_date)
    & (orders["created_at"].dt.date <= end_date)
    & (orders["category"].isin(selected_categories))
    & (orders["sale_price"] >= price_min)
    & (orders["sale_price"] <= price_max)
]
if status_choice == "Completeのみ":
    filtered_orders = filtered_orders[filtered_orders["status"] == "Complete"]
elif status_choice == "Cancelledのみ":
    filtered_orders = filtered_orders[filtered_orders["status"] == "Cancelled"]

if filtered_orders.empty:
    st.warning("絞り込み条件に一致する注文がありません。条件を変更してください。")
    st.stop()

total_sales = filtered_orders["sale_price"].sum()
order_count = len(filtered_orders)
avg_order_value = filtered_orders["sale_price"].mean()

col1, col2, col3 = st.columns(3)
col1.metric("売上合計", f"${total_sales:,.0f}")
col2.metric("注文数", f"{order_count:,}")
col3.metric("平均注文単価", f"${avg_order_value:,.0f}")

st.divider()
st.header("カテゴリ別売上")

category_summary = filtered_orders.groupby("category", as_index=False).agg(
    total_sales=("sale_price", "sum"), order_count=("order_id", "count")
)
category_summary = category_summary.sort_values("total_sales", ascending=False)

fig_category = px.bar(
    category_summary,
    x="category",
    y="total_sales",
    custom_data=["order_count"],
    title="カテゴリ別売上",
)
fig_category.update_traces(
    hovertemplate=(
        "カテゴリ: %{x}<br>売上: $%{y:,.0f}<br>注文数: %{customdata[0]:,}件<extra></extra>"
    )
)
fig_category.update_layout(xaxis_title="カテゴリ", yaxis_title="売上 (USD)")
st.plotly_chart(fig_category, use_container_width=True)

st.divider()
st.header("カテゴリ別集計テーブル")

category_table = category_summary.copy()
category_table["avg_order_value"] = category_table["total_sales"] / category_table["order_count"]
category_table["sales_share"] = category_table["total_sales"] / total_sales * 100

st.dataframe(
    category_table.rename(
        columns={
            "category": "カテゴリ",
            "total_sales": "売上合計 (USD)",
            "order_count": "注文数",
            "avg_order_value": "平均注文単価 (USD)",
            "sales_share": "売上構成比 (%)",
        }
    ),
    use_container_width=True,
    hide_index=True,
    column_config={
        "売上合計 (USD)": st.column_config.NumberColumn(format="$%.0f"),
        "平均注文単価 (USD)": st.column_config.NumberColumn(format="$%.0f"),
        "売上構成比 (%)": st.column_config.NumberColumn(format="%.1f%%"),
    },
)
