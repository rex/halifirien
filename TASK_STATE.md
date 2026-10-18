# TASK_STATE — halifirien v1

> Source of truth for in-flight work. Committed; survives sessions and compactions.
>
> Rivendell: rex/halifirien#1 (parent, under rex/homepage#16) · #2 service ·
> rex/homelab-inventory#47 topology + stack · rex/homepage#17 publish leg.
> Branch: `main` (trunk) · Owner: Pierce · Last update: 2026-10-18 by Claude Opus 5.5

## 0. TL;DR for a fresh agent session

The service is built and tested (v0.2.0): sources, mapping, state rules, fail-closed gate,
dry-run/S3 publishers, loop, routes, Dockerfile, Gitea CI. **Next:** homelab-inventory#47,
which renders `topology.json` and declares the ring stack (dry run). Then confirm the Gitea
pull mirror builds the image and Flux runs the pod. Publishing (homepage#17) waits on Pierce
minting the IAM key.

## Standing user directives

- Push only; never an inbound path from the internet (VIBE D1).
- Full disclosure of topology, including names, roles, hardware, addressing and VLANs (D2).
- 15-minute cadence. The website's /homelab page is on standby (rex/homepage#16).

## 1. Phases

| # | Phase | Status | Exit criteria |
|---|---|---|---|
| 1 | Service | ✅ done | gates green; image builds on the mirror |
| 2 | Topology + stack | ⏸ pending | renderer in inventory; pod runs in the ring in dry run |
| 3 | Publish | ⏸ pending | IAM writer, deploy.yml exclude, key in 1Password, PUBLISH_ENABLED |

## 3. Blockers / open questions

- The access key for the S3 writer is Pierce's to mint (agents never see the value).

## 4. Recent decisions (append-only, newest first)

- 2026-10-18 — Check→node mapping order: declared key, then hostname, then name; alerts on
  target/namespace/job/kubernetes_io_hostname/host/instance (agent; documented in app/attach.py).
- 2026-10-18 — VIBE D1–D5 (push only, full disclosure, public repo, loop not CronJob, tests).

## 5. Next actions (ordered)

1. homelab-inventory: `tools/render_halifirien_topology.py`, a `halifirien-topology`
   config source, `stacks/halifirien.yml`; commit and push the rex/isengard output.
2. Confirm the Gitea pull mirror exists and its CI pushed `rex/halifirien:latest`.
3. `GET https://halifirien.thelab.host/api/status`: review orphan checks and unknowns with Pierce.
4. rex/homepage#17: the publish leg.

## 6. Handoff note

2026-10-18: scaffold, onboarding to Rivendell (github-estate 0.23.0) and the service v0.2.0
landed in one session. Nothing is deployed yet.
