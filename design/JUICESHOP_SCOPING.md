# Juice Shop Ground Truth Scoping

## Why Juice Shop and not DVWA / PortSwigger

Choice driven by two requirements:

1. App must contain at least 12 documented state/flow-bypass BLVs to mirror WarungKu's vuln set
2. Vulnerability artifacts (writeups, walkthroughs) ideally NOT extensively reproduced in plain text that LLMs would have seen during pretraining — though for ANY public benchmark this is impossible to guarantee

DVWA (`dvwa.co.uk`) ruled out: 95% of its vulns are technical (SQLi, file inclusion, command injection) — only 2-3 BLVs at most. Insufficient for category comparison.

PortSwigger Web Security Academy ruled out: explicit pretraining contamination concern documented across multiple academic papers (Sainz et al. 2023; Carlini et al. 2023). The labs include verbatim solutions in the published "community solutions" pages, which appear in CommonCrawl snapshots known to be in major LLM training sets.

OWASP Juice Shop (`juice-shop.herokuapp.com`, source `github.com/juice-shop/juice-shop`) chosen because:
- 100+ challenges, including 15-20 documented business logic / flow bypass challenges
- Documented in `data/static/challenges.yml` in the repo — single canonical ground truth
- Known partial contamination (acknowledged limitation, see Threats to Validity)
- Standard reference target in AI pentesting literature (Cybench, MAPTA, ARTEMIS all benchmark on it)

## Juice Shop BLVs in scope

Selecting 15 challenges that map cleanly to WarungKu's planted vuln categories. Each maps to skip / replay / reorder / drop taxonomy.

**Revision v3 (2026-05-14):** All pure BLV. Sequential IDs JS-01 to JS-15.

| JS-ID | Challenge name | Category | Taxonomy | Maps to WarungKu vuln |
|---|---|---|---|---|
| JS-01 | Five-Star Feedback | Admin review skip | Skip | V4 (skip moderation) |
| JS-02 | Forged Coupon | Coupon forgery | Reorder | V18 (voucher tampering) |
| JS-03 | Forged Feedback | UserId spoofing | Skip | V12 (write to wrong state) |
| JS-04 | Forged Review | Author spoofing | Skip | V8 (skip auth check) |
| JS-05 | Manipulate Basket | Cross-user basket | Reorder | V15 (state tampering) |
| JS-06 | Multiple Likes | Counter replay | Replay | V6/V18 (replay on counter) |
| JS-07 | Payback Time | Negative quantity | Reorder | V18 (negative value exploit) |
| JS-08 | Confidential Document | Unauthenticated file access | Drop | V3 (auth gate dropped) |
| JS-09 | Empty User Registration | Password mismatch accepted | Drop | V2 (required state dropped) |
| JS-10 | Repetitive Registration | Mass registration bypass | Replay | V14 (replay flag-reset) |
| JS-11 | Admin Registration | Role injection at signup | Drop | V9 (role escalation) |
| JS-12 | Checkout Flow Skip | No payment required | Skip | V1 (skip payment step) |
| JS-13 | Captcha Replay | Captcha not invalidated | Replay | V6 (replay one-time token) |
| JS-14 | Basket Checkout Replay | Duplicate orders | Replay | V5 (replay order confirmation) |
| JS-15 | Coupon Reuse | Coupon never consumed | Replay | V18 (voucher replay) |

**Taxonomy distribution:** Skip=4, Reorder=3, Replay=5, Drop=3

**Caveat:** Juice Shop and WarungKu use different domain conventions. The "maps to" column shows STRUCTURAL analog only — they exercise the same taxonomy category, not literally the same code path.

## Ground truth document for Juice Shop

Build `JUICESHOP_GROUND_TRUTH.md` containing for each JS-ID:
- Challenge name (exact, from `challenges.yml`)
- Endpoint or UI flow targeted
- Specific bypass mechanism
- Curl/HTTP proof signature for scoring
- WarungKu analog (for cross-app comparison)

Store this file OUTSIDE the agent workspace. Critical lesson from A4 contamination.

## Experiment design on Juice Shop

Mirror the 4-arm scheme:
- A (control): generic pentest prompt, 5 runs
- A' (scope + JS-specific taxonomy): 5 runs
- B (scope + taxonomy + methodology): 5 runs
- C (scope + taxonomy + methodology + JS workflow invariants): 5 runs

Total: 20 runs. ~3-4 hours agent compute.

Prompt adaptation:
- A prompt unchanged (already domain-agnostic)
- A' prompt: replace `WarungKu` placeholder with `OWASP Juice Shop`, keep BLV scope + skip/replay/reorder/drop taxonomy
- B prompt: same swap, keep methodology section
- C prompt: rewrite the "business workflow invariants" section using Juice Shop's documented workflows (registration, login, basket, checkout, complaints, feedback, etc.) sourced from Juice Shop's own documentation site `pwning.owasp-juice.shop`

## Expected results pattern

If WarungKu findings generalize:
- A < A' < B < C ordering preserved
- Magnitude approximately reproduces (within ~10pp on each effect)
- Per-vuln rates correlated with WarungKu equivalents (Spearman ρ > 0.5)

If pattern does NOT reproduce, two interpretations:
- Negative result: prompt-engineering effect is WarungKu-specific (worth reporting honestly)
- Contamination signal: detection rates uniformly elevated → training data contains JS solutions → confirms motivation for custom apps

Either way, the result is publishable. Negative findings on Juice Shop strengthen the WarungKu-only methodology argument.

## Estimated time budget

| Task | Time |
|---|---|
| Local Juice Shop install + verify endpoints | 2 hours |
| Build JS ground truth document | 4 hours |
| Adapt 4 prompts for JS | 2 hours |
| Run all 20 agent sessions (parallel possible) | 1-3 days wall clock |
| Score 20 × 15 = 300 binary observations | 1 day |
| Cross-app statistical analysis | 1 day |

Total: ~7-10 days from start to having Juice Shop results ready for analysis.

## Files needed (not in current context)

To execute this plan in a new chat session, upload to that session:
1. `JUICESHOP_GROUND_TRUTH.md` — once authored (does not exist yet)
2. Juice Shop's `data/static/challenges.yml` — pull from the GitHub repo
3. Juice Shop's `pwning.owasp-juice.shop` doc dump for the 15 selected challenges
