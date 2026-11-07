"""Clean bench logs using the shared TV1 validator, from any working directory."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from prepare_telemetry import export, prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='*', type=Path, help='Logs/JSONL in collection order; default: latest firmware log')
    parser.add_argument('--output', type=Path, default=ROOT / 'firmware/data/bench_clean.csv')
    args = parser.parse_args()
    paths = args.inputs
    if not paths:
        logs = list((ROOT / 'firmware/logs').glob('device-monitor-*.log'))
        if not logs:
            parser.error('Không tìm thấy log. Truyền đường dẫn file JSONL hoặc log cần xử lý.')
        paths = [max(logs, key=lambda p: p.stat().st_mtime)]
    try:
        # Never allow an output artifact to overwrite a source log.
        outputs = [args.output.with_suffix(s).resolve() for s in ('.csv', '.quality.json', '.postgres.csv')]
        if any(p.resolve() in outputs for p in paths):
            parser.error('Đường dẫn đầu ra trùng file nguồn.')
        rows, columns, report = prepare(paths)
        export(rows, columns, report, args.output)
    except OSError as exc:
        parser.error(str(exc))
    print(f"Nguồn: {', '.join(str(p) for p in paths)}")
    print(f"Hợp lệ: {len(rows)} | Loại trùng: {report['duplicates_removed']} | Từ chối: {len(report['rejected'])}")
    print(f"Thiếu giờ đo: {report['missing']['timestamp']} | Thiếu giờ nhận: {report['missing']['received_at']}")
    print(f"CSV: {args.output.with_suffix('.csv')}")
    print(f"Báo cáo: {args.output.with_suffix('.quality.json')}")
    if not rows:
        raise SystemExit('Không có bản ghi hợp lệ; xem báo cáo chất lượng.')


if __name__ == '__main__':
    main()
