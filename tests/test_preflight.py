import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from spend_outcomes.export_plan import make_export_plan

ROOT = Path(__file__).resolve().parents[1]


class PreflightTests(unittest.TestCase):
    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, '-m', 'spend_outcomes', *map(str, args)],
                                cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0 if ok else 2, result.stderr)
        return json.loads(result.stdout if ok else result.stderr)

    def test_export_plan_does_not_read_or_change_environment(self):
        before = dict(os.environ)
        for entrypoint in ('cli', 'vscode', 'desktop'):
            result = make_export_plan(4319, entrypoint)
            self.assertFalse(result['applied'])
            self.assertFalse(result['settings_read'])
            self.assertEqual(result['proposed_environment']['OTEL_LOGS_EXPORTER'], 'none')
            self.assertEqual(result['proposed_environment']['OTEL_TRACES_EXPORTER'], 'none')
            self.assertIn('OTEL_EXPORTER_OTLP_HEADERS', result['must_be_absent_from_effective_configuration'])
            self.assertIn('BETA_TRACING_ENDPOINT', result['must_be_absent_from_effective_configuration'])
        self.assertEqual(before, dict(os.environ))
        self.assertEqual(self.cli('export-plan')['status'], 'review_required')

    def test_synthetic_reviewer_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'new-demo'
            result = self.cli('device-demo', '--root', root)
            self.assertTrue(result['synthetic'])
            self.assertFalse(result['real_usage_read'])
            self.assertTrue(result['view']['synthetic'])
            self.assertEqual(result['view']['consumption']['tokens'], 300)
            html = Path(result['html']).read_text(encoding='utf-8')
            self.assertIn('Synthetic demonstration only', html)
            self.assertIn('No real usage was read', html)
            old = Path(result['receipt']).read_bytes()
            self.cli('checkpoint', '--config', result['config'], '--project', 'demo', '--id', 'review',
                     '--status', 'complete', '--actor', 'reviewer', '--note', 'Synthetic review')
            second = self.cli('device-inspect', '--config', result['config'], '--html')
            self.assertEqual(second['view']['projects'][0]['operator_outcome']['checkpoints'][0]['status'], 'complete')
            self.assertEqual(Path(result['receipt']).read_bytes(), old)
            self.cli('device-demo', '--root', root, ok=False)

    @unittest.skipUnless(os.name == 'nt', 'native Windows lifecycle command plan')
    def test_lifecycle_cli_only_writes_staging(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); config = root / 'config.json'; state = root / 'state'
            self.cli('device-init', '--config', config, '--state', state, '--project', 'demo', '--workspace', root, '--claude')
            staged = root / 'review-plan'
            result = self.cli('lifecycle-plan', '--config', config, '--platform', 'windows',
                '--runtime-root', ROOT, '--python', sys.executable, '--output', staged,
                '--user-id', 'EXAMPLE\\Reviewer')
            self.assertFalse(result['registered'])
            self.assertFalse(result['started'])
            self.assertFalse(result['commands_executed'])
            self.assertTrue(Path(result['plan_file']).is_file())
            self.assertFalse(state.exists())


if __name__ == '__main__':
    unittest.main()
