import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_product import source

ROOT=Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def cli(self,*args,ok=True):
        r=subprocess.run(['python3','-m','spend_outcomes',*map(str,args)],cwd=ROOT,capture_output=True,text=True)
        if ok:self.assertEqual(r.returncode,0,r.stderr)
        else:self.assertEqual(r.returncode,2,r.stderr)
        return json.loads(r.stdout if ok else r.stderr)

    def setup_source(self,p):
        src=p/'consumer.json';src.write_text(json.dumps(source()))
        config={'telemetry':{'permitted':True,'export':{'path':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'permitted':True}},
                'projects':{'workflow':{'project_id':'canonical-p','telemetry_project_id':'p','association':'owner-attested','permitted':True}},
                'targets':{'workflow':[{'kind':'numeric','unit':'tokens','meaning':'observed','amount':100,'from':'2026-10-30','to':'2026-11-05'}]}}
        path=p/'config.json';path.write_text(json.dumps(config));return path

    def test_complete_selection_decision_export_reimport_and_correction(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);config=self.setup_source(p);state=p/'private'
            a=self.cli('inspect','--config',config,'--project','workflow','--state',state,'--html')
            b=self.cli('inspect','--config',config,'--project','workflow','--state',state,'--html')
            self.assertEqual(a['receipt'],b['receipt']);self.assertTrue(Path(a['html']).is_file())
            self.assertEqual(a['view']['comparisons'][0]['excess'],20)
            record_args=['record','--receipt',a['receipt'],'--state',state,'--id','decision-1','--actor','operator','--decision','keep','--feedback','Contrary result']
            record=self.cli(*record_args)['record'];original=Path(record).read_bytes()
            self.cli(*record_args);self.assertEqual(Path(record).read_bytes(),original)
            self.cli('export','--input',record,'--output',p/'export.json')
            self.cli('import','--input',p/'export.json','--state',p/'other')
            self.cli('import','--input',p/'export.json','--state',p/'other')
            self.assertEqual((p/'other/decisions/decision-1.json').read_bytes(),original)
            changed=json.loads(original);changed['feedback']='changed';(p/'changed.json').write_text(json.dumps(changed))
            self.cli('import','--input',p/'changed.json','--state',state,ok=False)
            self.assertEqual(Path(record).read_bytes(),original)

    def test_digest_refusal_and_no_private_receipt_export(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);config=self.setup_source(p)
            a=self.cli('inspect','--config',config,'--project','workflow','--state',p/'state')
            self.cli('export','--input',a['receipt'],'--output',p/'leak.json',ok=False)
            self.assertFalse((p/'leak.json').exists())
            (p/'consumer.json').write_text('{}')
            r=self.cli('inspect','--config',config,'--project','workflow','--state',p/'state',ok=False)
            self.assertIn('digest mismatch',r['reason'])

    def test_html_escapes_operator_content(self):
        from spend_outcomes.__main__ import render
        from spend_outcomes.core import inspect
        from test_product import binding
        r=inspect(source(),binding(),[{'kind':'qualitative','aim':'<script>alert(1)</script>'}])
        self.assertNotIn('<script>',render(r));self.assertIn('&lt;script&gt;',render(r))
