"""Human presentation checks; JSON qualification remains the existing owner's job."""
import base64
import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from spend_outcomes.__main__ import render
from spend_outcomes.core import encoded, inspect
from test_product import source, binding
import test_cli
from scripts.hn_delivery import build
from test_cli import ROOT


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.depth=0;self.visible=[];self.links=[];self.commands={};self.pre=None;self.machine=[]
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='details':
            assert 'open' not in attrs, 'machine details must start collapsed'
            self.depth+=1
        if tag=='a':self.links.append(attrs)
        if tag=='pre':self.pre=attrs.get('id')

    def handle_endtag(self, tag):
        if tag=='details':self.depth-=1
        if tag=='pre':self.pre=None

    def handle_data(self, text):
        if not self.depth:self.visible.append(text)
        if self.pre:
            self.commands[self.pre]=self.commands.get(self.pre,'')+text


def receipt():
    s=source();s['conflicts']={'total':0,'items':[]}
    r=inspect(s,{**binding(),'label':'Espansr'},[
        {'kind':'allocation','percent':5,'period':'weekly','unit':'tokens','account':a}
        for a in ('personal-openai','personal-anthropic')])
    r['outcomes']=[{'id':'result-130','intended_result':'One copyable block','delivered':True,'installed':True,
                    'acceptance':None,'benefit':None,'corrections':[{'text':'Cold-trigger correction reported','machine_causality':'unestablished'}],
                    'artifact':'https://example.test/result','association':'owner-attested'}]
    return r


class ReadableViewTests(unittest.TestCase):
    def test_human_facts_precede_collapsed_machine_evidence(self):
        r=receipt();before=copy.deepcopy(r);text=render(r);page=Page(text);visible=' '.join(page.visible)
        expected=['Espansr','2026-10-30','2026-11-05','Source as of','Observed consumption','Observed tokens',
                  'API-equivalent','Billed cash: Unknown','Delivered: Yes','Installed: Yes',
                  'Human acceptance: Unknown','Helpfulness / benefit: Unknown','Cold-trigger correction reported',
                  'Declared targets','personal-openai','personal-anthropic','5%','Comparison: Unknown',
                  'qualified account token denominator','Next move','Read and record feedback','Source qualifications']
        for value in expected:self.assertIn(value,visible)
        headings=['Observed consumption','Results','Declared targets','Next move','Read and record feedback','Source qualifications']
        positions=[text.index('<h2>'+h+'</h2>') for h in headings]
        self.assertEqual(positions,sorted(positions));self.assertLess(positions[-1],text.index('<details'))
        self.assertNotIn('"selection"',visible);self.assertNotIn('"source_versions"',visible)
        self.assertIn('non-additive',visible);self.assertIn('not cash',visible)
        self.assertEqual(r,before)

    def test_full_exact_receipt_download_survives_html_copy(self):
        r=receipt();r['extra_future_field']={'unknown':None,'text':'λ </pre> <script>evil</script>'}
        text=render(r);page=Page(text)
        download=next(a for a in page.links if a.get('download'))
        self.assertTrue(download['href'].startswith('data:application/json;base64,'))
        self.assertEqual(base64.b64decode(download['href'].split(',',1)[1]),encoded(r))
        self.assertEqual(page.commands['machine-json'],encoded(r).decode())
        with tempfile.TemporaryDirectory() as d:
            copied=Path(d)/'copy.html';copied.write_text(text)
            self.assertEqual(Page(copied.read_text()).links,page.links)
        self.assertNotIn('<script>',text)

    def test_untrusted_text_attributes_and_artifact_schemes(self):
        r=receipt();attack='"><img src=x onerror=alert(1)> & λ'
        r['selection']['label']=attack;r['outcomes'][0]['artifact']='javascript:alert(1)'
        r['outcomes'][0]['intended_result']=attack
        text=render(r);page=Page(text)
        self.assertNotIn('<img',text);self.assertIn('&lt;img',text)
        self.assertFalse(any(a.get('href','').startswith('javascript:') for a in page.links))
        self.assertIn(attack,' '.join(page.visible))
        self.assertIn('javascript:alert(1)',text)  # evidence retained as inert text

    def test_absent_data_is_unknown_and_contrary_history_stays_visible(self):
        r=receipt();r['consumption']['tokens']=None;r['consumption']['api_equivalent_cost_usd']=None
        r['outcomes'].append({**r['outcomes'][0],'review_verdict':'needs-changes','version':'new'})
        r['prior_comparison']={'status':'unsupported','reason':'Changed conditions'}
        text=render(r);visible=' '.join(Page(text).visible)
        for fact in ('Observed tokens: Unknown','API-equivalent estimate (USD): Unknown','needs-changes','Changed conditions'):
            self.assertIn(fact,visible)

    def exercise_commands(self, command):
        with tempfile.TemporaryDirectory(prefix='pv λ space ') as d:
            p=Path(d);config=test_cli.CLITests().setup_source(p);state=p/'private state'
            argv=[*command,'inspect','--config',str(config),'--project','workflow','--state',str(state),'--html']
            a=json.loads(subprocess.check_output(argv,cwd=ROOT,text=True))
            page=Page(Path(a['html']).read_text())
            show=shlex.split(page.commands['read-command'])
            self.assertEqual(show[:len(command)],command)
            self.assertEqual(show[-1],str(Path(a['receipt']).resolve()))
            self.assertEqual(json.loads(subprocess.check_output(show,cwd='/',text=True)),a['view'])
            record=shlex.split(page.commands['feedback-command'])
            self.assertEqual(record[:len(command)],command)
            self.assertIn(str(Path(a['receipt']).resolve()),record)
            saved=json.loads(subprocess.check_output(record,cwd='/',text=True))
            data=json.loads(Path(saved['record']).read_text())
            self.assertEqual(data['receipt'],a['sha256']);self.assertEqual(saved['execution_effects'],[])
            refresh=shlex.split(page.commands['refresh-command'])
            self.assertEqual(refresh[:len(command)],command)
            b=json.loads(subprocess.check_output(refresh,cwd=ROOT,text=True))
            self.assertEqual(b['receipt'],a['receipt'])
            download=next(x for x in page.links if x.get('download'))
            self.assertEqual(base64.b64decode(download['href'].split(',',1)[1]),Path(a['receipt']).read_bytes())

    def test_actual_cli_read_feedback_and_refresh_commands(self):
        # Absolute PYTHONPATH-independent source invocation, like installed archive.
        with tempfile.TemporaryDirectory() as d:
            wrapper=Path(d)/'local-cli.py'
            wrapper.write_text('import sys\nsys.path.insert(0,'+repr(str(ROOT))+')\nfrom spend_outcomes.__main__ import main\nraise SystemExit(main())\n')
            self.exercise_commands([sys.executable,str(wrapper)])

    def test_committed_archive_commands_and_complete_download(self):
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        built=build(ROOT,revision)
        with tempfile.TemporaryDirectory(prefix='pv archive ') as d:
            archive=Path(d)/'spend-outcomes.pyz';archive.write_bytes(built['bytes'])
            self.exercise_commands([sys.executable,str(archive)])

    def test_callsite_labels_project_without_changing_selection(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);config=test_cli.CLITests().setup_source(p)
            a=json.loads(subprocess.check_output([sys.executable,'-m','spend_outcomes','inspect',
                '--config',str(config),'--project','workflow','--state',str(p/'state'),'--html'],cwd=ROOT,text=True))
            visible=' '.join(Page(Path(a['html']).read_text()).visible)
            self.assertIn('Workflow',visible)
            self.assertNotIn('label',a['view']['selection'])
            refresh=shlex.split(Page(Path(a['html']).read_text()).commands['refresh-command'])
            for _ in range(2):
                again=json.loads(subprocess.check_output(refresh,cwd='/',text=True))
                self.assertEqual(again['receipt'],a['receipt'])
