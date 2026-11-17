# Is this package ready to generate a live page on openebench.bsc.es?

**Short answer: no, not by itself.** It contains everything that can be generated locally and
validated offline, but three things require action on the live OpenEBench platform that cannot
be done from this sandbox, plus containerization that was deliberately left as scripts, not
Docker images. Below is exactly what was checked and what remains.

## What WAS verified just now

Every metadata and dataset JSON file in the package was run through the actual OpenEBench 1.0.x
JSON Schemas (`inab/benchmarking-data-model`, draft-07, with the real `$ref`-resolving
validator) -- not just eyeballed against the TCGA example:

- **82 of 83 files pass schema validation with zero errors**: Community (structure, if the ID
  were valid), BenchmarkingEvent, all Challenges, Metrics, Tools (17), Contacts (14), and every
  Dataset instance (input, public_reference, metrics_reference, participant x14,
  assessment x27, aggregation).
- One packaging bug this check caught and fixed: 13 `cv_score_selection/group_*/
  cv_selection_results.json` files (QC diagnostics from Step 5c, not OEB Dataset instances)
  were sitting inside `datasets/` and would have been mistaken for malformed Dataset records.
  Moved to `qc_analysis/cv_score_selection/` -- they were never meant to be submitted as
  Datasets and are not referenced by any `depends_on` relationship.

## The one schema failure, and why it cannot be fixed locally

`metadata/Community.json`'s `_id` field (`"OEBC_3DBioinfo"`, a placeholder) fails the schema's
required pattern `^OEBC[0-9]{3}$`. Unlike Dataset/Tool/Challenge/Metrics/Contact -- which the
schema explicitly allows to carry an arbitrary human-readable `OriginalIdOnSub` string before
registration -- **Community has no such fallback: it must be a real, already-registered
3-digit OpenEBench community code from day one.** A web search confirms these are live,
platform-assigned numbers (e.g. `openebench.bsc.es/projects/OEBC001` for TCGA,
`.../OEBC009` for another community) -- not something this package can mint. Before
submission, whoever owns this on the ELIXIR 3D-BioInfo Community side needs to either:
(a) look up the community's existing OEBC number if 3D-BioInfo is already registered in
OpenEBench, or (b) request one from the OpenEBench team if it isn't.

## What else is needed that this package does NOT (and cannot, from here) provide

1. **Docker images.** `workflow/{validate,compute_metrics,consolidate}.py` are plain,
   dependency-free Python scripts, verified to run correctly end-to-end -- but OpenEBench's
   execution model (VRE) expects each step containerized. No Dockerfiles were written. This is
   a lightweight, mechanical follow-up (one `Dockerfile` per script, `python:3.11-slim` base,
   no non-stdlib dependencies to install) but has not been done.
2. **A tagged, public Git repository.** Submission to OpenEBench support requires "the
   repository URL and the specific tag/commit" (per the docs reviewed earlier in this
   conversation) -- this package is a local zip, not a versioned public repo.
3. **Official OpenEBench Tool IDs.** Each of the 14 scoring functions needs to be registered as
   a Tool in OpenEBench (or linked from bio.tools) to receive an official tool id before its
   Participant datasets can be published -- this is an account-holder action on the live
   platform, not something generatable offline.
4. **Real contact emails.** Every `Contact` record in this package uses a placeholder
   (`unknown@email.es`) since no real contact information was available in the source
   repository -- these need to be replaced with actual emails for the 13 groups' PIs/contacts
   before submission.
5. **No self-service submission API for a brand-new Benchmarking Event.** Per OpenEBench's own
   documentation, after the above are in place, the final step is still emailing OpenEBench
   support with the repository URL/tag so a team member loads it -- there is no API call this
   package (or any script) can make to publish a new Community/Event/Challenge directly.

## Bottom line

This package is the complete, schema-validated **data and metadata layer** plus **working
reference implementations of the three pipeline steps** -- everything that can be prepared
without platform credentials or a live account. Turning it into an actual page on
openebench.bsc.es needs: a real Community ID, Dockerized steps in a tagged public repo,
registered Tool IDs, real contact emails, and a support request -- all human/account actions
on the live platform, not generation gaps in this package.
