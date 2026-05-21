#!/usr/bin/env python3
"""
Combined vulnerability validator: WarungKu (localhost:5000) + Juice Shop (localhost:3000).

Runs all 33 vulnerability checks (18 WK + 15 JS) against live local servers.
Each test uses a freshly-registered user, isolates state, prints PASS/FAIL.

Usage:
    python3 verify_all.py            # run both
    python3 verify_all.py wk         # WarungKu only
    python3 verify_all.py js         # Juice Shop only

Exit code 0 if all PASS, 1 otherwise.
"""

import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import verify_wk  # noqa: E402
import verify_js  # noqa: E402


def run_wk():
    verify_wk.RESULTS.clear()
    rc = verify_wk.main()
    return rc, list(verify_wk.RESULTS)


def run_js():
    verify_js.RESULTS.clear()
    rc = verify_js.main()
    return rc, list(verify_js.RESULTS)


def main():
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
    wk_results, js_results = [], []
    rc_wk = rc_js = 0
    if arg in ("all", "wk"):
        rc_wk, wk_results = run_wk()
    if arg in ("all", "js"):
        rc_js, js_results = run_js()

    print("\n" + "=" * 60)
    print("OVERALL SUMMARY")
    print("=" * 60)
    official_js = {f"JS-{i:02d}" for i in range(1, 12)}
    in_scope = wk_results + [r for r in js_results if r[0] in official_js]
    out_scope = [r for r in js_results if r[0] not in official_js]
    in_pass = sum(1 for _, s, _ in in_scope if s == "PASS")
    out_pass = sum(1 for _, s, _ in out_scope if s == "PASS")
    print(f"In analysis scope: {in_pass}/{len(in_scope)} exploitable")
    if wk_results:
        wp = sum(1 for _, s, _ in wk_results if s == "PASS")
        print(f"  WarungKu (V1..V18):                {wp}/{len(wk_results)}")
    if js_results:
        official_pass = sum(1 for v, s, _ in js_results if v in official_js and s == "PASS")
        official_total = sum(1 for v, _, _ in js_results if v in official_js)
        print(f"  Juice Shop official (JS-01..JS-11): {official_pass}/{official_total}")
    if out_scope:
        print(f"Audit-only (removed JS-12..JS-15):   {out_pass}/{len(out_scope)} exploitable (real bugs but not in OWASP scoreboard)")
    failed_any = any(s == "FAIL" for _, s, _ in wk_results + js_results)
    return 1 if failed_any else 0


if __name__ == "__main__":
    sys.exit(main())
