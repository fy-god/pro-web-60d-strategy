# Audit Reports

Five independent audits were run against the source material. Each was produced
by a separate agent working from the raw artifacts, and each is cited in the
README. They are reproduced here so the negative results can be checked rather
than taken on trust.

| Report | What it establishes |
| --- | --- |
| [`STRATEGY_INVENTORY.md`](STRATEGY_INVENTORY.md) | Full roster of every strategy/model/rule-set in the source conversation: **71 distinct entries**, plus 26 definitional conflicts and the exact frozen spec. |
| [`NUMERIC_AUDIT.md`](NUMERIC_AUDIT.md) | Independent recomputation of ~60 reported ratios. Confirms **no arithmetic error** anywhere — and that no real evidence of predictive skill exists. |
| [`LOWZONE_EVIDENCE_AUDIT.md`](LOWZONE_EVIDENCE_AUDIT.md) | Dissects the V00–V08 evidence. **V08's claimed `PASS_YEARWISE_IN_SAMPLE` is unsupported as stated.** |
| [`ZIP_ARTIFACT_AUDIT.md`](ZIP_ARTIFACT_AUDIT.md) | Extracts and audits 11 previously-unexamined result archives, traces the generating code, and finds the single most serious methodology defect in the project. |
| [`OTHER_PROJECTS_AUDIT.md`](OTHER_PROJECTS_AUDIT.md) | Audits three sibling projects (`ly`, `a_share_intraday_lab`, the Web Pro export). **No validated strategy in any of them.** |

One audit is also **executable**, so its numbers can be reproduced rather than
read:

| Script | What it establishes |
| --- | --- |
| [`review_counterexamples.py`](review_counterexamples.py) | Reproduces U07–U12 from `docs/reviews/2026-09-17_ML_update_review.md` §13 against this repository's own source: the frontier bounds one ranking only, a prefix inside a score tie is not threshold-reachable, the date-only holdout split is label-blind, a global stride makes a stride>1 matrix panel-dependent, the 0.5pp tolerance classifies a 9.6% gap as open-at-limit, and a float32 entry can flip an exact-4x test. Writes `review_counterexamples.json`. |

Run it with `python audit/review_counterexamples.py`. It loads no panel, fits no
model and claims no hit rate; the U01–U06/U13–U14 label counterexamples live in
the private repository that owns that training code and are not copied here.

## The four findings that matter most

**1. The "70% success rate" is not a hit rate.**
`105/150 = 70%` is *winner-case coverage* over 150 post-hoc-selected annual
top-50 stocks, fitted in-sample per year. Four different denominators appear for
the same numerator — `105/150`, `105/156`, `105/164`, `105/131` — a 64%→80%
spread from denominator choice alone. Re-denominating over signals actually
emitted gives 64.02% or 67.31%; the honest unified retrain gives **85/150 =
56.7%**.

**2. The one frozen cross-year test failed its own pre-registered rule.**
`9/13 = 69.23%` required `N_signals >= 20`; N was 13, so the verification script
returns `FAILED / NOT ACCEPTED`. The 13 signals resolve to ~3.45 independent
market dates (HHI ≈ 0.290), 10 of them on a single day, and all 13 occur
*after* their matched anchor — so it measures bottom-confirmation, not early
warning. Against its own 50:50 pool, exact hypergeometric `P(X>=9) = 0.1168`.

**3. "0/50 loss false alerts" is vacuous, not impressive.**
The loss anchor is the eventual *trough*, but the code reuses the same
`abs(distance) <= 10` proximity test as for gain cases. Any signal on a stock
that later fell 50%+ fires *on the way down*, so it is structurally far from the
trough and can never register as a false alert. Verified exhaustively: **155
loss signals, distances −25 to −236 bars, zero counted as false** — while
70/150 loss cases did receive buy signals. 68–95% of the 28,880 searched
configurations also score zero, so the "gate" the search optimises is
near-constant.

**4. Honest out-of-sample results exist, and they are low.**
A frozen walk-forward 2026 test scores **10/80 = 12.5%**. An R01 logistic
lockbox scores **7/50 = 14.0%** with 48/50 loss false alerts. Two lockbox sweeps
pass **0 of 48 variants**. An oracle upper-bound analysis shows even a *perfect*
selector reaches only 36/29/27 — the target is unreachable by any threshold under
the stated loss constraint.

## Consistency with this repository's own backtest

These audits were produced independently of `src/backtest_lowzone.py`, and the
two agree:

| Claim | Independent audit | This repo's backtest |
| --- | --- | --- |
| V08 yearwise numbers | in-sample, 3 of 4 years fail the 60% gate when the window is made directional | V07/V08 in-sample hits (4.23%/4.08%) are compared against V03 (4.37%), but V03's 2024 block also picked its cutoff in-sample; on equal footing V03 is 2.87%, below the 3.089% base rate, while V07/V08 are 3.55%/3.72% |
| Honest low-zone ceiling | 12.5%–14.0% on frozen tests | 4.37% at the 10-session/+30% contract; 0.15% at the 60-session/4x contract |
| Loss-alert gate | semantically vacuous | not used as a success criterion here; strict-low is reported as a rate, never as a gate |

## Engineering results are not strategy results

The source material also reports many engineering achievements: 4,465 reachable
tickers, 1,500 trading days of public data, `364/364` SHA-256 verifications, 13
signals reproduced, a 40-symbol / 271,320-row synthetic smoke run, and test
counts of 14/14 or 21/21. **None of these carry information about predictive
power.** The same output stream reports `actual_market_stocks_trained = 0` and
`market_precision = null` from its first turn to its last.
