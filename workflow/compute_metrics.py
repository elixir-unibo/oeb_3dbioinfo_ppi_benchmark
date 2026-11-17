#!/usr/bin/env python3
"""
OpenEBench-style Step 2: METRICS GENERATION
Computes, for a participant's predictions against the gold-standard
(metrics_reference) labels:
  - AUC-ROC            (threshold-free ranking metric)
  - AUCPR              (threshold-free ranking metric, Average Precision)
  - Accuracy@threshold, Balanced Accuracy, F1 Score, MCC
    (threshold-based; use --threshold if the scoring function has a published
    decision threshold, otherwise the script falls back to the data-driven
    optimal threshold found via Youden's J statistic on this same data)

Usage:
    python compute_metrics.py --input predictions.csv --goldstandard_dir metrics_reference/ \
                               --community_id OEBC_3DBioinfo --challenges_ids PPI-PhysioClassification \
                               --participant_id <tool_name> --threshold <optional float> \
                               --outdir assessment_out/

If --threshold is omitted, the optimal threshold (Youden's J = max(TPR - FPR)
over all observed score cutpoints) is computed from the same scored population
and reported in the output alongside a flag marking it as data-driven rather
than published.
"""
import argparse, csv, json, os

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

def aucpr_average_precision(y, s):
    """Average Precision = AUCPR estimator used by scikit-learn: sum over
    thresholds of (Recall_k - Recall_{k-1}) * Precision_k, scanned from the
    highest score down."""
    order = sorted(range(len(s)), key=lambda i: -s[i])
    y_sorted = [y[i] for i in order]
    n_pos = sum(y_sorted)
    if n_pos == 0:
        return float("nan")
    tp = 0
    fp = 0
    prev_recall = 0.0
    ap = 0.0
    for lab in y_sorted:
        if lab == 1:
            tp += 1
        else:
            fp += 1
        precision = tp / (tp + fp)
        recall = tp / n_pos
        ap += precision * (recall - prev_recall)
        prev_recall = recall
    return ap

def confusion(y, preds):
    tp = sum(1 for p, l in zip(preds, y) if p == 1 and l == 1)
    tn = sum(1 for p, l in zip(preds, y) if p == 0 and l == 0)
    fp = sum(1 for p, l in zip(preds, y) if p == 1 and l == 0)
    fn = sum(1 for p, l in zip(preds, y) if p == 0 and l == 1)
    return tp, tn, fp, fn

def balanced_accuracy(tp, tn, fp, fn):
    tpr = tp / (tp + fn) if (tp + fn) else float("nan")
    tnr = tn / (tn + fp) if (tn + fp) else float("nan")
    return (tpr + tnr) / 2

def f1_score_(tp, fp, fn):
    denom = 2 * tp + fp + fn
    return (2 * tp / denom) if denom else float("nan")

def mcc_score(tp, tn, fp, fn):
    denom = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
    return ((tp * tn - fp * fn) / denom) if denom else float("nan")

def youden_optimal_threshold(y, s):
    """Scan every observed score as a candidate cutpoint (s >= thr => positive)
    and return the one maximizing Youden's J = TPR - FPR."""
    candidates = sorted(set(s))
    best_j, best_thr = -1.0, candidates[0]
    for thr in candidates:
        preds = [1 if v >= thr else 0 for v in s]
        tp, tn, fp, fn = confusion(y, preds)
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
    ap.add_argument("--community_id", required=True)
    ap.add_argument("--challenges_ids", required=True)
    ap.add_argument("--participant_id", required=True)
    ap.add_argument("--threshold", type=float, default=None)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    gold = {}
    with open(os.path.join(args.goldstandard_dir, "gold_standard_labels.csv")) as fh:
        for row in csv.DictReader(fh):
            gold[row["entry_id"]] = int(row["label"])

    entries, scores, labels = [], [], []
    with open(args.input) as fh:
        for row in csv.DictReader(fh):
            eid = row["entry_id"]
            if eid in gold:
                entries.append(eid)
                scores.append(float(row.get("raw_score_oriented", row["raw_score"])))
                labels.append(gold[eid])

    auc = auc_mannwhitney(labels, scores)
    aucpr = aucpr_average_precision(labels, scores)
    result = {
        "community_id": args.community_id,
        "challenges_ids": args.challenges_ids,
        "participant_id": args.participant_id,
        "n_entries": len(entries),
        "metrics": {"AUC-ROC": round(auc, 4), "AUCPR": round(aucpr, 4)},
    }

    if args.threshold is not None:
        thr = args.threshold
        threshold_source = "published"
    else:
        thr = youden_optimal_threshold(labels, scores)
        threshold_source = "data-driven optimal (Youden's J)"

    preds = [1 if s >= thr else 0 for s in scores]
    tp, tn, fp, fn = confusion(labels, preds)
    acc = sum(p == l for p, l in zip(preds, labels)) / len(labels)
    result["threshold_used"] = round(thr, 6)
    result["threshold_source"] = threshold_source
    result["metrics"]["Accuracy@threshold"] = round(acc, 4)
    result["metrics"]["BalancedAccuracy"] = round(balanced_accuracy(tp, tn, fp, fn), 4)
    result["metrics"]["F1"] = round(f1_score_(tp, fp, fn), 4)
    result["metrics"]["MCC"] = round(mcc_score(tp, tn, fp, fn), 4)

    json.dump(result, open(os.path.join(args.outdir, "assessment_results.json"), "w"), indent=2)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
