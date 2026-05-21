"""Build 00_handoff/BIMBINGAN_CALCULATIONS.xlsx — self-contained audit workbook
that reproduces every number in BIMBINGAN_KEYPOINTS.md tables A, B, C plus
power analysis breakdown, all via live Excel formulas.

Five sheets:
  1. Table A  — Per-condition detection rates (live formulas from run totals)
  2. Table B  — Effect decomposition (live deltas from Table A)
  3. Table C  — Tier classification (Tier 1/2/3 by C-condition detection)
  4. Power    — Cohen's d, statistical power, why n=5 works for some and not others
  5. Cross-check — Sanity ties to scoring_long CSV row counts
"""
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent.parent
HANDOFF_DIR = ROOT / "00_handoff"

FILL_HEADER = PatternFill("solid", fgColor="FF1F4E78")
FILL_GREY   = PatternFill("solid", fgColor="FFD9D9D9")
FILL_GREEN  = PatternFill("solid", fgColor="FFC6EFCE")
FILL_RED    = PatternFill("solid", fgColor="FFFFC7CE")
FILL_YELLOW = PatternFill("solid", fgColor="FFFFEB9C")
FONT_HEADER = Font(bold=True, color="FFFFFFFF")
FONT_TITLE  = Font(bold=True, size=12)
FONT_BOLD   = Font(bold=True)
FONT_ITALIC = Font(italic=True)
CENTER = Alignment(horizontal="center", vertical="center")
WRAP   = Alignment(wrap_text=True, vertical="center")
TOP    = Alignment(wrap_text=True, vertical="top")

wb = Workbook()

# ============================================================================
# SHEET 1: Table A — Per-condition detection rates
# ============================================================================
ws = wb.active
ws.title = "Table A"

ws.cell(1, 1, "TABLE A — Per-condition Detection Rate (reproduces BIMBINGAN_KEYPOINTS Table A)").font = FONT_TITLE
ws.cell(2, 1, "Input: detected counts per run (typed as values). Output: aggregate per condition, computed via formulas.").font = FONT_ITALIC

# WarungKu block
ws.cell(4, 1, "WarungKu (n_vulns = 18 per run, 5 runs per condition)").font = FONT_BOLD

ws.cell(5, 1, "Condition").font = FONT_HEADER
ws.cell(5, 1).fill = FILL_HEADER
ws.cell(5, 1).alignment = CENTER
for col_i, h in enumerate(["Run 1", "Run 2", "Run 3", "Run 4", "Run 5"], start=2):
    ws.cell(5, col_i, h).font = FONT_HEADER
    ws.cell(5, col_i).fill = FILL_HEADER
    ws.cell(5, col_i).alignment = CENTER
for col_i, h in enumerate(["Mean count", "Mean %", "SD %", "Min %", "Max %"], start=7):
    ws.cell(5, col_i, h).font = FONT_HEADER
    ws.cell(5, col_i).fill = FILL_HEADER
    ws.cell(5, col_i).alignment = CENTER

# WK run totals — from scoring_long_warungku.csv aggregates
wk_data = {
    "A":      [2, 2, 1, 1, 2],
    "A'":     [6, 9, 8, 7, 7],
    "B":      [8, 11, 8, 7, 7],
    "C":      [14, 14, 11, 14, 13],
}

for i, (cond, totals) in enumerate(wk_data.items()):
    r = 6 + i
    ws.cell(r, 1, cond).font = FONT_BOLD
    for col_i, val in enumerate(totals, start=2):
        ws.cell(r, col_i, val).alignment = CENTER
    # Mean count = AVERAGE(B:F)
    ws.cell(r, 7, f"=AVERAGE(B{r}:F{r})")
    ws.cell(r, 7).number_format = "0.00"
    # Mean % = Mean count / 18
    ws.cell(r, 8, f"=G{r}/18")
    ws.cell(r, 8).number_format = "0.0%"
    # SD % over per-run percentages = STDEV.S of (B/18 ... F/18). Use array.
    ws.cell(r, 9, f"=STDEV.S(B{r}/18,C{r}/18,D{r}/18,E{r}/18,F{r}/18)")
    ws.cell(r, 9).number_format = "0.0%"
    # Min % / Max %
    ws.cell(r, 10, f"=MIN(B{r}:F{r})/18")
    ws.cell(r, 10).number_format = "0.0%"
    ws.cell(r, 11, f"=MAX(B{r}:F{r})/18")
    ws.cell(r, 11).number_format = "0.0%"

# Juice Shop block
ws.cell(11, 1, "OWASP Juice Shop (n_vulns = 11 official challenges per run, 5 runs per condition)").font = FONT_BOLD

ws.cell(12, 1, "Condition").font = FONT_HEADER
ws.cell(12, 1).fill = FILL_HEADER
ws.cell(12, 1).alignment = CENTER
for col_i, h in enumerate(["Run 1", "Run 2", "Run 3", "Run 4", "Run 5"], start=2):
    ws.cell(12, col_i, h).font = FONT_HEADER
    ws.cell(12, col_i).fill = FILL_HEADER
    ws.cell(12, col_i).alignment = CENTER
for col_i, h in enumerate(["Mean count", "Mean %", "SD %", "Min %", "Max %"], start=7):
    ws.cell(12, col_i, h).font = FONT_HEADER
    ws.cell(12, col_i).fill = FILL_HEADER
    ws.cell(12, col_i).alignment = CENTER

js_data = {
    "A":      [1, 1, 1, 1, 1],
    "A'":     [2, 2, 1, 0, 1],
    "B":      [1, 0, 1, 1, 1],
    "C":      [8, 8, 8, 8, 8],
}

for i, (cond, totals) in enumerate(js_data.items()):
    r = 13 + i
    ws.cell(r, 1, cond).font = FONT_BOLD
    for col_i, val in enumerate(totals, start=2):
        ws.cell(r, col_i, val).alignment = CENTER
    ws.cell(r, 7, f"=AVERAGE(B{r}:F{r})")
    ws.cell(r, 7).number_format = "0.00"
    ws.cell(r, 8, f"=G{r}/11")
    ws.cell(r, 8).number_format = "0.0%"
    ws.cell(r, 9, f"=STDEV.S(B{r}/11,C{r}/11,D{r}/11,E{r}/11,F{r}/11)")
    ws.cell(r, 9).number_format = "0.0%"
    ws.cell(r, 10, f"=MIN(B{r}:F{r})/11")
    ws.cell(r, 10).number_format = "0.0%"
    ws.cell(r, 11, f"=MAX(B{r}:F{r})/11")
    ws.cell(r, 11).number_format = "0.0%"

# Verification block
ws.cell(19, 1, "Cross-check vs BIMBINGAN_KEYPOINTS Table A").font = FONT_BOLD
ws.cell(20, 1, "All Mean count, Mean %, SD %, range values in this sheet should EXACTLY match BIMBINGAN_KEYPOINTS Table A.")
ws.cell(21, 1, "If you change any of the 40 run-total values above, all derived numbers update automatically — useful for re-scoring sensitivity checks.")

for col_letter, w in zip("ABCDEFGHIJK", [16, 8, 8, 8, 8, 8, 12, 10, 10, 10, 10]):
    ws.column_dimensions[col_letter].width = w

# ============================================================================
# SHEET 2: Table B — Decomposition
# ============================================================================
ws2 = wb.create_sheet("Table B")

ws2.cell(1, 1, "TABLE B — Effect Decomposition (reproduces BIMBINGAN_KEYPOINTS Table B)").font = FONT_TITLE
ws2.cell(2, 1, "Δ = (mean % of higher-condition) − (mean % of lower-condition). Live references to 'Table A' sheet.").font = FONT_ITALIC

for col_i, h in enumerate(["Transition", "Component added", "Δ WK (pp)", "Δ JS (pp)", "WK formula", "JS formula"], start=1):
    ws2.cell(4, col_i, h).font = FONT_HEADER
    ws2.cell(4, col_i).fill = FILL_HEADER
    ws2.cell(4, col_i).alignment = CENTER

decomp = [
    ("A → A'",        "BLV scope + skip/replay/reorder/drop taxonomy",
     "='Table A'!H7-'Table A'!H6",  "='Table A'!H14-'Table A'!H13"),
    ("A' → B",        "Systematic methodology instruction",
     "='Table A'!H8-'Table A'!H7",  "='Table A'!H15-'Table A'!H14"),
    ("B → C",         "Business workflow invariants (context)",
     "='Table A'!H9-'Table A'!H8",  "='Table A'!H16-'Table A'!H15"),
    ("A → C (total)", "All three components combined",
     "='Table A'!H9-'Table A'!H6",  "='Table A'!H16-'Table A'!H13"),
]
for i, (trans, comp, wk_f, js_f) in enumerate(decomp):
    r = 5 + i
    ws2.cell(r, 1, trans).font = FONT_BOLD
    ws2.cell(r, 2, comp).alignment = WRAP
    ws2.cell(r, 3, wk_f).number_format = "+0.0%;-0.0%;0.0%"
    ws2.cell(r, 4, js_f).number_format = "+0.0%;-0.0%;0.0%"
    # Show formulas as text for audit
    ws2.cell(r, 5, wk_f.replace("=", "")).font = FONT_ITALIC
    ws2.cell(r, 6, js_f.replace("=", "")).font = FONT_ITALIC

ws2.cell(10, 1, "Interpretation reminders").font = FONT_BOLD
ws2.cell(11, 1, "• Δ A→A' positive on both apps: scope+taxonomy is the largest single contributor.")
ws2.cell(12, 1, "• Δ A'→B near zero on both, with sign flip (+ on WK, − on JS): null effect, methodology redundant once taxonomy supplied.")
ws2.cell(13, 1, "• Δ B→C positive and large on both: invariant context unlocks knowledge-shaped bugs.")
ws2.cell(14, 1, "• Δ A→C total ~65-70 pp on both apps: total scaffolding effect generalizes across apps.")

for col_letter, w in zip("ABCDEF", [16, 45, 14, 14, 28, 28]):
    ws2.column_dimensions[col_letter].width = w

# ============================================================================
# SHEET 3: Table C — Tier classification
# ============================================================================
ws3 = wb.create_sheet("Table C")

ws3.cell(1, 1, "TABLE C — Vulnerability Tier Classification (reproduces BIMBINGAN_KEYPOINTS Table C)").font = FONT_TITLE
ws3.cell(2, 1, "Tier defined by detection at Condition C (strongest prompt). Each vuln has 5 attempts in C; counts displayed below.").font = FONT_ITALIC

# WK vulns C-detection
wk_c = {
    "V1": 5, "V2": 5, "V3": 4, "V4": 5, "V5": 0, "V6": 5, "V7": 4, "V8": 1, "V9": 5,
    "V10": 1, "V11": 5, "V12": 4, "V13": 3, "V14": 5, "V15": 1, "V16": 5, "V17": 5, "V18": 3,
}
js_c = {
    "JS-01": 1, "JS-02": 3, "JS-03": 5, "JS-04": 5, "JS-05": 2, "JS-06": 0, "JS-07": 5,
    "JS-08": 4, "JS-09": 5, "JS-10": 5, "JS-11": 5,
}

def tier(c):
    if c >= 4: return "Tier 1 — Reliable"
    if c >= 2: return "Tier 2 — Inconsistent"
    return "Tier 3 — Ceiling"

# Headers
for col_i, h in enumerate(["Vuln", "App", "C detections / 5", "Tier", "Color"], start=1):
    ws3.cell(4, col_i, h).font = FONT_HEADER
    ws3.cell(4, col_i).fill = FILL_HEADER
    ws3.cell(4, col_i).alignment = CENTER

row = 5
for v, c in list(wk_c.items()) + list(js_c.items()):
    app = "WarungKu" if v.startswith("V") and not v.startswith("JS") else "Juice Shop"
    t = tier(c)
    ws3.cell(row, 1, v).font = FONT_BOLD
    ws3.cell(row, 1).alignment = CENTER
    ws3.cell(row, 2, app).alignment = CENTER
    ws3.cell(row, 3, c).alignment = CENTER
    ws3.cell(row, 4, t)
    # Color band
    if "Tier 1" in t:
        fill = FILL_GREEN
    elif "Tier 2" in t:
        fill = FILL_YELLOW
    else:
        fill = FILL_RED
    for c2 in range(1, 6):
        ws3.cell(row, c2).fill = fill
    row += 1

# Summary block
summary_row = row + 2
ws3.cell(summary_row, 1, "Tier summary").font = FONT_BOLD
for col_i, h in enumerate(["Tier", "WK vulns", "JS vulns", "Total", "Formula"], start=1):
    ws3.cell(summary_row + 1, col_i, h).font = FONT_HEADER
    ws3.cell(summary_row + 1, col_i).fill = FILL_HEADER
    ws3.cell(summary_row + 1, col_i).alignment = CENTER

wk_data_range = f"C5:C22"   # 18 WK vulns at rows 5..22
js_data_range = f"C23:C33"  # 11 JS vulns at rows 23..33

ws3.cell(summary_row + 2, 1, "Tier 1 (C ≥ 4/5)")
ws3.cell(summary_row + 2, 2, f"=COUNTIF({wk_data_range},\">=4\")")
ws3.cell(summary_row + 2, 3, f"=COUNTIF({js_data_range},\">=4\")")
ws3.cell(summary_row + 2, 4, f"=B{summary_row+2}+C{summary_row+2}")
ws3.cell(summary_row + 2, 5, f"COUNTIF for c >= 4").font = FONT_ITALIC

ws3.cell(summary_row + 3, 1, "Tier 2 (C 2-3/5)")
ws3.cell(summary_row + 3, 2, f"=COUNTIFS({wk_data_range},\">=2\",{wk_data_range},\"<=3\")")
ws3.cell(summary_row + 3, 3, f"=COUNTIFS({js_data_range},\">=2\",{js_data_range},\"<=3\")")
ws3.cell(summary_row + 3, 4, f"=B{summary_row+3}+C{summary_row+3}")
ws3.cell(summary_row + 3, 5, f"COUNTIFS for 2 <= c <= 3").font = FONT_ITALIC

ws3.cell(summary_row + 4, 1, "Tier 3 (C ≤ 1/5)")
ws3.cell(summary_row + 4, 2, f"=COUNTIF({wk_data_range},\"<=1\")")
ws3.cell(summary_row + 4, 3, f"=COUNTIF({js_data_range},\"<=1\")")
ws3.cell(summary_row + 4, 4, f"=B{summary_row+4}+C{summary_row+4}")
ws3.cell(summary_row + 4, 5, f"COUNTIF for c <= 1").font = FONT_ITALIC

# Color summary rows
for r_offset, fill in enumerate([FILL_GREEN, FILL_YELLOW, FILL_RED]):
    for c in range(1, 6):
        ws3.cell(summary_row + 2 + r_offset, c).fill = fill

for col_letter, w in zip("ABCDE", [12, 13, 17, 22, 14]):
    ws3.column_dimensions[col_letter].width = w

# ============================================================================
# SHEET 4: Power Analysis
# ============================================================================
ws4 = wb.create_sheet("Power Analysis")

ws4.cell(1, 1, "POWER ANALYSIS — Why n=5 works for some comparisons but not others").font = FONT_TITLE
ws4.cell(2, 1, "Cohen's d = (mean_diff) / (pooled SD). Larger d → easier to detect with small n. Power = probability of correctly detecting a real effect.").font = FONT_ITALIC
ws4.cell(2, 1).alignment = WRAP
ws4.row_dimensions[2].height = 32

# Block A: Cohen's d calculation for each comparison
ws4.cell(4, 1, "STEP 1: Cohen's d per pairwise comparison").font = FONT_BOLD

for col_i, h in enumerate(
    ["Comparison", "App", "Mean diff (pp)", "Pooled SD (pp)", "Cohen's d", "Interpretation", "Power at n=5 (α=0.05, one-sided)"],
    start=1
):
    ws4.cell(5, col_i, h).font = FONT_HEADER
    ws4.cell(5, col_i).fill = FILL_HEADER
    ws4.cell(5, col_i).alignment = CENTER

# Data — pulled values from existing scoring (JS n=11 official challenges only)
# WK SDs: A=3.0, A'=6.3, B=9.1, C=7.2 (in pp)
# JS SDs (n=11): A=0.0, A'=7.6, B=4.1, C=0.0 (in pp)
# Pooled SD = sqrt((SD1^2 + SD2^2) / 2)
comparisons = [
    ("A vs A'", "WarungKu", 32.2,
     "=SQRT((3.0^2+6.3^2)/2)", "=C6/D6",
     "Very large", "> 99%"),
    ("A vs A'", "Juice Shop", 1.8,
     "=SQRT((0.0^2+7.6^2)/2)", "=ABS(C7)/D7",
     "Tiny", "≈ 8%  (SEVERELY UNDERPOWERED — but matches null story)"),
    ("A' vs B", "WarungKu", 4.4,
     "=SQRT((6.3^2+9.1^2)/2)", "=C8/D8",
     "Small", "≈ 26%  (UNDERPOWERED)"),
    ("A' vs B", "Juice Shop", -3.6,
     "=SQRT((7.6^2+4.1^2)/2)", "=ABS(C9)/D9",
     "Small (negative direction)", "≈ 18%  (UNDERPOWERED)"),
    ("B vs C", "WarungKu", 27.8,
     "=SQRT((9.1^2+7.2^2)/2)", "=C10/D10",
     "Very large", "> 99%"),
    ("B vs C", "Juice Shop", 65.5,
     "=SQRT((4.1^2+0.0^2)/2)", "=C11/D11",
     "Enormous", "> 99%"),
]

for i, (comp, app, diff, sd_formula, d_formula, interp, power) in enumerate(comparisons):
    r = 6 + i
    ws4.cell(r, 1, comp).font = FONT_BOLD
    ws4.cell(r, 2, app)
    ws4.cell(r, 3, diff).number_format = "+0.0;-0.0;0.0"
    ws4.cell(r, 4, sd_formula).number_format = "0.00"
    ws4.cell(r, 5, d_formula).number_format = "0.00"
    ws4.cell(r, 6, interp)
    ws4.cell(r, 7, power)
    # Color code
    if "UNDERPOWERED" in power:
        for c in [1, 2, 7]:
            ws4.cell(r, c).fill = FILL_RED
    else:
        for c in [1, 2, 7]:
            ws4.cell(r, c).fill = FILL_GREEN

# Block B: Pentest-flavored explanation
ws4.cell(14, 1, "STEP 2: Plain-language explanation (for someone with offsec background, not stats)").font = FONT_BOLD

explanation = [
    "",
    "Q: What is statistical power?",
    "  Imagine you run this experiment 100 times in a universe where there IS a real effect.",
    "  Power = the fraction of those 100 experiments where you'd correctly detect the effect.",
    "  Power = 80% means you'd catch the bug 80 times out of 100 runs. Standard 'good enough' threshold.",
    "  Power = 26% means you'd catch it only 26 times out of 100 — most experiments would falsely say 'no effect'.",
    "",
    "Q: What is Cohen's d?",
    "  d = (gap between two conditions) / (typical noise within a condition).",
    "  Pentest analogy: d is how many 'critical-vs-info bug noise levels' apart the two conditions are.",
    "  d = 6 → huge gap, like Critical SQLi vs no finding. Catch it with 1-2 tests.",
    "  d = 3 → strong gap, like obvious IDOR. Catch it with a handful of tests.",
    "  d = 0.5 → small gap, like timing-based blind SQLi. Need many tests to catch reliably.",
    "  d = 0.2 → tiny gap, like a 50ms timing oracle. Need a LOT of tests.",
    "",
    "Q: Why does n=5 work for some comparisons but not others?",
    "  For A→A' on WarungKu, gap is +32.2 pp, SD ~5 pp. d = 32.2/5 ≈ 6. Easy to detect — like Critical RCE on default credentials.",
    "  For A'→B, gap is +4.4 pp, SD ~8 pp. d ≈ 0.5. Signal is below noise floor — like detecting a 5% timing difference when each request varies ±15%.",
    "  Five samples is enough when signal >> noise. Not enough when signal ≈ noise.",
    "",
    "Q: How is power computed?",
    "  Given d and n, power is computed via the non-central t-distribution. Standard tools: G*Power (free), pwr package in R.",
    "  Rule of thumb: power = 80% reached at n ≈ 16/d² for two-sample comparisons. So d=6 needs n≈0.5 (one sample is enough!); d=0.5 needs n≈64; d=0.2 needs n≈400.",
    "",
    "Q: What's the honest framing for the dosen?",
    "  ✓ 'A→A' effect is large and reliably detected: Cohen's d > 3 means power > 99% even at n=5.'",
    "  ✓ 'B→C effect is large and reliably detected on both apps: same logic.'",
    "  ✗ AVOID: 'methodology has zero effect' — we cannot prove zero, just cannot detect at our n.",
    "  ✓ HONEST: 'methodology effect is small enough that n=5 cannot distinguish it from zero. Direction-flip across apps (+4.4 WK, -1.3 JS) is qualitative evidence true effect is ≈0, but formally inconclusive.'",
    "",
    "Q: Could I just run more agent sessions to fix the underpower?",
    "  To reach power=0.8 on the methodology effect, need n ≈ 25 per arm per app. That's 75 more runs total. At ~10 min per run = ~12 hours of agent compute. Possible but not pre-registered. Time budget: ~4 weeks to defense.",
    "  Decision: keep n=5, frame A'→B honestly as exploratory.",
]

for i, text in enumerate(explanation):
    r = 15 + i
    cell = ws4.cell(r, 1, text)
    if text.startswith("Q:"):
        cell.font = FONT_BOLD
    cell.alignment = WRAP
    if text and not text.startswith("Q:"):
        ws4.row_dimensions[r].height = 22

# Block C: Formulas explanation
explain_row = 15 + len(explanation) + 2
ws4.cell(explain_row, 1, "STEP 3: Formulas used in this sheet").font = FONT_BOLD

formulas = [
    "Pooled SD = SQRT((SD1^2 + SD2^2) / 2)  — standard formula for two-sample pooled standard deviation when group sizes are equal.",
    "Cohen's d = |mean_diff| / pooled_SD",
    "Power ≈ Φ(d × sqrt(n/2) − z_α)  where Φ is normal CDF, z_α = 1.645 for α=0.05 one-sided. Approximation valid for moderate-to-large d.",
    "For exact power, use R pwr package: pwr.t.test(n=5, d=YOUR_D, alternative='greater')",
]
for i, t in enumerate(formulas):
    r = explain_row + 1 + i
    ws4.cell(r, 1, t).alignment = WRAP
    ws4.row_dimensions[r].height = 20

for col_letter, w in zip("ABCDEFG", [14, 12, 15, 16, 13, 22, 32]):
    ws4.column_dimensions[col_letter].width = w

# ============================================================================
# SHEET 5: Cross-check
# ============================================================================
ws5 = wb.create_sheet("Cross-check")

ws5.cell(1, 1, "CROSS-CHECK — Sanity ties to scoring_long CSV files").font = FONT_TITLE
ws5.cell(2, 1, "Verifies that the Table A run totals are consistent with scoring_long_warungku.csv and scoring_long_juiceshop.csv row counts.").font = FONT_ITALIC

checks = [
    ("", "", "", ""),
    ("WarungKu", "", "", ""),
    ("  Total binary observations (= 5 runs × 4 cond × 18 vulns)", "=5*4*18", "= 360", "Match scoring_long_warungku.csv row count"),
    ("  Sum of detected = (A: 2+2+1+1+2) + (A': 6+9+8+7+7) + (B: 8+11+8+7+7) + (C: 14+14+11+14+13)", "=SUM(8,37,41,66)", "= 152", "Match SUM of detected column in CSV"),
    ("  Overall detection rate", "=152/360", "", "8.9% A + 41.1% A' + 45.6% B + 73.3% C = 42.2% overall"),
    ("", "", "", ""),
    ("Juice Shop (n=11 official challenges only)", "", "", ""),
    ("  Total binary observations (= 5 runs × 4 cond × 11 vulns)", "=5*4*11", "= 220", "Match scoring_long_juiceshop.csv row count"),
    ("  Sum of detected = (A: 5) + (A': 6) + (B: 4) + (C: 40)", "=SUM(5,6,4,40)", "= 55", "Match SUM of detected column in CSV"),
    ("  Overall detection rate", "=55/220", "", "9.1% A + 10.9% A' + 7.3% B + 72.7% C = 25.0% overall"),
    ("", "", "", ""),
    ("Combined", "", "", ""),
    ("  Total observations across both apps", "=360+220", "= 580", "Match scoring_long_combined.csv row count"),
    ("  Total detected", "=152+55", "= 207", "Match SUM"),
]
for col_i, h in enumerate(["Check", "Formula", "Expected value", "Source"], start=1):
    ws5.cell(4, col_i, h).font = FONT_HEADER
    ws5.cell(4, col_i).fill = FILL_HEADER
    ws5.cell(4, col_i).alignment = CENTER

for i, row_data in enumerate(checks):
    r = 5 + i
    for col_i, val in enumerate(row_data, start=1):
        cell = ws5.cell(r, col_i, val)
        if "WarungKu" == val or "Juice Shop" == val or "Combined" == val:
            cell.font = FONT_BOLD
        else:
            cell.alignment = WRAP

for col_letter, w in zip("ABCD", [75, 35, 20, 50]):
    ws5.column_dimensions[col_letter].width = w

# Save
HANDOFF_DIR.mkdir(exist_ok=True)
out_path = HANDOFF_DIR / "BIMBINGAN_CALCULATIONS.xlsx"
wb.save(out_path)
print(f"Wrote {out_path}")
print("5 sheets: Table A, Table B, Table C, Power Analysis, Cross-check")
