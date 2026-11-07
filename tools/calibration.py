"""Record measured calibration; calculate estimates without enabling pump operation."""
import argparse
import hashlib
import json
import math
import re
import statistics
from datetime import datetime
from pathlib import Path

TEMPLATE = {
    'data_origin':'real', 'device_id':'garden-01', 'calibration_id':None,
    'measured_at':None, 'plant':None, 'soil_description':None, 'depth_cm':None,
    'dry_raw_samples':[], 'wet_raw_samples':[],
    'pump':{'voltage_v':None,'tube_description':None,'lift_cm':None,
            'trials':[], 'target_ml':None},
    'checks':{'relay_off_at_boot':False,'relay_off_at_reset':False,
              'empty_tank_stops_pump':False,'no_siphon_after_stop':False}
}


def number(value,name,positive=True):
    if type(value) not in (int,float) or not math.isfinite(value) or (value<=0 if positive else value<0):
        raise ValueError(f'{name}: finite {"positive" if positive else "nonnegative"} number required')
    return float(value)


def analyze(profile):
    if profile.get('data_origin') not in ('real','synthetic'):raise ValueError('data_origin must be real or synthetic')
    for k in ('device_id','calibration_id'):
        if not isinstance(profile.get(k),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',profile[k]):
            raise ValueError(f'{k}: use 1–64 letters, digits, hyphen or underscore')
    date=datetime.fromisoformat(profile['measured_at'].replace('Z','+00:00'))
    if date.utcoffset() is None:raise ValueError('measured_at needs timezone')
    for k in ('plant','soil_description'):
        if not isinstance(profile.get(k),str) or not profile[k].strip():raise ValueError(f'{k} required')
    number(profile.get('depth_cm'),'depth_cm')
    endpoints={}
    for k in ('dry_raw_samples','wet_raw_samples'):
        samples=profile.get(k)
        if not isinstance(samples,list) or len(samples)<5:raise ValueError(f'{k}: at least five measured samples')
        if any(type(v) is not int or not 50<v<4045 for v in samples):raise ValueError(f'{k}: integer ADC samples away from rails required')
        endpoints[k]={'median':round(statistics.median(samples)),'min':min(samples),'max':max(samples),
                      'samples':len(samples),'stdev':statistics.stdev(samples)}
    dry=endpoints['dry_raw_samples']['median'];wet=endpoints['wet_raw_samples']['median']
    if abs(dry-wet)<200:raise ValueError('dry/wet separation under 200 ADC counts: repeat calibration')
    pump=profile['pump'];number(pump.get('voltage_v'),'pump.voltage_v');number(pump.get('lift_cm'),'pump.lift_cm',False)
    if not isinstance(pump.get('tube_description'),str) or not pump['tube_description'].strip():raise ValueError('pump.tube_description required')
    trials=pump.get('trials')
    if not isinstance(trials,list) or len(trials)<3:raise ValueError('At least three measured pump trials required')
    rates=[];total_v=total_t=0
    for i,t in enumerate(trials):
        seconds=number(t.get('duration_s'),f'trial {i+1} duration_s')
        volume=number(t.get('volume_ml'),f'trial {i+1} volume_ml')
        total_v+=volume;total_t+=seconds;rates.append(volume/seconds)
    q=total_v/total_t
    target=pump.get('target_ml')
    checks=profile.get('checks',{})
    blockers=[k for k in TEMPLATE['checks'] if checks.get(k) is not True]
    report={'data_origin':profile['data_origin'],'device_id':profile['device_id'],'calibration_id':profile['calibration_id'],
            'soil_references':endpoints,'dry_raw':dry,'wet_raw':wet,'adc_separation':abs(dry-wet),
            'pump':{'trials':len(rates),'total_ml':total_v,'total_seconds':total_t,'weighted_ml_per_s':q,
                    'observed_min_ml_per_s':min(rates),'observed_max_ml_per_s':max(rates),
                    'rate_cv_pct':100*statistics.stdev(rates)/statistics.mean(rates)},
            'unconfirmed_checks':blockers,'hardware_approved':False,'automatic_irrigation_approved':False,
            'notes':['Calibration is a relative soil index, not volumetric moisture.',
                     'Flow estimates apply only to the measured voltage, tube and lift.',
                     'Input checkboxes are user records, not independent verification. No automatic enabling of firmware.']}
    if target is not None:
        target=number(target,'target_ml')
        report['target_volume_estimate']={'ml':target,'nominal_ms':1000*target/q,
            'ms_using_observed_fastest_flow':1000*target/max(rates),
            'ms_using_observed_slowest_flow':1000*target/min(rates),
            'note':'Estimate only, not a recommended safe limit or permission to lengthen pump tests.'}
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    init=sub.add_parser('template');init.add_argument('--output',type=Path,required=True)
    calc=sub.add_parser('analyze');calc.add_argument('input',type=Path);calc.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='template':
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x') as f:json.dump(TEMPLATE,f,ensure_ascii=False,indent=2);f.write('\n')
        print(f'Blank template: {args.output}');return
    source=args.input.read_bytes();profile=json.loads(source);report=analyze(profile)
    report['input_sha256']=hashlib.sha256(source).hexdigest()
    # Each calibration gets a new folder; never overwrite a previous record or actual site_config.h.
    args.output_dir.mkdir(parents=True,exist_ok=False)
    (args.output_dir/'measurements.json').write_bytes(source)
    (args.output_dir/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    (args.output_dir/'site_config.draft.h').write_text(
        '// DRAFT ONLY: merge references manually after verifying actual measurements.\n'
        f'// data_origin={profile["data_origin"]}\n'
        f'#define SG_DRY_RAW {report["dry_raw"]}\n#define SG_WET_RAW {report["wet_raw"]}\n'
        f'#define SG_CALIBRATION_ID "{profile["calibration_id"]}"\n'
        '#define SG_CALIBRATION_VERIFIED false\n#define SG_HARDWARE_VERIFIED false\n#define SG_AI_COMMANDS_ENABLED false\n')
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
