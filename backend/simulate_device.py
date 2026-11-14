"""Lightweight ESP32 HTTP simulator for the seeded SIM-ONLY dashboard device."""
from __future__ import annotations

import argparse
import json
import math
import os
import secrets
import time
import urllib.error
import urllib.request
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote


DEFAULT_KEY = "local-demo-sim-only-key"


def utc_now() -> tuple[int, str]:
    stamp = datetime.now(timezone.utc)
    return int(stamp.timestamp()), stamp.isoformat(timespec="seconds").replace("+00:00", "Z")


class ApiClient:
    def __init__(self, base_url: str, device_id: str, api_key: str, timeout: float = 2.0):
        self.base_url = base_url.rstrip("/")
        self.device_id = device_id
        self.api_key = api_key
        self.timeout = timeout
        self.root = f"/api/v1/devices/{quote(device_id, safe='')}"

    def request(self, method: str, path: str, payload: dict | None = None) -> tuple[int, Any]:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8") if payload is not None else None
        headers = {"X-API-Key": self.api_key}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
                return response.status, json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            body = exc.read()
            detail = body.decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} {path}: {detail}") from exc


class DeviceSimulator:
    def __init__(self, client: ApiClient, interval: float = 5.0, max_pulse_ms: int = 1000,
                 mode: str = "MANUAL", tank_ok: bool = True):
        self.client = client
        self.interval = interval
        self.max_pulse_ms = max_pulse_ms
        self.mode = mode
        self.tank_ok = tank_ok
        self.soil_pct = 43.0
        self.boot_id = uuid.uuid4().hex[:16]
        self.sample_seq = 0
        self.started_monotonic = time.monotonic()
        self.last_command_seq = 0
        self.event_id = 1_000_000_000 + secrets.randbelow(900_000_000)
        self.seen_commands: dict[int, tuple[str, dict | None]] = {}
        self.pending_events: deque[dict] = deque()

    def telemetry(self) -> dict:
        self.sample_seq += 1
        uptime = int((time.monotonic() - self.started_monotonic) * 1000)
        unix, stamp = utc_now()
        self.soil_pct = 43.0 - min(8.0, uptime / 3_600_000 * 0.5) + math.sin(uptime / 180_000) * 0.15
        soil_raw = round(2511 + self.soil_pct * (979 - 2511) / 100)
        return {
            "schema_version": 1, "build_stage": "http_simulator", "device_id": self.client.device_id,
            "boot_id": self.boot_id, "sample_seq": self.sample_seq, "timestamp": stamp,
            "uptime_ms": uptime, "data_origin": "synthetic", "calibration_id": "SIM-v1",
            "soil_raw": soil_raw, "soil_pct": round(self.soil_pct, 2), "soil_valid": True,
            "air_valid": True, "temperature_c": 26.8, "humidity_pct": 62.0,
            "light_raw": 910, "light_lux": None, "tank_ok": self.tank_ok,
            "pump_on": False, "mode": self.mode, "commissioned": False,
            "storage_fault": False, "clock_ready": True, "clock_fault": False,
            "server_available": True, "last_command_seq": self.last_command_seq,
            "queued_events": len(self.pending_events), "telemetry_overwrites": 0,
        }

    def _make_event(self, command: dict) -> dict:
        self.event_id += 1
        unix, _ = utc_now()
        duration = int(command["duration_ms"])
        return {"schema_version": 1, "device_id": self.client.device_id,
                "event_id": self.event_id, "command_seq": command["command_seq"],
                "started_at": unix, "planned_ms": duration, "actual_ms": duration,
                "source": command.get("source", "MANUAL"), "reason": "Duration"}

    def _execute(self, command: dict) -> tuple[str, dict | None]:
        now, _ = utc_now()
        seq = int(command["command_seq"])
        if now > int(command["expires_at"]):
            return "expired_or_clock", None
        kind = command.get("kind")
        if kind == "SET_MODE":
            mode = command.get("mode")
            if mode not in {"OFF", "MANUAL", "AUTO"}:
                return "invalid_mode", None
            self.mode = mode
            return "mode_set", None
        if kind == "STOP":
            self.mode = "OFF"
            return "stopped", None
        if kind != "WATER":
            return "invalid_kind", None
        duration = command.get("duration_ms")
        if type(duration) is not int or not 0 < duration <= self.max_pulse_ms:
            return "duration_limit", None
        if not self.tank_ok:
            return "sensor_tank_or_wet", None
        return "started", self._make_event(command)

    def _post_ack(self, seq: int, result: str) -> None:
        body = {"schema_version": 1, "device_id": self.client.device_id,
                "command_seq": seq, "result": result}
        self.client.request("POST", f"{self.client.root}/commands/{seq}/ack", body)
        self.last_command_seq = max(self.last_command_seq, seq)

    def _flush_events(self) -> None:
        while self.pending_events:
            event = self.pending_events[0]
            status, payload = self.client.request("POST", f"{self.client.root}/events", event)
            if status not in (200, 201) or not payload or payload.get("event_id") != event["event_id"]:
                raise RuntimeError(f"Unexpected event acknowledgement: HTTP {status} {payload}")
            self.pending_events.popleft()

    def step(self) -> None:
        self.client.request("POST", f"{self.client.root}/telemetry", self.telemetry())
        self._flush_events()
        status, command = self.client.request("GET", f"{self.client.root}/commands/next?after_seq=0")
        if status == 204 or command is None:
            return
        if status != 200 or not isinstance(command, dict):
            raise RuntimeError(f"Unexpected command response: HTTP {status} {command}")
        seq = int(command["command_seq"])
        if seq in self.seen_commands:
            result, event = self.seen_commands[seq]
        else:
            result, event = self._execute(command)
            self.seen_commands[seq] = (result, event)
        self._post_ack(seq, result)
        if event is not None:
            self.pending_events.append(event)
            self._flush_events()
        print(f"command_seq={seq} kind={command.get('kind')} result={result}", flush=True)

    def run(self, once: bool = False) -> None:
        print(f"SIMULATOR device={self.client.device_id} base={self.client.base_url} interval={self.interval:g}s", flush=True)
        while True:
            began = time.monotonic()
            try:
                self.step()
            except (OSError, RuntimeError, ValueError) as exc:
                print(f"simulator error: {exc}", flush=True)
            if once:
                return
            time.sleep(max(0.0, self.interval - (time.monotonic() - began)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("SG_BACKEND_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--device-id", default=os.getenv("SG_DEVICE_ID", "SIM-ONLY"))
    parser.add_argument("--api-key", default=os.getenv("SG_SIM_API_KEY", DEFAULT_KEY))
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--max-pulse-ms", type=int, default=1000)
    parser.add_argument("--mode", choices=["OFF", "MANUAL", "AUTO"], default="MANUAL")
    parser.add_argument("--empty-tank", action="store_true", help="Simulate a low water float sensor")
    parser.add_argument("--once", action="store_true", help="Send one telemetry sample and poll once")
    args = parser.parse_args()
    if args.interval <= 0 or args.max_pulse_ms <= 0:
        parser.error("--interval and --max-pulse-ms must be positive")
    client = ApiClient(args.base_url, args.device_id, args.api_key)
    simulator = DeviceSimulator(client, args.interval, args.max_pulse_ms, args.mode,
                                tank_ok=not args.empty_tank)
    try:
        simulator.run(once=args.once)
    except KeyboardInterrupt:
        print("simulator stopped", flush=True)


if __name__ == "__main__":
    main()
