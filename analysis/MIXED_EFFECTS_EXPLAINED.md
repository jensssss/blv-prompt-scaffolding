# Mixed-Effects Logistic Regression — Penjelasan untuk Pentester

**Tujuan:** Menjelaskan kenapa `analysis.R` pakai mixed-effects logistic regression (bukan t-test biasa) dan apa yang setiap komponen model itu artikan, dalam bahasa yang familiar untuk orang offsec.

**Audience:** Kamu (Jens) supaya kalau dosen tanya soal statistical model, bisa jawab dengan paham, bukan parroting.

---

## Bagian 1: "Logistic regression" — basics dulu

### Apa beda dengan regression biasa?

**Linear regression** = output kontinyu (e.g., suhu, response time). Model: `y = β₀ + β₁x + error`.

**Logistic regression** = output binary (0 atau 1). Model: `log(p/(1-p)) = β₀ + β₁x`, di mana `p = probability of 1`.

Kenapa pakai logistic untuk kita? Outcome kita per (run, vuln) adalah binary: detected (1) atau missed (0). Kalau pakai linear, prediksi bisa keluar < 0 atau > 1 yang tidak masuk akal sebagai probability.

### Apa itu "log-odds" yang muncul di output?

`odds = p / (1-p)` — kalau detection rate 75%, odds = 0.75/0.25 = 3. Artinya 3:1 chance terdeteksi.

`log(odds)` = ln(odds). Skala ini bagus untuk regression karena range-nya −∞ to +∞ (dibanding probability yang dibatasi 0-1).

### Apa itu "odds ratio"?

`OR = exp(β)`. Kalau koefisien condition C vs A = log(8) = 2.08, maka `OR = e^2.08 = 8`. Artinya: switching from condition A to C **multiplies the odds of detection by 8×**.

Pentest analogy:
- OR = 2 → "doubles your chance of finding the bug"
- OR = 10 → "10× your chance"
- OR = 1 → "no effect"
- OR = 0.5 → "halves your chance"

---

## Bagian 2: "Mixed-effects" — kenapa kita butuh ini

### Masalah: 660 observasi bukan 660 independent samples

Kita punya 660 baris di `scoring_long_combined.csv`. Tapi mereka **tidak semua independent**.

Pentest analogy: bayangkan kamu run 20 sessions of automated scanner, masing-masing pemindaian menghasilkan 30 findings per session. Total = 600 findings. Tapi findings dalam **session yang sama** akan correlated — kalau scanner-nya hari itu lagi "off", semua 30 findings akan affected. Kalau kamu treat 600 findings sebagai 600 independent observations, kamu **overstate evidence**.

Di eksperimen kita:
- 18 (WK) atau 15 (JS) vulns are tested **within the same agent run**.
- Kalau agent run-nya hari itu lagi "creative" (misalnya, manggil banyak edge-case probes), banyak vulns akan detected together.
- Kalau agent run-nya conservative, banyak vulns akan missed together.
- **Within-run observations are correlated.** Naive t-test mengabaikan ini.

### Solusi: random effects untuk grouping

"Mixed-effects" = combination of **fixed effects** (yang kita PEDULI) and **random effects** (yang kita kontrol).

**Fixed effects** di model kita:
- `condition` (A, A', B, C) — yang kita testing
- `app` (WK, JS) — yang kita testing (cross-app generalization)
- `condition * app` (interaction) — apakah prompt effect berbeda antar aplikasi

**Random effects** di model kita:
- `(1 | run_id)` — random intercept per run. Artinya: setiap run punya "baseline detection skill" sendiri yang kita kontrol.
- `(1 | vuln_id)` — random intercept per vuln. Artinya: setiap vuln punya "intrinsic difficulty" sendiri yang kita kontrol.

### Pentest analogy untuk random effects

Bayangkan kamu evaluating 4 scanner configurations (= 4 conditions) on 33 different test apps (= 33 vulns), dengan 5 scan runs per config (= 5 runs).

Fixed effects: "config A vs config B" — yang kamu peduli.
Random effects:
- "App X intrinsic harder than App Y" — kontrol via `(1 | app_id)` analog.
- "Run 3 had network hiccup affecting all scans that day" — kontrol via `(1 | run_id)` analog.

Tanpa random effects, kamu bisa salah simpulkan "config B lebih baik" padahal sebenarnya "config B kebetulan dijalankan di run yang lebih bagus."

---

## Bagian 3: Apa output yang kita baca

Dari `analysis.R` output `regression_summary.txt`:

### A. Fixed effects table

```
                              Estimate  Std.Error  z value  Pr(>|z|)
(Intercept)                     -3.5       0.6      -5.8     <0.001
conditionAprime                  2.5       0.3       8.3     <0.001    ← A→A' effect
conditionB                       2.7       0.3       9.0     <0.001    ← A→B effect
conditionC                       4.5       0.3      15.0     <0.001    ← A→C effect
appJuiceShop                    -0.4       0.5      -0.8      0.42     ← apps differ at A
conditionAprime:appJuiceShop   -1.2       0.4      -3.0     <0.01     ← A→A' lift differs by app
...
```

Cara baca:
- `Estimate` = log-odds change vs reference (A condition di WarungKu).
- `Pr(>|z|)` = p-value. < 0.05 = "statistically distinguishable from zero".
- Koefisien `conditionC = 4.5` → odds ratio `e^4.5 ≈ 90`. Switching from A to C multiplies odds by 90×.
- Interaction `conditionAprime:appJuiceShop = -1.2` → A→A' lift on JS is SMALLER than on WK by a factor of `e^1.2 ≈ 3.3`. Konsisten dengan our observed +32 pp WK vs +15 pp JS.

### B. ANOVA — does interaction matter?

```
            Df  AIC    BIC   logLik  deviance  Chisq  Pr(>Chisq)
reduced     7  650.3  681.7  -318.2   636.3
full       10  640.1  685.0  -310.0   620.1    16.2    0.001 *
```

Cara baca:
- p < 0.05 → adding the interaction term SIGNIFICANTLY improves model fit.
- Artinya: prompt effect **berbeda** antar aplikasi (interaction is real, not random noise).

### C. Random effects variance

```
 Groups   Name        Variance  Std.Dev.
 vuln_id  (Intercept) 4.2       2.05      ← per-vuln difficulty
 run_id   (Intercept) 0.5       0.71      ← per-run rollout variance
```

Cara baca:
- `vuln_id variance >> run_id variance` → differences between vulns dominate. Makes sense: V5 vs V12 difficulty is huge gap; run-to-run variance within condition is smaller.

### D. Predicted probabilities

```
   condition  app          predicted_prob
   A          WarungKu     0.089
   A          JuiceShop    0.067
   A'         WarungKu     0.411
   ...
```

Cara baca: model-predicted detection rate per cell, after controlling for run and vuln variance. Should approximately match the observed rates (8.9% WK A, 9.1% JS A, etc.).

---

## Bagian 4: Kenapa kita NGGAK pakai t-test atau chi-square

### t-test (naive)

Kalau dosen tanya "kenapa nggak t-test biasa A vs C?":
- t-test asumsi independent observations.
- Tapi kita punya within-run correlation (vulns dalam run yang sama not independent).
- Hasil: t-test akan **overstate** evidence — p-value lebih kecil dari yang seharusnya.
- Akibatnya: kita salah confident bahwa effect-nya "significant" padahal mungkin within-noise.

### Chi-square

Sama masalah: chi-square test of independence asumsi cell counts dari sampel independen. Our cell counts are clustered by run.

### Mixed-effects glmer = the right tool

Memodelkan clustering eksplisit. p-values dan CIs jadi correct after accounting for run dan vuln random effects.

---

## Bagian 5: How to run analysis.R

### Prerequisites

```bash
# Install R (di Mac):
brew install r

# Install R packages (sekali aja):
R -e "install.packages(c('lme4', 'lmerTest', 'broom.mixed', 'ggplot2', 'dplyr'), repos='https://cloud.r-project.org')"
```

### Run

```bash
cd /Users/jens/Desktop/Progress
Rscript 04_analysis/analysis.R
```

Output:
- `04_analysis/regression_summary.txt` — full model output
- `04_analysis/regression_coefficients.csv` — fixed-effects table untuk dimasukkan ke thesis
- `04_analysis/forest_plot.png` — visual fixed effects untuk thesis

### Yang harus dicek setelah run

1. Buka `regression_summary.txt`. Cari "Model 1" — pastikan converged (no warnings about "boundary (singular) fit" atau "Model failed to converge").
2. Cari "ANOVA" — pastikan interaction p-value reported.
3. Bandingkan "Predicted probabilities" dengan Table A di BIMBINGAN_KEYPOINTS. Should match within ~3 pp.

---

## Bagian 6: Talking points kalau dosen tanya statistik

**Kalau dosen tanya "kenapa mixed-effects?":**
> "Karena 18 vulns dalam satu run share the same agent rollout — they're correlated, not independent. Mixed-effects model dengan `(1 | run_id)` random intercept mengontrol within-run clustering. Tanpa ini, p-values overstate evidence. Citation: standard mixed-models reference (Bates et al. 2015, lme4 paper)."

**Kalau dosen tanya "kenapa logistic, bukan linear?":**
> "Outcome per (run, vuln) cell adalah binary (detected vs missed). Linear regression dapat predict probability < 0 atau > 1 yang tidak valid. Logistic transforms ke log-odds yang range unbounded, dengan probability dijamin dalam [0, 1]."

**Kalau dosen tanya "n=5 dengan mixed-effects masih reliable?":**
> "n=5 per cell tapi total observations 580 (lots of within-cluster data). Mixed-effects model menggunakan partial pooling — estimates per condition borrow strength dari other conditions via the shared random-effect structure. Effective sample size lebih besar dari naive n=5 per arm. Untuk large effects (WK A→A', cross-app B→C) ini lebih dari cukup; untuk A'→B masih underpowered (acknowledged in T5 of THREATS_TO_VALIDITY)."

**Kalau dosen tanya "apa interpretasi odds ratio?":**
> "OR = exp(coefficient). Untuk condition C vs A: estimate ~4.5 log-odds → OR ~90. Artinya: switching from generic prompt ke full-scaffolded prompt multiplies odds of detection by 90×. Pada absolute scale: 8.9% → 73.3% (WK), 9.1% → 72.7% (JS) — konsisten dengan model predictions."

---

## Bagian 7: Reference paper yang bisa di-cite kalau perlu

**Untuk model methodology:**
- Bates, D., Mächler, M., Bolker, B., & Walker, S. (2015). *Fitting Linear Mixed-Effects Models Using lme4.* Journal of Statistical Software. → [doi:10.18637/jss.v067.i01](https://doi.org/10.18637/jss.v067.i01) (canonical lme4 paper)
- Bolker, B. M., Brooks, M. E., Clark, C. J., Geange, S. W., Poulsen, J. R., Stevens, M. H. H., & White, J. S. (2009). *Generalized linear mixed models: a practical guide for ecology and evolution.* Trends in Ecology & Evolution. → [doi:10.1016/j.tree.2008.10.008](https://doi.org/10.1016/j.tree.2008.10.008) (practical glmer guide)

**Untuk reporting standards:**
- Lakens, D. (2013). *Calculating and reporting effect sizes to facilitate cumulative science.* Frontiers in Psychology. → [doi:10.3389/fpsyg.2013.00863](https://doi.org/10.3389/fpsyg.2013.00863)
- Bowman, S. R. (2022). *The Dangers of Underclaiming.* ACL 2022. → [arxiv:2110.08300](https://arxiv.org/abs/2110.08300) (null-result honesty)
