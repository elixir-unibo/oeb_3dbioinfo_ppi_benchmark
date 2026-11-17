#!/usr/bin/env bash
# Runs the full validate -> metrics -> consolidate pipeline for every participant
# in datasets/participant/*, then consolidates into one leaderboard.
# This is the plain-Python equivalent of the nextflow_main.nf skeleton, useful
# for a first local smoke test before wrapping each step in its own Docker image.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTDIR="${1:-$HERE/_pipeline_run}"
mkdir -p "$OUTDIR/validation_out" "$OUTDIR/assessment_out"

for pdir in "$HERE"/datasets/participant/*/; do
  pid=$(basename "$pdir")
  mkdir -p "$OUTDIR/validation_out/$pid" "$OUTDIR/assessment_out/$pid"
  python3 "$HERE/workflow/validate.py" \
    --input "$pdir/predictions.csv" \
    --public_ref_dir "$HERE/datasets/public_reference" \
    --community_id OEBC_3DBioinfo --challenges_ids 3DBioinfo:PPI-PhysioClassification \
    --participant_id "$pid" --outdir "$OUTDIR/validation_out/$pid" || true

  python3 "$HERE/workflow/compute_metrics.py" \
    --input "$pdir/predictions.csv" \
    --goldstandard_dir "$HERE/datasets/metrics_reference" \
    --community_id OEBC_3DBioinfo --challenges_ids 3DBioinfo:PPI-PhysioClassification \
    --participant_id "$pid" --outdir "$OUTDIR/assessment_out/$pid"
done

python3 "$HERE/workflow/consolidate.py" \
  --assess_dir "$OUTDIR/assessment_out" --community_id OEBC_3DBioinfo \
  --challenge_id 3DBioinfo:PPI-PhysioClassification --outdir "$OUTDIR/consolidated"

echo "Done. See $OUTDIR/consolidated/data_model_export.json and leaderboard.svg"
