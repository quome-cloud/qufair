<div align="center">

<img src="assets/qufair-logo.svg" alt="qufair" width="520">

### An out-of-band subgroup fairness monitor that audits the guardrail's own deny and escalate decisions

![built with](https://img.shields.io/badge/built_with-Rust-DEA584?logo=rust&logoColor=white)
![layer](https://img.shields.io/badge/layer-equity-7c3aed)
![HAARF](https://img.shields.io/badge/HAARF-C7-0ea5e9)
![paper](https://img.shields.io/badge/paper-preprint-2563eb)
![status](https://img.shields.io/badge/status-research_prototype-orange)
![license](https://img.shields.io/badge/license-Apache_2.0-3FB950)
[![dataset](https://img.shields.io/badge/🤗_dataset-Quome%2Fequitybench-FFD21E)](https://huggingface.co/datasets/Quome/equitybench)

[**Quickstart**](#quickstart) · [How it works](#how-it-works) · [Reproduce](#reproduce-the-experiments) · [Results](#headline-results) · [Paper](papers/010-equity/main.pdf) · [Dataset](https://huggingface.co/datasets/Quome/equitybench) · [Cite](#cite)

</div>

---

A guardrail that denies or escalates clinical agent actions unevenly across protected groups is itself a fairness hazard, distinct from and invisible to the agent's own bias. The equity layer is a passive, out-of-band consumer of the qfire decision stream: a streaming subgroup monitor (demographic parity, equalized odds, predictive parity with Wilson, Newcombe, and permutation inference), an equity calibrator with group-threshold, reject-option, and equalized-odds arms, a vulnerable-population flagger, and a HAARF C7.8 equity reporter. Running 1003 clinically identical requests that vary only the patient's demographic marker through the live gateway's llama3.1:8b scope-judge, the gateway is exactly even on sex, age, language, and payer but shows a 13.6% maximum race enforcement gap, over-blocking in-scope clinical requests for some racial groups; the same monitor recovers the documented COMPAS disparity (57.6% vs 33.1%) on real decisions.

`qufair` is **a module of the QUOKKAGUARD program**: one Rust security gateway (`qfire`) that sits in front of any OpenAI-compatible model endpoint and decides **ALLOW ▸ forward · BLOCK ▸ refuse · ESCALATE ▸ human review** for every request and response. Each module adds exactly one enforcement layer to that gateway plus one adversarial dataset and one paper. This repository is a self-contained snapshot of the gateway with **this layer** (`src/equity/`, on the *monitor* path, HAARF control C7), its dataset (**EquityBench**), the experiment harness, and the paper.

> **Needs a local model for some experiments.** Live runs go through [Ollama](https://ollama.com) on the OpenAI-compatible endpoint; no paid API keys are used anywhere in this repo.

## How it works

- **Streaming subgroup monitor** - per-(axis, group) accumulators over group-labeled `DecisionRecord`s (action in {allow, deny, escalate}) yield demographic-parity, equalized-odds, and predictive-parity disparities per axis; alerts fire only after a minimum per-group sample (no peeking), with an alert bound of a 10-point gap at alpha 0.05.
- **Inference done in Rust** - rates carry Wilson 95% CIs, the pairwise disparity carries a Newcombe square-and-add CI, significance is a two-sided permutation test that shuffles group labels over pooled outcomes (2000 iterations, fixed seed), and multi-cell intersectional audits are Holm-Bonferroni corrected.
- **Equity calibrator** - four mitigation arms (none, group_threshold equalizing selection rate, reject_option deferring near-boundary cases to human review, equalized_odds equalizing the true-positive rate) are fit offline on even seeds, evaluated on held-out odd seeds, and shipped as versioned, audited parameters that re-decide one case from its score.
- **Vulnerable-population flagger** - tags pediatric-dosing, pregnancy-contraindication, geriatric-polypharmacy, and low-resource cases and forces them to mandatory human review, with the escalation cost measured rather than hidden.
- **Equity reporter** - serializes the HAARF C7.8 equity report (per-axis disparities, CIs, alerts, mitigation deltas) into the quledger audit log; the monitor ingests the 180,000-record stream at 5.9M records/s, 0.17 us per record, so it can run always-on.

## Quickstart

Requires Rust 1.85+ (`rustup`), Python 3.10+ for the analysis scripts, and `tectonic` (or `pdflatex`) only if you want to rebuild the paper.

```bash
git clone https://github.com/quome-cloud/qufair
cd qufair
cargo build --release
cargo test --lib equity   # this layer's tests
```

Then see the layer in action:

```bash
# matched/matched_named/vulnerable/intersectional and external/compas.jsonl are tracked;
# the 180k-trace injected.jsonl (~45MB) is gitignored -- regenerate it (seed 42, stdlib only):
python3 scripts/010-equity/gen_equity.py
# EquityBench generated:
#   injected   180000 records  -> datasets/010-equity/equitybench/injected.jsonl  (plus the other corpora)

# E5 (offline): a disparity hidden at a race x payer intersection -- single-axis audit sees 2.7%, the cell carries 52.1%
./target/release/equityrun e5 --corpus datasets/010-equity/equitybench/intersectional.jsonl --out results/010-equity/e5_intersectional.json

# EXT (offline): run the streaming subgroup monitor over real COMPAS decisions (6,130 defendants)
./target/release/equityrun ext --corpus datasets/010-equity/external/compas.jsonl --out results/010-equity/ext_compas.json --axis race
# -> recovers the documented disparity: African-American 57.6% vs white 33.1% restrictive-label rate, p < 0.001

# E1 (needs a local Ollama with llama3.1:8b pulled): the live gateway scope-judge parity audit over 1003 matched requests
QFIRE_JUDGE_MODEL=llama3.1:8b ./target/release/equityrun e1 --corpus datasets/010-equity/equitybench/matched.jsonl --out results/010-equity/e1_enforcement.json --model llama3.1:8b
# -> sex/age/language/payer gap 0; race max pairwise gap 13.6%

# Figures, tables and numbers.tex from whatever results exist:
python3 scripts/010-equity/summarize.py
```

## Reproduce the experiments

Every number in the paper traces to one of these runs (95% Wilson CIs, deterministic seeds, pinned model snapshots). Run outputs land in `results/010-equity/` (not tracked; see [`results/010-equity/README.md`](results/010-equity/README.md) for the exact regeneration commands).

| Exp | What it measures | Needs |
|---|---|---|
| E1 | Enforcement-parity audit of the live gateway's LLM scope-judge over matched-counterfactual requests, by protected axis | ollama |
| E2 | Monitor detection power vs injected disparity magnitude delta and per-group N | offline |
| E3 | Mitigation frontier: max disparity vs aggregate safety retained across the four calibrator arms on a held-out split | offline |
| E4 | Vulnerable-population protection: harm rate under default vs protective (mandatory-review) policy, with escalation cost | offline |
| E5 | Intersectional disparity that single-axis audits miss (Holm-corrected cell audit) | offline |
| E6 | Monitor overhead: throughput and per-record latency over the 180,000-record stream | offline |
| EXT | External validation: the subgroup monitor over the ProPublica COMPAS cohort (race axis) | offline |
| summary | Figures, markdown tables, and numbers.tex from results/010-equity/*.json | offline |

```bash
# E1 — Enforcement-parity audit of the live gateway's LLM scope-judge over matched-counterfactual requests, by protected axis
QFIRE_JUDGE_MODEL=llama3.1:8b cargo run --release --bin equityrun -- e1 --corpus datasets/010-equity/equitybench/matched.jsonl --out results/010-equity/e1_enforcement.json --model llama3.1:8b   # optional --limit N --concurrency 8; use matched_named.jsonl for the real-name cohort

# E2 — Monitor detection power vs injected disparity magnitude delta and per-group N
cargo run --release --bin equityrun -- e2 --corpus datasets/010-equity/equitybench/injected.jsonl --out results/010-equity/e2_detection.json

# E3 — Mitigation frontier: max disparity vs aggregate safety retained across the four calibrator arms on a held-out split
cargo run --release --bin equityrun -- e3 --corpus datasets/010-equity/equitybench/injected.jsonl --out results/010-equity/e3_mitigation.json

# E4 — Vulnerable-population protection: harm rate under default vs protective (mandatory-review) policy, with escalation cost
cargo run --release --bin equityrun -- e4 --corpus datasets/010-equity/equitybench/vulnerable.jsonl --out results/010-equity/e4_vulnerable.json

# E5 — Intersectional disparity that single-axis audits miss (Holm-corrected cell audit)
cargo run --release --bin equityrun -- e5 --corpus datasets/010-equity/equitybench/intersectional.jsonl --out results/010-equity/e5_intersectional.json

# E6 — Monitor overhead: throughput and per-record latency over the 180,000-record stream
cargo run --release --bin equityrun -- e6 --corpus datasets/010-equity/equitybench/injected.jsonl --out results/010-equity/e6_overhead.json

# EXT — External validation: the subgroup monitor over the ProPublica COMPAS cohort (race axis)
python3 scripts/010-equity/prep_external.py   # downloads + converts COMPAS (already tracked at datasets/010-equity/external/compas.jsonl)
cargo run --release --bin equityrun -- ext --corpus datasets/010-equity/external/compas.jsonl --out results/010-equity/ext_compas.json --axis race   # optional --min-group-n K

# summary — Figures, markdown tables, and numbers.tex from results/010-equity/*.json
python3 scripts/010-equity/summarize.py
```

**Dataset — EquityBench** (`datasets/010-equity/`): Synthetic, deterministic (seed 42) corpora: equitybench/matched.jsonl (1003 matched-counterfactual clinical requests, 59 templates x 5 protected axes, roughly 15% genuinely out-of-scope), matched_named.jsonl (real distinctive-name rendering), vulnerable.jsonl (60 scenarios across four vulnerable populations), intersectional.jsonl (attribute-pair records with a 2x2 antisymmetric interaction), and the gitignored ~45MB injected.jsonl (180,000 decision traces with injected disparity over a delta x per-group-N x seed grid); external/compas.jsonl holds 6,130 ProPublica COMPAS defendants converted to the monitor's decision-stream schema.

Regenerate the corpus (deterministic seeds):

```bash
python3 scripts/010-equity/gen_equity.py   # rebuilds equitybench/ incl. the untracked injected.jsonl; python3 scripts/010-equity/prep_external.py re-downloads and converts COMPAS
```

The corpus is also published as a Hugging Face dataset with a full data card: **[Quome/equitybench](https://huggingface.co/datasets/Quome/equitybench)** (`datasets.load_dataset("Quome/equitybench")`, or `hf download Quome/equitybench --repo-type dataset`).

All data are synthetic; no protected health information is used anywhere in this repository.

## Headline results

| Metric | Value | Context |
|---|---|---|
| Live gateway race enforcement gap, max pairwise (E1) | **13.6% (0 of 5 axes significant at audit N; overall enforcement 12.0%)** | n = 1003 matched requests, llama3.1:8b scope-judge; sex, age, language, payer gaps are exactly 0 |
| Monitor detection power (E2) | **>= 90% by delta = 0.10 at N = 200 per group; 100.0% for delta >= 0.20** | nominal false-positive rate at delta = 0 |
| Mitigation: max disparity, baseline vs group-threshold arm (E3) | **51.3% -> 1.2% (97.6% reduction) at 99.8% aggregate safety retained** | held-out split, delta = 0.30, N = 400; meets the pre-registered >= 70% reduction at <= 2% safety loss |
| Vulnerable-population harm, default vs protective policy (E4) | **100.0% -> 0.0%** | at an escalation cost of 100.0% of flagged cases |
| Intersectional blind spot: single-axis marginal gap vs intersectional cell gap (E5) | **2.7% vs 52.1%** | single-axis audit misses it; Holm-corrected cell audit detects it |
| Monitor overhead (E6) | **0.17 us per record, 5.9M records/s** | over 180,000 records |
| Cross-model robustness (6 open-weight judges) | **race gap 1.7% to 45.8%; 3 of 6 substantial, 1 significant; real-name cohort 0 of 5 significant** | direction and magnitude are model-specific; gpt-oss:120b is on the even end |
| External validation on COMPAS | **African-American 57.6% vs white 33.1% (24.5% gap; max pairwise 37.2%; equalized-odds gap 37.7%), p < 0.001** | 6,130 defendants; monitor recovers the documented disparity without tuning |

Full methodology, ablations, and statistics: **[the paper](papers/010-equity/main.pdf)**.

## The paper

**Equity-Aware Enforcement: When the Guardrail Itself Becomes a Fairness Hazard**

- PDF: [`papers/010-equity/main.pdf`](papers/010-equity/main.pdf)
- Source: [`papers/010-equity/`](papers/010-equity/) — `main.tex`, `numbers.tex` (every headline macro, generated by the scripts above), `figs/`, `refs.bib`
- Pre-registered proposal (threat model, hypotheses, experiment→figure map): [`papers/010-equity/PROPOSAL.md`](papers/010-equity/PROPOSAL.md)
- Rebuild: `cd papers/010-equity && make paper` (tectonic, or pdflatex + bibtex)

## Repository layout

| Path | What |
|---|---|
| `src/` | The `qfire` gateway crate. This paper's layer lives in `src/equity/`; the other modules are the always-on baseline it plugs into. |
| `src/bin/` | CLI (`qfire`) and per-paper experiment harnesses |
| `rules/`, `chains/` | Declarative rule and detector-chain library used by the gateway |
| `datasets/010-equity/` | EquityBench (also on Hugging Face: [Quome/equitybench](https://huggingface.co/datasets/Quome/equitybench)) |
| `scripts/010-equity/` | Dataset generator, experiment runners, figure and `numbers.tex` builders |
| `scripts/common/` | Shared helpers |
| `papers/010-equity/` | The paper (LaTeX + PDF + proposal) |
| `results/010-equity/` | Experiment outputs (see above) |
| `tests/`, `benches/` | Integration tests and Criterion benches |
| `SNAPSHOT.md` | Which `quokkaguard` commit this repo was exported from |

## Relationship to QUOKKAGUARD

This repo is a **snapshot** of the QUOKKAGUARD program's gateway (export `1c04c3a34841`, 2026-10-02), filtered to the `qufair` module. The full `qfire` crate is included so this layer builds, tests, and runs standalone; the other modules are the always-on baseline the layer plugs into. Issues and pull requests are welcome here.

This layer builds on: [quledger](https://github.com/quome-cloud/quledger), [qutriage](https://github.com/quome-cloud/qutriage).

Sibling repos in the series: [quanchor](https://github.com/quome-cloud/quanchor), [quledger](https://github.com/quome-cloud/quledger), [qubom](https://github.com/quome-cloud/qubom), [quwarden](https://github.com/quome-cloud/quwarden), [qudam](https://github.com/quome-cloud/qudam), [quantidote](https://github.com/quome-cloud/quantidote), [quorum](https://github.com/quome-cloud/quorum), [qutriage](https://github.com/quome-cloud/qutriage), [qudrift](https://github.com/quome-cloud/qudrift), [qupassport](https://github.com/quome-cloud/qupassport), [quconsent](https://github.com/quome-cloud/quconsent), [qubroker](https://github.com/quome-cloud/qubroker), [qusiege](https://github.com/quome-cloud/qusiege).

## Cite

If you use this code or dataset, cite the paper and the HAARF framework it implements:

```bibtex
@unpublished{schwoebel2026qufair,
  author = {Schwoebel, Jim and {QUOKKAGUARD Contributors}},
  title  = {Equity-Aware Enforcement: When the Guardrail Itself Becomes a Fairness Hazard},
  note   = {Preprint. Quome, QUOKKAGUARD program (qufair module)},
  year   = {2026},
  url    = {https://github.com/quome-cloud/qufair}
}

@unpublished{schwoebel2026haarf,
  author = {Schwoebel, Jim and Frasch, Martin and Spalding, Art and Sewell, Ed and Englert, Phil and Halpert, Ben and Overbay, Collin and Semenec, Ingrida and Shor, Joel},
  title  = {{HAARF}: Healthcare {AI} agents regulatory framework --- a comprehensive security verification standard for autonomous {AI} systems in clinical environments},
  note   = {medRxiv Preprint},
  year   = {2026},
  month  = {April},
  doi    = {10.64898/2026.04.09.26350519},
  url    = {https://www.medrxiv.org/content/10.64898/2026.04.09.26350519v1}
}
```

## Status

Research prototype. It demonstrates the layer end to end with reproducible experiments; it is not a certified medical device or a production security product. Threat-model boundaries and known gaps are in the paper's Discussion.

## License

Apache License 2.0 — see [LICENSE](LICENSE). Copyright (c) 2026 Quome, Inc.
