"""Add 'Calculations' sheet to both SCORING_MATRIX_*.xlsx files.

The Calculations sheet shows the live arithmetic from Score Matrix raw data to
the aggregates (Mean, Mean %, SD %, Range %), using Excel formulas referencing
the Score Matrix sheet — so changing any cell in Score Matrix updates everything.

For each app the layout is identical (apple-to-apple):
  STEP 1: Per-run detection counts (pulled from Score Matrix)
  STEP 2: Per-condition aggregates with formulas
  STEP 3: Effect decomposition (Δ between conditions)
  Appendix: Formula explanations (plain language)
"""
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent.parent
SCORING_DIR = ROOT / "03_scoring"

FILL_HEADER = PatternFill("solid", fgColor="FF1F4E78")
FILL_GREY   = PatternFill("solid", fgColor="FFD9D9D9")
FILL_YELLOW = PatternFill("solid", fgColor="FFFFF2CC")
FONT_HEADER = Font(bold=True, color="FFFFFFFF")
FONT_TITLE  = Font(bold=True, size=12)
FONT_BOLD   = Font(bold=True)
FONT_ITALIC = Font(italic=True)
ALIGN_CENTER = Alignment(horizontal="center", vertical="center")
ALIGN_WRAP   = Alignment(wrap_text=True, vertical="center")


def add_calc_sheet(xlsx_path: Path, app_name: str, n_vulns: int,
                   total_row: int, pct_row: int):
    """
    xlsx_path: path to the xlsx
    app_name: 'WarungKu' or 'OWASP Juice Shop'
    n_vulns: 18 (WK) or 11 (JS, official challenges only)
    total_row: Score Matrix row containing TOTAL counts (23 for WK, 16 for JS-11)
    pct_row:   Score Matrix row containing % detection per run (24 for WK, 17 for JS-11)
    """
    wb = load_workbook(xlsx_path)
    # Replace if exists
    if "Calculations" in wb.sheetnames:
        del wb["Calculations"]
    ws = wb.create_sheet("Calculations")
    sm = "'Score Matrix'"  # reference name

    # ------------------- TITLE -------------------
    ws.cell(1, 1, f"Aggregate Calculations — Step-by-Step Audit Trail ({app_name})").font = FONT_TITLE
    ws.cell(2, 1, f"Every number in 'Aggregates' sheet is computed live from 'Score Matrix' raw data via Excel formulas. Edit any 0/1 cell in Score Matrix and these totals + means + SDs update automatically. n_vulns={n_vulns}, total_row={total_row} (TOTAL), pct_row={pct_row} (%).").font = FONT_ITALIC
    ws.cell(2, 1).alignment = ALIGN_WRAP
    ws.row_dimensions[2].height = 32

    # ------------------- STEP 1: Per-run detected counts -------------------
    ws.cell(4, 1, "STEP 1: Per-run detection counts (pulled live from Score Matrix Row " + str(total_row) + ")").font = FONT_BOLD
    headers1 = ["Run ID", "Cell in Score Matrix", "Detected count", "Total vulns", "% detected"]
    for col_i, h in enumerate(headers1, start=1):
        cell = ws.cell(5, col_i, h)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.alignment = ALIGN_CENTER

    # 20 runs, columns C-V in Score Matrix
    run_labels = [f"{p}{i}" for p in ["A", "A'", "B", "C"] for i in range(1, 6)]
    for row_offset, run_label in enumerate(run_labels):
        r = 6 + row_offset
        col_letter = get_column_letter(3 + row_offset)  # C=3, D=4, ..., V=22
        ws.cell(r, 1, run_label).font = FONT_BOLD
        ws.cell(r, 2, f"{sm}!{col_letter}{total_row}")
        ws.cell(r, 3, f"={sm}!{col_letter}{total_row}")  # pull TOTAL
        ws.cell(r, 4, n_vulns)
        ws.cell(r, 5, f"=C{r}/D{r}")
        ws.cell(r, 5).number_format = "0.0%"
        for c in [3, 4, 5]:
            ws.cell(r, c).alignment = ALIGN_CENTER

    # ------------------- STEP 2: Per-condition aggregates -------------------
    step2_row = 6 + 20 + 2  # blank row + section header
    ws.cell(step2_row, 1, "STEP 2: Per-condition aggregates").font = FONT_BOLD

    headers2 = ["Condition", "Runs included (% column)", "Mean count (vulns)",
                "Mean %", "SD %", "Min %", "Max %", "Range %"]
    for col_i, h in enumerate(headers2, start=1):
        cell = ws.cell(step2_row + 1, col_i, h)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.alignment = ALIGN_CENTER

    # Each condition uses 5 consecutive rows from STEP 1 (run percentages live in col E of THIS sheet)
    # A: rows 6-10, A': 11-15, B: 16-20, C: 21-25
    cond_ranges = [
        ("A (control)",                                "6:10",  6, 10),
        ("A' (scope + taxonomy)",                       "11:15", 11, 15),
        ("B (scope + taxonomy + methodology)",          "16:20", 16, 20),
        ("C (scope + taxonomy + methodology + context)","21:25", 21, 25),
    ]
    for i, (label, run_range, r_start, r_end) in enumerate(cond_ranges):
        r = step2_row + 2 + i
        ws.cell(r, 1, label).font = FONT_BOLD
        ws.cell(r, 2, f"E{r_start}:E{r_end}").font = FONT_ITALIC
        # Mean count = AVERAGE(detected counts) = AVERAGE(C{r_start}:C{r_end})
        ws.cell(r, 3, f"=AVERAGE(C{r_start}:C{r_end})")
        ws.cell(r, 3).number_format = "0.00"
        # Mean % = AVERAGE of per-run percentages
        ws.cell(r, 4, f"=AVERAGE(E{r_start}:E{r_end})")
        ws.cell(r, 4).number_format = "0.0%"
        # SD % = STDEV.S of per-run percentages (Bessel's n-1)
        ws.cell(r, 5, f"=STDEV.S(E{r_start}:E{r_end})")
        ws.cell(r, 5).number_format = "0.0%"
        # Min % / Max %
        ws.cell(r, 6, f"=MIN(E{r_start}:E{r_end})")
        ws.cell(r, 6).number_format = "0.0%"
        ws.cell(r, 7, f"=MAX(E{r_start}:E{r_end})")
        ws.cell(r, 7).number_format = "0.0%"
        # Range = Max - Min displayed as "X% – Y%"
        ws.cell(r, 8, f"=TEXT(F{r},\"0.0%\")&\" – \"&TEXT(G{r},\"0.0%\")")
        for c in range(3, 9):
            ws.cell(r, c).alignment = ALIGN_CENTER

    # ------------------- STEP 3: Effect decomposition -------------------
    step3_row = step2_row + 2 + len(cond_ranges) + 2
    ws.cell(step3_row, 1, "STEP 3: Effect decomposition (Δ between conditions, in percentage points)").font = FONT_BOLD

    headers3 = ["Transition", "Formula (cell refs)", "Δ Mean %",
                "Interpretation"]
    for col_i, h in enumerate(headers3, start=1):
        cell = ws.cell(step3_row + 1, col_i, h)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.alignment = ALIGN_CENTER

    # Conditions are at rows step2_row+2, step2_row+3, step2_row+4, step2_row+5
    # which are A, A', B, C — Mean % is in column D
    rA = step2_row + 2
    rAp = step2_row + 3
    rB = step2_row + 4
    rC = step2_row + 5
    transitions = [
        ("A → A'",        f"=D{rAp}-D{rA}",   "Adding BLV scope + skip/replay/reorder/drop taxonomy"),
        ("A' → B",        f"=D{rB}-D{rAp}",   "Adding systematic methodology instruction"),
        ("B → C",         f"=D{rC}-D{rB}",    "Adding business workflow invariants (context injection)"),
        ("A → C (total)", f"=D{rC}-D{rA}",    "All three components combined"),
    ]
    for i, (label, formula, interp) in enumerate(transitions):
        r = step3_row + 2 + i
        ws.cell(r, 1, label).font = FONT_BOLD
        ws.cell(r, 2, formula.replace("=", "")).font = FONT_ITALIC  # show as text
        ws.cell(r, 3, formula)
        ws.cell(r, 3).number_format = "+0.0%;-0.0%;0.0%"
        ws.cell(r, 4, interp).alignment = ALIGN_WRAP

    # ------------------- APPENDIX: Formula explanations -------------------
    appendix_row = step3_row + 2 + len(transitions) + 2
    ws.cell(appendix_row, 1, "APPENDIX: Formula explanations (in plain language)").font = FONT_BOLD

    notes = [
        "• Detected count per run = SUM of the 1s in that run's column in Score Matrix. The run column already has =SUM(...) in Row " + str(total_row) + ".",
        "• % detected per run = Detected count / n_vulns. The run column already has this in Row " + str(pct_row) + ".",
        "• Mean count (vulns) = arithmetic average of the 5 detected counts in that condition.",
        "• Mean % = arithmetic average of the 5 per-run percentages in that condition.",
        "  (Note: AVERAGE of percentages = TOTAL detected across all runs / TOTAL observations only when each run has the same n_vulns. Here it does, so the two are equivalent.)",
        "• SD % = STDEV.S of the 5 per-run percentages (Bessel's correction: divides by n−1 = 4, NOT by n = 5). This is the sample SD, which is what you report for an experiment that estimates a population parameter from a sample.",
        "• Min %, Max % = MIN/MAX of the 5 per-run percentages — the worst and best run in the condition.",
        "• Range % = Max − Min, displayed as 'low – high'. Gives a quick read on within-condition variance.",
        "• Δ Mean % (decomposition) = (mean of condition B) − (mean of condition A). Positive = condition B detects more on average.",
        "",
        "Why STDEV.S (sample, n−1) instead of STDEV.P (population, n)?",
        "  STDEV.P assumes you measured every run that exists. STDEV.S assumes you measured 5 runs out of an infinite pool of possible runs and want to estimate the true population SD. Bessel's correction (n−1 vs n) accounts for the fact that the sample mean is biased toward the sample (since the mean is computed from the same data the SD uses). For small n the correction matters: with n=5, STDEV.S is about 12% larger than STDEV.P. Always use STDEV.S for experiments.",
        "",
        "Cross-check: open 'Aggregates' sheet — values there should match the 'Mean count', 'Mean %', 'SD %', 'Range %' columns above.",
    ]
    for i, text in enumerate(notes):
        r = appendix_row + 1 + i
        ws.cell(r, 1, text).alignment = ALIGN_WRAP
        if "Why STDEV.S" in text:
            ws.cell(r, 1).font = FONT_BOLD

    # Column widths
    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 12
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 10
    ws.column_dimensions["G"].width = 10
    ws.column_dimensions["H"].width = 22

    # Save
    wb.save(xlsx_path)
    print(f"  Added Calculations sheet → {xlsx_path}")


# ---------------------------------------------------------------------------
# Run for both apps
# ---------------------------------------------------------------------------
print("Adding Calculations sheet to both xlsx files...")
add_calc_sheet(SCORING_DIR / "SCORING_MATRIX_WARUNGKU.xlsx",
               app_name="WarungKu", n_vulns=18, total_row=23, pct_row=24)
add_calc_sheet(SCORING_DIR / "SCORING_MATRIX_JUICESHOP.xlsx",
               app_name="OWASP Juice Shop", n_vulns=11, total_row=16, pct_row=17)
print("Done. Both xlsx now have 5 sheets: Score Matrix, Aggregates, Per-Vuln Rates, Notes, Calculations.")
