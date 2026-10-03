> **Paper 010 proposal — Equity-aware enforcement.** Imported 2026-06-07 from the local
> outline `P7` (`ongoing-papers/papers/07-equity-fairness/`). Read with the
> [`ROADMAP.md`](../ROADMAP.md) deltas in mind: **monorepo** — features are `qfire`
> modules, not `haarf-*` crates or spin-out repos — and **confidential-enclave**
> production deployment, validated locally on Ollama via the OpenAI-compatible
> bridge. The threat model, hypotheses, experiments, datasets, and figures below
> are the pre-registered working plan; they are reconciled against the gateway as
> built at the feature-spec (stage 2) and paper-spec (stage 4) gates.

---

# Paper 7 — Equity-Aware Enforcement: Fairness Assurance for Clinical AI Agents

**Crate:** `haarf-equity` · **New dataset:** HAARF-Equity · **Covers:** C7 (full) · **Status:** outline

## Abstract

HAARF Category 7 (Bias Mitigation & Population Equity) is entirely unaddressed by the
existing harness, and the security controls themselves may *introduce* inequity: if the
gateway denies, escalates, or contraindicates unevenly across demographic groups, it
becomes a fairness hazard. We build `haarf-equity`, a runtime fairness-monitoring layer
that (a) audits the agent's clinical decisions for subgroup performance disparities and
(b) audits the *gateway's own* deny/escalate behavior for parity. We contribute
**HAARF-Equity**, synthetic multi-demographic cohorts with injected, ground-truthed
disparities, and quantify both detection of disparate impact and the cost of mitigation.

## Stakeholders & expert-in-the-loop

Fairness claims are only credible when grounded by experts who live the harms and own
the metrics; this work keeps the following in the loop.

- **Health-equity / health-disparities researcher** — frames which gaps are clinically
  meaningful vs. statistical noise and which protected axes actually drive harm here.
- **Fairness-in-ML / algorithmic-bias scientist** — guards metric choice and the
  impossibility-theorem trade-offs, so mitigation does not just relocate disparity.
- **Biostatistician / epidemiologist** — owns subgroup power, disparity estimators, and
  multiple-comparison/intersectional correction (E2, E5) so detection claims hold up.
- **Frontline clinician serving diverse/underserved populations** — validates that
  "clinically matched" cases truly match and that deny/escalate behavior is safe at the
  bedside across the populations they treat.
- **Community / patient advocate from affected populations** — keeps the injected
  disparities and vulnerable-case scenarios representative of lived harm, not assumptions.
- **Bioethicist** — adjudicates the equity-vs-aggregate-safety tension (H3) and the ethics
  of group-aware thresholds and mandatory-review defaults.
- **Vulnerable-population clinical specialist (pediatrics / obstetrics / geriatrics)** —
  pressure-tests the B3 scenario set (dosing, contraindications, polypharmacy) for realism.
- **Regulatory / compliance lead for equity reporting** — ensures the C7.8 equity report
  and audit evidence meet reporting obligations and survive external scrutiny.

## Problem model

- **B1 Outcome disparity** — agent decisions differ in quality/accuracy across protected
  groups (sex, race/ethnicity, age, language, disability, payer).
- **B2 Enforcement disparity** — HAARF controls deny/escalate/contraindicate at
  different rates across groups for clinically equivalent cases.
- **B3 Vulnerable-population harm** — pediatrics, pregnancy, geriatrics, rare disease,
  resource-limited settings receive degraded or unsafe handling.
- **B4 Representation gap** — training/reference data under-represents a group, surfacing
  as low-confidence/high-deny zones.

## Research questions

- **RQ1** Do HAARF controls exhibit measurable enforcement disparity (B2) on
  clinically-matched cases across protected groups?
- **RQ2** Can runtime subgroup monitoring detect injected outcome disparities (B1) at
  what magnitude/sample size?
- **RQ3** What mitigation (threshold-by-group calibration, reject-option, equalized
  escalation) reduces disparity without lowering aggregate safety?
- **RQ4** How are vulnerable populations (B3) best protected — stricter defaults or
  mandatory human review?

## Hypotheses

- **H1** Uncalibrated HAARF enforcement shows statistically significant deny/escalate
  disparity (≥ 1 group, ≥ ε gap) on matched cases. *(motivates the paper.)*
- **H2** Subgroup monitoring detects an injected disparity of size δ with ≥ 90% power at
  N per group derived from the dataset.
- **H3** Equity-calibrated thresholds reduce the max pairwise disparity by ≥ 70% with
  aggregate safety loss ≤ 2%.
- **H4** Mandatory-review for flagged vulnerable cases removes B3 harm at a quantified
  escalation cost (ties to Paper 6).

## Experiments → figures

- **E1 Enforcement-parity audit (→ Fig 1):** deny/escalate/contra rates by group on
  matched cases; disparity bars + CIs.
- **E2 Detection power (→ Fig 2):** detection rate vs. injected disparity magnitude and
  per-group N.
- **E3 Mitigation frontier (→ Fig 3):** max disparity vs. aggregate safety across
  {none, group-calibrated, reject-option, equalized-odds-style}.
- **E4 Vulnerable-population protection (→ Fig 4):** harm rate for B3 groups under
  default vs. protective policy; escalation cost.
- **E5 Intersectional (→ Fig 5):** disparity across attribute *combinations* (where
  single-axis audits miss harm).
- **E6 Gateway overhead (→ shared Fig).**

## Datasets

**Public:**
- **MIMIC-IV / eICU-CRD** (credentialed) — real demographic distributions and outcome
  signals for realism and for measuring naturally-occurring disparity.
- **Folktables / ACS** and **AIF360 / Fairlearn** reference datasets — fairness-metric
  methodology and well-characterized bias benchmarks.
- **Synthea** — primary substrate: demographics are *controllable*, enabling injected
  ground-truth disparities.

**New — HAARF-Equity (the contribution):**
- Synthetic cohorts with **known, injected disparities** of tunable magnitude across
  single and intersectional protected attributes, each clinical case having a matched
  counterfactual across groups.
- Agent decision + gateway decision traces labeled with protected attributes and the
  "fair" reference decision, so any fairness/enforcement audit can be scored.
- A vulnerable-population scenario set (pediatric dosing, pregnancy contraindications,
  geriatric polypharmacy, low-resource defaults). Apache-2.0, synthetic.

## Validation & statistics

- Multiple fairness metrics reported side-by-side (demographic parity diff, equalized
  odds, predictive parity, calibration-within-groups) — with the impossibility-theorem
  caveat stated explicitly.
- Disparities with 95% CIs; significance via permutation tests; intersectional analysis
  with multiple-comparison correction.
- Counterfactual matching to isolate enforcement disparity from case-mix.
- **Threats to validity:** protected attributes are often proxies; synthetic disparity
  may not match real-world structure (cross-check against MIMIC where possible).

## Rust components (`haarf-equity`)

- **Subgroup monitor:** streaming per-group decision/outcome stats with sequential tests
  (no peeking bias); raises a disparity alert when a metric breaches a configured bound.
- **Equity calibrator:** offline-fit group-aware thresholds shipped as versioned,
  audited parameters (reuses Paper 6's calibration machinery).
- **Vulnerable-case flagger:** policy tags (links Paper 3) that force protective defaults
  or mandatory review (links Paper 6).
- **Equity reporter:** generates the C7.8 regulatory equity report from the audit log
  (links Paper 2).

## Server / proxy design

- Passive monitoring layer (does not block on the hot path by default) plus an optional
  active flagger for vulnerable cases.
- Consumes the signed audit stream (Paper 2) so equity metrics are computed over
  tamper-evident records.

## Metrics

| Metric | Definition | Target |
|---|---|---|
| EDP | Max pairwise enforcement disparity | ≤ ε after calibration |
| ODP | Outcome-disparity detection power | ≥ 90% @ δ |
| MIT | Disparity reduction from mitigation | ≥ 70% |
| VPH | Vulnerable-population harm rate | ≈ 0% (with review) |
| SAF | Aggregate safety retained | ≥ 98% |

## Repo scaffold

```
haarf-equity/
├── crates/haarf-equity/            # monitor + calibrator + flagger + reporter
├── dataset/haarf-equity/           # cohorts + counterfactuals + vulnerable scenarios
├── figures/
└── paper/
```
