"""The JSON Schema SSOT must be valid 2020-12 and its cross-file refs resolvable."""

from __future__ import annotations

import json

import pytest
from conftest import all_schema_paths, load_schema
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"


@pytest.mark.parametrize("path", all_schema_paths(), ids=lambda p: p.name)
def test_schema_is_valid_2020_12(path):
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema.get("$schema") == DRAFT_2020_12, f"{path.name} not declared draft 2020-12"
    assert "$id" in schema, f"{path.name} missing $id (needed for cross-file $ref resolution)"
    # Raises SchemaError if the schema itself is malformed.
    Draft202012Validator.check_schema(schema)


def _registry() -> Registry:
    """Register every schema by its $id so cross-file $ref (absolute URL) resolves."""
    resources = []
    for path in all_schema_paths():
        schema = json.loads(path.read_text(encoding="utf-8"))
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def test_cross_file_ref_resolves_and_validates():
    """library.schema.json#/$defs/SearchResultSetDTO $refs search.schema.json across files.

    Prove a standard validator (not just codegen) resolves it and that a real
    SearchResultPageDTO-shaped instance validates through the cross-file ref.
    """
    registry = _registry()
    library = load_schema("dtos/library.schema.json")
    validator = Draft202012Validator(
        {"$ref": f"{library['$id']}#/$defs/SearchResultSetDTO"}, registry=registry
    )
    page = {
        "cards": [
            {
                "title": "T",
                "authors": ["A"],
                "year": 2020,
                "arxivId": "2106.01234v1",
                "abstractSnippet": "snippet",
                "relevance": 1,
                "arxivUrl": "https://arxiv.org/abs/2106.01234",
            }
        ],
        "meta": {"resultCount": 1, "degraded": False},
    }
    validator.validate(page)  # raises ValidationError on failure

    # additionalProperties:false propagates through the ref — internal field rejected.
    bad = {**page}
    bad["cards"] = [{**page["cards"][0], "vector": [0.1]}]
    with pytest.raises(ValidationError):
        validator.validate(bad)
