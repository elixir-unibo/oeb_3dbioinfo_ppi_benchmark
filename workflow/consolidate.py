#!/usr/bin/env python3
"""
OpenEBench-style Step 3: CONSOLIDATION
Merges all assessment_results.json files of a challenge into a single
aggregation Dataset instance (OEB Benchmarking Data Model JSON) and renders
the leaderboard scatter plot (SVG) + a 2D-plot JSON ready to be validated and
pushed to Level 1 / Level 2 of OpenEBench.

Usage:
    python consolidate.py --assess_dir assessment_out/ --community_id OEBC_3DBioinfo \
                           --challenge_id PPI-PhysioClassification --outdir consolidated/
"""
import argparse, glob, json, os

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assess_dir", required=True, help="directory with one assessment_results.json per participant")
    ap.add_argument("--community_id", required=True)
    ap.add_argument("--challenge_id", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    challenge_participants = []
    for f in sorted(glob.glob(os.path.join(args.assess_dir, "*", "assessment_results.json"))):
        d = json.load(open(f))
        challenge_participants.append({
            "tool_id": d["participant_id"],
            "metric_x": d["metrics"].get("AUC-ROC"),
            "metric_y": d["metrics"].get("Accuracy@threshold"),
        })

    aggregation_dataset = {
        "_schema": "https://www.elixir-europe.org/excelerate/WP2/json-schemas/1.0/Dataset",
        "community_ids": [args.community_id],
        "challenge_ids": [args.challenge_id],
        "type": "aggregation",
        "visibility": "public",
        "datalink": {
            "inline_data": {
                "challenge_participants": challenge_participants,
                "visualization": {"type": "2D-plot", "x_axis": "AUC-ROC", "y_axis": "Accuracy@threshold"},
            }
        },
    }
    out_json = os.path.join(args.outdir, "data_model_export.json")
    json.dump(aggregation_dataset, open(out_json, "w"), indent=2)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        xs = [p["metric_x"] for p in challenge_participants]
        ys = [p["metric_y"] for p in challenge_participants if p["metric_y"] is not None]
        labels = [p["tool_id"] for p in challenge_participants]
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(xs, [p["metric_y"] for p in challenge_participants])
        for x, y, l in zip(xs, [p["metric_y"] for p in challenge_participants], labels):
            if y is not None:
                ax.annotate(l, (x, y), fontsize=6)
        ax.set_xlabel("AUC-ROC")
        ax.set_ylabel("Accuracy@threshold")
        ax.set_title(f"{args.challenge_id} leaderboard")
        fig.savefig(os.path.join(args.outdir, "leaderboard.svg"))
    except ImportError:
        pass

    print(f"Wrote {out_json} with {len(challenge_participants)} participants")

if __name__ == "__main__":
    main()
