/**
 * Xnoppo — Client-side utilities
 * Provides toast notifications, config saving, and sidebar toggle.
 */

const xnoppo = {
    /**
     * Save config to the server and show feedback.
     */
    async saveConfig(payload) {
        try {
            const res = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (res.ok) {
                showToast('Configuración guardada', 'success');
            } else {
                const data = await res.json().catch(() => ({}));
                showToast('Error al guardar: ' + (data.error || res.statusText), 'error');
            }
        } catch (e) {
            showToast('Error de red: ' + e.message, 'error');
        }
    },
};

/**
 * Show a toast notification.
 * @param {string} message
 * @param {'success'|'error'|'info'} type
 * @param {number} duration - ms to show
 */
function showToast(message, type = 'info', duration = 3500) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
        success: '✓',
        error: '✗',
        info: 'ℹ',
    };

    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.innerHTML =
        '<span style="font-size:1.1rem;font-weight:700;">' + (icons[type] || '') + '</span>' +
        '<span style="font-size:0.85rem;">' + message + '</span>';

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 350);
    }, duration);
}

/**
 * Toggle sidebar on mobile.
 */
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    sidebar.classList.toggle('open');
    overlay.classList.toggle('active');
}

/**
 * Update sidebar status indicator on page load.
 */
(async function updateSidebarStatus() {
    try {
        const res = await fetch('/api/state');
        const data = await res.json();
        const dot = document.getElementById('statusDot');
        const txt = document.getElementById('statusText');
        if (!dot || !txt) return;

        if (data.Playstate === 'Playing') {
            dot.style.background = 'var(--success)';
            dot.style.boxShadow = '0 0 8px rgba(34,197,94,0.4)';
            txt.textContent = 'Reproduciendo';
        } else if (data.Playstate === 'Free') {
            dot.style.background = 'var(--accent-secondary)';
            dot.style.boxShadow = '0 0 8px rgba(0,212,255,0.3)';
            txt.textContent = 'Conectado — Libre';
        } else if (data.Playstate === 'Loading') {
            dot.style.background = 'var(--warning)';
            dot.style.boxShadow = '0 0 8px rgba(251,191,36,0.3)';
            txt.textContent = 'Cargando...';
        } else {
            dot.style.background = 'var(--text-muted)';
            dot.style.boxShadow = 'none';
            txt.textContent = 'Sin conexión';
        }
    } catch (e) {
        const dot = document.getElementById('statusDot');
        const txt = document.getElementById('statusText');
        if (dot) { dot.style.background = 'var(--error)'; dot.style.boxShadow = 'none'; }
        if (txt) txt.textContent = 'Error';
    }
})();
