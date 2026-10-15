# oeb_3dbioinfo_ppi_benchmark -- static page for GitHub Pages (e.g. elixir-unibo.github.io)

This is a STATIC build of the PPI-PhysioClassification benchmark results page, meant to be
dropped directly into a subfolder of a static site (e.g. `tools/oeb_3dbioinfo_ppi_benchmark/`)
that only serves plain files -- no backend/Python process required.

## What works here, and how

- **Results tab**: the real OpenEBench Scientific Visualizer library (`build/build.js`, unmodified)
  renders the actual AUC-ROC-vs-Accuracy leaderboard chart. Since there is no live GraphQL server
  to talk to on a static host, a small shim (`<script>` near the bottom of `index.html`) overrides
  `XMLHttpRequest` to answer the library's two queries (`getDatasets`, `getMetrics`) instantly with
  a FIXED snapshot of the real 14-participant data -- the exact response a running
  `serve_local_openebench_visualizer.py` would have sent over the network. The chart code itself is
  not reimplemented or approximated in any way.
- The **Full metrics table** and **Quartile ranking table** (with its Classification Method
  selector -- Square/Diagonal quartiles, K-Means clustering) are fully interactive and work
  entirely client-side; no server needed.
- **Datasets** and **Tools** tabs link directly to the real data files bundled in `data/`.

## What does NOT work here (needs the live version instead)

Uploading your own predictions to see them evaluated and ranked (the "Submit new predictions"
feature) needs a running backend to do the leakage-safe cross-validated evaluation -- that cannot
run on a static host. The "Try it yourself" card at the bottom of the Results tab explains this and
links to `oeb_ppi_benchmark.zip`, the full package: extract it and run
`cd oeb_ppi_benchmark && python3 serve_local_openebench_visualizer.py` on your own machine to get
the complete, live, interactive version (same page, same look, plus the upload feature) -- a demo
predictions file is included there to try it immediately.

## Contents

- `index.html`, `build/` -- the static page and the real visualizer bundle.
- `data/` -- the 14 participants' submission files, the gold-standard reference data, the 4 CV
  fold-assignment files, and a demo predictions CSV.
- `CV_SPLITTING_STRATEGIES.md` -- referenced from the Datasets tab.
- `oeb_ppi_benchmark.zip` -- the full, live, interactive package (see above).

Deploy by copying this entire folder as-is into your site, e.g. as `tools/oeb_3dbioinfo_ppi_
benchmark/` -- no build step, no server configuration, works on GitHub Pages out of the box.
