import os
import random
import datetime
import json
import time
import hashlib
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'super_secret_churn_key_2026'

# ---------------------------------------------------------------------------
# CUSTOMER DATABASE  (Simulates LightGBM + K-Means output)
# ---------------------------------------------------------------------------
CUSTOMERS = [
    {"id": "CUST-001", "name": "Elena Rostova", "recency": 4, "frequency": 42, "monetary": 1850.50, "churn_risk": 0.08, "cluster": "Champions", "x": 42, "y": 1850, "email": "elena.r@example.com"},
    {"id": "CUST-002", "name": "Marcus Vance", "recency": 140, "frequency": 3, "monetary": 45.00, "churn_risk": 0.92, "cluster": "Lost", "x": 3, "y": 45, "email": "marcus.v@example.com"},
    {"id": "CUST-003", "name": "Akira Tanaka", "recency": 52, "frequency": 8, "monetary": 320.00, "churn_risk": 0.68, "cluster": "At Risk", "x": 8, "y": 320, "email": "akira.t@example.com"},
    {"id": "CUST-004", "name": "Sarah Jenkins", "recency": 8, "frequency": 28, "monetary": 1210.00, "churn_risk": 0.12, "cluster": "Loyalists", "x": 28, "y": 1210, "email": "sarah.j@example.com"},
    {"id": "CUST-005", "name": "David Alaba", "recency": 95, "frequency": 5, "monetary": 190.00, "churn_risk": 0.84, "cluster": "At Risk", "x": 5, "y": 190, "email": "david.a@example.com"},
    {"id": "CUST-006", "name": "Chloe Dupont", "recency": 3, "frequency": 35, "monetary": 1640.00, "churn_risk": 0.05, "cluster": "Champions", "x": 35, "y": 1640, "email": "chloe.d@example.com"},
    {"id": "CUST-007", "name": "Mateo Rossi", "recency": 110, "frequency": 2, "monetary": 30.00, "churn_risk": 0.95, "cluster": "Lost", "x": 2, "y": 30, "email": "mateo.r@example.com"},
    {"id": "CUST-008", "name": "Amina Bello", "recency": 45, "frequency": 12, "monetary": 580.00, "churn_risk": 0.45, "cluster": "Loyalists", "x": 12, "y": 580, "email": "amina.b@example.com"},
    {"id": "CUST-009", "name": "Siddharth Mehta", "recency": 68, "frequency": 6, "monetary": 220.00, "churn_risk": 0.72, "cluster": "At Risk", "x": 6, "y": 220, "email": "siddharth.m@example.com"},
    {"id": "CUST-010", "name": "Emily Watson", "recency": 12, "frequency": 22, "monetary": 950.00, "churn_risk": 0.18, "cluster": "Loyalists", "x": 22, "y": 950, "email": "emily.w@example.com"},
    {"id": "CUST-011", "name": "Liam O'Connor", "recency": 18, "frequency": 19, "monetary": 780.00, "churn_risk": 0.22, "cluster": "Loyalists", "x": 19, "y": 780, "email": "liam.o@example.com"},
    {"id": "CUST-012", "name": "Yuki Sato", "recency": 150, "frequency": 1, "monetary": 15.00, "churn_risk": 0.98, "cluster": "Lost", "x": 1, "y": 15, "email": "yuki.s@example.com"},
    {"id": "CUST-013", "name": "Carlos Gomez", "recency": 5, "frequency": 49, "monetary": 2450.00, "churn_risk": 0.02, "cluster": "Champions", "x": 49, "y": 2450, "email": "carlos.g@example.com"},
    {"id": "CUST-014", "name": "Fatima Al-Sayed", "recency": 85, "frequency": 4, "monetary": 140.00, "churn_risk": 0.81, "cluster": "At Risk", "x": 4, "y": 140, "email": "fatima.as@example.com"},
    {"id": "CUST-015", "name": "Oliver Hansen", "recency": 30, "frequency": 15, "monetary": 610.00, "churn_risk": 0.38, "cluster": "Loyalists", "x": 15, "y": 610, "email": "oliver.h@example.com"},
]

# ---------------------------------------------------------------------------
# A/B TESTING TELEMETRY
# ---------------------------------------------------------------------------
AB_TEST_METRICS = {
    "control_group_size": 5000,
    "treatment_group_size": 5000,
    "control_churn_rate": 18.4,
    "treatment_churn_rate": 12.1,
    "recovered_revenue": 45820.00,
    "campaign_roi": 324.5
}

# ---------------------------------------------------------------------------
# PRODUCT CATALOG
# ---------------------------------------------------------------------------
PRODUCTS = [
    {"id": "PROD-001", "name": "Eco-Cotton Utility Jacket", "category": "Apparel",     "price": 129.00, "img": "img/product_jacket.png",   "rating": 4.8, "reviews": 124},
    {"id": "PROD-002", "name": "Minimalist Canvas Backpack","category": "Accessories", "price": 85.00,  "img": "img/product_backpack.png", "rating": 4.5, "reviews": 89},
    {"id": "PROD-003", "name": "Linen Resort Collar Shirt", "category": "Apparel",     "price": 65.00,  "img": "img/product_shirt.png",    "rating": 4.6, "reviews": 201},
    {"id": "PROD-004", "name": "Aero-Breathe Knit Sneakers","category": "Footwear",    "price": 145.00, "img": "img/product_sneakers.png", "rating": 4.9, "reviews": 312},
]

# ---------------------------------------------------------------------------
# PREDEFINED USER ACCOUNTS
# ---------------------------------------------------------------------------
USERS = {
    "admin": {
        "username": "admin",
        "password": generate_password_hash("admin123"),
        "role": "admin",
        "name": "Analytics Manager"
    },
    "customer": {
        "username": "customer",
        "password": generate_password_hash("customer123"),
        "role": "customer",
        "name": "Akira Tanaka",
        "cust_id": "CUST-003",
        "email": "akira.t@example.com"
    },
    "loyal": {
        "username": "loyal",
        "password": generate_password_hash("customer123"),
        "role": "customer",
        "name": "Elena Rostova",
        "cust_id": "CUST-001",
        "email": "elena.r@example.com"
    }
}


def generate_customer_id():
    existing_ids = [int(c['id'].split('-')[1]) for c in CUSTOMERS if c['id'].startswith('CUST-')]
    next_id = max(existing_ids, default=0) + 1
    return f"CUST-{next_id:03d}"


def get_default_customer_profile(name, email, customer_id):
    return {
        "id": customer_id,
        "name": name,
        "recency": 0,
        "frequency": 0,
        "monetary": 0.00,
        "churn_risk": 0.50,
        "cluster": "At Risk",
        "x": 0,
        "y": 0,
        "email": email
    }


def push_user_to_cloudinary(payload):
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
    api_key = os.getenv('CLOUDINARY_API_KEY')
    api_secret = os.getenv('CLOUDINARY_API_SECRET')

    if not (cloud_name and api_key and api_secret):
        return {"status": "skipped", "reason": "Cloudinary credentials not configured"}

    endpoint = f"https://api.cloudinary.com/v1_1/{cloud_name}/raw/upload"
    timestamp = int(time.time())
    payload_str = json.dumps(payload)
    params = {
        "folder": "churnengine/users",
        "tags": "churnengine,new_user",
        "timestamp": timestamp
    }
    to_sign = '&'.join([f"{key}={params[key]}" for key in sorted(params)])
    signature = hashlib.sha1((to_sign + api_secret).encode('utf-8')).hexdigest()

    data = {
        "api_key": api_key,
        "timestamp": timestamp,
        "signature": signature,
        "folder": params['folder'],
        "tags": params['tags']
    }
    files = {"file": ("new_user.json", payload_str, "application/json")}

    try:
        response = requests.post(endpoint, data=data, files=files, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}

# ---------------------------------------------------------------------------
# IN-MEMORY STORES
# ---------------------------------------------------------------------------
CART_DATA = {}      # { customer_id: [ {product_id, name, price, img, qty} ] }
ORDERS = []         # [ {order_id, customer_id, customer_name, items, total, status, timestamp, item_count} ]
ACTIVITY_FEED = []  # [ {id, type, customer_id, customer_name, message, timestamp} ]
_order_counter = 1001


def log_activity(activity_type, cust_id, cust_name, message, extra=None):
    """Append event to the live activity feed (newest first, capped at 100)."""
    event = {
        "id": len(ACTIVITY_FEED) + 1,
        "type": activity_type,   # cart_add | order_placed | page_view
        "customer_id": cust_id,
        "customer_name": cust_name,
        "message": message,
        "timestamp": datetime.datetime.now().strftime("%I:%M %p"),
    }
    if extra:
        event.update(extra)
    ACTIVITY_FEED.insert(0, event)
    if len(ACTIVITY_FEED) > 100:
        ACTIVITY_FEED.pop()


# ===========================================================================
# CORE PAGE ROUTES
# ===========================================================================

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard') if session['role'] == 'admin' else url_for('storefront'))
    return redirect(url_for('login_page'))


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        data = request.get_json() or request.form
        username = (data.get('username') or '').strip()
        password = data.get('password')

        user = USERS.get(username)
        if user and check_password_hash(user['password'], password):
            session['user'] = user['name']
            session['role'] = user['role']

            if user['role'] == 'admin':
                return jsonify({"status": "success", "redirect": url_for('dashboard')})

            session['cust_id'] = user['cust_id']
            log_activity("page_view", user['cust_id'], user['name'], "Logged in — browsing the storefront")
            return jsonify({"status": "success", "redirect": url_for('storefront')})

        return jsonify({"status": "error", "message": "Invalid username or password."}), 401

    return render_template('login.html')


@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json() or request.form
    username = (data.get('username') or '').strip()
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()

    if not username or not password or not confirm_password or not name or not email:
        return jsonify({"status": "error", "message": "All fields are required for registration."}), 400
    if password != confirm_password:
        return jsonify({"status": "error", "message": "Passwords do not match."}), 400
    if len(password) < 8:
        return jsonify({"status": "error", "message": "Password must be at least 8 characters long."}), 400
    if not any(char.isdigit() for char in password) or not any(char.isalpha() for char in password):
        return jsonify({"status": "error", "message": "Password must include both letters and numbers."}), 400
    if username in USERS:
        return jsonify({"status": "error", "message": "Username already exists."}), 409
    if any(u.get('email') == email for u in USERS.values()):
        return jsonify({"status": "error", "message": "Email is already registered."}), 409

    customer_id = generate_customer_id()
    USERS[username] = {
        "username": username,
        "password": generate_password_hash(password),
        "role": "customer",
        "name": name,
        "cust_id": customer_id,
        "email": email
    }

    new_customer = get_default_customer_profile(name, email, customer_id)
    CUSTOMERS.append(new_customer)
    cloudinary_response = push_user_to_cloudinary({
        "customer_id": customer_id,
        "username": username,
        "name": name,
        "email": email,
        "registered_at": datetime.datetime.utcnow().isoformat() + 'Z',
        "customer_profile": new_customer
    })

    session['user'] = name
    session['role'] = 'customer'
    session['cust_id'] = customer_id
    log_activity("page_view", customer_id, name, "New user registered and logged in")

    return jsonify({
        "status": "success",
        "redirect": url_for('storefront'),
        "cloudinary": cloudinary_response
    })


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/dashboard')
def dashboard():
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login_page'))
    return render_template('dashboard.html', user=session['user'])


@app.route('/storefront')
def storefront():
    cust_id = session.get('cust_id', 'GUEST')
    customer_name = session.get('user', 'Guest Customer')
    customer_info = next((c for c in CUSTOMERS if c['id'] == cust_id), None)
    churn_risk = customer_info['churn_risk'] if customer_info else 0.20
    return render_template('storefront.html', customer_name=customer_name, cust_id=cust_id, churn_risk=churn_risk)


# ===========================================================================
# ML ANALYTICS API
# ===========================================================================

@app.route('/api/customers', methods=['GET'])
def get_customers():
    if 'user' not in session or session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify({"customers": CUSTOMERS, "ab_telemetry": AB_TEST_METRICS})


@app.route('/api/winback-offer', methods=['GET'])
def get_winback_offer():
    cust_id = session.get('cust_id', 'GUEST')
    customer_info = next((c for c in CUSTOMERS if c['id'] == cust_id), None)
    risk = customer_info['churn_risk'] if customer_info else 0.25

    if risk >= 0.70:
        offer = {"tier": "Critical Winback", "risk_score": risk,
                 "banner_title": "🌟 VIP Exclusive Offer Just For You!",
                 "banner_text": "We miss you! Get 30% OFF your next order plus FREE shipping instantly.",
                 "coupon_code": "RETENTION30VIP", "reward_value": "30% OFF + Free Shipping",
                 "button_text": "Copy & Claim 30% Discount"}
    elif risk >= 0.40:
        offer = {"tier": "Proactive Retention", "risk_score": risk,
                 "banner_title": "🎁 Special Loyalty Gift",
                 "banner_text": "Enjoy 15% OFF your cart value as a token of our appreciation.",
                 "coupon_code": "LOYALTY15", "reward_value": "15% OFF",
                 "button_text": "Copy & Activate 15% Coupon"}
    else:
        offer = {"tier": "Appreciation", "risk_score": risk,
                 "banner_title": "✨ Thanks for being our customer!",
                 "banner_text": "Here's a 5% discount code for your next purchase.",
                 "coupon_code": "THANKS5", "reward_value": "5% OFF",
                 "button_text": "Copy 5% Coupon"}
    return jsonify(offer)


@app.route('/api/spin-wheel', methods=['POST'])
def post_spin_result():
    data = request.get_json() or {}
    cust_id = session.get('cust_id', 'GUEST')
    customer_info = next((c for c in CUSTOMERS if c['id'] == cust_id), None)
    risk = customer_info['churn_risk'] if customer_info else 0.30
    reward = data.get('reward')
    print(f"[AUDIT LOG] Gamification: Customer {cust_id} (Risk: {risk*100:.0f}%) won: {reward}")
    return jsonify({"status": "logged", "message": f"Reward '{reward}' saved.", "customer_id": cust_id})


# ===========================================================================
# CART API
# ===========================================================================

@app.route('/api/cart', methods=['GET'])
def get_cart():
    """Return the current customer's full cart."""
    cust_id = session.get('cust_id', 'GUEST')
    cart = CART_DATA.get(cust_id, [])
    total = sum(item['price'] * item['qty'] for item in cart)
    return jsonify({
        "items": cart,
        "total": round(total, 2),
        "count": sum(item['qty'] for item in cart)
    })


@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    """Add a product to the customer's cart and log event to activity feed."""
    cust_id = session.get('cust_id', 'GUEST')
    cust_name = session.get('user', 'Guest')
    data = request.get_json() or {}
    product_id = data.get('product_id')

    product = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    if cust_id not in CART_DATA:
        CART_DATA[cust_id] = []

    cart = CART_DATA[cust_id]
    existing = next((i for i in cart if i['product_id'] == product_id), None)
    if existing:
        existing['qty'] += 1
    else:
        cart.append({
            "product_id": product_id,
            "name": product['name'],
            "price": product['price'],
            "img": product['img'],
            "qty": 1
        })

    total = sum(i['price'] * i['qty'] for i in cart)
    count = sum(i['qty'] for i in cart)

    log_activity("cart_add", cust_id, cust_name,
                 f"Added <strong>{product['name']}</strong> to cart",
                 {"product": product['name'], "price": product['price']})

    return jsonify({
        "status": "success",
        "cart_count": count,
        "cart_total": round(total, 2),
        "message": f"{product['name']} added to cart"
    })


@app.route('/api/cart/remove', methods=['POST'])
def remove_from_cart():
    """Remove a specific product from the cart."""
    cust_id = session.get('cust_id', 'GUEST')
    data = request.get_json() or {}
    product_id = data.get('product_id')

    if cust_id in CART_DATA:
        CART_DATA[cust_id] = [i for i in CART_DATA[cust_id] if i['product_id'] != product_id]

    cart = CART_DATA.get(cust_id, [])
    total = sum(i['price'] * i['qty'] for i in cart)
    count = sum(i['qty'] for i in cart)
    return jsonify({"status": "success", "cart_count": count, "cart_total": round(total, 2)})


@app.route('/api/cart/update', methods=['POST'])
def update_cart():
    """Update quantity of a product in the cart (qty=0 removes it)."""
    cust_id = session.get('cust_id', 'GUEST')
    data = request.get_json() or {}
    product_id = data.get('product_id')
    qty = int(data.get('qty', 1))

    if cust_id in CART_DATA:
        if qty <= 0:
            CART_DATA[cust_id] = [i for i in CART_DATA[cust_id] if i['product_id'] != product_id]
        else:
            for item in CART_DATA[cust_id]:
                if item['product_id'] == product_id:
                    item['qty'] = qty
                    break

    cart = CART_DATA.get(cust_id, [])
    total = sum(i['price'] * i['qty'] for i in cart)
    count = sum(i['qty'] for i in cart)
    return jsonify({"status": "success", "cart_count": count, "cart_total": round(total, 2)})


# ===========================================================================
# ORDER API
# ===========================================================================

@app.route('/api/orders', methods=['POST'])
def place_order():
    """
    Place an order from the customer's cart.
    IMPORTANT: Mutates the customer's RFM fields (recency, frequency, monetary, churn_risk)
    so the manager dashboard reflects real-time changes instantly.
    """
    global _order_counter
    cust_id = session.get('cust_id', 'GUEST')
    cust_name = session.get('user', 'Guest')
    cart = CART_DATA.get(cust_id, [])

    if not cart:
        return jsonify({"error": "Cart is empty"}), 400

    total = sum(i['price'] * i['qty'] for i in cart)
    order_id = f"ORD-{_order_counter}"
    _order_counter += 1

    order = {
        "order_id": order_id,
        "customer_id": cust_id,
        "customer_name": cust_name,
        "items": [dict(i) for i in cart],
        "total": round(total, 2),
        "status": "Confirmed",
        "timestamp": datetime.datetime.now().strftime("%I:%M %p"),
        "item_count": sum(i['qty'] for i in cart)
    }
    ORDERS.insert(0, order)
    CART_DATA[cust_id] = []  # clear cart after order

    # --- LIVE RFM MUTATION ---
    # This makes the manager dashboard reflect the purchase in real-time.
    customer_info = next((c for c in CUSTOMERS if c['id'] == cust_id), None)
    if customer_info:
        customer_info['monetary'] = round(customer_info['monetary'] + total, 2)
        customer_info['frequency'] += 1
        customer_info['recency'] = 0
        customer_info['x'] = customer_info['frequency']
        customer_info['y'] = int(customer_info['monetary'])
        # Successful purchase reduces churn risk (winback conversion)
        new_risk = round(max(0.03, customer_info['churn_risk'] - 0.15), 2)
        customer_info['churn_risk'] = new_risk
        # Upgrade cluster if risk dropped significantly
        if new_risk < 0.15 and customer_info['cluster'] in ('At Risk', 'Lost'):
            customer_info['cluster'] = 'Loyalists'
        elif new_risk < 0.40 and customer_info['cluster'] == 'Lost':
            customer_info['cluster'] = 'At Risk'
    # Update A/B recovered revenue metric
    AB_TEST_METRICS['recovered_revenue'] = round(AB_TEST_METRICS['recovered_revenue'] + total, 2)

    items_summary = ", ".join([f"{i['name']} x{i['qty']}" for i in cart[:2]])
    if len(cart) > 2:
        items_summary += f" +{len(cart)-2} more"

    log_activity("order_placed", cust_id, cust_name,
                 f"Placed order <strong>{order_id}</strong> — {items_summary}",
                 {"order_id": order_id, "total": round(total, 2), "item_count": len(cart)})

    return jsonify({
        "status": "success",
        "order_id": order_id,
        "total": round(total, 2),
        "message": f"Order {order_id} confirmed!"
    })


@app.route('/api/orders/history', methods=['GET'])
def get_order_history():
    """Customer's own order history."""
    cust_id = session.get('cust_id', 'GUEST')
    customer_orders = [o for o in ORDERS if o['customer_id'] == cust_id]
    return jsonify({"orders": customer_orders})


@app.route('/api/orders/all', methods=['GET'])
def get_all_orders():
    """All orders — manager only."""
    if 'user' not in session or session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify({"orders": ORDERS, "total": len(ORDERS)})


# ===========================================================================
# RECOMMENDATIONS API
# ===========================================================================

@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    """
    ML-driven product recommendations.
    Uses the customer's cluster and churn_risk to personalise:
    - Discount tier  (30% / 15% / 5%)
    - Badge label    (VIP Deal / Just For You / Member Pick)
    - Reason text    (Exclusive offer / Handpicked / Trending)
    """
    cust_id = session.get('cust_id', 'GUEST')
    customer_info = next((c for c in CUSTOMERS if c['id'] == cust_id), None)
    cluster = customer_info['cluster'] if customer_info else 'General'
    risk = customer_info['churn_risk'] if customer_info else 0.25

    shuffled = random.sample(PRODUCTS, len(PRODUCTS))
    recommendations = []

    for prod in shuffled:
        rec = dict(prod)
        if risk >= 0.70:
            rec['discount'] = 30;  rec['badge'] = '🔥 VIP Deal';      rec['badge_color'] = '#ef4444'
            rec['reason'] = 'Exclusive winback offer just for you'
        elif risk >= 0.40:
            rec['discount'] = 15;  rec['badge'] = '🎯 Just For You';   rec['badge_color'] = '#f59e0b'
            rec['reason'] = 'Handpicked based on your profile'
        else:
            rec['discount'] = 5;   rec['badge'] = '⭐ Member Pick';    rec['badge_color'] = '#10b981'
            rec['reason'] = 'Popular with loyal customers like you'

        if cluster == 'Champions':
            rec['reason'] = 'Trending among top customers'
        elif cluster == 'Loyalists':
            rec['reason'] = 'Popular with loyal members'

        rec['original_price'] = prod['price']
        rec['discounted_price'] = round(prod['price'] * (1 - rec['discount'] / 100), 2)
        recommendations.append(rec)

    return jsonify({
        "recommendations": recommendations,
        "cluster": cluster,
        "risk_score": risk,
        "section_title": "🎯 Special Deals Picked For You" if risk >= 0.40 else "Recommended for You",
        "section_subtitle": f"Personalised by ChurnEngine AI · {cluster} Segment"
    })


# ===========================================================================
# MANAGER LIVE ACTIVITY FEED API
# ===========================================================================

@app.route('/api/activity-feed', methods=['GET'])
def get_activity_feed():
    """
    Real-time activity feed for the manager dashboard.
    Returns new events since `since_id`, plus up-to-date customer data
    (including RFM mutations caused by orders) for instant dashboard refresh.
    """
    if 'user' not in session or session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403

    since_id = request.args.get('since_id', 0, type=int)
    new_events = [e for e in ACTIVITY_FEED if e['id'] > since_id] if since_id > 0 else ACTIVITY_FEED[:20]

    return jsonify({
        "events": new_events,
        "total_orders": len(ORDERS),
        "total_revenue": round(sum(o['total'] for o in ORDERS), 2),
        "customers": CUSTOMERS,          # live-mutated RFM data
        "ab_telemetry": AB_TEST_METRICS  # live-updated recovered_revenue
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)
