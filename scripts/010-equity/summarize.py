#!/usr/bin/env python3
# Copyright 2026 Quome. Licensed under the Apache License, Version 2.0.
"""Summarize EquityBench results (paper 010) into figures + numbers.tex + tables.

Reads results/010-equity/*.json (produced by the `equityrun` bench binary) and
writes figures to papers/010-equity/figs/, headline macros to
papers/010-equity/numbers.tex, and markdown tables to papers/010-equity/tables/.
Skips any experiment whose results file is absent (e.g. E1 still running).
"""
import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = "results/010-equity"
FIGS = "papers/010-equity/figs"
TABLES = "papers/010-equity/tables"
NUMBERS = "papers/010-equity/numbers.tex"

# Quome-ish palette.
NAVY, TEAL, AMBER, RED, GREY = "#1b2a4a", "#2a9d8f", "#e9c46a", "#c1432f", "#9aa0a6"
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})

macros = {}


def load(name):
    p = os.path.join(R, name)
    return json.load(open(p)) if os.path.exists(p) else None


def pct(x):
    return f"{100 * x:.1f}\\%"


# --- E1: enforcement-parity audit ------------------------------------------
def fig_e1():
    d = load("e1_enforcement.json")
    if not d:
        print("E1: results absent, skipping fig1")
        return
    axes = d["per_axis"]
    # Max demographic-parity gap per axis (the headline disparity).
    rows = []
    for ax, body in axes.items():
        dpd = next((x for x in body["disparities"] if x["metric"] == "demographic_parity"), None)
        if dpd:
            rows.append((ax, dpd["gap"], dpd["ci_lo"], dpd["ci_hi"], dpd["p_value"]))
    rows.sort(key=lambda r: -r[1])
    names = [r[0] for r in rows]
    gaps = [r[1] for r in rows]
    err_lo = [max(0, r[1] - r[2]) for r in rows]
    err_hi = [max(0, r[3] - r[1]) for r in rows]
    colors = [RED if r[4] < 0.05 else GREY for r in rows]

    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    y = range(len(names))
    ax.barh(list(y), gaps, xerr=[err_lo, err_hi], color=colors, height=0.6,
            error_kw={"ecolor": "#333", "capsize": 3})
    ax.set_yticks(list(y))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("Max pairwise enforcement-rate disparity (deny+escalate)")
    ax.axvline(0.10, ls="--", color=NAVY, lw=1, label="alert bound (0.10)")
    ax.set_title("E1 · Gateway enforcement disparity on matched cases")
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig1_enforcement_parity.png"), dpi=160)
    plt.close(fig)

    worst = rows[0]
    macros["EoneWorstAxis"] = worst[0]
    macros["EoneWorstGap"] = pct(worst[1])
    macros["EoneOverallEnf"] = pct(d["overall_enforcement_rate"])
    sig = sum(1 for r in rows if r[4] < 0.05)
    macros["EoneSigAxes"] = str(sig)
    macros["EoneNumAxes"] = str(len(rows))
    macros["EoneModel"] = d["model"].replace("_", "\\_")
    macros["EoneN"] = str(d["n"])
    print(f"E1: worst axis {worst[0]} gap {worst[1]:.3f}; {sig}/{len(rows)} axes significant")


# --- E2: detection power ----------------------------------------------------
def fig_e2():
    d = load("e2_detection.json")
    if not d:
        return
    grid = d["grid"]
    ns = sorted({g["n_per_group"] for g in grid})
    deltas = sorted({g["delta"] for g in grid})
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    cmap = [NAVY, TEAL, AMBER, RED]
    for i, n in enumerate(ns):
        xs = [dl for dl in deltas]
        ys = [next(g["power"] for g in grid if g["n_per_group"] == n and abs(g["delta"] - dl) < 1e-9)
              for dl in deltas]
        ax.plot(xs, ys, "-o", color=cmap[i % len(cmap)], label=f"N/group = {n}", lw=1.8, ms=4)
    ax.axhline(0.90, ls="--", color=GREY, lw=1, label="90% power")
    ax.set_xlabel("Injected disparity magnitude δ")
    ax.set_ylabel("Detection power")
    ax.set_ylim(-0.03, 1.03)
    ax.set_title("E2 · Subgroup-monitor detection power")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig2_detection_power.png"), dpi=160)
    plt.close(fig)

    # Smallest δ reaching ≥90% power at N=200.
    n200 = [g for g in grid if g["n_per_group"] == 200]
    hit = sorted([g for g in n200 if g["power"] >= 0.90], key=lambda g: g["delta"])
    # Don't leave the providecommand default in place if 90% is never reached —
    # that would silently render a wrong "by δ=0.00" claim.
    macros["EtwoDeltaNinety"] = f"{hit[0]['delta']:.2f}" if hit else "$>$0.30 (not reached)"
    macros["EtwoMaxPower"] = pct(max(g["power"] for g in grid))
    print("E2: power curve written")


# --- E3: mitigation frontier ------------------------------------------------
def fig_e3():
    d = load("e3_mitigation.json")
    if not d:
        return
    arms = d["arms"]
    label = {"none": "none", "group_threshold": "group-thresh",
             "reject_option": "reject-opt", "equalized_odds": "eq-odds"}
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for a in arms:
        col = {"none": GREY, "group_threshold": TEAL,
               "reject_option": AMBER, "equalized_odds": NAVY}[a["arm"]]
        ax.scatter(a["max_disparity"], a["safety"], s=90, color=col, zorder=3)
        ax.annotate(label[a["arm"]], (a["max_disparity"], a["safety"]),
                    textcoords="offset points", xytext=(6, 4), fontsize=9)
    ax.axhline(0.98, ls="--", color=RED, lw=1, label="98% safety floor")
    ax.set_xlabel("Max enforcement disparity (lower = fairer)")
    ax.set_ylabel("Aggregate safety retained")
    ax.set_title("E3 · Mitigation frontier")
    ax.legend(fontsize=9, loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig3_mitigation_frontier.png"), dpi=160)
    plt.close(fig)

    none = next(a for a in arms if a["arm"] == "none")
    # Best = largest disparity reduction among arms that keep aggregate safety at or
    # above the 0.98 floor (so we don't trade fairness for safety loss).
    floor_ok = [a for a in arms if a["arm"] != "none" and a["safety"] >= 0.98]
    pool = floor_ok if floor_ok else [a for a in arms if a["arm"] != "none"]
    best = max(pool, key=lambda a: a["disparity_reduction"])
    macros["EthreeBaseDisp"] = pct(none["max_disparity"])
    macros["EthreeBestArm"] = label[best["arm"]]
    macros["EthreeBestReduction"] = pct(best["disparity_reduction"])
    macros["EthreeBestSafety"] = pct(best["safety"])
    macros["EthreeBestDisp"] = pct(best["max_disparity"])
    # write a small table
    lines = ["| arm | max disparity | reduction | safety | escalation |",
             "|---|---|---|---|---|"]
    for a in arms:
        lines.append(f"| {label[a['arm']]} | {a['max_disparity']:.3f} | "
                     f"{100*a['disparity_reduction']:.1f}% | {100*a['safety']:.1f}% | "
                     f"{100*a['escalation_rate']:.1f}% |")
    open(os.path.join(TABLES, "e3_mitigation.md"), "w").write("\n".join(lines) + "\n")
    print(f"E3: best arm {best['arm']} reduces disparity {100*best['disparity_reduction']:.1f}%")


# --- E4: vulnerable populations ---------------------------------------------
def fig_e4():
    d = load("e4_vulnerable.json")
    if not d:
        return
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    cats = ["default\nharm", "protective\nharm", "escalation\ncost"]
    vals = [d["default_harm_rate"], d["protective_harm_rate"], d["escalation_cost"]]
    ax.bar(cats, vals, color=[RED, TEAL, AMBER], width=0.6)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.02, f"{100*v:.0f}%", ha="center", fontsize=10)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Rate")
    ax.set_title("E4 · Vulnerable-population protection")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig4_vulnerable.png"), dpi=160)
    plt.close(fig)
    macros["EfourDefaultHarm"] = pct(d["default_harm_rate"])
    macros["EfourProtHarm"] = pct(d["protective_harm_rate"])
    macros["EfourEscCost"] = pct(d["escalation_cost"])
    print("E4: vulnerable fig written")


# --- E5: intersectional -----------------------------------------------------
def fig_e5():
    d = load("e5_intersectional.json")
    if not d:
        return
    pairs = d["pairs"]
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    labels, single_gaps, cell_gaps = [], [], []
    for pr in pairs:
        labels.append("×".join(pr["axes"]))
        single_gaps.append(max(s["gap"] for s in pr["single_axis"]))
        cell = next(c for c in pr["cells"] if c["is_disadvantaged"])
        cell_gaps.append(cell["gap"])
    x = range(len(labels))
    w = 0.36
    ax.bar([i - w / 2 for i in x], single_gaps, w, color=GREY, label="max single-axis audit")
    ax.bar([i + w / 2 for i in x], cell_gaps, w, color=RED, label="intersectional cell")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Enforcement-rate disparity")
    ax.set_title("E5 · Single-axis audits miss intersectional harm")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig5_intersectional.png"), dpi=160)
    plt.close(fig)
    # headline: ratio of intersectional to single-axis for the first pair
    macros["EfiveCellGap"] = pct(cell_gaps[0])
    macros["EfiveSingleGap"] = pct(single_gaps[0])
    detected = all(pr["intersectional_cell_detected"] for pr in pairs)
    single_sig = any(s["significant_raw"] for pr in pairs for s in pr["single_axis"])
    macros["EfiveDetected"] = "yes" if detected else "no"
    macros["EfiveSingleMiss"] = "no" if single_sig else "yes"
    print(f"E5: intersection cell {cell_gaps[0]:.3f} vs single-axis {single_gaps[0]:.3f}")


# --- E6: overhead -----------------------------------------------------------
def num_e6():
    d = load("e6_overhead.json")
    if not d:
        return
    macros["EsixPerRecordUs"] = f"{d['per_record_us']:.2f}"
    macros["EsixThroughput"] = f"{d['throughput_per_s']/1e6:.1f}M"
    macros["EsixRecords"] = f"{d['records']:,}".replace(",", "{,}")
    print("E6: overhead numbers written")


def _race_gap(d):
    """(gap, p, group_a, group_b) for the race demographic-parity disparity, or None."""
    body = d.get("per_axis", {}).get("race")
    if not body:
        return None
    dpd = next((x for x in body["disparities"] if x["metric"] == "demographic_parity"), None)
    return (dpd["gap"], dpd["p_value"], dpd["group_a"], dpd["group_b"]) if dpd else None


# --- Robustness: race enforcement gap across model families -----------------
def fig_robustness():
    syn, named = {}, {}
    for path in sorted(glob.glob(os.path.join(R, "models", "e1_synthetic_*.json"))):
        d = json.load(open(path))
        g = _race_gap(d)
        if g:
            syn[d["model"]] = (g[0], g[1])
    for path in sorted(glob.glob(os.path.join(R, "models", "e1_named_*.json"))):
        d = json.load(open(path))
        g = _race_gap(d)
        if g:
            named[d["model"]] = (g[0], g[1])
    if not syn:
        print("robustness: no per-model results, skipping fig6")
        return
    models = sorted(syn.keys())
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    x = range(len(models))
    w = 0.38
    syn_g = [syn[m][0] for m in models]
    syn_c = [RED if syn[m][1] < 0.05 else GREY for m in models]
    ax.bar([i - w / 2 for i in x], syn_g, w, color=syn_c, label="explicit-category")
    if named:
        nm_g = [named.get(m, (0, 1))[0] for m in models]
        nm_c = [NAVY if named.get(m, (0, 1))[1] < 0.05 else "#b9c0d4" for m in models]
        ax.bar([i + w / 2 for i in x], nm_g, w, color=nm_c, label="real names (no label)")
    ax.axhline(0.10, ls="--", color=NAVY, lw=1)
    ax.set_xticks(list(x))
    ax.set_xticklabels([m.replace(":", "\n") for m in models], fontsize=8)
    ax.set_ylabel("Race enforcement-rate gap")
    ax.set_title("Robustness · race enforcement disparity across model families")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig6_robustness.png"), dpi=160)
    plt.close(fig)

    macros["RobustNumModels"] = str(len(models))
    macros["RobustSynthSig"] = str(sum(1 for m in models if syn[m][1] < 0.05))
    macros["RobustSubstantial"] = str(sum(1 for m in models if syn[m][0] >= 0.15))
    macros["RobustEven"] = str(sum(1 for m in models if syn[m][0] < 0.03))
    gaps = [syn[m][0] for m in models]
    macros["RobustGapMin"] = pct(min(gaps))
    macros["RobustGapMax"] = pct(max(gaps))
    if named:
        macros["RobustNamedSig"] = str(sum(1 for m in models if named.get(m, (0, 1))[1] < 0.05))
        macros["RobustNamedModels"] = str(len(named))
    lines = ["| model | explicit-category race gap | p | real-name race gap | p |",
             "|---|---|---|---|---|"]
    for m in models:
        s = syn[m]
        nmv = named.get(m)
        ns = f"{nmv[0]:.3f} | {nmv[1]:.4f}" if nmv else "— | —"
        lines.append(f"| {m} | {s[0]:.3f} | {s[1]:.4f} | {ns} |")
    open(os.path.join(TABLES, "robustness.md"), "w").write("\n".join(lines) + "\n")
    print(f"robustness: {len(models)} models; "
          f"{sum(1 for m in models if syn[m][1] < 0.05)} explicit-significant")


# --- External validation: COMPAS --------------------------------------------
def fig_compas():
    d = load("ext_compas.json")
    if not d:
        return
    groups = d["groups"]
    order = sorted(groups, key=lambda g: -groups[g]["enforced"] / groups[g]["n"])
    rates = [groups[g]["enforced"] / groups[g]["n"] for g in order]
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    cols = [RED if g == "African-American" else GREY for g in order]
    ax.bar(range(len(order)), rates, color=cols, width=0.62)
    for i, r in enumerate(rates):
        ax.text(i, r + 0.01, f"{100*r:.0f}%", ha="center", fontsize=9)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([g.replace("-", "-\n") for g in order], fontsize=8)
    ax.set_ylabel("Labeled medium/high risk (restrictive)")
    ax.set_title("External · COMPAS racial disparity recovered by the monitor")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig7_compas.png"), dpi=160)
    plt.close(fig)

    dpd = next((x for x in d["disparities"] if x["metric"] == "demographic_parity"), None)
    eod = next((x for x in d["disparities"] if x["metric"] == "equalized_odds"), None)
    macros["CompasN"] = f"{d['n']:,}".replace(",", "{,}")
    if dpd:
        macros["CompasMaxGap"] = pct(dpd["gap"])
        macros["CompasMaxPair"] = f"{dpd['group_a']} vs.\\ {dpd['group_b']}"
    if eod:
        macros["CompasEOD"] = pct(eod["gap"])
    if "African-American" in groups and "Caucasian" in groups:
        aa = groups["African-American"]["enforced"] / groups["African-American"]["n"]
        ca = groups["Caucasian"]["enforced"] / groups["Caucasian"]["n"]
        macros["CompasAARate"] = pct(aa)
        macros["CompasCaucRate"] = pct(ca)
        macros["CompasAAGap"] = pct(aa - ca)
    print("COMPAS: external validation figure written")


def write_numbers():
    os.makedirs(os.path.dirname(NUMBERS), exist_ok=True)
    with open(NUMBERS, "w") as f:
        f.write("% Auto-generated by scripts/010-equity/summarize.py — do not edit.\n")
        f.write("% Core macros are \\providecommand'd in main.tex; override here.\n")
        for k, v in macros.items():
            f.write(f"\\renewcommand{{\\{k}}}{{{v}}}\n")
    print(f"wrote {NUMBERS} ({len(macros)} macros)")


def main():
    for d in (FIGS, TABLES):
        os.makedirs(d, exist_ok=True)
    fig_e1()
    fig_e2()
    fig_e3()
    fig_e4()
    fig_e5()
    num_e6()
    fig_robustness()
    fig_compas()
    write_numbers()


if __name__ == "__main__":
    main()
