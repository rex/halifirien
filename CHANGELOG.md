# Changelog

All notable changes to this project are documented here. This project
follows [Semantic Versioning](https://semver.org/) and
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Format:

```markdown
## [X.Y.Z] — YYYY-MM-DD — Agent: <name>
### Added | Changed | Fixed | Removed | Deprecated | Security
- <what changed, in imperative voice>
```

**Every commit requires a version bump and a matching entry here.** The
`scripts/check_version_bumped.py` gate enforces this; `auto-commit.sh`
calls `scripts/bump_version.py <level>` before commit.

**Bump level guidance** (agent decides per slice):
- `patch` — bug fix, documentation change, refactor with no behavior change
- `minor` — new feature, new public API, any backward-compatible addition
- `major` — breaking change, removal, incompatible behavior change

**Agent attribution is required.** Every entry names the agent (or human)
that authored the change. This is how we keep `git blame` honest when
multiple agents and humans work on the same slice.

Append new entries at the top. One entry per commit (same cadence as
version bumps).

---

## [0.3.0] — 2026-10-18 — Agent: Claude Opus 5.5
### Changed
- Edges are physical links from the inventory's cabling (ethernet, dac, usb,
  power) and carry `speed_mbps`.
- `topology_generated_at` is now `topology_version` (the inventory's
  VERSION). The rendered topology is deterministic, so an unchanged inventory
  never rolls the pod.
- First live dry run against the lab (homelab-inventory 0.49.0 topology):
  69 nodes, 22 links, posture `degraded` (minas-tirith pool2), 40 ok with 19
  days of uptime, 27 unknown, 11 orphan probes, 52 KB.

## [0.2.0] — 2026-10-18 — Agent: Claude Opus 5.5
### Added
- The beacon (rex/halifirien#2). It merges the inventory-rendered topology
  with Gatus (latest checks), VictoriaMetrics (90 days of daily uptime) and
  Alertmanager (firing warning/critical) into one StatusDocument, every 15
  minutes. A source that fails leaves its nodes `unknown`; it never stops the
  cycle.
- The public contract: `app/document.py` and the generated
  `schema/status.schema.json` (closed objects). `make schema` writes it;
  `make typecheck` fails on drift.
- A fail-closed gate (`app/guard.py`): schema validation plus secret
  patterns. A refused document is never published.
- Publishers: dry run (default) or S3 PutObject to `status/status.json` with
  Cache-Control, when `PUBLISH_ENABLED=true`.
- `/api/health` (503 after two intervals without a good cycle),
  `/api/status` (in-lab preview: last document, source errors, orphan checks),
  `/api/cycle`, and `/api/docs`.
- Dockerfile (non-root, uv, HEALTHCHECK), Gitea Actions CI on the pull mirror
  (validate, test, then push the image), a full-history gitleaks workflow for
  the public repo, the MIT license and a README.
- 24 tests: sources, mapping, state rules, the gate, the loop, the routes, S3.

## [0.1.0] — 2026-10-18 — Agent: Claude Opus 5.5
### Added
- Scaffold from `agentic-skeleton` (`/scaffold`): AGENTS.md, VIBE.yaml with
  decisions D1–D5 (push only, full disclosure, public repo, long-running
  loop, tests required), TASK_STATE.md, Makefile, gates, `.claude/` config.
