"""Public limits shared by Dashboard and command validation; never raise a cap."""
import os


def manual_limits(payload: dict | None = None) -> dict:
    raw = os.getenv('SG_MAX_PULSE_MS', os.getenv('SG_MAX_PUMP_MS', '1000'))
    try:
        backend_max = int(raw)
        if not 1 <= backend_max <= 60000:
            raise ValueError
    except (ValueError, TypeError):
        backend_max = 0  # Invalid configuration locks WATER, not a permissive fallback.
    firmware_max = (payload or {}).get('max_pulse_ms')
    if type(firmware_max) is not int or not 0 <= firmware_max <= 60000:
        firmware_max = None
    effective = min(backend_max, firmware_max) if firmware_max is not None else backend_max
    return {'manual_max_ms': effective, 'backend_max_ms': backend_max,
            'firmware_max_ms': firmware_max, 'manual_ui_min_ms': 100}
