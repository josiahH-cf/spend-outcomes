"""First run uses only the executable and operator-selected source bindings."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from scripts.hn_delivery import build
from test_product import source

ROOT = Path(__file__).resolve().parents[1]


class FirstRunTests(unittest.TestCase):
    def command(self, command, cwd, *args, ok=True):
        r = subprocess.run([*command, *map(str, args)], cwd=cwd, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0 if ok else 2, r.stderr)
        return json.loads(r.stdout) if ok else r

    def exercise(self, command, p):
        src = p/'permitted source.json'
        src.write_text(json.dumps(source()))
        sha = hashlib.sha256(src.read_bytes()).hexdigest()
        config = p/'config directory'/'private config.json'
        config.parent.mkdir()
        state = p/'private state'
        args = ['init', '--config', config, '--project', 'workflow', '--project-id', 'canonical-p',
                '--telemetry-project-id', 'p', '--association', 'owner-attested',
                '--telemetry-export', src.name, '--sha256', sha, '--state', state]
        for help_args in (['--help'], ['init', '--help']):
            r = subprocess.run([*command, *help_args], cwd=p, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
        self.command(command, p, 'init', '--config', config, ok=False)
        self.assertFalse(config.exists());self.assertFalse(state.exists())
        result = self.command(command, p, *args)
        self.assertFalse(state.exists())
        if os.name != 'nt':
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
        original = config.read_bytes();data = json.loads(original)
        self.assertEqual(data['targets'], {})
        self.assertEqual(data['telemetry']['export']['path'], str(src))
        self.assertEqual(data['projects']['workflow']['association'], 'owner-attested')
        # Retry collisions preserve bytes, rather than reconciling init.
        self.command(command, p, *args, ok=False);self.assertEqual(config.read_bytes(), original)
        inspected = self.command(result['inspect_argv'], p)
        self.assertEqual(inspected['view']['consumption']['tokens'], 120)
        self.assertEqual(inspected['view']['comparisons'], [])
        self.assertIsNone(inspected['view']['consumption']['billed_cash_usd'])
        self.assertTrue(Path(inspected['html']).is_file())
        src.write_text('{}')
        refusal = self.command(result['inspect_argv'], p, ok=False)
        self.assertIn('digest mismatch', refusal.stderr)
        self.assertEqual(config.read_bytes(), original)

    def test_symlink_config_is_not_overwritten(self):
        import sys
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source_path=root/'export.json';source_path.write_text(json.dumps(source()))
            sha=hashlib.sha256(source_path.read_bytes()).hexdigest();config=root/'config.json'
            try:
                config.symlink_to(source_path)
            except OSError as error:
                if os.name=='nt' and getattr(error,'winerror',None)==1314:
                    self.skipTest('Windows runner lacks symlink privilege; no settings changed')
                raise
            self.command([sys.executable,'-m','spend_outcomes'],ROOT,'init','--config',config,
                '--project','workflow','--project-id','canonical-p','--telemetry-project-id','p',
                '--association','owner-attested','--telemetry-export',source_path,'--sha256',sha,
                '--state',root/'state',ok=False)
            self.assertEqual(hashlib.sha256(source_path.read_bytes()).hexdigest(),sha)

    def test_live_binding_reads_only_on_inspect_and_missing_source_is_disclosed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);marker=p/'called';consumer=p/'consumer.py'
            consumer.write_text('from pathlib import Path\nimport json,sys\nPath('+repr(str(marker))+').write_text(json.dumps(sys.argv[1:]))\nprint('+repr(json.dumps(source()))+')\n')
            command=[sys.executable,'-c','import sys; sys.path.insert(0,'+repr(str(ROOT))+'); from spend_outcomes.__main__ import main; raise SystemExit(main())']
            args=['init','--config','config.json','--project','workflow','--project-id','canonical-p',
                  '--telemetry-project-id','p','--association','correlated','--consumer','consumer.py',
                  '--state-root','producer state','--state','product state']
            r=self.command(command,p,*args)
            self.assertFalse(marker.exists());self.assertFalse((p/'product state').exists())
            inspected=self.command(r['inspect_argv'],p)
            self.assertEqual(inspected['view']['consumption']['tokens'],120)
            called=json.loads(marker.read_text())
            self.assertEqual(called[-2:],['--state-root',str(p/'producer state')])
            consumer.write_text("raise SystemExit(1)\n")
            held=self.command(r['inspect_argv'],p)
            self.assertEqual(held['view']['source']['status'],'unavailable')
            self.assertIsNone(held['view']['consumption']['tokens'])

    def test_incomplete_and_invalid_binding_creates_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            command=[sys.executable,'-c','import sys; sys.path.insert(0,'+repr(str(ROOT))+'); from spend_outcomes.__main__ import main; raise SystemExit(main())']
            args=['init','--config','config.json','--project','w','--project-id','canonical',
                  '--telemetry-project-id','p','--association','owner-attested',
                  '--telemetry-export','missing.json','--sha256','a'*64,'--state','state']
            for option in ('--project-id','--telemetry-project-id','--association','--telemetry-export','--sha256'):
                incomplete=args.copy();i=incomplete.index(option);del incomplete[i:i+2]
                self.command(command,p,*incomplete,ok=False)
                self.assertEqual(list(p.iterdir()),[])
            invalid=args.copy();invalid[invalid.index('--sha256')+1]='bad'
            self.command(command,p,*invalid,ok=False);self.assertEqual(list(p.iterdir()),[])
            blank=args.copy();blank[blank.index('--project-id')+1]=' '
            self.command(command,p,*blank,ok=False);self.assertEqual(list(p.iterdir()),[])
            # No digest verification or source read occurs at config creation.
            self.command(command,p,*args)
            self.assertEqual([x.name for x in p.iterdir()],['config.json'])

    def test_source_first_run(self):
        with tempfile.TemporaryDirectory() as d:
            # Bind source invocation explicitly while cwd has no repository files.
            command = [sys.executable, '-c', 'import sys; sys.path.insert(0,'+repr(str(ROOT))+'); from spend_outcomes.__main__ import main; raise SystemExit(main())']
            self.exercise(command, Path(d))

    def test_committed_archive_first_run(self):
        revision = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);app=p/'app.pyz';app.write_bytes(build(ROOT,revision)['bytes'])
            self.exercise([sys.executable, str(app)], p)
