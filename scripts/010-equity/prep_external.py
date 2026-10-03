#!/usr/bin/env python3
# Copyright 2026 Quome. Licensed under the Apache License, Version 2.0.
"""Fetch + convert an EXTERNAL public fairness dataset into the group-labeled
decision stream the equity `StreamingMonitor` consumes, so we can validate that
our monitor recovers a documented real-world disparity on real decisions (not
just synthetic injected ones).

Dataset: ProPublica COMPAS ("compas-scores-two-years.csv"), the recidivism
risk-score audit that found Black defendants are labeled higher-risk than white
defendants at equal reoffense rates (Angwin et al., ProPublica 2016).

Mapping to our schema (one decision per defendant):
  group  = {"race": <race>}
  action = "deny"  if the tool labeled the defendant Medium/High risk  (restrictive)
           "allow" if Low risk
  label  = two_year_recid (1 = did reoffend — the fair "should-restrict" ground truth)
  score  = decile_score / 10   (for threshold-sweep / calibration parity)

We apply ProPublica's standard quality filters. Output JSONL is what
`equityrun ext` reads.
"""
import csv
import io
import json
import os
import urllib.request

URL = ("https://raw.githubusercontent.com/propublica/compas-analysis/"
       "master/compas-scores-two-years.csv")
OUT_DIR = os.path.join("datasets", "010-equity", "external")
OUT = os.path.join(OUT_DIR, "compas.jsonl")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"downloading {URL} ...")
    raw = urllib.request.urlopen(URL, timeout=30).read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(raw))

    n_in = n_out = 0
    by_race = {}
    with open(OUT, "w") as f:
        for row in reader:
            n_in += 1
            # ProPublica's standard filters for a clean two-year cohort.
            try:
                days = int(row["days_b_screening_arrest"])
            except (ValueError, KeyError):
                continue
            if not (-30 <= days <= 30):
                continue
            if row.get("is_recid") == "-1":
                continue
            if row.get("c_charge_degree") == "O":
                continue
            score_text = row.get("score_text", "N/A")
            if score_text == "N/A" or not score_text:
                continue

            race = row.get("race", "Other")
            recid = row.get("two_year_recid", "0") == "1"
            try:
                decile = int(row["decile_score"])
            except (ValueError, KeyError):
                continue
            # Restrictive ("deny") = Medium or High risk label.
            action = "deny" if score_text in ("Medium", "High") else "allow"

            rec = {
                "case_id": f"compas-{n_out}",
                "group": {"race": race},
                "action": action,
                "label": recid,
                "score": round(decile / 10.0, 3),
            }
            f.write(json.dumps(rec) + "\n")
            n_out += 1
            by_race[race] = by_race.get(race, 0) + 1

    print(f"kept {n_out}/{n_in} rows -> {OUT}")
    for r, c in sorted(by_race.items(), key=lambda kv: -kv[1]):
        print(f"  {r:18s} {c}")


if __name__ == "__main__":
    main()
