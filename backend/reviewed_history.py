"""Reconcile an explicitly selected, reviewed journal with authoritative pump events."""
import pandas as pd
from backend.collection_sessions import checked_document


def reconcile(document, device_id, calibration_id, rows, pump_events, reviewed_until):
    doc = checked_document(document, device_id)
    if not doc['end'] or not doc['history_complete'] or doc['unknown_intervals']:
        raise ValueError('Cần phiên đã kết thúc, đối soát đầy đủ và không có khoảng lịch sử không rõ')
    if doc['calibration_id'] != calibration_id:
        raise ValueError('Mã hiệu chuẩn nhật ký không khớp thiết bị')
    start, end = pd.Timestamp(doc['start']), pd.Timestamp(doc['end'])
    cutoff = min(end, pd.Timestamp(reviewed_until))
    anchor = doc['last_watered_at_before_start']
    if not anchor:
        raise ValueError('Nhật ký thiếu thời điểm kết thúc lần tưới trước phiên')
    anchor = pd.Timestamp(anchor)
    # Full bins must lie inside reviewed coverage, including both boundaries.
    selected = [r for r in rows if start <= pd.Timestamp(r['measured_at']).floor('min')
                and pd.Timestamp(r['measured_at']).floor('min') + pd.Timedelta(minutes=1) <= cutoff]
    intervals = []
    for event in pump_events:
        a = pd.Timestamp(event['started_at'], unit='s', tz='UTC')
        if a > cutoff:
            continue
        if event['reason'] == 'Reboot' or event.get('actual_ms') is None:
            if a < anchor:
                continue  # A later explicitly reviewed watering establishes a new anchor.
            raise ValueError('Reset/thời lượng bơm không rõ sau mốc tưới đã biết; cần đối soát phiên mới')
        b = a + pd.Timedelta(milliseconds=event['actual_ms'])
        if b <= anchor:
            continue
        if a < start or b > cutoff:
            raise ValueError('Sự kiện bơm vượt phạm vi nhật ký đã đối soát')
        pair = (a, b)
        if pair not in intervals:
            intervals.append(pair)
    for event in doc['events']:
        a, b = pd.Timestamp(event['started_at']), pd.Timestamp(event['ended_at'])
        if b > cutoff:
            raise ValueError('Mốc đối soát chưa bao phủ sự kiện tưới trong nhật ký')
        pair = (a, b)
        if event['method'] == 'pump':
            if pair not in intervals:
                raise ValueError('Mốc bơm nhập tay chưa khớp thời gian sự kiện thiết bị; cần đối soát')
            continue  # Device record is authoritative; never count the journal copy twice.
        if any(a <= y and b >= x for x, y in intervals):
            raise ValueError('Tưới tay chồng lên sự kiện bơm; cần đối soát tránh đếm trùng')
        intervals.append(pair)
    intervals.sort()
    if any(a <= previous_b for (_, previous_b), (a, _) in zip(intervals, intervals[1:])):
        raise ValueError('Sự kiện bơm chồng lấn; cần đối soát')
    # Previous end is an anchor, not a fabricated volume or pump duration.
    events = [dict(reason='Manual', started_at=anchor.timestamp(), ended_at=anchor.timestamp())]
    events += [dict(reason='Manual', started_at=a.timestamp(), ended_at=b.timestamp()) for a,b in intervals]
    return selected, events
