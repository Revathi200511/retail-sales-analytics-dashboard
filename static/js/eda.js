/* ==========================================================================
   Retail Sales Analytics Dashboard - EDA Controller & Visualizations
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('edaPage')) return;
    
    fetchEDAData();

    window.addEventListener('themeChanged', () => {
        fetchEDAData();
    });
});

async function fetchEDAData() {
    const query = getFilterQueryParams();
    try {
        const response = await fetch(`/api/eda?${query}`);
        const data = await response.json();
        renderEDAData(data);
    } catch (err) {
        console.error('Failed to load EDA data:', err);
    }
}

function renderEDAData(data) {
    const theme = getChartThemeColors();

    // 1. Data Quality Cards
    const recordsElem = document.getElementById('edaTotalRecords');
    const colsElem = document.getElementById('edaTotalCols');
    const dupesElem = document.getElementById('edaDuplicateRows');
    const missingElem = document.getElementById('edaMissingValues');

    if (recordsElem) recordsElem.textContent = data.total_records.toLocaleString();
    if (colsElem) colsElem.textContent = data.total_columns;
    if (dupesElem) dupesElem.textContent = data.duplicate_rows;

    let totalMissing = 0;
    Object.values(data.missing_values).forEach(val => totalMissing += val);
    if (missingElem) missingElem.textContent = totalMissing;

    // 2. Summary Statistics Table
    const statsBody = document.getElementById('edaStatsTableBody');
    if (statsBody) {
        statsBody.innerHTML = '';
        data.summary_stats.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${row.column}</strong></td>
                <td>${row.count.toLocaleString()}</td>
                <td>$${row.mean.toLocaleString()}</td>
                <td>$${row.std.toLocaleString()}</td>
                <td>$${row.min.toLocaleString()}</td>
                <td>$${row.q25.toLocaleString()}</td>
                <td>$${row.q50.toLocaleString()}</td>
                <td>$${row.q75.toLocaleString()}</td>
                <td>$${row.max.toLocaleString()}</td>
            `;
            statsBody.appendChild(tr);
        });
    }

    // 3. Correlation Matrix (Plotly Heatmap)
    renderCorrelationHeatmap('edaCorrHeatmap', data.correlation_matrix, theme);

    // 4. Outlier Detection Badges
    const outliersContainer = document.getElementById('edaOutliersContainer');
    if (outliersContainer) {
        outliersContainer.innerHTML = '';
        Object.entries(data.outliers).forEach(([col, out]) => {
            const card = document.createElement('div');
            card.className = 'kpi-card';
            card.innerHTML = `
                <div class="kpi-top">
                    <span class="kpi-label">${col} Outliers</span>
                    <div class="kpi-icon"><i class="fa-solid fa-bug"></i></div>
                </div>
                <div class="kpi-value">${out.count} <span style="font-size:0.9rem; color:var(--text-secondary);">(${out.percentage}%)</span></div>
                <div class="kpi-subtext">Bounds: [${out.lower_bound}, ${out.upper_bound}]</div>
            `;
            outliersContainer.appendChild(card);
        });
    }

    // 5. Distribution Charts
    renderDistributionChart('edaSalesDist', data.distributions.Sales, 'Sales Distribution', theme.primary, theme);
    renderDistributionChart('edaProfitDist', data.distributions.Profit, 'Profit Distribution', theme.success, theme);
    renderDistributionChart('edaDiscountDist', data.distributions.Discount, 'Discount Distribution', theme.warning, theme);
}

function renderCorrelationHeatmap(elemId, corrData, theme) {
    const elem = document.getElementById(elemId);
    if (!elem) return;

    const trace = {
        z: corrData.values,
        x: corrData.columns,
        y: corrData.columns,
        type: 'heatmap',
        colorscale: 'YlGnBu',
        showscale: true,
        colorbar: { tickfont: { color: theme.textColor } }
    };

    const layout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        margin: { l: 80, r: 20, t: 20, b: 80 },
        xaxis: { color: theme.textColor, gridcolor: theme.gridColor },
        yaxis: { color: theme.textColor, gridcolor: theme.gridColor }
    };

    Plotly.newPlot(elemId, [trace], layout, { responsive: true, displayModeBar: false });
}

function renderDistributionChart(canvasId, distData, label, color, theme) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: distData.labels,
            datasets: [{
                label: label,
                data: distData.counts,
                backgroundColor: color,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { ticks: { color: theme.textColor }, grid: { display: false } },
                y: { ticks: { color: theme.textColor }, grid: { color: theme.gridColor } }
            }
        }
    });
}
