# Statistical Analysis Plan — Cross-App BLV Detection Experiment (WarungKu + Juice Shop)

**Version:** v3 — JS reduced from 15 to 11 (official challenges only) on 2026-05-19. Supersedes v2.

## Design

- **Apps:** 2 — WarungKu (custom, 18 planted vulns) and OWASP Juice Shop (public, 11 official challenges verified by name-match against `/api/Challenges`)
- **Factors:** 4 prompt conditions (A, A', B, C), each n=5 runs per app
- **Outcome:** binary detection per (run, vuln) pair
- **Total observations:**
  - WarungKu: 4 × 5 × 18 = 360 binary outcomes (20 independent runs)
  - Juice Shop: 4 × 5 × 11 = 220 binary outcomes (20 independent runs)
  - Combined: 580 binary outcomes from 40 independent agent rollouts
- **Effective sample size for inference:** 40 independent runs (vulns within a run are NOT independent — they share the same prompt and agent rollout)

## Observed aggregates

| Cond | WarungKu mean/18 | WK % | WK SD (pp) | JuiceShop mean/11 | JS % | JS SD (pp) |
|---|---|---|---|---|---|---|
| A  | 1.60 |  8.9 | 3.04 | 1.00 |  9.1 | 0.00 |
| A' | 7.40 | 41.1 | 6.33 | 1.20 | 10.9 | 7.61 |
| B  | 8.20 | 45.6 | 9.13 | 0.80 |  7.3 | 4.07 |
| C  | 13.20 | 73.3 | 7.24 | 8.00 | 72.7 | 0.00 |

## Decomposition

| Transition | Δ WK (pp) | Δ JS (pp) | Replicated direction? |
|---|---|---|---|
| A → A' | +32.2 |  +1.8 | Direction same, magnitude diverges (app-shape effect) |
| A' → B |  +4.4 |  −3.6 | Yes (null on both, sign flip) |
| B → C  | +27.8 | +65.5 | Yes |
| A → C  | +64.4 | +63.6 | Yes (robust within 1 pp) |

## Wrong way to analyze (do NOT do this)

Naive t-test on run-level detection counts:
```python
# WRONG — assumes within-run vulns are independent
t_test(A_counts, B_counts)
```

Why wrong: a run that misses V5 (or JS-06) due to compositional difficulty is also more likely to miss V8 and V10 (compositional limits affect the whole run). Within-run observations are correlated. A t-test ignoring this overstates degrees of freedom and produces tighter-than-true confidence intervals.

## Correct way: mixed-effects logistic regression (two-app model)

Model each binary detection outcome as a function of:
- Fixed effects: prompt condition (A, A', B, C), app (WarungKu, JuiceShop), and their interaction
- Random effect: run (intercept) — captures run-level variation
- Random effect: vuln (intercept), crossed with app — captures per-vuln intrinsic difficulty

Specification in R `lme4`:
```r
library(lme4)
library(lmerTest)
library(broom.mixed)

# Long-format combined data: 660 rows
# columns: run_id, condition, vuln_id, detected, app
df <- read.csv("scoring_long_combined.csv")
df$condition <- factor(df$condition, levels = c("A", "Aprime", "B", "C"))
df$app       <- factor(df$app, levels = c("WarungKu", "JuiceShop"))

# Primary model: condition × app interaction
model_full <- glmer(
  detected ~ condition * app + (1 | run_id) + (1 | vuln_id),
  data = df,
  family = binomial(link = "logit"),
  control = glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 1e5))
)
summary(model_full)
confint(model_full, method = "Wald")

# Compare to no-interaction reduced model
model_reduced <- glmer(
  detected ~ condition + app + (1 | run_id) + (1 | vuln_id),
  data = df,
  family = binomial(link = "logit"),
  control = glmerControl(optimizer = "bobyqa")
)
anova(model_reduced, model_full)
```

A significant interaction term tests whether the prompt effect *differs* between apps. With our observed Δ-of-Δs (e.g., A→A': +32.2 WK vs +1.8 JS = ~30 pp difference; B→C: +27.8 WK vs +65.5 JS = ~38 pp difference), we expect the condition×app interaction to be highly significant.

Python equivalent (when R not available):
```python
import pandas as pd
import statsmodels.formula.api as smf
df = pd.read_csv("scoring_long_combined.csv")
# pymer4 wraps lme4 if available; otherwise Bayesian via bambi/pymc.
# statsmodels.MixedLM does not natively do binomial logistic mixed models.
```

R is the path of least resistance. The `analysis.R` script (deliverable below) implements this.

## Pre-registered hypotheses (extended for two apps)

H1: μ(A') > μ(A) — adding BLV scope and taxonomy improves detection (tested per-app and pooled)
H2: μ(B) > μ(A') — adding systematic methodology improves detection beyond scope+taxonomy
H3: μ(C) > μ(B) — adding business workflow invariants improves detection beyond methodology
H4 (new): the prompt effect (A→C) generalizes across apps — formally, the condition main effect remains significant after adding app and the condition×app interaction terms.
H5 (new): the methodology effect (A'→B) is null on both apps individually (one-sided test against zero).

Each tested with one-sided z-test on the fixed-effect coefficient from the mixed model, α = 0.05 each. With five planned comparisons, apply Bonferroni: α_adj = 0.05/5 = 0.01 — or report uncorrected with explicit note that comparisons are pre-registered.

## Power analysis

### Within-app

Observed effects (recomputed from final dataset, JS n=11):
- WK: A→A' +32.2 pp; A'→B +4.4 pp; B→C +27.8 pp
- JS: A→A'  +1.8 pp; A'→B −3.6 pp; B→C +65.5 pp

For each pairwise comparison, Cohen's d on the run-level proportion:

**WarungKu (within-condition SDs in proportion units: A=0.030, A'=0.063, B=0.091, C=0.072):**
- A vs A': d = 0.322 / 0.052 ≈ 6.2 → power > 99% at n=5
- A' vs B: d = 0.044 / 0.082 ≈ 0.54 → power ~ 26% at n=5 (UNDERPOWERED)
- B vs C: d = 0.278 / 0.082 ≈ 3.4 → power > 99% at n=5

**Juice Shop (within-condition SDs: A=0.000, A'=0.076, B=0.041, C=0.000):**
- A vs A': d = 0.018 / 0.054 ≈ 0.33 → power ~ 8% at n=5 — but **the effect itself is tiny (≈ null)**, not a power issue. Cohen's h = 2(arcsin√0.109 − arcsin√0.091) ≈ 0.062 → negligible.
- A' vs B: d = 0.036 / 0.061 ≈ 0.59 → power ~ 18% at n=5 (UNDERPOWERED; negative direction)
- B vs C: d = 0.655 / 0.029 ≈ 22.6 → power > 99.99% (JS C SD is 0; pooled SD dominated by B)

**Critical findings:**
1. The A→A' comparison on JS is *not* underpowered in the conventional sense — the observed effect is +1.8 pp, well within the within-condition noise floor (~5 pp pooled). The JS taxonomy effect is effectively null at the run level. This is a positive finding for the "JS is invariant-shaped" claim.
2. The A'→B comparison is underpowered on both apps. The fact that the *direction* of Δ differs across apps (+4.4 WK, −3.6 JS) is strong qualitative evidence that the true effect is approximately zero, not that we are missing a real positive effect.

To detect a 4pp methodology effect with power 0.8 at α=0.05 would need n ≈ 25 runs per arm per app. Two responses:

1. **Honest framing:** "A'→B effect is small (~0–5pp) and statistically indistinguishable from zero at our sample size; methodology instruction may contribute marginally but our experiment cannot confirm this with confidence."
2. **Add runs** (10 more per arm per app, total 20 more agent-hours) to bring power above 0.7. **Recommendation: option 1 in writing; option 2 only if time permits.**

### Cross-app (interaction term)

For the condition × app interaction test, the relevant effect is the *difference of differences*:
- A→A' WK − A→A' JS = +30.4 pp (very large — clear app-shape divergence)
- B→C WK − B→C JS = −37.7 pp (very large — invariant-density divergence)
- A→C WK − A→C JS = +0.8 pp (near zero — supports robustness of total effect)

Both A→A' and B→C interactions are large enough (~30+ pp magnitude vs pooled SD ~8 pp) that the condition×app interaction is expected to be highly significant in the mixed model. Adequate power.

## Confidence intervals on per-condition means

Using Wilson score interval for proportions (naive — assumes independence):
```python
from statsmodels.stats.proportion import proportion_confint

# WK A: 8/90 → Wilson 95% CI
proportion_confint(count=8, nobs=90, method='wilson')   # → ~(0.04, 0.17)
# JS A: 5/55
proportion_confint(count=5, nobs=55, method='wilson')   # → ~(0.04, 0.20)
# WK C: 66/90
proportion_confint(count=66, nobs=90, method='wilson')  # → ~(0.64, 0.81)
# JS C: 40/55
proportion_confint(count=40, nobs=55, method='wilson')  # → ~(0.61, 0.83)
```

True CIs are wider due to clustering. Use cluster-robust SEs from the mixed model output for headline CIs. Wilson CIs only as quick sanity check.

## Effect-size reporting

For thesis, report effects in three forms per app:

1. **Absolute:** percentage points (table above)
2. **Relative:** multipliers — e.g., WK A→A' 8.9% → 41.1% = 4.6×; JS B→C 20% → 76% = 3.8×
3. **Cohen's h** for proportions: h = 2(arcsin√p₁ − arcsin√p₂)

| Transition | WK h | JS h |
|---|---|---|
| A → A' | 0.78 (large) | 0.06 (negligible) |
| A' → B | 0.09 (negligible) | −0.12 (negligible) |
| B → C | 0.59 (large) | 1.43 (very large) |
| A → C | 1.48 (very large) | 1.48 (very large) |

## Multi-app cross-tabulation analyses

In addition to the mixed model, report:

1. **Spearman correlation between per-vuln rates across apps (mapped via JS↔V cross-reference in JUICESHOP_GROUND_TRUTH.md).** Tests whether vulns of the same *type* are similarly detectable across implementations.
2. **Tier-level breakdown** (Tier 1 ≥4/5 at C, Tier 2 = 2–3/5, Tier 3 ≤1/5) — combine across apps to identify the ceiling cohort.
3. **JS-08 paradox visualization** — single-vuln tracked across conditions to demonstrate prompt-induced blindspot. Already in `per_vuln_heatmap.png`.

## Deliverables

1. `scoring_long_warungku.csv` — WK only (360 rows)
2. `scoring_long_juiceshop.csv` — Juice Shop only (220 rows, n=11 official challenges)
3. `scoring_long_combined.csv` — both apps with `app` column (580 rows), **the canonical analysis input**
4. `SCORING_MATRIX_WARUNGKU.xlsx` — WK audit-ready (5 sheets)
5. `SCORING_MATRIX_JUICESHOP.xlsx` — JS audit-ready (5 sheets, n=11)
6. `analysis.R` — reproducible analysis script (already written; runs `glmer` on combined data)
7. `decomposition_chart.png` — headline two-panel figure (cross-app bars + decomposition)
8. `per_vuln_heatmap.png` — per-vuln × condition heatmap (both apps, side-by-side)
9. `regression_output.txt` — model summary (after running analysis.R)
10. `06_verification/verify_all.py` — Python validator confirming all 29 in-scope vulns exploitable

## Pitfalls to avoid

- Reporting percent without uncertainty: "C achieves 73.3% detection" — meaningless without CI.
- Discussing A→B vs A'→B as if they isolate the same factor — A' = scope+taxonomy bundle, so A'→B uses A' as baseline (correct), while A→B confounds taxonomy and methodology.
- Treating the original contaminated A4 as data — explicitly note exclusion in methods section.
- Claiming methodology has zero effect — A'→B is UNDERPOWERED, not null; honest framing required. (Note: cross-app sign flip strengthens the null *interpretation* but does not eliminate underpower.)
- Generalizing to "all LLMs" — single model tested (Claude Sonnet 4.6 via Claude Code); cross-model robustness is supplementary work.
- Claiming the cross-app difference in A→A' magnitude is an "effect" without controlling for the per-vuln difficulty differences between WK and JS. The mixed model's per-vuln random intercept absorbs this; the interaction term then tests the residual effect.
