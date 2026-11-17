#!/usr/bin/env python3
"""
OpenEBench-style Step 2 (cross-validated variant): METRICS GENERATION WITH
HOMOLOGY-SAFE 5-FOLD CV.

The manuscript (Schweke et al., Results / "ROC-based approach", p.10) states:
"ROCs were computed from these scores using 5-fold cross validation to
select the best performing score for each group" -- i.e. in the manuscript,
the CV's role is per-group SCORE SELECTION among many candidate raw/
integrated columns. This script does NOT reproduce that selection
procedure. It implements a narrower, complementary check: held-out
AUC/accuracy for one already-fixed score column, using homology-safe folds
(see cv_fold_assignment.csv) to avoid sequence-identity leakage between
folds -- a question the manuscript does not itself report on, since it
does not document how its own folds were assigned.

Fold assignment (datasets/metrics_reference/cv_fold_assignment.csv) groups
entries by CATH superfamily (or UniProt gene when superfamily is missing,
or a per-entry singleton group otherwise) so that no two entries from the
same homology group land in different folds -- the manuscript does not
document how its own folds were built, so this is our own leakage control,
not a reproduction of an undisclosed procedure.

For each fold: the threshold farthest from the diagonal (Youden's J, same
convention as the manuscript) is computed on the OTHER 4 folds, then
applied to classify the held-out fold. AUC-ROC is computed per held-out
fold (threshold-free, so it is reported for completeness/variance even
though it is not affected by the threshold) and the headline numbers are
the **mean +/- std across the 5 held-out folds** -- the correct way to
report a cross-validated metric, instead of a single resubstitution AUC on
the full dataset (which is what plain `compute_metrics.py` does, and which
is the known source of the ranking disagreement with the manuscript's
Table 3 noted in this package's README).

Usage:
    python crossval_metrics.py --input predictions.csv \
        --goldstandard_dir metrics_reference/ --participant_id <tool_name> \
        --outdir crossval_out/
"""
import argparse, csv, json, os
import statistics as st

def auc_mannwhitney(y, s):
    pairs = sorted(zip(s, y))
    n = len(pairs)
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[k] = avg_rank
        i = j + 1
    n1 = sum(1 for _, lab in pairs if lab == 1)
    n0 = n - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    sum_ranks_pos = sum(r for (r, (_, lab)) in zip(ranks, pairs) if lab == 1)
    return (sum_ranks_pos - n1 * (n1 + 1) / 2) / (n1 * n0)

def youden_threshold(y, s):
    """Threshold farthest from the ROC diagonal (max TPR - FPR), as in the manuscript."""
    best_j, best_thr = -1, None
    for thr in sorted(set(s)):
        tp = sum(1 for yi, si in zip(y, s) if si >= thr and yi == 1)
        fn = sum(1 for yi, si in zip(y, s) if si < thr and yi == 1)
        fp = sum(1 for yi, si in zip(y, s) if si >= thr and yi == 0)
        tn = sum(1 for yi, si in zip(y, s) if si < thr and yi == 0)
        tpr = tp / (tp + fn) if (tp + fn) else 0.0
        fpr = fp / (fp + tn) if (fp + tn) else 0.0
        j = tpr - fpr
        if j > best_j:
            best_j, best_thr = j, thr
    return best_thr

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--goldstandard_dir", required=True)
    ap.add_argument("--participant_id", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    gold, fold_of = {}, {}
    with open(os.path.join(args.goldstandard_dir, "gold_standard_labels.csv")) as fh:
        for row in csv.DictReader(fh):
            gold[row["entry_id"]] = int(row["label"])
    with open(os.path.join(args.goldstandard_dir, "cv_fold_assignment.csv")) as fh:
        for row in csv.DictReader(fh):
            fold_of[row["entry_id"]] = int(row["fold"])

    entries, scores, labels, folds = [], [], [], []
    with open(args.input) as fh:
        for row in csv.DictReader(fh):
            eid = row["entry_id"]
            if eid in gold and eid in fold_of:
                entries.append(eid)
                scores.append(float(row.get("raw_score_oriented", row["raw_score"])))
                labels.append(gold[eid])
                folds.append(fold_of[eid])

    K = max(folds) + 1 if folds else 0
    fold_aucs, fold_accs = [], []
    for k in range(K):
        train_idx = [i for i in range(len(entries)) if folds[i] != k]
        test_idx  = [i for i in range(len(entries)) if folds[i] == k]
        if not train_idx or not test_idx:
            continue
        thr = youden_threshold([labels[i] for i in train_idx], [scores[i] for i in train_idx])
        test_y = [labels[i] for i in test_idx]
        test_s = [scores[i] for i in test_idx]
        fold_aucs.append(auc_mannwhitney(test_y, test_s))
        preds = [1 if s >= thr else 0 for s in test_s]
        fold_accs.append(sum(p == l for p, l in zip(preds, test_y)) / len(test_y))

    result = {
        "participant_id": args.participant_id,
        "n_entries": len(entries),
        "n_folds": K,
        "fold_auc": [round(a, 4) for a in fold_aucs],
        "fold_accuracy": [round(a, 4) for a in fold_accs],
        "cv_auc_mean": round(st.mean(fold_aucs), 4) if fold_aucs else None,
        "cv_auc_std": round(st.pstdev(fold_aucs), 4) if len(fold_aucs) > 1 else 0.0,
        "cv_accuracy_mean": round(st.mean(fold_accs), 4) if fold_accs else None,
        "cv_accuracy_std": round(st.pstdev(fold_accs), 4) if len(fold_accs) > 1 else 0.0,
        "resubstitution_auc_full_dataset": round(auc_mannwhitney(labels, scores), 4),
    }
    json.dump(result, open(os.path.join(args.outdir, "crossval_results.json"), "w"), indent=2)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
