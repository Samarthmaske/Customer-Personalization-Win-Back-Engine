"""
ChurnEngine — Comprehensive Test Suite
Run: python test_app.py
Requires the Flask server to be running at http://127.0.0.1:5000
"""

import requests
import sys

BASE = 'http://127.0.0.1:5000'
RESULTS = []


def ok(label, cond, detail=''):
    status = 'PASS' if cond else 'FAIL'
    RESULTS.append(cond)
    marker = 'OK' if cond else 'XX'
    msg = f'  [{status}] {marker}  {label}'
    if detail:
        msg += f'  ->  {detail}'
    print(msg)


def section(title):
    print()
    print(f'--- {title} ---')


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Unauthenticated access protection
# ─────────────────────────────────────────────────────────────────────────────
section('1  Unauthenticated Access Protection')
s = requests.Session()
r = s.get(BASE + '/dashboard', allow_redirects=False)
ok('Dashboard redirects unauthenticated users', r.status_code == 302)
r = s.get(BASE + '/api/customers')
ok('GET /api/customers -> 403 when unauthenticated', r.status_code == 403)
r = s.get(BASE + '/api/activity-feed')
ok('GET /api/activity-feed -> 403 when unauthenticated', r.status_code == 403)
r = s.get(BASE + '/api/orders/all')
ok('GET /api/orders/all -> 403 when unauthenticated', r.status_code == 403)

# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Login flows
# ─────────────────────────────────────────────────────────────────────────────
section('2  Login Authentication')
admin = requests.Session()
r = admin.post(BASE + '/login', json={'username': 'admin', 'password': 'admin123'})
ok('Admin login -> 200', r.status_code == 200)
ok('Admin redirected to /dashboard', '/dashboard' in r.json().get('redirect', ''))

cust = requests.Session()
r = cust.post(BASE + '/login', json={'username': 'customer', 'password': 'customer123'})
ok('High-risk customer login -> 200', r.status_code == 200)
ok('Customer redirected to /storefront', '/storefront' in r.json().get('redirect', ''))

loyal = requests.Session()
r = loyal.post(BASE + '/login', json={'username': 'loyal', 'password': 'customer123'})
ok('Low-risk (loyal) customer login -> 200', r.status_code == 200)

bad = requests.Session()
r = bad.post(BASE + '/login', json={'username': 'hacker', 'password': 'wrong'})
ok('Invalid credentials -> 401', r.status_code == 401)

# ─────────────────────────────────────────────────────────────────────────────
# Test 2b: New user registration
# ─────────────────────────────────────────────────────────────────────────────
new_user = requests.Session()
r = new_user.post(BASE + '/register', json={
    'name': 'Newcomer User',
    'email': 'newcomer@example.com',
    'username': 'newcomer',
    'password': 'newpass123',
    'confirm_password': 'newpass123'
})
ok('New user registration -> 200', r.status_code == 200)
ok('Registration redirects to storefront', '/storefront' in r.json().get('redirect', ''))

r = new_user.get(BASE + '/storefront')
ok('Registered user can access storefront', r.status_code == 200)

weak_pass = requests.Session()
r = weak_pass.post(BASE + '/register', json={
    'name': 'Weak Password',
    'email': 'weak@example.com',
    'username': 'weakpass',
    'password': 'abc123',
    'confirm_password': 'abc123'
})
ok('Weak password is rejected', r.status_code == 400)

# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Admin dashboard APIs
# ─────────────────────────────────────────────────────────────────────────────
section('3  Admin Dashboard APIs')
r = admin.get(BASE + '/api/customers')
data = r.json()
ok('GET /api/customers -> 200', r.status_code == 200)
ok('Has at least 16 customers after registration', len(data['customers']) >= 16, f"got {len(data['customers'])}")
ok('A/B telemetry included in response', 'ab_telemetry' in data)
ok('All customers have RFM fields',
   all('recency' in c and 'frequency' in c and 'monetary' in c for c in data['customers']))
ok('All customers have churn_risk',
   all('churn_risk' in c for c in data['customers']))
ok('All customers have K-Means cluster label',
   all('cluster' in c for c in data['customers']))
ok('Cluster values are valid',
   all(c['cluster'] in ('Champions', 'Loyalists', 'At Risk', 'Lost') for c in data['customers']))

r = admin.get(BASE + '/api/activity-feed')
data = r.json()
ok('GET /api/activity-feed -> 200', r.status_code == 200)
ok('Response has "events" key', 'events' in data)
ok('Response returns at least 16 customers (live RFM)', len(data.get('customers', [])) >= 16)
ok('Response has total_orders counter', 'total_orders' in data)
ok('Response has total_revenue counter', 'total_revenue' in data)
ok('Response has ab_telemetry', 'ab_telemetry' in data)

r = admin.get(BASE + '/api/orders/all')
ok('GET /api/orders/all -> 200 for admin', r.status_code == 200)

r = cust.get(BASE + '/api/orders/all')
ok('GET /api/orders/all -> 403 for customer (role guard)', r.status_code == 403)

# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Win-back offer — high-risk customer (Akira Tanaka, risk=0.68)
# ─────────────────────────────────────────────────────────────────────────────
section('4  Win-Back Offer — High-Risk Customer')
r = cust.get(BASE + '/api/winback-offer')
data = r.json()
ok('GET /api/winback-offer -> 200', r.status_code == 200)
ok('Tier = Proactive Retention (0.40-0.70 range)',
   data.get('tier') == 'Proactive Retention', f"got: {data.get('tier')}")
ok('Coupon code present', bool(data.get('coupon_code')))
ok('Reward describes 15% off', '15%' in data.get('reward_value', ''))
ok('Risk score returned as float', isinstance(data.get('risk_score'), float))

# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Win-back offer — low-risk customer (Elena Rostova, risk=0.08)
# ─────────────────────────────────────────────────────────────────────────────
section('5  Win-Back Offer — Low-Risk Customer')
r = loyal.get(BASE + '/api/winback-offer')
data = r.json()
ok('Tier = Appreciation for low-risk user',
   data.get('tier') == 'Appreciation', f"got: {data.get('tier')}")
ok('Coupon = THANKS5 (5% discount)', data.get('coupon_code') == 'THANKS5',
   f"got: {data.get('coupon_code')}")
ok('Risk score < 0.40', data.get('risk_score', 1.0) < 0.40, f"risk={data.get('risk_score')}")

# ─────────────────────────────────────────────────────────────────────────────
# Test 6: AI Recommendations (personalised)
# ─────────────────────────────────────────────────────────────────────────────
section('6  AI Recommendations (Personalised by Cluster & Risk)')
r = cust.get(BASE + '/api/recommendations')
data = r.json()
ok('GET /api/recommendations -> 200', r.status_code == 200)
ok('Returns exactly 4 recommendations', len(data.get('recommendations', [])) == 4,
   f"got {len(data.get('recommendations', []))}")

discounts = [rec['discount'] for rec in data['recommendations']]
ok('High-risk (0.40-0.70) gets 15% discount', all(d == 15 for d in discounts),
   f"discounts={discounts}")
ok('discounted_price < original_price for all',
   all(rec['discounted_price'] < rec['original_price'] for rec in data['recommendations']))
ok('section_title is populated', bool(data.get('section_title')))
ok('section_subtitle mentions ChurnEngine AI', 'ChurnEngine' in data.get('section_subtitle', ''))

r_loyal = loyal.get(BASE + '/api/recommendations')
loyal_data = r_loyal.json()
loyal_discounts = [rec['discount'] for rec in loyal_data['recommendations']]
ok('Low-risk customer gets 5% discount', all(d == 5 for d in loyal_discounts),
   f"discounts={loyal_discounts}")

# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Cart CRUD
# ─────────────────────────────────────────────────────────────────────────────
section('7  Cart  —  Add / Update / Remove')
r = cust.get(BASE + '/api/cart')
data = r.json()
ok('Cart starts empty for fresh session', data.get('count', 99) == 0,
   f"count={data.get('count')}")

r = cust.post(BASE + '/api/cart/add', json={'product_id': 'PROD-001'})
data = r.json()
ok('Add PROD-001 (Jacket $129) -> 200', r.status_code == 200)
ok('Cart count = 1', data.get('cart_count') == 1)
ok('Cart total = 129.00', data.get('cart_total') == 129.0)

r = cust.post(BASE + '/api/cart/add', json={'product_id': 'PROD-004'})
data = r.json()
ok('Add PROD-004 (Sneakers $145) -> 200', r.status_code == 200)
ok('Cart count = 2 items', data.get('cart_count') == 2)
ok('Cart total = 274.00', data.get('cart_total') == 274.0)

# Add duplicate — should increment qty
cust.post(BASE + '/api/cart/add', json={'product_id': 'PROD-001'})
cart = cust.get(BASE + '/api/cart').json()
jacket = next((i for i in cart['items'] if i['product_id'] == 'PROD-001'), None)
ok('Duplicate add increments qty (qty=2 for Jacket)', jacket is not None and jacket['qty'] == 2)
ok('Cart count = 3 total items', cart.get('count') == 3)

# Update qty
r = cust.post(BASE + '/api/cart/update', json={'product_id': 'PROD-001', 'qty': 1})
ok('Update qty to 1 -> 200', r.status_code == 200)
cart = cust.get(BASE + '/api/cart').json()
jacket = next((i for i in cart['items'] if i['product_id'] == 'PROD-001'), None)
ok('Jacket qty updated to 1', jacket is not None and jacket['qty'] == 1)

# Update qty to 0 = remove
r = cust.post(BASE + '/api/cart/update', json={'product_id': 'PROD-004', 'qty': 0})
cart = cust.get(BASE + '/api/cart').json()
ok('Update qty=0 removes item from cart', not any(i['product_id'] == 'PROD-004' for i in cart['items']))

# Invalid product
r = cust.post(BASE + '/api/cart/add', json={'product_id': 'DOES-NOT-EXIST'})
ok('Invalid product_id -> 404', r.status_code == 404)

# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Order placement & RFM mutation
# ─────────────────────────────────────────────────────────────────────────────
section('8  Order Placement & Live RFM Mutation')
customers_before = admin.get(BASE + '/api/customers').json()['customers']
before = next(c for c in customers_before if c['id'] == 'CUST-003')
old_risk = before['churn_risk']
old_freq = before['frequency']
old_monetary = before['monetary']

# Cart currently has PROD-001 (qty=1, $129)
r = cust.post(BASE + '/api/orders', json={})
data = r.json()
ok('POST /api/orders -> 200', r.status_code == 200)
ok('Order ID follows ORD-XXXX format', data.get('order_id', '').startswith('ORD-'))
ok('Order total = 129.00', data.get('total') == 129.0, f"got {data.get('total')}")
ok('Order success message returned', 'confirmed' in data.get('message', '').lower())

cart_after = cust.get(BASE + '/api/cart').json()
ok('Cart cleared after order placement', cart_after.get('count') == 0)

# Verify live RFM mutation visible via admin API
customers_after = admin.get(BASE + '/api/customers').json()['customers']
after = next(c for c in customers_after if c['id'] == 'CUST-003')
ok('Recency reset to 0 after purchase', after['recency'] == 0, f"got {after['recency']}")
ok('Frequency incremented +1', after['frequency'] == old_freq + 1,
   f"{old_freq} -> {after['frequency']}")
ok('Monetary value increased by 129', after['monetary'] == round(old_monetary + 129.0, 2),
   f"{old_monetary} -> {after['monetary']}")
ok('Churn risk decreased after purchase', after['churn_risk'] < old_risk,
   f"{old_risk} -> {after['churn_risk']}")

# Empty cart order must return 400
r2 = cust.post(BASE + '/api/orders', json={})
ok('Empty cart order -> 400', r2.status_code == 400)

# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Live A/B telemetry update after order
# ─────────────────────────────────────────────────────────────────────────────
section('9  Live A/B Telemetry After Order')
r = admin.get(BASE + '/api/activity-feed')
data = r.json()
ok('Recovered revenue increased after order',
   data['ab_telemetry']['recovered_revenue'] > 45820.0,
   f"rev={data['ab_telemetry']['recovered_revenue']}")
ok('total_orders >= 1', data['total_orders'] >= 1)
ok('total_revenue > 0', data['total_revenue'] > 0)

# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Activity feed event types
# ─────────────────────────────────────────────────────────────────────────────
section('10 Live Activity Feed Events')
r = admin.get(BASE + '/api/activity-feed')
events = r.json()['events']
ok('Feed has events logged', len(events) > 0, f"count={len(events)}")

types = {e['type'] for e in events}
ok('order_placed events present', 'order_placed' in types)
ok('cart_add events present', 'cart_add' in types)
ok('page_view (login) events present', 'page_view' in types)
ok('All events have customer_name', all('customer_name' in e for e in events))
ok('All events have message text', all('message' in e for e in events))
ok('All events have timestamp', all('timestamp' in e for e in events))
ok('All event IDs are unique', len({e['id'] for e in events}) == len(events))

# ─────────────────────────────────────────────────────────────────────────────
# Test 11: Order history (customer-scoped)
# ─────────────────────────────────────────────────────────────────────────────
section('11 Order History (Customer-Scoped)')
r = cust.get(BASE + '/api/orders/history')
data = r.json()
ok('GET /api/orders/history -> 200', r.status_code == 200)
ok('Order history is not empty', len(data.get('orders', [])) > 0)
ok('All orders belong to CUST-003 only',
   all(o['customer_id'] == 'CUST-003' for o in data['orders']))
ok('Orders have required fields',
   all('order_id' in o and 'total' in o and 'status' in o for o in data['orders']))

# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Spin wheel audit log
# ─────────────────────────────────────────────────────────────────────────────
section('12 Gamification  —  Spin Wheel Audit Log')
r = cust.post(BASE + '/api/spin-wheel', json={'reward': '30% OFF', 'coupon': 'SPIN30'})
ok('POST /api/spin-wheel -> 200', r.status_code == 200)
ok('Response status = "logged"', r.json().get('status') == 'logged')
ok('Response includes customer_id', 'customer_id' in r.json())

# ─────────────────────────────────────────────────────────────────────────────
# Test 13: HTML page rendering
# ─────────────────────────────────────────────────────────────────────────────
section('13 HTML Page Rendering')
r = requests.get(BASE + '/login')
ok('GET /login -> 200', r.status_code == 200)
ok('Login page contains brand name', 'ChurnEngine' in r.text)
ok('Login page has demo preset buttons', 'demo-preset-btn' in r.text)
ok('Login page loads custom CSS', 'style.css' in r.text)

r = admin.get(BASE + '/dashboard')
ok('GET /dashboard (admin) -> 200', r.status_code == 200)
ok('Dashboard contains churn table', 'churn-table' in r.text)
ok('Dashboard contains cluster chart canvas', 'clusterChart' in r.text)
ok('Dashboard contains new activity-feed-list', 'activity-feed-list' in r.text)
ok('Dashboard contains new orders-table-body', 'orders-table-body' in r.text)
ok('Dashboard contains live-dot element', 'live-dot' in r.text)
ok('Dashboard loads dashboard.js', 'dashboard.js' in r.text)

r = cust.get(BASE + '/storefront')
ok('GET /storefront (customer) -> 200', r.status_code == 200)
ok('Storefront contains product cards', 'product-card' in r.text)
ok('Storefront contains spin wheel canvas', 'wheel-canvas' in r.text)
ok('Storefront contains winback banner', 'retention-banner-container' in r.text)
ok('Storefront contains recommendations grid', 'recommendations-grid' in r.text)
ok('Storefront contains cart offcanvas', 'cartOffcanvas' in r.text)

# ─────────────────────────────────────────────────────────────────────────────
# Test 14: Logout & session cleanup
# ─────────────────────────────────────────────────────────────────────────────
section('14 Logout & Session Cleanup')
r = admin.get(BASE + '/logout', allow_redirects=False)
ok('GET /logout (admin) -> 302 redirect', r.status_code == 302)
r = admin.get(BASE + '/api/customers')
ok('Session cleared — /api/customers -> 403 after logout', r.status_code == 403)

r = cust.get(BASE + '/logout', allow_redirects=False)
ok('GET /logout (customer) -> 302', r.status_code == 302)

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
passed = sum(RESULTS)
total  = len(RESULTS)
failed = total - passed

print()
print('=' * 60)
if failed == 0:
    print(f'  ALL {total} TESTS PASSED')
else:
    print(f'  {passed}/{total} PASSED  ---  {failed} FAILED')
print('=' * 60)
print()

sys.exit(0 if failed == 0 else 1)
