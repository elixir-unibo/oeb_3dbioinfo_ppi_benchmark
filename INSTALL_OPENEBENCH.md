# Implementing the 3D-BioInfo PPI benchmark on OpenEBench

This package describes the benchmark *Discrimination of physiological versus crystallographic protein homodimer interfaces* (challenge `PPI-PhysioClassification`) in the OpenEBench Scientific Benchmarking Data Model. It is **not yet registered** on openebench.bsc.es. OpenEBench has no self-service upload: the OpenEBench team loads a package from a repository URL and a tag after a support request. This file explains what is in the package, how to check it locally, and what remains to be done.

## 1. Contents

| Folder | Content |
|---|---|
| `metadata/` | Community, Benchmarking Event, Challenge, Metrics, Tools and Contacts records (JSON) |
| `datasets/` | input, public reference, metrics reference (gold-standard labels, cross-validation fold assignments), participant (14 methods), assessment and aggregation datasets |
| `workflow/` | the three workflow steps (`validate.py`, `compute_metrics.py`, `consolidate.py`), `run_pipeline.sh`, a Nextflow skeleton, three Dockerfiles, `prepare_for_openebench_submission.py` |
| `schemas/` | offline copy of the OpenEBench 1.0.x JSON Schemas |
| `qc_analysis/` | cross-validated results and quality-control analyses (see its README) |

## 2. Check the package locally

Requirements: Python 3.8 or later. `matplotlib` is needed only by the consolidation step (the leaderboard figure) and `jsonschema` only for the schema check.

```
bash workflow/run_pipeline.sh [output_dir]
```

The runner validates each of the 14 participants, computes the metrics and consolidates them. A good run ends with `Done.`, one `validation_result.json` with `"status": "ok"` for each participant under `validation_out/`, and `consolidated/data_model_export.json` listing 14 participants. The individual steps can be run on their own:

```
python3 workflow/validate.py --input <predictions.csv> --public_ref_dir datasets/public_reference \
    --community_id OEBC_3DBioinfo --challenges_ids 3DBioinfo:PPI-PhysioClassification \
    --participant_id <name> --outdir <dir>
python3 workflow/compute_metrics.py --input <predictions.csv> --goldstandard_dir datasets/metrics_reference \
    --community_id OEBC_3DBioinfo --challenges_ids 3DBioinfo:PPI-PhysioClassification \
    --participant_id <name> --outdir <dir>
python3 workflow/consolidate.py --assess_dir <dir with all assessments> --community_id OEBC_3DBioinfo \
    --challenge_id 3DBioinfo:PPI-PhysioClassification --outdir <dir>
```

A predictions file has the columns `entry_id`, `raw_score` and `raw_score_oriented` (higher means more likely physiological).

## 3. Fill in the values only OpenEBench or the groups can supply

Run the preparation script from the package folder:

```
python3 workflow/prepare_for_openebench_submission.py              # asks for each value; Enter skips it
python3 workflow/prepare_for_openebench_submission.py --non-interactive   # checks only, lists what is open
```

It asks for:
1. the **Community ID** assigned by OpenEBench (format `OEBC###`). It replaces the placeholder `OEBC_3DBioinfo` in every record;
2. a real **e-mail address** for each of the 14 contacts (the placeholder is `unknown@email.es`). The contact records are placeholders as well (`Contact <group> group`): edit `givenName` and `surname` by hand in each file of `metadata/Contacts/` once the contact person of the group is known; the script asks only for the e-mail;
3. optionally the **registry ID** of each tool in CURIE form (for example `biotools:...`), written to `registry_tool_id`;
4. the **repository URL and tag** of this package, used to draft the support request (`OPENEBENCH_SUBMISSION_REQUEST_DRAFT.txt`).

It then validates all records against the schemas (150 files; all pass once the Community ID is set) and writes the draft. It sends nothing.

## 4. Containers

OpenEBench runs each workflow step in a container. The three Dockerfiles in `workflow/` are drafts: they have **not been built, tested or published**. Build them with `workflow/` as the build context:

```
docker build -f workflow/Dockerfile.validate        -t <registry>/ppi-validate:1.2.0        workflow/
docker build -f workflow/Dockerfile.compute_metrics -t <registry>/ppi-compute-metrics:1.2.0 workflow/
docker build -f workflow/Dockerfile.consolidate     -t <registry>/ppi-consolidate:1.2.0     workflow/
```

Run each image on one participant with the arguments of section 2 and compare the result with the shell runner. `Dockerfile.consolidate` installs `matplotlib` without a version: pin the version you tested. `workflow/nextflow_main.nf` runs the validation and metric steps for one participant with the local executor and no container (`nextflow run workflow/nextflow_main.nf --predictionsFile <predictions.csv> --participant_name <name>`, from the package folder; it gave the same assessment as `run_pipeline.sh` for `Oliva_CP`). The consolidation process is defined there but not connected, and no process names a container image. For the whole benchmark use `run_pipeline.sh`.

## 5. Register the tools

The 14 scoring methods have to be registered as OpenEBench tools to receive official identifiers (step 3, item 3).

## 6. Send the request to OpenEBench

Send the drafted request to the OpenEBench support team with the repository URL and the release tag (`v1.2.0` for this release). Ask them, in the same message:
- for the Community ID, if 3D-BioInfo does not have one;
- whether the package should sit at the repository root, as here, or in a subfolder;
- whether they require the container images in a given registry.

## 7. Status

The current status of each item is in `OPENEBENCH_SUBMISSION_READINESS.md`. How the package was built, step by step, is in `BUILD_NOTES.md`; that file is a historical log. The random-forest consensus (`RF_Consensus_top221`) uses leave-one-out probabilities and is an upper estimate compared with the other methods.
