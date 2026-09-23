# =============================================================================
# analysis.py
# DataCo SMART Supply Chain Analytics — Single Source of Truth
#
# All functions used by app.py and the Jupyter notebook.
# Every function accepts an already-cleaned + feature-engineered DataFrame so
# the same function works correctly on the full dataset OR any filtered subset.
# =============================================================================

import os
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH  = os.path.join(_THIS_DIR, "DataCoSupplyChainDataset.csv")


# ---------------------------------------------------------------------------
# 1. LOAD
# ---------------------------------------------------------------------------
def load_data(path: str = CSV_PATH) -> pd.DataFrame:
    """
    Load the raw DataCo CSV and return a DataFrame.
    Uses latin-1 encoding because the file contains non-ASCII characters.
    """
    df = pd.read_csv(path, encoding="latin-1", low_memory=False)
    return df


# ---------------------------------------------------------------------------
# 2. CLEAN
# ---------------------------------------------------------------------------
def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Clean the raw DataFrame and return (cleaned_df, summary_dict).

    Cleaning steps
    ──────────────
    • Parse date columns to datetime
    • Strip leading/trailing whitespace from string columns
    • Drop columns that contain no useful information (Product Description,
      Product Image, Customer Password, Customer Email)
    • Fill the handful of missing Customer Lname values with 'Unknown'
    • Drop rows where Sales or Order Profit Per Order is NaN (none expected,
      but guards against future data issues)
    • Reset the index
    """
    original_rows = len(df)
    original_cols = df.shape[1]

    # ── Parse dates ──────────────────────────────────────────────────────────
    df = df.copy()
    df["order date (DateOrders)"]    = pd.to_datetime(
        df["order date (DateOrders)"],    format="%m/%d/%Y %H:%M", errors="coerce"
    )
    df["shipping date (DateOrders)"] = pd.to_datetime(
        df["shipping date (DateOrders)"], format="%m/%d/%Y %H:%M", errors="coerce"
    )

    # ── Strip whitespace from string columns ─────────────────────────────────
    str_cols = df.select_dtypes(include=["object", "str"]).columns
    for col in str_cols:
        df[col] = df[col].str.strip()

    # ── Drop uninformative columns ───────────────────────────────────────────
    drop_cols = ["Product Description", "Product Image",
                 "Customer Password",   "Customer Email"]
    df.drop(columns=[c for c in drop_cols if c in df.columns], inplace=True)

    # ── Fill small gaps ──────────────────────────────────────────────────────
    if "Customer Lname" in df.columns:
        df["Customer Lname"] = df["Customer Lname"].fillna("Unknown")
    if "Customer Zipcode" in df.columns:
        df["Customer Zipcode"] = df["Customer Zipcode"].fillna(0)

    # ── Drop rows with missing core numeric values ───────────────────────────
    df.dropna(subset=["Sales", "Order Profit Per Order"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    summary = {
        "original_rows":  original_rows,
        "original_cols":  original_cols,
        "cleaned_rows":   len(df),
        "cleaned_cols":   df.shape[1],
        "rows_dropped":   original_rows - len(df),
        "cols_dropped":   original_cols - df.shape[1],
        "missing_after":  int(df.isnull().sum().sum()),
    }
    return df, summary


# ---------------------------------------------------------------------------
# 3. FEATURE ENGINEERING
# ---------------------------------------------------------------------------
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived columns to support analysis.

    New columns
    ───────────
    Order Year          — integer year of the order date
    Order Month         — integer month (1–12)
    Order Month Name    — abbreviated month name (Jan … Dec)
    Order Quarter       — 'Q1' … 'Q4'
    Order YearMonth     — period string 'YYYY-MM' for time-series charts
    Shipping Delay Days — actual − scheduled shipping days
    Is Late             — 1 if Delivery Status == 'Late delivery' else 0
    Profit Margin (%)   — Order Profit Per Order / Sales × 100  (clipped to [-200, 200])
    Discount Amount     — Order Item Discount (absolute £ discount)
    Revenue Band        — Low / Medium / High / Very High based on Sales quartiles
    """
    df = df.copy()

    # ── Time features ─────────────────────────────────────────────────────
    df["Order Year"]       = df["order date (DateOrders)"].dt.year
    df["Order Month"]      = df["order date (DateOrders)"].dt.month
    df["Order Month Name"] = df["order date (DateOrders)"].dt.strftime("%b")
    df["Order Quarter"]    = "Q" + df["order date (DateOrders)"].dt.quarter.astype(str)
    df["Order YearMonth"]  = df["order date (DateOrders)"].dt.to_period("M").astype(str)

    # ── Shipping features ─────────────────────────────────────────────────
    df["Shipping Delay Days"] = (
        df["Days for shipping (real)"] - df["Days for shipment (scheduled)"]
    )
    df["Is Late"] = (df["Delivery Status"] == "Late delivery").astype(int)

    # ── Profitability features ────────────────────────────────────────────
    df["Profit Margin (%)"] = np.where(
        df["Sales"] != 0,
        (df["Order Profit Per Order"] / df["Sales"] * 100).clip(-200, 200),
        0
    )

    # ── Revenue band (based on full-dataset quartiles) ────────────────────
    try:
        df["Revenue Band"] = pd.qcut(
            df["Sales"],
            q=4,
            labels=["Low", "Medium", "High", "Very High"],
            duplicates="drop"
        )
    except Exception:
        df["Revenue Band"] = "Medium"

    return df


# ---------------------------------------------------------------------------
# 4. COMBINED LOADER  (convenience wrapper)
# ---------------------------------------------------------------------------
def load_and_prepare(path: str = CSV_PATH) -> tuple[pd.DataFrame, dict]:
    """Load, clean, and engineer features in one call. Returns (df, clean_summary)."""
    raw = load_data(path)
    cleaned, summary = clean_data(raw)
    prepared = engineer_features(cleaned)
    return prepared, summary


# ---------------------------------------------------------------------------
# 5. KPIs
# ---------------------------------------------------------------------------
def get_kpis(df: pd.DataFrame) -> dict:
    """
    Return a dictionary of top-level KPI values computed from df.

    Keys
    ────
    total_sales           — sum of Sales
    total_profit          — sum of Order Profit Per Order
    total_orders          — number of unique Order Ids
    total_customers       — number of unique Customer Ids
    avg_order_value       — mean Sales per order item
    avg_profit_per_order  — mean Order Profit Per Order
    overall_profit_margin — total_profit / total_sales × 100
    late_delivery_rate    — fraction of rows where Is Late == 1  (0–100 %)
    avg_discount_rate     — mean Order Item Discount Rate × 100
    total_order_items     — row count (each row = one order-item)
    """
    if df.empty:
        return {k: 0 for k in [
            "total_sales", "total_profit", "total_orders", "total_customers",
            "avg_order_value", "avg_profit_per_order", "overall_profit_margin",
            "late_delivery_rate", "avg_discount_rate", "total_order_items"
        ]}

    total_sales  = df["Sales"].sum()
    total_profit = df["Order Profit Per Order"].sum()

    return {
        "total_sales":           round(total_sales,  2),
        "total_profit":          round(total_profit, 2),
        "total_orders":          df["Order Id"].nunique(),
        "total_customers":       df["Customer Id"].nunique(),
        "avg_order_value":       round(df["Sales"].mean(), 2),
        "avg_profit_per_order":  round(df["Order Profit Per Order"].mean(), 2),
        "overall_profit_margin": round((total_profit / total_sales * 100) if total_sales else 0, 2),
        "late_delivery_rate":    round(df["Is Late"].mean() * 100, 2),
        "avg_discount_rate":     round(df["Order Item Discount Rate"].mean() * 100, 2),
        "total_order_items":     len(df),
    }


# ---------------------------------------------------------------------------
# 6. SALES ANALYSIS
# ---------------------------------------------------------------------------
def sales_analysis(df: pd.DataFrame) -> dict:
    """
    Returns a dict of DataFrames/Series useful for sales charts.

    Keys
    ────
    monthly_trend     — monthly sales totals indexed by Order YearMonth
    yearly_trend      — yearly sales totals
    by_market         — sales by Market
    by_region         — sales by Order Region
    by_segment        — sales by Customer Segment
    by_shipping_mode  — sales by Shipping Mode
    by_quarter        — sales by Order Quarter
    """
    monthly = (
        df.groupby("Order YearMonth")["Sales"]
          .sum()
          .reset_index()
          .rename(columns={"Sales": "Total Sales"})
          .sort_values("Order YearMonth")
    )

    yearly = (
        df.groupby("Order Year")["Sales"]
          .sum()
          .reset_index()
          .rename(columns={"Sales": "Total Sales"})
          .sort_values("Order Year")
    )

    return {
        "monthly_trend":    monthly,
        "yearly_trend":     yearly,
        "by_market":        df.groupby("Market")["Sales"].sum().reset_index().rename(columns={"Sales": "Total Sales"}),
        "by_region":        df.groupby("Order Region")["Sales"].sum().reset_index().rename(columns={"Sales": "Total Sales"}).sort_values("Total Sales", ascending=False),
        "by_segment":       df.groupby("Customer Segment")["Sales"].sum().reset_index().rename(columns={"Sales": "Total Sales"}),
        "by_shipping_mode": df.groupby("Shipping Mode")["Sales"].sum().reset_index().rename(columns={"Sales": "Total Sales"}),
        "by_quarter":       df.groupby("Order Quarter")["Sales"].sum().reset_index().rename(columns={"Sales": "Total Sales"}),
    }


# ---------------------------------------------------------------------------
# 7. PROFIT ANALYSIS
# ---------------------------------------------------------------------------
def profit_analysis(df: pd.DataFrame) -> dict:
    """
    Returns a dict of DataFrames/Series for profitability charts.

    Keys
    ────
    monthly_trend     — monthly profit totals
    yearly_trend      — yearly profit totals
    by_market         — profit by Market
    by_region         — profit by Order Region
    by_segment        — profit by Customer Segment
    by_category       — profit by Category Name
    by_department     — profit by Department Name
    margin_by_market  — average Profit Margin (%) by Market
    margin_by_segment — average Profit Margin (%) by Customer Segment
    """
    monthly = (
        df.groupby("Order YearMonth")["Order Profit Per Order"]
          .sum()
          .reset_index()
          .rename(columns={"Order Profit Per Order": "Total Profit"})
          .sort_values("Order YearMonth")
    )

    yearly = (
        df.groupby("Order Year")["Order Profit Per Order"]
          .sum()
          .reset_index()
          .rename(columns={"Order Profit Per Order": "Total Profit"})
          .sort_values("Order Year")
    )

    return {
        "monthly_trend":     monthly,
        "yearly_trend":      yearly,
        "by_market":         df.groupby("Market")["Order Profit Per Order"].sum().reset_index().rename(columns={"Order Profit Per Order": "Total Profit"}),
        "by_region":         df.groupby("Order Region")["Order Profit Per Order"].sum().reset_index().rename(columns={"Order Profit Per Order": "Total Profit"}).sort_values("Total Profit", ascending=False),
        "by_segment":        df.groupby("Customer Segment")["Order Profit Per Order"].sum().reset_index().rename(columns={"Order Profit Per Order": "Total Profit"}),
        "by_category":       df.groupby("Category Name")["Order Profit Per Order"].sum().reset_index().rename(columns={"Order Profit Per Order": "Total Profit"}).sort_values("Total Profit", ascending=False),
        "by_department":     df.groupby("Department Name")["Order Profit Per Order"].sum().reset_index().rename(columns={"Order Profit Per Order": "Total Profit"}).sort_values("Total Profit", ascending=False),
        "margin_by_market":  df.groupby("Market")["Profit Margin (%)"].mean().reset_index().rename(columns={"Profit Margin (%)": "Avg Profit Margin (%)"}),
        "margin_by_segment": df.groupby("Customer Segment")["Profit Margin (%)"].mean().reset_index().rename(columns={"Profit Margin (%)": "Avg Profit Margin (%)"}),
    }


# ---------------------------------------------------------------------------
# 8. CUSTOMER ANALYSIS
# ---------------------------------------------------------------------------
def customer_analysis(df: pd.DataFrame) -> dict:
    """
    Returns a dict of DataFrames for customer-related charts.

    Keys
    ────
    segment_counts        — order-item count per Customer Segment
    sales_by_segment      — total sales by Customer Segment
    profit_by_segment     — total profit by Customer Segment
    top_customers         — top 20 customers by total sales
    segment_avg_order     — avg Sales per order-item by segment
    payment_type_counts   — count by Type (payment method)
    """
    top_customers = (
        df.groupby(["Customer Id", "Customer Fname", "Customer Lname"])["Sales"]
          .sum()
          .reset_index()
          .rename(columns={"Sales": "Total Sales"})
          .sort_values("Total Sales", ascending=False)
          .head(20)
    )
    top_customers["Customer Name"] = (
        top_customers["Customer Fname"].astype(str) + " " +
        top_customers["Customer Lname"].astype(str)
    )

    return {
        "segment_counts":    df.groupby("Customer Segment").size().reset_index(name="Order Items"),
        "sales_by_segment":  df.groupby("Customer Segment")["Sales"].sum().reset_index().rename(columns={"Sales": "Total Sales"}),
        "profit_by_segment": df.groupby("Customer Segment")["Order Profit Per Order"].sum().reset_index().rename(columns={"Order Profit Per Order": "Total Profit"}),
        "top_customers":     top_customers,
        "segment_avg_order": df.groupby("Customer Segment")["Sales"].mean().reset_index().rename(columns={"Sales": "Avg Sales"}),
        "payment_type_counts": df.groupby("Type").size().reset_index(name="Count"),
    }


# ---------------------------------------------------------------------------
# 9. PRODUCT ANALYSIS
# ---------------------------------------------------------------------------
def product_analysis(df: pd.DataFrame) -> dict:
    """
    Returns a dict of DataFrames for product/category charts.

    Keys
    ────
    sales_by_category      — total sales per Category Name
    profit_by_category     — total profit per Category Name
    sales_by_department    — total sales per Department Name
    top_products_by_sales  — top 15 products by total sales
    top_products_by_profit — top 15 products by total profit
    bottom_products        — bottom 10 products by total profit
    category_profit_margin — avg profit margin by category
    """
    prod_sales = (
        df.groupby("Product Name")["Sales"]
          .sum()
          .reset_index()
          .rename(columns={"Sales": "Total Sales"})
          .sort_values("Total Sales", ascending=False)
    )
    prod_profit = (
        df.groupby("Product Name")["Order Profit Per Order"]
          .sum()
          .reset_index()
          .rename(columns={"Order Profit Per Order": "Total Profit"})
          .sort_values("Total Profit", ascending=False)
    )

    return {
        "sales_by_category":      df.groupby("Category Name")["Sales"].sum().reset_index().rename(columns={"Sales": "Total Sales"}).sort_values("Total Sales", ascending=False),
        "profit_by_category":     df.groupby("Category Name")["Order Profit Per Order"].sum().reset_index().rename(columns={"Order Profit Per Order": "Total Profit"}).sort_values("Total Profit", ascending=False),
        "sales_by_department":    df.groupby("Department Name")["Sales"].sum().reset_index().rename(columns={"Sales": "Total Sales"}).sort_values("Total Sales", ascending=False),
        "top_products_by_sales":  prod_sales.head(15),
        "top_products_by_profit": prod_profit.head(15),
        "bottom_products":        prod_profit.tail(10).sort_values("Total Profit"),
        "category_profit_margin": df.groupby("Category Name")["Profit Margin (%)"].mean().reset_index().rename(columns={"Profit Margin (%)": "Avg Profit Margin (%)"}).sort_values("Avg Profit Margin (%)", ascending=False),
    }


# ---------------------------------------------------------------------------
# 10. SHIPPING ANALYSIS
# ---------------------------------------------------------------------------
def shipping_analysis(df: pd.DataFrame) -> dict:
    """
    Returns a dict of DataFrames for shipping charts.

    Keys
    ────
    mode_counts         — count of order-items per Shipping Mode
    mode_sales          — total sales per Shipping Mode
    mode_avg_delay      — avg Shipping Delay Days per Shipping Mode
    delay_distribution  — distribution of Shipping Delay Days values
    mode_late_rate      — late delivery rate (%) per Shipping Mode
    """
    mode_late = (
        df.groupby("Shipping Mode")["Is Late"]
          .mean()
          .mul(100)
          .reset_index()
          .rename(columns={"Is Late": "Late Rate (%)"})
    )
    delay_counts = df["Shipping Delay Days"].value_counts().reset_index()
    # pandas ≥ 2.0 uses value_counts column name as 'count'; ensure consistent naming
    delay_counts.columns = ["Shipping Delay Days", "Count"]
    delay_dist = delay_counts.sort_values("Shipping Delay Days")

    return {
        "mode_counts":        df.groupby("Shipping Mode").size().reset_index(name="Order Items"),
        "mode_sales":         df.groupby("Shipping Mode")["Sales"].sum().reset_index().rename(columns={"Sales": "Total Sales"}),
        "mode_avg_delay":     df.groupby("Shipping Mode")["Shipping Delay Days"].mean().reset_index().rename(columns={"Shipping Delay Days": "Avg Delay Days"}),
        "delay_distribution": delay_dist,
        "mode_late_rate":     mode_late,
    }


# ---------------------------------------------------------------------------
# 11. DELIVERY ANALYSIS
# ---------------------------------------------------------------------------
def delivery_analysis(df: pd.DataFrame) -> dict:
    """
    Returns a dict of DataFrames for delivery performance charts.

    Keys
    ────
    status_counts        — count of order-items per Delivery Status
    status_by_market     — delivery status breakdown by Market
    late_by_region       — late delivery rate by Order Region
    late_by_category     — late delivery rate by Category Name
    order_status_counts  — count of order-items per Order Status
    late_by_year         — late delivery rate trend by year
    """
    late_region = (
        df.groupby("Order Region")["Is Late"]
          .mean()
          .mul(100)
          .reset_index()
          .rename(columns={"Is Late": "Late Rate (%)"})
          .sort_values("Late Rate (%)", ascending=False)
    )
    late_category = (
        df.groupby("Category Name")["Is Late"]
          .mean()
          .mul(100)
          .reset_index()
          .rename(columns={"Is Late": "Late Rate (%)"})
          .sort_values("Late Rate (%)", ascending=False)
    )
    late_year = (
        df.groupby("Order Year")["Is Late"]
          .mean()
          .mul(100)
          .reset_index()
          .rename(columns={"Is Late": "Late Rate (%)"})
          .sort_values("Order Year")
    )

    return {
        "status_counts":       df.groupby("Delivery Status").size().reset_index(name="Count").sort_values("Count", ascending=False),
        "status_by_market":    df.groupby(["Market", "Delivery Status"]).size().reset_index(name="Count"),
        "late_by_region":      late_region,
        "late_by_category":    late_category,
        "order_status_counts": df.groupby("Order Status").size().reset_index(name="Count").sort_values("Count", ascending=False),
        "late_by_year":        late_year,
    }


# ---------------------------------------------------------------------------
# 12. GEOGRAPHIC ANALYSIS
# ---------------------------------------------------------------------------
def geo_analysis(df: pd.DataFrame) -> dict:
    """
    Returns a dict of DataFrames for geographic charts.

    Keys
    ────
    sales_by_market       — total sales by Market
    profit_by_market      — total profit by Market
    sales_by_region       — total sales by Order Region
    profit_by_region      — total profit by Order Region
    sales_by_country      — total sales by Order Country (top 20)
    market_order_count    — order count by Market
    """
    sales_country = (
        df.groupby("Order Country")["Sales"]
          .sum()
          .reset_index()
          .rename(columns={"Sales": "Total Sales"})
          .sort_values("Total Sales", ascending=False)
          .head(20)
    )

    return {
        "sales_by_market":    df.groupby("Market")["Sales"].sum().reset_index().rename(columns={"Sales": "Total Sales"}).sort_values("Total Sales", ascending=False),
        "profit_by_market":   df.groupby("Market")["Order Profit Per Order"].sum().reset_index().rename(columns={"Order Profit Per Order": "Total Profit"}).sort_values("Total Profit", ascending=False),
        "sales_by_region":    df.groupby("Order Region")["Sales"].sum().reset_index().rename(columns={"Sales": "Total Sales"}).sort_values("Total Sales", ascending=False),
        "profit_by_region":   df.groupby("Order Region")["Order Profit Per Order"].sum().reset_index().rename(columns={"Order Profit Per Order": "Total Profit"}).sort_values("Total Profit", ascending=False),
        "sales_by_country":   sales_country,
        "market_order_count": df.groupby("Market")["Order Id"].nunique().reset_index().rename(columns={"Order Id": "Total Orders"}),
    }


# ---------------------------------------------------------------------------
# 13. BUSINESS QUESTIONS
# ---------------------------------------------------------------------------
def answer_business_questions(df: pd.DataFrame) -> dict:
    """
    Answer key supply chain business questions.

    Returns a dict where each key is a question label and each value is
    a small DataFrame or scalar with the answer.
    """
    answers = {}

    # Q1 — Which market generates the most revenue?
    answers["top_market_by_revenue"] = (
        df.groupby("Market")["Sales"].sum().idxmax()
    )

    # Q2 — Which customer segment is most profitable?
    answers["most_profitable_segment"] = (
        df.groupby("Customer Segment")["Order Profit Per Order"].sum().idxmax()
    )

    # Q3 — What shipping mode is used the most?
    answers["most_used_shipping_mode"] = (
        df["Shipping Mode"].value_counts().idxmax()
    )

    # Q4 — What is the on-time delivery rate?
    on_time_mask = df["Delivery Status"].isin(["Advance shipping", "Shipping on time"])
    answers["on_time_delivery_rate_pct"] = round(on_time_mask.mean() * 100, 2)

    # Q5 — Which product category has the highest profit margin?
    answers["highest_margin_category"] = (
        df.groupby("Category Name")["Profit Margin (%)"].mean().idxmax()
    )

    # Q6 — Which region has the highest late delivery rate?
    answers["highest_late_rate_region"] = (
        df.groupby("Order Region")["Is Late"].mean().idxmax()
    )

    # Q7 — What is the average shipping delay?
    answers["avg_shipping_delay_days"] = round(df["Shipping Delay Days"].mean(), 2)

    # Q8 — Which order status is most common?
    answers["most_common_order_status"] = (
        df["Order Status"].value_counts().idxmax()
    )

    # Q9 — Which department drives the most sales?
    answers["top_department_by_sales"] = (
        df.groupby("Department Name")["Sales"].sum().idxmax()
    )

    # Q10 — What is the average discount rate?
    answers["avg_discount_rate_pct"] = round(df["Order Item Discount Rate"].mean() * 100, 2)

    return answers


# ---------------------------------------------------------------------------
# 14. INSIGHTS
# ---------------------------------------------------------------------------
def generate_insights(df: pd.DataFrame) -> list[str]:
    """
    Dynamically generate a list of insight strings from the data.
    All numbers are computed from df, not hard-coded.
    """
    if df.empty:
        return ["No data available for the current filter selection."]

    kpis = get_kpis(df)
    bq   = answer_business_questions(df)
    insights = []

    # Revenue
    insights.append(
        f"💰 Total revenue of ${kpis['total_sales']:,.0f} with an overall profit of "
        f"${kpis['total_profit']:,.0f} (margin: {kpis['overall_profit_margin']:.1f}%)."
    )

    # Top market
    top_market_sales = df.groupby("Market")["Sales"].sum()
    top_market_pct   = top_market_sales.max() / top_market_sales.sum() * 100
    insights.append(
        f"🌍 {bq['top_market_by_revenue']} is the top-performing market, contributing "
        f"{top_market_pct:.1f}% of total revenue."
    )

    # Late delivery
    insights.append(
        f"🚚 Late delivery rate is {kpis['late_delivery_rate']:.1f}%. "
        f"The region most affected by late deliveries is {bq['highest_late_rate_region']}."
    )

    # On-time
    insights.append(
        f"✅ On-time delivery rate: {bq['on_time_delivery_rate_pct']:.1f}%."
    )

    # Most profitable segment
    seg_profit = df.groupby("Customer Segment")["Order Profit Per Order"].sum()
    seg_pct    = seg_profit.max() / seg_profit.sum() * 100
    insights.append(
        f"👥 The '{bq['most_profitable_segment']}' customer segment contributes "
        f"{seg_pct:.1f}% of total profit."
    )

    # Shipping mode
    insights.append(
        f"📦 '{bq['most_used_shipping_mode']}' is the most commonly used shipping mode."
    )

    # Average discount
    insights.append(
        f"🏷️ Average discount rate is {kpis['avg_discount_rate']:.1f}%, which reduces "
        f"potential revenue."
    )

    # Delay
    insights.append(
        f"⏱️ Average shipping delay is {bq['avg_shipping_delay_days']} days "
        f"(actual vs scheduled)."
    )

    # Top department
    insights.append(
        f"🏪 The '{bq['top_department_by_sales']}' department drives the most sales."
    )

    # Highest margin category
    insights.append(
        f"📈 '{bq['highest_margin_category']}' has the highest average profit margin "
        f"across all product categories."
    )

    return insights


# ---------------------------------------------------------------------------
# 15. RECOMMENDATIONS
# ---------------------------------------------------------------------------
def generate_recommendations(df: pd.DataFrame) -> list[dict]:
    """
    Generate a list of actionable recommendation dicts.
    Each dict has keys: 'finding', 'recommendation', 'priority'.
    All findings are derived from df.
    """
    if df.empty:
        return [{"finding": "No data", "recommendation": "Broaden filter selection.", "priority": "N/A"}]

    kpis = get_kpis(df)
    bq   = answer_business_questions(df)
    recs = []

    # 1 — Late delivery
    if kpis["late_delivery_rate"] > 50:
        recs.append({
            "finding":        f"Late delivery rate is high at {kpis['late_delivery_rate']:.1f}%.",
            "recommendation": "Audit logistics partners and route planning. Introduce real-time tracking and penalty clauses for carriers consistently missing SLAs.",
            "priority":       "High",
        })
    else:
        recs.append({
            "finding":        f"Late delivery rate is {kpis['late_delivery_rate']:.1f}%.",
            "recommendation": "Maintain current logistics performance; consider extending advance shipping offers to improve customer satisfaction further.",
            "priority":       "Medium",
        })

    # 2 — Discount rate
    if kpis["avg_discount_rate"] > 5:
        recs.append({
            "finding":        f"Average discount rate is {kpis['avg_discount_rate']:.1f}%, eroding margins.",
            "recommendation": "Implement a structured discount policy — cap product-level discounts and restrict high-discount orders to high-volume customers only.",
            "priority":       "High",
        })

    # 3 — Profit margin
    if kpis["overall_profit_margin"] < 10:
        recs.append({
            "finding":        f"Overall profit margin is only {kpis['overall_profit_margin']:.1f}%.",
            "recommendation": "Focus on high-margin categories and customer segments. Renegotiate supplier contracts for low-margin products.",
            "priority":       "High",
        })

    # 4 — Most used shipping mode vs delay
    mode_delay = df.groupby("Shipping Mode")["Shipping Delay Days"].mean()
    worst_mode = mode_delay.idxmax()
    recs.append({
        "finding":        f"'{worst_mode}' shipping mode has the highest average delay ({mode_delay.max():.1f} days).",
        "recommendation": f"Review carrier agreements for '{worst_mode}'. Consider alternative providers or mode-switching incentives for customers.",
        "priority":       "Medium",
    })

    # 5 — Underperforming region
    region_profit = df.groupby("Order Region")["Order Profit Per Order"].sum()
    worst_region  = region_profit.idxmin()
    recs.append({
        "finding":        f"'{worst_region}' has the lowest total profit (${region_profit.min():,.0f}).",
        "recommendation": "Evaluate pricing strategy and cost structure in this region. Consider targeted promotions or reducing operational footprint if margins remain negative.",
        "priority":       "Medium",
    })

    # 6 — Top market
    recs.append({
        "finding":        f"{bq['top_market_by_revenue']} is the highest-revenue market.",
        "recommendation": f"Invest further in {bq['top_market_by_revenue']} market with localised product offerings and faster shipping tiers to capture greater market share.",
        "priority":       "Low",
    })

    # 7 — Customer segment
    recs.append({
        "finding":        f"'{bq['most_profitable_segment']}' segment drives the most profit.",
        "recommendation": f"Design loyalty programmes and exclusive offers for the '{bq['most_profitable_segment']}' segment to increase retention and wallet share.",
        "priority":       "Low",
    })

    return recs


# ---------------------------------------------------------------------------
# CLI self-test — run `python analysis.py` to verify no import / logic errors
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import pprint
    print("Loading data …")
    df, clean_summary = load_and_prepare()
    print(f"  Shape after clean+engineer: {df.shape}")
    print(f"  Clean summary: {clean_summary}")

    print("\nKPIs:")
    pprint.pprint(get_kpis(df))

    print("\nBusiness Questions:")
    pprint.pprint(answer_business_questions(df))

    print("\nInsights:")
    for ins in generate_insights(df):
        print(" *", ins.encode("ascii", "replace").decode())

    print("\nRecommendations:")
    for r in generate_recommendations(df):
        print(f"  [{r['priority']}] {r['finding']}".encode("ascii","replace").decode())
        print(f"       -> {r['recommendation']}".encode("ascii","replace").decode())

    print("\nanalysis.py ran successfully.")
