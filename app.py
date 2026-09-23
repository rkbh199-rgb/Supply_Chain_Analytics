# =============================================================================
# app.py
# DataCo SMART Supply Chain Performance & Analytics Dashboard
#
# Run:  streamlit run app.py
#
# All KPIs and charts are computed from analysis.py functions so that they
# automatically update when sidebar filters change.
# =============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Import our single source of truth
import analysis as an

# ---------------------------------------------------------------------------
# Page config (must be the very first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="DataCo Supply Chain Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Helper — format large numbers nicely
# ---------------------------------------------------------------------------
def fmt_currency(value: float) -> str:
    """Format a number as a compact dollar amount, e.g. $36.8M."""
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:.2f}"


def fmt_number(value: float) -> str:
    """Format a plain number with commas."""
    return f"{int(value):,}"


# ---------------------------------------------------------------------------
# Data loading — cached so the CSV is only read once
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading and preparing data …")
def get_data():
    """Load, clean, and feature-engineer the dataset. Returns (df, clean_summary)."""
    return an.load_and_prepare()


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
df_full, clean_summary = get_data()

# ---------------------------------------------------------------------------
# Sidebar — filters
# ---------------------------------------------------------------------------
st.sidebar.title("🔍 Filters")
st.sidebar.markdown("Use the filters below to explore a subset of the data.")

# Helper: sorted unique values with an "All" option
def sidebar_multiselect(label, column, df):
    options = sorted(df[column].dropna().unique().tolist())
    return st.sidebar.multiselect(label, options=options, default=[])

# Year (single select via slider or multiselect)
years = sorted(df_full["Order Year"].dropna().unique().tolist())
selected_years = st.sidebar.multiselect("📅 Year", options=years, default=[])

# Market
selected_markets = sidebar_multiselect("🌍 Market", "Market", df_full)

# Order Region
selected_regions = sidebar_multiselect("📍 Order Region", "Order Region", df_full)

# Customer Segment
selected_segments = sidebar_multiselect("👥 Customer Segment", "Customer Segment", df_full)

# Department Name (acts as broad product category)
selected_departments = sidebar_multiselect("🏪 Department", "Department Name", df_full)

# Shipping Mode
selected_shipping = sidebar_multiselect("🚚 Shipping Mode", "Shipping Mode", df_full)

# Order Status
selected_order_status = sidebar_multiselect("📋 Order Status", "Order Status", df_full)

# Delivery Status
selected_delivery = sidebar_multiselect("📬 Delivery Status", "Delivery Status", df_full)

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------
df = df_full.copy()

if selected_years:
    df = df[df["Order Year"].isin(selected_years)]
if selected_markets:
    df = df[df["Market"].isin(selected_markets)]
if selected_regions:
    df = df[df["Order Region"].isin(selected_regions)]
if selected_segments:
    df = df[df["Customer Segment"].isin(selected_segments)]
if selected_departments:
    df = df[df["Department Name"].isin(selected_departments)]
if selected_shipping:
    df = df[df["Shipping Mode"].isin(selected_shipping)]
if selected_order_status:
    df = df[df["Order Status"].isin(selected_order_status)]
if selected_delivery:
    df = df[df["Delivery Status"].isin(selected_delivery)]

# Sidebar stats
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Filtered rows:** {len(df):,} / {len(df_full):,}")
st.sidebar.markdown(f"**({len(df)/len(df_full)*100:.1f}% of total)**")

# ---------------------------------------------------------------------------
# Main header
# ---------------------------------------------------------------------------
st.title("📦 DataCo SMART Supply Chain Performance & Analytics Dashboard")
st.markdown(
    "*Interactive analysis of sales, profitability, customers, products, "
    "shipping and delivery performance.*"
)
st.markdown("---")

# Guard against empty filtered result
if df.empty:
    st.warning(
        "⚠️ No data matches the current filter selection. "
        "Please adjust the sidebar filters."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Compute all analytics on the filtered DataFrame
# ---------------------------------------------------------------------------
kpis          = an.get_kpis(df)
sales_data    = an.sales_analysis(df)
profit_data   = an.profit_analysis(df)
customer_data = an.customer_analysis(df)
product_data  = an.product_analysis(df)
ship_data     = an.shipping_analysis(df)
deliver_data  = an.delivery_analysis(df)
geo_data      = an.geo_analysis(df)
insights      = an.generate_insights(df)
recommendations = an.generate_recommendations(df)

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
tabs = st.tabs([
    "📊 Executive Overview",
    "💰 Sales & Profitability",
    "👥 Customer Analytics",
    "📦 Product Analytics",
    "🚚 Shipping & Delivery",
    "🌍 Geographic Performance",
    "💡 Key Insights",
    "✅ Recommendations",
    "🔎 Data Explorer",
])

# ────────────────────────────────────────────────────────────────────────────
# TAB 1 — Executive Overview
# ────────────────────────────────────────────────────────────────────────────
with tabs[0]:
    st.header("Executive Overview")

    # KPI Cards — top row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Revenue",       fmt_currency(kpis["total_sales"]))
    c2.metric("Total Profit",        fmt_currency(kpis["total_profit"]))
    c3.metric("Profit Margin",       f"{kpis['overall_profit_margin']:.1f}%")
    c4.metric("Total Orders",        fmt_number(kpis["total_orders"]))
    c5.metric("Total Customers",     fmt_number(kpis["total_customers"]))

    c6, c7, c8, c9, c10 = st.columns(5)
    c6.metric("Avg Order Value",     fmt_currency(kpis["avg_order_value"]))
    c7.metric("Avg Profit / Order",  fmt_currency(kpis["avg_profit_per_order"]))
    c8.metric("Late Delivery Rate",  f"{kpis['late_delivery_rate']:.1f}%")
    c9.metric("Avg Discount Rate",   f"{kpis['avg_discount_rate']:.1f}%")
    c10.metric("Order Items",        fmt_number(kpis["total_order_items"]))

    st.markdown("---")

    col_left, col_right = st.columns(2)

    # Monthly sales trend
    with col_left:
        fig = px.line(
            sales_data["monthly_trend"],
            x="Order YearMonth", y="Total Sales",
            title="Monthly Revenue Trend",
            markers=True,
            color_discrete_sequence=["#3b82f6"],
        )
        fig.update_layout(xaxis_tickangle=-45, height=350)
        st.plotly_chart(fig, use_container_width=True)

    # Monthly profit trend
    with col_right:
        monthly_profit = profit_data["monthly_trend"]
        fig = px.line(
            monthly_profit,
            x="Order YearMonth", y="Total Profit",
            title="Monthly Profit Trend",
            markers=True,
            color_discrete_sequence=["#10b981"],
        )
        fig.update_layout(xaxis_tickangle=-45, height=350)
        st.plotly_chart(fig, use_container_width=True)

    # Sales by market + delivery status pie
    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.bar(
            geo_data["sales_by_market"],
            x="Market", y="Total Sales",
            title="Revenue by Market",
            color="Market",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        fig = px.pie(
            deliver_data["status_counts"],
            names="Delivery Status", values="Count",
            title="Delivery Status Distribution",
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

# ────────────────────────────────────────────────────────────────────────────
# TAB 2 — Sales & Profitability
# ────────────────────────────────────────────────────────────────────────────
with tabs[1]:
    st.header("Sales & Profitability Analysis")

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            profit_data["by_market"].sort_values("Total Profit", ascending=True),
            x="Total Profit", y="Market", orientation="h",
            title="Profit by Market",
            color="Total Profit",
            color_continuous_scale="RdYlGn",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            profit_data["by_department"].head(10),
            x="Total Profit", y="Department Name", orientation="h",
            title="Profit by Department (Top 10)",
            color="Total Profit",
            color_continuous_scale="Blues",
        )
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        # Sales vs Profit by category (bubble chart)
        cat_df = (
            df.groupby("Category Name")
              .agg(Total_Sales=("Sales","sum"),
                   Total_Profit=("Order Profit Per Order","sum"),
                   Count=("Order Id","count"))
              .reset_index()
        )
        fig = px.scatter(
            cat_df,
            x="Total_Sales", y="Total_Profit",
            size="Count", hover_name="Category Name",
            title="Sales vs Profit by Category",
            color="Total_Profit",
            color_continuous_scale="RdYlGn",
            labels={"Total_Sales": "Total Sales ($)", "Total_Profit": "Total Profit ($)"},
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        fig = px.bar(
            profit_data["margin_by_market"],
            x="Market", y="Avg Profit Margin (%)",
            title="Average Profit Margin by Market (%)",
            color="Market",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Yearly comparison
    yearly = sales_data["yearly_trend"].merge(
        profit_data["yearly_trend"], on="Order Year"
    )
    fig = go.Figure()
    fig.add_trace(go.Bar(x=yearly["Order Year"].astype(str), y=yearly["Total Sales"], name="Sales", marker_color="#3b82f6"))
    fig.add_trace(go.Bar(x=yearly["Order Year"].astype(str), y=yearly["Total Profit"], name="Profit", marker_color="#10b981"))
    fig.update_layout(barmode="group", title="Yearly Sales vs Profit Comparison", height=350)
    st.plotly_chart(fig, use_container_width=True)

# ────────────────────────────────────────────────────────────────────────────
# TAB 3 — Customer Analytics
# ────────────────────────────────────────────────────────────────────────────
with tabs[2]:
    st.header("Customer Analytics")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(
            customer_data["segment_counts"],
            names="Customer Segment", values="Order Items",
            title="Order Items by Customer Segment",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            customer_data["sales_by_segment"],
            x="Customer Segment", y="Total Sales",
            title="Revenue by Customer Segment",
            color="Customer Segment",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        fig = px.bar(
            customer_data["profit_by_segment"],
            x="Customer Segment", y="Total Profit",
            title="Profit by Customer Segment",
            color="Customer Segment",
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        fig = px.bar(
            customer_data["payment_type_counts"],
            x="Type", y="Count",
            title="Order Count by Payment Type",
            color="Type",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Top 20 customers
    st.subheader("Top 20 Customers by Revenue")
    top_c = customer_data["top_customers"]
    fig = px.bar(
        top_c,
        x="Customer Name", y="Total Sales",
        title="Top 20 Customers",
        color="Total Sales",
        color_continuous_scale="Blues",
    )
    fig.update_layout(xaxis_tickangle=-45, height=400)
    st.plotly_chart(fig, use_container_width=True)

# ────────────────────────────────────────────────────────────────────────────
# TAB 4 — Product Analytics
# ────────────────────────────────────────────────────────────────────────────
with tabs[3]:
    st.header("Product Analytics")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            product_data["sales_by_category"].head(15),
            x="Total Sales", y="Category Name", orientation="h",
            title="Top 15 Categories by Revenue",
            color="Total Sales", color_continuous_scale="Blues",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            product_data["sales_by_department"],
            x="Total Sales", y="Department Name", orientation="h",
            title="Revenue by Department",
            color="Total Sales", color_continuous_scale="Teal",
        )
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        fig = px.bar(
            product_data["top_products_by_sales"],
            x="Total Sales", y="Product Name", orientation="h",
            title="Top 15 Products by Revenue",
            color="Total Sales", color_continuous_scale="Purples",
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        fig = px.bar(
            product_data["top_products_by_profit"],
            x="Total Profit", y="Product Name", orientation="h",
            title="Top 15 Products by Profit",
            color="Total Profit", color_continuous_scale="RdYlGn",
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

    # Profit margin by category (top 20)
    st.subheader("Average Profit Margin by Category (%)")
    margin_cat = product_data["category_profit_margin"].head(20)
    fig = px.bar(
        margin_cat,
        x="Avg Profit Margin (%)", y="Category Name", orientation="h",
        color="Avg Profit Margin (%)", color_continuous_scale="RdYlGn",
    )
    fig.update_layout(height=550)
    st.plotly_chart(fig, use_container_width=True)

# ────────────────────────────────────────────────────────────────────────────
# TAB 5 — Shipping & Delivery
# ────────────────────────────────────────────────────────────────────────────
with tabs[4]:
    st.header("Shipping & Delivery Analysis")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(
            ship_data["mode_counts"],
            names="Shipping Mode", values="Order Items",
            title="Order Items by Shipping Mode",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            ship_data["mode_late_rate"].sort_values("Late Rate (%)", ascending=True),
            x="Late Rate (%)", y="Shipping Mode", orientation="h",
            title="Late Delivery Rate by Shipping Mode (%)",
            color="Late Rate (%)", color_continuous_scale="Reds",
        )
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        fig = px.bar(
            ship_data["mode_avg_delay"].sort_values("Avg Delay Days", ascending=True),
            x="Avg Delay Days", y="Shipping Mode", orientation="h",
            title="Average Shipping Delay by Mode (Days)",
            color="Avg Delay Days", color_continuous_scale="Oranges",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        fig = px.bar(
            deliver_data["order_status_counts"],
            x="Order Status", y="Count",
            title="Order Status Distribution",
            color="Order Status",
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    # Late delivery rate by region
    st.subheader("Late Delivery Rate by Region (%)")
    fig = px.bar(
        deliver_data["late_by_region"].head(15),
        x="Late Rate (%)", y="Order Region", orientation="h",
        color="Late Rate (%)", color_continuous_scale="RdYlGn_r",
    )
    fig.update_layout(height=450)
    st.plotly_chart(fig, use_container_width=True)

    # Year-over-year late rate
    if "Order Year" in df.columns and deliver_data["late_by_year"].shape[0] > 0:
        st.subheader("Late Delivery Rate Trend by Year")
        fig = px.line(
            deliver_data["late_by_year"],
            x="Order Year", y="Late Rate (%)",
            markers=True, color_discrete_sequence=["#ef4444"],
        )
        st.plotly_chart(fig, use_container_width=True)

# ────────────────────────────────────────────────────────────────────────────
# TAB 6 — Geographic Performance
# ────────────────────────────────────────────────────────────────────────────
with tabs[5]:
    st.header("Geographic Performance")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            geo_data["sales_by_market"].sort_values("Total Sales", ascending=True),
            x="Total Sales", y="Market", orientation="h",
            title="Revenue by Market",
            color="Total Sales", color_continuous_scale="Blues",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            geo_data["profit_by_market"].sort_values("Total Profit", ascending=True),
            x="Total Profit", y="Market", orientation="h",
            title="Profit by Market",
            color="Total Profit", color_continuous_scale="RdYlGn",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Revenue by Order Region (Top 15)")
    fig = px.bar(
        geo_data["sales_by_region"].head(15),
        x="Total Sales", y="Order Region", orientation="h",
        color="Total Sales", color_continuous_scale="Teal",
    )
    fig.update_layout(height=450)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Revenue by Country (Top 20)")
    fig = px.bar(
        geo_data["sales_by_country"],
        x="Total Sales", y="Order Country", orientation="h",
        color="Total Sales", color_continuous_scale="Purples",
    )
    fig.update_layout(height=550)
    st.plotly_chart(fig, use_container_width=True)

# ────────────────────────────────────────────────────────────────────────────
# TAB 7 — Key Insights
# ────────────────────────────────────────────────────────────────────────────
with tabs[6]:
    st.header("Key Insights")
    st.markdown(
        "The following insights are **dynamically computed** from the currently "
        "filtered dataset."
    )
    for i, insight in enumerate(insights, 1):
        st.info(f"**Insight {i}:** {insight}")

# ────────────────────────────────────────────────────────────────────────────
# TAB 8 — Recommendations
# ────────────────────────────────────────────────────────────────────────────
with tabs[7]:
    st.header("Recommendations")
    st.markdown(
        "Actionable recommendations based on analysis of the currently filtered data."
    )

    priority_color = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}

    for rec in recommendations:
        icon = priority_color.get(rec["priority"], "⚪")
        with st.expander(f"{icon} [{rec['priority']} Priority] {rec['finding']}"):
            st.markdown(f"**Recommendation:** {rec['recommendation']}")

# ────────────────────────────────────────────────────────────────────────────
# TAB 9 — Data Explorer
# ────────────────────────────────────────────────────────────────────────────
with tabs[8]:
    st.header("Data Explorer")
    st.markdown(
        f"Showing **{len(df):,}** rows matching the current filter selection."
    )

    # Column selector
    all_cols = df.columns.tolist()
    default_cols = [
        "order date (DateOrders)", "Market", "Order Region", "Customer Segment",
        "Department Name", "Category Name", "Product Name", "Shipping Mode",
        "Delivery Status", "Order Status", "Sales", "Order Profit Per Order",
        "Profit Margin (%)", "Shipping Delay Days",
    ]
    default_cols = [c for c in default_cols if c in df.columns]
    selected_cols = st.multiselect(
        "Choose columns to display:", options=all_cols, default=default_cols
    )

    if selected_cols:
        display_df = df[selected_cols].head(5000)   # cap for browser performance
        st.dataframe(display_df, use_container_width=True, height=400)

        # CSV download
        csv_bytes = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download filtered data as CSV",
            data=csv_bytes,
            file_name="supply_chain_filtered.csv",
            mime="text/csv",
        )
    else:
        st.warning("Please select at least one column to display.")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#888; font-size:12px;'>"
    "DataCo SMART Supply Chain Analytics Dashboard · Built with Streamlit & Plotly"
    "</div>",
    unsafe_allow_html=True,
)
