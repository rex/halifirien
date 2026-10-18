# TASK_STATE — halifirien v1

> Source of truth for in-flight work. Committed; survives sessions and compactions.
>
> Rivendell: rex/halifirien#1 (done, under rex/homepage#16): #2 service, homelab-inventory#47
> topology + stack, homepage#17 publish leg, all done. Open follow-ups, under rex/homepage#16:
> rex/homelab-inventory#48 (probes), #49 (orphan probes).
> Branch: `main` (trunk) · Owner: Pierce · Last update: 2026-10-18 by Claude Opus 5.5

## 0. TL;DR for a fresh agent session

**v1 is live.** Every 15 minutes the beacon publishes
https://piercemoore.com/status/status.json: 70 nodes, 22 links, Gatus checks, 90-day uptime
and firing alerts, gated by the committed schema and the secret scrubber. In-lab, each cycle
is at https://halifirien.thelab.host/api/status. The writer is `halifirien-status-writer`
(homepage infra `PiercemooreStatusWriterStack`, PutObject on `status/*` only). The agentic
vault item named for that user holds its credentials. Rotation is homepage
`make mint-status-key` (see homepage infra/README.md). Next is the website's /homelab page
(rex/homepage#16, on standby), which reads that file.

## Standing user directives

- Push only; never an inbound path from the internet (VIBE D1).
- Full disclosure of topology, including names, roles, hardware, addressing and VLANs (D2).
- 15-minute cadence. The website's /homelab page is on standby (rex/homepage#16).

## 1. Phases

| # | Phase | Status | Exit criteria |
|---|---|---|---|
| 1 | Service | ✅ done | gates green; image builds on the mirror (Gitea run 15698) |
| 2 | Topology + stack | ✅ done | pod Running 1/1; /api/status serves the document |
| 3 | Publish | ✅ done | live at piercemoore.com/status/status.json; survives a site deploy |

## 3. Blockers / open questions

- The access key for the S3 writer is Pierce's to mint (agents never see the value).
- 27 nodes are `unknown` (no probe) and 11 probes are orphans; see inventory #48 and #49.

## 4. Recent decisions (append-only, newest first)

- 2026-10-18: `topology_version` is a 12-hex content hash, not the inventory VERSION, which
  every commit bumps (homelab-inventory 0.51.0).
- 2026-10-18: The check→node mapping order is declared key, then hostname, then name. Alerts
  attach on target/namespace/job/kubernetes_io_hostname/host/instance (app/attach.py).
- 2026-10-18: VIBE D1–D5 (push only, full disclosure, public repo, loop not CronJob, tests).

## 5. Next actions (ordered)

1. Done 2026-10-18: rex/homepage#17, the publish leg (Pierce: "do it and go ahead and mint the
   key and create the 1password item").
2. rex/homelab-inventory#48: probes for the unknown nodes. #49: homes for the orphan probes.
3. rex/homepage#16: the /homelab page that reads `status/status.json` (on standby).

## 6. Handoff note

2026-10-18, one session:
- scaffold;
- github-estate onboarding (0.23.0);
- service v0.2.0–v0.3.x;
- the Gitea pull mirror (Actions enabled), CI green;
- inventory renderer and stack (0.50.0/0.51.0);
- isengard 0.227.0–0.227.2, landed by Flux.

The first live cycle: posture `degraded` (minas-tirith pool2, wideframe-marks), 41 ok,
27 unknown, 0 down.
