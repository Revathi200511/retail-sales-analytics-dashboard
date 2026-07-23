/* ==========================================================================
   Retail Sales Analytics Dashboard - Main JavaScript Helpers & Theme Controller
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSidebar();
});

// Theme Management (Light / Dark)
function initTheme() {
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const storedTheme = localStorage.getItem('retail_dashboard_theme') || 'dark';
    
    document.documentElement.setAttribute('data-theme', storedTheme);
    updateThemeIcon(storedTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('retail_dashboard_theme', newTheme);
            updateThemeIcon(newTheme);

            // Dispatch global event for chart re-rendering if needed
            window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: newTheme } }));
        });
    }
}

function updateThemeIcon(theme) {
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        themeIcon.className = theme === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
    }
}

// Sidebar Mobile Toggle
function initSidebar() {
    const toggleBtn = document.getElementById('toggleSidebarBtn');
    const sidebar = document.querySelector('.sidebar');

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('show');
        });
    }
}

// Global Toast Notification Helper
function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let iconClass = 'fa-info-circle';
    if (type === 'success') iconClass = 'fa-check-circle';
    if (type === 'danger') iconClass = 'fa-exclamation-circle';
    if (type === 'warning') iconClass = 'fa-exclamation-triangle';

    toast.innerHTML = `<i class="fa-solid ${iconClass}"></i> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Helper to serialize filter form parameters into query string
function getFilterQueryParams() {
    const params = new URLSearchParams();
    
    const filterIds = ['startDate', 'endDate', 'filterRegion', 'filterState', 'filterCategory', 'filterSubCategory', 'filterCustomer', 'filterYear'];
    const paramKeys = ['start_date', 'end_date', 'region', 'state', 'category', 'sub_category', 'customer', 'year'];

    filterIds.forEach((id, index) => {
        const elem = document.getElementById(id);
        if (elem && elem.value && elem.value !== 'All') {
            params.append(paramKeys[index], elem.value);
        }
    });

    return params.toString();
}

// Get Theme Colors for Charts
function getChartThemeColors() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    return {
        textColor: isDark ? '#94a3b8' : '#64748b',
        gridColor: isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.06)',
        bgCard: isDark ? '#131b2e' : '#ffffff',
        primary: '#4f46e5',
        success: '#10b981',
        warning: '#f59e0b',
        danger: '#ef4444',
        info: '#06b6d4',
        purple: '#8b5cf6',
        pink: '#ec4899',
        palette: ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#8b5cf6', '#ec4899', '#f97316', '#14b8a6', '#6366f1']
    };
}
