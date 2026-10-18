# halifirien

> *"The beacons of Minas Tirith! The beacons are lit!"*
> Halifirien was the last of them, the one on the border that called to Rohan.

halifirien is the last beacon of my homelab. Every fifteen minutes it gathers what the lab
knows about itself and sends one JSON document to the outside world. Nothing ever comes back
in: the lab pushes outbound, so the public site never needs a path into the lab.

```
homelab-inventory ──make apply──► topology.json  (hosts, guests, VLANs, services, edges)
                                       │  ConfigMap in the isengard RKE2 ring
                                       ▼
halifirien ── every 15 min ──────────────────────────────────────────────
   Gatus ──────────── the latest probe result for every endpoint
   VictoriaMetrics ── 90 days of daily uptime per probe
   Alertmanager ───── firing warning and critical alerts
   → build StatusDocument → JSON-Schema gate + secret scrubber (fail closed)
   → PUT s3://<site>/status/status.json  ──►  piercemoore.com reads it
```

## What it publishes

The whole shape of the lab, on purpose: host names, roles, hardware, platforms, addresses,
VLANs, and which service runs where. Each node also carries its live **state**, its **checks**,
its firing **alerts**, and its **uptime** history. The contract is
[`schema/status.schema.json`](schema/status.schema.json), generated from `app/document.py`.
Every object in it is closed (`additionalProperties: false`), so a field the models don't
declare cannot be published.

### State rules

| State | Meaning |
|---|---|
| `ok` | It has probes, they all pass, and nothing is firing on it. |
| `degraded` | Some probes fail, or a warning or critical alert is firing on it. |
| `down` | Every probe fails. |
| `unknown` | Nothing observes it. An honest grey is better than an invented green. |

The **posture** is `outage` when any machine (host, VM, container, device) is down,
`degraded` when anything is degraded or down, and `ok` otherwise.

## What it refuses to publish

Credentials. Before every PUT, the document must validate against the committed schema, and
no string in it may look like a secret (1Password references, cloud access keys, private
keys, tokens, `password=`-style pairs). If either check fails, nothing is published that cycle,
and `/api/health` turns red once it has been two intervals without a good cycle.

## Running it

```sh
make setup        # uv sync, .env from .env.example, typecheck
make test         # pytest: sources, mapping, state rules, the gate, the loop, the routes
make preview      # one dry-run cycle against the sources in .env; prints the document
make dev          # the API on :8000 with the 15-minute loop (dry run by default)
```

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | 200 while cycles succeed; 503 with a reason when they don't |
| `GET /api/status` | the last document, plus how the last cycle went (in-lab only) |
| `POST /api/cycle` | run a cycle now |
| `GET /api/docs` | OpenAPI UI |

Publishing is off until `PUBLISH_ENABLED=true` and an `S3_BUCKET` are set. The IAM user
behind the credentials can `PutObject` under `status/` and nothing else.

## Stack

Python 3.13 · FastAPI · Pydantic v2 · httpx · boto3 · uv · ruff · mypy `--strict` · pytest.
CI runs on the lab's Gitea pull mirror and pushes the image to the lab's registry. Flux rolls
it out to the isengard ring.

## License

MIT
