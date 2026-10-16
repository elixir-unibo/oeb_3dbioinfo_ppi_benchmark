# oeb_3dbioinfo_ppi_benchmark -- static page for GitHub Pages (e.g. elixir-unibo.github.io)

This is a STATIC build of the PPI-PhysioClassification benchmark results page, meant to be
dropped directly into a subfolder of a static site (e.g. `tools/oeb_3dbioinfo_ppi_benchmark/`)
that only serves plain files -- no backend/Python process required.

## What works here, and how

- **Results tab**: the real OpenEBench Scientific Visualizer library (`build/build.js`, unmodified)
  renders the actual AUC-ROC-vs-Accuracy leaderboard chart. Since there is no live GraphQL server
  to talk to on a static host, a small shim (`<script>` near the bottom of `index.html`) overrides
  both `window.fetch` and `XMLHttpRequest` (the library can use either transport depending on the
  browser) to answer the library's two queries (`getDatasets`, `getMetrics`) instantly with a FIXED
  snapshot of the real 14-participant data -- the exact response a running
  `serve_local_openebench_visualizer.py` would have sent over the network. The chart code itself is
  not reimplemented or approximated in any way.
- The **Full metrics table** and **Quartile ranking table** (with its Classification Method
  selector -- Square/Diagonal quartiles, K-Means clustering) are fully interactive and work
  entirely client-side; no server needed.
- **Datasets** and **Tools** tabs link directly to the real data files bundled in `data/`.
- **Submit new predictions**: fully live, zero-backend. Uploading a CSV runs the SAME leakage-safe
  cross-validation engine as `workflow/cv_evaluate.py` (ported line-for-line to JavaScript and
  numerically validated to match the Python output to 4 decimal places), entirely in your browser --
  the uploaded file is never sent anywhere over the network. It fetches the chosen CV strategy's
  fold-assignment CSV and the gold-standard labels from `data/` (plain static GETs, which work on
  GitHub Pages), evaluates every fold with the decision threshold learned only from the other folds,
  computes the rank against the 14 baseline participants, and updates the metrics table, quartile
  table, and chart in place -- the same experience as the full interactive package below, with no
  installation needed.

## Contents

- `index.html`, `build/` -- the static page and the real visualizer bundle.
- `data/` -- the 14 participants' submission files, the gold-standard reference data, the 4 CV
  fold-assignment files, the per-strategy CV leaderboards (`data/cv_leaderboard/`), and a demo
  predictions CSV.
- `CV_SPLITTING_STRATEGIES.md` -- referenced from the Datasets tab and the Submit tab.
- `oeb_ppi_benchmark.zip` -- the full OpenEBench submission package (metadata, schemas, Docker
  drafts, the submission-preparation wizard) for anyone who wants the complete offline bundle or
  needs to actually submit this benchmark to OpenEBench; not required to use the Submit feature
  above, which is fully self-contained on this static page.

Deploy by copying this entire folder as-is into your site, e.g. as `tools/oeb_3dbioinfo_ppi_
benchmark/` -- no build step, no server configuration, works on GitHub Pages out of the box.
