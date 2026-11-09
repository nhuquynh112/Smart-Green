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
python -m backend.seed_demo
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

`SG_DEVICE_KEYS` maps device IDs to plaintext secrets in the process environment; only SHA-256 hashes are stored in `devices.api_key_hash`. A single device can also use `SG_DEVICE_ID` plus `SG_API_KEY`. Provision devices through the same `Database.ensure_device()` method when using an external provisioning workflow.

The model bundle is loaded once when the app is constructed. `SG_AI_MODEL_PATH` overrides the default `artifacts/offline-demo-v2/model/candidate.joblib`. The checked-in demo bundle was trained on synthetic SIM data, so it will correctly return `unavailable` for real device telemetry due to its metadata mismatch. Set `devices.watering_history_complete=true` only after confirming the full watering record, including manual watering, is represented. Missing minutes, invalid sensors, unknown/reboot watering events, or mismatched model metadata disable inference safely.

The device API is under `/api/v1/devices/{device_id}/...`. Trusted application code can add a queued command through `backend.app.enqueue_command()`, which validates TTL and command shape. AI WATER commands also require `SG_AI_COMMANDS_ENABLED=true` and an advice object explicitly containing `can_trigger_pump=true`; the current inference contract always returns false, so AI cannot issue a pump command. Normal firmware authorization and ESP32 safety checks remain mandatory.

The web root is `/` and assets are served from `/static/`. Read-only device listing/dashboard APIs are public. Control and prediction APIs use HTTP Basic Auth, verified through `/api/v1/web/auth/check`; local defaults are `admin` / `smartgreen2026`, set `SG_WEB_USER` and `SG_WEB_PASSWORD` for your environment. The page uses its own login modal and the server does not send a `WWW-Authenticate` challenge. Run `python -m backend.seed_demo` before starting the app to seed a clearly labelled Fittonia bench sample and the complete `SIM-ONLY` v2 synthetic showcase. The seed command is repeatable and only replaces those two demo device records. It keeps the bench history incomplete and marks its values synthetic; the synthetic demo is time-shifted to the latest closed UTC minute so inference can run immediately without altering the candidate model metadata.

Check connectivity and required tables with `python -m backend.check_db`. This creates/applies the production schema when PostgreSQL is configured; do not run the demo seeder against a production database.

Run the backend tests with:

```bash
PYTHONUTF8=1 python -m pytest -q backend/tests
```
