"""The last gate before the internet. Fails closed.

A document is published only if (1) it validates against the committed JSON Schema
(schema/status.schema.json, every object closed with additionalProperties: false) and
(2) no string in it, key or value, looks like a credential. Full disclosure of the lab's
shape is the point (VIBE D2); secrets are not part of the lab's shape.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from app.document import StatusDocument

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "status.schema.json"

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"op://"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|glpat-[A-Za-z0-9_-]{20,}|xox[abprs]-[A-Za-z0-9-]{10,})"
    ),
    re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key|token)\s*[=:]\s*\S{8,}"),
)


class PublishRefusedError(Exception):
    """The document failed the gate. Nothing is published this cycle."""


def schema_document() -> dict[str, Any]:
    """The JSON Schema the models describe; `make schema` writes it to SCHEMA_PATH."""
    schema = StatusDocument.model_json_schema(mode="serialization")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://github.com/rex/halifirien/blob/main/schema/status.schema.json"
    return schema


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def _strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def render_public(document: StatusDocument) -> bytes:
    """The bytes to publish. Raises PublishRefusedError rather than ever returning a bad one."""
    payload = json.loads(document.model_dump_json())
    errors = sorted(_validator().iter_errors(payload), key=lambda e: list(e.absolute_path))
    if errors:
        where = "/".join(str(p) for p in errors[0].absolute_path) or "(root)"
        raise PublishRefusedError(f"schema: {where}: {errors[0].message}")
    for text in _strings(payload):
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise PublishRefusedError(f"secret-like string matched {pattern.pattern!r}")
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
