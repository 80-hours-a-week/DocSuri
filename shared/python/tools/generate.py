#!/usr/bin/env python
"""Generate the pydantic v2 models in ``docsuri_shared/_generated`` from the
language-neutral JSON Schema SSOT (``shared/{vector-spec,dtos,events}/*.schema.json``).

§5-B decision: the JSON Schema files are the single source of truth; the Python
types are GENERATED, never hand-edited. This script is the only thing that writes
``_generated/``. Run it after changing a schema; run it with ``--check`` in CI to
fail the build if the committed models have drifted from the schemas.

Usage::

    uv run python tools/generate.py            # regenerate _generated/ in place
    uv run python tools/generate.py --check     # fail (exit 1) if _generated/ is stale

Only ``*.schema.json`` is fed to the generator. ``vector-spec/vector-spec.yaml`` is
embedding *config*, not a per-record shape, so it is hand-mapped to constants in
``docsuri_shared/vector_spec.py`` (guarded by ``tests/test_vector_spec.py``), never
codegen'd.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[1]  # shared/python/
SHARED_ROOT = PKG_ROOT.parent  # shared/
SCHEMA_DIRS = ("vector-spec", "dtos", "events")
GENERATED_DIR = PKG_ROOT / "src" / "docsuri_shared" / "_generated"

# NOTE: datamodel-codegen inserts --custom-file-header verbatim, so every line MUST
# already be a comment (leading '#'), otherwise the generated modules are invalid Python.
FILE_HEADER = (
    "# DO NOT EDIT. Generated from the JSON Schema SSOT in shared/ by tools/generate.py.\n"
    "# Change the schema and regenerate (§5-B); never hand-edit."
)


def _stage_schemas(dest: Path) -> int:
    """Copy every ``*.schema.json`` (only) into ``dest`` preserving the group
    subdir, so cross-file ``$ref``/``$id`` resolution still works. Returns count."""
    count = 0
    for group in SCHEMA_DIRS:
        src_group = SHARED_ROOT / group
        if not src_group.is_dir():
            raise SystemExit(f"missing schema group: {src_group}")
        dest_group = dest / group
        dest_group.mkdir(parents=True, exist_ok=True)
        for schema in sorted(src_group.glob("*.schema.json")):
            shutil.copy2(schema, dest_group / schema.name)
            count += 1
    if count == 0:
        raise SystemExit("no *.schema.json files found to generate from")
    return count


def _run_codegen(input_dir: Path, output_dir: Path) -> None:
    """Run datamodel-codegen into ``output_dir`` (must be a fresh, empty dir)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "datamodel-codegen",
        "--input",
        str(input_dir),
        "--input-file-type",
        "jsonschema",
        "--output",
        str(output_dir),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        "3.11",
        "--use-standard-collections",
        "--use-union-operator",
        "--use-schema-description",
        "--field-constraints",
        "--disable-timestamp",  # deterministic output → clean --check diff
        "--custom-file-header",
        FILE_HEADER,
        "--formatters",
        "black",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise SystemExit(
            "datamodel-codegen not found on PATH — run via `uv run python tools/generate.py` "
            "(it is a dev dependency in pyproject.toml)."
        ) from exc
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"datamodel-codegen failed (rc={proc.returncode})")


def _build(output_dir: Path) -> int:
    """Stage schemas and codegen into ``output_dir`` (fresh). Returns schema count."""
    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp) / "schemas"
        n = _stage_schemas(staged)
        _run_codegen(staged, output_dir)
    return n


def generate(*, announce: bool = True) -> None:
    """Regenerate GENERATED_DIR atomically: build into a temp dir, then swap in on
    success. A codegen failure leaves the committed models untouched (no wipe-on-fail)."""
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "_generated"
        n = _build(fresh)
        if GENERATED_DIR.exists():
            shutil.rmtree(GENERATED_DIR)
        GENERATED_DIR.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(fresh, GENERATED_DIR)
    if announce:
        print(f"generated models from {n} schema files -> {GENERATED_DIR}")


def _py_files(root: Path) -> set[Path]:
    """Relative paths of the generated .py files (ignores __pycache__/.pyc noise)."""
    return {p.relative_to(root) for p in root.rglob("*.py")}


def _content_diff(committed: Path, fresh: Path) -> list[str]:
    """Content-based diff of two generated trees (NOT stat/shallow — robust to mtime
    coincidence and coarse-mtime filesystems). Compares bytes of every .py file."""
    a, b = _py_files(committed), _py_files(fresh)
    diffs: list[str] = []
    diffs += [f"  only in committed: {p}" for p in sorted(a - b)]
    diffs += [f"  only in freshly-generated: {p}" for p in sorted(b - a)]
    diffs += [
        f"  differs: {p}"
        for p in sorted(a & b)
        if (committed / p).read_bytes() != (fresh / p).read_bytes()
    ]
    return diffs


def check() -> int:
    if not GENERATED_DIR.exists():
        sys.stderr.write("drift: _generated/ does not exist — run tools/generate.py\n")
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "_generated"
        _build(fresh)
        diffs = _content_diff(GENERATED_DIR, fresh)
    if diffs:
        sys.stderr.write(
            "drift: committed _generated/ is stale vs the schemas.\n"
            "Run `uv run python tools/generate.py` and commit the result.\n"
            + "\n".join(diffs)
            + "\n"
        )
        return 1
    print("ok: _generated/ matches the schemas")
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv[1:]:
        raise SystemExit(check())
    generate()
