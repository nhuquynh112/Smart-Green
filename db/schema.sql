-- Production schema for Smart-Green. Apply with psql to the target database.
BEGIN;

CREATE TABLE IF NOT EXISTS devices (
    device_id text PRIMARY KEY,
    api_key_hash char(64) NOT NULL,
    display_name text,
    is_demo boolean NOT NULL DEFAULT false,
    connected boolean NOT NULL DEFAULT false,
    last_seen_at timestamptz,
    calibration_id text,
    dry_raw integer,
    wet_raw integer,
    last_command_seq bigint NOT NULL DEFAULT 0,
    watering_history_complete boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS display_name text;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT false;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS dry_raw integer;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS wet_raw integer;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS last_command_seq bigint NOT NULL DEFAULT 0;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS watering_history_complete boolean NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS telemetry (
    device_id text NOT NULL REFERENCES devices(device_id),
    boot_id text NOT NULL,
    sample_seq bigint NOT NULL CHECK (sample_seq > 0),
    schema_version integer NOT NULL DEFAULT 1,
    build_stage text,
    measured_at timestamptz,
    received_at timestamptz NOT NULL DEFAULT now(),
    uptime_ms bigint,
    data_origin text,
    calibration_id text,
    soil_raw integer,
    soil_pct double precision CHECK (soil_pct IS NULL OR soil_pct BETWEEN 0 AND 100),
    soil_valid boolean,
    temperature_c double precision,
    humidity_pct double precision CHECK (humidity_pct IS NULL OR humidity_pct BETWEEN 0 AND 100),
    air_valid boolean,
    light_raw integer,
    light_lux double precision,
    water_ok boolean,
    tank_ok boolean,
    mode text CHECK (mode IS NULL OR mode IN ('OFF','MANUAL','AUTO')),
    pump_running boolean,
    commissioned boolean,
    storage_fault boolean,
    clock_ready boolean,
    clock_fault boolean,
    server_available boolean,
    last_command_seq bigint,
    queued_events integer,
    telemetry_overwrites bigint,
    payload jsonb NOT NULL,
    PRIMARY KEY (device_id, boot_id, sample_seq)
);
CREATE INDEX IF NOT EXISTS telemetry_device_measured_idx
    ON telemetry(device_id, measured_at DESC);
CREATE INDEX IF NOT EXISTS telemetry_device_received_idx
    ON telemetry(device_id, received_at DESC);

CREATE TABLE IF NOT EXISTS commands (
    device_id text NOT NULL REFERENCES devices(device_id),
    command_seq bigint NOT NULL CHECK (command_seq > 0),
    schema_version integer NOT NULL DEFAULT 1 CHECK (schema_version = 1),
    kind text NOT NULL CHECK (kind IN ('WATER','SET_MODE','STOP')),
    source text CHECK (source IS NULL OR source IN ('AI','MANUAL')),
    duration_ms integer CHECK (duration_ms IS NULL OR duration_ms > 0),
    mode text CHECK (mode IS NULL OR mode IN ('OFF','MANUAL','AUTO')),
    issued_at bigint NOT NULL,
    expires_at bigint NOT NULL,
    status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','ACKED','EXPIRED')),
    ack_result text,
    acked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (device_id, command_seq),
    CHECK (expires_at > issued_at AND expires_at - issued_at <= 60),
    CHECK ((kind = 'WATER' AND source IS NOT NULL AND duration_ms IS NOT NULL AND mode IS NULL)
        OR (kind = 'SET_MODE' AND mode IS NOT NULL AND source IS NULL AND duration_ms IS NULL)
        OR (kind = 'STOP' AND source IS NULL AND duration_ms IS NULL AND mode IS NULL))
);
CREATE INDEX IF NOT EXISTS commands_pending_idx
    ON commands(device_id, status, command_seq);

CREATE TABLE IF NOT EXISTS watering_events (
    device_id text NOT NULL REFERENCES devices(device_id),
    event_id bigint NOT NULL CHECK (event_id > 0),
    schema_version integer NOT NULL DEFAULT 1 CHECK (schema_version = 1),
    command_seq bigint NOT NULL DEFAULT 0,
    started_at bigint NOT NULL,
    planned_ms integer CHECK (planned_ms IS NULL OR planned_ms >= 0),
    actual_ms integer CHECK (actual_ms IS NULL OR actual_ms >= 0),
    ended_at bigint,
    source text NOT NULL CHECK (source IN ('AI','MANUAL','RULE','MANUAL_CARE')),
    reason text NOT NULL CHECK (reason IN ('Running','Duration','Wet','Sensor','Tank','Stop','Reboot','Guard','Manual','Scheduled','ManualCheck','ManualHandWatering')),
    received_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL,
    PRIMARY KEY (device_id, event_id),
    CHECK (reason IN ('Running','Duration','Wet','Sensor','Tank','Stop','Reboot','Guard','Manual','Scheduled','ManualCheck','ManualHandWatering'))
);
ALTER TABLE watering_events ADD COLUMN IF NOT EXISTS ended_at bigint;
ALTER TABLE watering_events ALTER COLUMN planned_ms DROP NOT NULL;
ALTER TABLE watering_events DROP CONSTRAINT IF EXISTS watering_events_check;
ALTER TABLE watering_events DROP CONSTRAINT IF EXISTS watering_events_reason_check;
ALTER TABLE watering_events DROP CONSTRAINT IF EXISTS watering_events_source_check;
ALTER TABLE watering_events DROP CONSTRAINT IF EXISTS watering_events_planned_ms_check;
ALTER TABLE watering_events DROP CONSTRAINT IF EXISTS watering_events_reason_values_ck;
ALTER TABLE watering_events DROP CONSTRAINT IF EXISTS watering_events_source_values_ck;
ALTER TABLE watering_events DROP CONSTRAINT IF EXISTS watering_events_planned_ms_ck;
ALTER TABLE watering_events DROP CONSTRAINT IF EXISTS watering_events_duration_reason_ck;
ALTER TABLE watering_events DROP CONSTRAINT IF EXISTS watering_events_manual_hand_watering_ck;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='watering_events'::regclass AND conname='watering_events_reason_values_ck') THEN
        ALTER TABLE watering_events ADD CONSTRAINT watering_events_reason_values_ck CHECK (
            reason IN ('Running','Duration','Wet','Sensor','Tank','Stop','Reboot','Guard','Manual','Scheduled','ManualCheck','ManualHandWatering')
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='watering_events'::regclass AND conname='watering_events_source_values_ck') THEN
        ALTER TABLE watering_events ADD CONSTRAINT watering_events_source_values_ck CHECK (source IN ('AI','MANUAL','RULE','MANUAL_CARE'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='watering_events'::regclass AND conname='watering_events_planned_ms_ck') THEN
        ALTER TABLE watering_events ADD CONSTRAINT watering_events_planned_ms_ck CHECK (planned_ms IS NULL OR planned_ms >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='watering_events'::regclass AND conname='watering_events_duration_reason_ck') THEN
        ALTER TABLE watering_events ADD CONSTRAINT watering_events_duration_reason_ck CHECK (
            (reason IN ('Reboot','Manual') AND actual_ms IS NULL AND (reason <> 'Manual' OR ended_at IS NOT NULL))
            OR (reason='ManualHandWatering' AND source IN ('MANUAL_CARE','MANUAL') AND planned_ms IS NULL AND actual_ms IS NULL)
            OR (reason NOT IN ('Reboot','Manual','ManualHandWatering') AND planned_ms IS NOT NULL AND actual_ms IS NOT NULL)
        );
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS watering_events_device_started_idx
    ON watering_events(device_id, started_at DESC);

CREATE TABLE IF NOT EXISTS ai_predictions (
    prediction_id bigserial PRIMARY KEY,
    device_id text NOT NULL REFERENCES devices(device_id),
    as_of timestamptz,
    available_at timestamptz,
    horizon_minutes integer,
    predicted_soil_pct double precision,
    model_name text,
    data_origin text,
    can_trigger_pump boolean NOT NULL DEFAULT false CHECK (can_trigger_pump = false),
    status text NOT NULL CHECK (status IN ('available','unavailable')),
    raw_output jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_predictions_device_created_idx
    ON ai_predictions(device_id, created_at DESC);

-- Durable web request identity; old commands retain NULL identity.
ALTER TABLE commands ADD COLUMN IF NOT EXISTS request_id text;
ALTER TABLE commands ADD COLUMN IF NOT EXISTS request_fingerprint text;
CREATE UNIQUE INDEX IF NOT EXISTS commands_request_id_idx ON commands(device_id,request_id) WHERE request_id IS NOT NULL;

COMMIT;
