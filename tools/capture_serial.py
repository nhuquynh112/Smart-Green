"""Capture bring-up JSON with host reception time. Not an AI-ready CSV."""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from prepare_telemetry import strict_json, validate


def decode_sample(raw, received_at):
    record = strict_json(raw)
    if not isinstance(record, dict):
        raise ValueError('not an object')
    record['received_at'] = received_at
    validate(record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("port", help="e.g. /dev/ttyUSB0")
    parser.add_argument("--output", default="data/bench.jsonl")
    parser.add_argument("--seconds", type=float, default=0, help="Stop after N seconds; 0 means continuous")
    args = parser.parse_args()
    if args.seconds < 0:
        parser.error("--seconds must be nonnegative")
    import serial

    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Opening serial may reset ESP32; boot_id distinguishes each session.
    device = serial.Serial(port=None, baudrate=115200, timeout=0.3, exclusive=True)
    device.dtr = False
    device.rts = False
    device.port = args.port
    device.open()
    with device, target.open("a", encoding="utf-8") as out:
        print(f"Capturing to {target}; Ctrl+C to stop. Close other serial monitors first.")
        started = time.monotonic()
        accepted = rejected = 0
        buffer = b""
        discarding = False
        try:
            while not args.seconds or time.monotonic() - started < args.seconds:
                chunk = device.read(2048)
                if not chunk:
                    continue
                received_at = datetime.now(timezone.utc).isoformat()
                buffer += chunk
                while b"\n" in buffer:
                    raw, buffer = buffer.split(b"\n", 1)
                    if discarding:
                        discarding = False
                        rejected += 1
                        continue
                    try:
                        record = decode_sample(raw, received_at)
                    except (ValueError, TypeError, AttributeError, UnicodeDecodeError):
                        rejected += 1
                        continue
                    out.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
                    out.flush()
                    accepted += 1
                    print(json.dumps(record, ensure_ascii=False, allow_nan=False))
                if len(buffer) > 8192:
                    buffer = b""
                    discarding = True
        except KeyboardInterrupt:
            print("\nCapture stopped.")
        if buffer or discarding:
            rejected += 1
        print(f"Saved {accepted} records; skipped {rejected} malformed/non-JSON lines.")


if __name__ == "__main__":
    main()
