-- Run with psql, connected to the intended development database.
-- Isolated staging schema, not a replacement for TV2's production schema.
\set ON_ERROR_STOP on
BEGIN;
CREATE SCHEMA IF NOT EXISTS bench;
CREATE TABLE IF NOT EXISTS bench.telemetry (
    device_id text NOT NULL,
    boot_id text NOT NULL,
    sample_seq bigint NOT NULL CHECK (sample_seq > 0),
    measured_at timestamptz,
    received_at timestamptz,
    payload jsonb NOT NULL,
    imported_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (device_id, boot_id, sample_seq)
);
CREATE TEMP TABLE import_telemetry (LIKE bench.telemetry INCLUDING DEFAULTS) ON COMMIT DROP;
-- psql resolves this local path relative to the repo root where you run it.
\copy import_telemetry(device_id,boot_id,sample_seq,measured_at,received_at,payload) FROM 'firmware/data/prepared/bench_received_session_03.postgres.csv' WITH (FORMAT csv, HEADER true)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM import_telemetry i JOIN bench.telemetry t
        USING (device_id,boot_id,sample_seq)
        WHERE (i.payload - 'received_at') IS DISTINCT FROM (t.payload - 'received_at')
    ) THEN RAISE EXCEPTION 'Conflicting telemetry identity; import rolled back'; END IF;
END $$;
INSERT INTO bench.telemetry(device_id,boot_id,sample_seq,measured_at,received_at,payload)
SELECT device_id,boot_id,sample_seq,measured_at,received_at,payload FROM import_telemetry
ON CONFLICT (device_id,boot_id,sample_seq) DO NOTHING;
COMMIT;
SELECT count(*) AS saved_rows FROM bench.telemetry;
