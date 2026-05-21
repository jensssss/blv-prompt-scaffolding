from flask import Flask, request, jsonify, render_template
from functools import wraps
from datetime import datetime, timedelta
from uuid import uuid4
import random
import string
import math

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

PRODUCTS = {
    'P001': {
        'id': 'P001',
        'name': 'Nasi Goreng Special',
        'price': 25000,
        'category': 'food',
        'description': 'Classic Indonesian fried rice with egg, chicken, and house-made sambal',
        'stock': 100,
    },
    'P002': {
        'id': 'P002',
        'name': 'Mie Ayam Bakso',
        'price': 20000,
        'category': 'food',
        'description': 'Chicken noodle soup served with tender meatballs and crispy wontons',
        'stock': 80,
    },
    'P003': {
        'id': 'P003',
        'name': 'Es Teh Manis',
        'price': 8000,
        'category': 'drink',
        'description': 'Sweet iced tea, freshly brewed and served over ice',
        'stock': 200,
    },
    'P004': {
        'id': 'P004',
        'name': 'Jus Alpukat Segar',
        'price': 18000,
        'category': 'drink',
        'description': 'Fresh avocado juice blended with condensed milk and a dash of chocolate syrup',
        'stock': 50,
    },
    'P005': {
        'id': 'P005',
        'name': 'Kopi Susu Kekinian',
        'price': 22000,
        'category': 'drink',
        'description': 'Trendy Indonesian milk coffee with a caramel drizzle and oat milk option',
        'stock': 150,
    },
    'P006': {
        'id': 'P006',
        'name': 'Dish Washing Liquid 500ml',
        'price': 15000,
        'category': 'household',
        'description': 'Concentrated dish washing liquid with fresh lemon fragrance, cuts through grease',
        'stock': 60,
    },
    'P007': {
        'id': 'P007',
        'name': 'Laundry Detergent Powder 1kg',
        'price': 35000,
        'category': 'household',
        'description': 'High-efficiency laundry powder suitable for all fabric types and washing machines',
        'stock': 40,
    },
    'P008': {
        'id': 'P008',
        'name': 'Cooking Oil 1L',
        'price': 28000,
        'category': 'grocery',
        'description': 'Pure refined palm cooking oil, cholesterol-free and suitable for frying or sauteing',
        'stock': 75,
    },
}

SUBSCRIPTION_PLANS = {
    'basic': {
        'id': 'basic',
        'name': 'Basic',
        'price_monthly': 0,
        'features': [
            'Standard shipping rates',
            'Regular customer support',
            'Order history access',
        ],
        'free_shipping': False,
        'order_discount_pct': 0,
        'api_access': False,
        'bulk_ordering': False,
    },
    'premium': {
        'id': 'premium',
        'name': 'Premium',
        'price_monthly': 99000,
        'features': [
            'Free shipping on all orders',
            '10% discount on every order',
            'Priority customer support',
        ],
        'free_shipping': True,
        'order_discount_pct': 10,
        'api_access': False,
        'bulk_ordering': False,
    },
    'enterprise': {
        'id': 'enterprise',
        'name': 'Enterprise',
        'price_monthly': 299000,
        'features': [
            'Free shipping on all orders',
            '10% discount on every order',
            'Priority customer support',
            'API access for integrations',
            'Bulk ordering support',
            'Dedicated account manager',
        ],
        'free_shipping': True,
        'order_discount_pct': 10,
        'api_access': True,
        'bulk_ordering': True,
    },
}

GIFT_CARD_DENOMINATIONS = [50000, 100000, 200000, 500000]

SHIPPING_RATES = {
    'regular': {'label': 'Regular Delivery', 'cost': 15000, 'eta': '3-5 business days'},
    'express': {'label': 'Express Delivery', 'cost': 25000, 'eta': '1-2 business days'},
    'same_day': {'label': 'Same Day Delivery', 'cost': 45000, 'eta': 'Today by 9 PM'},
}

# ---------------------------------------------------------------------------
# Runtime storage
# ---------------------------------------------------------------------------

users = {}
sessions = {}
carts = {}
checkout_sessions = {}
orders = {}
vouchers = {}
gift_cards = {}
subscriptions = {}
return_requests = {}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_str():
    return datetime.utcnow().isoformat() + 'Z'

def generate_token():
    return str(uuid4())

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def ok(data=None, message=None, status_code=200):
    resp = {'success': True}
    if message:
        resp['message'] = message
    if data is not None:
        resp['data'] = data
    return jsonify(resp), status_code

def fail(message, status_code=400):
    return jsonify({'success': False, 'error': message}), status_code

def get_token_from_header():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    return None

def get_current_user():
    token = get_token_from_header()
    if not token or token not in sessions:
        return None, None
    session = sessions[token]
    user_id = session['user_id']
    return user_id, users.get(user_id)

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()
        if not token or token not in sessions:
            return fail('Authentication required', 401)
        if not sessions[token].get('authenticated'):
            return fail('Authentication required', 401)
        return f(*args, **kwargs)
    return decorated

def require_2fa(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()
        if not token or token not in sessions:
            return fail('Authentication required', 401)
        if not sessions[token].get('authenticated'):
            return fail('Authentication required', 401)
        if not sessions[token].get('two_fa_verified'):
            return fail('Two-factor authentication verification required', 403)
        return f(*args, **kwargs)
    return decorated

def get_active_subscription(user_id):
    sub = subscriptions.get(user_id)
    if not sub or not sub.get('active'):
        return None
    expires = sub.get('expires_at')
    if expires:
        try:
            if datetime.fromisoformat(expires.replace('Z', '')) < datetime.utcnow():
                subscriptions[user_id]['active'] = False
                return None
        except ValueError:
            pass
    return sub

def recalculate_checkout_total(cs):
    item_total = sum(item['price'] * item['quantity'] for item in cs.get('items', []))
    shipping_cost = cs.get('shipping_cost', 0)
    discount_amount = cs.get('discount_amount', 0)
    balance_applied = cs.get('balance_applied', 0)
    total = max(0, item_total + shipping_cost - discount_amount - balance_applied)
    cs['item_total'] = item_total
    cs['total'] = total
    return cs

def loyalty_points_for(order_total):
    return math.floor(order_total / 100000) * 10

# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')

# ---------------------------------------------------------------------------
# Flow 2 + 3: Authentication and Registration
# ---------------------------------------------------------------------------

@app.route('/api/auth/register', methods=['POST'])
def register():
    body = request.get_json() or {}
    name = (body.get('name') or '').strip()
    email = (body.get('email') or '').strip().lower()
    phone = (body.get('phone') or '').strip()
    password = (body.get('password') or '').strip()

    if not all([name, email, phone, password]):
        return fail('name, email, phone, and password are required')

    for u in users.values():
        if u['email'] == email:
            return fail('An account with this email already exists')

    user_id = 'USR-' + str(uuid4()).replace('-', '')[:8].upper()
    otp = generate_otp()
    token = generate_token()

    users[user_id] = {
        'id': user_id,
        'name': name,
        'email': email,
        'phone': phone,
        'password': password,
        'email_verified': False,
        'profile_complete': False,
        'address': None,
        'date_of_birth': None,
        'welcome_bonus_claimed': False,
        'balance': 0,
        'loyalty_points': 0,
        'otp': otp,
        'otp_2fa': None,
        'pending_otp': otp,
        'otp_purpose': 'email_verification',
        'created_at': now_str(),
    }

    sessions[token] = {
        'user_id': user_id,
        'authenticated': True,
        'two_fa_verified': False,
    }

    return ok({
        'user_id': user_id,
        'token': token,
        'otp': otp,
    }, 'Registration successful. Use the OTP to verify your email.', 201)


@app.route('/api/auth/verify-email', methods=['POST'])
@require_auth
def verify_email():
    user_id, user = get_current_user()
    if not user:
        return fail('User not found', 404)

    body = request.get_json() or {}
    otp = (body.get('otp') or '').strip()

    if not otp:
        return fail('otp is required')

    if user.get('email_verified'):
        return fail('Email address is already verified')

    if user.get('pending_otp') != otp or user.get('otp_purpose') != 'email_verification':
        return fail('Invalid or expired OTP')

    users[user_id]['email_verified'] = True
    users[user_id]['pending_otp'] = None
    users[user_id]['otp_purpose'] = None

    return ok({'email': user['email'], 'email_verified': True}, 'Email verified successfully')


@app.route('/api/auth/complete-profile', methods=['POST'])
@require_auth
def complete_profile():
    user_id, user = get_current_user()
    if not user:
        return fail('User not found', 404)

    body = request.get_json() or {}
    full_address = (body.get('full_address') or '').strip()
    city = (body.get('city') or '').strip()
    province = (body.get('province') or '').strip()
    postal_code = (body.get('postal_code') or '').strip()
    date_of_birth = (body.get('date_of_birth') or '').strip()

    if not all([full_address, city, postal_code, date_of_birth]):
        return fail('full_address, city, postal_code, and date_of_birth are required')

    users[user_id]['address'] = {
        'full_address': full_address,
        'city': city,
        'province': province,
        'postal_code': postal_code,
    }
    users[user_id]['date_of_birth'] = date_of_birth
    users[user_id]['profile_complete'] = True

    return ok({
        'profile_complete': True,
        'address': users[user_id]['address'],
        'date_of_birth': date_of_birth,
    }, 'Profile completed successfully')


@app.route('/api/auth/profile', methods=['PUT'])
@require_auth
def update_profile():
    user_id, user = get_current_user()
    if not user:
        return fail('User not found', 404)

    body = request.get_json() or {}
    name = (body.get('name') or '').strip()
    phone = (body.get('phone') or '').strip()
    full_address = (body.get('full_address') or '').strip()
    city = (body.get('city') or '').strip()
    postal_code = (body.get('postal_code') or '').strip()
    date_of_birth = (body.get('date_of_birth') or '').strip()

    if name:
        users[user_id]['name'] = name
    if phone:
        users[user_id]['phone'] = phone
    if date_of_birth:
        users[user_id]['date_of_birth'] = date_of_birth
    if full_address or city or postal_code:
        addr = users[user_id].get('address') or {}
        if full_address:
            addr['full_address'] = full_address
        if city:
            addr['city'] = city
        if postal_code:
            addr['postal_code'] = postal_code
        users[user_id]['address'] = addr

    # Reset onboarding flow on profile change for support cases
    users[user_id]['welcome_bonus_claimed'] = False
    for vid, v in vouchers.items():
        if v.get('user_id') == user_id and v.get('type') == 'welcome_bonus' and v.get('status') == 'active':
            vouchers[vid]['status'] = 'expired'

    return ok({
        'name': users[user_id]['name'],
        'phone': users[user_id]['phone'],
        'address': users[user_id].get('address'),
        'date_of_birth': users[user_id].get('date_of_birth'),
    }, 'Profile updated successfully')


@app.route('/api/auth/claim-welcome-bonus', methods=['POST'])
@require_auth
def claim_welcome_bonus():
    user_id, user = get_current_user()
    if not user:
        return fail('User not found', 404)

    if not user.get('profile_complete'):
        return fail('Please complete your profile before claiming the welcome bonus')

    existing_welcome = [
        v for v in vouchers.values()
        if v.get('user_id') == user_id
        and v.get('type') == 'welcome_bonus'
        and v.get('status') == 'active'
    ]
    if existing_welcome:
        return fail('Welcome bonus has already been claimed')

    voucher_id = 'VCH-' + str(uuid4()).replace('-', '')[:8].upper()
    voucher_code = 'WELCOME-' + ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=8)
    )

    vouchers[voucher_id] = {
        'id': voucher_id,
        'code': voucher_code,
        'user_id': user_id,
        'type': 'welcome_bonus',
        'discount_amount': 20000,
        'status': 'active',
        'expires_at': (datetime.utcnow() + timedelta(days=90)).isoformat() + 'Z',
        'created_at': now_str(),
    }

    users[user_id]['loyalty_points'] = user.get('loyalty_points', 0) + 100
    users[user_id]['welcome_bonus_claimed'] = True

    return ok({
        'voucher_code': voucher_code,
        'voucher_id': voucher_id,
        'discount_amount': 20000,
        'loyalty_points_awarded': 100,
        'total_points': users[user_id]['loyalty_points'],
    }, 'Welcome bonus claimed. Voucher and 100 loyalty points added to your account.')


@app.route('/api/auth/login', methods=['POST'])
def login():
    body = request.get_json() or {}
    email = (body.get('email') or '').strip().lower()
    password = (body.get('password') or '').strip()

    if not email or not password:
        return fail('email and password are required')

    matched = None
    for uid, u in users.items():
        if u['email'] == email:
            matched = (uid, u)
            break

    if not matched:
        return fail('Invalid email or password', 401)

    user_id, user = matched
    if user['password'] != password:
        return fail('Invalid email or password', 401)

    otp = generate_otp()
    users[user_id]['pending_otp'] = otp
    users[user_id]['otp_purpose'] = 'two_factor'
    users[user_id]['otp_2fa'] = otp

    token = generate_token()
    sessions[token] = {
        'user_id': user_id,
        'authenticated': True,
        'two_fa_verified': False,
    }

    return ok({
        'token': token,
        'user_id': user_id,
        'name': user['name'],
        'otp': otp,
    }, 'Login successful. Please verify your identity with the OTP sent to your device.')


@app.route('/api/auth/verify-2fa', methods=['POST'])
@require_auth
def verify_2fa():
    user_id, user = get_current_user()
    if not user:
        return fail('User not found', 404)

    body = request.get_json() or {}
    otp = (body.get('otp') or '').strip()

    if not otp:
        return fail('otp is required')

    if otp != user.get('otp_2fa') and otp != user.get('otp'):
        return fail('Invalid or expired OTP')

    token = get_token_from_header()
    sessions[token]['two_fa_verified'] = True

    users[user_id]['otp_2fa'] = None
    users[user_id]['pending_otp'] = None
    users[user_id]['otp_purpose'] = None

    return ok({
        'two_fa_verified': True,
    }, '2FA verification successful. Please select your account role to continue.')


@app.route('/api/auth/select-role', methods=['POST'])
@require_auth
def select_role():
    user_id, user = get_current_user()
    if not user:
        return fail('User not found', 404)

    body = request.get_json() or {}
    role = (body.get('role') or '').strip()

    if role not in ('buyer', 'seller', 'admin'):
        return fail('role must be one of: buyer, seller, admin')

    users[user_id]['role'] = role

    dashboard_paths = {
        'buyer': '/api/buyer/history',
        'seller': '/api/seller/products',
        'admin': '/api/admin/users',
    }

    return ok({
        'role': role,
        'dashboard_url': dashboard_paths[role],
    }, f'Role set to {role}')


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_me():
    user_id, user = get_current_user()
    if not user:
        return fail('User not found', 404)

    sub = get_active_subscription(user_id)

    return ok({
        'id': user_id,
        'name': user['name'],
        'email': user['email'],
        'phone': user['phone'],
        'email_verified': user.get('email_verified', False),
        'profile_complete': user.get('profile_complete', False),
        'role': user.get('role'),
        'balance': user.get('balance', 0),
        'loyalty_points': user.get('loyalty_points', 0),
        'subscription': {
            'plan': sub['plan_id'] if sub else 'basic',
            'active': bool(sub),
            'expires_at': sub.get('expires_at') if sub else None,
        },
    })

# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@app.route('/api/products', methods=['GET'])
def list_products():
    category = request.args.get('category')
    result = list(PRODUCTS.values())
    if category:
        result = [p for p in result if p['category'] == category]
    return ok({'products': result, 'total': len(result)})


@app.route('/api/products/<product_id>', methods=['GET'])
def get_product(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return fail('Product not found', 404)
    return ok({'product': product})


@app.route('/api/products', methods=['POST'])
@require_2fa
def create_product():
    user_id, user = get_current_user()
    user_role = user.get('role', 'admin')
    if user_role not in ('seller', 'admin'):
        return fail('Seller or admin access required', 403)

    body = request.get_json() or {}
    name = (body.get('name') or '').strip()
    price = body.get('price')
    category = (body.get('category') or '').strip()
    description = (body.get('description') or '').strip()
    stock = body.get('stock', 0)

    if not all([name, price, category]):
        return fail('name, price, and category are required')

    if not isinstance(price, (int, float)) or price <= 0:
        return fail('price must be a positive number')

    pid = 'P' + str(uuid4()).replace('-', '')[:6].upper()
    PRODUCTS[pid] = {
        'id': pid,
        'name': name,
        'price': int(price),
        'category': category,
        'description': description,
        'stock': int(stock) if isinstance(stock, int) else 0,
        'seller_id': user_id,
        'created_at': now_str(),
    }

    return ok({'product': PRODUCTS[pid]}, 'Product created', 201)


@app.route('/api/products/<product_id>', methods=['PUT'])
@require_2fa
def update_product(product_id):
    user_id, user = get_current_user()
    user_role = user.get('role', 'admin')
    if user_role not in ('seller', 'admin'):
        return fail('Seller or admin access required', 403)

    product = PRODUCTS.get(product_id)
    if not product:
        return fail('Product not found', 404)

    body = request.get_json() or {}
    for field in ('name', 'description', 'category'):
        if body.get(field):
            PRODUCTS[product_id][field] = body[field]
    if 'price' in body and isinstance(body['price'], (int, float)) and body['price'] > 0:
        PRODUCTS[product_id]['price'] = int(body['price'])
    if 'stock' in body and isinstance(body['stock'], int) and body['stock'] >= 0:
        PRODUCTS[product_id]['stock'] = body['stock']

    return ok({'product': PRODUCTS[product_id]}, 'Product updated')

# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------

@app.route('/api/cart', methods=['GET'])
@require_auth
def get_cart():
    user_id, _ = get_current_user()
    cart = carts.get(user_id, [])
    total = sum(item['price'] * item['quantity'] for item in cart)
    return ok({'items': cart, 'item_count': len(cart), 'total': total})


@app.route('/api/cart/items', methods=['POST'])
@require_auth
def add_to_cart():
    user_id, _ = get_current_user()

    body = request.get_json() or {}
    product_id = (body.get('product_id') or '').strip()
    quantity = body.get('quantity', 1)

    if not product_id:
        return fail('product_id is required')

    product = PRODUCTS.get(product_id)
    if not product:
        return fail('Product not found', 404)

    if not isinstance(quantity, int) or quantity < 1:
        return fail('quantity must be a positive integer')

    cart = carts.get(user_id, [])
    existing = next((item for item in cart if item['product_id'] == product_id), None)
    if existing:
        existing['quantity'] += quantity
    else:
        cart.append({
            'product_id': product_id,
            'name': product['name'],
            'price': product['price'],
            'category': product['category'],
            'quantity': quantity,
        })

    carts[user_id] = cart
    total = sum(item['price'] * item['quantity'] for item in cart)
    return ok({'items': cart, 'item_count': len(cart), 'total': total}, 'Item added to cart')


@app.route('/api/cart/items/<product_id>', methods=['PUT'])
@require_auth
def update_cart_item(product_id):
    user_id, _ = get_current_user()

    body = request.get_json() or {}
    quantity = body.get('quantity')

    if not isinstance(quantity, int) or quantity < 0:
        return fail('quantity must be a non-negative integer')

    cart = carts.get(user_id, [])

    if quantity == 0:
        carts[user_id] = [item for item in cart if item['product_id'] != product_id]
    else:
        item = next((i for i in cart if i['product_id'] == product_id), None)
        if not item:
            return fail('Item not found in cart', 404)
        item['quantity'] = quantity

    cart = carts.get(user_id, [])
    total = sum(item['price'] * item['quantity'] for item in cart)
    return ok({'items': cart, 'item_count': len(cart), 'total': total}, 'Cart updated')


@app.route('/api/cart/items/<product_id>', methods=['DELETE'])
@require_auth
def remove_from_cart(product_id):
    user_id, _ = get_current_user()
    if product_id == 'all':
        carts[user_id] = []
    else:
        cart = carts.get(user_id, [])
        carts[user_id] = [item for item in cart if item['product_id'] != product_id]
    cart = carts.get(user_id, [])
    total = sum(item['price'] * item['quantity'] for item in cart)
    return ok({'items': cart, 'item_count': len(cart), 'total': total}, 'Item removed from cart')

# ---------------------------------------------------------------------------
# Flow 1: Checkout
# ---------------------------------------------------------------------------

@app.route('/api/checkout/init', methods=['POST'])
@require_auth
def checkout_init():
    user_id, _ = get_current_user()

    cart = carts.get(user_id, [])
    if not cart:
        return fail('Your cart is empty. Add items before initiating checkout.')

    item_total = sum(item['price'] * item['quantity'] for item in cart)

    pending_with_discount = next(
        (cs for cs in checkout_sessions.values()
         if cs['user_id'] == user_id
         and (cs.get('applied_voucher_id') or cs.get('balance_applied', 0) > 0)
         and not cs.get('payment_confirmed')),
        None
    )

    if pending_with_discount:
        pending_with_discount['items'] = list(cart)
        pending_with_discount['item_total'] = item_total
        pending_with_discount['shipping_cost'] = 0
        pending_with_discount['shipping_address'] = None
        pending_with_discount['shipping_method'] = None
        pending_with_discount['payment_id'] = None
        pending_with_discount['payment_method'] = None
        pending_with_discount['payment_initiated'] = False
        pending_with_discount['payment_confirmed'] = False
        recalculate_checkout_total(pending_with_discount)
        return ok({
            'checkout_id': pending_with_discount['id'],
            'items': cart,
            'item_total': item_total,
        }, 'Checkout ready')

    checkout_id = 'CHK-' + str(uuid4()).replace('-', '')[:10].upper()

    checkout_sessions[checkout_id] = {
        'id': checkout_id,
        'user_id': user_id,
        'items': list(cart),
        'item_total': item_total,
        'shipping_cost': 0,
        'discount_amount': 0,
        'balance_applied': 0,
        'total': item_total,
        'shipping_address': None,
        'shipping_method': None,
        'applied_voucher_id': None,
        'payment_id': None,
        'payment_method': None,
        'payment_initiated': False,
        'payment_confirmed': False,
        'created_at': now_str(),
    }

    return ok({
        'checkout_id': checkout_id,
        'items': cart,
        'item_total': item_total,
    }, 'Checkout ready')


@app.route('/api/checkout/shipping-address', methods=['PUT'])
@require_auth
def set_shipping_address():
    user_id, _ = get_current_user()

    body = request.get_json() or {}
    checkout_id = (body.get('checkout_id') or '').strip()
    recipient_name = (body.get('recipient_name') or '').strip()
    phone = (body.get('phone') or '').strip()
    full_address = (body.get('full_address') or '').strip()
    city = (body.get('city') or '').strip()
    postal_code = (body.get('postal_code') or '').strip()

    if not checkout_id:
        return fail('checkout_id is required')

    cs = checkout_sessions.get(checkout_id)
    if not cs or cs['user_id'] != user_id:
        return fail('Checkout session not found', 404)

    if not all([recipient_name, phone, full_address, city, postal_code]):
        return fail('recipient_name, phone, full_address, city, and postal_code are required')

    cs['shipping_address'] = {
        'recipient_name': recipient_name,
        'phone': phone,
        'full_address': full_address,
        'city': city,
        'postal_code': postal_code,
    }

    return ok({
        'checkout_id': checkout_id,
        'shipping_address': cs['shipping_address'],
    }, 'Shipping address saved')


@app.route('/api/checkout/shipping-method', methods=['PUT'])
@require_auth
def set_shipping_method():
    user_id, _ = get_current_user()

    body = request.get_json() or {}
    checkout_id = (body.get('checkout_id') or '').strip()
    method = (body.get('method') or '').strip()

    if not checkout_id:
        return fail('checkout_id is required')

    cs = checkout_sessions.get(checkout_id)
    if not cs or cs['user_id'] != user_id:
        return fail('Checkout session not found', 404)

    if not cs.get('shipping_address'):
        return fail('Please set a shipping address first')

    if method not in SHIPPING_RATES:
        return fail('method must be one of: regular, express, same_day')

    rate = SHIPPING_RATES[method]
    shipping_cost = rate['cost']

    sub = get_active_subscription(user_id)
    if sub:
        plan = SUBSCRIPTION_PLANS.get(sub.get('plan_id', 'basic'), SUBSCRIPTION_PLANS['basic'])
        if plan.get('free_shipping'):
            shipping_cost = 0

    cs['shipping_method'] = method
    cs['shipping_cost'] = shipping_cost
    cs['shipping_label'] = rate['label']
    cs['eta'] = rate['eta']
    recalculate_checkout_total(cs)

    return ok({
        'checkout_id': checkout_id,
        'shipping_method': method,
        'shipping_label': rate['label'],
        'shipping_cost': shipping_cost,
        'free_shipping_applied': shipping_cost == 0 and rate['cost'] > 0,
        'total': cs['total'],
    }, 'Shipping method selected')


@app.route('/api/checkout/apply-voucher', methods=['POST'])
@require_auth
def apply_voucher():
    user_id, _ = get_current_user()

    body = request.get_json() or {}
    checkout_id = (body.get('checkout_id') or '').strip()
    voucher_code = (body.get('voucher_code') or '').strip()

    if not voucher_code:
        return fail('voucher_code is required')

    voucher = next((v for v in vouchers.values() if v.get('code') == voucher_code), None)
    if not voucher:
        return fail('Invalid voucher code')

    if voucher.get('user_id') != user_id:
        return fail('This voucher does not belong to your account')

    if voucher.get('status') != 'active':
        return fail('This voucher has already been used or is no longer active')

    expires_at = voucher.get('expires_at')
    if expires_at:
        try:
            if datetime.fromisoformat(expires_at.replace('Z', '')) < datetime.utcnow():
                return fail('This voucher has expired')
        except ValueError:
            pass

    cs = checkout_sessions.get(checkout_id) if checkout_id else None
    if not cs or cs['user_id'] != user_id:
        new_id = 'CHK-' + str(uuid4()).replace('-', '')[:10].upper()
        current_cart = carts.get(user_id, [])
        item_total = sum(i['price'] * i['quantity'] for i in current_cart)
        checkout_sessions[new_id] = {
            'id': new_id,
            'user_id': user_id,
            'items': list(current_cart),
            'item_total': item_total,
            'shipping_cost': 0,
            'discount_amount': 0,
            'balance_applied': 0,
            'total': item_total,
            'shipping_address': None,
            'shipping_method': None,
            'applied_voucher_id': None,
            'payment_id': None,
            'payment_method': None,
            'payment_initiated': False,
            'payment_confirmed': False,
            'created_at': now_str(),
        }
        checkout_id = new_id
        cs = checkout_sessions[checkout_id]

    cs['applied_voucher_id'] = voucher['id']
    cs['discount_amount'] = cs.get('discount_amount', 0) + voucher['discount_amount']
    recalculate_checkout_total(cs)

    return ok({
        'checkout_id': checkout_id,
        'voucher_code': voucher_code,
        'discount_amount': voucher['discount_amount'],
        'total': cs['total'],
    }, 'Voucher applied successfully')


@app.route('/api/checkout/apply-balance', methods=['POST'])
@require_auth
def apply_balance():
    user_id, user = get_current_user()

    body = request.get_json() or {}
    checkout_id = (body.get('checkout_id') or '').strip()
    amount = body.get('amount', 0)

    if not isinstance(amount, (int, float)) or amount <= 0:
        return fail('amount must be a positive number')

    available = user.get('balance', 0)
    if available < amount:
        return fail(f'Insufficient balance. Your available balance is Rp {available:,}')

    cs = checkout_sessions.get(checkout_id) if checkout_id else None
    if not cs or cs['user_id'] != user_id:
        new_id = 'CHK-' + str(uuid4()).replace('-', '')[:10].upper()
        current_cart = carts.get(user_id, [])
        item_total = sum(i['price'] * i['quantity'] for i in current_cart)
        checkout_sessions[new_id] = {
            'id': new_id,
            'user_id': user_id,
            'items': list(current_cart),
            'item_total': item_total,
            'shipping_cost': 0,
            'discount_amount': 0,
            'balance_applied': 0,
            'total': item_total,
            'shipping_address': None,
            'shipping_method': None,
            'applied_voucher_id': None,
            'payment_id': None,
            'payment_method': None,
            'payment_initiated': False,
            'payment_confirmed': False,
            'created_at': now_str(),
        }
        checkout_id = new_id
        cs = checkout_sessions[checkout_id]

    cs['balance_applied'] = int(amount)
    recalculate_checkout_total(cs)

    return ok({
        'checkout_id': checkout_id,
        'balance_applied': int(amount),
        'remaining_balance': available,
        'total': cs['total'],
    }, 'Balance applied to your order')


@app.route('/api/checkout/payment/initiate', methods=['POST'])
@require_auth
def initiate_checkout_payment():
    user_id, _ = get_current_user()

    body = request.get_json() or {}
    checkout_id = (body.get('checkout_id') or '').strip()
    payment_method = (body.get('payment_method') or '').strip()

    if not checkout_id:
        return fail('checkout_id is required')

    cs = checkout_sessions.get(checkout_id)
    if not cs or cs['user_id'] != user_id:
        return fail('Checkout session not found', 404)

    if not cs.get('shipping_address'):
        return fail('Shipping address is required before initiating payment')

    if not cs.get('shipping_method'):
        return fail('Shipping method must be selected before initiating payment')

    valid_methods = ['bank_transfer', 'credit_card', 'e_wallet', 'cash_on_delivery']
    if payment_method not in valid_methods:
        return fail(f'payment_method must be one of: {", ".join(valid_methods)}')

    payment_id = 'PAY-' + str(uuid4()).replace('-', '')[:8].upper()
    cs['payment_id'] = payment_id
    cs['payment_method'] = payment_method
    cs['payment_initiated'] = True

    return ok({
        'checkout_id': checkout_id,
        'payment_id': payment_id,
        'payment_method': payment_method,
        'amount_due': cs['total'],
    }, 'Payment initiated. Complete your transfer and then confirm the payment.')


@app.route('/api/checkout/payment/confirm', methods=['POST'])
@require_auth
def confirm_checkout_payment():
    user_id, _ = get_current_user()

    body = request.get_json() or {}
    checkout_id = (body.get('checkout_id') or '').strip()
    payment_id = (body.get('payment_id') or '').strip()

    if not checkout_id or not payment_id:
        return fail('checkout_id and payment_id are required')

    cs = checkout_sessions.get(checkout_id)
    if not cs or cs['user_id'] != user_id:
        return fail('Checkout session not found', 404)

    if not cs.get('payment_initiated'):
        return fail('Payment has not been initiated for this checkout session')

    if cs.get('payment_id') != payment_id:
        return fail('Payment ID does not match this checkout session')

    if cs.get('payment_confirmed'):
        return fail('Payment for this session has already been confirmed')

    cs['payment_confirmed'] = True
    cs['payment_confirmed_at'] = now_str()

    return ok({
        'checkout_id': checkout_id,
        'payment_id': payment_id,
        'amount_paid': cs['total'],
    }, 'Payment confirmed. Your order is ready to be placed.')


@app.route('/api/checkout/confirm', methods=['POST'])
@require_auth
def confirm_order():
    user_id, user = get_current_user()

    body = request.get_json() or {}
    checkout_id = (body.get('checkout_id') or '').strip()

    if not checkout_id:
        return fail('checkout_id is required')

    cs = checkout_sessions.get(checkout_id)
    if not cs or cs['user_id'] != user_id:
        return fail('Checkout session not found', 404)

    if not cs.get('items'):
        return fail('Checkout session contains no items')

    if not cs.get('shipping_address'):
        return fail('Shipping address is required to confirm the order')

    sub = get_active_subscription(user_id)
    plan = SUBSCRIPTION_PLANS.get(sub['plan_id'], SUBSCRIPTION_PLANS['basic']) if sub else SUBSCRIPTION_PLANS['basic']

    item_total = cs.get('item_total', 0)
    sub_discount = 0
    if sub and plan.get('order_discount_pct', 0) > 0:
        sub_discount = int(item_total * plan['order_discount_pct'] / 100)

    voucher_discount = cs.get('discount_amount', 0)
    balance_applied = cs.get('balance_applied', 0)
    final_total = max(0, item_total + cs.get('shipping_cost', 0) - voucher_discount - sub_discount - balance_applied)

    if balance_applied > 0:
        users[user_id]['balance'] = max(0, user.get('balance', 0) - final_total)

    applied_vid = cs.get('applied_voucher_id')
    if applied_vid and applied_vid in vouchers:
        vouchers[applied_vid]['status'] = 'used'
        vouchers[applied_vid]['used_at'] = now_str()

    order_id = 'ORD-' + str(uuid4()).replace('-', '')[:10].upper()
    points = loyalty_points_for(final_total)
    orders[order_id] = {
        'id': order_id,
        'user_id': user_id,
        'items': cs.get('items', []),
        'item_total': item_total,
        'shipping_cost': cs.get('shipping_cost', 0),
        'shipping_method': cs.get('shipping_method'),
        'shipping_address': cs.get('shipping_address'),
        'voucher_discount': voucher_discount,
        'subscription_discount': sub_discount,
        'balance_applied': balance_applied,
        'total': final_total,
        'payment_method': cs.get('payment_method', 'unknown'),
        'payment_id': cs.get('payment_id'),
        'status': 'processing',
        'loyalty_points_earned': points,
        'refund_count': 0,
        'created_at': now_str(),
    }

    users[user_id]['loyalty_points'] = user.get('loyalty_points', 0) + points

    carts[user_id] = []

    return ok({
        'order_id': order_id,
        'order': orders[order_id],
        'points_earned': points,
        'total_points': users[user_id]['loyalty_points'],
    }, 'Order placed successfully')

# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

@app.route('/api/orders', methods=['GET'])
@require_auth
def list_orders():
    user_id, user = get_current_user()
    user_role = user.get('role', 'admin')

    if user_role in ('admin', 'seller'):
        result = list(orders.values())
    else:
        result = [o for o in orders.values() if o['user_id'] == user_id]

    result.sort(key=lambda o: o['created_at'], reverse=True)
    return ok({'orders': result, 'total': len(result)})


@app.route('/api/orders/<order_id>', methods=['GET'])
@require_auth
def get_order(order_id):
    user_id, user = get_current_user()
    user_role = user.get('role', 'admin')

    order = orders.get(order_id)
    if not order:
        return fail('Order not found', 404)

    if order['user_id'] != user_id and user_role not in ('admin', 'seller'):
        return fail('Access denied', 403)

    return ok({'order': order})


@app.route('/api/orders/<order_id>/status', methods=['PUT'])
@require_auth
def update_order_status(order_id):
    user_id, user = get_current_user()
    user_role = user.get('role', 'admin')

    order = orders.get(order_id)
    if not order:
        return fail('Order not found', 404)

    body = request.get_json() or {}
    new_status = (body.get('status') or '').strip()

    valid_statuses = ['processing', 'shipped', 'delivered', 'cancelled']
    if new_status not in valid_statuses:
        return fail(f'status must be one of: {", ".join(valid_statuses)}')

    if user_role not in ('admin', 'seller'):
        if order['user_id'] != user_id:
            return fail('Access denied', 403)
        if new_status != 'cancelled':
            return fail('You can only cancel your own orders', 403)

    if new_status == 'cancelled':
        order_owner = order['user_id']
        refund_amount = order.get('total', 0)
        users[order_owner]['balance'] = users[order_owner].get('balance', 0) + refund_amount
        orders[order_id]['refund_count'] = orders[order_id].get('refund_count', 0) + 1

    orders[order_id]['status'] = new_status
    orders[order_id]['status_updated_at'] = now_str()
    orders[order_id]['status_updated_by'] = user_id

    return ok({'order_id': order_id, 'status': new_status}, 'Order status updated')

# ---------------------------------------------------------------------------
# Flow 3: Dashboard
# ---------------------------------------------------------------------------

@app.route('/api/dashboard', methods=['GET'])
@require_auth
def get_dashboard():
    user_id, user = get_current_user()
    user_role = user.get('role', 'admin')

    sub = get_active_subscription(user_id)
    user_orders = [o for o in orders.values() if o['user_id'] == user_id]
    user_vouchers = [v for v in vouchers.values() if v.get('user_id') == user_id and v.get('status') == 'active']

    return ok({
        'user': {
            'id': user_id,
            'name': user['name'],
            'email': user['email'],
            'role': user_role,
            'balance': user.get('balance', 0),
            'loyalty_points': user.get('loyalty_points', 0),
        },
        'subscription': {
            'plan': sub['plan_id'] if sub else 'basic',
            'active': bool(sub),
            'expires_at': sub.get('expires_at') if sub else None,
        },
        'stats': {
            'total_orders': len(user_orders),
            'total_spent': sum(o['total'] for o in user_orders),
            'active_vouchers': len(user_vouchers),
        },
    })


@app.route('/api/admin/users', methods=['GET'])
@require_2fa
def list_users():
    user_id, user = get_current_user()
    user_role = user.get('role', 'admin')

    if user_role != 'admin':
        return fail('Admin access required', 403)

    all_users = [
        {
            'id': uid,
            'name': u['name'],
            'email': u['email'],
            'phone': u['phone'],
            'role': u.get('role'),
            'email_verified': u.get('email_verified', False),
            'balance': u.get('balance', 0),
            'loyalty_points': u.get('loyalty_points', 0),
            'created_at': u.get('created_at'),
        }
        for uid, u in users.items()
    ]

    return ok({'users': all_users, 'total': len(all_users)})


@app.route('/api/admin/users/<target_user_id>', methods=['DELETE'])
@require_2fa
def delete_user(target_user_id):
    user_id, user = get_current_user()
    user_role = user.get('role', 'admin')

    if user_role != 'admin':
        return fail('Admin access required', 403)

    if target_user_id == user_id:
        return fail('You cannot delete your own account')

    if target_user_id not in users:
        return fail('User not found', 404)

    del users[target_user_id]
    to_remove = [t for t, s in sessions.items() if s['user_id'] == target_user_id]
    for t in to_remove:
        del sessions[t]

    return ok({'deleted_user_id': target_user_id}, 'User account deleted')


@app.route('/api/admin/revenue', methods=['GET'])
@require_2fa
def get_revenue():
    user_id, user = get_current_user()
    user_role = user.get('role', 'admin')

    if user_role != 'admin':
        return fail('Admin access required', 403)

    total_revenue = sum(o['total'] for o in orders.values())
    order_count = len(orders)
    active_subs = sum(1 for s in subscriptions.values() if s.get('active'))

    return ok({
        'total_revenue': total_revenue,
        'total_orders': order_count,
        'average_order_value': int(total_revenue / order_count) if order_count else 0,
        'total_users': len(users),
        'active_subscriptions': active_subs,
    })


@app.route('/api/seller/products', methods=['GET'])
@require_2fa
def seller_products():
    user_id, user = get_current_user()
    user_role = user.get('role', 'admin')

    if user_role not in ('seller', 'admin'):
        return fail('Seller or admin access required', 403)

    if user_role == 'admin':
        result = list(PRODUCTS.values())
    else:
        result = [p for p in PRODUCTS.values() if p.get('seller_id') == user_id]

    return ok({'products': result, 'total': len(result)})


@app.route('/api/seller/orders', methods=['GET'])
@require_2fa
def seller_orders():
    user_id, user = get_current_user()
    user_role = user.get('role', 'admin')

    if user_role not in ('seller', 'admin'):
        return fail('Seller or admin access required', 403)

    result = list(orders.values())
    result.sort(key=lambda o: o['created_at'], reverse=True)
    return ok({'orders': result, 'total': len(result)})


@app.route('/api/buyer/history', methods=['GET'])
@require_auth
def buyer_history():
    user_id, _ = get_current_user()
    result = [o for o in orders.values() if o['user_id'] == user_id]
    result.sort(key=lambda o: o['created_at'], reverse=True)
    return ok({'orders': result, 'total': len(result)})


@app.route('/api/buyer/vouchers', methods=['GET'])
@require_auth
def buyer_vouchers():
    user_id, _ = get_current_user()
    result = [v for v in vouchers.values() if v.get('user_id') == user_id]
    return ok({'vouchers': result, 'total': len(result)})


@app.route('/api/buyer/points', methods=['GET'])
@require_auth
def buyer_points():
    user_id, user = get_current_user()
    return ok({
        'loyalty_points': user.get('loyalty_points', 0),
        'balance': user.get('balance', 0),
    })

# ---------------------------------------------------------------------------
# Flow 4: Subscriptions
# ---------------------------------------------------------------------------

@app.route('/api/subscriptions/plans', methods=['GET'])
def list_subscription_plans():
    return ok({'plans': list(SUBSCRIPTION_PLANS.values())})


@app.route('/api/subscriptions/select', methods=['POST'])
@require_auth
def select_subscription():
    user_id, _ = get_current_user()

    body = request.get_json() or {}
    plan_id = (body.get('plan_id') or '').strip()

    if plan_id not in SUBSCRIPTION_PLANS:
        return fail(f'plan_id must be one of: {", ".join(SUBSCRIPTION_PLANS.keys())}')

    existing = subscriptions.get(user_id)
    if existing and existing.get('active'):
        return fail('You already have an active subscription. Please wait for it to expire or contact support.')

    plan = SUBSCRIPTION_PLANS[plan_id]
    sub_id = 'SUB-' + str(uuid4()).replace('-', '')[:8].upper()

    subscriptions[user_id] = {
        'id': sub_id,
        'user_id': user_id,
        'plan_id': plan_id,
        'plan_name': plan['name'],
        'price_monthly': plan['price_monthly'],
        'payment_status': 'pending',
        'payment_id': None,
        'payment_method': None,
        'active': False,
        'selected_at': now_str(),
        'activated_at': None,
        'expires_at': None,
    }

    return ok({
        'subscription_id': sub_id,
        'plan': plan,
    }, f'Plan "{plan["name"]}" selected')


@app.route('/api/subscriptions/payment/initiate', methods=['POST'])
@require_auth
def initiate_subscription_payment():
    user_id, _ = get_current_user()

    sub = subscriptions.get(user_id)
    if not sub:
        return fail('No subscription plan selected. Please select a plan first.')

    if sub.get('active'):
        return fail('Subscription is already active')

    body = request.get_json() or {}
    payment_method = (body.get('payment_method') or '').strip()

    valid_methods = ['bank_transfer', 'credit_card', 'e_wallet']
    if payment_method not in valid_methods:
        return fail(f'payment_method must be one of: {", ".join(valid_methods)}')

    payment_id = 'SPAY-' + str(uuid4()).replace('-', '')[:8].upper()
    subscriptions[user_id]['payment_id'] = payment_id
    subscriptions[user_id]['payment_method'] = payment_method

    return ok({
        'payment_id': payment_id,
        'plan': sub['plan_id'],
        'amount_due': sub['price_monthly'],
    }, 'Subscription payment initiated. Complete the transfer and confirm to activate.')


@app.route('/api/subscriptions/payment/confirm', methods=['POST'])
@require_auth
def confirm_subscription_payment():
    user_id, _ = get_current_user()

    sub = subscriptions.get(user_id)
    if not sub:
        return fail('No subscription found for your account')

    body = request.get_json() or {}
    payment_id = (body.get('payment_id') or '').strip()

    if not payment_id:
        return fail('payment_id is required')

    if sub.get('payment_id') != payment_id:
        return fail('Payment ID does not match the subscription on record')

    if sub.get('payment_status') == 'completed':
        return fail('Payment has already been confirmed')

    subscriptions[user_id]['payment_status'] = 'completed'
    subscriptions[user_id]['payment_confirmed_at'] = now_str()

    return ok({
        'plan': sub['plan_id'],
        'payment_status': 'completed',
    }, 'Subscription payment confirmed. Your membership is ready to activate.')


@app.route('/api/subscriptions/activate', methods=['POST'])
@require_auth
def activate_subscription():
    user_id, _ = get_current_user()

    sub = subscriptions.get(user_id)
    if not sub:
        return fail('No subscription plan selected. Please select a plan first.')

    if sub.get('active'):
        return fail('Your subscription is already active')

    activated_at = datetime.utcnow()
    expires_at = activated_at + timedelta(days=30)

    subscriptions[user_id]['active'] = True
    subscriptions[user_id]['activated_at'] = activated_at.isoformat() + 'Z'
    subscriptions[user_id]['expires_at'] = expires_at.isoformat() + 'Z'

    plan = SUBSCRIPTION_PLANS[sub['plan_id']]

    return ok({
        'plan': sub['plan_id'],
        'plan_name': plan['name'],
        'active': True,
        'activated_at': subscriptions[user_id]['activated_at'],
        'expires_at': subscriptions[user_id]['expires_at'],
        'features': plan['features'],
    }, 'Subscription activated successfully')


@app.route('/api/subscriptions/status', methods=['GET'])
@require_auth
def subscription_status():
    user_id, _ = get_current_user()

    sub = get_active_subscription(user_id)
    if not sub:
        pending = subscriptions.get(user_id)
        return ok({
            'active': False,
            'plan': 'basic',
            'pending_plan': pending.get('plan_id') if pending else None,
            'payment_status': pending.get('payment_status') if pending else None,
        })

    plan = SUBSCRIPTION_PLANS.get(sub['plan_id'], SUBSCRIPTION_PLANS['basic'])
    return ok({
        'active': True,
        'plan': sub['plan_id'],
        'plan_name': plan['name'],
        'features': plan['features'],
        'expires_at': sub.get('expires_at'),
    })

# ---------------------------------------------------------------------------
# Flow 5: Gift Cards
# ---------------------------------------------------------------------------

@app.route('/api/gift-cards/denominations', methods=['GET'])
def list_gc_denominations():
    return ok({'denominations': GIFT_CARD_DENOMINATIONS})


@app.route('/api/gift-cards', methods=['GET'])
@require_auth
def list_gift_cards():
    user_id, _ = get_current_user()
    result = [gc for gc in gift_cards.values() if gc.get('owner_id') == user_id]
    return ok({'gift_cards': result, 'total': len(result)})


@app.route('/api/gift-cards/purchase', methods=['POST'])
@require_auth
def purchase_gift_card():
    user_id, _ = get_current_user()

    body = request.get_json() or {}
    amount = body.get('amount')

    if amount not in GIFT_CARD_DENOMINATIONS:
        return fail(f'amount must be one of: {GIFT_CARD_DENOMINATIONS}')

    gc_id = 'GC-' + str(uuid4()).replace('-', '')[:10].upper()
    gc_code = 'GC-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    payment_id = 'GCPAY-' + str(uuid4()).replace('-', '')[:8].upper()

    gift_cards[gc_id] = {
        'id': gc_id,
        'code': gc_code,
        'amount': amount,
        'owner_id': user_id,
        'original_owner_id': user_id,
        'payment_status': 'pending',
        'payment_id': payment_id,
        'status': 'active',
        'transferred_to': None,
        'redeemed_by': None,
        'created_at': now_str(),
    }

    return ok({
        'gift_card_id': gc_id,
        'code': gc_code,
        'amount': amount,
        'payment_id': payment_id,
        'payment_status': 'pending',
    }, 'Gift card order created. Complete payment to activate your gift card.')


@app.route('/api/gift-cards/payment/confirm', methods=['POST'])
@require_auth
def confirm_gc_payment():
    user_id, _ = get_current_user()

    body = request.get_json() or {}
    gift_card_id = (body.get('gift_card_id') or '').strip()
    payment_id = (body.get('payment_id') or '').strip()

    if not gift_card_id or not payment_id:
        return fail('gift_card_id and payment_id are required')

    gc = gift_cards.get(gift_card_id)
    if not gc:
        return fail('Gift card not found', 404)

    if gc['owner_id'] != user_id:
        return fail('Access denied', 403)

    if gc.get('payment_id') != payment_id:
        return fail('Payment ID does not match')

    if gc.get('payment_status') == 'completed':
        return fail('Payment has already been confirmed for this gift card')

    gift_cards[gift_card_id]['payment_status'] = 'completed'
    gift_cards[gift_card_id]['payment_confirmed_at'] = now_str()

    return ok({
        'gift_card_id': gift_card_id,
        'code': gc['code'],
        'amount': gc['amount'],
        'payment_status': 'completed',
    }, 'Gift card payment confirmed. Your gift card is ready to use or share.')


@app.route('/api/gift-cards/transfer', methods=['POST'])
@require_auth
def transfer_gift_card():
    user_id, _ = get_current_user()

    body = request.get_json() or {}
    code = (body.get('code') or '').strip()
    recipient_email = (body.get('recipient_email') or '').strip().lower()

    if not code or not recipient_email:
        return fail('code and recipient_email are required')

    gc = next((g for g in gift_cards.values() if g.get('code') == code), None)
    if not gc:
        return fail('Gift card not found', 404)
    gift_card_id = gc['id']

    if gc['owner_id'] != user_id:
        return fail('This gift card does not belong to you')

    if gc.get('status') == 'redeemed':
        return fail('Redeemed gift cards cannot be transferred')

    if gc.get('transferred_to') is not None:
        return fail('This gift card has already been transferred')

    recipient = next((u for u in users.values() if u['email'] == recipient_email), None)
    if not recipient:
        return fail('Recipient account not found. They must be a registered WarungKu user.')

    if recipient['id'] == user_id:
        return fail('You cannot transfer a gift card to yourself')

    gift_cards[gift_card_id]['transferred_to'] = recipient['id']
    gift_cards[gift_card_id]['owner_id'] = recipient['id']
    gift_cards[gift_card_id]['transferred_at'] = now_str()

    return ok({
        'gift_card_id': gift_card_id,
        'transferred_to': recipient_email,
        'amount': gc['amount'],
    }, f'Gift card transferred to {recipient_email}')


@app.route('/api/gift-cards/redeem', methods=['POST'])
@require_auth
def redeem_gift_card():
    user_id, user = get_current_user()

    body = request.get_json() or {}
    code = (body.get('code') or '').strip()

    if not code:
        return fail('Gift card code is required')

    gc = next((g for g in gift_cards.values() if g.get('code') == code), None)
    if not gc:
        return fail('Invalid gift card code')

    if gc['owner_id'] != user_id:
        return fail('This gift card does not belong to you')

    if gc.get('status') == 'cancelled':
        return fail('This gift card has been cancelled and is no longer valid')

    users[user_id]['balance'] = user.get('balance', 0) + gc['amount']
    gift_cards[gc['id']]['status'] = 'redeemed'
    gift_cards[gc['id']]['redeemed_at'] = now_str()
    gift_cards[gc['id']]['redeemed_by'] = user_id

    return ok({
        'amount_added': gc['amount'],
        'new_balance': users[user_id]['balance'],
    }, f'Gift card redeemed. Rp {gc["amount"]:,} has been added to your account balance.')

# ---------------------------------------------------------------------------
# Flow 6: Returns and Refunds
# ---------------------------------------------------------------------------

@app.route('/api/returns/submit', methods=['POST'])
@require_auth
def submit_return():
    user_id, _ = get_current_user()

    body = request.get_json() or {}
    order_id = (body.get('order_id') or '').strip()
    reason = (body.get('reason') or '').strip()
    details = (body.get('details') or '').strip()

    if not order_id or not reason:
        return fail('order_id and reason are required')

    order = orders.get(order_id)
    if not order or order['user_id'] != user_id:
        return fail('Order not found', 404)

    if order['status'] == 'cancelled':
        return fail('Return requests cannot be submitted for cancelled orders')

    existing = next(
        (r for r in return_requests.values()
         if r['order_id'] == order_id and r['status'] not in ('rejected',)),
        None
    )
    if existing:
        return fail('A return request for this order is already being processed')

    return_id = 'RET-' + str(uuid4()).replace('-', '')[:10].upper()
    return_requests[return_id] = {
        'id': return_id,
        'user_id': user_id,
        'order_id': order_id,
        'order_total': order['total'],
        'reason': reason,
        'details': details,
        'status': 'pending',
        'admin_notes': None,
        'refund_amount': order['total'],
        'refund_processed': False,
        'submitted_at': now_str(),
        'reviewed_at': None,
        'reviewed_by': None,
    }

    return ok({
        'return_id': return_id,
        'order_id': order_id,
        'status': 'pending',
        'refund_amount': order['total'],
    }, 'Return request submitted successfully. Pending admin review.', 201)


@app.route('/api/returns', methods=['GET'])
@require_auth
def list_returns():
    user_id, user = get_current_user()
    user_role = user.get('role', 'admin')

    if user_role in ('admin', 'seller'):
        result = list(return_requests.values())
    else:
        result = [r for r in return_requests.values() if r['user_id'] == user_id]

    result.sort(key=lambda r: r['submitted_at'], reverse=True)
    return ok({'returns': result, 'total': len(result)})


@app.route('/api/returns/<return_id>', methods=['GET'])
@require_auth
def get_return(return_id):
    user_id, user = get_current_user()
    user_role = user.get('role', 'admin')

    ret = return_requests.get(return_id)
    if not ret:
        return fail('Return request not found', 404)

    if ret['user_id'] != user_id and user_role not in ('admin', 'seller'):
        return fail('Access denied', 403)

    return ok({'return': ret})


@app.route('/api/returns/<return_id>/approve', methods=['PUT'])
@require_2fa
def approve_return(return_id):
    user_id, user = get_current_user()
    user_role = user.get('role', 'admin')

    if user_role != 'admin':
        return fail('Admin access required', 403)

    ret = return_requests.get(return_id)
    if not ret:
        return fail('Return request not found', 404)

    if ret['status'] != 'pending':
        return fail(f'Cannot approve a return with status: {ret["status"]}')

    body = request.get_json() or {}
    admin_notes = (body.get('admin_notes') or '').strip()
    refund_amount = body.get('refund_amount', ret['refund_amount'])

    if not isinstance(refund_amount, (int, float)) or refund_amount <= 0:
        return fail('refund_amount must be a positive number')

    if refund_amount > ret['order_total']:
        return fail(f'Refund amount cannot exceed the original order total of Rp {ret["order_total"]:,}')

    return_requests[return_id]['status'] = 'approved'
    return_requests[return_id]['admin_notes'] = admin_notes
    return_requests[return_id]['refund_amount'] = int(refund_amount)
    return_requests[return_id]['reviewed_at'] = now_str()
    return_requests[return_id]['reviewed_by'] = user_id

    return ok({
        'return_id': return_id,
        'status': 'approved',
        'refund_amount': int(refund_amount),
    }, 'Return request approved. The customer may now request their refund.')


@app.route('/api/returns/<return_id>/reject', methods=['PUT'])
@require_2fa
def reject_return(return_id):
    user_id, user = get_current_user()
    user_role = user.get('role', 'admin')

    if user_role != 'admin':
        return fail('Admin access required', 403)

    ret = return_requests.get(return_id)
    if not ret:
        return fail('Return request not found', 404)

    if ret['status'] != 'pending':
        return fail(f'Cannot reject a return with status: {ret["status"]}')

    body = request.get_json() or {}
    admin_notes = (body.get('admin_notes') or '').strip()

    return_requests[return_id]['status'] = 'rejected'
    return_requests[return_id]['admin_notes'] = admin_notes
    return_requests[return_id]['reviewed_at'] = now_str()
    return_requests[return_id]['reviewed_by'] = user_id

    return ok({'return_id': return_id, 'status': 'rejected'}, 'Return request rejected')


@app.route('/api/returns/<return_id>/process-refund', methods=['POST'])
@require_auth
def process_refund(return_id):
    user_id, user = get_current_user()

    ret = return_requests.get(return_id)
    if not ret:
        return fail('Return request not found', 404)

    if ret['user_id'] != user_id:
        return fail('Access denied', 403)

    if ret.get('refund_processed'):
        return fail('Refund has already been processed for this return request')

    refund_amount = ret.get('refund_amount', 0)
    if refund_amount <= 0:
        return fail('No refund amount is set for this return request')

    users[user_id]['balance'] = user.get('balance', 0) + refund_amount
    return_requests[return_id]['refund_processed'] = True
    return_requests[return_id]['refund_processed_at'] = now_str()
    return_requests[return_id]['status'] = 'refunded'

    return ok({
        'return_id': return_id,
        'refund_amount': refund_amount,
        'new_balance': users[user_id]['balance'],
    }, f'Refund of Rp {refund_amount:,} has been credited to your account balance.')

# ---------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True, port=5000)
