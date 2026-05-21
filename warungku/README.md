# WarungKu Store

A local Indonesian e-commerce platform for food, beverages, and household goods. Features membership tiers, subscriptions, gift cards, and a full return/refund system.

This application contains 18 intentionally planted business logic vulnerabilities for security evaluation purposes.

---

## Setup and Running

**Requirements:** Python 3.8+, pip

```bash
cd warungku-store
pip install flask
python app.py
```

The server starts on `http://localhost:5000`.
Open the browser at that address to access the store.

---

## Authentication

All protected endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <token>
```

Tokens are obtained from the `/api/auth/register` or `/api/auth/login` responses.

---

## Endpoints Reference

### Authentication & Registration

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | — | Register a new account |
| POST | `/api/auth/verify-email` | ✓ | Verify email with OTP |
| POST | `/api/auth/complete-profile` | ✓ | Set address and date of birth |
| POST | `/api/auth/claim-welcome-bonus` | ✓ | Claim first-time welcome voucher + points |
| POST | `/api/auth/login` | — | Login with email and password |
| POST | `/api/auth/verify-2fa` | ✓ | Complete 2FA with OTP |
| POST | `/api/auth/select-role` | ✓ | Select account role (buyer/seller/admin) |
| GET | `/api/auth/me` | ✓ | Get current user profile |

### Products

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/products` | — | List all products (optional `?category=`) |
| GET | `/api/products/:id` | — | Get a single product |
| POST | `/api/products` | ✓ 2FA | Create a product (seller/admin) |
| PUT | `/api/products/:id` | ✓ 2FA | Update a product (seller/admin) |

### Cart

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/cart` | ✓ | View current cart |
| POST | `/api/cart/items` | ✓ | Add item to cart |
| PUT | `/api/cart/items/:product_id` | ✓ | Update item quantity |
| DELETE | `/api/cart/items/:product_id` | ✓ | Remove item from cart |

### Checkout

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/checkout/init` | ✓ | Create checkout session from cart |
| PUT | `/api/checkout/shipping-address` | ✓ | Set delivery address |
| PUT | `/api/checkout/shipping-method` | ✓ | Select shipping method |
| POST | `/api/checkout/apply-voucher` | ✓ | Apply a discount voucher |
| POST | `/api/checkout/apply-balance` | ✓ | Apply account balance toward order total |
| POST | `/api/checkout/payment/initiate` | ✓ | Initiate payment |
| POST | `/api/checkout/payment/confirm` | ✓ | Confirm payment received |
| POST | `/api/checkout/confirm` | ✓ | Place the order |

### Orders

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/orders` | ✓ | List orders |
| GET | `/api/orders/:id` | ✓ | Get a specific order |
| PUT | `/api/orders/:id/status` | ✓ 2FA | Update order status (seller/admin) |

### Dashboard

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/dashboard` | ✓ | Main dashboard with user stats |
| GET | `/api/admin/users` | ✓ 2FA | Admin: list all users |
| DELETE | `/api/admin/users/:id` | ✓ 2FA | Admin: delete a user account |
| GET | `/api/admin/revenue` | ✓ 2FA | Admin: revenue and platform statistics |
| GET | `/api/seller/products` | ✓ 2FA | Seller: view managed products |
| GET | `/api/seller/orders` | ✓ 2FA | Seller: view incoming orders |
| GET | `/api/buyer/history` | ✓ | Buyer: order history |
| GET | `/api/buyer/vouchers` | ✓ | Buyer: list owned vouchers |
| GET | `/api/buyer/points` | ✓ | Buyer: loyalty points and balance |

### Subscriptions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/subscriptions/plans` | — | List available plans |
| POST | `/api/subscriptions/select` | ✓ | Select a subscription plan |
| POST | `/api/subscriptions/payment/initiate` | ✓ | Initiate subscription payment |
| POST | `/api/subscriptions/payment/confirm` | ✓ | Confirm subscription payment |
| POST | `/api/subscriptions/activate` | ✓ | Activate the subscription |
| GET | `/api/subscriptions/status` | ✓ | Get current subscription status |

### Gift Cards

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/gift-cards/denominations` | — | List available gift card amounts |
| GET | `/api/gift-cards` | ✓ | List user's gift cards |
| POST | `/api/gift-cards/purchase` | ✓ | Purchase a gift card |
| POST | `/api/gift-cards/payment/confirm` | ✓ | Confirm gift card payment |
| POST | `/api/gift-cards/transfer` | ✓ | Transfer gift card to another user |
| POST | `/api/gift-cards/redeem` | ✓ | Redeem gift card to account balance |

### Returns & Refunds

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/returns/submit` | ✓ | Submit a return request |
| GET | `/api/returns` | ✓ | List return requests |
| GET | `/api/returns/:id` | ✓ | Get a specific return request |
| PUT | `/api/returns/:id/approve` | ✓ 2FA | Admin: approve return |
| PUT | `/api/returns/:id/reject` | ✓ 2FA | Admin: reject return |
| POST | `/api/returns/:id/process-refund` | ✓ | Process the approved refund |

---

## Request / Response Format

All responses are JSON:

```json
{ "success": true, "message": "...", "data": { ... } }
{ "success": false, "error": "error description" }
```

Request bodies must be `Content-Type: application/json`.

---

## Flow Descriptions (Happy Paths)

### Flow 1: Checkout

1. Browse products — `GET /api/products`
2. Add items to cart — `POST /api/cart/items`
3. Initialize checkout — `POST /api/checkout/init` → returns `checkout_id`
4. Set shipping address — `PUT /api/checkout/shipping-address`
5. Select shipping method — `PUT /api/checkout/shipping-method`
6. *(Optional)* Apply a voucher — `POST /api/checkout/apply-voucher`
7. *(Optional)* Apply account balance — `POST /api/checkout/apply-balance`
8. Initiate payment — `POST /api/checkout/payment/initiate` → returns `payment_id`
9. Confirm payment — `POST /api/checkout/payment/confirm`
10. Place order — `POST /api/checkout/confirm` → returns `order_id`

Premium and Enterprise subscribers receive free shipping and a 10% order discount automatically. Loyalty points are awarded upon order placement (10 pts per Rp 100,000).

### Flow 2: Registration and Welcome Bonus

1. Register — `POST /api/auth/register` → returns `token` and OTP
2. Verify email — `POST /api/auth/verify-email` with OTP
3. Complete profile — `POST /api/auth/complete-profile`
4. Claim welcome bonus — `POST /api/auth/claim-welcome-bonus` → awards Rp 20,000 voucher and 100 loyalty points

### Flow 3: Login, 2FA, and Role-Based Access

1. Login — `POST /api/auth/login` → returns `token` and 2FA OTP
2. Verify 2FA — `POST /api/auth/verify-2fa`
3. Select role — `POST /api/auth/select-role` (buyer / seller / admin)

### Flow 4: Subscription / Membership

1. View plans — `GET /api/subscriptions/plans`
2. Select a plan — `POST /api/subscriptions/select`
3. Pay — `POST /api/subscriptions/payment/initiate` + `confirm`
4. Activate — `POST /api/subscriptions/activate`

**Premium** (Rp 99,000/mo): free shipping + 10% discount. **Enterprise** (Rp 299,000/mo): all Premium + API access + bulk ordering.

### Flow 5: Gift Cards

1. Purchase — `POST /api/gift-cards/purchase` → returns `gift_card_id`, `code`, `payment_id`
2. Confirm payment — `POST /api/gift-cards/payment/confirm`
3. Transfer *(optional)* — `POST /api/gift-cards/transfer`
4. Redeem — `POST /api/gift-cards/redeem`

### Flow 6: Returns and Refunds

1. Submit — `POST /api/returns/submit`
2. Admin approves — `PUT /api/returns/:id/approve`
3. Process refund — `POST /api/returns/:id/process-refund` → credits balance

---

## Seed Data

### Products

| ID | Name | Price | Category |
|----|------|-------|----------|
| P001 | Nasi Goreng Special | Rp 25,000 | food |
| P002 | Mie Ayam Bakso | Rp 20,000 | food |
| P003 | Es Teh Manis | Rp 8,000 | drink |
| P004 | Jus Alpukat Segar | Rp 18,000 | drink |
| P005 | Kopi Susu Kekinian | Rp 22,000 | drink |
| P006 | Dish Washing Liquid 500ml | Rp 15,000 | household |
| P007 | Laundry Detergent Powder 1kg | Rp 35,000 | household |
| P008 | Cooking Oil 1L | Rp 28,000 | grocery |

### Subscription Plans

| ID | Name | Price | Benefits |
|----|------|-------|---------|
| basic | Basic | Free | Standard access |
| premium | Premium | Rp 99,000/mo | Free shipping, 10% discount |
| enterprise | Enterprise | Rp 299,000/mo | All Premium + API + bulk |

### Gift Card Denominations

Rp 50,000 · Rp 100,000 · Rp 200,000 · Rp 500,000

### Shipping Methods

| Method | Cost | Delivery |
|--------|------|---------|
| regular | Rp 15,000 | 3–5 business days |
| express | Rp 25,000 | 1–2 business days |
| same_day | Rp 45,000 | Today by 9 PM |

---

## Technical Notes

- All data is stored in-memory. Restarting the server resets all data.
- OTPs for email verification and 2FA are returned in API responses for testing convenience.
- Tokens do not expire during a single server session.
