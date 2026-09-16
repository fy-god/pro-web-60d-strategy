# NUMERIC AUDIT — Chinese A-share KDJ "big bull stock low-zone signal" conversation

**Audited inputs**
- `D:\ccc\KDJ对话_完整版_合并.md` (16,481 lines; assistant research replies are the `## [00NN] 助手 → all` blocks; the export itself states 88 complete research replies at line 16472)
- `D:\ccc\KDJ对话_结构化消息.json` (291 messages: 124 user / 139 assistant / 22 tool / 6 system)

**Method.** Every number below was located with `grep` and read with ≥20 lines of surrounding context before judging. Every interval was computed by running Python (`D:\ccc\audit_intervals.py`, `D:\ccc\audit_intervals2.py`) using `scipy.stats.beta.ppf` (Clopper–Pearson exact) and the Wilson score interval with z = 1.959963984540054. No interval is estimated by hand. Arithmetic the transcript asserts was recomputed term by term.

**Headline finding.** The conversation's own arithmetic is essentially faultless. Of the 60-odd ratios and derived quantities re-computed here, every one reproduces to the stated precision — including both HHI values, every Wilson bound quoted, the PPV conversion table, the log-lift figures, and the incompatibility probabilities. The problem is **not** arithmetic. The problem is that a small number of numerators are repeatedly divided by denominators that count a *different population*, and that a handful of ratios are quoted far from the paragraph that states their true denominator. Section 1 tabulates that; Section 2 dissects the "70%" chain; Section 3 quantifies the noise floor.

---

## 1. Headline-number table

| Number as stated | Line # in .md | What it is claimed to measure | What the denominator ACTUALLY counts | Independent events behind it | Valid as evidence for the attached claim? |
|---|---|---|---|---|---|
| `105/150 = 70%` | 3373, 3650, 3834, 10315, 10344, 10638, 10771, 15144 | "原年度赢家锚点覆盖" — winner low-point coverage | 150 post-hoc-selected annual Top-50 winners × 3 years; numerator = winners whose chart-window contains a signal within ±10 bars of the *ex-post* low anchor | **0 out-of-sample events.** Same-year in-sample fits, three separately-fitted rule sets | **No.** Correctly downgraded by the assistant at 3373 and 10771 to "同年度样本内拟合", not OOS precision |
| `105/156 ≈ 67.31%` | 3377, 3657, 3835, 10655, 10773 | "原选样内去重信号锚点Precision" — signal precision | **156 de-duplicated signal ROWS (year+stock+signal-date) over all 300 cases**, not 150 winner cases | Same 105 winner hits; ~0 out-of-sample | **No.** Numerator population (winner cases, ≤150) ≠ denominator population (signal rows, ≤164) — see §1.2 |
| `105/164 = 64.02%` | 10772 | "原年度所有案例级信号锚点命中" | 164 signal-bearing case rows, undeduplicated | same 105 | **No.** Third denominator for the same 105 numerator in the same conversation |
| `52.67%` | 4879–4881 (context 4862–4892) | "signal at or before the ex-post low" coverage | (61+18)/150 — winner cases | 150 post-hoc winner cases, clustered (44/50 of 2025 winners share 3 anchor dates, line 3710–3716) | **Partially — as a sensitivity check only.** It is a re-cut of the same in-sample 150, not new evidence |
| `40.67%` | 4887–4889 (context 4862–4892) | "strictly before the low" coverage | 61/150 — winner cases | as above | **Partially**, same caveat |
| `9/13 = 69.23%` | first at 3381; 3640, 3837, 5525, 5790, 6139, 10139, 10716, 10939, 13128, 13360, 15267, 16095 | "2025冻结图窗锚点命中" — signal precision | **13 signals only**; signals→6 dates; 11 of 13 in April 2025; 10/13 share the single anchor date 2025-04-09 | ≈3.45 HHI-effective dates (line 15967); 1 dominant market day; all 9 hits occur *after* the low (line 10925) | **No** for any claim about future 4× performance. Genuinely a frozen cross-year window task; the assistant says so at 10146, 10168, 10347 |
| `9/50 = 18%` | 3381, 3640, 3838, 5526, 5791, 5845, 10142, 10348, 13069, 14960 | "赢家案例覆盖 / Recall" | 50 ex-post annual Top-50 winners in the 2025 window set | Same 13 signals / same single market episode | Valid *as a recall on a hand-picked pool*, and correctly labelled "Recall_selected_winners" at 10722 |
| `4/50 = 8%` | 3381, 3839, 5527, 10382, 16083 | P(Signal ∣ Loser) | 50 ex-post annual Bottom-50 losers | Same window set | Valid only as a same-pool contrast — see §1.4 |
| `2.25×` lift | 16089, 16161 | 18%/8% discrimination ratio | 100 hand-picked extreme cases | ≈4 date clusters | **No.** Fisher exact two-sided p = 0.2336; one-sided p = 0.1168; risk-ratio 95% CI [0.74, 6.83] — computed, §3.6. The transcript itself disclaims it at 16118 |
| `10/59 = 16.95%` (KDJ-only) | 3389, 5849, 10352, 10991, 13041, 13128, 13539, 14932 | KDJ Logistic anchor precision | 59 KDJ signals inside the same 6-date cluster set | ≈6 dates | Valid as an *ablation*; the always-signal control on the same windows is 47/286 = 16.43% (13041), ratio 1.03× (13046) |
| `50.00%–72.73%` (±0.5-pixel perturbation) | 3383, 3807, 5851, 10354, 10460, 10743, 10777, 11004, 13170, 15633, 15770 | "10次复算的锚点Precision" | 10 perturbed re-runs, **7–11 signals each** | ≤ the same few date clusters | Valid **only** as a fragility demonstration. Correctly used that way (10354: "绝不能把69.23%四舍五入成'已经做到70%'") |
| `57.14% ↔ 80.0%` (leave-one-day-cluster-out) | 10998–11002, 15972–15984 | sensitivity of 69.23% to one date cluster | (9−5)/(13−6) and (9−1)/(13−3) | 13 signals over 6 dates | Valid as a fragility demonstration; explicitly called "不是新策略收益结果" at 15984 |
| `HHI = 0.290`, `1/HHI ≈ 3.45` | 4258, 15960–15970 | signal clustering by date | 13 signals over 6 dates, `[1,3,6,1,1,1]` | ≈3.45 equal-weight date clusters | **Valid and important.** Recomputed 0.289941 and 3.448980 ✓ |
| `32/1993 = 1.606%` | 5210, 15179 (also "1.61%" at 2418) | natural 4× base rate, 252-day cohort | 1993 tradable proxy observation points, 40 convenience-sample A-shares | **Unknown; the transcript states 32 positive windows are not 32 events** (15569). Earliest positive windows came from one ticker | Valid as a base rate *for those 40 stocks only* — stated at 2673 |
| `1/110 = 0.91%` (KDJ Logistic) | 2422, 5215, 9203, 10486, 12266, 15186 | out-of-sample signal precision | 110 de-duplicated signals | **1 true positive** | **Statistically empty.** Wilson 95% [0.16%, 4.97%] — see §3.7 |
| `1/25 = 4.00%` (full-feature Logistic) | 2423, 5216, 9204, 10487, 12267, 15187 | out-of-sample signal precision | 25 de-duplicated signals | **1 true positive** | **Statistically empty.** Wilson 95% [0.71%, 19.54%]; P(≥1 hit ∣ base rate) = 33.3% (15198) |
| `0/3` ExtraTrees, `0/3` HistGB | 2424–2425, 5217–5218, 10488–10489, 12268–12269, 15188–15189 | precision | 3 signals each | 0 true positives | **No information.** Wilson upper bound 56.15% — cannot distinguish 0% from a coin flip |
| `1362` obs / `8` positives / `0.587%` | 704, 2354, 2479, 2635, 15452, 15861 (`0.5874%`), 16060 | out-of-sample monthly US proxy base rate | 1,362 stock-month windows, 8 monthly price files | **2 independent bull events** (7 positives are AAPL adjacent months, 1 is AMZN) — established at 13921–13927 | Valid only as the 2-event diagnostic the assistant later calls it |
| `1342/1362` at `0.60%` precision | 721, 16253 | post-hoc threshold-0.01 sensitivity | 1,342 of 1,362 windows fire | Same 2 independent events | **No.** Precision 0.60% vs base rate 0.5874% = 1.022× lift, i.e. no information at all — see §3.9 |
| `252/504/756-day positives 0/32/93` | 2410, 2543, 5228–5230, 15561, 15565 | label counts by horizon on a 915-point cohort | 915 observation points (a *different* cohort from the 1993-point one — flagged at 2412 and 15561) | These are **label counts, not predictions**; stated at 2543 | Valid as label prevalence; explicitly "事后标签数而非预测准确率" |
| `624` low-zone points, `0/32/81` | 2433, 2435, 5232–5235, 15563, 15565 | low-zone subset label counts | 624 of 915 points (68.2%) | label counts only | Valid as label prevalence |
| `32/624 = 5.13%` vs `3.50%` | 2433, 5234, 15563 | low-zone 4× enrichment | 624 vs 915 points | label counts | Valid as a *label-level* enrichment (1.47×), stated as such |
| `12.98%` vs `10.16%` | 2435, 5235, 15565 | 756-day low-zone vs overall | 624 vs 915 | label counts | Valid as label prevalence; correctly warned against horizon-shopping at 5237 |
| `78/100 → 68.93%` and `79/100 = 79%` | 15670–15689 | Wilson lower-bound boundary at the framework's minimum n=100 | 100 signals | hypothetical | **Arithmetically exact.** Recomputed: 78/100 lower = 68.9296%, 79/100 lower = 70.0200% ✓ |
| median threshold margin `0.01294` | 15614 (min `0.00117` at 15610) | distance of the 13 frozen signals from the 0.825 threshold | 13 signal scores | 13 (≤6 dates) | Valid as a fragility diagnostic only; the assistant says the score is not a calibrated probability (15605) |
| within-signal AUC `0.472` | 14365, 14397, 15766 | can the score rank hits above misses inside the 13 signals | 9 hits vs 4 misses = 36 rank pairs | 13 | **No.** Exact P(AUC ≤ 0.472 under null) = 0.4126 — see §3.11 |
| cooldown bug: `100%` (Wilson `93.98%`) vs `60/540 = 11.11%` | 4043–4053 | policy-vs-production precision identity | 60 stress stocks, 540 production signals | synthetic | Valid **as a software defect proof**, explicitly "不是市场回测" (4063) |
| cooldown bug: `84%` (Wilson `71.49%`) vs `21%` | 4184–4198; variant `100%` (Wilson `92.87%`) vs `50/250 = 20%` at 12711–12736 | same defect, second construction | 50 stress stocks | synthetic | Valid as a software defect proof only |

### 1.1 `105/150 = 70%` — an in-sample anchor-coverage rate, not a precision

Line 3650: "**105 / 150 = 70%**"; line 3652 explains: "也就是三年150个事后选出的上涨Top案例中，有105个案例在赢家锚点±10根K线附近找到了信号". The denominator is *cases selected because they went up*, and the numerator asks whether the model's chart contains a mark near the low that was identified *after* the year closed. Line 3373 is the decisive self-correction: "105/150＝70%来自2023、2024、2025三套分别在各自年份拟合的规则组合，仍属于'**同年度样本内拟合**'；统一重新训练版本只有85/150＝56.7%." That 85/150 = 56.67% figure (computed: 56.6667%, Wilson 95% [48.67%, 64.33%]) is the same task run honestly and it does not reach 70%. Any claim of a 70% *hit rate* attached to 105/150 is unsupported by its own denominator.

### 1.2 `105/156 ≈ 67.31%` — the numerator and denominator count different populations

Line 3652: "原表共有164个带信号的案例行，按年份、股票代码、信号日期去重后是156条"; line 3657 then divides **the 105 winner hits** by **156 signal rows**. Those are not the same population. The transcript's own alternative row makes this explicit — line 10772 labels `105/164 = 64.02%` as "原年度**所有案例级**信号锚点命中", i.e. 164 counts case rows from *both* the winner and loser arms, whereas the 105 numerator counts only winner cases. Line 3379 states the loser contribution directly: "150个年度极端下跌案例中仍有**33个案例在其他位置发出了信号**" (repeated at 15144 and 10320). On that basis the coherent variants are:

```
105/164 (all case rows, undeduplicated — as printed at 10772)  = 64.02%
105/131 (winner case rows only, 164 − 33 losers)               = 80.15%
105/156 (as printed as "signal Precision")                     = 67.31%
105/150 (winner-case anchor coverage, original)                = 70.00%
```

Four different denominators for the same numerator appear across lines 3373, 3650, 3657, 3834, 3835, 10772, 10773 — a spread from 64.02% to 80.15%. `105/156` is therefore neither a precision nor a recall; it is a ratio between a case-level numerator and a mixed-case row-level denominator. The same substitution is made for the re-targeted goal: `84/156 ≈ 53.85%` at line 3377 versus `84/117 ≈ 71.8%` at line 3680 — a 17.9-point swing driven purely by denominator choice, on the same underlying events.

### 1.3 `52.67%` / `40.67%` — a re-cut of the same in-sample 150

Lines 4866–4890 split the 105 hits into 61 before / 18 on / 26 after the ex-post anchor, then compute (61+18)/150 and 61/150. The decomposition is legitimate and is the single most useful correction in the whole conversation, but both figures inherit the 150 in-sample winners. Line 4894 concedes it: "这套原评价只是判断信号与**事后选出的低点锚点距离≤10根K线**."

### 1.4 `9/50 = 18%` and `4/50 = 8%` — a 50:50 prior, on 4 effective clusters

Lines 16078–16104: P(Signal∣Winner) = 9/50, P(Signal∣Loser) = 4/50, ratio 2.25×, and `(0.18×0.5)/(0.18×0.5+0.08×0.5) = 69.23%` — the identity holds exactly (recomputed 69.2308%). The decisive point the assistant makes at 16106 is that 69.23% **is algebraically identical to** this 50:50 balanced-pool conversion, so it carries no information about the natural base rate. Recomputing the conversion table at 16110–16116 reproduces every cell: 10% → 20.00%, 5% → 10.588%, 3% → 6.506%, 1% → 2.222%, and the prior needed for PPV = 70% is 50.909%.

---

## 2. The "70%" claim, fully dissected

The user's stated target is "希望命中率>70%只是待验证目标" (e.g. line 16304). Five distinct quantities in this conversation have been called "70%" at one time or another, and they measure four different things.

**Chain, in order of appearance.**

1. **`105/150` — anchor coverage inside post-hoc annual winners (lines 3373, 3650, 3834, 10315, 10344, 10638, 10771, 15144).** Population: 300 hand-picked extreme cases (50 winners + 50 losers per year × 3 years). Selection: winners chosen *after* the year's ranking was known; the low anchor identified *after* the fact; the chart window drawn *around* that anchor (3387). Independent events: ~0 out-of-sample. Verdict: **(b) an anchor coverage rate on a post-hoc-selected pool.**

2. **`105/156`, `105/164` — the same 105 numerator over signal-row denominators (3377, 3657, 3835, 10655, 10772, 10773).** Population: signal-bearing case rows. Verdict: **(d) a mixed-population ratio** — neither precision nor recall.

3. **`84/117 ≈ 71.8%` — winner hits restricted to cases that really rose >300% (line 3680).** This is the closest thing in the chain to a conditional success statement, and it is still a coverage rate on post-hoc winners: "这些股票和上涨区间是**事后已经知道答案以后挑出来的**" (3680).

4. **`79/150 = 52.67%` and `61/150 = 40.67%` — anchor coverage restricted to signals at-or-before / strictly-before the low (4879–4889).** Verdict: **(c) a post-hoc-selected rate**, re-cut for honesty. This is the step that reveals 26 of the 105 "hits" fired *after* the low.

5. **`9/13 = 69.23%` — the frozen 2025 chart-window task (from 3381 onward, ~40 occurrences).** Population: 13 signals emitted by a rule frozen after 2024 development. Verdict: **(a) a signal precision — but for a different task.** Line 10146: "**现在确实存在一套跨年冻结后得到 9/13=69.23% 的实验，但它不是你的'未来4倍大牛股'标签实验。**" Line 10168 names it precisely: "**2025 年事后极端样本图窗上的低点锚点识别 Precision = 9/13。**"

**Is 70% a signal precision, an anchor coverage rate, a post-hoc rate, or something else?**

It is **(b) an anchor coverage rate on a post-hoc-selected, in-sample pool**, which was repeatedly mistaken for (a) a signal precision. The sentences that establish this:

> 原包自己的说明已经明确写明：105/150＝70%来自2023、2024、2025三套分别在各自年份拟合的规则组合，仍属于"**同年度样本内拟合**"；统一重新训练版本只有85/150＝56.7%。 — line 3373

> 原来的70%更接近**赢家案例覆盖率/锚点召回**，而不是实际发出信号后的条件成功率。 — line 3664

> 原年度70%的高成绩主要是评价口径和选样造成的，不是已经验证的未来>300%信号Precision … **你的70%目标仍未被真实验证。** — line 3393

> 原年度"70%" | **105/150赢家锚点覆盖，同年度拟合，不是OOS Precision** — line 10771 (table row)

> 所以当前的 **9/13=69.23%** 绝不能解释为"69%的大牛股低位被提前识别"。 — line 5834

**Every independent-event count feeding the 70% family, in one place:**

| Stage | Headline | Denominator as stated | Effective independent events |
|---|---|---|---|
| Original annual rules | 105/150 = 70% | 150 post-hoc winners | 3 same-year fits, 0 OOS; winners clustered — 44/50 of 2025 winners share 3 anchor dates (3710–3716) |
| Dedup by signal | 105/156 = 67.31% | 156 signal rows | mixed populations (§1.2) |
| Case-level | 105/164 = 64.02% | 164 case rows | mixed populations |
| >300% only | 84/117 = 71.8% | 117 truly-4× winners | post-hoc coverage |
| Timing-honest | 79/150 = 52.67% / 61/150 = 40.67% | 150 winners | post-hoc coverage, re-cut |
| Frozen 2025 window | 9/13 = 69.23% | 13 signals | **≈3.45 HHI-effective dates; 1 dominant market day (2025-04-09 → 10/13 signals, 7/9 hits) — lines 10730, 10736, 14865, 15967** |
| Same-pool contrast | 18% vs 8% | 50 + 50 hand-picked | Fisher p = 0.234 → **2.25× is not established** |
| 40-A-share 252-day OOS | 1/110 and 1/25 | 110 / 25 signals | **1 true positive each** |
| Monthly US proxy | 1362 obs / 8 pos | 1362 windows | **2 independent bull events** (13921) |

The chain therefore terminates, on real out-of-sample data, at **one** true positive. Whatever the 70% was, nothing in this conversation measures a 70% out-of-sample signal precision.

**The single decisive test.** Line 14882–14904 asks whether 9/13 beats the 50% random benchmark of its own balanced pool. Recomputed exactly (§3.15): hypergeometric `P(X≥9) = 0.1168`. It does not reach 5% significance. So even under the experiment's own most favourable assumptions — 50:50 prior, no pixel noise, no development-search penalty, no clustering adjustment — **the flagship number is not distinguishable from chance.**

---

## 3. Statistical fragility inventory

All intervals below were produced by running Python. The kernel is:

```python
from scipy.stats import beta
import math
def wilson(k, n, conf=0.95):
    z = 1.959963984540054
    p = k/n; d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (max(0.0, c-h), min(1.0, c+h))
def clopper(k, n, conf=0.95):        # exact Clopper-Pearson
    a = 1 - conf
    lo = 0.0 if k == 0 else beta.ppf(a/2, k, n-k+1)
    hi = 1.0 if k == n else beta.ppf(1-a/2, k+1, n-k)
    return (lo, hi)
```

### 3.1 `9/13 = 69.23%` — the flagship number (lines 3381, 3837, 6139, …)

```
9/13 = 69.2308%
Wilson 95%  [42.3693%, 87.3193%]   width 44.95 pp
exact  95%  [38.5738%, 90.9080%]   width 52.33 pp
```
The transcript quotes "约42.37%～87.32%" (10280, 13067, 14906) — **it matches the Wilson interval I compute exactly.** The lower bound is 27.6 points below the 70% target. Under an independent-Bernoulli reading, 13/13 = 100% would be required for the Wilson lower bound to reach 70% (§3.10). **Also note:** the exact interval is materially wider than the Wilson interval at this n, and the transcript only ever reports the Wilson one.

### 3.2 `9/13` collapsed to its real independent units (lines 4258, 14868, 15967)

```
4 effective date clusters, 4 hits   →  4/4  Wilson95 [51.0%, 100.0%]
6 signal DATES (generous upper bound) →  9/6  Wilson95 [61.0%, 100.0%]
```
At the conversation's own HHI-effective sample size of 3.45 dates, the interval spans essentially the whole unit range. The Wilson interval quoted for 9/13 is a **best case**, which the assistant states at 10741 and 14906.

### 3.3 `9/50 = 18%` (recall) and `4/50 = 8%` (loser rate)

```
9/50 = 18.0000%  Wilson95 [ 9.7702%, 30.7961%]  exact [ 8.5762%, 31.4369%]
4/50 =  8.0000%  Wilson95 [ 3.1550%, 18.8382%]  exact [ 2.2228%, 19.2343%]
```
Recall is bounded above by 30.8% at 95% confidence; it cannot exclude anything from ~10% to ~31%.

### 3.4 `10/59 = 16.95%` (KDJ-only) vs the always-signal control `47/286 = 16.43%` (lines 13041–13049)

```
10/59  = 16.9492%  Wilson95 [ 9.4758%, 28.4632%]
47/286 = 16.4336%  Wilson95 [12.5890%, 21.1679%]
ratio  = 1.0314×   absolute difference = 0.516 pp
```
The two intervals overlap almost entirely. The control's interval is *narrower* because n is 4.8× larger. The conversation's reading — KDJ-alone produces no lift over always-firing — is correct; its "1.03倍" is arithmetically exact.

### 3.5 Model-comparison ratios: `13/32`, `4/8`, `27/70`, `4/6`

```
13/32 = 40.6250%  Wilson95 [25.5196%, 57.7400%]  width 32.2 pp
 4/8  = 50.0000%  Wilson95 [21.5216%, 78.4784%]  width 57.0 pp
27/70 = 38.5714%  Wilson95 [28.0477%, 50.2843%]  width 22.2 pp
 4/6  = 66.6667%  Wilson95 [29.9993%, 90.3229%]  width 60.3 pp
```
Every one of these four is statistically indistinguishable from the others and from 50%: `4/8 = 50%` at line 3389 is quoted without any hint that its interval spans 21.5%–78.5%. `4/6 = 66.67%` (also line 3389) is quoted as a model result when its interval spans 30%–90%.

### 3.6 The `2.25×` lift (lines 16089, 16161)

```
contingency [[9,41],[4,46]]
Fisher exact, two-sided          p = 0.2336
Fisher exact, one-sided (W>L)    p = 0.1168
risk ratio = 2.25, log-RR 95% CI [0.74, 6.83]   ← includes 1.0
```
The point estimate is correct; the confidence interval on the ratio includes 1.0, and the two conditional rates' Wilson intervals (9.77–30.80% vs 3.15–18.84%) overlap. **The 2.25× is a point estimate with no established discrimination.** The transcript reaches the same conclusion by a different route (the PPV conversion), but never states the significance test.

### 3.7 The real out-of-sample results are the weakest numbers in the file

```
1/110 = 0.9091%  Wilson95 [0.1607%, 4.9706%]  exact [0.0230%, 4.9611%]
1/25  = 4.0000%  Wilson95 [0.7096%,19.5441%]  exact [0.1012%,20.3517%]
0/3   = 0.0000%  Wilson95 [0.0000%,56.1497%]  exact [0.0000%,70.7598%]   (×2 models)
```
Both `1/110` and `1/25` rest on **a single true positive**. `0/3` cannot distinguish 0% from 56%. The transcript's quoted bounds (15186–15189: 0.16%–4.97%, 0.71%–19.54%, 0–56.15%) **match my computations exactly**. Its incompatibility test (15203) also reproduces:

```
P(≤1 success in 110 | true p = 0.70) = 7.841e-56   (transcript: 7.8×10⁻⁵⁶ ✓)
P(≤1 success in  25 | true p = 0.70) = 5.027e-12   (transcript: 5.0×10⁻¹² ✓)
P( 0 success in   3 | true p = 0.70) = 0.027000    (transcript: 2.7% ✓)
```

### 3.8 The natural base rate `32/1993 = 1.606%` (lines 5210, 15179)

```
32/1993 = 1.6056%  Wilson95 [1.1396%, 2.2578%]
```
The stated `1/25 = 4.00%` lift of 2.49× is correctly computed (4.00/1.6056 = 2.4913). But the lift is computed against a base rate whose own 95% interval is [1.14%, 2.26%], and the numerator is one event. Line 15198's `1-(1-0.01606)^25 ≈ 33.3%` recomputes to 33.286% ✓ — the transcript itself concludes "这个1/25完全可能由偶然产生."

### 3.9 `1342/1362` at `0.60%` precision (lines 721, 16253)

```
fire rate          = 1342/1362 = 98.5316%
base rate          =    8/1362 =  0.5874%
stated precision   = 0.60%
lift over base rate = 0.0060 / 0.005874 = 1.022×
expected TP at random ≈ 1342 × 8/1362 = 7.88 ; observed 0.006 × 1342 = 8.05
```
Firing on 98.5% of all windows yields precision statistically identical to the base rate. **This number measures nothing about the model; it measures the threshold.** The transcript labels it a post-hoc sensitivity check (721) but it is worth stating plainly that a 1.02× lift is exactly zero information.

### 3.10 The framework's own acceptance rule is unreachable at the sample sizes involved (lines 15659–15691)

Wilson lower bound ≥ 70% requires:

```
n=  13: need 13/13 = 100.00%
n=  50: need 42/50 =  84.00%     (transcript states this at 3566, 3975 ✓)
n= 100: need 79/100 = 79.00%     (transcript states this at 15682 ✓)
n= 200: need 153/200 = 76.50%
n= 500: need 371/500 = 74.20%
n=2000: need 1441/2000 = 72.05%
```
Recomputed Wilson lower bounds: `78/100 → 68.9296%` (transcript "68.93%" ✓) and `79/100 → 70.0200%` (transcript "70.02%" ✓). A perfect record is required at n = 13; and a perfect 13/13 record's Wilson interval is [77.19%, 100%]. **A perfect record on this experiment would still not license a 70% point claim with a 70% lower bound at n=13 — it would, at 77.19%, but with a 22.8-point upper slack.** Line 13283 already notes the frozen protocol demanded ≥20 signals and returned `NOT_ACCEPTED` at 13.

### 3.11 Within-signal AUC `0.472` (lines 14365, 14397, 15766)

```
AUC 0.472 over 9 hits / 4 misses  →  U = 0.472 × 36 = 16.99 of max 36
achievable grid step = 1/36 = 2.78 pp
exact P(AUC ≤ 0.472 under the null) = 295/715 = 0.4126
```
An AUC *below* chance on 13 points is unremarkable (two-sided p ≈ 0.83). The transcript draws the right conclusion — "分数更高 = 更值得优先 的证据不存在" (14368) — but the number is best read as *no signal either way*, not as evidence of negative ranking ability.

### 3.12 HHI checks — both reproduce exactly (lines 4258, 15960–15970)

Line 4258: "2024开发阶段31条冻结规则信号分散在26个日期，单日最多2条；按信号日期计算的集中度HHI约0.0427，相当于约23.4个'有效独立日期'", and the 2025 counterpart at 15960–15967.

With 31 signals spread over 26 dates with a maximum of 2 on any day, the only consistent distribution is 5 dates with 2 signals and 21 dates with 1:

```
2024 dev: [2,2,2,2,2,1×21] over 31 signals
          sum((n_i/31)^2) = 41/961 = 0.04266389   →  transcript "0.0427" ✓
          1/HHI           = 23.4390               →  transcript "约23.4" ✓

2025 holdout: [1,3,6,1,1,1] over 13 signals
          sum((n_i/13)^2) = 49/169 = 0.28994083   →  transcript "0.290" ✓
          1/HHI           = 3.448980              →  transcript "3.45" ✓
```

Both HHI values reproduce exactly from the stated counts. This was the only candidate arithmetic discrepancy in the dataset and it resolves in the transcript's favour. **The 2024→2025 collapse from 23.44 effective dates to 3.45 is real and is one of the conversation's most valuable quantitative findings.**

### 3.13 Fragility of the 69.23% under resampling and perturbation

```
leave-out 2025-04-14 cluster: (9-5)/(13-6) = 4/7  = 57.1429%  Wilson95 [25.0%, 84.2%]
leave-out 2025-04-11 cluster: (9-1)/(13-3) = 8/10 = 80.0000%  Wilson95 [49.0%, 94.3%]
±0.5-pixel perturbation: 10 runs in [50.00%, 72.73%], 7-11 signals each (3383, 5851, 10354)
2024 dev search: 198 + 1089 = 1287 configurations (10288-10290)
```
Removing **one day** moves the headline by 22.9 points (57.14% ↔ 80.0%) — a swing larger than the entire claimed distance to the 70% target. With 1,287 development configurations searched (3387) on a 2024 set of 31 signals, the 2025 holdout is a single small draw from a heavily optimized selection procedure.

### 3.14 Minimum sample size for the user's actual goal (line 15228–15236)

```
n ≈ 1.96² × 0.7 × 0.3 / 0.10² = 80.67  → 81 independent signals for ±10 pp
n ≈ 1.96² × 0.7 × 0.3 / 0.05² = 322.7  → 323 independent signals for ±5 pp
```
Both reproduce exactly ✓. The largest honest independent count anywhere in this conversation is **13 signals collapsed to ≈3.45 dates** (frozen 2025), **1 true positive** (40-A-share OOS), and **2 bull events** (US monthly proxy). The gap to 81 independent signals is roughly two orders of magnitude.

### 3.15 `9/13` against the balanced-pool 50% benchmark (lines 14882–14904)

The transcript computes the exact hypergeometric tail: X ~ Hypergeometric(N=100, K=50, n=13), and reports `P(X≥9) ≈ 0.1168`, concluding "在常用5%显著性标准下没有达到."

```
scipy.stats.hypergeom.sf(8, 100, 50, 13) = 0.116801     →  transcript "≈0.1168" ✓
scipy.stats.binomtest(9, 13, 0.50, alternative='greater').pvalue = 0.133423
scipy.stats.binomtest(9, 13, 0.50).pvalue                        = 0.266846
```
The transcript's exact hypergeometric p-value is **correct**, and it is the right model (sampling 13 of 100 without replacement from a 50:50 pool). Both it and the binomial-with-replacement reading fail to reach 5% significance. **This is the single cleanest refutation of the 69.23% in the whole conversation:** even granting the experiment its own hand-built 50:50 benchmark, ignoring the pixel-derived data, ignoring the 1,287-configuration development search, and ignoring the market clustering, 9/13 is **not** significantly better than chance.

---

## 4. Numbers that are engineering (not strategy) results

The following are genuine, reproducible engineering achievements. **None of them carries any information about predictive power.** They are listed here so that they are never counted as strategy evidence.

| Engineering result | Line # | What it establishes |
|---|---|---|
| `4465` unique tickers readable from CASE stock list | 4495 | data access worked |
| `1500` trading days, 2016-01-04 → 2022-03-04 | 4495 | calendar readable; also proves the frozen 2005–2010/2013–2014 training blocks cannot exist in this dataset (4499) |
| `001207.XSHE` limit-up case: 4 consecutive days with `open=high=low=close=limit_up` and positive volume/trades | 4511–4524, 4532 | execution-layer defect: current logic judges all 4 as valid next-open entries; "当天有成交量"不能证明你能以次日开盘价成交 (4536) |
| `364/364` SHA-256 manifest match | 3381, 5788, 5918, 10135, 10910, 13124 | package integrity |
| `13` signals reproduced by the frozen re-check script | 3381, 5918, 10135, 10824, 10910, 13124 | bit-for-bit reproducibility of a *frozen* result; the script itself returns `NOT_ACCEPTED` (13198) |
| `40` simulated symbols / `271320` synthetic rows, 4-model smoke test | 2691, 2903, 4023, 4489, 10467 | the pipeline runs end-to-end |
| `21/21` tests (documented) vs `14/14` tests (independently readable) | 13481 / 14390, 16205, 16290 | **a version-evidence gap the audit flags:** the artifact claims 21 tests; the readable log shows 14. The transcript states this correctly at 16205 and 16290 |
| `16/16` SHA (bull framework) | 6566, 7209, 7513, 8499 | package integrity |
| `20/20` SHA (old KDJ package) | 7332, 8501, 13907 | package integrity |
| `9/9` tests (old KDJ package) | 2693, 7332, 11860 | pipeline runs |
| `actual_market_stocks_trained=0` | 2691, 3154, 3539, 3913, 4354, 4489, 4600, 4769, 5447, 5614, 5916, 6352, 6566, 6702, 7209, 7513, 7608, 8499, 8677, 9010 | **the program's own output: zero real stocks trained** |
| `market_precision=null` | 2691, 3154, 3539, 3913, 4354, 4489, 4600, 4769, 5447, 5614, 5916, 6352, 6566, 6702, 7209, 7513, 7608, 8677, 9010 | **the program's own output: no market precision exists** |
| Wilson-interval spot values `92.87%`, `93.98%`, `71.49%`, `15.51%`, `56.15%`, `42.37–87.32%`, `35.4–87.9%`, `0.16–4.97%`, `0.71–19.54%` | 6381, 4046, 4191, 12739, 15188, 10280, 10853, 15186, 15187 | **recomputed and all correct** — the conversation's own statistics are reliable |

**Statement to be made plainly:** `4465` tickers, `1500` days, `364/364` hashes, `13` reproduced signals, `40` symbols, `271320` synthetic rows, `21/21` or `14/14` tests, `16/16` or `20/20` hashes, and the `001207.XSHE` limit-up finding are engineering facts. **They carry no information whatsoever about whether the strategy predicts anything.** The strongest of them — `actual_market_stocks_trained=0` and `market_precision=null` — are the program's own admission that no strategy result exists.

**One engineering number that is more than engineering:** the `001207.XSHE` finding (4511–4538) is a *data-integrity* result that retroactively casts doubt on any precision computed with a `next_open > 0 and volume > 0` entry test, because the framework would have treated four unbuyable limit-up opens as valid entries. It biases precision upward. This is the one engineering discovery with direct bearing on the validity of the strategy numbers.

---

## 5. Bottom line

**No.** Nothing in this conversation constitutes real evidence of predictive skill.

The only out-of-sample real-market results are `1/110 = 0.91%` (Wilson 95% [0.16%, 4.97%]) and `1/25 = 4.00%` (Wilson 95% [0.71%, 19.54%]) — **one true positive each** — against a base rate of `1.606%`. Two tree models scored `0/3`. The US monthly proxy has `2` independent bull events in `1362` windows. The `9/13 = 69.23%` headline is an anchor-recognition rate on post-hoc-selected charts, effective n ≈ 3.45 market dates, and its own screening protocol returned `NOT_ACCEPTED`. The original `70%` is same-year in-sample anchor coverage, and re-trained honestly it drops to `85/150 = 56.7%`.

The assistant's own final status statements, verbatim:

> 在这些真实结果出现之前，70%仍只是研究目标，不能作为已完成结论。 — line 16294

> | >70%实股证据 | **仍无** | — line 16251 (identical at 14399 and 15833; "仍然没有" at 14964; "仍没有" at 10780)

> 本轮没有新的实股训练，因此没有新的正式命中率、事件召回率或股票名单。最重要的新结论是：旧69.23%的代理结果可以精确拆解成“18%赢家触发率 vs 8%输家触发率”，其2.25倍区分力远不足以证明在自然稀有事件分布下接近70%的 Precision。 — line 16161

> 因此当前可核验状态是：**40只真实A股的252日旧基线没有新增结果，仍未达到70%；504日严格低位真实OHLCV模型仍未完成；新增加的是一个真正冻结跨年的“图窗代理实验”，2025为9/13、69.23%，但事件级有效独立样本远小于13，赢家覆盖仅9/50，而且目标标签不是未来4倍。** 当前没有新的独立 bull-cycle Recall，也没有可以宣称的>70%实股精确率。 — line 13172 (quoting in full; no elision)

> 你的70%目标仍未被真实验证。 — line 3393

The conversation's greatest virtue is that it audits itself accurately: its arithmetic is sound, its intervals are correct, and it repeatedly refuses to promote the 70%. Its greatest defect is structural — `actual_market_stocks_trained=0` from the first assistant turn to the last.

---

### Audit artifacts

- `D:\ccc\audit_intervals.py` — Wilson + exact Clopper–Pearson for every headline ratio; recomputation of ~55 ratios and derived quantities.
- `D:\ccc\audit_intervals2.py` — Fisher exact test on the 2.25× lift, exact null for AUC 0.472, HHI recomputation, Wilson lower-bound boundary search, engineering-number intervals.

### Cited verification commands

```
python audit_intervals.py    # Section A/B/C output
python audit_intervals2.py   # Section D1-D8 output
```
