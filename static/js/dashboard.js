/* ==========================================================================
   Retail Sales Analytics Dashboard - Dashboard Controller & Interactive Charts
   ========================================================================== */

let chartInstances = {};

document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('dashboardPage')) return;
    
    initFilterOptions();
    fetchDashboardData();

    // Reset Filters Button
    const resetBtn = document.getElementById('resetFiltersBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            const filterIds = ['startDate', 'endDate', 'filterRegion', 'filterState', 'filterCategory', 'filterSubCategory', 'filterCustomer', 'filterYear'];
            filterIds.forEach(id => {
                const elem = document.getElementById(id);
                if (elem) elem.value = 'All';
            });
            fetchDashboardData();
        });
    }

    // Filter Change Listeners
    const filterInputs = document.querySelectorAll('.filter-input');
    filterInputs.forEach(input => {
        input.addEventListener('change', () => {
            fetchDashboardData();
        });
    });

    // Re-render charts on theme change
    window.addEventListener('themeChanged', () => {
        fetchDashboardData();
    });
});

// Fetch Filter Dropdown Options
async function initFilterOptions() {
    try {
        const response = await fetch('/api/filters/options');
        const data = await response.json();

        populateSelect('filterRegion', data.regions);
        populateSelect('filterState', data.states);
        populateSelect('filterCategory', data.categories);
        populateSelect('filterSubCategory', data.sub_categories);
        populateSelect('filterCustomer', data.customers);
        populateSelect('filterYear', data.years);

        if (data.min_date && document.getElementById('startDate')) {
            document.getElementById('startDate').min = data.min_date;
            document.getElementById('startDate').max = data.max_date;
        }
        if (data.max_date && document.getElementById('endDate')) {
            document.getElementById('endDate').min = data.min_date;
            document.getElementById('endDate').max = data.max_date;
        }
    } catch (err) {
        console.error('Failed to load filter options:', err);
    }
}

function populateSelect(elemId, items) {
    const select = document.getElementById(elemId);
    if (!select) return;
    select.innerHTML = '<option value="All">All</option>';
    items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item;
        opt.textContent = item;
        select.appendChild(opt);
    });
}

// Fetch KPIs and Charts Data
async function fetchDashboardData() {
    const query = getFilterQueryParams();
    
    // 1. Fetch KPIs
    try {
        const kpiRes = await fetch(`/api/dashboard/kpis?${query}`);
        const kpiData = await kpiRes.json();
        updateKPICards(kpiData);
    } catch (err) {
        console.error('Failed to load KPIs:', err);
    }

    // 2. Fetch Charts
    try {
        const chartRes = await fetch(`/api/dashboard/charts?${query}`);
        const chartData = await chartRes.json();
        renderAllCharts(chartData);
    } catch (err) {
        console.error('Failed to load Charts:', err);
    }
}

function updateKPICards(data) {
    animateCounter('kpiTotalSales', data.total_sales, '$');
    animateCounter('kpiTotalProfit', data.total_profit, '$');
    animateCounter('kpiTotalOrders', data.total_orders, '');
    animateCounter('kpiAvgOrderValue', data.avg_order_value, '$');
    animateCounter('kpiProfitMargin', data.profit_margin, '', '%');
}

function animateCounter(elemId, targetValue, prefix = '', suffix = '') {
    const elem = document.getElementById(elemId);
    if (!elem) return;

    let start = 0;
    const duration = 800;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const currentVal = start + (targetValue - start) * progress;

        if (prefix === '$') {
            elem.textContent = `${prefix}${currentVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${suffix}`;
        } else {
            elem.textContent = `${prefix}${currentVal.toLocaleString('en-US', { maximumFractionDigits: 1 })}${suffix}`;
        }

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    requestAnimationFrame(update);
}

// Render All 10 Interactive Charts
function renderAllCharts(data) {
    if (!data || data.error) return;

    const theme = getChartThemeColors();

    // 1. Sales by Region Chart
    renderChart('chartSalesByRegion', {
        type: 'doughnut',
        data: {
            labels: data.sales_by_region.labels,
            datasets: [{
                data: data.sales_by_region.sales,
                backgroundColor: theme.palette,
                borderWidth: 2,
                borderColor: theme.bgCard
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { color: theme.textColor } }
            }
        }
    });

    // 2. Sales by Category
    renderChart('chartSalesByCategory', {
        type: 'bar',
        data: {
            labels: data.sales_by_category.labels,
            datasets: [{
                label: 'Sales ($)',
                data: data.sales_by_category.sales,
                backgroundColor: theme.primary,
                borderRadius: 6
            }]
        },
        options: createBarOptions(theme)
    });

    // 3. Profit by Category (Grouped Bar)
    renderChart('chartProfitByCategory', {
        type: 'bar',
        data: {
            labels: data.profit_by_category.labels,
            datasets: [
                {
                    label: 'Sales ($)',
                    data: data.profit_by_category.sales,
                    backgroundColor: theme.info,
                    borderRadius: 6
                },
                {
                    label: 'Profit ($)',
                    data: data.profit_by_category.profit,
                    backgroundColor: theme.success,
                    borderRadius: 6
                }
            ]
        },
        options: createBarOptions(theme)
    });

    // 4. Top 10 Products (Horizontal Bar)
    renderChart('chartTop10Products', {
        type: 'bar',
        data: {
            labels: data.top_10_products.labels.map(l => l.length > 25 ? l.substring(0, 25) + '...' : l),
            datasets: [{
                label: 'Sales ($)',
                data: data.top_10_products.sales,
                backgroundColor: theme.purple,
                borderRadius: 6
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: (items) => data.top_10_products.labels[items[0].dataIndex]
                    }
                }
            },
            scales: {
                x: { ticks: { color: theme.textColor }, grid: { color: theme.gridColor } },
                y: { ticks: { color: theme.textColor }, grid: { display: false } }
            }
        }
    });

    // 5. Top Customers
    renderChart('chartTopCustomers', {
        type: 'bar',
        data: {
            labels: data.top_customers.labels,
            datasets: [{
                label: 'Total Revenue ($)',
                data: data.top_customers.sales,
                backgroundColor: theme.palette[0],
                borderRadius: 6
            }]
        },
        options: createBarOptions(theme)
    });

    // 6. Sales by State
    renderChart('chartSalesByState', {
        type: 'bar',
        data: {
            labels: data.sales_by_state.labels,
            datasets: [{
                label: 'Sales ($)',
                data: data.sales_by_state.sales,
                backgroundColor: theme.palette[3],
                borderRadius: 6
            }]
        },
        options: createBarOptions(theme)
    });

    // 7. Discount vs Profit Scatter Plot (Plotly.js)
    renderPlotlyScatter('chartDiscountVsProfit', data.discount_vs_profit, theme);

    // 8. Monthly Sales Line Chart
    renderChart('chartMonthlySalesLine', {
        type: 'line',
        data: {
            labels: data.monthly_trend.labels,
            datasets: [
                {
                    label: 'Sales ($)',
                    data: data.monthly_trend.sales,
                    borderColor: theme.primary,
                    backgroundColor: 'rgba(79, 70, 229, 0.1)',
                    fill: true,
                    tension: 0.35,
                    borderWidth: 3
                },
                {
                    label: 'Profit ($)',
                    data: data.monthly_trend.profit,
                    borderColor: theme.success,
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.35,
                    borderWidth: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top', labels: { color: theme.textColor } }
            },
            scales: {
                x: { ticks: { color: theme.textColor }, grid: { color: theme.gridColor } },
                y: { ticks: { color: theme.textColor }, grid: { color: theme.gridColor } }
            }
        }
    });

    // 9. Category-wise Pie Chart
    renderChart('chartCategoryPie', {
        type: 'pie',
        data: {
            labels: data.category_pie.labels,
            datasets: [{
                data: data.category_pie.sales,
                backgroundColor: [theme.primary, theme.success, theme.warning, theme.purple],
                borderWidth: 2,
                borderColor: theme.bgCard
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { color: theme.textColor } }
            }
        }
    });

    // 10. Profit Heatmap (Plotly.js)
    renderPlotlyHeatmap('chartProfitHeatmap', data.profit_heatmap, theme);
}

function renderChart(canvasId, config) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }
    chartInstances[canvasId] = new Chart(ctx, config);
}

function createBarOptions(theme) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { labels: { color: theme.textColor } }
        },
        scales: {
            x: { ticks: { color: theme.textColor }, grid: { display: false } },
            y: { ticks: { color: theme.textColor }, grid: { color: theme.gridColor } }
        }
    };
}

function renderPlotlyScatter(elemId, points, theme) {
    const elem = document.getElementById(elemId);
    if (!elem) return;

    const x = points.map(p => p.x);
    const y = points.map(p => p.y);
    const text = points.map(p => `${p.product}<br>Sales: $${p.sales}`);

    const trace = {
        x: x,
        y: y,
        mode: 'markers',
        type: 'scatter',
        text: text,
        marker: {
            size: 10,
            color: y,
            colorscale: 'Viridis',
            showscale: true,
            colorbar: { tickfont: { color: theme.textColor } }
        }
    };

    const layout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        margin: { l: 50, r: 20, t: 20, b: 50 },
        xaxis: { title: 'Discount (%)', color: theme.textColor, gridcolor: theme.gridColor },
        yaxis: { title: 'Profit ($)', color: theme.textColor, gridcolor: theme.gridColor }
    };

    Plotly.newPlot(elemId, [trace], layout, { responsive: true, displayModeBar: false });
}

function renderPlotlyHeatmap(elemId, heatmapData, theme) {
    const elem = document.getElementById(elemId);
    if (!elem) return;

    const trace = {
        z: heatmapData.values,
        x: heatmapData.regions,
        y: heatmapData.categories,
        type: 'heatmap',
        colorscale: 'RdBu',
        reversescale: true,
        colorbar: { tickfont: { color: theme.textColor } }
    };

    const layout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        margin: { l: 120, r: 20, t: 20, b: 50 },
        xaxis: { color: theme.textColor, gridcolor: theme.gridColor },
        yaxis: { color: theme.textColor, gridcolor: theme.gridColor }
    };

    Plotly.newPlot(elemId, [trace], layout, { responsive: true, displayModeBar: false });
}
