import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO, StringIO

from flask import (
    Flask, render_template, request, jsonify, redirect, url_for, 
    session, flash, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

app = Flask(__name__)
app.secret_key = 'retail_analytics_super_secret_key_2026'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DEFAULT_CSV = os.path.join(BASE_DIR, 'retail_sales.csv')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Cache for dataframe to prevent re-reading on every hit
DF_CACHE = None
CACHE_FILE_PATH = None

# -------------------------------------------------------------------
# Database Initialization
# -------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Datasets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            is_active INTEGER DEFAULT 0,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create default admin user if not existing
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed_pw = generate_password_hash('admin123')
        cursor.execute("INSERT INTO users (username, password, role) VALUES ('admin', ?, 'admin')", (hashed_pw,))
    
    # Register default dataset if none exists
    cursor.execute("SELECT * FROM datasets WHERE filename = 'retail_sales.csv'")
    if not cursor.fetchone() and os.path.exists(DEFAULT_CSV):
        cursor.execute(
            "INSERT INTO datasets (filename, filepath, is_active) VALUES ('retail_sales.csv', ?, 1)",
            (DEFAULT_CSV,)
        )
        
    conn.commit()
    conn.close()

init_db()

# -------------------------------------------------------------------
# Data Engine & Helper Functions
# -------------------------------------------------------------------
def get_active_dataset_path():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT filepath FROM datasets WHERE is_active = 1 LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row and os.path.exists(row['filepath']):
        return row['filepath']
    return DEFAULT_CSV

def load_data(force_reload=False):
    global DF_CACHE, CACHE_FILE_PATH
    current_path = get_active_dataset_path()
    
    if DF_CACHE is not None and CACHE_FILE_PATH == current_path and not force_reload:
        return DF_CACHE.copy()
        
    if not os.path.exists(current_path):
        current_path = DEFAULT_CSV
        
    df = pd.read_csv(current_path)
    
    # Clean and parse columns
    df['Order Date'] = pd.to_datetime(df['Order Date'], errors='coerce')
    df['Ship Date'] = pd.to_datetime(df['Ship Date'], errors='coerce')
    
    # Numeric conversions
    for col in ['Sales', 'Quantity', 'Discount', 'Profit']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # Synthetic columns
    df['Year'] = df['Order Date'].dt.year.astype('Int64').astype(str)
    df['YearMonth'] = df['Order Date'].dt.strftime('%Y-%m')
    df['Month'] = df['Order Date'].dt.strftime('%b')
    df['MonthNum'] = df['Order Date'].dt.month
    
    DF_CACHE = df
    CACHE_FILE_PATH = current_path
    return df.copy()

def filter_dataframe(df, filters):
    filtered = df.copy()
    
    if not filters:
        return filtered
        
    # Date Range
    if filters.get('start_date'):
        filtered = filtered[filtered['Order Date'] >= pd.to_datetime(filters['start_date'])]
    if filters.get('end_date'):
        filtered = filtered[filtered['Order Date'] <= pd.to_datetime(filters['end_date'])]
        
    # Region
    regions = filters.get('region')
    if regions:
        if isinstance(regions, str):
            regions = [r.strip() for r in regions.split(',') if r.strip()]
        if regions and 'All' not in regions:
            filtered = filtered[filtered['Region'].isin(regions)]
            
    # State
    states = filters.get('state')
    if states:
        if isinstance(states, str):
            states = [s.strip() for s in states.split(',') if s.strip()]
        if states and 'All' not in states:
            filtered = filtered[filtered['State'].isin(states)]
            
    # Category
    categories = filters.get('category')
    if categories:
        if isinstance(categories, str):
            categories = [c.strip() for c in categories.split(',') if c.strip()]
        if categories and 'All' not in categories:
            filtered = filtered[filtered['Category'].isin(categories)]
            
    # Sub-Category
    sub_cats = filters.get('sub_category')
    if sub_cats:
        if isinstance(sub_cats, str):
            sub_cats = [sc.strip() for sc in sub_cats.split(',') if sc.strip()]
        if sub_cats and 'All' not in sub_cats:
            filtered = filtered[filtered['Sub-Category'].isin(sub_cats)]
            
    # Customer
    customers = filters.get('customer')
    if customers:
        if isinstance(customers, str):
            customers = [cust.strip() for cust in customers.split(',') if cust.strip()]
        if customers and 'All' not in customers:
            filtered = filtered[filtered['Customer Name'].isin(customers)]
            
    # Year
    years = filters.get('year')
    if years:
        if isinstance(years, str):
            years = [str(y).strip() for y in years.split(',') if str(y).strip()]
        if years and 'All' not in years:
            filtered = filtered[filtered['Year'].astype(str).isin(years)]
            
    return filtered

def get_filter_params_from_request():
    return {
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date'),
        'region': request.args.get('region'),
        'state': request.args.get('state'),
        'category': request.args.get('category'),
        'sub_category': request.args.get('sub_category'),
        'customer': request.args.get('customer'),
        'year': request.args.get('year')
    }

# -------------------------------------------------------------------
# Authentication Decorators
# -------------------------------------------------------------------
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin permissions required.', 'danger')
            return redirect(url_for('dashboard_view'))
        return f(*args, **kwargs)
    return decorated_function

# -------------------------------------------------------------------
# Page Routes
# -------------------------------------------------------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard_view'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username:
            flash('Please enter a username.', 'warning')
            return render_template('login.html')
            
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if not user:
            # Automatically create user if not exists so any username/password works!
            role = 'admin' if 'admin' in username.lower() else 'user'
            hashed_pw = generate_password_hash(password if password else 'password')
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, hashed_pw, role))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            
        conn.close()
        
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        flash(f'Welcome, {user["username"]}!', 'success')
        return redirect(url_for('dashboard_view'))
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_pw = request.form.get('confirm_password')
        
        if password != confirm_pw:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
            
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            flash('Username already exists. Please choose another.', 'warning')
            return render_template('register.html')
            
        hashed_pw = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'user')", (username, hashed_pw))
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard_view():
    return render_template('dashboard.html', active_page='dashboard')

@app.route('/eda')
@login_required
def eda_view():
    return render_template('eda.html', active_page='eda')

@app.route('/insights')
@login_required
def insights_view():
    return render_template('insights.html', active_page='insights')

@app.route('/prediction')
@login_required
def prediction_view():
    return render_template('prediction.html', active_page='prediction')

@app.route('/reports')
@login_required
def reports_view():
    return render_template('reports.html', active_page='reports')

@app.route('/admin')
@login_required
@admin_required
def admin_view():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM datasets ORDER BY uploaded_at DESC")
    datasets = cursor.fetchall()
    conn.close()
    return render_template('admin.html', active_page='admin', datasets=datasets)

# -------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------

@app.route('/api/filters/options')
@login_required
def filter_options():
    df = load_data()
    
    years = sorted([str(y) for y in df['Year'].dropna().unique() if str(y) != '<NA>'])
    regions = sorted([str(r) for r in df['Region'].dropna().unique()])
    states = sorted([str(s) for s in df['State'].dropna().unique()])
    categories = sorted([str(c) for c in df['Category'].dropna().unique()])
    sub_categories = sorted([str(sc) for sc in df['Sub-Category'].dropna().unique()])
    customers = sorted([str(cust) for cust in df['Customer Name'].dropna().unique()])
    
    min_date = df['Order Date'].min().strftime('%Y-%m-%d') if not df['Order Date'].empty else ''
    max_date = df['Order Date'].max().strftime('%Y-%m-%d') if not df['Order Date'].empty else ''
    
    return jsonify({
        'years': years,
        'regions': regions,
        'states': states,
        'categories': categories,
        'sub_categories': sub_categories,
        'customers': customers,
        'min_date': min_date,
        'max_date': max_date
    })

@app.route('/api/dashboard/kpis')
@login_required
def dashboard_kpis():
    df = load_data()
    filters = get_filter_params_from_request()
    filtered = filter_dataframe(df, filters)
    
    total_sales = float(filtered['Sales'].sum())
    total_profit = float(filtered['Profit'].sum())
    total_orders = int(filtered['Order ID'].nunique())
    total_quantity = int(filtered['Quantity'].sum())
    avg_order_value = float(total_sales / total_orders) if total_orders > 0 else 0.0
    profit_margin = float((total_profit / total_sales) * 100) if total_sales > 0 else 0.0
    avg_discount = float(filtered['Discount'].mean() * 100) if len(filtered) > 0 else 0.0
    
    return jsonify({
        'total_sales': round(total_sales, 2),
        'total_profit': round(total_profit, 2),
        'total_orders': total_orders,
        'total_quantity': total_quantity,
        'avg_order_value': round(avg_order_value, 2),
        'profit_margin': round(profit_margin, 2),
        'avg_discount': round(avg_discount, 2)
    })

@app.route('/api/dashboard/charts')
@login_required
def dashboard_charts():
    df = load_data()
    filters = get_filter_params_from_request()
    filtered = filter_dataframe(df, filters)
    
    if filtered.empty:
        return jsonify({'error': 'No data matches the selected filters.'}), 200

    # 1. Sales by Region
    reg_df = filtered.groupby('Region')[['Sales', 'Profit']].sum().reset_index()
    sales_by_region = {
        'labels': reg_df['Region'].tolist(),
        'sales': reg_df['Sales'].round(2).tolist(),
        'profit': reg_df['Profit'].round(2).tolist()
    }
    
    # 2. Sales by Category
    cat_df = filtered.groupby('Category')[['Sales', 'Profit', 'Quantity']].sum().reset_index()
    sales_by_category = {
        'labels': cat_df['Category'].tolist(),
        'sales': cat_df['Category'].map(filtered.groupby('Category')['Sales'].sum()).round(2).tolist()
    }
    
    # 3. Profit by Category
    profit_by_category = {
        'labels': cat_df['Category'].tolist(),
        'profit': cat_df['Profit'].round(2).tolist(),
        'sales': cat_df['Sales'].round(2).tolist()
    }
    
    # 4. Top 10 Products
    top_prod = filtered.groupby('Product Name')['Sales'].sum().nlargest(10).reset_index()
    top_10_products = {
        'labels': top_prod['Product Name'].tolist(),
        'sales': top_prod['Sales'].round(2).tolist()
    }
    
    # 5. Top 10 Customers
    top_cust = filtered.groupby('Customer Name')[['Sales', 'Profit']].sum().nlargest(10, 'Sales').reset_index()
    top_customers = {
        'labels': top_cust['Customer Name'].tolist(),
        'sales': top_cust['Sales'].round(2).tolist(),
        'profit': top_cust['Profit'].round(2).tolist()
    }
    
    # 6. Sales by State (Top 10)
    state_df = filtered.groupby('State')['Sales'].sum().nlargest(10).reset_index()
    sales_by_state = {
        'labels': state_df['State'].tolist(),
        'sales': state_df['State'].map(filtered.groupby('State')['Sales'].sum()).round(2).tolist()
    }
    
    # 7. Discount vs Profit Scatter Plot (Sampled if large)
    scatter_df = filtered[['Discount', 'Profit', 'Sales', 'Product Name', 'Category']].dropna()
    if len(scatter_df) > 300:
        scatter_df = scatter_df.sample(300, random_state=42)
        
    discount_vs_profit = [
        {
            'x': float(row['Discount'] * 100),
            'y': float(row['Profit']),
            'sales': float(row['Sales']),
            'product': str(row['Product Name']),
            'category': str(row['Category'])
        }
        for _, row in scatter_df.iterrows()
    ]
    
    # 8. Monthly Sales & Profit Trend Line Chart
    trend_df = filtered.groupby('YearMonth')[['Sales', 'Profit']].sum().reset_index().sort_values('YearMonth')
    monthly_trend = {
        'labels': trend_df['YearMonth'].tolist(),
        'sales': trend_df['Sales'].round(2).tolist(),
        'profit': trend_df['Profit'].round(2).tolist()
    }
    
    # 9. Category-wise Pie Chart (Sales & Quantity share)
    category_pie = {
        'labels': cat_df['Category'].tolist(),
        'sales': cat_df['Sales'].round(2).tolist(),
        'quantity': cat_df['Quantity'].astype(int).tolist()
    }
    
    # 10. Profit Heatmap (Category vs Region matrix)
    pivot_heatmap = filtered.pivot_table(index='Category', columns='Region', values='Profit', aggfunc='sum', fill_value=0)
    profit_heatmap = {
        'categories': pivot_heatmap.index.tolist(),
        'regions': pivot_heatmap.columns.tolist(),
        'values': pivot_heatmap.round(2).values.tolist()
    }
    
    return jsonify({
        'sales_by_region': sales_by_region,
        'sales_by_category': sales_by_category,
        'profit_by_category': profit_by_category,
        'top_10_products': top_10_products,
        'top_customers': top_customers,
        'sales_by_state': sales_by_state,
        'discount_vs_profit': discount_vs_profit,
        'monthly_trend': monthly_trend,
        'category_pie': category_pie,
        'profit_heatmap': profit_heatmap
    })

@app.route('/api/eda')
@login_required
def eda_data():
    df = load_data()
    filters = get_filter_params_from_request()
    filtered = filter_dataframe(df, filters)
    
    # Missing values
    missing_values = filtered.isnull().sum().to_dict()
    
    # Duplicate rows
    duplicate_count = int(filtered.duplicated().sum())
    
    # Data Types
    dtypes_dict = {col: str(dtype) for col, dtype in filtered.dtypes.items()}
    
    # Summary Statistics for numeric columns
    num_cols = ['Sales', 'Quantity', 'Discount', 'Profit']
    summary_df = filtered[num_cols].describe().T.reset_index()
    summary_stats = []
    for _, row in summary_df.iterrows():
        summary_stats.append({
            'column': row['index'],
            'count': int(row['count']),
            'mean': round(float(row['mean']), 2),
            'std': round(float(row['std']), 2),
            'min': round(float(row['min']), 2),
            'q25': round(float(row['25%']), 2),
            'q50': round(float(row['50%']), 2),
            'q75': round(float(row['75%']), 2),
            'max': round(float(row['max']), 2)
        })
        
    # Correlation Matrix
    corr_df = filtered[num_cols].corr()
    corr_matrix = {
        'columns': num_cols,
        'values': corr_df.round(3).values.tolist()
    }
    
    # Outlier Detection (IQR method)
    outliers = {}
    for col in num_cols:
        q1 = filtered[col].quantile(0.25)
        q3 = filtered[col].quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outlier_count = int(((filtered[col] < lower_bound) | (filtered[col] > upper_bound)).sum())
        outliers[col] = {
            'count': outlier_count,
            'percentage': round((outlier_count / len(filtered) * 100), 2) if len(filtered) > 0 else 0,
            'lower_bound': round(float(lower_bound), 2),
            'upper_bound': round(float(upper_bound), 2)
        }
        
    # Distribution histograms for Sales, Profit, Discount
    distributions = {}
    for col in ['Sales', 'Profit', 'Discount']:
        counts, bin_edges = np.histogram(filtered[col].dropna(), bins=10)
        bin_labels = [f"{round(bin_edges[i], 1)} - {round(bin_edges[i+1], 1)}" for i in range(len(counts))]
        distributions[col] = {
            'labels': bin_labels,
            'counts': counts.tolist()
        }

    return jsonify({
        'total_records': len(filtered),
        'total_columns': len(filtered.columns),
        'missing_values': missing_values,
        'duplicate_rows': duplicate_count,
        'data_types': dtypes_dict,
        'summary_stats': summary_stats,
        'correlation_matrix': corr_matrix,
        'outliers': outliers,
        'distributions': distributions
    })

@app.route('/api/insights')
@login_required
def generate_insights():
    df = load_data()
    filters = get_filter_params_from_request()
    filtered = filter_dataframe(df, filters)
    
    if filtered.empty:
        return jsonify({'error': 'No data available for current filters'}), 200

    # 1. Region Analysis
    reg_sales = filtered.groupby('Region')['Sales'].sum()
    reg_profit = filtered.groupby('Region')['Profit'].sum()
    highest_rev_region = reg_sales.idxmax() if not reg_sales.empty else 'N/A'
    highest_rev_val = float(reg_sales.max()) if not reg_sales.empty else 0.0
    
    lowest_profit_region = reg_profit.idxmin() if not reg_profit.empty else 'N/A'
    lowest_profit_val = float(reg_profit.min()) if not reg_profit.empty else 0.0

    # 2. Category Analysis
    cat_sales = filtered.groupby('Category')['Sales'].sum()
    cat_profit = filtered.groupby('Category')['Profit'].sum()
    best_cat = cat_sales.idxmax() if not cat_sales.empty else 'N/A'
    best_cat_sales = float(cat_sales.max()) if not cat_sales.empty else 0.0
    
    # 3. Most Profitable Products
    prod_profit = filtered.groupby('Product Name')['Profit'].sum().nlargest(3)
    top_products = [{'name': name, 'profit': round(float(val), 2)} for name, val in prod_profit.items()]
    
    # 4. Monthly Growth Percentage (Latest vs Previous Month)
    m_sales = filtered.groupby('YearMonth')['Sales'].sum().reset_index().sort_values('YearMonth')
    growth_pct = 0.0
    if len(m_sales) >= 2:
        latest = m_sales.iloc[-1]['Sales']
        prev = m_sales.iloc[-2]['Sales']
        if prev > 0:
            growth_pct = round(((latest - prev) / prev) * 100, 2)
            
    # 5. Top Customer
    cust_sales = filtered.groupby('Customer Name')['Sales'].sum()
    top_cust_name = cust_sales.idxmax() if not cust_sales.empty else 'N/A'
    top_cust_rev = float(cust_sales.max()) if not cust_sales.empty else 0.0

    # 6. Discount Impact Analysis
    high_disc = filtered[filtered['Discount'] >= 0.20]
    high_disc_profit = float(high_disc['Profit'].sum()) if not high_disc.empty else 0.0
    high_disc_count = len(high_disc)
    
    insights = [
        {
            'icon': 'fa-globe',
            'title': 'Highest Revenue Region',
            'value': f"{highest_rev_region} (${highest_rev_val:,.2f})",
            'detail': f"{highest_rev_region} leads in total sales revenue across the current filtered scope.",
            'type': 'success'
        },
        {
            'icon': 'fa-triangle-exclamation',
            'title': 'Lowest Profit Region',
            'value': f"{lowest_profit_region} (${lowest_profit_val:,.2f})",
            'detail': f"{lowest_profit_region} generated the lowest cumulative net profit and may require pricing adjustments.",
            'type': 'warning' if lowest_profit_val >= 0 else 'danger'
        },
        {
            'icon': 'fa-cart-shopping',
            'title': 'Best-Selling Category',
            'value': f"{best_cat} (${best_cat_sales:,.2f})",
            'detail': f"{best_cat} contributes the largest volume of sales revenue.",
            'type': 'info'
        },
        {
            'icon': 'fa-chart-line',
            'title': 'Latest MoM Sales Growth',
            'value': f"{growth_pct:+.2f}%",
            'detail': f"Sales trend changed by {growth_pct:+.2f}% compared to the prior month.",
            'type': 'success' if growth_pct >= 0 else 'danger'
        },
        {
            'icon': 'fa-user-tie',
            'title': 'Top Customer',
            'value': f"{top_cust_name} (${top_cust_rev:,.2f})",
            'detail': f"Accounted for the highest individual purchase value.",
            'type': 'primary'
        },
        {
            'icon': 'fa-tags',
            'title': 'Discount Impact Warning',
            'value': f"{high_disc_count} Orders (≥20% Disc)",
            'detail': f"High discount orders yielded ${high_disc_profit:,.2f} total profit. Heavy discounting reduces margins.",
            'type': 'warning'
        }
    ]
    
    return jsonify({
        'insights': insights,
        'top_products': top_products
    })

@app.route('/api/predict')
@login_required
def predict_sales():
    df = load_data()
    filters = get_filter_params_from_request()
    filtered = filter_dataframe(df, filters)
    
    # Monthly aggregate
    monthly = filtered.groupby('YearMonth')[['Sales', 'Profit']].sum().reset_index().sort_values('YearMonth')
    
    if len(monthly) < 4:
        return jsonify({'error': 'Insufficient historical data points (minimum 4 months required for prediction).'}), 400
        
    monthly['MonthIdx'] = np.arange(len(monthly))
    
    X = monthly[['MonthIdx']].values
    y_sales = monthly['Sales'].values
    
    # Fit Linear Regression Model
    model = LinearRegression()
    model.fit(X, y_sales)
    
    y_pred_hist = model.predict(X)
    
    # Model evaluation metrics
    r2 = round(float(r2_score(y_sales, y_pred_hist)), 3)
    mae = round(float(mean_absolute_error(y_sales, y_pred_hist)), 2)
    rmse = round(float(np.sqrt(mean_squared_error(y_sales, y_pred_hist))), 2)
    
    # Forecast future months
    horizon = int(request.args.get('months', 6))
    last_date = datetime.strptime(monthly['YearMonth'].iloc[-1], '%Y-%m')
    
    future_dates = []
    for i in range(1, horizon + 1):
        # Add months
        month_val = (last_date.month + i - 1) % 12 + 1
        year_val = last_date.year + (last_date.month + i - 1) // 12
        future_dates.append(f"{year_val:04d}-{month_val:02d}")
        
    future_idx = np.arange(len(monthly), len(monthly) + horizon).reshape(-1, 1)
    future_pred = model.predict(future_idx)
    future_pred = np.maximum(future_pred, 0)  # Prevent negative sales
    
    return jsonify({
        'historical': {
            'labels': monthly['YearMonth'].tolist(),
            'actual_sales': monthly['Sales'].round(2).tolist(),
            'fitted_sales': np.round(y_pred_hist, 2).tolist()
        },
        'forecast': {
            'labels': future_dates,
            'predicted_sales': np.round(future_pred, 2).tolist()
        },
        'metrics': {
            'r2_score': r2,
            'mae': mae,
            'rmse': rmse,
            'slope': round(float(model.coef_[0]), 2),
            'intercept': round(float(model.intercept_), 2)
        }
    })

# -------------------------------------------------------------------
# Reports & PDF Generator
# -------------------------------------------------------------------
@app.route('/api/reports/csv')
@login_required
def export_csv():
    df = load_data()
    filters = get_filter_params_from_request()
    filtered = filter_dataframe(df, filters)
    
    buffer = StringIO()
    filtered.to_csv(buffer, index=False)
    buffer.seek(0)
    
    return send_file(
        BytesIO(buffer.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'retail_sales_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/api/reports/pdf')
@login_required
def export_pdf():
    df = load_data()
    filters = get_filter_params_from_request()
    filtered = filter_dataframe(df, filters)
    
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1e1b4b'),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=15
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#4f46e5'),
        spaceBefore=12,
        spaceAfter=8
    )
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['BodyText'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )
    
    elements = []
    
    # Title & Header
    elements.append(Paragraph("Retail Sales Analytics Executive Report", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y - %H:%M')} | User: {session.get('username', 'Admin')}", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=15))
    
    # Executive Summary KPIs Table
    elements.append(Paragraph("1. Key Performance Summary", heading_style))
    
    total_sales = filtered['Sales'].sum()
    total_profit = filtered['Profit'].sum()
    total_orders = filtered['Order ID'].nunique()
    avg_order = total_sales / total_orders if total_orders > 0 else 0
    margin = (total_profit / total_sales * 100) if total_sales > 0 else 0
    
    kpi_data = [
        ['Metric', 'Value', 'Metric', 'Value'],
        ['Total Revenue', f"${total_sales:,.2f}", 'Total Orders', f"{total_orders:,}"],
        ['Net Profit', f"${total_profit:,.2f}", 'Avg Order Value', f"${avg_order:,.2f}"],
        ['Profit Margin', f"{margin:.2f}%", 'Total Records', f"{len(filtered):,}"]
    ]
    
    kpi_table = Table(kpi_data, colWidths=[120, 130, 120, 130])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 15))
    
    # Regional Breakdown Table
    elements.append(Paragraph("2. Regional Performance", heading_style))
    reg_df = filtered.groupby('Region').agg(
        Sales=('Sales', 'sum'),
        Profit=('Profit', 'sum'),
        Orders=('Order ID', 'nunique')
    ).reset_index()
    
    reg_data = [['Region', 'Sales ($)', 'Profit ($)', 'Orders', 'Margin (%)']]
    for _, row in reg_df.iterrows():
        reg_margin = (row['Profit'] / row['Sales'] * 100) if row['Sales'] > 0 else 0
        reg_data.append([
            row['Region'],
            f"${row['Sales']:,.2f}",
            f"${row['Profit']:,.2f}",
            f"{row['Orders']:,}",
            f"{reg_margin:.2f}%"
        ])
        
    reg_table = Table(reg_data, colWidths=[100, 110, 110, 80, 100])
    reg_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    elements.append(reg_table)
    elements.append(Spacer(1, 15))
    
    # Category Performance Table
    elements.append(Paragraph("3. Category Breakdown", heading_style))
    cat_df = filtered.groupby('Category').agg(
        Sales=('Sales', 'sum'),
        Profit=('Profit', 'sum'),
        Quantity=('Quantity', 'sum')
    ).reset_index()
    
    cat_data = [['Category', 'Sales ($)', 'Profit ($)', 'Quantity Sold']]
    for _, row in cat_df.iterrows():
        cat_data.append([
            row['Category'],
            f"${row['Sales']:,.2f}",
            f"${row['Profit']:,.2f}",
            f"{row['Quantity']:,}"
        ])
        
    cat_table = Table(cat_data, colWidths=[140, 120, 120, 120])
    cat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f766e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    elements.append(cat_table)
    elements.append(Spacer(1, 15))
    
    # Top 5 Products
    elements.append(Paragraph("4. Top 5 Best-Selling Products", heading_style))
    top_p = filtered.groupby(['Product Name', 'Category']).agg(Sales=('Sales', 'sum'), Profit=('Profit', 'sum')).nlargest(5, 'Sales').reset_index()
    top_p_data = [['Product Name', 'Category', 'Sales ($)', 'Profit ($)']]
    for _, row in top_p.iterrows():
        top_p_data.append([
            Paragraph(str(row['Product Name'])[:35], body_style),
            row['Category'],
            f"${row['Sales']:,.2f}",
            f"${row['Profit']:,.2f}"
        ])
    top_p_table = Table(top_p_data, colWidths=[200, 110, 95, 95])
    top_p_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    elements.append(top_p_table)

    doc.build(elements)
    pdf_buffer.seek(0)
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'retail_sales_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    )

# -------------------------------------------------------------------
# Admin Dataset Management Endpoints
# -------------------------------------------------------------------
@app.route('/api/admin/upload', methods=['POST'])
@login_required
@admin_required
def admin_upload_dataset():
    if 'file' not in request.files:
        flash('No file part in request.', 'danger')
        return redirect(url_for('admin_view'))
        
    file = request.files['file']
    if file.filename == '':
        flash('No selected file.', 'danger')
        return redirect(url_for('admin_view'))
        
    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{int(datetime.now().timestamp())}_{filename}")
        file.save(save_path)
        
        # Verify CSV readability and required columns
        try:
            temp_df = pd.read_csv(save_path, nrows=5)
            req_cols = ['Order ID', 'Order Date', 'Sales', 'Profit']
            missing = [c for c in req_cols if c not in temp_df.columns]
            if missing:
                os.remove(save_path)
                flash(f'Dataset missing required columns: {", ".join(missing)}', 'danger')
                return redirect(url_for('admin_view'))
        except Exception as e:
            if os.path.exists(save_path):
                os.remove(save_path)
            flash(f'Failed to parse uploaded CSV: {str(e)}', 'danger')
            return redirect(url_for('admin_view'))

        # Deactivate previous active dataset if replacing
        set_active = request.form.get('set_active') == '1'
        conn = get_db()
        cursor = conn.cursor()
        
        if set_active:
            cursor.execute("UPDATE datasets SET is_active = 0")
            
        cursor.execute(
            "INSERT INTO datasets (filename, filepath, is_active) VALUES (?, ?, ?)",
            (filename, save_path, 1 if set_active else 0)
        )
        conn.commit()
        conn.close()
        
        load_data(force_reload=True)
        flash(f'Successfully uploaded dataset "{filename}".', 'success')
    else:
        flash('Only CSV files are supported.', 'warning')
        
    return redirect(url_for('admin_view'))

@app.route('/api/admin/activate/<int:dataset_id>', methods=['POST'])
@login_required
@admin_required
def admin_activate_dataset(dataset_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE datasets SET is_active = 0")
    cursor.execute("UPDATE datasets SET is_active = 1 WHERE id = ?", (dataset_id,))
    conn.commit()
    conn.close()
    
    load_data(force_reload=True)
    flash('Active dataset updated successfully.', 'success')
    return redirect(url_for('admin_view'))

@app.route('/api/admin/delete/<int:dataset_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_dataset(dataset_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,))
    ds = cursor.fetchone()
    
    if ds:
        if ds['is_active']:
            flash('Cannot delete the currently active dataset. Activate another dataset first.', 'warning')
            conn.close()
            return redirect(url_for('admin_view'))
            
        if os.path.exists(ds['filepath']) and ds['filepath'] != DEFAULT_CSV:
            try:
                os.remove(ds['filepath'])
            except Exception:
                pass
                
        cursor.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
        conn.commit()
        flash('Dataset deleted successfully.', 'info')
    conn.close()
    return redirect(url_for('admin_view'))

@app.route('/api/admin/refresh', methods=['POST'])
@login_required
@admin_required
def admin_refresh_cache():
    load_data(force_reload=True)
    flash('Dashboard cache and indexes successfully refreshed.', 'success')
    return redirect(url_for('admin_view'))

# -------------------------------------------------------------------
# Error Handlers
# -------------------------------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', page_error="404 - Page Not Found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', page_error="500 - Internal Server Error"), 500

if __name__ == '__main__':
    print("Starting Retail Sales Analytics Dashboard Server on http://127.0.0.1:5000 ...")
    app.run(debug=True, port=5000)
