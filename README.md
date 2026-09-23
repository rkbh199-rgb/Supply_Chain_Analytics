# DataCo SMART Supply Chain Analytics

A complete, integrated data analytics project built on the **DataCo SMART Supply Chain Dataset**. Covers end-to-end analysis including data cleaning, feature engineering, KPI computation, interactive dashboarding, Jupyter notebook exploration, and a PowerPoint presentation.

---

## Project Structure

```
Supply_Chain_Analytics/
├── DataCoSupplyChainDataset.csv          ← Raw dataset (do not modify)
├── analysis.py                           ← Single source of truth: load, clean, engineer, KPIs, analysis
├── app.py                                ← Streamlit interactive dashboard
├── DataCo_Supply_Chain_Analytics.ipynb   ← Full Jupyter EDA notebook
├── DataCo_Supply_Chain_Analytics.pptx    ← PowerPoint presentation
├── requirements.txt
└── README.md
```

---

## Dataset Description

| Attribute            | Value                                |
|----------------------|--------------------------------------|
| **File**             | DataCoSupplyChainDataset.csv         |
| **Rows**             | 180,519 order-item records           |
| **Columns**          | 53 raw features (49 after cleaning)  |
| **Date Range**       | 2015 – 2018                          |
| **Markets**          | Africa, Europe, LATAM, Pacific Asia, USCA |
| **Order Regions**    | 23 regions worldwide                 |
| **Customer Segments**| Consumer, Corporate, Home Office     |
| **Shipping Modes**   | Standard Class, Second Class, First Class, Same Day |
| **Categories**       | 50 product categories                |
| **Departments**      | 11 departments                       |

### Key Raw Columns

| Column | Description |
|--------|-------------|
| `Type` | Payment type (DEBIT, TRANSFER, CASH, PAYMENT) |
| `Days for shipping (real)` | Actual days taken to ship |
| `Days for shipment (scheduled)` | Originally scheduled shipping days |
| `Benefit per order` | Benefit (profit) per order |
| `Sales per customer` | Sales attributed to the customer |
| `Delivery Status` | Advance shipping / Late delivery / Shipping on time / Shipping canceled |
| `Late_delivery_risk` | 1 = at risk of late delivery, 0 = not at risk |
| `Customer Segment` | Consumer / Corporate / Home Office |
| `Market` | Geographic market |
| `Order Region` | Sub-regional breakdown |
| `Sales` | Revenue per order-item ($) |
| `Order Profit Per Order` | Profit per order ($) |
| `Order Item Discount Rate` | Fractional discount rate |
| `Shipping Mode` | Shipping tier |
| `order date (DateOrders)` | Order timestamp |

---

## Data Cleaning Summary

Cleaning is performed by `clean_data()` in `analysis.py`:

| Step | Action |
|------|--------|
| Date parsing | `order date` and `shipping date` parsed to `datetime` |
| Whitespace | All string columns stripped of leading/trailing whitespace |
| Dropped columns | `Product Description` (100% missing), `Product Image`, `Customer Password`, `Customer Email` (4 columns) |
| Missing fills | `Customer Lname` → `"Unknown"` (8 rows); `Customer Zipcode` → `0` (3 rows) |
| Invalid core rows | Rows with missing `Sales` or `Order Profit Per Order` dropped (0 rows affected) |
| **Result** | 180,519 rows × 49 columns (unchanged row count) |

---

## Feature Engineering

`engineer_features()` adds the following derived columns:

| New Column | Description |
|------------|-------------|
| `Order Year` | Year extracted from order date |
| `Order Month` | Month number (1–12) |
| `Order Month Name` | Abbreviated month name |
| `Order Quarter` | Q1–Q4 |
| `Order YearMonth` | Period string `YYYY-MM` for time series |
| `Shipping Delay Days` | Actual − Scheduled shipping days |
| `Is Late` | 1 if `Delivery Status == 'Late delivery'` else 0 |
| `Profit Margin (%)` | `Order Profit Per Order / Sales × 100` (clipped ±200%) |
| `Revenue Band` | Low / Medium / High / Very High quartile bands |

---

## Key Performance Indicators (Full Dataset)

| KPI | Value |
|-----|-------|
| Total Revenue | $36.78M |
| Total Profit | $3.97M |
| Overall Profit Margin | 10.78% |
| Total Unique Orders | 65,752 |
| Total Unique Customers | 20,652 |
| Total Order Items | 180,519 |
| Avg Order Value | $203.77 |
| Avg Profit Per Order | $21.97 |
| Late Delivery Rate | 54.83% |
| Avg Discount Rate | 10.17% |

> All values computed dynamically from the CSV — no hard-coded figures.

---

## Key Findings

1. **Europe** is the top-performing market, contributing ~29.6% of total revenue.
2. **Late delivery rate is 54.8%** — over half of all orders experience late delivery. Central Africa has the highest regional late-delivery rate.
3. **Consumer segment** accounts for ~52.3% of total profit.
4. **Standard Class** is the most used shipping mode (~55% of orders).
5. **Average discount rate is 10.2%**, which significantly erodes margins.
6. **Fan Shop** is the highest-revenue department; **Golf Bags & Carts** has the best average profit margin.
7. **On-time delivery rate is only 40.9%** — a major operational gap.
8. Average shipping delay is **+0.57 days** (actual vs scheduled).

---

## Dashboard Features (`app.py`)

| Tab | Content |
|-----|---------|
| 📊 Executive Overview | KPI cards, monthly sales/profit trends, market revenue, delivery status pie |
| 💰 Sales & Profitability | Profit by market/department, sales vs profit scatter, yearly comparison |
| 👥 Customer Analytics | Segment breakdown, revenue/profit by segment, top 20 customers, payment types |
| 📦 Product Analytics | Top categories/products by sales & profit, category profit margins |
| 🚚 Shipping & Delivery | Shipping mode distribution, late rate by mode, delay by mode, order status |
| 🌍 Geographic Performance | Revenue/profit by market, region, and country |
| 💡 Key Insights | Dynamically generated insights from filtered data |
| ✅ Recommendations | Priority-ranked actionable recommendations |
| 🔎 Data Explorer | Searchable filtered table + CSV download |

**All charts and KPIs update automatically when sidebar filters change.**

---

## Technologies

| Library | Purpose |
|---------|---------|
| `pandas` | Data loading, cleaning, manipulation |
| `numpy` | Numerical operations |
| `plotly` | Interactive charts in dashboard & notebook |
| `streamlit` | Interactive web dashboard |
| `matplotlib` | Static charts in notebook |
| `seaborn` | Statistical visualisation styling |
| `jupyter` | Notebook environment |
| `python-pptx` | PowerPoint generation |
| `openpyxl` | Excel compatibility |
| `nbformat` | Notebook file format |

---

## Installation

```bash
# 1. Navigate to project directory
cd Supply_Chain_Analytics

# 2. (Recommended) Create virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## How to Run

### Streamlit Dashboard
```bash
cd Supply_Chain_Analytics
streamlit run app.py
```
Then open `http://localhost:8501` in your browser.

### Jupyter Notebook
```bash
cd Supply_Chain_Analytics
jupyter notebook DataCo_Supply_Chain_Analytics.ipynb
```

### Run analysis module directly (self-test)
```bash
cd Supply_Chain_Analytics
python analysis.py
```

---

## Limitations

- **Product Description** column was entirely empty (100% missing) and was dropped.
- **Order Zipcode** is missing for ~86% of rows — not used in analysis.
- Late delivery risk is based on the `Delivery Status` column (not the `Late_delivery_risk` binary flag, which is a model prediction in the source data). Both are available for cross-checking.
- Geographic map charts are not implemented (Plotly Mapbox requires a token); region/country bar charts are used instead.
- Data covers 2015–2018; conclusions may not reflect current supply chain conditions.

---

## Future Scope

- Machine learning model to predict late delivery risk before shipping
- Supplier performance analysis (if supplier data is enriched)
- Real-time dashboard connected to a live database
- Customer churn prediction based on order history
- Route optimisation analysis using latitude/longitude coordinates
- Automated alerting when KPIs fall below thresholds

---

*Built with Python · pandas · Streamlit · Plotly · Jupyter*
#   S u p p l y _ C h a i n _ A n a l y t i c s  
 