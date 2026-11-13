import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sqlite3
from contextlib import closing
import sys
import tempfile
import unittest
from unittest.mock import patch

from spend_outcomes.claude import ClaudeStore
from spend_outcomes.device import device_report, load_config, merge_observations, observe_source
from spend_outcomes.storage import atomic_bytes
from spend_outcomes.__main__ import command_text
from test_claude import payload
from test_public_v1 import write_session

ROOT = Path(__file__).resolve().parents[1]


class DeviceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = self.root / 'project'; self.workspace.mkdir()
        self.config = self.root / 'config.json'
        self.logs = self.root / 'synthetic-codex'
        self.state = self.root / 'private-state'

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, '-m', 'spend_outcomes', *map(str, args)],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0 if ok else 2, result.stderr)
        return json.loads(result.stdout if ok else result.stderr)

    def initialize(self, *extra):
        return self.cli('device-init', '--config', self.config, '--state', self.state,
            '--project', 'demo', '--workspace', self.workspace, '--codex-root', self.logs,
            '--claude', '--tracking-start', '2026-11-01T00:00:00Z', *extra)

    def test_init_and_doctor_do_not_read_sources_or_create_store(self):
        result = self.initialize()
        self.assertFalse(self.state.exists())
        self.assertFalse(self.logs.exists())
        self.assertFalse(result['sources_read'])
        doctor = self.cli('doctor', '--config', self.config)
        self.assertFalse(doctor['sources_read'])
        self.assertFalse(self.state.exists())
        before = self.config.read_bytes()
        self.initialize_failure()
        self.assertEqual(before, self.config.read_bytes())

    def initialize_failure(self):
        return self.cli('device-init', '--config', self.config, '--state', self.state,
                        '--project', 'demo', '--workspace', self.workspace, '--claude', ok=False)

    def test_tandem_device_and_project_html(self):
        self.initialize('--target-tokens', 1000, '--outcome', 'A useful result',
                        '--success-criterion', 'Operator review', '--checkpoint', 'review=Review report')
        write_session(self.logs / 'one.jsonl', self.workspace)
        config = load_config(self.config)
        store = ClaudeStore(config['sources'][1]['store'], config['tracking_start'])
        store.ingest(payload(20, day=8, start=7, workspace=self.workspace))
        result = self.cli('device-inspect', '--config', self.config, '--through', '2026-11-10', '--html')
        view = result['view']
        self.assertEqual(view['consumption']['tokens'], 185)
        self.assertEqual({row['client'] for row in view['consumption']['provider_models']}, {'codex', 'claude-code'})
        self.assertEqual(view['projects'][0]['consumption']['tokens'], 185)
        self.assertEqual(view['projects'][0]['comparisons'][0]['status'], 'unknown')
        self.assertEqual(view['projects'][0]['operator_outcome']['checkpoints'][0]['status'], 'pending')
        raw = Path(result['html']).read_text(encoding='utf-8')
        self.assertIn('Source coverage', raw)
        self.assertNotIn('PRIVATE PROMPT', raw)
        self.assertNotIn('PRIVATE_SENTINEL', raw)
        self.assertTrue(Path(result['receipt']).is_file())

    def test_missing_source_preserves_other_source_and_all_missing_unknown(self):
        self.initialize()
        empty = device_report(load_config(self.config), through='2026-11-10')
        self.assertIsNone(empty['consumption']['tokens'])
        self.assertEqual(empty['coverage']['status'], 'unavailable')
        write_session(self.logs / 'one.jsonl', self.workspace)
        view = device_report(load_config(self.config), through='2026-11-10')
        self.assertEqual(view['consumption']['tokens'], 165)
        self.assertEqual(view['coverage']['status'], 'partial')

    def test_empty_existing_claude_store_is_unknown(self):
        self.initialize()
        config = load_config(self.config)
        ClaudeStore(config['sources'][1]['store'], config['tracking_start'])
        view = device_report(config, through='2026-11-10')
        self.assertIsNone(view['consumption']['tokens'])
        self.assertEqual(view['coverage']['status'], 'unavailable')

    def test_process_timeout_retains_other_sources(self):
        self.initialize()
        config = load_config(self.config)
        with patch('spend_outcomes.device.subprocess.run', side_effect=subprocess.TimeoutExpired('scan', 35)):
            result = observe_source(config['sources'][0], config, None, 7, '2026-11-10')
        self.assertEqual(result['status'], 'unavailable')
        self.assertIn('TimeoutExpired', result['coverage']['issues'][0])

    def test_corrupt_store_does_not_abort_other_sources(self):
        self.initialize()
        write_session(self.logs / 'one.jsonl', self.workspace)
        config = load_config(self.config)
        self.state.mkdir()
        Path(config['sources'][1]['store']).write_bytes(b'not a database')
        view = device_report(config, through='2026-11-10')
        self.assertEqual(view['consumption']['tokens'], 165)
        self.assertEqual(view['coverage']['status'], 'partial')

    def test_semantically_invalid_store_preserves_codex(self):
        self.initialize()
        write_session(self.logs / 'one.jsonl', self.workspace)
        config = load_config(self.config)
        store = ClaudeStore(config['sources'][1]['store'], config['tracking_start'])
        store.ingest(payload(20, day=8, start=7, workspace=self.workspace))
        with closing(sqlite3.connect(store.path)) as db, db:
            db.execute("UPDATE points SET dimensions='{}'")
        view = device_report(config, through='2026-11-10')
        self.assertEqual(view['consumption']['tokens'], 165)
        self.assertEqual(view['coverage']['status'], 'partial')

    def test_concurrent_checkpoint_updates_preserve_all_history(self):
        self.initialize('--outcome', 'Result', '--success-criterion', 'Evidence', '--checkpoint', 'review=Review')
        command = [sys.executable, '-m', 'spend_outcomes', 'checkpoint', '--config', str(self.config),
                   '--project', 'demo', '--id', 'review', '--status', 'in-progress', '--actor', 'operator']
        def update(number):
            return subprocess.run([*command, '--note', str(number)], cwd=ROOT, capture_output=True, text=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(update, range(12)))
        self.assertTrue(all(result.returncode == 0 for result in results), [result.stderr for result in results])
        history = json.loads(self.config.read_text())['outcome']['history']
        self.assertEqual(len(history), 12)
        self.assertEqual({item['note'] for item in history}, {str(number) for number in range(12)})

    def test_immutable_concurrent_retry_and_conflict(self):
        path = self.root / 'receipt.json'
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: atomic_bytes(path, b'complete data'), range(16)))
        self.assertEqual(path.read_bytes(), b'complete data')
        with self.assertRaises(ValueError):
            atomic_bytes(path, b'conflicting data')
        self.assertEqual(path.read_bytes(), b'complete data')

    def test_config_permissions_fail_closed(self):
        self.initialize()
        config = json.loads(self.config.read_text())
        config['sources'][0]['permitted'] = False
        self.config.write_text(json.dumps(config))
        result = self.cli('device-inspect', '--config', self.config, ok=False)
        self.assertEqual(result['status'], 'held')
        self.assertFalse(self.state.exists())

    @unittest.skipUnless(os.name == 'nt', 'native PowerShell command rendering')
    def test_native_command_with_unicode_space_and_apostrophe(self):
        value = "C:\\synthetic space\\O'Brien\\\u03bb"
        argv = [sys.executable, '-c', 'import json,sys; print(json.dumps(sys.argv[1:]))', value]
        result = subprocess.run(['powershell', '-NoProfile', '-Command', command_text(argv)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [value])


if __name__ == '__main__':
    unittest.main()
