/**
 * Dashboard JavaScript
 * Handles property swapping, UI interactions
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard loaded');

    // Swap functionality (when implemented)
    const swapButtons = document.querySelectorAll('.swap-btn');
    swapButtons.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const propertyId = btn.dataset.propertyId;
            const segment = btn.dataset.segment;

            if (confirm('Replace this property with next best alternative?')) {
                try {
                    const resp = await fetch('/api/properties/swap', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({segment, new_property_id: propertyId})
                    });
                    if (resp.ok) {
                        alert('Property swapped! Reloading...');
                        location.reload();
                    }
                } catch (err) {
                    alert('Swap failed: ' + err.message);
                }
            }
        });
    });

    // Auto-refresh every 20 minutes (in case scrapes update)
    setTimeout(() => {
        console.log('Auto-refreshing...');
        location.reload();
    }, 20 * 60 * 1000);
});
