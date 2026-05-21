"""Build Juice Shop scoring artifacts:
- scoring_long_juiceshop.csv  (220 rows = 11 vulns × 4 conds × 5 runs)
- scoring_long_combined.csv   (WK 360 + JS 220 = 580 rows, with app column)
- _aggregates.json            (for build_charts.py / xlsx builders)

n=11 selection: JS-01..JS-11 are the official OWASP Juice Shop challenges
(verified by name-match against /api/Challenges, 2026-05-19). Originally
JS-12..JS-15 were included in the published v3 ground truth but were
discovered to be source-code bugs not represented in the official scoreboard
— see CONTEXT_HANDOFF.md "URGENT" section and project_js_4_fabricated memory.
They are excluded from analysis as of 2026-05-19.

Reads:
- ../../03_scoring/scoring_long_warungku.csv

Writes everything to: ../../03_scoring/

Location-independent: run from anywhere with `python3 04_analysis/scripts/build_artifacts.py`
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

# Project root = two levels up from this script
ROOT = Path(__file__).resolve().parent.parent.parent
SCORING_DIR = ROOT / "03_scoring"
SCORING_DIR.mkdir(exist_ok=True)
WK_CSV = SCORING_DIR / "scoring_long_warungku.csv"

# ---------------------------------------------------------------------------
# Juice Shop scoring matrix (canonical) — from 4 Explore agents
# Per-run line breakdown. Original v3 ground truth had 15 vulns; we now slice
# to 11 (JS-01..JS-11) as JS-12..JS-15 turned out not to be in the official
# JS scoreboard. The raw 15-col rows below are preserved for audit, and then
# sliced via `[:JS_N_VULNS]` when materializing.
# Format: js_matrix_full[condition][run_index_0to4] = [JS-01..JS-15] binary
# ---------------------------------------------------------------------------
JS_N_VULNS = 11  # JS-01..JS-11 (official OWASP Juice Shop challenges)
js_matrix_full = {
    "A": [
        # A1..A5: all only detected JS-08
        [0,0,0,0,0,0,0,1,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,1,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,1,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,1,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,1,0,0,0,0,0,0,0],
    ],
    "Aprime": [
        # A'1: JS-04, JS-07, JS-12, JS-14
        [0,0,0,1,0,0,1,0,0,0,0,1,0,1,0],
        # A'2: JS-04, JS-07, JS-12
        [0,0,0,1,0,0,1,0,0,0,0,1,0,0,0],
        # A'3: JS-04, JS-12, JS-14
        [0,0,0,1,0,0,0,0,0,0,0,1,0,1,0],
        # A'4: JS-12, JS-15
        [0,0,0,0,0,0,0,0,0,0,0,1,0,0,1],
        # A'5: JS-07, JS-12, JS-14, JS-15
        [0,0,0,0,0,0,1,0,0,0,0,1,0,1,1],
    ],
    "B": [
        # B1: JS-07, JS-12, JS-13, JS-15
        [0,0,0,0,0,0,1,0,0,0,0,1,1,0,1],
        # B2: JS-12, JS-15
        [0,0,0,0,0,0,0,0,0,0,0,1,0,0,1],
        # B3: JS-07, JS-12, JS-13, JS-15
        [0,0,0,0,0,0,1,0,0,0,0,1,1,0,1],
        # B4: JS-07, JS-12
        [0,0,0,0,0,0,1,0,0,0,0,1,0,0,0],
        # B5: JS-07, JS-12, JS-15
        [0,0,0,0,0,0,1,0,0,0,0,1,0,0,1],
    ],
    "C": [
        # C1: 11 hits — missed JS-02, JS-05, JS-06, JS-15
        [1,0,1,1,0,0,1,1,1,1,1,1,1,1,0],
        # C2: 12 hits — missed JS-01, JS-05, JS-06
        [0,1,1,1,0,0,1,1,1,1,1,1,1,1,1],
        # C3: 12 hits — missed JS-01, JS-06, JS-08
        [0,1,1,1,1,0,1,0,1,1,1,1,1,1,1],
        # C4: 11 hits — missed JS-01, JS-02, JS-06, JS-15
        [0,0,1,1,1,0,1,1,1,1,1,1,1,1,0],
        # C5: 11 hits — missed JS-01, JS-05, JS-06, JS-14
        [0,1,1,1,0,0,1,1,1,1,1,1,1,0,1],
    ],
}

condition_labels = {"A": "A", "Aprime": "Aprime", "B": "B", "C": "C"}
# Slice raw 15-col rows to first JS_N_VULNS columns for analysis.
js_matrix = {c: [row[:JS_N_VULNS] for row in runs] for c, runs in js_matrix_full.items()}
js_vuln_ids = [f"JS-{i:02d}" for i in range(1, JS_N_VULNS + 1)]

# ---------------------------------------------------------------------------
# 1. Write scoring_long_js.csv
# ---------------------------------------------------------------------------
with open(SCORING_DIR / "scoring_long_juiceshop.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["run_id", "condition", "vuln_id", "detected", "app"])
    for cond_key, runs in js_matrix.items():
        for run_idx, hits in enumerate(runs, start=1):
            run_id = f"{cond_key}{run_idx}_JS"
            for vuln_idx, val in enumerate(hits):
                w.writerow([run_id, condition_labels[cond_key], js_vuln_ids[vuln_idx], val, "JuiceShop"])

# ---------------------------------------------------------------------------
# 2. Write combined CSV (WK + JS)
# ---------------------------------------------------------------------------
combined_rows = []
# Load existing WK csv
with open(WK_CSV) as f:
    r = csv.DictReader(f)
    for row in r:
        row["app"] = "WarungKu"
        # rename WK run_ids to be unambiguous
        row["run_id"] = f"{row['run_id']}_WK"
        combined_rows.append(row)
# Append JS rows
with open(SCORING_DIR / "scoring_long_juiceshop.csv") as f:
    r = csv.DictReader(f)
    for row in r:
        combined_rows.append(row)

with open(SCORING_DIR / "scoring_long_combined.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["run_id", "condition", "vuln_id", "detected", "app"])
    w.writeheader()
    for row in combined_rows:
        w.writerow({k: row[k] for k in ["run_id", "condition", "vuln_id", "detected", "app"]})

# ---------------------------------------------------------------------------
# 3. Compute aggregates
# ---------------------------------------------------------------------------
def aggregate(matrix, n_vulns):
    out = {}
    for cond, runs in matrix.items():
        run_totals = [sum(r) for r in runs]
        total_detected = sum(run_totals)
        total_obs = len(runs) * n_vulns
        mean = total_detected / len(runs)
        pct = total_detected / total_obs * 100
        # SD of run-level totals
        mu = mean
        variance = sum((x - mu) ** 2 for x in run_totals) / (len(runs) - 1) if len(runs) > 1 else 0
        sd = variance ** 0.5
        sd_pp = sd / n_vulns * 100
        out[cond] = {
            "run_totals": run_totals,
            "mean": mean,
            "pct": pct,
            "sd_count": sd,
            "sd_pp": sd_pp,
            "n_obs": total_obs,
            "n_detected": total_detected,
        }
    return out

js_agg = aggregate(js_matrix, JS_N_VULNS)

# Per-vuln totals for JS
js_per_vuln = defaultdict(lambda: defaultdict(int))
for cond, runs in js_matrix.items():
    for run in runs:
        for v_idx, val in enumerate(run):
            js_per_vuln[js_vuln_ids[v_idx]][cond] += val

# WK aggregates from existing CSV
wk_per_cond = defaultdict(lambda: defaultdict(int))
wk_per_run = defaultdict(lambda: defaultdict(int))
wk_per_vuln = defaultdict(lambda: defaultdict(int))
with open(WK_CSV) as f:
    for row in csv.DictReader(f):
        c = row["condition"]
        v = row["vuln_id"]
        d = int(row["detected"])
        run = row["run_id"]
        wk_per_cond[c]["detected"] += d
        wk_per_cond[c]["total"] += 1
        wk_per_run[c][run] += d
        wk_per_vuln[v][c] += d

wk_agg = {}
for c in ["A", "Aprime", "B", "C"]:
    run_totals = sorted(wk_per_run[c].values())
    mean = sum(run_totals) / len(run_totals)
    mu = mean
    sd = (sum((x - mu) ** 2 for x in run_totals) / (len(run_totals) - 1)) ** 0.5
    pct = wk_per_cond[c]["detected"] / wk_per_cond[c]["total"] * 100
    wk_agg[c] = {
        "run_totals": run_totals,
        "mean": mean,
        "pct": pct,
        "sd_count": sd,
        "sd_pp": sd / 18 * 100,
        "n_obs": wk_per_cond[c]["total"],
        "n_detected": wk_per_cond[c]["detected"],
    }

# ---------------------------------------------------------------------------
# 4. Print summary report
# ---------------------------------------------------------------------------
print("=" * 70)
print("WARUNGKU AGGREGATES (n=18 vulns × 5 runs per cond)")
print("=" * 70)
print(f"{'Cond':<8}{'Mean':>8}{'%':>10}{'SD(pp)':>10}{'Runs':>20}")
for c in ["A", "Aprime", "B", "C"]:
    a = wk_agg[c]
    print(f"{c:<8}{a['mean']:>8.2f}{a['pct']:>10.1f}{a['sd_pp']:>10.2f}{str(a['run_totals']):>20}")

print()
print("=" * 70)
print(f"JUICESHOP AGGREGATES (n={JS_N_VULNS} vulns × 5 runs per cond)")
print("=" * 70)
print(f"{'Cond':<8}{'Mean':>8}{'%':>10}{'SD(pp)':>10}{'Runs':>20}")
for c in ["A", "Aprime", "B", "C"]:
    a = js_agg[c]
    print(f"{c:<8}{a['mean']:>8.2f}{a['pct']:>10.1f}{a['sd_pp']:>10.2f}{str(a['run_totals']):>20}")

print()
print("=" * 70)
print("DECOMPOSITION (pp = percentage points)")
print("=" * 70)
print(f"{'Transition':<14}{'WK':>10}{'JS':>10}")
for (a, b) in [("A", "Aprime"), ("Aprime", "B"), ("B", "C"), ("A", "C")]:
    d_wk = wk_agg[b]["pct"] - wk_agg[a]["pct"]
    d_js = js_agg[b]["pct"] - js_agg[a]["pct"]
    print(f"{a}->{b:<10}{d_wk:>10.1f}{d_js:>10.1f}")

print()
print("=" * 70)
print("JUICESHOP PER-VULN BREAKDOWN")
print("=" * 70)
print(f"{'Vuln':<8}{'A':>4}{'Apr':>5}{'B':>4}{'C':>4}{'Total':>7}")
for v in js_vuln_ids:
    a, ap, b, c = js_per_vuln[v]["A"], js_per_vuln[v]["Aprime"], js_per_vuln[v]["B"], js_per_vuln[v]["C"]
    print(f"{v:<8}{a:>4}{ap:>5}{b:>4}{c:>4}{a+ap+b+c:>7}")

# Save aggregates JSON for downstream use
out = {
    "warungku": {k: {kk: vv for kk, vv in v.items() if kk != "run_totals"} | {"run_totals": v["run_totals"]}
                 for k, v in wk_agg.items()},
    "juiceshop": {k: {kk: vv for kk, vv in v.items() if kk != "run_totals"} | {"run_totals": v["run_totals"]}
                  for k, v in js_agg.items()},
    "js_per_vuln": {v: dict(js_per_vuln[v]) for v in js_vuln_ids},
}
with open(SCORING_DIR / "_aggregates.json", "w") as f:
    json.dump(out, f, indent=2, default=str)
print(f"\nWrote outputs to {SCORING_DIR}")
print("  scoring_long_juiceshop.csv")
print("  scoring_long_combined.csv")
print("  _aggregates.json (intermediate, consumed by build_chart_and_xlsx.py)")
