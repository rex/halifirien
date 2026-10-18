from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from app.builder import BuildContext, LiveInputs, build_document
from app.cli import schema
from app.document import StatusDocument
from app.guard import PublishRefusedError, _validator, render_public
from app.live import FiringAlert
from app.topology import Topology
from tests.conftest import TOPOLOGY

CTX = BuildContext(
    now=datetime(2026, 10, 18, 18, tzinfo=UTC),
    interval=timedelta(minutes=15),
    version="1.2.3",
    days=5,
)


def document(summary: str | None = None) -> StatusDocument:
    alerts = [
        FiringAlert(
            name="PoolUnhealthy",
            severity="critical",
            since=None,
            summary=summary,
            labels={"alertname": "PoolUnhealthy", "target": "erebor"},
        )
    ]
    return build_document(Topology.model_validate(TOPOLOGY), LiveInputs(alerts=alerts), CTX)


def test_committed_schema_matches_the_models() -> None:
    assert schema(check=True) == 0


def test_a_clean_document_renders_compact_json() -> None:
    body = render_public(document("pool2 DEGRADED"))
    payload = json.loads(body)
    assert payload["posture"] == "degraded"
    assert payload["nodes"][0]["alerts"][0]["summary"] == "pool2 DEGRADED"
    assert "future_field" not in body.decode()


# Assembled at run time so no scanner (pre-commit, GitHub push protection) sees a credential
# shape in the source.
LEAKS = [
    "see " + "op:" + "//vault/item/field",
    "key " + "AK" + "IA" + "ABCDEFGHIJKLMNOP leaked",
    "-----BEGIN " + "OPENSSH " + "PRIVATE KEY-----",
    "to" + "ken=" + "abcdefgh12345678",
    "gh" + "p_" + "abcdefghij" * 3,
]


@pytest.mark.parametrize("leak", LEAKS)
def test_secret_like_strings_refuse_the_whole_document(leak: str) -> None:
    with pytest.raises(PublishRefusedError, match="secret-like"):
        render_public(document(leak))


def test_the_schema_closes_every_object() -> None:
    payload = json.loads(document().model_dump_json())
    assert _validator().is_valid(payload)
    payload["nodes"][0]["serial"] = "anything"
    assert not _validator().is_valid(payload)
    del payload["nodes"][0]["serial"]
    payload["extra"] = 1
    assert not _validator().is_valid(payload)
