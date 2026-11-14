"""Render descriptive sensor history and frozen-model evaluation; no inference of causation."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from zoneinfo import ZoneInfo
p=Path(__file__).parent
raw=pd.read_json(p/'telemetry.jsonl',lines=True)
raw['t']=pd.to_datetime(raw.timestamp,utc=True).dt.tz_convert('Asia/Ho_Chi_Minh')
f=raw.dropna(subset=['t']).set_index('t').resample('1min')[['soil_pct','temperature_c','humidity_pct','light_raw']].median()
fig,axes=plt.subplots(4,1,figsize=(12,10),sharex=True)
for ax,(key,label,color) in zip(axes,[('soil_pct','Soil index (%)','#187957'),('temperature_c','Temperature (°C)','#c58017'),('humidity_pct','Air humidity (%)','#307caa'),('light_raw','Light (raw ADC)','#7560a5')]):
 ax.plot(f.index,f[key],color=color,lw=1);ax.set_ylabel(label);ax.grid(alpha=.18)
 for a,b in [('12:00','12:01'),('12:20','12:21')]:
  ax.axvspan(pd.Timestamp(f'2026-11-14 {a}',tz='Asia/Ho_Chi_Minh'),pd.Timestamp(f'2026-11-14 {b}',tz='Asia/Ho_Chi_Minh'),alpha=.3,color='blue')
axes[0].set_title('W04 • 14 Nov 2026 • two hand-water events (nominal times)')
axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M',tz=ZoneInfo('Asia/Ho_Chi_Minh')))
axes[-1].set_xlabel('Local time (UTC+7); minute medians, no interpolation')
fig.tight_layout();fig.savefig(p/'w04-sensors.png',dpi=160);plt.close(fig)
fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True)
for ax,h in zip(axes,[30,60]):
 pred=pd.read_csv(p/f'evaluation-{h}/test_predictions.csv');t=pd.to_datetime(pred.label_time,utc=True).dt.tz_convert('Asia/Ho_Chi_Minh')
 for key in ['target','persistence','random_forest']:
  if key in pred:ax.plot(t,pred[key],label=key,lw=1.2)
 ax.set_title(f'Frozen W01 → W04 • horizon {h} min');ax.set_ylabel('Soil index (%)');ax.grid(alpha=.2);ax.legend()
axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M',tz=ZoneInfo('Asia/Ho_Chi_Minh')))
axes[-1].set_xlabel('Target time (UTC+7); only eligible post-watering windows')
fig.tight_layout();fig.savefig(p/'w04-predictions.png',dpi=160);plt.close(fig)
