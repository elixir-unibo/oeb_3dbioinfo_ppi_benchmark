#!/usr/bin/env python3
"""
Reconstruction of the manuscript's ACTUAL score-selection procedure (Schweke et al.,
Results / "ROC-based approach", p.10): "ROCs were computed from these scores using
5-fold cross validation to select the best performing score for each group."

IMPORTANT CAVEAT -- read before trusting these numbers:
The manuscript does NOT specify, anywhere in the main text, how its 5 folds were
constructed (random? stratified? homology-aware?), and no fold assignment file is
provided in the source repository. This script therefore uses THIS PACKAGE's own
homology-safe fold assignment (datasets/metrics_reference/cv_fold_assignment.csv,
built in Step 5b from CATH-superfamily / UniProt-gene grouping) -- it is our own
leakage-safe reconstruction of a plausible 5-fold split, NOT the manuscript's actual
split, which is not published. Results should therefore be read as "what a sound
leakage-safe nested-CV selection would give on this dataset", useful to check
whether CV-based score selection (rather than its absence) explains the discrepancy
between a naive single-fixed-score AUC and the manuscript's Table 3 -- not as an
exact reproduction of the manuscript's own numbers.

For each of the 13 groups: pool EVERY raw and integrated score column the group
submitted (across all its CSVs in groups/<group>/{results-raw,results-classifier,
data-raw}/), excluding analysis-only files (e.g. most_misclassified_structures.csv).
For each held-out fold: pick, among all candidate columns, the one with the highest
AUC on the 4 TRAINING folds only (orientation auto-picked to be >=0.5 on training
data), then evaluate that single selected column on the held-out fold. The reported
CV-selected AUC is the mean of the 5 held-out-fold AUCs (nested CV: selection never
sees the fold it is evaluated on).

Usage:
    python select_best_score_cv.py --group_dir groups/group_Bonvin \
        --goldstandard_dir metrics_reference/ --outdir cv_selection_out/
"""
import argparse, glob, json, os
import numpy as np
import pandas as pd

SKIP_FILES = {"most_misclassified_structures.csv"}
SKIP_SUBDIRS = {"imported", "data-unused", "analysis"}
ID_PATTERNS = ["pdb-id", "pdb_id", "pdb id", "pdb", "id", "#pdb-id", "code", "model", "file"]
EXCLUDE_COLS = {"training", "trainingcolumn", "source", "misclassification_ratio", "is_physiological"}

def auc_manual(y, s):
    order = np.argsort(s, kind="mergesort")
    s_sorted = s[order]
    n = len(s)
    ranks_sorted = np.empty(n)
    idx = 0
    while idx < n:
        j = idx
        while j + 1 < n and s_sorted[j + 1] == s_sorted[idx]:
            j += 1
        ranks_sorted[idx:j + 1] = (idx + 1 + j + 1) / 2.0
        idx = j + 1
    ranks = np.empty(n); ranks[order] = ranks_sorted
    n1 = np.sum(y == 1); n0 = np.sum(y == 0)
    if n1 == 0 or n0 == 0:
        return np.nan
    return (ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)

def load_group_table(group_dir):
    merged = None
    for sub in os.listdir(group_dir):
        subpath = os.path.join(group_dir, sub)
        if not os.path.isdir(subpath) or sub in SKIP_SUBDIRS:
            continue
        for f in glob.glob(os.path.join(subpath, "*.csv")):
            if os.path.basename(f) in SKIP_FILES:
                continue
            df = pd.read_csv(f)
            df.columns = [c.strip() for c in df.columns]
            cols_lower = {c.lower(): c for c in df.columns}
            idcol = next((cols_lower[p] for p in ID_PATTERNS if p in cols_lower), df.columns[0])
            cands = [c for c in df.columns if c != idcol and c.lower() not in EXCLUDE_COLS
                     and pd.api.types.is_numeric_dtype(df[c])]
            sub_df = df[[idcol] + cands].rename(columns={idcol: "entry_id"})
            sub_df["entry_id"] = sub_df["entry_id"].astype(str).str.replace(".pdb", "", regex=False).str.strip()
            fname = os.path.splitext(os.path.basename(f))[0]
            sub_df = sub_df.rename(columns={c: f"{fname}::{c}" for c in cands}).drop_duplicates("entry_id")
            merged = sub_df if merged is None else merged.merge(sub_df, on="entry_id", how="outer")
    return merged

def nested_cv_select(table, gold, folds, min_coverage=0.5):
    entries = table["entry_id"].values
    y_all = np.array([gold.get(e, np.nan) for e in entries])
    fold_all = np.array([folds.get(e, -1) for e in entries])
    valid = ~np.isnan(y_all) & (fold_all >= 0)
    table = table[valid].reset_index(drop=True)
    y_all = y_all[valid].astype(int)
    fold_all = fold_all[valid].astype(int)
    candidates = [c for c in table.columns if c != "entry_id"]
    K = fold_all.max() + 1

    fold_results = []
    for k in range(K):
        train_mask, test_mask = fold_all != k, fold_all == k
        best_col, best_train_auc, best_sign = None, -1, 1
        for c in candidates:
            v = table[c].values.astype(float)
            tr_valid = train_mask & ~np.isnan(v)
            if tr_valid.sum() < min_coverage * train_mask.sum():
                continue
            a = auc_manual(y_all[tr_valid], v[tr_valid])
            if np.isnan(a):
                continue
            sign = 1
            if a < 0.5:
                a, sign = 1 - a, -1
            if a > best_train_auc:
                best_train_auc, best_col, best_sign = a, c, sign
        if best_col is None:
            continue
        v = table[best_col].values.astype(float)
        te_valid = test_mask & ~np.isnan(v)
        if te_valid.sum() == 0:
            continue
        test_auc = auc_manual(y_all[te_valid], v[te_valid] * best_sign)
        fold_results.append({"fold": int(k), "selected_column": best_col, "sign": best_sign,
                              "train_auc": round(float(best_train_auc), 4),
                              "test_auc": round(float(test_auc), 4)})
    return fold_results

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group_dir", required=True)
    ap.add_argument("--goldstandard_dir", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    gold, folds = {}, {}
    gold_csv = pd.read_csv(os.path.join(args.goldstandard_dir, "gold_standard_labels.csv"))
    for _, row in gold_csv.iterrows():
        gold[row["entry_id"]] = int(row["label"])
    fold_csv = pd.read_csv(os.path.join(args.goldstandard_dir, "cv_fold_assignment.csv"))
    for _, row in fold_csv.iterrows():
        folds[row["entry_id"]] = int(row["fold"])

    table = load_group_table(args.group_dir)
    fold_results = nested_cv_select(table, gold, folds)
    test_aucs = [r["test_auc"] for r in fold_results]
    result = {
        "group_dir": args.group_dir,
        "n_candidates_considered": len([c for c in table.columns if c != "entry_id"]),
        "fold_results": fold_results,
        "cv_selected_auc_mean": round(float(np.mean(test_aucs)), 4) if test_aucs else None,
        "cv_selected_auc_std": round(float(np.std(test_aucs)), 4) if test_aucs else None,
        "caveat": ("Fold split is this package's own homology-safe reconstruction "
                   "(cv_fold_assignment.csv), NOT the manuscript's undisclosed split."),
    }
    json.dump(result, open(os.path.join(args.outdir, "cv_selection_results.json"), "w"), indent=2)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
