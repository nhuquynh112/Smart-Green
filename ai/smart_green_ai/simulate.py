"""Synthetic plumbing fixture. Not plant physics, measured evidence, or calibration."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd


def generate(days=10, seed=42):
    if days < 1:
        raise ValueError("days must be positive")
    rng = np.random.default_rng(seed)
    rows=[]
    soil=60.0
    total=0
    since=0
    for t in pd.date_range("2026-01-01", periods=days*1440, freq="min", tz="UTC"):
        phase=2*np.pi*(t.hour+t.minute/60)/24
        temp=27+4*np.sin(phase)
        soil -= 0.025+0.008*np.sin(phase)+rng.normal(0,0.008)
        since += 1
        if soil < 28:
            soil=65.0;total+=2000;since=0
        rows.append({"timestamp":t.isoformat(),"device_id":"SIM-ONLY", "calibration_id":"SIM-v1",
                     "data_origin":"synthetic", "soil_pct":soil, "temperature_c":temp,
                     "humidity_pct":65-8*np.sin(phase), "minutes_since_water":since,"water_total_ms":total})
    return pd.DataFrame(rows)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("data/synthetic.csv"))
    parser.add_argument("--days",type=int,default=10)
    args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    generate(args.days).to_csv(args.output,index=False)
    print(f"SYNTHETIC ONLY: {args.output}")


if __name__ == "__main__":
    main()
