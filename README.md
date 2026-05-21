# BLV Prompt Scaffolding — Replication Package

Companion repository for the paper *"Decomposing Prompt Scaffolding for LLM Agent Detection of Business Logic Vulnerabilities: A Cross-Application Empirical Study."*

Empirical decomposition of prompt-engineering effects on LLM-based detection of state-machine business logic vulnerabilities (BLVs), across two architecturally distinct web applications. Agent under test: Claude Code Sonnet 4.6. Total experiment: 4 prompt conditions × 5 runs × 2 applications = 40 agent rollouts, scored against 29 in-scope vulnerabilities = **580 binary detection observations**.

## Headline result

| Cond | WarungKu (n=18) | Juice Shop (n=11 official) |
|---|---|---|
| A (control) | 8.9% | 9.1% |
| A′ (+scope+taxonomy) | 41.1% | 10.9% |
| B (+methodology) | 45.6% | 7.3% |
| C (+workflow invariants) | **73.3%** | **72.7%** |

Total scaffolding effect (A→C) replicates within **1 percentage point** across two applications: +64.4 pp (WK) vs +63.6 pp (JS). Decomposition reveals taxonomy effect is large on WK (+32.2 pp) but null on JS (+1.8 pp); methodology effect null on both apps with sign flip; workflow invariants drive the largest single improvement (+27.8 pp WK / +65.5 pp JS).

## Repository layout

```
.
├── paper/                  LaTeX source + figures (IEEE conference, 2-column)
├── warungku/               Custom Flask application with 18 planted BLVs (source)
├── ground_truth/           Planted vulnerability specifications (KEEP OUT OF AGENT WORKSPACE)
│   ├── WARUNGKU_GROUND_TRUTH.md       18 vulns, mechanism per vuln
│   └── JUICESHOP_GROUND_TRUTH.md      11 official OWASP scoreboard challenges in scope
├── design/                 Juice Shop scoping rationale (why JS, which challenges)
├── prompts/                The 4 prompt templates × 2 apps (8 files)
├── raw_runs/               40 agent transcripts as captured
│   ├── warungku/           4 files (one per condition), each containing 5 runs
│   └── juiceshop/          4 files (one per condition), each containing 5 runs
├── scoring/                Audit-trail scoring spreadsheets + long-format CSVs
│   ├── SCORING_MATRIX_WARUNGKU.xlsx   5 sheets incl. cell-by-cell matrix + edge case notes
│   ├── SCORING_MATRIX_JUICESHOP.xlsx  same design
│   ├── scoring_long_warungku.csv      360 rows
│   ├── scoring_long_juiceshop.csv     220 rows
│   └── scoring_long_combined.csv      580 rows — canonical regression input
├── verification/           Python scripts that confirm each in-scope vuln is exploitable
└── analysis/               Synthesis doc, statistical plan, R script, charts, build scripts
```

## ⚠️ Critical reproducibility warning

`ground_truth/` files **must not** be placed inside the directory the LLM agent has read access to. The agent will read the ground truth verbatim and reproduce its content as "findings," inflating detection rate to near-100%. This is not hypothetical — the original WarungKu A4 rollout was contaminated this way (found 18/18) and was excluded from analysis; a clean re-run found 1/18, consistent with other A-condition runs.

When reproducing this study, run the agent with its workspace pointing to `warungku/` (which contains app.py, static/, templates/, README.md) only. Keep `ground_truth/` elsewhere on disk and consult it only for post-hoc scoring.

## How to reproduce

### 1. Run WarungKu locally

```bash
cd warungku/
pip install flask
python3 app.py   # listens on http://localhost:5000
```

### 2. Run Juice Shop locally

Juice Shop is not in this repo (it is publicly maintained by OWASP). Spin up:

```bash
docker run --rm -p 3000:3000 bkimminich/juice-shop
```

Or follow the official instructions at <https://owasp.org/www-project-juice-shop/>.

### 3. Verify all 29 in-scope vulnerabilities are exploitable

With both apps running on localhost:5000 (WK) and localhost:3000 (JS):

```bash
cd verification/
python3 verify_all.py
```

Expected output: `29/29 PASS`. Uses Python stdlib only.

### 4. Reproduce the agent experiment

Set up Claude Code (Sonnet 4.6 via Claude Pro) pointed at one target app, with workspace = `warungku/` (or the Juice Shop directory) **and `ground_truth/` outside that workspace**. For each condition (A, A′, B, C), paste the corresponding prompt from `prompts/[cond]_[app].txt`, then run the agent. Capture the output. Repeat 5× per condition.

The transcripts in `raw_runs/` show what we captured from our own runs.

### 5. Score the agent output

Use the scoring rubric documented in the paper (§III-E and III-E.1): a vulnerability is scored 1 only if the agent's report contains (i) a working curl exploit proof, (ii) the correct endpoint, (iii) a mechanism matching the planted root cause. See `scoring/SCORING_MATRIX_*.xlsx` Sheet 4 for edge-case decisions from our scoring pass.

### 6. Re-derive aggregate numbers and charts

```bash
cd analysis/scripts/
python3 build_artifacts.py    # rebuilds scoring_long_*.csv + _aggregates.json
python3 build_charts.py       # rebuilds decomposition_chart.png + per_vuln_heatmap.png
```

Scripts use `pathlib`, are location-independent, and rely on Python stdlib + `matplotlib` + `openpyxl`.

## Citation

If you use this dataset, code, or methodology, please cite:

```
[BibTeX entry — to be filled in after publication]
```

## License

MIT — see `LICENSE`.

## Caveat on dataset utility over time

WarungKu and its planted vulnerabilities are now public. Future LLM pretraining corpora will likely incorporate this repository, which means **WarungKu will not remain a contamination-free benchmark indefinitely**. Researchers extending this methodology after ~2027 should construct their own custom application following the same design pattern (state-machine workflow with planted skip / replay / reorder / drop / accounting bugs).

## Contact

Issues, questions, replication failures: please file a GitHub issue.
