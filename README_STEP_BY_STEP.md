# From the Elixir-3DBioInfo PPI benchmark repository to an OpenEBench-compliant benchmarking workflow

Source data: https://github.com/vibbits/Elixir-3DBioInfo-Benchmark-Protein-Interfaces
(preprint: doi:10.22541/au.167569565.51141128/v1)

OpenEBench Scientific Benchmarking Data Model (v1.0.x) used as the target schema:
https://github.com/inab/benchmarking-data-model, docs at https://openebench.readthedocs.io

This package was generated programmatically from the files actually present in the source
repository (no synthetic data). Every number in `qc_analysis/diagnostics/benchmark_summary_published_vs_recomputed.csv`
and every JSON file under `metadata/` and `datasets/` was produced by parsing the repository's
own CSVs. All numbered steps below are exactly the steps a maintainer would repeat to update or
extend this benchmarking event.

--------------------------------------------------------------------------------------------
# CRITICAL CORRECTION — entry_id matching bug (fixed)

**Root cause found and fixed.** Every AUC computed earlier in this package's development
(Steps 4, 5b, 5c, and the MOBI/Wolfson diagnostics) used the gold standard's bare `ID` column
to match entries across group score files. This is WRONG for ProtCID-derived complexes: the
gold standard's `ID` column for these entries is just the 4-letter PDB code (e.g. `1a17`),
while every group's own score files identify the same entries as `ID_InterfaceID`
(e.g. `1a17_6`), using the `InterfaceID` column already present in
`benchmark_annotated.csv`. The naive match therefore silently found zero overlap for ~700 of
1671 entries (the entire ProtCID/"Dunbrack" half of the benchmark) and every AUC in this
package up to this point was computed on only the ~971-entry QSalign-derived subset, not the
full 1671-entry benchmark the manuscript reports on.

**Fix**: entry_id is now built as `f"{ID}_{int(InterfaceID)}"` when `InterfaceID` is present
(ProtCID-derived rows), and `ID` unchanged otherwise (QSalign-derived rows, which already
carry a `_N` suffix). This also resolves, as a side effect, the earlier-flagged "27 duplicate
ID" data-quality issue (Step 1 of this README) -- those were exactly the ProtCID rows whose
bare ID collided before adding the InterfaceID suffix.

**Effect**: recomputing a PLAIN, non-cross-validated, single-fixed-column AUC per participant
on the corrected full 1671-entry population brings the package into close agreement with the
manuscript's published Table 3 for 12 of 13 groups, with mean |AUC difference| = 0.0119
(was 0.14 with the bug, and 0.043 after the elaborate nested-CV score-selection reconstruction
in Step 5c -- which was solving the wrong problem):

| group | published | corrected (fixed ID, full population) | abs diff |
|---|---|---|---|
| RF (221 features) | 0.94 | 0.947 | 0.007 |
| Bonvin (DeepRank-GNN) | 0.85 | 0.860 | 0.010 |
| Furman | 0.84 | 0.849 | 0.009 |
| Venclovas | 0.82 | 0.807 | 0.013 |
| Zou | 0.81 | 0.817 | 0.007 |
| Guerois | 0.81 | 0.821 | 0.011 |
| Fernandez-Recio | 0.79 | 0.791 | 0.001 |
| SWISS-MODEL | 0.79 | 0.808 | 0.018 |
| Bologna | 0.76 | 0.769 | 0.009 |
| Kihara | 0.75 | 0.754 | 0.004 |
| Oliva | 0.75 | 0.749 | 0.001 |
| MOBI | 0.72 | 0.731 | 0.011 |
| Wolfson | 0.71 | 0.726 | 0.016 |
| **Correia** | 0.75 | 0.800 | **0.050 (residual, see below)** |

**Correia remains the one unresolved case**, and for a different reason: its own score file
covers only 947 of 1671 entries after fixing the ID match (vs. 1671 for most other groups),
suggesting MaSIF genuinely failed to compute a score for a large fraction of structures
(likely surface-computation failures), not an ID-matching artifact. This is a real data-
coverage gap, not a bug in this package's matching logic.

**Consequence for earlier sections of this README**: Steps 4.4, 5b, 5c, and
qc_analysis/diagnostics/MOBI_WOLFSON_DISCREPANCY_DIAGNOSTIC.md / qc_analysis/diagnostics/training_flag_hypothesis_test.csv were all computed
on the BUGGY ~971-entry population and their specific numeric conclusions (e.g. "mean abs
diff 0.043 via nested CV", the Training-flag test table, the F_Network_full/bsa-correlation
finding) are retained below for transparency and audit trail, but are SUPERSEDED by this
correction for any question about why recomputed AUC differs from published -- the dominant
answer is this ID-matching bug, not cross-validation methodology, score selection, or
Training-flag semantics. The CV infrastructure (Step 5b/5c scripts) remains correct and
useful, but should be re-run on the corrected `cv_fold_assignment.csv` and
`gold_standard_labels.csv` (already updated in this version of the package) for any future
work -- the nested-CV score-selection results in `qc_analysis/superseded/cv_score_selection_vs_published.csv` were
NOT regenerated in this pass and still reflect the buggy ID matching.

---------------------------------------------------------------------------------------------

## Step 0 — Inventory the source repository and decide the OEB entity mapping

1.1  Clone the repo and list its 5 top-level folders: `benchmark/` (structures + annotation),
     `groups/` (13 participating groups' raw/classifier scores), `AlphaFold_models/`
     (AF-multimer models + DockQ), `random_forest_analysis/` (consensus RF classifier),
     `ROC_analysis/` (published AUCs / best score per group).

1.2  Map the repository onto the OpenEBench concepts (`technical_references/1_scientific_data_model`):
     - **Community**            -> ELIXIR 3D-BioInfo Community (`metadata/Community.json`)
     - **BenchmarkingEvent**    -> "PPI physiological-interface benchmark 2023" (`metadata/BenchmarkingEvent.json`)
     - **Challenge**            -> a single challenge "PPI-PhysioClassification": classify each
       homodimer interface as physiological vs. crystallographic (`metadata/Challenges/`)
     - **Metrics**              -> AUC-ROC, Accuracy-at-threshold (assessment), and a leaderboard
       aggregation metric (`metadata/Metrics/`)
     - **Tool**                 -> one Tool per scoring function evaluated (14 total: 13 groups'
       best-performing score + the cross-validated Random-Forest consensus) plus 3 utility tools
       that implement the metrics/aggregation steps (`metadata/Tools/`)
     - **Dataset** (7 types)    -> input, public_reference, metrics_reference, participant,
       assessment, aggregation (community/event metadata lives in the files above)

1.3  Decide what is public vs. restricted: structures and the list of valid entry IDs are
     `public`; the physiological/non-physiological **label** is kept at `challenge` visibility
     (it is the gold standard participants must not see before scoring).

--------------------------------------------------------------------------------------------
## Step 1 — Build the gold-standard (ground truth) table

2.1  Load `benchmark/benchmark_annotated_updated_30042023.csv` — the manually-curated version of
     the benchmark (6 ambiguous entries flagged "to delete" are dropped, giving 1671 entries;
     840 physiological / 831 non-physiological).

2.2  **Known data-quality caveat (document for future curators):** the `ID` column alone is
     **not globally unique**. For complexes derived from ProtCID, several distinct interfaces of
     the same PDB entry can share the same 4-letter `ID` and are disambiguated only by the
     `InterfaceID` / `AuthChain1` / `AuthChain2` / `SymmetryOp1` / `SymmetryOp2` columns (27 such
     duplicate `ID`s were found, all non-physiological crystal-packing contacts). A production
     OpenEBench submission should mint a composite `entry_id` (e.g. `ID_InterfaceID`) before
     publishing the public_reference / gold-standard datasets; this package kept the plain `ID`
     for the demonstration and flags the 27 colliding rows in the inventory.

2.3  Output: `datasets/metrics_reference/gold_standard_labels.csv` (entry_id, label) and its
     metadata record `Dataset_metrics_reference.json` (`type: metrics_reference`,
     `visibility: challenge`).

--------------------------------------------------------------------------------------------
## Step 2 — Build the input and public_reference datasets

3.1  `datasets/input/benchmark_entries_manifest.csv`: the 1671 entries with their *non-label*
     structural metadata (gene, CATH superfamily, Pfam, buried-surface-area features) — this is
     what participants are given, together with the PDB/mmCIF coordinate files already present
     in `benchmark/benchmark_pdb_format/` and `benchmark/benchmark_mmcif_format/` (referenced by
     URI rather than re-hosted). Metadata: `Dataset_input.json` (`type: input`).

3.2  `datasets/public_reference/public_reference_ids.csv`: the list of valid entry identifiers,
     used by the validation container to check a submission's coverage/format. Metadata:
     `Dataset_public_reference.json` (`type: public_reference`).

--------------------------------------------------------------------------------------------
## Step 3 — Turn each group's raw-score CSV into a standardized participant dataset

4.1  Inventory every `results-raw/`, `results-classifier/` and `data-raw/` CSV under `groups/*`
     (23 files from 13 groups), skipping the `imported/` subfolders (those are copies of other
     groups' files bundled for a group's own correlation analysis, not original predictions).

4.2  For each of the 13 groups, take the single scoring function already identified by the
     repository's own analysis as the group's best performer
     (`ROC_analysis/AUC_best_scores_participants.csv`), plus the cross-validated Random-Forest
     consensus classifier (`random_forest_analysis/rf_topk221.out`) as a 14th participant — 14
     Tools total. (Each raw file in fact contains many more individual scoring functions — up to
     252 across the whole repository per the paper — so this is a representative subset; the
     same extraction procedure in step 4.3 generalizes column-by-column to all of them.)

4.3  For every participant: read the (`id_column`, `score_column`) pair out of its native CSV,
     auto-orient the sign of the score so that higher = "more physiological" (chosen empirically
     per column against the gold standard, since raw sign conventions differ — e.g. binding
     energies are more negative for stable/physiological interfaces), and write a standardized
     two-column `predictions.csv` (`entry_id,raw_score[,raw_score_oriented]`) under
     `datasets/participant/<participant_id>/`, together with a `Tool_<participant_id>.json` and
     a `Dataset_participant_<participant_id>.json` (`type: participant`,
     `depends_on.tool_id`, `depends_on.rel_dataset_ids -> input dataset`).

4.4  QC note kept in the package (`qc_analysis/diagnostics/benchmark_summary_published_vs_recomputed.csv`, now with
     `published_rank` / `recomputed_rank` columns): the AUC-ROC recomputed directly from each
     `predictions.csv` against the gold standard is numerically close to the value published in
     `ROC_analysis/AUC_best_scores_participants.csv` for some participants (e.g. Bonvin 0.878
     vs. 0.85 published, Furman 0.835 vs. 0.84, Venclovas 0.817 vs. 0.82), but the **ranking is
     not preserved**: RF_Consensus_top221 drops from published rank 1 (AUC 0.94) to a tie for
     rank 1 on recomputed AUC (0.878) only by coincidence, Wolfson_ProbaConsensus jumps from
     published rank 14 (AUC 0.71) to recomputed rank 4 (0.844), Guerois_IESnorm rises from rank
     5 to rank 3, and Fernandez-Recio_NIPacking falls from rank 7 (AUC 0.79) to last place
     (0.567). **This package's recomputed leaderboard should therefore be read as an independent
     QC/reproduction check, not as a reproduction of the manuscript's published ranking** — the
     two disagree substantially for several participants, most likely because the published
     figures were computed on the pre-curation `benchmark_annotated.csv` and/or a
     `Training`-flag-filtered subset and possibly different sign/threshold conventions per raw
     feature, while this package recomputes on the fully-curated 1671-entry set with an
     automatically chosen score orientation. Both numbers (`published_value` and recomputed
     `value`) are kept side by side in every `assessment` dataset's `datalink.inline_data` for
     traceability, and `published_rank`/`recomputed_rank` make the reordering explicit rather
     than asserting agreement.

4.5  **Venclovas_Voronota has no published classification threshold** in
     `ROC_analysis/AUC_best_scores_participants.csv` (only AUC is reported for that row). Its
     Accuracy-at-threshold assessment dataset therefore uses a **data-driven threshold** chosen
     by maximizing Youden's J statistic on this benchmark (`threshold_source:
     "data_driven_youden_j"` in `Dataset_assessment_ACC_Venclovas_Voronota.json`), unlike the
     other 13 participants whose thresholds are taken directly from the repository. This is
     flagged explicitly in that dataset's `description` field and in the summary CSV's
     `threshold_source` column, and Venclovas is included with all other 14 participants in the
     final aggregation dataset and leaderboard.

--------------------------------------------------------------------------------------------
## Step 4 — Define Challenge, Metrics and the 3-container benchmarking workflow

5.1  `metadata/Challenges/Challenge_PPI-PhysioClassification.json` lists two `assessment`
     metrics (AUC-ROC, Accuracy-at-threshold) and one `aggregation` metric, each bound to a
     "Tool" that performs the computation (`compute_AUC`, `compute_ACC`, `aggregate_benchmark`),
     mirroring the published TCGA example 1:1.

5.2  Implement the three OpenEBench container steps as standalone, Docker-able CLI scripts
     (`workflow/validate.py`, `workflow/compute_metrics.py`, `workflow/consolidate.py`):
     - `validate.py` checks a submitted `predictions.csv` covers the `public_reference` entry
       list and has the required columns -> `validation_result.json`.
     - `compute_metrics.py` computes AUC-ROC (Mann-Whitney U, dependency-free) and, if a
       threshold is supplied, Accuracy, against `gold_standard_labels.csv` ->
       `assessment_results.json`.
     - `consolidate.py` merges every participant's `assessment_results.json` into one
       `aggregation` Dataset instance (`data_model_export.json`) plus a leaderboard scatter
       plot (`leaderboard.svg`), exactly the two outputs OpenEBench expects
       (`outdir` + `data_model_export_dir`).

5.3  `workflow/nextflow_main.nf` wraps the same three scripts as Nextflow processes
     (VALIDATE -> COMPUTE_METRICS -> CONSOLIDATE), matching the structure of the reference
     implementation at https://github.com/inab/TCGA_benchmarking_workflow, so the pipeline can
     later be containerized per-step (one Dockerfile per process) as required before submission
     to OpenEBench support.

5.4  `workflow/run_pipeline.sh` is a plain-bash/Python smoke test that runs all three steps for
     every one of the 14 participants without Nextflow/Docker, for fast local iteration.

--------------------------------------------------------------------------------------------
## Step 5 — Run the pipeline end-to-end and build the aggregation / leaderboard dataset

6.1  The full validate -> compute_metrics -> consolidate sequence (the logic in
     `workflow/run_pipeline.sh`) was run for all 14 participants in this session, each producing
     a `validation_result.json` and an `assessment_results.json` containing both AUC-ROC and
     Accuracy@threshold (Venclovas included, using its data-driven threshold — see 4.5), then
     one consolidated `consolidated/data_model_export.json` + `consolidated/leaderboard.svg`
     covering all 14 participants with no missing points.

6.2  The same numbers were also written as individual OEB Dataset instances for traceability:
     `datasets/assessment/Dataset_assessment_AUC_<participant>.json`,
     `datasets/assessment/Dataset_assessment_ACC_<participant>.json`, and one
     `datasets/aggregation/Dataset_aggregation_PPI-PhysioClassification.json` (a `2D-plot` of
     AUC-ROC vs. Accuracy per participant, following the exact `visualization` block used in the
     TCGA prototype data).

--------------------------------------------------------------------------------------------
## Step 5b — Homology-safe 5-fold cross-validation (independent check, not a reproduction of the manuscript's CV)

The manuscript states (Results, "ROC-based approach" section, p.10): "ROCs were computed from
these scores using 5-fold cross validation **to select the best performing score for each
group**" — i.e. the CV's actual purpose is per-group **feature/score selection** among many
candidate raw/integrated columns (up to 221 raw scores across groups), not merely computing a
held-out AUC for an already-fixed single score. It does **not** document how folds were
assigned, and no sequence-identity-based split is provided anywhere in the repository or the
manuscript (checked: no mention of homology-aware CV, redundancy removal, or an explicit
sequence-identity threshold for fold construction).

**`crossval_metrics.py` below does NOT reproduce that selection procedure.** It only computes
a held-out AUC/accuracy for one already-fixed score column per participant, using our own
homology-safe folds. This is a useful independent leakage check, not a reproduction of the
manuscript's CV-based score-selection step — see Finding 5b.4, which this script's result
directly supports.

5b.1  Since no FASTA/sequence-identity clustering was available in the repository, folds were
      built from the structural-homology annotations already present in
      `benchmark_annotated.csv`: each entry is grouped by **CATH superfamily** (the closest
      available proxy for structural/sequence homology), falling back to **UniProt gene id**
      when the superfamily is missing, and to a per-entry singleton group otherwise. 852 groups
      were found for 1671 entries; 1000 entries (60%) share a CATH superfamily with at least
      one other entry, confirming that a naive random split would leak homologous dimers across
      folds for the majority of the dataset.

5b.2  A greedy stratified-group-5-fold assignment (`datasets/metrics_reference/
      cv_fold_assignment.csv`) places every entry of a group in the same fold while balancing
      fold size and physiological/non-physiological ratio (verified: 48.8%-51.2% physiological
      per fold, **zero groups span more than one fold**).

5b.3  `workflow/crossval_metrics.py` does NOT reproduce the manuscript's per-group score-selection
      CV (that would require re-running the comparison across every candidate raw/integrated
      column per group, within each fold). It implements a simpler, complementary check: for an
      already-fixed score column, the Youden's-J threshold is computed on 4 training folds only,
      then applied to the held-out fold; AUC-ROC and accuracy are reported as **mean +/- std
      across the 5 folds**, instead of the single full-dataset ("resubstitution") AUC that
      `compute_metrics.py` computes. This isolates one question only: does this package's
      full-dataset AUC change once homology-safe held-out evaluation is used?

5b.4  **Finding, saved to `qc_analysis/superseded/cv_vs_resubstitution_auc.csv`**: for all 14 participants, the
      cross-validated AUC is nearly identical to the resubstitution AUC (e.g. Bonvin 0.8796 CV
      vs. 0.8779 resubstitution; Fernandez-Recio 0.5716 CV vs. 0.5675 resubstitution) — because
      AUC-ROC is a threshold-free, rank-based statistic, and this package already uses each
      group's single pre-identified best-performing raw column rather than re-selecting the
      best feature from many candidates per fold. **This means the large reordering relative to
      the manuscript's published ranking (Step 4.4) is NOT caused by missing cross-validation**;
      it most likely stems from (a) evaluating a different, more fully curated 1671-entry subset
      than whatever population the manuscript's Table 3 figures were computed on, and/or (b) the
      manuscript selecting the "best" raw score per group via CV over many candidate columns
      (221 raw scores total across groups) rather than this package's single fixed column per
      group. Reproducing the manuscript's selection step exactly would require re-running that
      per-group, per-candidate-column CV search, which is a natural next extension of this
      package but was out of scope here.

--------------------------------------------------------------------------------------------
## Step 5c — Reconstructing the manuscript's actual score-selection CV

**The manuscript does not specify a particular dataset split for its 5-fold CV.** The only
text describing it (Results, p.10) is: "ROCs were computed from these scores using 5-fold
cross validation to select the best performing score for each group" — there is no statement
of how the 5 folds were built (random seed, stratification, homology control), and no fold
file is provided in the GitHub repository. **This is therefore not reproducible exactly**; the
best that can be done is to reconstruct a methodologically sound version of the same
procedure using our own split, and see whether the result is compatible with the published
numbers.

5c.1  `workflow/select_best_score_cv.py` implements the full nested-CV score-selection
      procedure the manuscript describes, instead of the single-fixed-column check in 5b:
      pool *every* raw and integrated score column a group submitted (up to 88 for
      Fernandez-Recio, 74 for Venclovas, as few as 1 for SWISS-MODEL — 261 candidate columns
      pooled across the 13 groups, close to the manuscript's reported "221 raw scores, and 31
      integrated scores"). For each of the 5 held-out folds (the Step 5b homology-safe split —
      **our own reconstruction, not the manuscript's undisclosed split**), select the column
      with the highest AUC on the 4 training folds only, then evaluate that single selected
      column on the held-out fold. The reported `cv_selected_auc_mean` is the average of the 5
      held-out-fold AUCs — genuine nested CV, so no candidate is ever evaluated on the fold used
      to pick it.

5c.2  Run for all 13 groups (`datasets/cv_score_selection/group_*/cv_selection_results.json`,
      summarized in `qc_analysis/superseded/cv_score_selection_vs_published.csv`):

      | group | published AUC | CV-selected AUC (this split) | abs diff |
      |---|---|---|---|
      | Bonvin | 0.85 | 0.880 | 0.030 |
      | Furman | 0.84 | 0.835 | 0.005 |
      | Venclovas | 0.82 | 0.829 | 0.009 |
      | Guerois | 0.81 | 0.861 | 0.051 |
      | Zou | 0.81 | 0.807 | 0.003 |
      | Fernandez-Recio | 0.79 | 0.754 | 0.036 |
      | SWISS-MODEL | 0.79 | 0.825 | 0.035 |
      | Bologna | 0.76 | 0.819 | 0.059 |
      | Correia | 0.75 | 0.767 | 0.017 |
      | Kihara | 0.75 | 0.766 | 0.016 |
      | Oliva | 0.75 | 0.781 | 0.031 |
      | MOBI | 0.72 | 0.829 | 0.109 |
      | Wolfson | 0.71 | 0.867 | 0.157 |

      Mean absolute difference from the published AUC drops to **0.043**, versus ~0.14 for the
      earlier single-fixed-column approach (Step 4.4) — a clear sign that **CV-based score
      selection across many candidates, not the presence/absence of cross-validation on a
      single fixed score, was the main source of the earlier mismatch.** MOBI and Wolfson
      remain the two clear outliers (0.109 and 0.157 off), which could come from a different
      fold split, a different candidate-inclusion rule, or the manuscript's authors applying
      group-specific domain knowledge (e.g. excluding a column) not encoded in this generic
      script — this is flagged as an open discrepancy, not resolved here.

5c.3  **Bottom line for anyone extending this package**: do not treat `cv_selected_auc_mean`
      as *the* manuscript number — it is this package's best-effort, leakage-safe
      reconstruction of an *undocumented* procedure, evaluated on *our own* fold split. Report
      it alongside `published_auc` (as the CSV already does), never in place of it.

--------------------------------------------------------------------------------------------
## Step 6 — What remains to go live on openebench.bsc.es (not executed here — needs
##          OpenEBench support / VRE access)

7.1  Register each Tool (14 scoring functions here) in OpenEBench to obtain an official tool id
     (`how_to/4_manage_events`).

7.2  Package each of the three steps (`validate.py`, `compute_metrics.py`, `consolidate.py`) as
     its own Docker image, using the TCGA Cancer Driver Benchmarking dockers repository as a
     template, and wire them into a versioned, tagged Git repository.

7.3  Run the containerized workflow inside the OpenEBench Virtual Research Environment (VRE),
     then email the OpenEBench support team the repository URL and the specific tag/commit so
     the Benchmarking Event, Challenge, and metadata records described in `metadata/` can be
     loaded into the production database (there is currently no self-service UI for this step).

7.4  Once the event is active, publish further Participant / Participant-Assessment datasets
     (e.g. new scoring functions, or the AlphaFold-multimer DockQ results already present in
     `AlphaFold_models/`) via the VRE or the OpenEBench REST API.

--------------------------------------------------------------------------------------------
## File map of this package

```
metadata/
  Community.json, BenchmarkingEvent.json
  Challenges/Challenge_PPI-PhysioClassification.json
  Metrics/Metrics_{AUC-ROC,ACC-at-threshold,leaderboard-aggregation}.json
  Tools/Tool_<participant_id>.json            (14 scoring-function tools)
  Tools/Tool_{compute_AUC,compute_ACC,aggregate_benchmark}.json
  Contacts/Contact_<group>.json
datasets/
  input/Dataset_input.json, benchmark_entries_manifest.csv
  public_reference/Dataset_public_reference.json, public_reference_ids.csv
  metrics_reference/Dataset_metrics_reference.json, gold_standard_labels.csv
  participant/<participant_id>/{Dataset_participant_<id>.json, predictions.csv}
  assessment/Dataset_assessment_{AUC,ACC}_<participant_id>.json
  aggregation/Dataset_aggregation_PPI-PhysioClassification.json
workflow/
  validate.py, compute_metrics.py, consolidate.py
  nextflow_main.nf, run_pipeline.sh
  example_leaderboard.svg   (output of a full test run of the pipeline)
qc_analysis/diagnostics/benchmark_summary_published_vs_recomputed.csv
```


## Follow-up (requested check): any OTHER group with a Training-like column we hadn't checked?

A comprehensive re-scan of EVERY csv under `groups/` (including `imported/`, `data-unused/`,
`analysis/` subfolders previously skipped, and a broad column-name pattern: train, test, split,
fold, cv, holdout, held, calib, valid) found:

- No group beyond the 6 already tested (Bonvin, Casadio/Bologna, MOBI, SWISS-MODEL, Wolfson, Zou)
  carries an INFORMATIVE Training/TrainingColumn flag (one with >=2 distinct values).
- A few additional files DO have a `Training` column, but it is CONSTANT across all rows and
  therefore carries no split information: Oliva (`'No'` for all 1677 rows), Venclovas (`0` for
  all 1677 rows), Bonvin's own `haddock.csv` (`False` for all 1677 -- unlike its `deeprank.csv`/
  `deeprank-gnn.csv`/`prodigy-crystal.csv` which DO vary), Zou's `Zoulab_results_ITScorePP.csv`
  (`False` for all -- unlike `Zoulab_results_DLScoreBC.csv` which DOES vary and was tested), and
  AlphaFold's own gap-mode results file.
- Fernandez-Recio, Guerois, Correia, Furman (Schueler-Furman), and Kihara's own (non-imported)
  raw-score file carry NO Training-like column at all.
- Apparent "split" hits for Venclovas/Kihara were false positives: substring matches inside
  Voronota feature names (`F_Voronota_split_area`, etc.), unrelated to any train/test split.

So the comprehensive answer is: no, no additional group's Training flag was left unchecked.

## Follow-up (requested check): NaN predictions are excluded, confirmed per participant

Every participant's `predictions.csv` in this package is built via an explicit `.dropna()` on
the score column before any AUC/accuracy is computed, so missing predictions are never silently
treated as zero, as a tie, or as any other default value. Per-participant counts (file rows ->
matched to gold standard -> NaN-score rows excluded -> final n used):

| participant | raw file rows | matched to corrected gold standard | NaN scores excluded | final n used |
|---|---|---|---|---|
| Guerois | 1677 | 1585 | 250 | 1395 |
| SWISS-MODEL | 1677 | 1671 | 548 | 1123 |
| Correia | 1677 | 1618 (after bare-ID fallback, see below; 59 unresolved: 53 ambiguous + 6 pre-"to delete") | 66 | 1552 |
| Bonvin | 1678 | 1672 | 37 | 1635 |
| Fernandez-Recio | 1677 | 1671 | 14 | 1657 |
| all others | 1677-1678 | 1671-1672 | 0 | 1671-1672 |

Guerois and SWISS-MODEL have the largest genuine NaN fractions (their own scoring pipelines did
not produce a value for a meaningful share of entries); those rows are correctly excluded, not
imputed.

## Bonus finding from this check: Correia's remaining coverage gap was an ID-format issue, now fixed

Investigating Correia's NaN counts surfaced that its 947/1671-entry coverage (flagged as an open,
presumed data-coverage issue in the CRITICAL CORRECTION section above) was actually a SECOND,
narrower ID-matching gap: Correia's own file identifies ProtCID-derived complexes by the BARE
PDB code (e.g. `4czm`), not `ID_InterfaceID` like every other group's files. A two-tier
resolution was added: try the exact composite entry_id first, then fall back to the bare code
ONLY when the gold standard has a single, unambiguous interface for that code (647 of 700 cases
are safely resolvable this way; the remaining 53 are genuinely ambiguous -- multiple interfaces
share that PDB code -- and are correctly excluded rather than guessed).

**Result**: Correia's coverage rose from 947 to 1552 entries, and AUC moved from 0.7996 (abs
diff 0.050 from published) to **0.7661 (abs diff 0.016)**. This was the last group with a
meaningfully large discrepancy; package-wide mean |AUC difference| from the manuscript's Table 3
is now **0.0096** across all 13 groups (down from 0.0119 before this fix, 0.14 before the
entry_id bug fix, and ~0.14 at the very start of this exercise).


## Follow-up (requested check): NaN handling in the Training column itself

Checked every file identified as carrying an informative Training/TrainingColumn flag
(Bonvin x4 files, Casadio x2 files, MOBI, SWISS-MODEL, Wolfson, Zou) for missing (NaN) values
in that column specifically (not the score column):

| file | n_rows | n_NaN in Training/TrainingColumn |
|---|---|---|
| Bonvin/deeprank.csv | 1677 | 0 |
| Bonvin/haddock.csv | 1677 | 0 |
| Bonvin/prodigy-crystal.csv | 1677 | 0 |
| **Bonvin/deeprank-gnn.csv** | 1678 | **4** |
| Casadio/ispred4-sens-score.csv | 1677 | 0 |
| Casadio/ispred4-mcc-score.csv | 1677 | 0 |
| MOBI/MOBI_raw_scores.csv | 1677 | 0 |
| SWISS-MODEL/qsqe_results.csv | 1677 | 0 |
| Wolfson/classifier-data.csv | 1677 | 0 |
| Zou/Zoulab_results_DLScoreBC.csv | 1677 | 0 |

Only `Bonvin/deeprank-gnn.csv` (the file used for Bonvin's official participant in this package)
has any NaN in its Training column, at rows `6vdd_2`, `6vjb_4`, `6wrh_3`, `6w25_2`. Checked
those 4 rows directly: **their `I_p_biological`/`I_p_crystal` score columns are ALSO NaN** --
these are entries DeepRank-GNN produced no prediction for at all (not just an unlabeled
Training status), so they are already excluded from every AUC/accuracy computation in this
package via the score-column `.dropna()`, independent of how the Training column is handled.
No bug, no double-counting: `qc_analysis/diagnostics/training_flag_hypothesis_test.csv`'s `dropna(subset=["label",
"score","tflag"])` and the main pipeline's score-only dropna agree on excluding exactly these
4 rows for Bonvin. Casadio has zero NaN in its Training column across both files.


## Follow-up (requested re-check): whole-REPOSITORY scan for Training-like columns (not just groups/)

Re-ran the column-name scan (train, test, split, fold, cv, holdout, held, calib, valid,
class_set, subset) across every CSV/.out file in the ENTIRE repository, not just `groups/` --
including `AlphaFold_models/`, `random_forest_analysis/`, `ROC_analysis/`, and `benchmark/`.

Result (full list in `qc_analysis/diagnostics/training_flag_wholerepo_scan.csv`):
- Zero hits outside `groups/`.
- Every hit inside `groups/imported/` (Casadio's, Bonvin's, MOBI's, Venclovas's files bundled
  under `group_Kihara/imported/`) is BYTE-IDENTICAL (verified by checksum) to the origin
  group's own file -- these are Kihara's own copies for an internal correlation analysis, not
  independently-submitted variants with their own Training flag.
- The `F_Voronota_split_*` hits are false positives: Voronota feature names containing the
  substring "split" (e.g. interface-vs-whole-complex "split" decomposition terms), unrelated
  to any train/test split.
- Confirms, now at full-repository scope: no group beyond the 6 already tested (Bonvin,
  Casadio/Bologna, MOBI, SWISS-MODEL, Wolfson, Zou) carries an informative Training-like flag.


---------------------------------------------------------------------------------------------
## >>> MULTIPLE CROSS-VALIDATION SPLITTING STRATEGIES PROPOSED (own work, not from manuscript) <<<

See **CV_SPLITTING_STRATEGIES.md** for the full writeup. Short version, to make this
unambiguous: the Step 5b/5c CV splits described earlier in this README are this package's OWN
proposal -- the manuscript never discloses how its folds were built. Four alternative,
leakage-verified (zero groups spanning >1 fold) strategies are now provided:

1. **CATH superfamily / UniProt gene** (original, annotation-based, no external tool).
2. **MMseqs2 sequence-identity clustering** (this package's own run on sequences extracted
   from the benchmark's PDB structures), parameterized to approximate the user's own prior
   `blastclust -S 25 -L 0.5 -b F` protocol.
3. **Authoritative blastclust reference** (user-provided, from
   https://biofold.github.io/ppi-benchmark-fair -- confirmed 100% entry-id match against this
   exact 1677-entry benchmark).
4. **Combined union of (1) and (3)** -- RECOMMENDED: two entries share a fold if either
   structural-annotation or sequence-identity homology links them.

Files: `datasets/metrics_reference/cv_fold_strategy{1,2,2b,3}_*.csv`,
`benchmark_sequences.fasta`, `blastclust_reference_S25_L05_bF.txt`, `mmseqs2_strict_cluster.tsv`.
---------------------------------------------------------------------------------------------


---------------------------------------------------------------------------------------------
## >>> IS THIS PACKAGE READY TO GO LIVE ON openebench.bsc.es? See OPENEBENCH_SUBMISSION_READINESS.md <<<

Short version: 82 of 83 metadata/dataset JSON files in this package now PASS validation against
the real OpenEBench 1.0.x JSON Schemas (verified with the actual schema repository and its
$ref resolver, not just eyeballed against the TCGA example). The one failure is structural and
cannot be fixed offline: `Community._id` must be a real, platform-assigned `OEBC###` code
(confirmed via public examples like `openebench.bsc.es/projects/OEBC001`), not a self-chosen
string. Remaining gaps needing a human/account action on the live platform: Docker images for
the three workflow steps (written as Dockerfiles in this pass, not built -- no Docker daemon in
this sandbox), a tagged public Git repository, official Tool-ID registration for all 14
participants, real contact emails (currently placeholders), and the mandatory email to
OpenEBench support (no self-service submission API exists for a new Benchmarking Event).
---------------------------------------------------------------------------------------------


---------------------------------------------------------------------------------------------
## >>> LOCAL LEADERBOARD VISUALIZER (real OpenEBench component, your own machine) <<<

`local_visualizer/` contains a ready-to-run bundle of the actual open-source OpenEBench
scientific visualizer (github.com/inab/OpenEBench_scientific_visualizer), built from source and
wired up to render THIS challenge's own aggregation dataset via a small local mock of its two
GraphQL queries -- no database, no live OpenEBench account, no network access needed.

**This sandbox cannot open a listening network socket (verified)**, so there is no live URL to
click from here. Run it on your own machine: `cd oeb_ppi_benchmark && python3
serve_local_openebench_visualizer.py --port 8080`, then open http://localhost:8080/. Full
details, limitations, and how to point it at a different challenge: `local_visualizer/README.md`.
---------------------------------------------------------------------------------------------


## Additional performance metrics (AUCPR, Balanced Accuracy, F1, MCC)

Beyond the original AUC-ROC and Accuracy-at-threshold, the package now computes and reports,
for all 14 participant scoring functions, on the full corrected 1671-entry gold standard:

- **AUROC** (`3DBioinfo:AUC-ROC`) -- threshold-free ranking metric (unchanged from before).
- **AUCPR** (`3DBioinfo:AUCPR`) -- Average Precision, the threshold-free area under the
  Precision-Recall curve. More informative than AUROC when the positive/negative split is
  imbalanced (here it is close to balanced: 840 physiological vs. 831 non-physiological, so
  AUROC and AUCPR agree closely for every participant).
- **Balanced Accuracy** (`3DBioinfo:Balanced-Accuracy`) -- mean of sensitivity and specificity.
- **F1 Score** (`3DBioinfo:F1-Score`) -- harmonic mean of precision and recall for the
  physiological class.
- **MCC** (`3DBioinfo:MCC`) -- Matthews Correlation Coefficient.

**Threshold used for the three threshold-based metrics (Balanced Accuracy, F1, MCC) and for
Accuracy-at-threshold**: the published decision threshold reported for that scoring function
in the manuscript, when one exists. The single exception is Voronota (Venclovas group), for
which no published threshold exists; its data-driven optimal threshold is used instead,
found by maximizing Youden's J statistic (TPR - FPR) over all observed score cutpoints on this
same scored population. This fallback rule -- "published threshold if available, else Youden's
J-optimal threshold" -- is implemented in `workflow/compute_metrics.py`
(`youden_optimal_threshold()`) and is applied consistently to every metric that requires a
decision threshold, not only Accuracy.

All reported values were cross-checked against `scikit-learn`
(`roc_auc_score`, `average_precision_score`, `balanced_accuracy_score`, `f1_score`,
`matthews_corrcoef`) computed on the same oriented scores and thresholds; the dependency-free
`compute_metrics.py` reimplementation (no external packages, matching the rest of the OEB
pipeline scripts) agrees with scikit-learn to within 0.002 for every participant and metric
(small residual differences come from tie-handling in the Average-Precision estimator).

New package contents added for these metrics:
- `metadata/Metrics/Metrics_AUCPR.json`, `Metrics_Balanced-Accuracy.json`, `Metrics_F1-Score.json`,
  `Metrics_MCC.json` -- OpenEBench Metrics entity definitions.
- `metadata/Tools/Tool_compute_AUCPR.json`, `Tool_compute_BalancedAccuracy.json`,
  `Tool_compute_F1.json`, `Tool_compute_MCC.json` -- the corresponding metric-computation Tool
  entities, following the same pattern as the original `compute_AUC`/`compute_ACC`.
- `datasets/assessment/Dataset_assessment_{AUCPR,BalancedAccuracy,F1,MCC}_<participant>.json`
  (56 files, 4 metrics x 14 participants) -- one assessment Dataset per participant per metric,
  schema-identical in structure to the existing AUC/ACC assessment datasets.
- Three additional 2D-plot aggregation (leaderboard) datasets, respecting the real OpenEBench
  visualizer's pairwise x/y scatter format (it does not support more than two metrics per
  chart): AUC-ROC vs. AUCPR, Balanced Accuracy vs. F1 Score, and MCC vs. Balanced Accuracy.
  The original AUC-ROC vs. Accuracy leaderboard is unchanged and remains the chart embedded
  in the local visualizer page.
- `Challenge_PPI-PhysioClassification.json`'s `metrics_categories` updated to register all
  6 assessment metrics and reference all 4 aggregation datasets.
- `qc_analysis/diagnostics/benchmark_summary_published_vs_recomputed.csv` extended with `aucpr`, `balanced_accuracy`,
  `f1_score`, `mcc`, `threshold_used_oriented` and `threshold_source` columns.
- The local visualizer page's Results section now also shows a full table with all 5 metrics
  for all 14 participants, underneath the original AUC-vs-Accuracy scatter chart.

All 68 new/modified JSON files (4 Metrics + 4 Tools + 56 assessment Datasets + 3 aggregation
Datasets + 1 Challenge) were validated against the real OpenEBench 1.0.x JSON Schemas with
zero failures.


## Upload-and-compare: evaluating a new scoring function against declared CV splits

The local visualizer bundle (`local_visualizer/`) now supports uploading a new participant's
predictions and evaluating them, live, against the existing 14 scoring functions under one of
the package's 4 declared, leakage-safe CV splitting strategies (see
`CV_SPLITTING_STRATEGIES.md`). This directly extends the CV-splitting work above from a static
analysis into an interactive comparison tool:

- A new **cv_evaluate.py** module (`workflow/cv_evaluate.py`) factors the leakage-safe CV
  procedure (per-fold Youden's J threshold learned on the OTHER folds only; AUROC/AUCPR computed
  threshold-free on the held-out fold) into a reusable, dependency-free engine, shared between
  the CLI (`crossval_metrics.py`) and the server's upload endpoint.
- **Baseline CV leaderboards** were precomputed for all 14 participants under all 4 strategies
  (`qc_analysis/cv_leaderboard/strategy{1,2,2b,3}.json`) so a new upload is compared against
  numbers computed with the exact same held-out procedure, not against the resubstitution values
  in `qc_analysis/diagnostics/benchmark_summary_published_vs_recomputed.csv` (which use each tool's own published
  threshold and are not cross-validated).
- The server (`serve_local_openebench_visualizer.py`) exposes `POST /api/evaluate_submission`
  (multipart file upload + chosen strategy + submission name), `GET /api/strategies`, and a
  `GET /package/<path>` read-only file server used to link every leaderboard row to its own
  submission file and to the exact reference data (gold standard + fold assignment) used for
  evaluation.
- The page's new **Submit new predictions** section (linked from the sidebar) renders this
  live, highlighting the uploaded entry in the resulting ranked table.

This was end-to-end verified by calling the server's actual request-handling code (`do_GET`/
`do_POST`) against mocked sockets (confirmed separately that this sandbox cannot bind a real
listening socket) with a real multipart body, and by a headless jsdom render of the page.

## Package restructured: single flat directory (web page + submission files as siblings)

Per follow-up feedback, the local visualizer's web page launch files (`serve_local_openebench_
visualizer.py`, `visualizer_static/`) have been moved from a `local_visualizer/` subfolder up to
the package root, so they sit directly alongside every submission file rather than nested inside
a wrapper folder:

```
oeb_ppi_benchmark/                      <- open this one directory for everything
  serve_local_openebench_visualizer.py  <- run this to view the local web page
  visualizer_static/                    <- the web page itself
  metadata/                             <- OpenEBench submission files, as direct siblings
  datasets/
  workflow/
    prepare_for_openebench_submission.py   <- the interactive submission-prep wizard
    validate.py / compute_metrics.py / consolidate.py
    Dockerfile.validate / .compute_metrics / .consolidate
  schemas/                              <- bundled OpenEBench JSON Schemas (offline validation)
  qc_analysis/
  README_STEP_BY_STEP.md, OPENEBENCH_SUBMISSION_READINESS.md, CV_SPLITTING_STRATEGIES.md, ...
```

`resolve_default_package_dir()` in the server script was extended to recognize this layout first
(the script sitting directly next to `metadata/`/`datasets/`), while still supporting the earlier
standalone-bundle and legacy-subfolder layouts as fallbacks, so `--package` never needs to be
passed explicitly. Running the page is now simply `cd oeb_ppi_benchmark && python3
serve_local_openebench_visualizer.py`.

Verified by copying this restructured package to a clean, isolated directory and confirming: the
resolver correctly identifies its own directory as the package root, a full prediction submission
evaluates correctly, the chart's GraphQL data merge still works, the `/package/` file-download
route still works, the reset-on-page-reload behavior is unaffected, and the page itself renders
with zero errors headlessly.
