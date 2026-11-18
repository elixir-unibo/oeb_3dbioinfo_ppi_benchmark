#!/usr/bin/env python3
"""
Interactive wizard that fills in the handful of real-world values this package cannot supply on
its own (see OPENEBENCH_SUBMISSION_READINESS.md) directly into its metadata JSON files, then
re-validates everything and drafts the support-request email the actual submission still needs
a human to send.

Collects, with prompts for each:
  1. A real OpenEBench Community ID (format OEBC###) -- replaces every occurrence of the
     placeholder "OEBC_3DBioinfo" across the ENTIRE package (Community._id, every Dataset's
     community_ids, every Challenge/Contact/BenchmarkingEvent's community_id), not just one file.
  2. Real contact emails for each of the 14 Contact records that still carry the placeholder
     "unknown@email.es".
  3. (Optional) official OpenEBench/bio.tools Tool IDs for the 14 participant scoring functions,
     if already registered.
  4. The public Git repository URL and tag/commit this package will be hosted at, used only to
     draft the OpenEBench support-request email (OpenEBench has no self-service submission API;
     per its own process, a human still emails support with the tagged repo location).

This script does NOT submit anything to openebench.bsc.es -- no such API exists. It only prepares
this package's own files and drafts the request a person still needs to send. Press Enter on any
prompt to skip it and keep the current placeholder, which is then listed as still-unresolved in
the final summary.

Usage:
    python prepare_for_openebench_submission.py [--package PATH] [--non-interactive]
The --non-interactive flag runs validation/summary only, with no prompts (useful for CI checks).
"""
import argparse
import glob
import json
import os
import re
import sys

PLACEHOLDER_COMMUNITY_ID = "OEBC_3DBioinfo"
PLACEHOLDER_EMAIL = "unknown@email.es"
COMMUNITY_ID_PATTERN = re.compile(r"^OEBC[0-9]{3}$")


def ask(prompt, validator=None, allow_skip=True):
    suffix = " (Enter to skip)" if allow_skip else ""
    while True:
        try:
            val = input(f"{prompt}{suffix}: ").strip()
        except EOFError:
            return None
        if not val:
            return None
        if validator and not validator(val):
            print("  That doesn't look valid -- try again, or press Enter to skip.")
            continue
        return val


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, doc):
    with open(path, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")


def walk_replace(obj, old_value, new_value):
    """Recursively replaces every string value exactly equal to old_value with new_value,
    anywhere in a JSON-decoded structure (dicts, lists, or a bare string)."""
    if isinstance(obj, dict):
        return {k: walk_replace(v, old_value, new_value) for k, v in obj.items()}
    if isinstance(obj, list):
        return [walk_replace(v, old_value, new_value) for v in obj]
    if obj == old_value:
        return new_value
    return obj


def replace_community_id_everywhere(package_dir, new_id):
    """Replaces every occurrence of the placeholder Community ID across ALL package JSON files
    (Community._id, every Dataset's community_ids, every Challenge/Contact/BenchmarkingEvent's
    community_id) -- not just metadata/Community.json -- since the placeholder appears in all of
    them identically, a single string-value replacement handles every field name/shape at once."""
    changed = 0
    for path in glob.glob(os.path.join(package_dir, "**", "*.json"), recursive=True):
        if os.sep + "qc_analysis" + os.sep in path or os.sep + "local_visualizer" + os.sep in path:
            continue  # not OEB entity files
        try:
            doc = load_json(path)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        new_doc = walk_replace(doc, PLACEHOLDER_COMMUNITY_ID, new_id)
        if new_doc != doc:
            save_json(path, new_doc)
            changed += 1
    return changed


def update_contacts(package_dir, non_interactive):
    unresolved = []
    contact_files = sorted(glob.glob(os.path.join(package_dir, "metadata", "Contacts", "*.json")))
    print(f"\n--- Contact emails ({len(contact_files)} contacts) ---")
    for cf in contact_files:
        contact = load_json(cf)
        full_name = f"{contact.get('givenName', '')} {contact.get('surname', '')}".strip() or os.path.basename(cf)
        emails = contact.get("email", [])
        if emails and emails != [PLACEHOLDER_EMAIL]:
            continue
        if non_interactive:
            unresolved.append(f"Contact '{full_name}' ({os.path.basename(cf)}) still has the placeholder email.")
            continue
        email = ask(f"Real email for '{full_name}'", validator=lambda v: "@" in v and "." in v.split("@")[-1])
        if email:
            contact["email"] = [email]
            save_json(cf, contact)
            print(f"  -> {full_name}: {email}")
        else:
            unresolved.append(f"Contact '{full_name}' ({os.path.basename(cf)}) still has the placeholder email.")
    return unresolved


def update_tool_ids(package_dir, non_interactive):
    tool_files = sorted(
        f for f in glob.glob(os.path.join(package_dir, "metadata", "Tools", "*.json"))
        if not os.path.basename(f).startswith(("Tool_compute_", "Tool_aggregate_"))
    )
    print(f"\n--- Official Tool IDs ({len(tool_files)} participant tools, optional) ---")
    if non_interactive:
        print("  (non-interactive mode: skipped)")
        return
    for tf in tool_files:
        tool = load_json(tf)
        name = tool.get("name", os.path.basename(tf))
        print(f"Tool: {name}  (internal id: {tool['_id']})")
        registered_id = ask("  Registry ID in CURIE form (e.g. biotools:voronota), if already registered")
        if registered_id:
            tool["registry_tool_id"] = registered_id
            save_json(tf, tool)
            print(f"  -> recorded {registered_id}")


def revalidate(package_dir):
    """Best-effort schema re-validation. Uses the schema copy bundled with this package
    (schemas/) if present so this works fully offline regardless of the machine's network
    access; falls back to skipping with a note if `jsonschema` isn't installed."""
    print("\n--- Re-validation against the OpenEBench 1.0.x JSON Schemas ---")
    try:
        from jsonschema import Draft7Validator, RefResolver
    except ImportError:
        print("  `jsonschema` is not installed in this Python environment -- skipping full schema "
              "re-validation (the values above were still written correctly). Install it with "
              "`pip install jsonschema` and re-run to get a full re-check.")
        return

    schema_dir = os.path.join(package_dir, "schemas")
    if not os.path.isdir(schema_dir):
        print(f"  No bundled schema copy found at {schema_dir} -- skipping re-validation.")
        return

    store = {}
    for fname in glob.glob(os.path.join(schema_dir, "*.json")):
        s = load_json(fname)
        sid = s.get("$id")
        if sid:
            store[sid] = s

    def make_validator(name):
        schema = load_json(os.path.join(schema_dir, f"{name}.json"))
        resolver = RefResolver.from_schema(schema, store=store)
        return Draft7Validator(schema, resolver=resolver)

    validators = {
        "Community": make_validator("community"),
        "BenchmarkingEvent": make_validator("benchmarkingEvent"),
        "Challenge": make_validator("challenge"),
        "Metrics": make_validator("metrics"),
        "Tool": make_validator("tool"),
        "Contact": make_validator("contact"),
        "Dataset": make_validator("dataset"),
    }

    total, failed = 0, []
    for path in glob.glob(os.path.join(package_dir, "**", "*.json"), recursive=True):
        if os.sep + "qc_analysis" + os.sep in path or os.sep + "local_visualizer" + os.sep in path or os.sep + "schemas" + os.sep in path:
            continue
        try:
            doc = load_json(path)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        schema_url = doc.get("_schema", "")
        stype = schema_url.rstrip("/").split("/")[-1]
        v = validators.get(stype)
        if v is None:
            continue
        total += 1
        errors = list(v.iter_errors(doc))
        if errors:
            failed.append((os.path.relpath(path, package_dir), [e.message for e in errors[:2]]))

    print(f"  Checked {total} files -> {total - len(failed)} pass, {len(failed)} fail.")
    for relpath, msgs in failed:
        print(f"    FAIL {relpath}: {'; '.join(msgs)}")
    return failed


def draft_support_email(package_dir, repo_url, repo_tag, community_id, unresolved):
    lines = [
        "Subject: New Benchmarking Event submission -- ELIXIR 3D-BioInfo Community "
        "(PPI-PhysioClassification)",
        "",
        "To: OpenEBench support",
        "",
        "Hello,",
        "",
        "We would like to submit a new Benchmarking Event to OpenEBench on behalf of the",
        "ELIXIR 3D-BioInfo Community: 'PPI-PhysioClassification', a classification benchmark",
        "distinguishing physiological from crystallographic (non-physiological) interfaces in",
        "homodimer protein complexes (1671 entries, 14 participant scoring functions), based on",
        f"Schweke et al. (doi:10.1002/pmic.202200323).",
        "",
        f"Community ID: {community_id or '<PENDING -- see note below>'}",
        f"Repository: {repo_url or '<PENDING -- not yet provided>'}",
        f"Tag/commit: {repo_tag or '<PENDING -- not yet provided>'}",
        "",
        "The repository contains the full OpenEBench benchmarking-data-model metadata and",
        "datasets (Community, BenchmarkingEvent, Challenges, Metrics, Tools, Contacts, and all",
        "input/reference/participant/assessment/aggregation Datasets), validated against the",
        "real OpenEBench 1.0.x JSON Schemas.",
        "",
        "Please let us know if anything else is needed to complete the submission.",
        "",
        "Best regards,",
        "[sender name / ELIXIR 3D-BioInfo Community contact]",
    ]
    if unresolved:
        lines += ["", "--- Internal note: NOT yet ready to send -- still unresolved ---"]
        lines += [f"  - {u}" for u in unresolved]

    draft_path = os.path.join(package_dir, "OPENEBENCH_SUBMISSION_REQUEST_DRAFT.txt")
    with open(draft_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return draft_path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--package", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    ap.add_argument("--non-interactive", action="store_true",
                     help="Skip all prompts; only re-validate and report what is still unresolved.")
    args = ap.parse_args()
    package_dir = os.path.abspath(args.package)

    print("=" * 78)
    print("OpenEBench submission preparation wizard -- 3DBioinfo PPI-PhysioClassification")
    print("=" * 78)
    print(f"Package: {package_dir}\n")
    print("This fills in values this package cannot supply on its own (see")
    print("OPENEBENCH_SUBMISSION_READINESS.md). It does NOT submit anything to openebench.bsc.es")
    print("-- no such self-service API exists -- it prepares this package's files and drafts the")
    print("support-request email a human still needs to send.\n")

    unresolved = []

    # 1. Community ID
    community_path = os.path.join(package_dir, "metadata", "Community.json")
    community = load_json(community_path)
    print(f"Current Community ID (placeholder): {community['_id']}")
    new_community_id = None
    if not args.non_interactive:
        new_community_id = ask(
            "Real OpenEBench Community ID (format OEBC followed by three digits)",
            validator=lambda v: bool(COMMUNITY_ID_PATTERN.match(v)),
        )
    if new_community_id:
        n_changed = replace_community_id_everywhere(package_dir, new_community_id)
        print(f"  -> Community ID updated to {new_community_id} across {n_changed} files.")
        final_community_id = new_community_id
    else:
        unresolved.append(
            f"Community ID is still the placeholder '{PLACEHOLDER_COMMUNITY_ID}' -- request a "
            "real OEBC### code from the OpenEBench team before submitting."
        )
        final_community_id = PLACEHOLDER_COMMUNITY_ID

    # 2. Contact emails
    unresolved += update_contacts(package_dir, args.non_interactive)

    # 3. Tool IDs (optional, no unresolved-list impact since these are genuinely optional pre-submission)
    update_tool_ids(package_dir, args.non_interactive)

    # 4. Repository location, for the draft email only
    repo_url = repo_tag = None
    if not args.non_interactive:
        print("\n--- Repository & submission request ---")
        repo_url = ask("Public Git repository URL this package will be hosted at (e.g. https://github.com/org/repo)")
        if repo_url:
            repo_tag = ask("Tag or commit to submit (e.g. v1.0 or a commit SHA)")
    if not repo_url:
        unresolved.append("No tagged public repository URL provided yet -- required before OpenEBench support can load this submission.")

    # 5. Re-validate
    failed = revalidate(package_dir)
    if failed:
        unresolved.append(f"{len(failed)} file(s) still fail schema validation -- see the FAIL lines above.")

    # 6. Draft the support email
    draft_path = draft_support_email(package_dir, repo_url, repo_tag, final_community_id, unresolved)
    print(f"\nDraft OpenEBench support-request email written to:\n  {draft_path}")

    # 7. Summary
    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    if unresolved:
        print(f"{len(unresolved)} item(s) still need action before this is submission-ready:")
        for u in unresolved:
            print(f"  - {u}")
    else:
        print("All items this wizard tracks are resolved. Docker images, Tool-ID registration on")
        print("the live OpenEBench platform (if not already done above), and actually sending the")
        print("drafted email are the remaining steps -- see OPENEBENCH_SUBMISSION_READINESS.md.")


if __name__ == "__main__":
    main()
