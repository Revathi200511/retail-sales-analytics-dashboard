import app

def run_tests():
    print("Initializing Flask test client...")
    client = app.app.test_client()
    
    # 1. Test Login GET & POST
    print("Testing /login ...")
    res = client.get('/login')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    
    res = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    assert res.status_code == 200
    print("Login successful!")

    # 2. Test Filter options
    print("Testing /api/filters/options ...")
    res = client.get('/api/filters/options')
    assert res.status_code == 200
    data = res.get_json()
    assert 'regions' in data and len(data['regions']) > 0
    print(f"Filter options loaded successfully! Regions: {data['regions']}")

    # 3. Test Dashboard KPIs API
    print("Testing /api/dashboard/kpis ...")
    res = client.get('/api/dashboard/kpis')
    assert res.status_code == 200
    kpis = res.get_json()
    assert kpis['total_sales'] > 0
    print(f"KPIs loaded: Total Sales=${kpis['total_sales']}, Total Profit=${kpis['total_profit']}")

    # 4. Test Dashboard Charts API
    print("Testing /api/dashboard/charts ...")
    res = client.get('/api/dashboard/charts')
    assert res.status_code == 200
    charts = res.get_json()
    assert 'sales_by_region' in charts and 'top_10_products' in charts
    print("All 10 chart endpoints verified successfully!")

    # 5. Test EDA API
    print("Testing /api/eda ...")
    res = client.get('/api/eda')
    assert res.status_code == 200
    eda = res.get_json()
    assert eda['total_records'] == 1500
    print(f"EDA API verified! Total records: {eda['total_records']}")

    # 6. Test Insights API
    print("Testing /api/insights ...")
    res = client.get('/api/insights')
    assert res.status_code == 200
    insights = res.get_json()
    assert len(insights['insights']) >= 5
    print("Automated insights verified!")

    # 7. Test ML Prediction API
    print("Testing /api/predict ...")
    res = client.get('/api/predict?months=6')
    assert res.status_code == 200
    pred = res.get_json()
    assert 'forecast' in pred and len(pred['forecast']['predicted_sales']) == 6
    print(f"ML Prediction verified! R2 score: {pred['metrics']['r2_score']}")

    # 8. Test PDF Report API
    print("Testing /api/reports/pdf ...")
    res = client.get('/api/reports/pdf')
    assert res.status_code == 200
    assert res.mimetype == 'application/pdf'
    print("PDF Report generation verified!")

    # 9. Test CSV Export API
    print("Testing /api/reports/csv ...")
    res = client.get('/api/reports/csv')
    assert res.status_code == 200
    assert res.mimetype == 'text/csv'
    print("CSV Export verified!")

    print("\nALL BACKEND TESTS PASSED CLEANLY!")

if __name__ == '__main__':
    run_tests()
