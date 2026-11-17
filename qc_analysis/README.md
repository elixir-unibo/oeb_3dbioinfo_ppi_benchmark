# qc_analysis

Quality-control tables and analyses produced while the package was built. None of these files is an OpenEBench dataset or is read by the workflow.

| Path | Content |
|---|---|
| `cv_leaderboard/` | cross-validated results of the 14 reference methods for each of the four splitting strategies; used by the page to rank new submissions |
| `diagnostics/` | working analyses: published versus recomputed AUC (`benchmark_summary_published_vs_recomputed.csv`), comparison of the four splitting strategies, handling of missing scores, and the checks of the training flag and of the MOBI and Wolfson scores |
| `superseded/` | analyses computed **before** a correction of the entry matching for ProtCID-derived entries, kept for transparency. Their values do not agree with the current results (for example, the resubstitution AUC of the random-forest consensus is 0.8775 there and 0.9474 in `diagnostics/benchmark_summary_published_vs_recomputed.csv`). Do not use them |

The current reference values are those of `cv_leaderboard/` and `diagnostics/benchmark_summary_published_vs_recomputed.csv`.
