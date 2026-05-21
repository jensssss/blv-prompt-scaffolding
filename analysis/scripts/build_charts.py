"""Build decomposition_chart.png and per_vuln_heatmap.png.

Reads:
- ../../03_scoring/_aggregates.json  (produced by build_artifacts.py)
- ../../03_scoring/scoring_long_warungku.csv
- ../../03_scoring/scoring_long_juiceshop.csv

Writes:
- ../decomposition_chart.png  (04_analysis/)
- ../per_vuln_heatmap.png     (04_analysis/)

NB: The Juice Shop xlsx is built by `build_js_xlsx_mirror.py` (mirrors WK xlsx
design exactly). Do not regenerate the xlsx here.

Run order:
  1. build_artifacts.py        — CSVs + _aggregates.json
  2. build_charts.py           — this script
  3. build_js_xlsx_mirror.py   — SCORING_MATRIX_JUICESHOP.xlsx
"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCORING_DIR = ROOT / "03_scoring"
ANALYSIS_DIR = ROOT / "04_analysis"

# Load aggregates
with open(SCORING_DIR / "_aggregates.json") as f:
    agg = json.load(f)

conds = ["A", "Aprime", "B", "C"]
cond_labels = ["A", "A'", "B", "C"]
wk = agg["warungku"]
js = agg["juiceshop"]

# ============================================================================
# CHART 1: decomposition_chart.png — two-panel comparison
# ============================================================================
fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(13.5, 6.0), gridspec_kw={"width_ratios": [1, 0.85]})

# LEFT PANEL: per-condition detection rate bar chart with error bars
x = np.arange(len(conds))
width = 0.38
wk_pcts = [wk[c]["pct"] for c in conds]
js_pcts = [js[c]["pct"] for c in conds]
wk_sds = [wk[c]["sd_pp"] for c in conds]
js_sds = [js[c]["sd_pp"] for c in conds]

bars_wk = ax_left.bar(x - width/2, wk_pcts, width, yerr=wk_sds, capsize=4,
                       label="WarungKu (n=18 vulns × 5 runs)", color="#3a6ea5", edgecolor="#1c4978", linewidth=0.6)
bars_js = ax_left.bar(x + width/2, js_pcts, width, yerr=js_sds, capsize=4,
                       label="OWASP Juice Shop (n=11 × 5, official challenges)", color="#d97c30", edgecolor="#a85820", linewidth=0.6)

ax_left.set_xticks(x)
ax_left.set_xticklabels(cond_labels, fontsize=11)
ax_left.set_xlabel("Prompt condition", fontsize=11)
ax_left.set_ylabel("BLV detection rate (%)", fontsize=11)
ax_left.set_ylim(0, 100)
ax_left.set_yticks(np.arange(0, 101, 10))
ax_left.grid(axis="y", linestyle="--", alpha=0.35)
ax_left.set_axisbelow(True)
ax_left.legend(loc="upper left", fontsize=10, frameon=False)
ax_left.set_title("Per-condition BLV detection rate (± within-cond. SD)", fontsize=12)

# Annotate exact values on each bar
for b, v in zip(bars_wk, wk_pcts):
    ax_left.text(b.get_x() + b.get_width()/2, b.get_height() + 1.5, f"{v:.1f}",
                 ha="center", va="bottom", fontsize=9, color="#1c4978")
for b, v in zip(bars_js, js_pcts):
    ax_left.text(b.get_x() + b.get_width()/2, b.get_height() + 1.5, f"{v:.1f}",
                 ha="center", va="bottom", fontsize=9, color="#a85820")

# RIGHT PANEL: decomposition (Δ per transition) horizontal bar
transitions = [("A", "Aprime"), ("Aprime", "B"), ("B", "C"), ("A", "C")]
trans_labels = ["A → A'\n(scope+taxonomy)", "A' → B\n(methodology)", "B → C\n(workflow invariants)", "A → C\n(total)"]
wk_deltas = [wk[b]["pct"] - wk[a]["pct"] for a, b in transitions]
js_deltas = [js[b]["pct"] - js[a]["pct"] for a, b in transitions]

y = np.arange(len(transitions))
ax_right.barh(y - 0.2, wk_deltas, 0.38, label="WarungKu", color="#3a6ea5", edgecolor="#1c4978", linewidth=0.6)
ax_right.barh(y + 0.2, js_deltas, 0.38, label="Juice Shop", color="#d97c30", edgecolor="#a85820", linewidth=0.6)

# Zero line for null-effect reference
ax_right.axvline(0, color="#666", linewidth=0.8, linestyle="-")
ax_right.set_yticks(y)
ax_right.set_yticklabels(trans_labels, fontsize=10)
ax_right.invert_yaxis()
ax_right.set_xlabel("Δ detection rate (pp)", fontsize=11)
ax_right.set_title("Effect decomposition per transition", fontsize=12)
ax_right.grid(axis="x", linestyle="--", alpha=0.35)
ax_right.set_axisbelow(True)
ax_right.set_xlim(-10, 80)
ax_right.legend(loc="lower right", fontsize=10, frameon=False)

# Annotate deltas with sign
for i, (dw, dj) in enumerate(zip(wk_deltas, js_deltas)):
    sign_w = "+" if dw > 0 else ""
    sign_j = "+" if dj > 0 else ""
    ax_right.text(dw + (1.0 if dw >= 0 else -1.0), i - 0.2,
                  f"{sign_w}{dw:.1f}",
                  va="center", ha="left" if dw >= 0 else "right",
                  fontsize=9, color="#1c4978", fontweight="bold")
    ax_right.text(dj + (1.0 if dj >= 0 else -1.0), i + 0.2,
                  f"{sign_j}{dj:.1f}",
                  va="center", ha="left" if dj >= 0 else "right",
                  fontsize=9, color="#a85820", fontweight="bold")

fig.suptitle("Cross-app effect decomposition: WarungKu vs OWASP Juice Shop\nClaude Code Sonnet 4.6 — 4 prompt conditions × 5 runs each",
             fontsize=13, y=0.99)
plt.tight_layout()
plt.subplots_adjust(top=0.88)
plt.savefig(ANALYSIS_DIR / "decomposition_chart.png", dpi=160, bbox_inches="tight")
plt.close()
print(f"Wrote {ANALYSIS_DIR}/decomposition_chart.png")

# ============================================================================
# CHART 2: per-vuln heatmap (optional, but useful for thesis appendix)
# ============================================================================
fig2, (ax_wk, ax_js) = plt.subplots(1, 2, figsize=(13, 7), gridspec_kw={"width_ratios": [1.2, 1]})

# Load per-vuln matrices: re-compute from CSV
import csv

# WK per-vuln × condition (5 runs each → max 5)
wk_pv = {f"V{i}": {c: 0 for c in conds} for i in range(1, 19)}
with open(SCORING_DIR / "scoring_long_warungku.csv") as f:
    for r in csv.DictReader(f):
        wk_pv[r["vuln_id"]][r["condition"]] += int(r["detected"])

JS_N_VULNS = len(agg["js_per_vuln"])  # 11 after dropping JS-12..JS-15
wk_matrix = np.array([[wk_pv[f"V{i}"][c] for c in conds] for i in range(1, 19)])
js_matrix = np.array([[agg["js_per_vuln"][f"JS-{i:02d}"][c] for c in conds] for i in range(1, JS_N_VULNS + 1)])

# Heatmap WK
im_wk = ax_wk.imshow(wk_matrix, cmap="YlGn", aspect="auto", vmin=0, vmax=5)
ax_wk.set_xticks(np.arange(len(conds)))
ax_wk.set_xticklabels(cond_labels, fontsize=11)
ax_wk.set_yticks(np.arange(18))
ax_wk.set_yticklabels([f"V{i}" for i in range(1, 19)], fontsize=9)
ax_wk.set_title("WarungKu — detections/5 per (vuln, condition)", fontsize=12)
for i in range(18):
    for j in range(4):
        val = wk_matrix[i, j]
        color = "white" if val >= 4 else "black"
        ax_wk.text(j, i, str(val), ha="center", va="center", color=color, fontsize=9)
ax_wk.set_xlabel("Condition", fontsize=11)

# Heatmap JS
im_js = ax_js.imshow(js_matrix, cmap="YlGn", aspect="auto", vmin=0, vmax=5)
ax_js.set_xticks(np.arange(len(conds)))
ax_js.set_xticklabels(cond_labels, fontsize=11)
ax_js.set_yticks(np.arange(JS_N_VULNS))
ax_js.set_yticklabels([f"JS-{i:02d}" for i in range(1, JS_N_VULNS + 1)], fontsize=9)
ax_js.set_title(f"Juice Shop — detections/5 per (vuln, condition)  [n={JS_N_VULNS} official]", fontsize=12)
for i in range(JS_N_VULNS):
    for j in range(4):
        val = js_matrix[i, j]
        color = "white" if val >= 4 else "black"
        ax_js.text(j, i, str(val), ha="center", va="center", color=color, fontsize=9)
ax_js.set_xlabel("Condition", fontsize=11)

cbar = fig2.colorbar(im_js, ax=[ax_wk, ax_js], shrink=0.75, label="detections / 5 runs")
fig2.suptitle("Per-vulnerability detection heatmap", fontsize=13)
plt.savefig(ANALYSIS_DIR / "per_vuln_heatmap.png", dpi=160, bbox_inches="tight")
plt.close()
print(f"Wrote {ANALYSIS_DIR}/per_vuln_heatmap.png")
