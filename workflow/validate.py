#!/usr/bin/env python3
"""
OpenEBench-style Step 1: VALIDATION
Checks that a participant's prediction file covers the entries listed in the
public_reference dataset and conforms to the expected 2-column format.

Usage:
    python validate.py --input predictions.csv --public_ref_dir public_reference/ \
                        --community_id OEBC_3DBioinfo --challenges_ids PPI-PhysioClassification \
                        --participant_id <tool_name> --outdir validation_out/
"""
import argparse, csv, json, os, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="participant predictions.csv (entry_id,raw_score[,...])")
    ap.add_argument("--public_ref_dir", required=True, help="directory with public_reference_ids.csv")
    ap.add_argument("--community_id", required=True)
    ap.add_argument("--challenges_ids", required=True)
    ap.add_argument("--participant_id", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    ref_ids = set()
    with open(os.path.join(args.public_ref_dir, "public_reference_ids.csv")) as fh:
        for row in csv.DictReader(fh):
            ref_ids.add(row["entry_id"])

    submitted = {}
    with open(args.input) as fh:
        reader = csv.DictReader(fh)
        if "entry_id" not in reader.fieldnames or "raw_score" not in reader.fieldnames:
            result = {"status": "error", "reason": "missing required columns entry_id,raw_score"}
            json.dump(result, open(os.path.join(args.outdir, "validation_result.json"), "w"), indent=2)
            sys.exit(1)
        for row in reader:
            submitted[row["entry_id"]] = row["raw_score"]

    missing = sorted(ref_ids - set(submitted))
    unexpected = sorted(set(submitted) - ref_ids)
    coverage = 1 - len(missing) / len(ref_ids) if ref_ids else 0

    result = {
        "status": "ok" if coverage > 0.5 else "error",
        "community_id": args.community_id,
        "challenges_ids": args.challenges_ids,
        "participant_id": args.participant_id,
        "n_reference_entries": len(ref_ids),
        "n_submitted_entries": len(submitted),
        "n_missing": len(missing),
        "n_unexpected": len(unexpected),
        "coverage": round(coverage, 4),
        "missing_entries_sample": missing[:10],
    }
    json.dump(result, open(os.path.join(args.outdir, "validation_result.json"), "w"), indent=2)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "ok" else 1)

if __name__ == "__main__":
    main()
