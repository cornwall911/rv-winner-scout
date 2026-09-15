"""Updates public/index.html and index.html to make the refresh button 100% manual (no automatic periodic timer).
"""

import re

for path in ['public/index.html', 'index.html']:
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    # 1. Update button text and remove syncCountdown
    c = re.sub(
        r'<button id="refreshBtn".*?</button>',
        '''<button id="refreshBtn" class="btn-refresh" onclick="manualRefresh()" title="Click to refresh latest discoveries">
                    <span id="refreshIcon" class="refresh-icon">🔄</span>
                    <span id="refreshText">Refresh Feed</span>
                </button>''',
        c,
        flags=re.DOTALL
    )

    # 2. Replace the timer JS block with pure manual refresh
    old_timer_pattern = r'// 7\..*?function manualRefresh\(\) \{\s*refreshLiveDashboard\(.*?\);\s*\}\s*(// Auto-refresh timer.*?\},\s*1000\);)?'
    
    manual_js = '''// 7. Manual Live Refresh Engine
        let isSyncing = false;

        async function refreshLiveDashboard() {
            if (isSyncing) return;
            isSyncing = true;
            const icon = document.getElementById('refreshIcon');
            const text = document.getElementById('refreshText');
            if (icon) icon.classList.add('spinning');
            if (text) text.innerText = 'Checking...';

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
                    } else {
                        showToast('✅ Feed is up to date (' + curCardsCount + ' items)');
                    }
                }
            } catch (err) {
                console.warn('Refresh error:', err);
                window.location.reload(true);
            } finally {
                if (icon) icon.classList.remove('spinning');
                if (text) text.innerText = 'Refresh Feed';
                isSyncing = false;
            }
        }

        function manualRefresh() {
            refreshLiveDashboard();
        }'''

    c = re.sub(
        r'// 7\. Real-Time Auto-Refresh.*?(?=function showToast)',
        manual_js + '\n\n        ',
        c,
        flags=re.DOTALL
    )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)

    print(f'Successfully updated {path} to purely manual refresh')
