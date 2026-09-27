import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Sales Overview", page_icon="📊", layout="wide")

st.title("Sales Overview")
st.caption("売上の全体像をひと目で把握するためのダッシュボードです。")

NOT_SOLD_STATUSES = ["Cancelled", "Returned"]


@st.cache_data
def load_data():
    orders = pd.read_csv("sample_data/orders.csv", parse_dates=["created_at"])
    users = pd.read_csv("sample_data/users.csv", parse_dates=["created_at"])
    return orders, users


try:
    orders, users = load_data()
except FileNotFoundError as e:
    st.error(f"データの読み込みに失敗しました: {e}")
    st.stop()

orders = orders.merge(users[["id", "country"]], left_on="user_id", right_on="id", how="left").drop(
    columns=["id"]
)

# --- サイドバー: ページ全体に効く絞り込みフィルター ---
st.sidebar.header("絞り込み条件")

min_date = orders["created_at"].min().date()
max_date = orders["created_at"].max().date()
date_range = st.sidebar.date_input(
    "分析期間（注文日）",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

all_categories = sorted(orders["category"].unique())
selected_categories = st.sidebar.multiselect("商品カテゴリ", options=all_categories, default=all_categories)

all_countries = sorted(orders["country"].dropna().unique())
selected_countries = st.sidebar.multiselect("ユーザーの居住国", options=all_countries, default=all_countries)

orders_filtered = orders[
    (orders["created_at"].dt.date >= start_date)
    & (orders["created_at"].dt.date <= end_date)
    & (orders["category"].isin(selected_categories))
    & (orders["country"].isin(selected_countries))
]

if orders_filtered.empty:
    st.info("選択した条件に一致するデータがありません。サイドバーのフィルター条件を変更してください。")
    st.stop()

orders_valid = orders_filtered[~orders_filtered["status"].isin(NOT_SOLD_STATUSES)]

# 月別集計（KPIのdelta計算・月別トレンドの両方で使う）
orders_m = orders_filtered.assign(month=orders_filtered["created_at"].dt.to_period("M"))
valid_m = orders_m[~orders_m["status"].isin(NOT_SOLD_STATUSES)]

monthly_valid = valid_m.groupby("month").agg(
    sales=("sale_price", "sum"),
    order_count=("order_id", "count"),
)
monthly_valid["aov"] = monthly_valid["sales"] / monthly_valid["order_count"]

monthly_all = orders_m.groupby("month").agg(
    total_count=("order_id", "count"),
    cancelled_count=("status", lambda s: (s == "Cancelled").sum()),
)
monthly_all["cancel_rate"] = monthly_all["cancelled_count"] / monthly_all["total_count"]

months = sorted(monthly_all.index)
latest_month = months[-1]
prev_month = months[-2] if len(months) > 1 else None


def rate_change(current, previous):
    if previous is None or pd.isna(previous) or previous == 0:
        return None
    return (current - previous) / previous


def point_change(current, previous):
    if previous is None or pd.isna(previous):
        return None
    return current - previous


latest_sales = monthly_valid["sales"].get(latest_month, 0.0)
latest_orders = monthly_valid["order_count"].get(latest_month, 0)
latest_aov = monthly_valid["aov"].get(latest_month, 0.0)
latest_cancel_rate = monthly_all["cancel_rate"].get(latest_month, 0.0)

prev_sales = monthly_valid["sales"].get(prev_month) if prev_month is not None else None
prev_orders = monthly_valid["order_count"].get(prev_month) if prev_month is not None else None
prev_aov = monthly_valid["aov"].get(prev_month) if prev_month is not None else None
prev_cancel_rate = monthly_all["cancel_rate"].get(prev_month) if prev_month is not None else None

sales_delta = rate_change(latest_sales, prev_sales)
orders_delta = rate_change(latest_orders, prev_orders)
aov_delta = rate_change(latest_aov, prev_aov)
cancel_rate_delta = point_change(latest_cancel_rate, prev_cancel_rate)

st.caption(f"KPIは直近月（{latest_month.strftime('%Y年%m月')}）の実績、deltaは前月比です。")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric(
    "売上",
    f"${latest_sales:,.0f}",
    delta=f"{sales_delta:+.1%}" if sales_delta is not None else None,
)
kpi2.metric(
    "注文数",
    f"{latest_orders:,}",
    delta=f"{orders_delta:+.1%}" if orders_delta is not None else None,
)
kpi3.metric(
    "平均注文単価",
    f"${latest_aov:,.2f}",
    delta=f"{aov_delta:+.1%}" if aov_delta is not None else None,
)
kpi4.metric(
    "キャンセル率",
    f"{latest_cancel_rate:.1%}",
    delta=f"{cancel_rate_delta * 100:+.1f}pt" if cancel_rate_delta is not None else None,
    delta_color="inverse",
)

st.divider()

col_trend, col_category = st.columns([2, 1])

TREND_METRIC_OPTIONS = ["売上", "注文数", "販売数量"]
TREND_METRIC_COL = {"売上": "sales", "注文数": "order_count", "販売数量": "quantity"}
TREND_METRIC_LABEL = {"売上": "売上 (USD)", "注文数": "注文数", "販売数量": "販売数量"}

TREND_GRANULARITY_OPTIONS = ["日", "週", "月"]
TREND_GRANULARITY_FREQ = {"日": "D", "週": "W", "月": "M"}
TREND_GRANULARITY_LABEL = {"日": "日付", "週": "週", "月": "月"}

with col_trend:
    with st.container(border=True):
        st.subheader("売上の推移")

        control_metric, control_granularity = st.columns(2)
        with control_metric:
            trend_metric = (
                st.segmented_control(
                    "表示する指標",
                    options=TREND_METRIC_OPTIONS,
                    default="売上",
                    key="trend_metric",
                )
                or "売上"
            )
        with control_granularity:
            trend_granularity = (
                st.segmented_control(
                    "集計の粒度",
                    options=TREND_GRANULARITY_OPTIONS,
                    default="月",
                    key="trend_granularity",
                )
                or "月"
            )

        freq = TREND_GRANULARITY_FREQ[trend_granularity]
        trend_source = orders_valid.assign(
            period=orders_valid["created_at"].dt.to_period(freq).dt.start_time
        )
        trend_data = trend_source.groupby(["period", "category"], as_index=False).agg(
            sales=("sale_price", "sum"),
            order_count=("order_id", "count"),
            quantity=("quantity", "sum"),
        )

        if trend_data.empty:
            st.info("表示するデータがありません。")
        else:
            metric_col = TREND_METRIC_COL[trend_metric]
            metric_label = TREND_METRIC_LABEL[trend_metric]
            value_format = "$%{y:,.0f}" if trend_metric == "売上" else "%{y:,.0f}"

            fig_trend = px.line(
                trend_data,
                x="period",
                y=metric_col,
                color="category",
                markers=True,
            )
            fig_trend.update_traces(
                hovertemplate=f"%{{x}}<br>%{{fullData.name}}: {value_format}<extra></extra>"
            )
            fig_trend.update_layout(
                xaxis_title=TREND_GRANULARITY_LABEL[trend_granularity],
                yaxis_title=metric_label,
                legend_title_text="カテゴリ",
                hovermode="x unified",
            )
            fig_trend.update_xaxes(rangeslider_visible=True)
            st.plotly_chart(fig_trend, use_container_width=True)

with col_category:
    with st.container(border=True):
        st.subheader("カテゴリ別売上構成比")
        category_sales = (
            orders_valid.groupby("category", as_index=False)["sale_price"]
            .sum()
            .sort_values("sale_price", ascending=False)
        )
        fig_donut = px.pie(
            category_sales,
            names="category",
            values="sale_price",
            hole=0.5,
        )
        fig_donut.update_traces(hovertemplate="カテゴリ: %{label}<br>売上: $%{value:,.0f}<extra></extra>")
        st.plotly_chart(fig_donut, use_container_width=True)

st.divider()

tab_category, tab_customer, tab_detail = st.tabs(["カテゴリ・商品", "顧客", "明細データ"])

with tab_category:
    with st.container(border=True):
        st.subheader("カテゴリ別売上")
        category_sales_bar = (
            orders_valid.groupby("category", as_index=False)["sale_price"]
            .sum()
            .sort_values("sale_price", ascending=True)
        )
        fig_category_bar = px.bar(
            category_sales_bar,
            x="sale_price",
            y="category",
            orientation="h",
        )
        fig_category_bar.update_traces(hovertemplate="カテゴリ: %{y}<br>売上: $%{x:,.0f}<extra></extra>")
        fig_category_bar.update_layout(xaxis_title="売上 (USD)", yaxis_title="カテゴリ")
        category_event = st.plotly_chart(
            fig_category_bar,
            use_container_width=True,
            on_select="rerun",
            selection_mode="points",
            key="category_bar_chart",
        )

        category_points = category_event["selection"]["points"] if category_event else []
        selected_category = category_points[0]["y"] if category_points else None
        category_scope_label = selected_category or "全カテゴリ"

        if selected_category:
            scope_orders = orders_valid[orders_valid["category"] == selected_category]
        else:
            scope_orders = orders_valid

        st.caption(f"選択中のカテゴリ: {category_scope_label}（棒をクリックすると絞り込めます）")

    with st.container(border=True):
        st.subheader(f"商品別売上ランキング（{category_scope_label}）")

        if scope_orders.empty:
            st.info("表示するデータがありません。")
        else:
            product_sales_bar = (
                scope_orders.groupby("product_name", as_index=False)["sale_price"]
                .sum()
                .sort_values("sale_price", ascending=True)
            )
            fig_product_bar = px.bar(
                product_sales_bar,
                x="sale_price",
                y="product_name",
                orientation="h",
            )
            fig_product_bar.update_traces(hovertemplate="商品: %{y}<br>売上: $%{x:,.0f}<extra></extra>")
            fig_product_bar.update_layout(xaxis_title="売上 (USD)", yaxis_title="商品")
            st.plotly_chart(fig_product_bar, use_container_width=True)

        st.subheader(f"商品一覧（{category_scope_label}）")

        product_table = (
            scope_orders.groupby(["product_name", "category"], as_index=False)
            .agg(
                sales=("sale_price", "sum"),
                quantity=("quantity", "sum"),
                order_count=("order_id", "count"),
            )
            .sort_values("sales", ascending=False)
            .reset_index(drop=True)
        )

        product_event = st.dataframe(
            product_table,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="product_table",
            column_config={
                "product_name": "商品名",
                "category": "カテゴリ",
                "sales": st.column_config.NumberColumn("売上", format="$%,.0f"),
                "quantity": st.column_config.NumberColumn("販売数量", format="%,d"),
                "order_count": st.column_config.NumberColumn("注文数", format="%,d"),
            },
        )

        selected_rows = product_event["selection"]["rows"] if product_event else []
        selected_product = (
            product_table.iloc[selected_rows[0]]["product_name"] if selected_rows else None
        )

    with st.container(border=True):
        if selected_product is None:
            st.subheader("商品詳細")
            st.caption("上の商品一覧テーブルから行を選択すると、詳細が表示されます。")
        else:
            st.subheader(f"商品詳細: {selected_product}")
            product_orders = scope_orders[scope_orders["product_name"] == selected_product]

            col_qty, col_age = st.columns(2)
            with col_qty:
                st.markdown("##### 月別販売数量の推移")
                monthly_qty = (
                    product_orders.assign(
                        month=product_orders["created_at"].dt.to_period("M").dt.to_timestamp()
                    )
                    .groupby("month", as_index=False)["quantity"]
                    .sum()
                )
                fig_qty = px.line(monthly_qty, x="month", y="quantity", markers=True)
                fig_qty.update_traces(
                    hovertemplate="月: %{x|%Y-%m}<br>販売数量: %{y:,}<extra></extra>"
                )
                fig_qty.update_layout(xaxis_title="月", yaxis_title="販売数量")
                st.plotly_chart(fig_qty, use_container_width=True)

            with col_age:
                st.markdown("##### 購入者の年齢分布")
                buyer_ages = product_orders.merge(
                    users[["id", "age"]], left_on="user_id", right_on="id", how="left"
                )["age"].dropna()
                if buyer_ages.empty:
                    st.info("年齢データがありません。")
                else:
                    fig_age = px.histogram(buyer_ages.to_frame(), x="age")
                    fig_age.update_traces(hovertemplate="年齢: %{x}<br>購入者数: %{y}<extra></extra>")
                    fig_age.update_layout(xaxis_title="年齢", yaxis_title="購入者数")
                    st.plotly_chart(fig_age, use_container_width=True)

with tab_customer:
    with st.container(border=True):
        st.subheader("居住国別売上")
        country_sales = orders_valid.groupby("country", as_index=False)["sale_price"].sum()
        fig_map = px.choropleth(
            country_sales,
            locations="country",
            locationmode="country names",
            color="sale_price",
            color_continuous_scale="Blues",
            hover_name="country",
        )
        fig_map.update_traces(hovertemplate="%{hovertext}<br>売上: $%{z:,.0f}<extra></extra>")
        fig_map.update_layout(coloraxis_colorbar_title="売上 (USD)")
        st.plotly_chart(fig_map, use_container_width=True)

with tab_detail:
    with st.container(border=True):
        st.subheader("注文明細データ")
        st.dataframe(
            orders_filtered.sort_values("created_at", ascending=False),
            use_container_width=True,
        )
