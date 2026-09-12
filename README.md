# lahari.org

Source of truth for the `lahari.org` personal site: a small static
multi-page site plus a tiny visitor-counter backend.

## Layout

- `index.html` — home page: **Science Lab**, a set of animated, interactive
  science experiments.
- `play.html` — two small browser games (Root Access, Keep It Up). Fetches
  `GET /api/visits` on load to show a running visit count.
- `*-experiment.html` — the standalone Science Lab experiment pages linked
  from `index.html` (gravity, eclipses, relativity, the periodic table,
  etc.). Each is fully self-contained (own `<style>`/`<script>`, no shared
  assets) so it can be opened directly as well as linked from the hub.
- `counter_store.py` — persists a single integer counter to a JSON file,
  safe under concurrent access (file locking + atomic writes).
- `counter_server.py` — stdlib-only `http.server` service exposing
  `GET /api/visits` (increments and returns `{"count": N}`). No framework,
  no dependencies — it's one endpoint.
- `tests/` — pytest coverage for both.

## Running the backend locally

```
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
pytest

LAHARI_COUNTER_PATH=/tmp/visits.json python3 counter_server.py
# in another shell:
curl http://127.0.0.1:8083/api/visits
```

## Deployment

Hosted on a Raspberry Pi, alongside this owner's other domains. Provisioning
lives in the sibling `rpi-setup` repo:

- `rpi-setup/scripts/configure-lahari.sh` — creates the `lahari` system user,
  installs every `*.html` page into the docroot (replacing the previous set
  wholesale, so a renamed/removed page doesn't linger), installs
  `counter_store.py`/`counter_server.py` under `/opt/lahari`, runs the
  counter as a systemd service (`lahari-counter.service`), and writes the
  Apache vhost (static docroot at `/`, `/api/` reverse-proxied to the counter
  service on loopback).
- `rpi-setup/scripts/deploy-to-pi.sh` stages every `*.html` page,
  `counter_store.py`, and `counter_server.py` from this repo before running
  the script above — this repo is the source of truth, rpi-setup only wires
  it up.

```
cd ../rpi-setup/scripts
./deploy-to-pi.sh <user>@<host-or-ip> Lahari
```

See `rpi-setup/docs/14-app-deployment.md` for the full picture, and
`docs/02-dns-and-domain.md` for what has to be true in DNS first
(`lahari.org`'s A record must point at the Pi's public IP before a cert can
be obtained).
