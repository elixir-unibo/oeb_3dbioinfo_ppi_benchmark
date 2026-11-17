# Diagnostic: MOBI and Wolfson AUC discrepancy (published vs. this package)

Investigated at the user's request after Step 5c flagged MOBI (+0.109) and Wolfson (+0.157)
as outliers relative to the manuscript's Table 3.

## Ruled out
| hypothesis | result |
|---|---|
| Training-flag leakage (Training/TrainingColumn columns in MOBI_raw_scores.csv / classifier-data.csv) | held-out-only AUC is HIGHER, not lower (no leakage effect in this direction) |
| Gold-standard curation version (original vs. benchmark_annotated_updated_30042023.csv) | AUC still far above published on both versions |
| Ambiguous-entry inclusion (20 entries flagged "ambiguous") | negligible AUC change after dropping them |
| File version drift | MOBI_raw_scores.csv, classifier-data.csv, AUC_best_scores_participants.csv all added in the SAME commit (30ab243, 2023-05-03) -- no staleness |
| Population mismatch (MOBI vs Wolfson entry coverage) | identical 971-entry set for both |
| Fold-to-fold instability | cv_selected_std is low for both (MOBI 0.0151, Wolfson 0.0113) -- the gap is systematic, not noise |

## Finding: Wolfson's F_Network_full is a buried-surface-area proxy
F_Network_full (wrongly selected by the nested-CV script over the manuscript's published
I_Proba_Consensus) correlates at r=-0.77 with raw buried surface area (bsa). bsa ALONE, with
no classifier, already reaches AUC 0.62 on this dataset -- the benchmark's intended size-
matching between physio/non-physio classes did not fully eliminate residual size signal.
F_Network_full's high apparent AUC is substantially a rediscovery of this residual bsa signal,
plausibly why the manuscript's authors did not select it as Wolfson's representative score
even if it scores well algorithmically -- a domain judgment this package's generic
column-pooling script cannot replicate.

## Open / unresolved
Even isolating the manuscript's own published column per group (I_Proba_Consensus for
Wolfson, I_shape_hydro_tails for MOBI) and controlling for every variable above, this
package's AUC (0.82-0.85) remains well above the published value (0.71-0.72). This cannot be
closed from the public repository alone -- it would require the authors' actual fold
assignment (behind Figure S1, not published) or their analysis code. Reported as an open
discrepancy, not resolved.


## Follow-up: systematic test of the "Training column = train/test split" hypothesis

Tested across ALL 6 groups whose raw-score files carry a Training/TrainingColumn flag
(Bonvin, Zou, SWISS-MODEL, Bologna, MOBI, Wolfson), not just the two outliers, by comparing
full-dataset AUC vs. held-out-only (Training==False/0) AUC vs. flagged-subset-only AUC
(see qc_analysis/diagnostics/training_flag_hypothesis_test.csv).

**Result: refuted as a general explanation.**
- Only 2/6 groups (Bonvin, SWISS-MODEL) move even marginally closer to the published value when
  restricted to the held-out subset, and neither closes the gap (Bonvin 0.862 vs 0.85 published;
  SWISS-MODEL 0.825 vs 0.79).
- For the other 4 groups (Zou, Bologna, MOBI, Wolfson), held-out restriction moves away from or
  barely changes agreement with published.
- The flagged (Training=True/1) subset shows a HIGHER AUC than the held-out subset for Bonvin
  (0.988), Zou (0.962), and SWISS-MODEL (0.866) -- the opposite of what leakage-into-training
  would predict. Only MOBI (0.781) and Wolfson (0.818) show the flagged subset performing worse,
  consistent with it marking harder/calibration examples rather than leaked training examples --
  but even their held-out AUC (0.841, 0.849) remains far above the published value (0.72, 0.71).

Conclusion: the Training column does not function as a leakage-marking train/test split for
this task in this dataset, for any of the 6 groups that carry it. It does not explain the
MOBI/Wolfson discrepancy. That discrepancy remains open (see main finding above re:
F_Network_full / buried-surface-area correlation, which explains the nested-CV mis-selection
for Wolfson but not the residual gap on the manuscript's own published column).


## RESOLVED — superseded by entry_id matching bug fix (see README CRITICAL CORRECTION section)

**The MOBI and Wolfson discrepancies documented above were caused by a bug, not an unresolved
scientific puzzle.** All AUC values above were computed using the gold standard's bare `ID`
column for matching, which silently dropped ~700 ProtCID-derived entries (identified in group
files as `ID_InterfaceID`, e.g. `1a17_6`, but in the gold standard as bare `ID`, e.g. `1a17`).
Every AUC above was therefore computed on only ~971 of 1671 entries (the QSalign-derived
subset only).

After fixing entry_id construction to `f"{ID}_{int(InterfaceID)}"` for ProtCID-derived rows:

- MOBI (`I_shape_hydro_tails`), full 1671-entry population: **AUC = 0.7307** vs. published 0.72
  (abs diff 0.011) -- was 0.8268 (abs diff 0.109) on the buggy ~971-entry subset.
- Wolfson (`I_Proba_Consensus`), full 1671-entry population: **AUC = 0.7262** vs. published 0.71
  (abs diff 0.016) -- was 0.8442 (abs diff 0.157) on the buggy subset. Restricting further to
  the TrainingColumn==0 (test) subset under the corrected IDs gives **AUC = 0.7212**, an almost
  exact match.

The Training-flag hypothesis test below, and the F_Network_full/buried-surface-area finding,
were genuine observations on the (buggy) ~971-entry population and are retained for the audit
trail, but neither was the actual explanation -- the ID bug was. This file's title should be
read as historical; the live, corrected numbers are in
`qc_analysis/diagnostics/benchmark_summary_published_vs_recomputed.csv` and the datasets under `datasets/assessment/`.


## Correction: qc_analysis/diagnostics/training_flag_hypothesis_test.csv regenerated on corrected entry_id + fixed NaN handling

The version of this table referenced above was computed on the pre-fix ~971-entry population
AND had a bug counting `tflag != false_val` rows that were actually NaN (missing Training flag)
as "flagged/training" (e.g. Bonvin showed n_flagged=133 = 129 True + 4 NaN). Both are now fixed:
entry_id uses the corrected ID_InterfaceID composite, and rows with a missing Training flag are
dropped before computing held-out/flagged subsets (Bonvin n_flagged is now correctly 129).
See the regenerated qc_analysis/diagnostics/training_flag_hypothesis_test.csv for the corrected numbers. The qualitative
conclusion is unchanged: the Training flag does not behave as a leakage-marking split -- on the
corrected data, 4 of 6 groups (Bonvin, Zou, SWISS-MODEL, MOBI) show the flagged subset with a
HIGHER AUC than held-out (opposite of leakage inflation), and only Bologna and Wolfson show it
lower -- and it does not explain the MOBI/Wolfson gap -- the entry_id matching bug does (see
CRITICAL CORRECTION in README_STEP_BY_STEP.md).
