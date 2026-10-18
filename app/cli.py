"""Repo tooling: `python -m app.cli schema [--check]` and `python -m app.cli preview`."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.config import get_settings
from app.guard import SCHEMA_PATH, schema_document
from app.publisher import NullPublisher
from app.runner import Beacon


def _schema_text() -> str:
    return json.dumps(schema_document(), indent=2, sort_keys=True) + "\n"


def schema(check: bool) -> int:
    """Write the committed JSON Schema from the models, or fail if it has drifted."""
    wanted = _schema_text()
    current = SCHEMA_PATH.read_text(encoding="utf-8") if SCHEMA_PATH.exists() else ""
    if check:
        if current != wanted:
            print(f"{SCHEMA_PATH} is stale: run `make schema`", file=sys.stderr)
            return 1
        return 0
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(wanted, encoding="utf-8")
    return 0


def preview() -> int:
    """One dry-run cycle against the configured sources; prints the document or the error."""
    beacon = Beacon(get_settings(), NullPublisher())
    report = asyncio.run(beacon.run_once())
    if report.source_errors:
        print(json.dumps({"source_errors": report.source_errors}, indent=2), file=sys.stderr)
    if report.orphan_checks:
        print(json.dumps({"orphan_checks": report.orphan_checks}, indent=2), file=sys.stderr)
    if beacon.document is None:
        print(report.error, file=sys.stderr)
        return 1
    print(beacon.document.model_dump_json(indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Dispatch a subcommand."""
    parser = argparse.ArgumentParser(prog="halifirien")
    sub = parser.add_subparsers(dest="command", required=True)
    schema_cmd = sub.add_parser("schema", help="write or check schema/status.schema.json")
    schema_cmd.add_argument("--check", action="store_true")
    sub.add_parser("preview", help="run one dry-run cycle and print the document")
    args = parser.parse_args(argv)
    if args.command == "schema":
        return schema(args.check)
    return preview()


if __name__ == "__main__":
    raise SystemExit(main())
