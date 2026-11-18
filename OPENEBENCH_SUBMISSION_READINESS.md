# Status of the OpenEBench package (release 1.1.0)

This package contains the metadata, datasets and workflow of the 3D-BioInfo PPI benchmark in the OpenEBench data model. It is **not yet registered on openebench.bsc.es**. OpenEBench has no self-service route for a new benchmarking event: the OpenEBench team loads the package from a repository URL and a release tag, after a support request.

## Checked

- 149 of the 150 metadata and dataset records validate against the OpenEBench 1.0.x JSON Schemas (a copy is in `schemas/`). The exception is `metadata/Community.json`, whose identifier is a placeholder (see below).
- The 14 participant dataset records state the number of entries of their predictions file.
- `workflow/run_pipeline.sh` was run from a clean copy of the package on the 14 participants: all 14 submissions passed the validation step, the metrics were computed, and the consolidation step produced the aggregated results and the leaderboard figure.

## Still to do on the platform side

1. **Community identifier.** `metadata/Community.json` has the placeholder `OEBC_3DBioinfo`. OpenEBench requires an assigned code of the form `OEBC###`. `workflow/prepare_for_openebench_submission.py` replaces the placeholder everywhere once the code is known.
2. **Tools.** The 14 scoring methods have to be registered as OpenEBench tools to receive official identifiers.
3. **Containers.** `workflow/Dockerfile.validate`, `Dockerfile.compute_metrics` and `Dockerfile.consolidate` are drafts. They have not been built, tested or published, and matplotlib is not pinned to a version.
4. **Contacts.** The 13 group contacts in `metadata/Contacts/` are placeholders (`Contact <group> group`, e-mail `unknown@email.es`). The contact person of each group and the real e-mail address have to be entered; the preparation script asks for the e-mail address, the names are edited in the files.
5. **Support request** to OpenEBench with the repository URL and the release tag. The preparation script drafts it.

## Note on the random-forest consensus

The scores of `RF_Consensus_top221` are the leave-one-out probabilities of the original benchmark repository, used unchanged. Homologous entries are not removed from the training set, so its AUROC is an upper estimate with respect to the other methods, which are single scores.
