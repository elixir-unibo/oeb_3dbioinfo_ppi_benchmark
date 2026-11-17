#!/usr/bin/env python3
"""
Dependency-free, leakage-safe cross-validated evaluation engine, shared by:
  - crossval_metrics.py (CLI, single participant, single strategy)
  - the local visualizer's upload-and-compare feature
    (serve_local_openebench_visualizer.py)

For each of the K folds of a chosen homology-safe CV splitting strategy
(see CV_SPLITTING_STRATEGIES.md -- Strategy 1 CATH/gene, Strategy 2 own
MMseqs2, Strategy 2b authoritative blastclust reference, Strategy 3
combined-union [recommended]):
  - the decision threshold for the 3 threshold-based metrics (Balanced
    Accuracy, F1, MCC -- and Accuracy for backward compatibility) is learned
    from the OTHER K-1 folds only, by maximizing Youden's J statistic
    (TPR - FPR) -- never from the held-out fold itself;
  - AUROC and AUCPR are threshold-free and are computed directly on the
    held-out fold.
This is applied identically to every participant, old or newly uploaded, so
cross-validated numbers are directly comparable.

No participant's *published* threshold is used here on purpose: mixing a
globally fixed published threshold for some tools with a data-driven one for
others (including any newly uploaded tool, which has no published threshold)
would make the comparison apples-to-oranges. The resubstitution metrics in
qc_analysis/diagnostics/benchmark_summary_published_vs_recomputed.csv (which DO use published
thresholds) remain the correct place to compare against the manuscript.
"""
import csv
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


def aucpr_average_precision(y, s):
    order = sorted(range(len(s)), key=lambda i: -s[i])
    y_sorted = [y[i] for i in order]
    n_pos = sum(y_sorted)
    if n_pos == 0:
        return float("nan")
    tp = fp = 0
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


def youden_threshold(y, s):
    best_j, best_thr = -1.0, sorted(s)[0]
    for thr in sorted(set(s)):
        preds = [1 if v >= thr else 0 for v in s]
        tp, tn, fp, fn = confusion(y, preds)
        tpr = tp / (tp + fn) if (tp + fn) else 0.0
        fpr = fp / (fp + tn) if (fp + tn) else 0.0
        j = tpr - fpr
        if j > best_j:
            best_j, best_thr = j, thr
    return best_thr


def load_gold_standard(path):
    gold = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            gold[row["entry_id"]] = int(row["label"])
    return gold


def load_fold_assignment(path):
    fold_of = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            fold_of[row["entry_id"]] = int(row["fold"])
    return fold_of


def load_predictions(path):
    """Returns {entry_id: oriented_score}. Accepts either a
    `raw_score_oriented` column (package convention) or a plain `score`
    column (expected to already be oriented so that higher = more
    physiological)."""
    scores = {}
    with open(path) as fh:
        reader = csv.DictReader(fh)
        cols = reader.fieldnames or []
        score_col = None
        for cand in ("raw_score_oriented", "score", "raw_score"):
            if cand in cols:
                score_col = cand
                break
        if score_col is None:
            raise ValueError(
                "predictions file must have an 'entry_id' column and a score "
                "column named 'raw_score_oriented', 'score', or 'raw_score'"
            )
        for row in reader:
            eid = row.get("entry_id")
            val = row.get(score_col)
            if eid and val not in (None, ""):
                try:
                    scores[eid] = float(val)
                except ValueError:
                    continue
    return scores


def cross_validate(scores, gold, fold_of):
    """scores: {entry_id: oriented_score}. Returns a result dict with
    per-fold and mean+/-std metrics, using only entries present in all three
    of scores/gold/fold_of."""
    entries = [e for e in scores if e in gold and e in fold_of]
    if not entries:
        return {"error": "no overlapping entries between predictions, gold standard and fold assignment", "n_entries": 0}

    labels = {e: gold[e] for e in entries}
    folds = {e: fold_of[e] for e in entries}
    K = max(folds.values()) + 1

    per_fold = []
    for k in range(K):
        train = [e for e in entries if folds[e] != k]
        test = [e for e in entries if folds[e] == k]
        if not train or not test:
            continue
        train_y = [labels[e] for e in train]
        train_s = [scores[e] for e in train]
        test_y = [labels[e] for e in test]
        test_s = [scores[e] for e in test]
        if len(set(test_y)) < 2:
            # fold has only one class present in the held-out set -- AUC/AUCPR undefined
            auc = float("nan")
            aucpr = float("nan")
        else:
            auc = auc_mannwhitney(test_y, test_s)
            aucpr = aucpr_average_precision(test_y, test_s)
        thr = youden_threshold(train_y, train_s)
        preds = [1 if s >= thr else 0 for s in test_s]
        tp, tn, fp, fn = confusion(test_y, preds)
        acc = sum(p == l for p, l in zip(preds, test_y)) / len(test_y)
        per_fold.append({
            "fold": k, "n_test": len(test), "threshold": round(thr, 6),
            "auroc": None if auc != auc else round(auc, 4),
            "aucpr": None if aucpr != aucpr else round(aucpr, 4),
            "accuracy": round(acc, 4),
            "balanced_accuracy": round(balanced_accuracy(tp, tn, fp, fn), 4),
            "f1": round(f1_score_(tp, fp, fn), 4),
            "mcc": round(mcc_score(tp, tn, fp, fn), 4),
        })

    def agg(key):
        vals = [f[key] for f in per_fold if f[key] is not None]
        if not vals:
            return None, None
        mean = st.mean(vals)
        sd = st.pstdev(vals) if len(vals) > 1 else 0.0
        return round(mean, 4), round(sd, 4)

    result = {"n_entries": len(entries), "n_folds": K, "per_fold": per_fold}
    for key in ("auroc", "aucpr", "accuracy", "balanced_accuracy", "f1", "mcc"):
        mean, sd = agg(key)
        result[f"cv_{key}_mean"] = mean
        result[f"cv_{key}_std"] = sd
    return result
