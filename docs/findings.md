# Findings

## Current Study Status

The current study evaluates whether conventional debt-to-income (DTI) ratios adequately capture household-level borrowing risk when financial uncertainty and liquidity are taken into account.

Three research questions have been evaluated so far:

- **RQ-A:** Do households within a similar DTI range exhibit substantially different simulated financial risk?
- **RQ-B:** Does the proposed Borrowing Stress Score rank simulated borrowing risk better than DTI alone?
- **Sensitivity Analysis:** How strongly do the results depend on assumptions used in the simulation?

The experiments currently use a synthetic population of 600 household/loan combinations, with 1,500 simulation trials per household.

---

# Finding 1 — DTI Hides Substantial Risk Variation

### Research Question

> Among households within a conventional DTI band, how much can their simulated financial risk differ?

We selected households with a DTI between **33% and 37%**. There were **46 households** in this band, meaning they would all appear similar under a conventional DTI-based affordability assessment.

However, their simulated probability of savings depletion varied substantially:

| Statistic | Probability of savings depletion |
|---|---:|
| Minimum | 0.1% |
| 25th percentile | 0.1% |
| Median | 1.0% |
| 75th percentile | 4.3% |
| Maximum | 26.3% |

The results demonstrate substantial risk heterogeneity among households with similar DTI.

### Liquidity comparison

Within the same DTI band:

- Households with **<3 months of liquidity** had a mean simulated depletion probability of **11.0%** (n=16).
- Households with **≥6 months of liquidity** had a mean simulated depletion probability of **0.1%** (n=18).

This represents a very large difference in simulated risk despite the households having similar DTI.

### Income volatility comparison

The same DTI band also showed differences based on income volatility:

- Income volatility <10%: mean depletion probability = **3.7%** (n=12)
- Income volatility >25%: mean depletion probability = **6.3%** (n=13)

The difference was smaller than the liquidity effect in this experiment.

### Interpretation

DTI captures the relationship between debt obligations and income, but it does not directly capture the household's liquidity buffer or exposure to financial shocks.

Therefore, two households with similar DTI can have substantially different simulated probabilities of exhausting their savings.

### Important limitation

These are **simulation results, not observed default or bankruptcy rates**. They depend on the assumptions used by the simulation model. The results therefore support the claim that DTI can hide differences under the specified simulation assumptions, rather than proving that real-world borrowers with similar DTI have the exact same risk spread.

---

# Finding 2 — Borrowing Stress Score Tracks Simulated Risk Better Than DTI Alone

### Research Question

> Does the proposed Borrowing Stress Score provide a better ranking of simulated borrowing risk than DTI alone?

Across all **600 simulated households**, Spearman rank correlations with simulated probability of savings depletion were:

| Metric | Spearman ρ | p-value |
|---|---:|---:|
| Borrowing Stress Score | **+0.927** | 8.12e-257 |
| DTI alone | +0.754 | 3.61e-111 |
| Emergency-fund months | **-0.815** | 9.64e-144 |

The Borrowing Stress Score had the strongest rank correlation with simulated depletion probability.

### Interpretation

Within this simulated population, the Borrowing Stress Score was a stronger ranking proxy for simulated financial risk than DTI alone.

This suggests that incorporating additional dimensions of financial resilience—particularly liquidity and other household characteristics—can provide more information about simulated borrowing risk than relying on DTI alone.

### Important caveat: structural correlation

The correlation should **not** be interpreted as proof that the Borrowing Stress Score independently predicts real-world financial risk.

Both the stress score and the simulation use overlapping inputs, including savings and expenses. Therefore, part of the observed correlation is structurally induced.

The appropriate claim at this stage is:

> **The Borrowing Stress Score is a strong ranking proxy for simulated depletion risk within the current experimental framework.**

It should not yet be described as a validated real-world risk score.

---

# Finding 3 — Simulation Results Are Highly Sensitive to Certain Assumptions

### Research Question

> How much do assumptions about economic shocks affect the estimated probability of savings depletion?

A stretched financial profile was selected:

- Monthly income: **₹55,000**
- Monthly expenses: **₹28,000**
- Savings: **₹1,20,000**
- Loan: **₹8,00,000**
- Tenure: **5 years**

Under the default assumptions, the simulated probability of savings depletion was:

> **29.4%**

Each major simulation assumption was then perturbed independently.

| Perturbation | Depletion probability | Change |
|---|---:|---:|
| Baseline | 29.4% | — |
| Job-loss probability 1% | 16.4% | -13.0 pp |
| Job-loss probability 4% | 49.6% | +20.2 pp |
| Income volatility 2.5% | 29.3% | -0.1 pp |
| Income volatility 10% | 30.4% | +1.0 pp |
| Expense shock 1.5% | 25.7% | -3.8 pp |
| Expense shock 6% | 39.6% | +10.1 pp |
| Job-loss income = 40% | 22.8% | -6.6 pp |
| No expense compression | 31.5% | +2.0 pp |

### Interpretation

The simulated depletion probability is highly sensitive to the assumed monthly job-loss probability.

Changing the assumed job-loss probability from 1% to 4% changed the estimated depletion probability from **16.4% to 49.6%**.

In contrast, changing income volatility from 2.5% to 10% had a relatively small effect in this particular experiment.

This indicates that the simulation's absolute probability estimates are strongly dependent on the assumptions governing major financial shocks.

### Consequence for interpretation

The current simulation does **not** provide sufficient evidence to claim:

> "This household has exactly a 29.4% probability of running out of savings."

The 29.4% figure is conditional on the assumptions used by the simulation.

A more defensible interpretation is:

> "Under the current simulation assumptions, this scenario produces a substantially higher depletion risk than alternative scenarios."

This distinction is important because some of the assumptions, particularly the job-loss probability, have not yet been validated against external empirical data.

### Current conclusion

Absolute risk probabilities should therefore be treated as **model-dependent estimates** rather than calibrated real-world probabilities.

Relative comparisons between scenarios are currently more defensible because the scenarios are evaluated under the same simulation assumptions.

---

# Overall Findings So Far

The experiments provide three preliminary findings:

### 1. Static DTI can hide substantial differences in simulated financial resilience.

Households within the same 33–37% DTI band showed depletion probabilities ranging from **0.1% to 26.3%**.

### 2. A multidimensional stress score provides a stronger ranking of simulated risk than DTI alone.

The Borrowing Stress Score achieved a Spearman correlation of **0.927**, compared with **0.754** for DTI alone.

However, this relationship is partly structural because the score and simulation share several inputs.

### 3. Simulation assumptions materially affect absolute risk estimates.

The estimated depletion probability changed from **16.4% to 49.6%** when the assumed job-loss probability was changed.

Therefore, the project should avoid presenting simulated probabilities as calibrated real-world probabilities until the underlying assumptions are empirically justified.

---

# What We Can Claim at This Stage

The current experiments support the following claim:

> **Within the simulated population, households with similar DTI can exhibit substantially different financial resilience, and incorporating liquidity and other household-level characteristics provides a stronger ranking of simulated savings-depletion risk than DTI alone.**

The experiments also demonstrate that:

> **Probabilistic financial risk estimates are highly dependent on assumptions about major financial shocks, making sensitivity analysis essential when interpreting simulation results.**

---

# What We Cannot Claim Yet

The current results do NOT establish that:

- DTI is inadequate for real-world lending decisions.
- The Borrowing Stress Score predicts real-world loan default.
- The simulated depletion probabilities represent real-world probabilities.
- The Borrowing Stress Score is better than DTI for actual borrowers.
- The system improves people's financial decisions.
- The simulation model is empirically calibrated.
- The methodology is novel relative to all existing financial planning or credit-risk research.

These claims require additional validation.

---

# Next Research Priorities

The next stage should focus on strengthening the evidence rather than adding more product features.

1. **Validate simulation assumptions**
   - Identify credible empirical sources for income shocks, unemployment/job loss, expense shocks, and related parameters.
   - Replace arbitrary assumptions where possible.

2. **Reduce structural circularity in RQ-B**
   - Investigate whether the Borrowing Stress Score provides useful information beyond the variables directly used by the simulation.
   - Consider out-of-sample or holdout evaluation.

3. **Test robustness**
   - Repeat RQ-A across different DTI bands.
   - Test different loan sizes and tenures.
   - Test different household financial profiles.

4. **Compare alternative affordability measures**
   - DTI
   - EMI-to-income
   - Emergency-fund months
   - Borrowing Stress Score

5. **Evaluate scenario recommendations**
   - Compare alternative loan amounts, tenures, and down-payment strategies.

6. (venv) rakshansingh@Rakshans-MacBook-Air finlens % python -m scripts.faithfulness_study   
Running 20 explanation cases...

Direct use of automatic function calling (AFC) in Models.generate_content is not recommended. Instead, we recommend to use AFC in Chat.send_message. Similarly, direct use of AFC in Models.generate_content_stream is not recommended. Instead, we recommend to use AFC in Chat.send_message_stream.
  case  1: 15/15 = 100.0%
  case  2: 12/12 = 100.0%
  case  3: 15/16 = 93.8%  unsupported: [100.0]
  case  4: 9/11 = 81.8%  unsupported: [100.0, 100.0]
  case  5: 15/15 = 100.0%
  case  6: 14/16 = 87.5%  unsupported: [100.0, 100.0]
  case  7: 13/14 = 92.9%  unsupported: [100.0]
  case  8: 9/9 = 100.0%
  case  9: 17/19 = 89.5%  unsupported: [100.0, 100.0]
  case 10: 11/13 = 84.6%  unsupported: [100.0, 100.0]
  case 11: 13/13 = 100.0%
  case 12: 10/11 = 90.9%  unsupported: [100.0]
  case 13: 11/11 = 100.0%
  case 14: 13/14 = 92.9%  unsupported: [100.0]
  case 15: 13/13 = 100.0%
  case 16: 6/7 = 85.7%  unsupported: [100.0]
  case 17: 17/17 = 100.0%
  case 18: 12/14 = 85.7%  unsupported: [100.0, 100.0]
  case 19: 15/15 = 100.0%
  case 20: 11/13 = 84.6%  unsupported: [100.0, 100.0]

==========================================================
RQ-C: LLM EXPLANATION FAITHFULNESS
==========================================================
Cases evaluated        : 20
Mean faithfulness rate : 93.5%
Median                 : 93.3%
Minimum                : 81.8%
Cases with 100% rate   : 9 / 20
Cases with any failure : 11 / 20

Most common unsupported values:
          100.00  x17

Note: the strict checker flags scale references (e.g. the literal
100 in 'out of 100') as unsupported. These are false positives and
are retained rather than special-cased -- see docs/findings.md.