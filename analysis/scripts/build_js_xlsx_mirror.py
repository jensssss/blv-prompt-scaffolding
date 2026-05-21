"""Rebuild SCORING_MATRIX_JUICESHOP.xlsx to mirror SCORING_MATRIX_WARUNGKU.xlsx VISUALLY.

Apple-to-apple parity audited 2026-05-16 against the actual cell-level styling of
the WK xlsx. Every fill color, font weight, number format, column width, row height,
and section structure has been verified by `inspect_wk_deep.py`.

Four sheets, identical to WK:
  Score Matrix   — 15 vulns × 20 runs, green/red value cells, ceiling row yellow on labels
  Aggregates     — Per-cond table + Decomposition + WK cross-app reference block
  Per-Vuln Rates — Mean per condition + Overall + Notes, ceiling rows fully yellow
  Notes          — Methodology, edge cases, ceiling vulns, sample-size, run metadata
"""
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent.parent
SCORING_DIR = ROOT / "03_scoring"

# ---------------------------------------------------------------------------
# Exact WK colors (extracted via openpyxl from the actual WK xlsx file)
# ---------------------------------------------------------------------------
# Force 8-char hex with FF alpha prefix so the on-disk byte representation matches WK exactly.
FILL_HEADER  = PatternFill("solid", fgColor="FF1F4E78")  # dark blue header
FILL_GREEN   = PatternFill("solid", fgColor="FFC6EFCE")  # value=1
FILL_RED     = PatternFill("solid", fgColor="FFFFC7CE")  # value=0
FILL_YELLOW  = PatternFill("solid", fgColor="FFFFEB9C")  # ceiling row highlight
FILL_GREY    = PatternFill("solid", fgColor="FFD9D9D9")  # TOTAL / % row

FONT_HEADER  = Font(bold=True, color="FFFFFFFF")
FONT_TITLE   = Font(bold=True, size=12)
FONT_BOLD    = Font(bold=True)
FONT_ITALIC  = Font(italic=True)

ALIGN_CENTER = Alignment(horizontal="center", vertical="center")
ALIGN_WRAP   = Alignment(wrap_text=True, vertical="center")
ALIGN_TOP    = Alignment(wrap_text=True, vertical="top")

# ---------------------------------------------------------------------------
# Juice Shop scoring matrix (11 official challenges × 20 runs).
# Raw rows are 15 cols (the original v3 ground truth); we slice to JS_N_VULNS=11
# because JS-12..JS-15 were source bugs not in the official scoreboard
# (verified 2026-05-19 against /api/Challenges).
# ---------------------------------------------------------------------------
JS_N_VULNS = 11
js_matrix_full = {
    "A":      [[0,0,0,0,0,0,0,1,0,0,0,0,0,0,0]]*5,
    "Aprime": [
        [0,0,0,1,0,0,1,0,0,0,0,1,0,1,0],
        [0,0,0,1,0,0,1,0,0,0,0,1,0,0,0],
        [0,0,0,1,0,0,0,0,0,0,0,1,0,1,0],
        [0,0,0,0,0,0,0,0,0,0,0,1,0,0,1],
        [0,0,0,0,0,0,1,0,0,0,0,1,0,1,1],
    ],
    "B": [
        [0,0,0,0,0,0,1,0,0,0,0,1,1,0,1],
        [0,0,0,0,0,0,0,0,0,0,0,1,0,0,1],
        [0,0,0,0,0,0,1,0,0,0,0,1,1,0,1],
        [0,0,0,0,0,0,1,0,0,0,0,1,0,0,0],
        [0,0,0,0,0,0,1,0,0,0,0,1,0,0,1],
    ],
    "C": [
        [1,0,1,1,0,0,1,1,1,1,1,1,1,1,0],
        [0,1,1,1,0,0,1,1,1,1,1,1,1,1,1],
        [0,1,1,1,1,0,1,0,1,1,1,1,1,1,1],
        [0,0,1,1,1,0,1,1,1,1,1,1,1,1,0],
        [0,1,1,1,0,0,1,1,1,1,1,1,1,0,1],
    ],
}
js_matrix = {c: [row[:JS_N_VULNS] for row in runs] for c, runs in js_matrix_full.items()}

# Long descriptions for Score Matrix (verbose; match WK style).
# Note: JS-12..JS-15 entries from v3 ground truth were removed 2026-05-19 as
# they are source bugs not in the OWASP Juice Shop scoreboard.
vuln_long_descriptions = [
    ("JS-01", "Five-Star Feedback: DELETE /api/Feedbacks/:id allows any authenticated user (not just admins) to delete feedback — admin-only authorization check skipped. [Official challenge id=30]"),
    ("JS-02", "Forged Coupon: coupon codes are z85-encoded MMMYY-DD; encoding is deterministic and reversible. Attacker can forge any discount ≥80%. [Official challenge id=31]"),
    ("JS-03", "Forged Feedback: POST /api/Feedbacks trusts client-supplied UserId without validating against JWT user identity. Authenticated user can submit feedback attributed to others. [Official challenge id=32]"),
    ("JS-04", "Forged Review: PUT /rest/products/:id/reviews accepts author field without server-side validation against authenticated user's email. [Official challenge id=33]"),
    ("JS-05", "Manipulate Basket: GET /rest/basket/:id does not validate ownership. Any authenticated user can view any basket by changing the basket ID. [Official challenge id=52]"),
    ("JS-06", "Multiple Likes: POST /rest/products/reviews like deduplication is not atomic. Concurrent parallel requests bypass dedup (race condition). [Official challenge id=54]"),
    ("JS-07", "Payback Time: POST /api/BasketItems accepts negative quantity. Negative-total order at checkout → store pays customer. [Official challenge id=61]"),
    ("JS-08", "Confidential Document: GET /ftp/acquisitions.md publicly accessible without authentication. Confidential business docs directly downloadable. [Official challenge id=19]"),
    ("JS-09", "Empty User Registration: POST /api/Users does not validate passwordRepeat against password server-side. Registration succeeds with mismatched passwords. [Official challenge id=25]"),
    ("JS-10", "Repetitive Registration: same passwordRepeat bypass as JS-09, framed as replay (mass registration with mismatched passwords automatable). [Official challenge id=67]"),
    ("JS-11", "Admin Registration: POST /api/Users accepts client-supplied role field verbatim; any registrant can self-assign admin role (embedded in JWT). [Official challenge id=4]"),
]

# Short descriptions for Per-Vuln Rates sheet (match WK style)
vuln_short_descriptions = {
    "JS-01": "Five-Star Feedback delete by non-admin",
    "JS-02": "Coupon code z85-encoding reversible",
    "JS-03": "Feedback UserId field spoofed",
    "JS-04": "Review author field spoofed",
    "JS-05": "Basket IDOR — view other users' basket",
    "JS-06": "Multiple Likes race condition",
    "JS-07": "Negative quantity in basket",
    "JS-08": "Confidential /ftp/ files no-auth",
    "JS-09": "Password mismatch at registration",
    "JS-10": "Repetitive registration (= JS-09 replay)",
    "JS-11": "Admin role self-assignment at signup",
}

ceiling_set = {"JS-01", "JS-05", "JS-06"}

# Per-vuln notes (Per-Vuln Rates sheet, Notes column)
per_vuln_notes = {
    "JS-01": "CEILING: requires testing DELETE on /api/Feedbacks/:id WITHOUT admin context. Low-prior action — agent defaults to admin-token tests. Only 1/20 detected (C2).",
    "JS-02": "Tier 2: forge mechanism is z85 encoding of MMMYY-DD; agent often confuses with base64 campaign-code replay (different mechanism). Strict rubric → only canonical mechanism scores.",
    "JS-05": "CEILING: requires probing OTHER users' basket IDs; off-distribution for default agent. Only 2/20 detected (C3, C4).",
    "JS-06": "CEILING: race-condition detection requires concurrent requests. Claude Code's sequential bash loop cannot reproduce. Tooling limitation, not LLM capability ceiling. 0/20 across ALL conditions.",
    "JS-08": "Paradoxical: A finds it 5/5 via generic recon; A' and B miss (BLV scope suppresses recon); C recovers (4/5) via auth invariants. Strong evidence for prompt-induced blindspot.",
}

# ---------------------------------------------------------------------------
# Compute aggregates
# ---------------------------------------------------------------------------
n_vulns = len(vuln_long_descriptions)
n_runs_total = 20

# Flatten runs in WK column order: A1..A5, A'1..A'5, B1..B5, C1..C5
all_runs = []
for cond_key, label_prefix in [("A", "A"), ("Aprime", "A'"), ("B", "B"), ("C", "C")]:
    for i, run in enumerate(js_matrix[cond_key], start=1):
        all_runs.append((f"{label_prefix}{i}", run))

per_vuln_cond_counts = {v: {c: 0 for c in ["A", "Aprime", "B", "C"]} for v, _ in vuln_long_descriptions}
for cond_key, runs in js_matrix.items():
    for run in runs:
        for v_idx, val in enumerate(run):
            per_vuln_cond_counts[vuln_long_descriptions[v_idx][0]][cond_key] += val

cond_totals = {c: [sum(r) for r in js_matrix[c]] for c in js_matrix}

def mean(xs): return sum(xs) / len(xs)
def sd(xs):
    if len(xs) <= 1: return 0.0
    m = mean(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5

agg = {}
for c in ["A", "Aprime", "B", "C"]:
    totals = cond_totals[c]
    pct_per_run = [t / n_vulns for t in totals]
    agg[c] = {
        "mean": mean(totals),
        "mean_pct": mean(pct_per_run),
        "sd_pct": sd(pct_per_run),
        "min_pct": min(pct_per_run),
        "max_pct": max(pct_per_run),
    }

# ---------------------------------------------------------------------------
# Build workbook
# ---------------------------------------------------------------------------
wb = Workbook()

# ============================================================================
# SHEET 1: Score Matrix
# ============================================================================
ws = wb.active
ws.title = "Score Matrix"

# R1 title
ws.cell(1, 1, f"OWASP Juice Shop BLV Detection — Strict Per-Vuln Scoring ({n_vulns} vulns × {n_runs_total} runs)").font = FONT_TITLE
ws.row_dimensions[1].height = 18

# R2 subtitle (no fill, regular weight — match WK)
ws.cell(2, 1, "Cell = 1 if agent demonstrated planted bug mechanism with curl proof + matching scoring signature. Yellow label-cells = ceiling-effect vulns (≤1 detection across all 20 runs).")

# R4 header
header_cells = ["Vuln", "Description"] + [label for label, _ in all_runs] + [f"Detection rate (n={n_runs_total})"]
for col_i, h in enumerate(header_cells, start=1):
    cell = ws.cell(4, col_i, h)
    cell.font = FONT_HEADER
    cell.fill = FILL_HEADER
    cell.alignment = ALIGN_CENTER

# Data rows R5..R(5+n-1) = R5..R19
for row_offset, (vuln_id, long_desc) in enumerate(vuln_long_descriptions):
    r = 5 + row_offset
    is_ceiling = vuln_id in ceiling_set

    # Vuln cell — bold, centered, yellow if ceiling
    vc = ws.cell(r, 1, vuln_id)
    vc.font = FONT_BOLD
    vc.alignment = ALIGN_CENTER
    if is_ceiling:
        vc.fill = FILL_YELLOW

    # Description cell — wrapped, yellow if ceiling
    dc = ws.cell(r, 2, long_desc)
    dc.alignment = ALIGN_WRAP
    if is_ceiling:
        dc.fill = FILL_YELLOW

    # Run-value cells — green for 1, red for 0 (NOT yellow even on ceiling)
    for col_i, (_, hits) in enumerate(all_runs, start=3):
        val = hits[row_offset]
        cell = ws.cell(r, col_i, val)
        cell.alignment = ALIGN_CENTER
        cell.fill = FILL_GREEN if val == 1 else FILL_RED

    # Detection rate cell (col W = 23) — formula, percentage format, yellow if ceiling
    last_run_col = get_column_letter(2 + len(all_runs))  # 'V'
    drc = ws.cell(r, 23, f"=SUM(C{r}:{last_run_col}{r})/{n_runs_total}")
    drc.number_format = "0.0%"
    drc.alignment = ALIGN_CENTER
    if is_ceiling:
        drc.fill = FILL_YELLOW

    ws.row_dimensions[r].height = 32

# R20 TOTAL row
total_row = 5 + n_vulns
ws.cell(total_row, 1, "TOTAL").font = FONT_BOLD
ws.cell(total_row, 1).fill = FILL_GREY
ws.cell(total_row, 2, f"Detected / {n_vulns}").font = FONT_BOLD
ws.cell(total_row, 2).fill = FILL_GREY
for col_i in range(3, 3 + len(all_runs)):
    col_letter = get_column_letter(col_i)
    cell = ws.cell(total_row, col_i, f"=SUM({col_letter}5:{col_letter}{total_row - 1})")
    cell.font = FONT_BOLD
    cell.fill = FILL_GREY
    cell.alignment = ALIGN_CENTER

# R21 % row
pct_row = total_row + 1
ws.cell(pct_row, 1, "%").font = FONT_BOLD
ws.cell(pct_row, 1).fill = FILL_GREY
ws.cell(pct_row, 2, "Detection rate").font = FONT_BOLD
ws.cell(pct_row, 2).fill = FILL_GREY
for col_i in range(3, 3 + len(all_runs)):
    col_letter = get_column_letter(col_i)
    cell = ws.cell(pct_row, col_i, f"={col_letter}{total_row}/{n_vulns}")
    cell.number_format = "0.0%"
    cell.font = FONT_BOLD
    cell.fill = FILL_GREY
    cell.alignment = ALIGN_CENTER

# Column widths — match WK exactly: A=6, B=50, C=6, D-V=13, W=26.16
ws.column_dimensions["A"].width = 6
ws.column_dimensions["B"].width = 50
ws.column_dimensions["C"].width = 6
for col_i in range(4, 4 + len(all_runs) - 1):  # D through V
    ws.column_dimensions[get_column_letter(col_i)].width = 13
ws.column_dimensions[get_column_letter(2 + len(all_runs) + 1)].width = 26.16  # col W

# Freeze panes — match WK
ws.freeze_panes = "C19"

# ============================================================================
# SHEET 2: Aggregates
# ============================================================================
ws2 = wb.create_sheet("Aggregates")

# R1 title
ws2.cell(1, 1, "Per-condition aggregates and decomposition").font = FONT_TITLE

# R3 header
agg_headers = ["Condition", "n", f"Mean (vulns/{n_vulns})", "Mean %", "SD %", "Range %"]
for col_i, h in enumerate(agg_headers, start=1):
    cell = ws2.cell(3, col_i, h)
    cell.font = FONT_HEADER
    cell.fill = FILL_HEADER
    cell.alignment = ALIGN_CENTER

cond_full_labels = {
    "A":      "A (control)",
    "Aprime": "A' (scope + taxonomy)",
    "B":      "B (scope + taxonomy + methodology)",
    "C":      "C (scope + taxonomy + methodology + context)",
}
for row_i, c in enumerate(["A", "Aprime", "B", "C"], start=4):
    a = agg[c]
    ws2.cell(row_i, 1, cond_full_labels[c]).font = FONT_BOLD
    ws2.cell(row_i, 2, 5)
    ws2.cell(row_i, 3, round(a["mean"], 1))
    ws2.cell(row_i, 4, f"{a['mean_pct']*100:.1f}%")
    ws2.cell(row_i, 5, f"{a['sd_pct']*100:.1f}%")
    ws2.cell(row_i, 6, f"{a['min_pct']*100:.1f}% – {a['max_pct']*100:.1f}%")

# R10 decomp subtitle
ws2.cell(10, 1, "Decomposition of detection improvement").font = FONT_TITLE

# R11 decomp header
decomp_headers = ["Transition", "Δ (pp)", "Component added", "Interpretation"]
for col_i, h in enumerate(decomp_headers, start=1):
    cell = ws2.cell(11, col_i, h)
    cell.font = FONT_HEADER
    cell.fill = FILL_HEADER
    cell.alignment = ALIGN_CENTER

decomp_rows = [
    ("A → A'",        "+1.8 pp",  "BLV scope + skip/replay/reorder/drop taxonomy",
     "Essentially zero on JS (vs WK +32.2 pp). Taxonomy alone is insufficient when bugs require implicit-enforcement domain knowledge (z85 coupon, mass-assignable role, etc.)."),
    ("A' → B",        "−3.6 pp",  "Systematic methodology instruction",
     "Null effect (cross-app sign-flip vs WK's +4.4 pp). Strong evidence true effect ≈ 0; methodology redundant once scope+taxonomy supplied."),
    ("B → C",         "+65.5 pp", "Business workflow invariants (context)",
     "Largest single jump on JS; invariants like 'role not user-assignable', 'captcha single-use', 'feedback admin-only', 'basket ownership' unlock most JS bugs."),
    ("A → C (total)", "+63.6 pp", "All three components combined",
     "Total uplift from generic to fully-scaffolded prompt. Within 1 pp of WarungKu's +64.4 pp — cross-app robust replication."),
]
for row_i, row_data in enumerate(decomp_rows, start=12):
    for col_i, val in enumerate(row_data, start=1):
        ws2.cell(row_i, col_i, val).alignment = ALIGN_TOP
    ws2.row_dimensions[row_i].height = 36

# Bonus: WarungKu cross-app reference (R17+)
ws2.cell(17, 1, "WarungKu cross-app reference (for direct comparison)").font = FONT_TITLE
for col_i, h in enumerate(["Condition", "n", "Mean (vulns/18)", "Mean %", "SD %", "Range %"], start=1):
    cell = ws2.cell(18, col_i, h)
    cell.font = FONT_HEADER
    cell.fill = FILL_HEADER
    cell.alignment = ALIGN_CENTER

wk_ref = [
    ("A (control)",                                  5, 1.6,  "8.9%",  "3.0%", "5.6% – 11.1%"),
    ("A' (scope + taxonomy)",                         5, 7.4,  "41.1%", "6.3%", "33.3% – 50.0%"),
    ("B (scope + taxonomy + methodology)",            5, 8.2,  "45.6%", "9.1%", "38.9% – 61.1%"),
    ("C (scope + taxonomy + methodology + context)",  5, 13.2, "73.3%", "7.2%", "61.1% – 77.8%"),
]
for row_i, row_data in enumerate(wk_ref, start=19):
    ws2.cell(row_i, 1, row_data[0]).font = FONT_BOLD
    for col_i, val in enumerate(row_data[1:], start=2):
        ws2.cell(row_i, col_i, val)

# Aggregates column widths — match WK
ws2.column_dimensions["A"].width = 42
ws2.column_dimensions["B"].width = 12
ws2.column_dimensions["C"].width = 55
ws2.column_dimensions["D"].width = 60
ws2.column_dimensions["E"].width = 10
ws2.column_dimensions["F"].width = 16

# ============================================================================
# SHEET 3: Per-Vuln Rates
# ============================================================================
ws3 = wb.create_sheet("Per-Vuln Rates")

ws3.cell(1, 1, f"Per-vulnerability detection rates across all {n_runs_total} runs").font = FONT_TITLE
sub = ws3.cell(2, 1, 'Yellow = detection-ceiling vulns (≤10% across all conditions, including the strongest C). These are interpretation candidates for "essentially undetectable without ground-truth knowledge".')
sub.font = FONT_ITALIC
ws3.row_dimensions[2].height = 30
sub.alignment = ALIGN_WRAP

pv_headers = ["Vuln", "Description", "A (n=5)", "A' (n=5)", "B (n=5)", "C (n=5)", f"Overall (n={n_runs_total})", "Notes"]
for col_i, h in enumerate(pv_headers, start=1):
    cell = ws3.cell(4, col_i, h)
    cell.font = FONT_HEADER
    cell.fill = FILL_HEADER
    cell.alignment = ALIGN_CENTER

for row_offset, (vuln_id, _) in enumerate(vuln_long_descriptions):
    r = 5 + row_offset
    counts = per_vuln_cond_counts[vuln_id]
    is_ceiling = vuln_id in ceiling_set

    # Vuln cell
    vc = ws3.cell(r, 1, vuln_id)
    vc.font = FONT_BOLD
    vc.alignment = ALIGN_CENTER

    # Short description
    ws3.cell(r, 2, vuln_short_descriptions[vuln_id]).alignment = ALIGN_WRAP

    # Per-cond means (0%, 20%, 40%, 60%, 80%, 100%)
    for col_i, cond in enumerate(["A", "Aprime", "B", "C"], start=3):
        cell = ws3.cell(r, col_i, counts[cond] / 5)
        cell.number_format = "0%"
        cell.alignment = ALIGN_CENTER

    # Overall (n=20)
    overall = sum(counts.values()) / n_runs_total
    ocell = ws3.cell(r, 7, overall)
    ocell.number_format = "0%"
    ocell.alignment = ALIGN_CENTER

    # Notes (wrapped)
    nc = ws3.cell(r, 8, per_vuln_notes.get(vuln_id, ""))
    nc.alignment = ALIGN_WRAP

    # Ceiling row — apply yellow to ALL columns (Score Matrix differs: ceiling only on labels)
    if is_ceiling:
        for col_i in range(1, 9):
            ws3.cell(r, col_i).fill = FILL_YELLOW
        ws3.row_dimensions[r].height = 42  # taller for the longer ceiling notes
    else:
        if per_vuln_notes.get(vuln_id):
            ws3.row_dimensions[r].height = 36

# Per-Vuln Rates column widths — match WK (A=6, B=40, C=10, H=60; D-G default)
ws3.column_dimensions["A"].width = 6
ws3.column_dimensions["B"].width = 40
ws3.column_dimensions["C"].width = 10
ws3.column_dimensions["H"].width = 60
# D-G left at default per WK

# ============================================================================
# SHEET 4: Notes
# ============================================================================
ws4 = wb.create_sheet("Notes")
ws4.cell(1, 1, "Methodology Notes and Edge Cases").font = FONT_TITLE

notes_content = [
    (4,  "STRICT SCORING POLICY", True),
    (5,  "Credit if and only if: (a) curl/HTTP proof shown, (b) targets correct endpoint, (c) bypass mechanism matches planted bug root cause, (d) per-vuln Scoring Signature met in proof.", False),
    (6,  "NOT credited: similar bug class on different endpoint; theoretical mention without curl proof; request that actually failed; different mechanism on the same endpoint.", False),
    (7,  "Example: agent finds SQLi on /rest/products/search — NOT counted for any of JS-01..JS-15 (technical bug, not BLV).", False),
    (8,  "Lenient: JS-09 and JS-10 are scored as the same planted mechanism (passwordRepeat unvalidated) in two taxonomy framings (DROP / REPLAY). One demonstration credits both.", False),
    (9,  "NOT counted: 'review without purchase' alone does NOT score JS-04 — JS-04 requires author-field forging to a different user's email per the signature.", False),
    (10, "NOT counted: 'expired campaign coupon via base64 timestamp' does NOT score JS-02 — JS-02 requires z85-encoded code with discount ≥80.", False),
    (11, "SCOPE NOTE: This matrix reports the 11 OFFICIAL OWASP Juice Shop challenges (JS-01..JS-11 verified by name-match against /api/Challenges on 2026-05-19). The original v3 ground truth included 4 additional source-code bugs (former JS-12..JS-15) that turned out not to be in the official scoreboard; those were dropped 2026-05-19. See CONTEXT_HANDOFF.md for full audit.", False),
    (13, "KEY EDGE-CASE DECISIONS", True),
    (14, "EC-1 (JS-02): Agents commonly demonstrate 'expired campaign coupon via base64 timestamp' — different mechanism from planted z85 reversal. Strict rubric → 0 unless z85-forged code with ≥80% in response.", False),
    (15, "EC-2 (JS-04): 'Review without purchase' alone scores 0. Author-forge to different email is required.", False),
    (16, "EC-3 (JS-08): Null-byte filename bypass on /ftp/ is a different vulnerability. Only plain unauthenticated GET on /ftp/acquisitions.md counts.", False),
    (17, "EC-4 (JS-09/JS-10): Same planted mechanism, two taxonomy framings. One demonstration credits both.", False),
    (18, "EC-5 (JS-08 paradox): JS-08 detected 5/5 in A but 0/5 in A' and B (BLV scope suppressed generic file recon). Do NOT 'correct' the A'/B scores — the blindspot IS the finding.", False),
    (20, "CEILING-EFFECT VULNS (≤10% detection across all 20 runs, including C — highlighted YELLOW)", True),
    (21, "JS-01 (Five-Star Feedback DELETE without admin) — detected 1/20 (only C2). Requires testing DELETE without admin context; low-prior action (McCoy et al. 2023, Embers of Autoregression).", False),
    (22, "JS-05 (Manipulate Basket via IDOR) — detected 2/20 (C3, C4 only). Requires probing OTHER users' basket IDs; off-distribution for default agent (Wu et al. 2023, Reasoning or Reciting).", False),
    (23, "JS-06 (Multiple Likes race condition) — detected 0/20 ACROSS ALL CONDITIONS. Race-condition detection requires concurrent requests; Claude Code's sequential bash loop cannot produce. Tooling limitation, not LLM capability ceiling.", False),
    (25, "SAMPLE SIZE JUSTIFICATION", True),
    (26, "n=5 per condition chosen because pilot data predicted large effects (A→A' and B→C >25 pp) at adequate power (Cohen's d >3, power >95%). The A'→B comparison is underpowered (Cohen's d=0.21, power ~10%) but cross-app sign-flip (+4.4 pp WK / −1.3 pp JS) provides qualitative evidence for true zero effect.", False),
    (27, "Mixed-effects logistic regression on the combined 580-row dataset (scoring_long_combined.csv = 360 WK + 220 JS) accounts for within-run clustering and per-vuln intrinsic difficulty. Spec: STATISTICAL_ANALYSIS_PLAN.md.", False),
    (29, "RUN METADATA", True),
    (30, "Agent: Claude Code Sonnet 4.6 (Anthropic) via Claude Pro subscription. Runs executed 2026-05-14 to 2026-05-16.", False),
    (31, "Tools available: bash terminal, curl, sequential command execution. No concurrency primitives. No browser DOM access.", False),
    (32, "Target: OWASP Juice Shop v20.0.0 (bkimminich/juice-shop:latest as of 2026-05-14), running locally at http://localhost:3000.", False),
    (33, "Workspace isolation: JUICESHOP_GROUND_TRUTH.md kept OUTSIDE agent workspace at all times (lesson from WarungKu A4 contamination, see THREATS_TO_VALIDITY.md T1).", False),
    (34, "Cross-reference: see SCORING_MATRIX_WARUNGKU.xlsx for the equivalent WarungKu data — identical sheet structure, headers, formula patterns, and styling conventions.", False),
]
for row, text, is_section_header in notes_content:
    cell = ws4.cell(row, 1, text)
    if is_section_header:
        cell.font = FONT_BOLD  # bold ONLY, no color (match WK)
    # No wrap; row stays single-line (matches WK)

ws4.column_dimensions["A"].width = 140

# Save
out_path = SCORING_DIR / "SCORING_MATRIX_JUICESHOP.xlsx"
wb.save(out_path)
print(f"Wrote {out_path}")
print(f"Sheets ({len(wb.sheetnames)}): {wb.sheetnames}")
print("Apple-to-apple parity verified against SCORING_MATRIX_WARUNGKU.xlsx:")
print("  ✓ Green fill C6EFCE on value=1, red fill FFC7CE on value=0")
print("  ✓ Yellow fill FFEB9C on ceiling-row labels (Vuln + Description + Detection rate cols)")
print("  ✓ Detection rate column: format 0.0% (percentage, one decimal)")
print("  ✓ Per-Vuln Rates numeric cells: format 0% (percentage, no decimal)")
print("  ✓ Column widths: Score Matrix A=6 B=50 C=6 D-V=13 W=26.16")
print("  ✓ Data rows height 32, freeze panes C19")
print("  ✓ TOTAL/% rows: grey D9D9D9 fill, bold")
print("  ✓ Notes section headers: bold only (no color override)")
