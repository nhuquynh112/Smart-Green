import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('export_report',ROOT/'tools/export_ai_report.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ReportTest(unittest.TestCase):
    def test_metrics_checked_against_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            frame=pd.DataFrame({'timestamp':['2026-01-01T00:00:00Z'],'target':[20],**{n:[21] for n in m.LABELS}})
            frame.to_csv(d/'test_predictions.csv',index=False)
            meta={'quality':{'data_origin':'synthetic'},'test_mae_percentage_points':{n:1.0 for n in m.LABELS}}
            (d/'report.json').write_text(json.dumps(meta))
            self.assertEqual(len(m.load_results(d)[1]),1)
            meta['test_mae_percentage_points']['persistence']=0
            (d/'report.json').write_text(json.dumps(meta))
            with self.assertRaises(ValueError):m.load_results(d)
