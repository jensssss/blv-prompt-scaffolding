# Vulnerability Verification

Validates that all planted business-logic vulnerabilities are actually exploitable against the running local servers.

## Result (latest run)

**29/29 in-scope PASS**, **4/4 audit-only PASS**.

- WarungKu: 18/18 (V1–V18)
- Juice Shop official scoreboard challenges: 11/11 (JS-01–JS-11)
- Juice Shop audit-only (removed from analysis 2026-05-19 because not in official scoreboard): 4/4 still exploitable (former JS-12..JS-15)

## How to run

Start both servers first:
- WarungKu Flask on `http://localhost:5000`
- Juice Shop on `http://localhost:3000`

Then:

```bash
python3 verify_all.py        # both apps
python3 verify_all.py wk     # WarungKu only
python3 verify_all.py js     # Juice Shop only
```

Exit code is 0 if all pass, 1 otherwise. Stdlib only, no `pip install` required.

## What each test does

Each vuln gets its own freshly-registered user (unique email per run, no cross-vuln state pollution). The test follows the exact exploit path in `GROUND_TRUTH.md` and asserts the documented scoring signature (e.g., a curl proof, an HTTP code, or a state-change like `voucher2 != voucher1`).

Pass criteria are intentionally strict — they match the same rubric used to score the 40 agent rollouts in `03_scoring/`.

## Files

- `verify_wk.py` — WarungKu tests (V1–V18)
- `verify_js.py` — Juice Shop tests (JS-01–JS-15)
- `verify_all.py` — driver that runs both and prints overall summary

## Caveats observed during validation

- WarungKu's server is **in-memory Flask** — state accumulates across runs (vouchers, baskets, orders). Tests are isolated by using fresh users, but if you `kill` the Flask process, the next run starts from a clean DB. Both scenarios produce identical PASS results because vuln signatures are per-user.
- Juice Shop **auto-creates a basket** at registration with the next sequential ID. The `find_basket_id()` helper iterates basket IDs and matches by `UserId` from the JWT — works regardless of how many users existed before.
- JS-06 (race condition / Multiple Likes) is the only test using parallel threads. It currently wins reliably under default conditions; on slower machines, increase the thread count from 5 to 10.
- JS-02 / JS-15 forge a coupon by z85-encoding `MMMyy-NN` where `MMM` is the current month (uppercase) and `yy` is the two-digit year. Encoding follows RFC 32/Z85. Coupon expires monthly, so re-run will regenerate it.

## Cross-reference

The validators encode the same exploit paths documented in:
- `warungku-store-cleaned/GROUND_TRUTH.md` (WK V1–V18)
- `01_design/JUICESHOP_GROUND_TRUTH.md` (JS-01–JS-15)

If the validator fails for a vuln, it means either (a) the server-side bug was patched, (b) the ground truth describes an unreachable code path, or (c) the test setup drifted. Triage by re-reading the relevant `GROUND_TRUTH.md` entry against the validator function.
