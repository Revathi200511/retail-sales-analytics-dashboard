/* ==========================================================================
   Retail Sales Analytics Dashboard - Machine Learning Sales Prediction Controller
   ========================================================================== */

let predChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('predictionPage')) return;

    fetchPredictionData();

    const horizonSelect = document.getElementById('forecastHorizon');
    if (horizonSelect) {
        horizonSelect.addEventListener('change', fetchPredictionData);
    }

    window.addEventListener('themeChanged', fetchPredictionData);
});

async function fetchPredictionData() {
    const horizon = document.getElementById('forecastHorizon') ? document.getElementById('forecastHorizon').value : 6;
    const query = getFilterQueryParams();
    
    try {
        const response = await fetch(`/api/predict?months=${horizon}&${query}`);
        const data = await response.json();
        
        if (data.error) {
            showToast(data.error, 'warning');
            return;
        }

        renderPredictionMetrics(data.metrics);
        renderPredictionChart(data);
    } catch (err) {
        console.error('Failed to load prediction data:', err);
    }
}

function renderPredictionMetrics(metrics) {
    const r2Elem = document.getElementById('metricR2');
    const maeElem = document.getElementById('metricMAE');
    const rmseElem = document.getElementById('metricRMSE');
    const slopeElem = document.getElementById('metricSlope');

    if (r2Elem) r2Elem.textContent = metrics.r2_score;
    if (maeElem) maeElem.textContent = `$${metrics.mae.toLocaleString()}`;
    if (rmseElem) rmseElem.textContent = `$${metrics.rmse.toLocaleString()}`;
    if (slopeElem) slopeElem.textContent = `$${metrics.slope.toLocaleString()} / mo`;
}

function renderPredictionChart(data) {
    const ctx = document.getElementById('chartSalesPrediction');
    if (!ctx) return;

    const theme = getChartThemeColors();

    const histLabels = data.historical.labels;
    const futureLabels = data.forecast.labels;
    const allLabels = [...histLabels, ...futureLabels];

    // Align historical actuals (padded with nulls for future)
    const actualData = [...data.historical.actual_sales, ...Array(futureLabels.length).fill(null)];

    // Align fitted linear trend (connected to forecast)
    const lastFitted = data.historical.fitted_sales[data.historical.fitted_sales.length - 1];
    const forecastWithBridge = [lastFitted, ...data.forecast.predicted_sales];
    
    const fittedData = [...data.historical.fitted_sales, ...Array(futureLabels.length).fill(null)];
    
    // Forecast data array padded with nulls for history except bridge index
    const forecastData = [...Array(histLabels.length - 1).fill(null), ...forecastWithBridge];

    if (predChartInstance) {
        predChartInstance.destroy();
    }

    predChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allLabels,
            datasets: [
                {
                    label: 'Historical Actual Sales ($)',
                    data: actualData,
                    borderColor: theme.primary,
                    backgroundColor: 'rgba(79, 70, 229, 0.15)',
                    borderWidth: 3,
                    fill: false,
                    tension: 0.2
                },
                {
                    label: 'Regression Fit Line ($)',
                    data: fittedData,
                    borderColor: theme.info,
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0
                },
                {
                    label: 'Predicted Future Sales ($)',
                    data: forecastData,
                    borderColor: theme.success,
                    backgroundColor: 'rgba(16, 185, 129, 0.2)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.35,
                    pointStyle: 'circle',
                    pointRadius: 5
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top', labels: { color: theme.textColor } },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: $${ctx.raw ? ctx.raw.toLocaleString() : 'N/A'}`
                    }
                }
            },
            scales: {
                x: { ticks: { color: theme.textColor }, grid: { color: theme.gridColor } },
                y: { ticks: { color: theme.textColor }, grid: { color: theme.gridColor } }
            }
        }
    });
}
