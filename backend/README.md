# Smart-Green FastAPI backend

## Run locally

Install from the repository root:

```bash
python -m pip install -r backend/requirements.txt
```

Set `PYTHONUTF8=1` when running Python subprocesses on Windows if the process handles Vietnamese text. Configure `DATABASE_URL` as a PostgreSQL URL (`postgresql://...`) for production. Without it, the app and seed CLI use persistent `sqlite:///./smart_green.sqlite3`; tests can inject `sqlite:///:memory:`. PostgreSQL schema is in `db/schema.sql`; `db/import_bench.sql` remains the separate TV1 staging import.

Configure device credentials without committing them:

```bash
export SG_DEVICE_KEYS='{"garden-01":"replace-with-a-long-random-key"}'
export DATABASE_URL='postgresql://user:password@localhost:5432/smart_green'
export SG_WEB_USER='admin'
read -rsp 'Admin password: ' SG_WEB_PASSWORD; echo
export SG_WEB_PASSWORD
python -m backend.seed_demo
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

`SG_DEVICE_KEYS` maps device IDs to plaintext secrets in the process environment; only SHA-256 hashes are stored in `devices.api_key_hash`. A single device can also use `SG_DEVICE_ID` plus `SG_API_KEY`. Provision devices through the same `Database.ensure_device()` method when using an external provisioning workflow.

The model bundle is loaded once when the app is constructed. `SG_AI_MODEL_PATH` overrides the default `artifacts/offline-demo-v2/model/candidate.joblib`. The checked-in demo bundle was trained on synthetic SIM data, so it will correctly return `unavailable` for real device telemetry due to its metadata mismatch. For real devices, select a saved, ended, fully reviewed collection session with a known previous watering end. The prediction request carries its ID/revision and the fresh telemetry/boot watermark. Manual events are read from that journal and matched with device pump events; a checkbox alone is insufficient. Prediction still requires recent complete bins, so an old ended session is evaluated offline rather than time-shifted. Missing minutes, invalid sensors, unknown/reboot watering events, or mismatched model metadata disable inference safely.

The device API is under `/api/v1/devices/{device_id}/...`. Trusted application code can add a queued command through `backend.app.enqueue_command()`, which validates TTL and command shape. AI WATER commands also require `SG_AI_COMMANDS_ENABLED=true` and an advice object explicitly containing `can_trigger_pump=true`; the current inference contract always returns false, so AI cannot issue a pump command. Normal firmware authorization and ESP32 safety checks remain mandatory.

The web root is `/` and assets are served from `/static/`. Read-only device listing/dashboard APIs are public. Control and prediction APIs use HTTP Basic Auth, verified through `/api/v1/web/auth/check`; `SG_WEB_USER` defaults to `admin`, but **SG_WEB_PASSWORD has no fallback**. Missing/blank password disables admin actions with HTTP 503; telemetry ingestion is unaffected. Configure the password before starting the backend; do not commit it. Use HTTPS when exposing Basic Auth beyond a trusted local demo network. The page uses its own login modal and the server does not send a `WWW-Authenticate` challenge. Run `python -m backend.seed_demo` before starting the app to seed a clearly labelled Fittonia bench sample and the complete `SIM-ONLY` v2 synthetic showcase. The seed command is repeatable and only replaces those two demo device records. It keeps the bench history incomplete and marks its values synthetic; the synthetic demo is time-shifted to the latest closed UTC minute so inference can run immediately without altering the candidate model metadata.

Check connectivity and required tables with `python -m backend.check_db`. This creates/applies the production schema when PostgreSQL is configured; do not run the demo seeder against a production database.

Run the backend tests with:

```bash
PYTHONUTF8=1 python -m pytest -q backend/tests
```

## Local Docker database and pgAdmin

The current local setup uses PostgreSQL 16 and pgAdmin in `compose.yaml`. Open http://127.0.0.1:5050 to inspect the Smart Green connection. See [local database guide](../docs/LOCAL_DATABASE.md) for startup, storage and connection details.

## Offline Dashboard and reviewed history

Chart.js 4.4.7 and its MIT license are bundled under `backend/static/vendor`; charts and system fonts require no CDN. AI evaluation captions reflect the loaded model data origin.

For real prediction, finish/save/review a session, keep it selected, and predict immediately after review. No unknown-history interval is accepted. A recorded pump event must match the journal pump interval exactly; hand events overlapping a pump are rejected rather than double-counted. An old Reboot can be superseded only by an explicitly reviewed later watering anchor; reset/unknown duration after that anchor blocks prediction. Revision changes require reloading the session. Online advice remains unable to trigger the pump.

Backend restart is needed to activate API changes; do it outside a data collection session after backup. Static HTML may update earlier. Check the admin password configuration before restarting; this change does not itself restart the process or change production credentials.
