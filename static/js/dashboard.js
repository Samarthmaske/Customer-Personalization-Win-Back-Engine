let customersData = [];
let clusterChartInstance = null;
let lastActivityId = 0;       // tracks last seen event ID for delta polling
let pollIntervalId  = null;   // setInterval handle

$(document).ready(function() {
    // Initial fetch of analytical data
    fetchDashboardTelemetry();
});


// Fetch simulated ML metrics & customer profiling data
function fetchDashboardTelemetry() {
    $.ajax({
        url: '/api/customers',
        type: 'GET',
        dataType: 'json',
        success: function(response) {
            customersData = response.customers;
            const abTelemetry = response.ab_telemetry;

            // 1. Populate KPI Metrics Cards
            $('#kpi-recovered-rev').text('$' + abTelemetry.recovered_revenue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
            $('#kpi-campaign-roi').text('+' + abTelemetry.campaign_roi.toFixed(1) + '%');
            
            const uplift = abTelemetry.treatment_churn_rate - abTelemetry.control_churn_rate;
            $('#kpi-uplift').text(uplift.toFixed(1) + '%');
            
            const totalMonitored = abTelemetry.control_group_size + abTelemetry.treatment_group_size;
            $('#kpi-campaign-groups').text(totalMonitored.toLocaleString('en-US'));

            // 2. Populate Churn Predictor Table
            populateChurnTable(customersData);

            // 3. Render Chart.js Micro-Segmentation Scatter Plot
            renderClusterChart(customersData);

            // 4. Default select highest churn-risk customer in the RFM Profiler
            if (customersData.length > 0) {
                const sortedFirst = [...customersData].sort((a, b) => b.churn_risk - a.churn_risk)[0];
                selectCustomerProfile(sortedFirst.id);
                setTimeout(() => {
                    $(`.customer-row-item[data-id="${sortedFirst.id}"]`).addClass('row-selected');
                }, 100);
            }

            // 5. Start live activity feed & orders polling (every 5 seconds)
            if (!pollIntervalId) {
                startActivityFeedPolling();
                pollIntervalId = setInterval(startActivityFeedPolling, 5000);
            }
        },
        error: function(xhr, status, error) {
            console.error("Inference telemetry API failure:", error);
            $('#churn-table tbody').html(`
                <tr>
                    <td colspan="6" class="text-center py-5 text-danger">
                        <i class="fa-solid fa-triangle-exclamation fs-3 mb-2"></i><br>
                        Failed to connect to ML Microservices backend. Verify server logs.
                    </td>
                </tr>
            `);
        }
    });
}

// Populate the customer churn classification output
function populateChurnTable(customers) {
    const tbody = $('#churn-table tbody');
    tbody.empty();

    // Sort by churn probability descending to focus on highest risks first
    const sortedCustomers = [...customers].sort((a, b) => b.churn_risk - a.churn_risk);

    sortedCustomers.forEach(customer => {
        let badgeClass = '';
        let progressClass = '';
        let statusLabel = '';
        
        // Dynamic classification classification based on prediction threshold
        if (customer.churn_risk >= 0.70) {
            badgeClass = 'badge-risk-high';
            progressClass = 'bg-danger';
            statusLabel = 'Critical Risk';
        } else if (customer.churn_risk >= 0.40) {
            badgeClass = 'badge-risk-medium';
            progressClass = 'bg-warning';
            statusLabel = 'Medium Risk';
        } else {
            badgeClass = 'badge-risk-low';
            progressClass = 'bg-success';
            statusLabel = 'Low Risk';
        }

        const riskPercentage = Math.round(customer.churn_risk * 100);

        const rowHtml = `
            <tr class="customer-row-item cursor-pointer" data-id="${customer.id}" style="cursor: pointer;">
                <td class="font-monospace text-cyan">${customer.id}</td>
                <td><strong>${customer.name}</strong></td>
                <td><span class="text-secondary-dark">${customer.cluster}</span></td>
                <td>
                    <div class="d-flex align-items-center">
                        <span class="font-monospace me-2" style="width: 35px; text-align: right;">${riskPercentage}%</span>
                        <div class="progress progress-dark flex-grow-1">
                            <div class="progress-bar ${progressClass}" role="progressbar" style="width: ${riskPercentage}%" aria-valuenow="${riskPercentage}" aria-valuemin="0" aria-valuemax="100"></div>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="badge ${badgeClass}">${statusLabel}</span>
                </td>
                <td class="text-center">
                    <button class="btn btn-outline-info btn-xs py-1 px-2 rounded font-monospace btn-inspect" style="font-size: 0.75rem;">
                        Inspect
                    </button>
                </td>
            </tr>
        `;
        tbody.append(rowHtml);
    });

    // Row Click Event Binding
    $('.customer-row-item').on('click', function(e) {
        if ($(e.target).closest('.btn-inspect').length) return;
        const custId = $(this).data('id');
        selectCustomerProfile(custId);

        $('.customer-row-item').removeClass('row-selected');
        $(this).addClass('row-selected');
    });

    $('.btn-inspect').on('click', function(e) {
        e.stopPropagation();
        const custId = $(this).closest('.customer-row-item').data('id');
        selectCustomerProfile(custId);
        $('.customer-row-item').removeClass('row-selected');
        $(this).closest('.customer-row-item').addClass('row-selected');
    });
}

// Select a customer profile to display in the RFM Detail card
function selectCustomerProfile(customerId, options = {}) {
    const customer = customersData.find(c => c.id === customerId);
    if (!customer) return;

    const rfmContainer = $('#rfm-detail-content');
    const htmlContent = buildRfmProfileHtml(customer);

    if (options.skipAnimation) {
        rfmContainer.html(htmlContent);
        return;
    }

    rfmContainer.fadeOut(150, function() {
        rfmContainer.html(htmlContent).fadeIn(150);
    });
}

function buildRfmProfileHtml(customer) {
        let riskColor = '#10b981'; // Green
        if (customer.churn_risk >= 0.70) riskColor = '#ef4444'; // Red
        else if (customer.churn_risk >= 0.40) riskColor = '#f59e0b'; // Amber

        return `
            <div class="text-start">
                <!-- Profile Header -->
                <div class="d-flex align-items-center mb-4">
                    <div class="rounded-circle d-flex align-items-center justify-content-center text-white" style="width: 50px; height: 50px; background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);">
                        <span class="fs-4 fw-bold">${customer.name.charAt(0)}</span>
                    </div>
                    <div class="ms-3">
                        <h5 class="mb-0 text-white">${customer.name}</h5>
                        <small class="text-secondary-dark font-monospace">${customer.id} | ${customer.email}</small>
                    </div>
                </div>

                <!-- Churn Probability Gauge Info -->
                <div class="p-3 rounded-3 mb-4" style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border-dark);">
                    <div class="d-flex justify-content-between mb-1">
                        <span class="text-secondary-dark small">ML Churn Risk Estimate</span>
                        <span class="font-monospace fw-bold" style="color: ${riskColor};">${(customer.churn_risk * 100).toFixed(1)}%</span>
                    </div>
                    <div class="progress progress-dark" style="height: 6px;">
                        <div class="progress-bar" role="progressbar" style="width: ${customer.churn_risk * 100}%; background-color: ${riskColor};" aria-valuenow="${customer.churn_risk * 100}" aria-valuemin="0" aria-valuemax="100"></div>
                    </div>
                </div>

                <h6 class="brand-font text-white mb-3 text-uppercase letter-spacing-5" style="font-size: 0.75rem;">Transactional Telemetry (RFM)</h6>

                <!-- RFM Details Grid -->
                <div class="row g-3 mb-4">
                    <!-- Recency -->
                    <div class="col-4">
                        <div class="p-3 text-center rounded-3 bg-dark-opacity" style="background: rgba(15, 23, 42, 0.3); border: 1px solid rgba(255,255,255,0.03);">
                            <span class="text-secondary-dark d-block text-uppercase" style="font-size: 0.65rem;">Recency</span>
                            <span class="fs-4 fw-bold text-white font-monospace">${customer.recency}</span>
                            <span class="text-secondary-dark d-block" style="font-size: 0.65rem;">days ago</span>
                        </div>
                    </div>
                    <!-- Frequency -->
                    <div class="col-4">
                        <div class="p-3 text-center rounded-3 bg-dark-opacity" style="background: rgba(15, 23, 42, 0.3); border: 1px solid rgba(255,255,255,0.03);">
                            <span class="text-secondary-dark d-block text-uppercase" style="font-size: 0.65rem;">Frequency</span>
                            <span class="fs-4 fw-bold text-white font-monospace">${customer.frequency}</span>
                            <span class="text-secondary-dark d-block" style="font-size: 0.65rem;">orders</span>
                        </div>
                    </div>
                    <!-- Monetary -->
                    <div class="col-4">
                        <div class="p-3 text-center rounded-3 bg-dark-opacity" style="background: rgba(15, 23, 42, 0.3); border: 1px solid rgba(255,255,255,0.03);">
                            <span class="text-secondary-dark d-block text-uppercase" style="font-size: 0.65rem;">Monetary</span>
                            <span class="fs-6 fw-bold text-white font-monospace">$${Math.round(customer.monetary)}</span>
                            <span class="text-secondary-dark d-block" style="font-size: 0.65rem;">LTV</span>
                        </div>
                    </div>
                </div>

                <!-- Segmentation Interpretation -->
                <div class="p-3 rounded-3" style="background: rgba(139, 92, 246, 0.05); border: 1px dashed rgba(139, 92, 246, 0.2);">
                    <div class="d-flex align-items-center mb-1">
                        <i class="fa-solid fa-circle-nodes text-purple me-2"></i>
                        <h6 class="mb-0 text-white brand-font" style="font-size: 0.85rem;">Cohort: ${customer.cluster}</h6>
                    </div>
                    <p class="text-secondary-dark mb-0 small" style="font-size: 0.75rem;">
                        ${getCohortInterpretation(customer.cluster)}
                    </p>
                </div>
            </div>
        `;
}

function getCohortInterpretation(cluster) {
    switch (cluster) {
        case 'Champions':
            return 'High-value transactors buying very frequently. Low churn risk. Should be target of early access & premium tiers.';
        case 'Loyalists':
            return 'Steady buyers with higher average spend. Low risk. Target with standard loyalty points and high retention recognition campaigns.';
        case 'At Risk':
            return 'Highly irregular purchasing behavior. Churn probability elevated. Requires proactive prescriptive win-back offers and discount incentives.';
        case 'Lost':
            return 'Long duration since last checkout with minimal historic value. Extremely high probability of churn. Winback campaigns must be highly aggressive.';
        default:
            return 'General customer segment. Maintain standard engagement campaigns.';
    }
}

// Render Unsupervised Clustering boundaries in Chart.js
function renderClusterChart(customers) {
    const ctx = document.getElementById('clusterChart').getContext('2d');
    
    // Group customers by segment
    const clusters = {
        'Champions': [],
        'Loyalists': [],
        'At Risk': [],
        'Lost': []
    };
    
    customers.forEach(cust => {
        if (clusters[cust.cluster]) {
            clusters[cust.cluster].push({
                x: cust.frequency,
                y: cust.monetary,
                name: cust.name,
                id: cust.id
            });
        }
    });

    // Define colors to align with our neon styling variables
    const chartColors = {
        'Champions': '#10b981', // Neon green
        'Loyalists': '#06b6d4', // Neon Cyan
        'At Risk': '#f59e0b',   // Amber
        'Lost': '#ef4444'       // Rose/Red
    };

    const datasets = Object.keys(clusters).map(key => {
        return {
            label: key,
            data: clusters[key],
            backgroundColor: chartColors[key] + 'bb', // slightly transparent fill
            borderColor: chartColors[key],
            borderWidth: 1.5,
            pointRadius: 8,
            pointHoverRadius: 10,
            pointHoverBackgroundColor: chartColors[key],
            pointHoverBorderColor: '#ffffff'
        };
    });

    if (clusterChartInstance) {
        clusterChartInstance.destroy();
    }

    clusterChartInstance = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#94a3b8',
                        font: {
                            family: 'Outfit',
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const cust = context.raw;
                            return `${cust.name} (${cust.id}): Orders: ${cust.x}, LTV: $${cust.y}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Frequency (Total Purchases)',
                        color: '#94a3b8'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        borderColor: 'rgba(255, 255, 255, 0.08)'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Monetary Value (LTV in USD)',
                        color: '#94a3b8'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        borderColor: 'rgba(255, 255, 255, 0.08)'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                }
            }
        }
    });

    // Make chart interactive: clicking on a scatter dot inspects the customer
    document.getElementById('clusterChart').onclick = function(evt) {
        const activePoints = clusterChartInstance.getElementsAtEventForMode(evt, 'nearest', { intersect: true }, true);
        if (activePoints.length > 0) {
            const datasetIndex = activePoints[0].datasetIndex;
            const index = activePoints[0].index;
            const customerObj = clusterChartInstance.data.datasets[datasetIndex].data[index];
            selectCustomerProfile(customerObj.id);

            // Highlight corresponding row in table using proper class
            $('.customer-row-item').removeClass('row-selected');
            $(`.customer-row-item[data-id="${customerObj.id}"]`).addClass('row-selected');
        }
    };
}


// ══════════════════════════════════════════════════════════════════════════════
// LIVE ACTIVITY FEED POLLING
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Polls /api/activity-feed for new events and updated customer/KPI data.
 * Uses delta polling via lastActivityId to only fetch new events each cycle.
 */
function startActivityFeedPolling() {
    $.ajax({
        url: '/api/activity-feed',
        type: 'GET',
        data: { since_id: lastActivityId },
        dataType: 'json',
        success: function(data) {
            // ── Update live KPI sub-metrics (recovered revenue changes as orders come in) ──
            const recRevEl = $('#kpi-recovered-rev');
            const newRevText = '$' + data.ab_telemetry.recovered_revenue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            if (recRevEl.text() !== newRevText) {
                recRevEl.text(newRevText);
                recRevEl.addClass('kpi-updated');
                setTimeout(() => recRevEl.removeClass('kpi-updated'), 1000);
            }

            // ── Update total orders & live revenue header in Recent Orders panel ──
            $('#kpi-total-orders').text(data.total_orders);
            const totalRevText = '$' + data.total_revenue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            $('#kpi-total-rev').text(totalRevText);

            // ── Refresh RFM data (customer mutations from orders) ──
            if (data.customers && data.customers.length > 0) {
                const prevSelected = $('.customer-row-item.row-selected').data('id');
                customersData = data.customers;
                populateChurnTable(customersData);
                renderClusterChart(customersData);
                // Re-apply selected row highlight and refresh RFM panel with live data
                if (prevSelected) {
                    $(`.customer-row-item[data-id="${prevSelected}"]`).addClass('row-selected');
                    selectCustomerProfile(prevSelected, { skipAnimation: true });
                }
            }

            // ── Render new activity feed events ──
            if (data.events && data.events.length > 0) {
                renderActivityEvents(data.events);
                // Track last seen ID for delta polling
                const maxId = Math.max(...data.events.map(e => e.id));
                if (maxId > lastActivityId) lastActivityId = maxId;
            }
        },
        error: function(xhr, status, err) {
            // Silently fail — don't disrupt the dashboard on poll errors
            console.warn('[Live Feed] Poll failed:', err);
        }
    });

    // Also refresh recent orders table
    fetchAllOrders();
}


/**
 * Renders activity feed events into the live feed panel.
 * New events are prepended with a slide-in animation.
 * @param {Array} events - Array of event objects from /api/activity-feed
 */
function renderActivityEvents(events) {
    const feedList = $('#activity-feed-list');
    $('#activity-feed-empty').remove();

    // Build HTML for each event (newest first, already sorted server-side)
    events.forEach(event => {
        // Skip if this event is already rendered
        if ($(`[data-event-id="${event.id}"]`).length > 0) return;

        let iconClass = 'page-view';
        let iconHtml  = '<i class="fa-solid fa-eye"></i>';

        if (event.type === 'cart_add') {
            iconClass = 'cart-add';
            iconHtml  = '<i class="fa-solid fa-cart-plus"></i>';
        } else if (event.type === 'order_placed') {
            iconClass = 'order-placed';
            iconHtml  = '<i class="fa-solid fa-circle-check"></i>';
        }

        const eventHtml = `
            <div class="activity-feed-item" data-event-id="${event.id}">
                <div class="activity-icon ${iconClass}">${iconHtml}</div>
                <div class="flex-grow-1" style="min-width:0;">
                    <div class="text-white small fw-semibold text-truncate">${event.customer_name}</div>
                    <div class="text-secondary-dark" style="font-size:0.78rem;line-height:1.4;">${event.message}</div>
                    <div class="text-secondary-dark font-monospace" style="font-size:0.7rem;opacity:0.6;margin-top:2px;">${event.timestamp}</div>
                </div>
            </div>
        `;

        // Prepend new events so newest appears at top
        feedList.prepend(eventHtml);
    });

    // Cap at 30 events shown in feed to keep it performant
    feedList.find('.activity-feed-item').slice(30).remove();
}


/**
 * Fetches all orders from /api/orders/all and renders them into the Recent Orders table.
 */
function fetchAllOrders() {
    $.ajax({
        url: '/api/orders/all',
        type: 'GET',
        dataType: 'json',
        success: function(data) {
            const tbody = $('#orders-table-body');
            if (!data.orders || data.orders.length === 0) {
                tbody.html(`
                    <tr id="orders-empty-row">
                        <td colspan="6" class="text-center py-4 text-secondary-dark">
                            <i class="fa-solid fa-inbox me-2"></i>
                            No orders yet. Place orders via the storefront to see them here.
                        </td>
                    </tr>`);
                return;
            }

            // Only re-render when order list actually changed (avoid flicker)
            const currentIds = tbody.find('tr[data-order-id]').map(function() {
                return $(this).data('order-id');
            }).get().join(',');
            const newIds = data.orders.map(o => o.order_id).join(',');
            if (currentIds === newIds) return;

            tbody.empty();
            data.orders.forEach(order => {
                tbody.append(`
                    <tr data-order-id="${order.order_id}">
                        <td class="font-monospace text-cyan" style="font-size:0.82rem;">${order.order_id}</td>
                        <td><strong>${order.customer_name}</strong></td>
                        <td class="text-center text-secondary-dark">${order.item_count}</td>
                        <td class="text-end font-monospace fw-bold">$${order.total.toFixed(2)}</td>
                        <td class="text-center"><span class="order-badge-confirmed">${order.status}</span></td>
                        <td class="text-end text-secondary-dark" style="font-size:0.78rem;">${order.timestamp}</td>
                    </tr>
                `);
            });
        },
        error: function() {
            // Silently ignore — orders table is supplemental
        }
    });
}
