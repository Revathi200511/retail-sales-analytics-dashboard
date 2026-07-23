import csv
import random
from datetime import datetime, timedelta

# Seed for reproducibility
random.seed(42)

regions_states = {
    'West': ['California', 'Washington', 'Oregon', 'Arizona', 'Nevada'],
    'East': ['New York', 'Pennsylvania', 'Massachusetts', 'New Jersey', 'Connecticut'],
    'Central': ['Texas', 'Illinois', 'Ohio', 'Michigan', 'Wisconsin'],
    'South': ['Florida', 'North Carolina', 'Georgia', 'Virginia', 'Tennessee']
}

catalog = {
    'Technology': {
        'Laptops': [('MacBook Pro 16"', 1999.99), ('Dell XPS 15', 1499.99), ('Lenovo ThinkPad X1', 1299.99), ('HP Spectre x360', 1199.99)],
        'Smartphones': [('iPhone 15 Pro', 999.99), ('Samsung Galaxy S24', 899.99), ('Google Pixel 8', 699.99), ('OnePlus 12', 799.99)],
        'Accessories': [('Logitech MX Master 3S', 99.99), ('Anker USB-C Hub', 49.99), ('Apple AirPods Pro', 249.99), ('Sony WH-1000XM5', 399.99)],
        'Monitors': [('Dell UltraSharp 27"', 499.99), ('LG UltraGear 34"', 699.99), ('Samsung Odyssey G7', 599.99)]
    },
    'Office Supplies': {
        'Paper': [('Multipurpose Copy Paper 500 Sheets', 12.99), ('Premium Heavyweight Cardstock', 19.99), ('Recycled Printer Paper', 14.49)],
        'Binders': [('Heavy-Duty 3-Ring Binder 2"', 8.99), ('Presentation Binder 1"', 5.49), ('Zipper Binder 3"', 24.99)],
        'Storage': [('Plastic Storage Tote 10 Gal', 15.99), ('Desktop File Organizer', 22.99), ('Archive Storage Boxes 10-Pack', 34.99)],
        'Art & Writing': [('Gel Pen Set 12-Pack', 14.99), ('Dry Erase Markers 8-Pack', 11.99), ('Highlighter Pack', 7.99)]
    },
    'Furniture': {
        'Chairs': [('Ergonomic Executive Mesh Chair', 299.99), ('Gaming Chair High-Back', 249.99), ('Task Chair Armless', 119.99)],
        'Tables': [('Adjustable Standing Desk 55"', 450.00), ('Conference Table 8-ft', 799.99), ('Side Table Wooden', 89.99)],
        'Bookcases': [('5-Shelf Wooden Bookcase', 189.99), ('3-Tier Industrial Metal Shelf', 139.99), ('Corner Bookshelf', 99.99)],
        'Furnishings': [('LED Desk Lamp with Wireless Charger', 45.99), ('Anti-Fatigue Floor Mat', 39.99), ('Acoustic Desk Divider', 79.99)]
    }
}

customers = [
    "Emily Johnson", "Michael Smith", "David Brown", "Sarah Davis", "James Wilson",
    "Jessica Taylor", "Christopher Anderson", "Amanda Thomas", "Matthew Jackson", "Ashley White",
    "Daniel Harris", "Stephanie Martin", "Robert Thompson", "Nicole Garcia", "Brian Martinez",
    "Elizabeth Robinson", "William Clark", "Megan Rodriguez", "Joseph Lewis", "Jennifer Lee",
    "Anthony Walker", "Rachel Hall", "Charles Allen", "Samantha Young", "Thomas Hernandez",
    "Patricia King", "Steven Wright", "Linda Lopez", "Paul Hill", "Barbara Scott",
    "Mark Green", "Laura Adams", "Donald Baker", "Kimberly Gonzalez", "George Nelson",
    "Edward Carter", "Helen Mitchell", "Kevin Perez", "Donna Roberts", "Jason Turner",
    "Brian Phillips", "Carol Campbell", "Ronald Parker", "Michelle Evans", "Timothy Edwards",
    "Laura Collins", "Jason Stewart", "Sarah Sanchez", "Jeffrey Morris", "Amy Rogers"
]

discounts_pool = [0.0, 0.0, 0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40]

start_date = datetime(2023, 1, 1)
end_date = datetime(2026, 6, 30)
days_range = (end_date - start_date).days

rows = []
order_counter = 10001

for i in range(1500):
    order_id = f"CA-{random.randint(2023, 2026)}-{order_counter}"
    order_counter += 1
    
    # Order date biased slightly over time to show growth trend
    days_offset = int(random.triangular(0, days_range, days_range * 0.7))
    order_dt = start_date + timedelta(days=days_offset)
    ship_dt = order_dt + timedelta(days=random.randint(1, 5))
    
    customer = random.choice(customers)
    region = random.choice(list(regions_states.keys()))
    state = random.choice(regions_states[region])
    
    category = random.choice(list(catalog.keys()))
    sub_cat = random.choice(list(catalog[category].keys()))
    product_name, unit_price = random.choice(catalog[category][sub_cat])
    
    quantity = random.choices([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], weights=[25, 25, 20, 10, 8, 5, 3, 2, 1, 1])[0]
    discount = random.choice(discounts_pool)
    
    # Calculate Sales and Profit
    gross_sales = unit_price * quantity
    actual_sales = round(gross_sales * (1 - discount), 2)
    
    # Base cost is 50-70% of unit price
    cost_margin = random.uniform(0.52, 0.68)
    base_cost = gross_sales * cost_margin
    profit = round(actual_sales - base_cost, 2)
    
    rows.append({
        'Order ID': order_id,
        'Order Date': order_dt.strftime('%Y-%m-%d'),
        'Ship Date': ship_dt.strftime('%Y-%m-%d'),
        'Customer Name': customer,
        'Region': region,
        'State': state,
        'Category': category,
        'Sub-Category': sub_cat,
        'Product Name': product_name,
        'Sales': actual_sales,
        'Quantity': quantity,
        'Discount': discount,
        'Profit': profit
    })

# Write CSV
fieldnames = ['Order ID', 'Order Date', 'Ship Date', 'Customer Name', 'Region', 'State', 
              'Category', 'Sub-Category', 'Product Name', 'Sales', 'Quantity', 'Discount', 'Profit']

with open('retail_sales.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Successfully generated retail_sales.csv with {len(rows)} records.")
