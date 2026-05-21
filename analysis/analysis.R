# =============================================================================
# Mixed-Effects Logistic Regression — Cross-App BLV Detection
# =============================================================================
# Input: ../03_scoring/scoring_long_combined.csv (660 rows = 18 WK + 15 JS vulns
#        × 5 runs × 4 conditions × 2 apps)
#
# Models fit:
#   Model 1 (primary):  detected ~ condition * app + (1 | run_id) + (1 | vuln_id)
#   Model 2 (reduced):  detected ~ condition + app + (1 | run_id) + (1 | vuln_id)
#   ANOVA tests whether condition × app interaction is significant.
#
# Outputs (written to ../04_analysis/):
#   regression_summary.txt    — full model summary
#   regression_coefficients.csv — fixed-effect estimates + CIs
#   forest_plot.png            — visual of pairwise effects
# =============================================================================
#
# To run:
#   Rscript 04_analysis/analysis.R
#
# Required R packages (install if missing):
#   install.packages(c("lme4", "lmerTest", "broom.mixed", "ggplot2", "dplyr"))
# =============================================================================

# ---- Setup ----
library(lme4)
library(lmerTest)
library(broom.mixed)
library(ggplot2)
library(dplyr)

# Resolve paths relative to script location
script_dir <- dirname(sys.frame(1)$ofile %||% rstudioapi::getActiveDocumentContext()$path %||% getwd())
if (basename(script_dir) == "04_analysis") {
  project_root <- dirname(script_dir)
} else if (basename(script_dir) == "Progress") {
  project_root <- script_dir
} else {
  # fallback: assume CWD is project root
  project_root <- getwd()
}
scoring_csv <- file.path(project_root, "03_scoring", "scoring_long_combined.csv")
out_dir     <- file.path(project_root, "04_analysis")

cat("Reading:", scoring_csv, "\n")
df <- read.csv(scoring_csv)
cat("Loaded", nrow(df), "rows. Columns:", paste(names(df), collapse=", "), "\n\n")

# ---- Factorize and set reference levels ----
df$condition <- factor(df$condition, levels = c("A", "Aprime", "B", "C"))
df$app       <- factor(df$app, levels = c("WarungKu", "JuiceShop"))
df$run_id    <- factor(df$run_id)
df$vuln_id   <- factor(df$vuln_id)

cat("Sample sizes per condition × app:\n")
print(with(df, table(condition, app)))
cat("\n")

# ---- Sanity: overall detection rate ----
cat("Overall detection rate by condition × app (mean of 0/1):\n")
df %>%
  group_by(condition, app) %>%
  summarise(rate = mean(detected), n_obs = n(), .groups = "drop") %>%
  print()
cat("\n")

# =============================================================================
# Model 1 — Primary: condition × app interaction
# =============================================================================
cat("=== MODEL 1: detected ~ condition * app + (1|run_id) + (1|vuln_id) ===\n\n")

model_full <- glmer(
  detected ~ condition * app + (1 | run_id) + (1 | vuln_id),
  data    = df,
  family  = binomial(link = "logit"),
  control = glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 1e5))
)

summary_full <- summary(model_full)
print(summary_full)
cat("\n")

cat("Wald 95% CIs (fast):\n")
ci_wald <- confint(model_full, method = "Wald")
print(round(ci_wald, 3))
cat("\n")

# =============================================================================
# Model 2 — Reduced: no interaction
# =============================================================================
cat("=== MODEL 2: detected ~ condition + app + (1|run_id) + (1|vuln_id) ===\n\n")

model_reduced <- glmer(
  detected ~ condition + app + (1 | run_id) + (1 | vuln_id),
  data    = df,
  family  = binomial(link = "logit"),
  control = glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 1e5))
)

# =============================================================================
# ANOVA — test whether interaction term is significant
# =============================================================================
cat("=== ANOVA: condition × app interaction significance ===\n")
anova_test <- anova(model_reduced, model_full)
print(anova_test)
cat("\n")
cat("Interpretation: if p < 0.05, the prompt effect DIFFERS between apps\n")
cat("(supports our observed app-dependent decomposition pattern).\n\n")

# =============================================================================
# Tidy fixed effects with CIs
# =============================================================================
tidy_effects <- broom.mixed::tidy(model_full, effects = "fixed", conf.int = TRUE,
                                   conf.method = "Wald")
cat("=== FIXED EFFECTS (with 95% Wald CIs) ===\n\n")
print(tidy_effects)
cat("\n")

# Save coefficients table
coef_out <- file.path(out_dir, "regression_coefficients.csv")
write.csv(tidy_effects, coef_out, row.names = FALSE)
cat("Saved fixed-effects table →", coef_out, "\n")

# =============================================================================
# Compute per-condition predicted probabilities (averaged over vulns)
# =============================================================================
cat("\n=== PREDICTED DETECTION RATE per (condition, app) — averaged over vulns ===\n")

# Build a grid: each condition × app, random effects integrated out
newdat <- expand.grid(
  condition = levels(df$condition),
  app       = levels(df$app)
)
newdat$run_id  <- NA  # marginal over runs
newdat$vuln_id <- NA  # marginal over vulns
newdat$predicted_logodds <- predict(model_full, newdata = newdat, re.form = NA,
                                      type = "link")
newdat$predicted_prob <- plogis(newdat$predicted_logodds)
print(newdat)
cat("\n")

# =============================================================================
# Pairwise effect comparisons via the fixed-effects table
# =============================================================================
cat("=== PAIRWISE EFFECTS ON THE LOG-ODDS SCALE ===\n")
cat("(Exponentiated = odds ratios. e.g., OR=4 means condition multiplies\n")
cat(" the odds of detection by 4.)\n\n")

# Extract main effect of condition (collapsed over apps via the full model)
# In the full model, condition coefficients are 'condition vs A within WarungKu'
# because WarungKu is the reference level for app.
# To get the cross-app pooled effect, use the reduced model (no interaction).
tidy_reduced <- broom.mixed::tidy(model_reduced, effects = "fixed", conf.int = TRUE,
                                    conf.method = "Wald")
cat("Reduced model (pooled across apps):\n")
print(tidy_reduced)
cat("\n")

# =============================================================================
# Random effect variance — how much variability is run-level vs vuln-level?
# =============================================================================
cat("=== RANDOM EFFECTS variance components ===\n")
re_var <- as.data.frame(VarCorr(model_full))[, c("grp", "var1", "vcov", "sdcor")]
print(re_var)
cat("\n")
cat("Interpretation:\n")
cat("  vuln_id variance = how much vulns differ in intrinsic difficulty\n")
cat("  run_id  variance = how much agent rollouts differ within a condition\n")
cat("  If vuln_id >> run_id: differences between vulns dominate; between-run\n")
cat("    variance is secondary. (Expected for our setup.)\n\n")

# =============================================================================
# Forest plot of condition effects (vs A baseline) per app
# =============================================================================
cat("Building forest plot...\n")

# Get coefficients for visualization (full model, app-stratified)
effects_df <- broom.mixed::tidy(model_full, effects = "fixed", conf.int = TRUE,
                                  conf.method = "Wald") %>%
  filter(term != "(Intercept)") %>%
  mutate(
    term_label = case_when(
      term == "conditionAprime"             ~ "A → A' (WarungKu, ref)",
      term == "conditionB"                  ~ "A → B  (WarungKu, ref)",
      term == "conditionC"                  ~ "A → C  (WarungKu, ref)",
      term == "appJuiceShop"                ~ "App: JuiceShop vs WarungKu (at A)",
      term == "conditionAprime:appJuiceShop" ~ "A → A' interaction (JS vs WK delta)",
      term == "conditionB:appJuiceShop"     ~ "A → B  interaction (JS vs WK delta)",
      term == "conditionC:appJuiceShop"     ~ "A → C  interaction (JS vs WK delta)",
      TRUE                                  ~ term
    ),
    odds_ratio = exp(estimate),
    or_low     = exp(conf.low),
    or_high    = exp(conf.high)
  )

p_forest <- ggplot(effects_df, aes(x = odds_ratio, y = reorder(term_label, odds_ratio))) +
  geom_vline(xintercept = 1, linetype = "dashed", color = "grey50") +
  geom_errorbarh(aes(xmin = or_low, xmax = or_high), height = 0.2, color = "#3a6ea5") +
  geom_point(size = 3, color = "#1c4978") +
  scale_x_log10(breaks = c(0.1, 0.3, 1, 3, 10, 30, 100, 300)) +
  labs(
    title    = "Fixed-effects forest plot — Cross-app BLV detection model",
    subtitle = "Odds ratios with 95% Wald CIs. OR=1 (dashed) = no effect. Log scale.",
    x        = "Odds ratio (log scale)",
    y        = NULL
  ) +
  theme_minimal(base_size = 11) +
  theme(plot.title = element_text(face = "bold"))

forest_out <- file.path(out_dir, "forest_plot.png")
ggsave(forest_out, p_forest, width = 9, height = 5, dpi = 160)
cat("Saved forest plot →", forest_out, "\n")

# =============================================================================
# Save full text summary to file
# =============================================================================
sink(file.path(out_dir, "regression_summary.txt"))
cat("MIXED-EFFECTS LOGISTIC REGRESSION RESULTS\n")
cat("Generated:", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "\n")
cat(paste(rep("=", 78), collapse=""), "\n\n")
cat("MODEL 1 (primary): condition × app interaction\n\n")
print(summary_full)
cat("\n\n")
cat("Wald 95% CIs:\n")
print(round(ci_wald, 3))
cat("\n\n")
cat("MODEL COMPARISON via likelihood-ratio test:\n")
print(anova_test)
cat("\n\n")
cat("REDUCED MODEL (no interaction):\n\n")
print(summary(model_reduced))
cat("\n\n")
cat("PREDICTED PROBABILITIES per condition × app (marginal over random effects):\n\n")
print(newdat)
cat("\n\n")
cat("RANDOM EFFECTS variance components:\n\n")
print(re_var)
sink()

cat("\nSaved full summary →", file.path(out_dir, "regression_summary.txt"), "\n")
cat("\nDone. Three artifacts written to", out_dir, ":\n")
cat("  regression_summary.txt    — full model output (read this first)\n")
cat("  regression_coefficients.csv — fixed-effect estimates for the thesis\n")
cat("  forest_plot.png            — figure for the thesis\n")
