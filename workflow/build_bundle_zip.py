#!/usr/bin/env python3
"""Build oeb_ppi_benchmark-v<version>.zip from this repository tree (the version is read from CITATION.cff).

The zip is the single-file distribution of the OpenEBench package (metadata, datasets, workflow, schemas,
quality-control tables, documentation, licence and citation files). It is attached to each GitHub release and
is NOT committed to the repository, so it can never differ from the files that are. The web page files
(index.html, build/, data/) and the repository README are not part of the package.

Usage:  python3 workflow/build_bundle_zip.py [output_dir]      (default output_dir = current directory)
"""
import os, re, sys, zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TOP = "oeb_ppi_benchmark"
EXCLUDE_DIRS = {".git", ".github", "build", "data", "__pycache__", "_pipeline_run"}   # excluded at the repository root only
EXCLUDE_FILES = {"index.html", "README.md", ".zenodo.json", ".gitignore"}   # plus any oeb_ppi_benchmark*.zip, see collect()


def package_version():
    """Value of the `version:` key of CITATION.cff (not `cff-version`)."""
    with open(os.path.join(ROOT, "CITATION.cff"), encoding="utf-8") as fh:
        m = re.search(r'(?m)^version:\s*"?([^"\s#]+)"?', fh.read())
    if not m:
        sys.exit("No version found in CITATION.cff")
    return m.group(1)


def collect(out_path):
    """List the files of the package first, so the output zip can never be picked up while it is written."""
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        at_root = os.path.abspath(dirpath) == ROOT
        dirnames[:] = sorted(d for d in dirnames if not (at_root and d in EXCLUDE_DIRS))
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            if (at_root and (fn in EXCLUDE_FILES or (fn.startswith(TOP) and fn.endswith(".zip")))) or os.path.abspath(full) == out_path:
                continue
            files.append(full)
    return files


def main():
    outdir = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{TOP}-v{package_version()}.zip")
    files = collect(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for full in files:
            z.write(full, os.path.join(TOP, os.path.relpath(full, ROOT)))
    print(f"Wrote {out} with {len(files)} files")


if __name__ == "__main__":
    main()
