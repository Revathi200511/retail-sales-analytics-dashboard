# 🛒 Retail Sales Analytics Dashboard

A complete, full-stack Data Analytics web application built with **Python Flask**, **SQLite**, **Pandas**, **Scikit-Learn**, **Plotly**, and **Chart.js**.

![Dashboard Preview](static/images/preview.png)

---

## 🌟 Key Features

1. **📊 Executive Dashboard & KPIs**
   - **Total Sales**, **Total Profit**, **Total Orders**, **Average Order Value**, and **Profit Margin**.
   - **10 Interactive Dynamic Charts**:
     1. Sales by Region (Donut)
     2. Sales by Category (Bar)
     3. Profit vs Revenue by Category (Grouped Bar)
     4. Top 10 Best-Selling Products (Horizontal Bar)
     5. Top Customers by Revenue (Bar)
     6. Top States by Sales (Bar)
     7. Discount vs Profit Correlation (Plotly Scatter)
     8. Monthly Sales & Profit Trend (Line with area gradient)
     9. Category Share Breakdown (Pie)
     10. Regional Profitability Matrix (Plotly Heatmap)

2. **🔍 Multi-Dimensional Dynamic Filtering**
   - Filter by **Date Range**, **Region**, **State**, **Category**, **Sub-Category**, **Customer**, and **Year**.
   - All KPIs and 10 charts update dynamically in real time.

3. **🔬 Exploratory Data Analysis (EDA)**
   - Missing values count & duplicate rows detection.
   - Summary statistics table (`mean`, `std`, `min`, `25%`, `median`, `75%`, `max`).
   - Interactive Pearson Correlation Matrix Heatmap.
   - IQR Outlier detection metrics & distribution histograms for Sales, Profit, and Discount.

4. **💡 Automated AI Business Insights**
   - Automatically computes highest revenue region, lowest profit region, best-selling category, top customer account, latest MoM growth %, and high-discount risk flags.

5. **🤖 Machine Learning Sales Prediction**
   - Fits Ordinary Least Squares (OLS) **Scikit-Learn Linear Regression** on historical monthly sales.
   - Projects 3 to 12 months future revenue trends.
   - Displays evaluation metrics ($R^2$ Score, MAE, RMSE, Monthly Growth Velocity).

6. **📄 PDF Reports & CSV Exports**
   - Download executive PDF report generated dynamically with **ReportLab**.
   - Export raw or filtered dataset records as CSV.

7. **🔐 User Authentication**
   - Login, User Registration, and Logout with secure password hashing (`Werkzeug`).

8. **⚡ Admin Panel & Dataset Management**
   - Drag & drop upload new CSV datasets.
   - Activate, replace, or delete datasets.
   - Clear cache & refresh dashboard indexes.

9. **🌙 Modern UI & Theme System**
   - Sleek responsive design with **Dark & Light Mode** toggle.
   - Glassmorphism UI cards, sidebar navigation, FontAwesome icons, and animated KPI counters.

---

## 📁 Project Folder Structure

```
c:/Users/gorup/OneDrive/Documents/data analytics/
│
├── app.py                     # Main Flask Application & API Controller
├── requirements.txt           # Python Package Dependencies
├── generate_dataset.py        # Dataset Generator Script
├── retail_sales.csv           # Sample Dataset (~1,500 records)
├── database.db                # SQLite Database (Users & Datasets)
│
├── templates/                 # Jinja2 HTML Templates
│   ├── base.html              # Base layout with sidebar & theme switcher
│   ├── login.html             # User Login page
│   ├── register.html          # Registration page
│   ├── dashboard.html         # Main Analytics Dashboard (KPIs & 10 Charts)
│   ├── eda.html               # Exploratory Data Analysis page
│   ├── insights.html          # Automated Business Insights page
│   ├── prediction.html        # Machine Learning Forecasting page
│   ├── reports.html           # Downloadable PDF & CSV page
│   └── admin.html             # Admin Dataset Manager
│
├── static/                    # Frontend Static Assets
│   ├── css/
│   │   └── style.css          # Design System & Theme CSS
│   └── js/
│       ├── main.js            # Theme toggle & toast helpers
│       ├── dashboard.js       # Dynamic filter & Chart.js/Plotly handler
│       ├── eda.js             # EDA calculations & correlation matrix
│       └── prediction.js      # ML controls & forecast chart
│
└── uploads/                   # User Uploaded Datasets Directory
```

---

## 🚀 Quick Setup & Running Instructions

### 1. Prerequisites
- Python 3.10+
- `pip` package manager

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Generate Sample Dataset (Optional)
```bash
python generate_dataset.py
```

### 4. Run Flask Application
```bash
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

### Default Credentials:
- **Username**: `admin`
- **Password**: `admin123`

---

## 🔌 API Endpoints Summary

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/filters/options` | GET | Dynamic filter dropdown values & date bounds |
| `/api/dashboard/kpis` | GET | Aggregated KPI card values |
| `/api/dashboard/charts` | GET | Data for all 10 interactive charts |
| `/api/eda` | GET | Summary stats, missing values, correlation matrix, outliers |
| `/api/insights` | GET | Executive business intelligence findings |
| `/api/predict` | GET | Scikit-Learn linear regression forecast & metrics |
| `/api/reports/pdf` | GET | ReportLab generated PDF file download |
| `/api/reports/csv` | GET | Download filtered CSV data export |
| `/api/admin/upload` | POST | Upload and activate new CSV dataset |
