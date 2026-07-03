/**
 * storefront.js — GlowStyle E-Commerce Storefront Controller
 * Handles: Cart (add/remove/update), Order placement,
 *          Prescriptive Win-back banner, Spin Wheel,
 *          AI Recommended Products section.
 */

// ─── Global State ──────────────────────────────────────────────────────────────
let isSpinning = false;
let churnRisk  = parseFloat(document.body.dataset.churnRisk || '0.20');
let wheelRotationDeg = 0;

// ─── Spin Wheel Segments ───────────────────────────────────────────────────────
const segments = [
    { text: "10% OFF",      coupon: "SPIN10",   color: "#0ea5e9" },
    { text: "Free Shipping",coupon: "FREESHIP", color: "#8b5cf6" },
    { text: "20% OFF",      coupon: "SPIN20",   color: "#06b6d4" },
    { text: "Try Again",    coupon: "TRYAGAIN", color: "#475569" },
    { text: "25% OFF",      coupon: "SPIN25",   color: "#10b981" },
    { text: "30% OFF",      coupon: "SPIN30",   color: "#f43f5e" },
];

// ─── Bootstrap instances (lazy init) ──────────────────────────────────────────
let cartOffcanvasInst = null;
let orderModalInst    = null;

// ══════════════════════════════════════════════════════════════════════════════
// DOM READY
// ══════════════════════════════════════════════════════════════════════════════
$(document).ready(function () {

    // Init Bootstrap component references
    cartOffcanvasInst = new bootstrap.Offcanvas(document.getElementById('cartOffcanvas'));
    orderModalInst    = new bootstrap.Modal(document.getElementById('orderSuccessModal'));

    // 1. Load personalised win-back banner
    fetchWinbackOffer();

    // 2. Draw the spin wheel canvas
    drawSpinWheel();

    // 3. Load AI recommendations
    fetchRecommendations();

    // 4. Load cart from server (persist across page refresh in session)
    syncCartFromServer();

    // ── Cart badge action button ──────────────────────────────────────────
    // Open offcanvas when cart button in navbar is clicked
    // (handled natively by Bootstrap data-bs-toggle, but we also reload items)
    $('#cartOffcanvas').on('show.bs.offcanvas', function () {
        syncCartFromServer();
    });

    // ── Add to Cart (product cards) ────────────────────────────────────────
    $(document).on('click', '.btn-add-cart, .btn-quick-add', function () {
        const productId = $(this).data('product-id');
        const name      = $(this).data('name') || 'Item';
        addToCart(productId, name, $(this));
    });

    // ── Wishlist Toggle ────────────────────────────────────────────────────
    $(document).on('click', '.btn-wishlist', function () {
        const icon = $(this).find('i');
        if (icon.hasClass('fa-regular')) {
            icon.removeClass('fa-regular').addClass('fa-solid');
            $(this).removeClass('btn-outline-secondary').addClass('btn-outline-danger');
        } else {
            icon.removeClass('fa-solid').addClass('fa-regular');
            $(this).removeClass('btn-outline-danger').addClass('btn-outline-secondary');
        }
    });

    // ── Spin Wheel ─────────────────────────────────────────────────────────
    $('#spin-button').on('click', function () {
        if (!isSpinning) triggerSpinSequence();
    });

    // ── Copy coupon (spin wheel result) ───────────────────────────────────
    $(document).on('click', '.btn-copy-coupon', function () {
        const code = $('#spin-coupon-code').text();
        copyToClipboard(code).then(() => {
            const btn = $(this);
            btn.text('Copied!').addClass('btn-success');
            setTimeout(() => btn.text('Copy').removeClass('btn-success'), 1500);
        }).catch(() => showToast('Could not copy coupon code', true));
    });

    // ── Banner Action Button: copy coupon ─────────────────────────────────
    $('#banner-action-btn').on('click', function () {
        const code = $('#coupon-display').text();
        if (!code || code === '-----') return;
        const btn = $(this);
        const orig = btn.text();
        copyToClipboard(code).then(() => {
            btn.text('✓ Coupon Copied!').addClass('opacity-75');
            setTimeout(() => btn.text(orig).removeClass('opacity-75'), 1800);
        }).catch(() => showToast('Could not copy coupon code', true));
    });

    // ── Place Order Button ─────────────────────────────────────────────────
    $(document).on('click', '#place-order-btn', placeOrder);

    // ── Cart: Remove item ──────────────────────────────────────────────────
    $(document).on('click', '.cart-remove-btn', function () {
        const productId = $(this).data('product-id');
        removeFromCart(productId);
    });

    // ── Cart: Qty +/- ──────────────────────────────────────────────────────
    $(document).on('click', '.cart-qty-btn', function () {
        const productId = $(this).data('product-id');
        const delta     = parseInt($(this).data('delta'));
        const qtyEl     = $(`.cart-qty-value[data-product-id="${productId}"]`);
        const newQty    = Math.max(0, parseInt(qtyEl.text()) + delta);
        updateCartQty(productId, newQty);
    });

    // ── View / Close Order History ─────────────────────────────────────────
    $('#view-order-history-btn').on('click', function () {
        loadOrderHistory();
        $('#order-history-panel').slideDown(200);
    });
    $(document).on('click', '#close-order-history-btn', function () {
        $('#order-history-panel').slideUp(200);
    });
});


// ══════════════════════════════════════════════════════════════════════════════
// WIN-BACK BANNER
// ══════════════════════════════════════════════════════════════════════════════
function fetchWinbackOffer() {
    $.ajax({
        url: '/api/winback-offer', type: 'GET', dataType: 'json',
        success: function (offer) {
            churnRisk = offer.risk_score;
            $('#banner-title').text(offer.banner_title);
            $('#banner-text').text(offer.banner_text);
            $('#coupon-display').text(offer.coupon_code);
            $('#banner-action-btn').text(offer.button_text);
            $('#retention-banner-container').fadeIn(500);
        },
        error: function (err) { console.error('Win-back offer fetch failed:', err); }
    });
}


// ══════════════════════════════════════════════════════════════════════════════
// CART MANAGEMENT
// ══════════════════════════════════════════════════════════════════════════════

/** Fetch current cart from server and refresh the offcanvas UI. */
function syncCartFromServer() {
    $.get('/api/cart', function (data) {
        updateCartUI(data.items, data.total, data.count);
    });
}

/** Add a product to the cart via API. */
function addToCart(productId, name, btn) {
    // Optimistic button feedback
    if (btn) {
        btn.prop('disabled', true);
        const orig = btn.html();
        btn.html('<i class="fa-solid fa-circle-notch fa-spin"></i>');
        setTimeout(() => { btn.prop('disabled', false).html(orig); }, 600);
    }

    $.ajax({
        url: '/api/cart/add', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ product_id: productId }),
        success: function (res) {
            updateCartBadge(res.cart_count);
            showToast(`${name} added to cart!`);
            syncCartFromServer();
        },
        error: function (err) {
            console.error('Add to cart failed:', err);
            showToast('Could not add item to cart. Please try again.', true);
        }
    });
}

/** Remove a product from the cart. */
function removeFromCart(productId) {
    $.ajax({
        url: '/api/cart/remove', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ product_id: productId }),
        success: function (res) {
            updateCartBadge(res.cart_count);
            syncCartFromServer();
        },
        error: function () {
            showToast('Could not remove item from cart.', true);
        }
    });
}

/** Update quantity of a product in the cart. */
function updateCartQty(productId, qty) {
    $.ajax({
        url: '/api/cart/update', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ product_id: productId, qty: qty }),
        success: function (res) {
            updateCartBadge(res.cart_count);
            syncCartFromServer();
        },
        error: function () {
            showToast('Could not update cart quantity.', true);
        }
    });
}

/** Render the offcanvas cart from item list returned by server. */
function updateCartUI(items, total, count) {
    updateCartBadge(count);
    $('#cart-offcanvas-badge').text(count);
    $('#cart-item-count').text(count);

    if (!items || items.length === 0) {
        $('#cart-empty-state').show();
        $('#cart-items-wrapper').hide();
        $('#cart-footer').hide();
        return;
    }

    $('#cart-empty-state').hide();
    $('#cart-items-wrapper').show();
    $('#cart-footer').show();
    $('#cart-total-display').text('$' + total.toFixed(2));

    let html = '';
    items.forEach(item => {
        html += `
        <div class="cart-item d-flex align-items-center gap-3 mb-3 p-2 rounded-3" style="background:#f8fafc;border:1px solid rgba(0,0,0,0.04);">
            <img src="/static/${item.img}" alt="${item.name}" class="cart-item-img rounded-2">
            <div class="flex-grow-1">
                <div class="fw-semibold text-dark small">${item.name}</div>
                <div class="text-muted" style="font-size:0.78rem;">$${item.price.toFixed(2)} each</div>
                <div class="d-flex align-items-center gap-2 mt-1">
                    <button class="cart-qty-btn btn btn-outline-secondary btn-xs px-2" 
                            data-product-id="${item.product_id}" data-delta="-1">−</button>
                    <span class="cart-qty-value font-monospace fw-bold" data-product-id="${item.product_id}">${item.qty}</span>
                    <button class="cart-qty-btn btn btn-outline-secondary btn-xs px-2" 
                            data-product-id="${item.product_id}" data-delta="1">+</button>
                </div>
            </div>
            <div class="text-end">
                <div class="font-monospace fw-bold text-dark small">$${(item.price * item.qty).toFixed(2)}</div>
                <button class="btn btn-link btn-xs text-danger p-0 mt-1 cart-remove-btn" 
                        data-product-id="${item.product_id}" title="Remove">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            </div>
        </div>`;
    });

    $('#cart-items-list').html(html);
}

/** Update the cart count badge in the navbar. */
function updateCartBadge(count) {
    const badge = $('#cart-count');
    badge.text(count);
    badge.toggleClass('d-none', count === 0);
}


// ══════════════════════════════════════════════════════════════════════════════
// ORDER PLACEMENT
// ══════════════════════════════════════════════════════════════════════════════
function placeOrder() {
    const btn = $('#place-order-btn');
    btn.prop('disabled', true).html('<i class="fa-solid fa-circle-notch fa-spin me-2"></i> Processing...');

    $.ajax({
        url: '/api/orders', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({}),
        success: function (res) {
            btn.prop('disabled', false).html('<i class="fa-solid fa-lock me-2"></i> Place Order Securely');

            // Close cart offcanvas, show success modal
            cartOffcanvasInst.hide();
            $('#modal-order-id').text(res.order_id);
            $('#modal-order-total').text('$' + res.total.toFixed(2));
            setTimeout(() => orderModalInst.show(), 300);

            // Reset cart UI
            updateCartUI([], 0, 0);
        },
        error: function (xhr) {
            btn.prop('disabled', false).html('<i class="fa-solid fa-lock me-2"></i> Place Order Securely');
            const msg = xhr.responseJSON?.error || 'Order failed. Please try again.';
            showToast('⚠ ' + msg, true);
        }
    });
}


// ══════════════════════════════════════════════════════════════════════════════
// ORDER HISTORY
// ══════════════════════════════════════════════════════════════════════════════
function loadOrderHistory() {
    $.get('/api/orders/history', function (data) {
        const orders = data.orders;
        if (!orders || orders.length === 0) {
            $('#order-history-list').empty();
            $('#order-history-empty').show();
            return;
        }
        $('#order-history-empty').hide();
        let html = '';
        orders.forEach(o => {
            html += `
            <div class="order-history-item mb-2 p-2 rounded-3" style="background:white;border:1px solid rgba(0,0,0,0.05);">
                <div class="d-flex justify-content-between">
                    <span class="font-monospace fw-bold small text-purple">${o.order_id}</span>
                    <span class="badge bg-success bg-opacity-10 text-success small">${o.status}</span>
                </div>
                <div class="text-muted" style="font-size:0.75rem;">${o.item_count} item(s) · $${o.total.toFixed(2)} · ${o.timestamp}</div>
            </div>`;
        });
        $('#order-history-list').html(html);
    });
}


// ══════════════════════════════════════════════════════════════════════════════
// RECOMMENDED PRODUCTS (AI Engine)
// ══════════════════════════════════════════════════════════════════════════════
function fetchRecommendations() {
    $.ajax({
        url: '/api/recommendations', type: 'GET', dataType: 'json',
        success: function (data) {
            $('#rec-section-title').text(data.section_title);
            $('#rec-section-subtitle').text(data.section_subtitle);
            renderRecommendations(data.recommendations);
        },
        error: function () {
            $('#rec-loading').html('<p class="text-muted text-center">Could not load recommendations.</p>');
        }
    });
}

function renderRecommendations(recs) {
    $('#rec-loading').hide();
    const grid = $('#recommendations-grid');
    grid.empty();

    recs.forEach(rec => {
        const stars = Math.round(rec.rating);
        let starsHtml = '';
        for (let i = 0; i < 5; i++) {
            starsHtml += i < stars
                ? '<i class="fa-solid fa-star text-warning"></i>'
                : '<i class="fa-regular fa-star text-warning"></i>';
        }

        const card = `
        <div class="col-md-6 col-lg-3">
            <div class="rec-card">
                <div class="rec-img-wrapper">
                    <img src="/static/${rec.img}" alt="${rec.name}">
                    <span class="rec-badge" style="background:${rec.badge_color};">${rec.badge}</span>
                    <div class="rec-discount-tag">−${rec.discount}%</div>
                </div>
                <div class="p-3">
                    <span class="text-muted" style="font-size:0.72rem;">${rec.category}</span>
                    <h6 class="brand-font fw-semibold text-dark my-1" style="font-size:0.9rem;">${rec.name}</h6>
                    <div class="mb-1">${starsHtml} <span class="text-muted ms-1" style="font-size:0.7rem;">${rec.rating} (${rec.reviews})</span></div>
                    <div class="d-flex align-items-center gap-2 mb-2">
                        <span class="font-monospace fw-bold text-dark">$${rec.discounted_price.toFixed(2)}</span>
                        <span class="text-muted text-decoration-line-through" style="font-size:0.8rem;">$${rec.original_price.toFixed(2)}</span>
                    </div>
                    <p class="rec-reason mb-2">${rec.reason}</p>
                    <button class="btn btn-storefront w-100 btn-sm btn-add-cart"
                            data-product-id="${rec.id}" data-name="${rec.name}">
                        <i class="fa-solid fa-plus me-1"></i> Add to Cart
                    </button>
                </div>
            </div>
        </div>`;
        grid.append(card);
    });

    grid.fadeIn(300);
}


// ══════════════════════════════════════════════════════════════════════════════
// SPIN WHEEL
// ══════════════════════════════════════════════════════════════════════════════
function drawSpinWheel() {
    const canvas = document.getElementById('wheel-canvas');
    if (!canvas) return;
    const ctx    = canvas.getContext('2d');
    const center = canvas.width / 2;
    const radius = center - 8;
    const angle  = (2 * Math.PI) / segments.length;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    segments.forEach((seg, i) => {
        const start = i * angle;
        const end   = start + angle;

        ctx.beginPath();
        ctx.moveTo(center, center);
        ctx.arc(center, center, radius, start, end);
        ctx.closePath();
        ctx.fillStyle   = seg.color;
        ctx.fill();
        ctx.lineWidth   = 2;
        ctx.strokeStyle = '#0f172a';
        ctx.stroke();

        ctx.save();
        ctx.translate(center, center);
        ctx.rotate(start + angle / 2);
        ctx.fillStyle = '#ffffff';
        ctx.font      = 'bold 13px Outfit';
        ctx.textAlign = 'right';
        ctx.fillText(seg.text, radius - 15, 5);
        ctx.restore();
    });

    ctx.beginPath();
    ctx.arc(center, center, radius, 0, 2 * Math.PI);
    ctx.lineWidth   = 4;
    ctx.strokeStyle = '#0f172a';
    ctx.stroke();
}

function triggerSpinSequence() {
    isSpinning = true;
    $('#spin-button').addClass('opacity-50').text('...');
    $('#spin-result-container').slideUp(200);

    let targetSector = 3; // default: Try Again
    if (churnRisk >= 0.60) {
        targetSector = Math.random() > 0.5 ? 4 : 5; // 25% or 30% OFF
        console.log(`[ML WINBACK] High risk (${Math.round(churnRisk*100)}%) → premium sector ${targetSector}`);
    } else {
        const low = [0, 1, 2, 3];
        targetSector = low[Math.floor(Math.random() * low.length)];
    }

    const sectorAngle = 360 / segments.length;
    const extraSpins  = 5 * 360;
    const baseDeg     = 270 - (targetSector * sectorAngle) - (sectorAngle / 2);
    const variance    = (Math.random() * 20) - 10;
    const finalDeg    = wheelRotationDeg + extraSpins + baseDeg + variance;
    wheelRotationDeg  = finalDeg;

    const wheel = $('#spin-wheel-element');
    wheel.css({ transform: `rotate(${finalDeg}deg)`, transition: 'transform 5s cubic-bezier(0.1,0.8,0.2,1)' });

    wheel.one('transitionend', function () {
        isSpinning = false;
        $('#spin-button').removeClass('opacity-50').text('SPIN');

        const won = segments[targetSector];
        logSpinResult(won);

        if (won.coupon === 'TRYAGAIN') {
            $('#spin-reward-text').html('Unlucky! Feel free to checkout, or try again on your next session.');
            $('#spin-coupon-code').text('NO_COUPON');
        } else {
            $('#spin-reward-text').html(`You won <strong>${won.text}</strong>!`);
            $('#spin-coupon-code').text(won.coupon);
        }
        $('#spin-result-container').slideDown(300);
    });
}

function logSpinResult(rewardItem) {
    $.ajax({
        url: '/api/spin-wheel', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ reward: rewardItem.text, coupon: rewardItem.coupon, risk_score: churnRisk }),
        success: function (res) { console.log('Spin audit log synced:', res.message); },
        error:   function (err) { console.error('Spin log failed:', err); }
    });
}


// ══════════════════════════════════════════════════════════════════════════════
// CLIPBOARD HELPER
// ══════════════════════════════════════════════════════════════════════════════
function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text);
    }
    return new Promise((resolve, reject) => {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        try {
            document.execCommand('copy') ? resolve() : reject(new Error('copy failed'));
        } catch (err) {
            reject(err);
        } finally {
            document.body.removeChild(ta);
        }
    });
}


// ══════════════════════════════════════════════════════════════════════════════
// TOAST HELPER
// ══════════════════════════════════════════════════════════════════════════════
function showToast(message, isError = false) {
    const toastEl = document.getElementById('cart-toast');
    if (isError) {
        toastEl.style.background = 'linear-gradient(135deg,#ef4444,#b91c1c)';
    } else {
        toastEl.style.background = 'linear-gradient(135deg,#10b981,#047857)';
    }
    $('#toast-message').text(message);
    const toast = new bootstrap.Toast(toastEl, { delay: 2400 });
    toast.show();
}
