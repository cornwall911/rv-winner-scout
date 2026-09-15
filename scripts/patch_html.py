"""Patches public/index.html and index.html to include:
1. Refresh button in navbar next to Live Feed
2. .btn-refresh and spin CSS rules
3. Reliable filterCards() display logic
4. Real-time background sync engine (manual refresh + 45s auto-polling + toast)
"""

CSS_SNIPPET = """
        .btn-refresh {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.3);
            color: #38BDF8;
            padding: 7px 14px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            transition: all 0.2s ease;
        }
        .btn-refresh:hover {
            background: rgba(56, 189, 248, 0.25);
            border-color: #38BDF8;
            transform: translateY(-1px);
        }
        .btn-refresh:active {
            transform: scale(0.97);
        }
        .refresh-icon.spinning {
            display: inline-block;
            animation: spin-icon 0.75s linear infinite;
        }
        @keyframes spin-icon {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        .sync-countdown {
            font-size: 0.72rem;
            color: var(--text-secondary);
            font-weight: 600;
        }
"""

NAVBAR_BTN = """                <div class="live-badge" title="Real-Time Scout Live Feed Active">
                    <span class="pulse-dot"></span> Live Feed
                </div>

                <button id="refreshBtn" class="btn-refresh" onclick="manualRefresh()" title="Click to check and refresh latest discoveries">
                    <span id="refreshIcon" class="refresh-icon">🔄</span>
                    <span id="refreshText">Refresh</span>
                    <span id="syncCountdown" class="sync-countdown">(45s)</span>
                </button>"""

OLD_NAVBAR = """                <div class="live-badge" title="Real-Time Scout Live Feed Active">
                    <span class="pulse-dot"></span> Live Feed
                </div>"""

OLD_FILTER = """                if (matchesSearch && matchesFilter) {
                    if (card.style.display === 'none') {
                        card.style.display = 'flex';
                        card.style.animation = 'none';
                        card.offsetHeight; /* trigger reflow */
                        card.style.animation = 'fadeInCard 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards';
                    }
                } else {
                    card.style.display = 'none';
                }"""

NEW_FILTER = """                if (matchesSearch && matchesFilter) {
                    card.style.display = 'flex';
                } else {
                    card.style.display = 'none';
                }"""

JS_ENGINE = """        // 7. Real-Time Auto-Refresh & Background Live Sync Engine
        let countdownSeconds = 45;
        let isSyncing = false;

        async function refreshLiveDashboard(isManual = false) {
            if (isSyncing) return;
            isSyncing = true;
            const icon = document.getElementById('refreshIcon');
            const text = document.getElementById('refreshText');
            if (icon) icon.classList.add('spinning');
            if (text && isManual) text.innerText = 'Syncing...';

            try {
                const url = window.location.pathname + '?_v=' + Date.now();
                const res = await fetch(url, {
                    cache: 'no-store',
                    headers: { 'Pragma': 'no-cache', 'Cache-Control': 'no-cache' }
                });
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const htmlText = await res.text();
                const parser = new DOMParser();
                const newDoc = parser.parseFromString(htmlText, 'text/html');

                const newGrid = newDoc.getElementById('cardsGrid');
                const curGrid = document.getElementById('cardsGrid');
                if (newGrid && curGrid) {
                    const curCardsCount = curGrid.querySelectorAll('.product-card').length;
                    const newCardsCount = newGrid.querySelectorAll('.product-card').length;

                    // Update Grid HTML
                    curGrid.innerHTML = newGrid.innerHTML;

                    // Update KPI row
                    const newKpis = newDoc.querySelector('.kpi-row');
                    const curKpis = document.querySelector('.kpi-row');
                    if (newKpis && curKpis) curKpis.innerHTML = newKpis.innerHTML;

                    // Update Filter tabs while preserving active state
                    const newTabs = newDoc.querySelector('.filter-tabs');
                    const curTabs = document.querySelector('.filter-tabs');
                    if (newTabs && curTabs) {
                        const activeFilterType = currentFilter;
                        curTabs.innerHTML = newTabs.innerHTML;
                        const targetBtn = curTabs.querySelector("[onclick*=\\"'" + activeFilterType + "'\\"]");
                        if (targetBtn) {
                            curTabs.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                            targetBtn.classList.add('active');
                        }
                    }

                    // Re-apply filter and search seamlessly
                    filterCards();

                    if (newCardsCount > curCardsCount) {
                        showToast('🎉 ' + (newCardsCount - curCardsCount) + ' new products added!');
                    } else if (isManual) {
                        showToast('✅ Feed is up to date (' + curCardsCount + ' items)');
                    }
                }
            } catch (err) {
                console.warn('Background sync error:', err);
                if (isManual) {
                    window.location.reload(true);
                }
            } finally {
                if (icon) icon.classList.remove('spinning');
                if (text) text.innerText = 'Refresh';
                countdownSeconds = 45;
                isSyncing = false;
            }
        }

        function manualRefresh() {
            refreshLiveDashboard(true);
        }

        // Auto-refresh timer: ticks every second, syncs every 45s
        setInterval(() => {
            countdownSeconds--;
            const cd = document.getElementById('syncCountdown');
            if (cd) cd.innerText = '(' + countdownSeconds + 's)';
            if (countdownSeconds <= 0) {
                countdownSeconds = 45;
                refreshLiveDashboard(false);
            }
        }, 1000);

        function showToast(msg) {
            let toast = document.getElementById('scoutToast');
            if (!toast) {
                toast = document.createElement('div');
                toast.id = 'scoutToast';
                toast.style.cssText = 'position:fixed; bottom:24px; right:24px; background:#1E293B; border:1px solid #10B981; color:#F8FAFC; padding:12px 20px; border-radius:12px; font-weight:600; font-size:0.9rem; z-index:9999; box-shadow:0 8px 30px rgba(0,0,0,0.5); display:flex; align-items:center; gap:8px; transition:opacity 0.3s ease;';
                document.body.appendChild(toast);
            }
            toast.innerText = msg;
            toast.style.opacity = '1';
            toast.style.display = 'flex';
            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => { toast.style.display = 'none'; }, 300);
            }, 3500);
        }

        // Run authentication check on startup
        checkAuth();"""

for path in ['public/index.html', 'index.html']:
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    if '.btn-refresh' not in c:
        c = c.replace('/* KPI Row */', CSS_SNIPPET + '\n        /* KPI Row */')

    if 'id="refreshBtn"' not in c:
        c = c.replace(OLD_NAVBAR, NAVBAR_BTN)

    if OLD_FILTER in c:
        c = c.replace(OLD_FILTER, NEW_FILTER)

    if 'refreshLiveDashboard' not in c:
        c = c.replace('        // Run authentication check on startup\n        checkAuth();', JS_ENGINE)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print(f'Successfully updated {path}')
