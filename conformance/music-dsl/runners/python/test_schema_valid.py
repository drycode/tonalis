"""Every conformance/music-dsl case validates against case.schema.json (additionalProperties:false).
This is the C1 guard: a port that emits an extra/renamed/missing field, or a malformed case,
fails loudly instead of 'agreeing by accident'. (leadsheet has the schema but no validator; we add one.)"""
import json
from pathlib import Path

import jsonschema

SCHEMA = Path(__file__).resolve().parents[2] / "schema" / "case.schema.json"
CASES = Path(__file__).resolve().parents[2] / "cases"


def test_every_case_matches_schema():
    schema = json.loads(SCHEMA.read_text())
    validator = jsonschema.Draft7Validator(schema)
    errors = []
    for f in sorted(CASES.rglob("*.json")):
        for case in json.loads(f.read_text()):
            for e in validator.iter_errors(case):
                errors.append(f"{f.name}::{case.get('name','?')}: {e.message}")
    assert not errors, "schema violations:\n" + "\n".join(errors)
