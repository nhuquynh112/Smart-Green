"""Export a standalone AI evaluation report with explicit data provenance."""
import argparse
import base64
import hashlib
import html
import json
from pathlib import Path

import numpy as np
import pandas as pd

LABELS={'persistence':'Hold-last','linear_extrapolation':'Linear drift',
        'linear_regression':'Linear Regression','random_forest':'Random Forest'}
COLORS=['#6b7280','#d97706','#0072b2','#009e73']


def load_results(run_dir):
    meta=json.loads((run_dir/'report.json').read_text())
    if meta['quality']['data_origin'] not in ('real','synthetic'):
        raise ValueError('Unrecognized provenance')
    df=pd.read_csv(run_dir/'test_predictions.csv')
    if df.empty:raise ValueError('No predictions to report')
    for key in ['target',*LABELS]:
        if key not in df or not np.isfinite(df[key].to_numpy(dtype=float)).all():
            raise ValueError(f'Missing or nonfinite predictions: {key}')
    df['timestamp']=pd.to_datetime(df.timestamp,utc=True,errors='raise')
    if df.timestamp.duplicated().any():raise ValueError('Duplicate prediction times')
    df=df.sort_values('timestamp')
    for name in LABELS:
        mae=float(np.abs(df[name]-df.target).mean())
        if not np.isclose(mae,meta['test_mae_percentage_points'][name],rtol=1e-6,atol=1e-9):
            raise ValueError(f'Prediction/report MAE mismatch: {name}')
    return meta,df


def export(run_dir,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    meta,df=load_results(run_dir)
    output.mkdir(parents=True,exist_ok=True)
    synthetic=meta['quality']['data_origin']=='synthetic'
    stamp='SYNTHETIC - SOFTWARE CHECK ONLY' if synthetic else 'REAL DATA - CONDITIONAL FORECAST EVALUATION'
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    names=list(LABELS);x=np.arange(len(names))
    fig,ax=plt.subplots(figsize=(10,5.5),layout='constrained')
    ax.bar(x-.18,[meta['validation_mae_percentage_points'][n] for n in names],.36,color='#93c5fd',label='Validation')
    bars=ax.bar(x+.18,[meta['test_mae_percentage_points'][n] for n in names],.36,color='#0072b2',label='Test')
    ax.bar_label(bars,fmt='%.3f',padding=4)
    ax.set_xticks(x,[LABELS[n] for n in names]);ax.set_ylabel('MAE (relative moisture percentage points)')
    ax.set_title(f'{stamp}\n{meta["horizon_minutes"]}-minute forecast: lower MAE is better',fontsize=13)
    ax.set_ylim(0,max(max(meta['validation_mae_percentage_points'].values()),max(meta['test_mae_percentage_points'].values()))*1.25+.01)
    ax.legend();ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    fig.savefig(output/'mae.png',dpi=160);fig.savefig(output/'mae.svg');plt.close(fig)
    # Use target time rather than the forecast issuance time on the axis; preserve missing windows.
    series=df.set_index('timestamp')[['target',*names]].copy()
    series.index=series.index+pd.Timedelta(minutes=meta['horizon_minutes'])
    end=min(series.index.max(),series.index.min()+pd.Timedelta(hours=6))
    series=series.reindex(pd.date_range(series.index.min(),end,freq='min'))
    fig,ax=plt.subplots(figsize=(12,5.5),layout='constrained')
    ax.plot(series.index,series.target,color='#111827',lw=2,label='Observed target (synthetic)' if synthetic else 'Observed target')
    for name,color in zip(names,COLORS):ax.plot(series.index,series[name],color=color,lw=1.2,alpha=.85,label=LABELS[name])
    ax.set_title(f'{stamp}\nPredicted vs target moisture - first 6 hours of test',fontsize=13)
    ax.set_ylabel('Relative soil moisture (%)');ax.set_xlabel('Target time (UTC); gaps remain gaps')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M',tz=series.index.tz))
    ax.legend(ncol=3,fontsize=9);ax.grid(alpha=.15)
    fig.savefig(output/'forecast.png',dpi=160);fig.savefig(output/'forecast.svg');plt.close(fig)
    rows=[]
    for n in names:
        rows.append({'model':n,'validation_mae_pp':meta['validation_mae_percentage_points'][n],
                     'test_mae_pp':meta['test_mae_percentage_points'][n],
                     'falling_soil_test_mae_pp':meta.get('falling_soil_test',{}).get('mae_percentage_points',{}).get(n),
                     'selected_by_validation':n==meta['selected_by_validation']})
    pd.DataFrame(rows).to_csv(output/'metrics.csv',index=False)
    def embed(name):return 'data:image/png;base64,'+base64.b64encode((output/name).read_bytes()).decode()
    provenance=('DỮ LIỆU GIẢ LẬP — chỉ kiểm tra phần mềm, không phải độ chính xác trên cây thật.' if synthetic
                else 'Dữ liệu thật — chỉ đánh giá dự báo có điều kiện, chưa chứng minh hiệu quả điều khiển tưới.')
    selected=LABELS[meta['selected_by_validation']]
    table=''.join(f'<tr><td>{LABELS[r["model"]]}</td><td>{r["validation_mae_pp"]:.4f}</td><td>{r["test_mae_pp"]:.4f}</td><td>{"Có" if r["selected_by_validation"] else ""}</td></tr>' for r in rows)
    splits=''.join(f'<li>{html.escape(k)}: {v["rows"]} cửa sổ, {html.escape(v["first"])} → {html.escape(v["last"])}</li>' for k,v in meta['split'].items())
    report=f'''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Smart-Green — báo cáo AI</title><style>body{{font:16px/1.6 system-ui,sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;color:#17212b}}h1,h2{{line-height:1.3}}.notice{{background:#fff1d6;border-left:5px solid #b45309;padding:16px}}img{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #cbd5e1;padding:10px;text-align:left}}code{{overflow-wrap:anywhere}}@media print{{body{{margin:0}}img{{break-inside:avoid}}}}</style>
<h1>Smart-Green · Đánh giá dự báo {meta['horizon_minutes']} phút</h1><p class="notice">{provenance}</p>
<p>Chọn theo validation: <strong>{selected}</strong>. MAE tính bằng điểm phần trăm của chỉ số độ ẩm tương đối; không phải % accuracy. Chưa cho phép tự động kích bơm.</p>
<h2>So sánh mô hình</h2><table><tr><th>Phương án</th><th>Validation MAE</th><th>Test MAE</th><th>Được chọn</th></tr>{table}</table>
<img alt="Biểu đồ so sánh MAE validation và test" src="{embed('mae.png')}">
<h2>Dự đoán và giá trị đích</h2><img alt="Đường dự đoán và giá trị đích theo thời gian UTC" src="{embed('forecast.png')}">
<p>Chỉ vẽ tối đa 6 giờ đầu của tập test; bảng MAE dùng toàn bộ tập test. Không nối qua khoảng dữ liệu bị loại.</p>
<h2>Phạm vi đánh giá</h2><ul>{splits}</ul><p>Các cửa sổ có đủ lịch sử và không có tưới bổ sung. Nhóm đất giảm ẩm gồm {meta.get('falling_soil_test',{}).get('rows','chưa thống kê')} mẫu có target thấp hơn giá trị hiện tại; đây là phân nhóm hồi cứu, không phải tín hiệu kích bơm.</p>
<p>Các cửa sổ gần nhau có tương quan. Số mẫu không thay thế số chu kỳ độc lập. Kết quả không chứng minh phần trăm tiết kiệm nước.</p>
<p>Dataset SHA256: <code>{html.escape(meta['dataset_sha256'])}</code></p></html>'''
    (output/'index.html').write_text(report,encoding='utf-8')
    evidence={'data_origin':meta['quality']['data_origin'],'source_run':str(run_dir),'test_rows':len(df),
              'predictions_sha256':hashlib.sha256((run_dir/'test_predictions.csv').read_bytes()).hexdigest(),
              'selected_by_validation':meta['selected_by_validation'],'automatic_irrigation_approved':False}
    (output/'provenance.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(f'Report: {output / "index.html"}; {stamp}')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run_dir',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();export(a.run_dir,a.output)


if __name__=='__main__':main()
