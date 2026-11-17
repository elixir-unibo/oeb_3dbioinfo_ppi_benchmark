# ELIXIR 3D-BioInfo PPI Benchmark — OpenEBench experiment

**Interactive page: [https://elixir.unibo.it/tools/oeb_3dbioinfo_ppi_benchmark/](https://elixir.unibo.it/tools/oeb_3dbioinfo_ppi_benchmark/)**
**Submit your own predictions: [https://elixir.unibo.it/tools/oeb_3dbioinfo_ppi_benchmark/#submit-section](https://elixir.unibo.it/tools/oeb_3dbioinfo_ppi_benchmark/#submit-section)**
Load your own predictions there and see how they rank against the 14 reference methods of Schweke *et al.* (DOI [10.22541/au.167569565.51141128/v1](https://doi.org/10.22541/au.167569565.51141128/v1)). The evaluation runs in your browser; no file is uploaded anywhere.

Benchmark task: discriminate **physiological** from **crystallographic (non-physiological)** protein homodimer interfaces. 1,671 curated entries (840 physiological, 831 non-physiological). The data were FAIRified in [ppi-benchmark-fair](https://biofold.github.io/ppi-benchmark-fair); this repository connects them to the [OpenEBench](https://openebench.bsc.es) ecosystem (ELIXIR Tools Platform, WP4 Activity 1, University of Bologna node).

## Example of results

Cross-validated performance of the 14 reference methods (5-fold, homology-aware Strategy 3, mean ± standard deviation across folds; decision thresholds for balanced accuracy, F1 and MCC are learned on the training folds only):

| Rank | Method | n | AUROC | AUCPR | Balanced accuracy | F1 | MCC |
|---:|---|---:|---|---|---|---|---|
| 1 | Random Forest consensus (top-221 features) | 1642 | 0.948 ± 0.011 | 0.946 ± 0.010 | 0.881 ± 0.019 | 0.882 ± 0.022 | 0.763 ± 0.037 |
| 2 | DeepRank-GNN | 1634 | 0.861 ± 0.015 | 0.821 ± 0.039 | 0.802 ± 0.016 | 0.821 ± 0.019 | 0.614 ± 0.032 |
| 3 | Rosetta InterfaceAnalyzer | 1665 | 0.848 ± 0.019 | 0.819 ± 0.047 | 0.794 ± 0.022 | 0.800 ± 0.021 | 0.588 ± 0.044 |
| 4 | IES (normalized) | 1395 | 0.823 ± 0.019 | 0.846 ± 0.022 | 0.765 ± 0.031 | 0.807 ± 0.025 | 0.532 ± 0.060 |
| 5 | DLScore-BC | 1671 | 0.818 ± 0.019 | 0.802 ± 0.023 | 0.747 ± 0.011 | 0.756 ± 0.018 | 0.497 ± 0.022 |
| 6 | QSQE | 1123 | 0.810 ± 0.050 | 0.918 ± 0.031 | 0.714 ± 0.022 | 0.774 ± 0.069 | 0.402 ± 0.060 |
| 7 | Voronota | 1671 | 0.808 ± 0.019 | 0.772 ± 0.041 | 0.749 ± 0.023 | 0.751 ± 0.025 | 0.500 ± 0.046 |
| 8 | NIPacking | 1657 | 0.791 ± 0.030 | 0.748 ± 0.034 | 0.766 ± 0.018 | 0.766 ± 0.019 | 0.533 ± 0.037 |
| 9 | ISPRED4 | 1671 | 0.769 ± 0.029 | 0.750 ± 0.023 | 0.716 ± 0.023 | 0.708 ± 0.029 | 0.433 ± 0.046 |
| 10 | MaSIF | 1552 | 0.767 ± 0.022 | 0.750 ± 0.034 | 0.704 ± 0.031 | 0.720 ± 0.030 | 0.408 ± 0.062 |
| 11 | GOAP | 1671 | 0.754 ± 0.038 | 0.717 ± 0.063 | 0.692 ± 0.021 | 0.709 ± 0.028 | 0.388 ± 0.042 |
| 12 | CP/COCOMAPS | 1671 | 0.749 ± 0.032 | 0.733 ± 0.048 | 0.690 ± 0.028 | 0.692 ± 0.039 | 0.381 ± 0.056 |
| 13 | shape_hydro_tails | 1671 | 0.729 ± 0.016 | 0.699 ± 0.031 | 0.666 ± 0.014 | 0.671 ± 0.030 | 0.334 ± 0.027 |
| 14 | ProbaConsensus (ScanNet F_Network) | 1671 | 0.727 ± 0.027 | 0.668 ± 0.044 | 0.668 ± 0.020 | 0.709 ± 0.023 | 0.356 ± 0.050 |

`n` is the number of benchmark entries each method scored. Methods with fewer than 1,671 entries are evaluated on their own subset, so values are not strictly comparable across rows (the high AUCPR of QSQE, which is above its AUROC, reflects its subset of 1,123 entries).

### Example of a new submission

Evaluating the demo file [`data/demo_predictions_for_upload_test.csv`](data/demo_predictions_for_upload_test.csv) (1,610 entries) with Strategy 3 gives:

| Metric | Value (mean ± std over 5 folds) |
|---|---|
| AUROC | 0.814 ± 0.026 |
| AUCPR | 0.799 ± 0.036 |
| Balanced accuracy | 0.747 ± 0.019 |
| F1 | 0.735 ± 0.023 |
| MCC | 0.496 ± 0.037 |

Rank by AUROC: **6 of 15** (the 14 reference methods plus the new one). The page shows this result in the metrics table, the quartile ranking and the leaderboard chart (AUROC versus accuracy at the threshold). The values above were computed with `workflow/cv_evaluate.py` from the bundle and agree with the in-browser result (0.814 ± 0.026).

### How to submit your own predictions

1. Prepare a CSV with two columns, `entry_id` and `score` (higher score = more likely physiological), as in [`data/predictions_template.csv`](data/predictions_template.csv).
2. Open the [submission section](https://elixir.unibo.it/tools/oeb_3dbioinfo_ppi_benchmark/#submit-section), select a cross-validation strategy (Strategy 3 is the default recommendation) and upload the file.

## What is in this repository

| Path | Content |
|---|---|
| `index.html`, `build/` | the page and the OpenEBench Scientific Visualizer bundle |
| `data/datasets/participant/` | predictions of the 14 reference methods, with their OpenEBench dataset records |
| `data/datasets/metrics_reference/` | gold-standard labels and the four cross-validation fold assignments |
| `data/cv_leaderboard/` | cross-validated results of the reference methods for each strategy |
| `CV_SPLITTING_STRATEGIES.md` | description of the four splitting strategies |
| `oeb_ppi_benchmark.zip` | the complete OpenEBench bundle: metadata, datasets, schemas, workflow scripts, preparation script |

## Deployment note

The page is a static site (no backend). The header links point two levels up (`../../`) because it is deployed at `tools/oeb_3dbioinfo_ppi_benchmark/` on the ELIXIR University of Bologna node site; opened from another location, those links will not resolve, while the benchmark features work anywhere.
