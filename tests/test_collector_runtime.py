import datetime as dt
import http.client
import json
from pathlib import Path
import socket
import sqlite3
from contextlib import closing
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from spend_outcomes.claude import ClaudeStore
from spend_outcomes.runtime import CollectorRun, read_lifecycle
from spend_outcomes.device import run_command
from test_claude import payload

ROOT = Path(__file__).resolve().parents[1]


class CollectorRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = self.root / 'private-config.json'
        self.state = self.root / 'state'
        self.processes = []
        self.run_cli('device-init', '--config', self.config, '--state', self.state,
                     '--project', 'demo', '--workspace', self.root, '--claude',
                     '--tracking-start', '2026-11-01T00:00:00Z')
        self.store = Path(json.loads(self.config.read_text())['sources'][0]['store'])

    def tearDown(self):
        for process in self.processes:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
        self.temp.cleanup()

    def run_cli(self, *args):
        result = subprocess.run([sys.executable, '-m', 'spend_outcomes', *map(str, args)],
                                cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def free_port(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            return sock.getsockname()[1]

    def start(self, port):
        process = subprocess.Popen([sys.executable, '-m', 'spend_outcomes', 'collect',
            '--config', str(self.config), '--port', str(port)], cwd=ROOT, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
        self.processes.append(process)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self.fail('collector exited: ' + process.communicate()[1])
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=0.2)
            try:
                connection.request('GET', '/health')
                response = connection.getresponse()
                result = json.loads(response.read())
                if response.status == 200 and result.get('store_identity'):
                    return process, result
            except (OSError, http.client.HTTPException):
                pass
            finally:
                connection.close()
            time.sleep(0.05)
        self.fail('collector did not become reachable')

    def test_health_without_collector_creates_no_store(self):
        result = self.run_cli('collector-health', '--config', self.config, '--port', self.free_port())
        self.assertEqual(result['receiver']['status'], 'unreachable_or_mismatched')
        self.assertFalse(result['usage_sources_read'])
        self.assertFalse(self.store.exists())

    def test_unrelated_json_health_service_is_mismatch(self):
        args = SimpleNamespace(cmd='collector-health', config=self.config, port=4318)
        with patch('spend_outcomes.device.http.client.HTTPConnection') as connection:
            response = connection.return_value.getresponse.return_value
            response.status = 200
            response.read.return_value = b'[]'
            result = run_command(args, [])
        self.assertEqual(result['receiver']['status'], 'unreachable_or_mismatched')

    def test_legacy_store_refuses_startup_before_listening(self):
        store = ClaudeStore(self.store, '2026-11-01T00:00:00Z')
        store.ingest(payload(10, day=8, start=7))
        with closing(sqlite3.connect(self.store)) as db, db:
            db.execute("DELETE FROM metadata WHERE key='identity_schema_version'")
        result = subprocess.run([sys.executable, '-m', 'spend_outcomes', 'collect', '--config', str(self.config),
                                '--port', str(self.free_port())], cwd=ROOT, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn('prospective tracking-start cutover', result.stderr)
        self.assertNotIn('listening', result.stdout)
        self.assertEqual(read_lifecycle(self.store)['status'], 'unknown')

    def test_restart_replay_reports_and_singleton_are_independent(self):
        port = self.free_port()
        process, health = self.start(port)
        second = subprocess.run([sys.executable, '-m', 'spend_outcomes', 'collect', '--config', str(self.config),
                                 '--port', str(self.free_port())], cwd=ROOT, capture_output=True, text=True, timeout=5)
        self.assertEqual(second.returncode, 2)
        self.assertIn('lock timed out', second.stderr)
        body = json.dumps(payload(20, day=8, start=7, workspace=self.root)).encode()
        def post():
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
            try:
                connection.request('POST', '/v1/metrics', body, {'Content-Type': 'application/json'})
                response = connection.getresponse(); response.read()
                self.assertEqual(response.status, 200)
            finally:
                connection.close()
        post()
        report = self.run_cli('device-inspect', '--config', self.config, '--through', '2026-11-10')
        self.assertEqual(report['view']['consumption']['tokens'], 20)
        self.assertIsNone(process.poll())  # Reporting did not own/stop the receiver.
        verified = self.run_cli('collector-health', '--config', self.config, '--port', port)
        self.assertEqual(verified['receiver']['run_id'], health['run_id'])
        process.kill(); process.communicate(timeout=10)
        restarted, new_health = self.start(port)
        self.assertNotEqual(health['run_id'], new_health['run_id'])
        post()
        report = self.run_cli('device-inspect', '--config', self.config, '--through', '2026-11-10')
        self.assertEqual(report['view']['consumption']['tokens'], 20)
        lifecycle = report['view']['sources'][0]['collector_lifecycle']
        self.assertEqual(lifecycle['runs'][0]['status'], 'interrupted_without_shutdown')
        self.assertGreaterEqual(len(lifecycle['gaps']), 1)
        self.assertIsNone(restarted.poll())

    def test_heartbeat_gap_and_graceful_stop_are_retained(self):
        ClaudeStore(self.store, '2026-11-01T00:00:00Z')
        run = CollectorRun(self.store)
        earlier = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=2)
        run.last_heartbeat = earlier.isoformat()
        run.heartbeat()
        run.finish()
        evidence = read_lifecycle(self.store)
        self.assertEqual(evidence['status'], 'stopped')
        self.assertTrue(any(gap['reason'] == 'collector_heartbeat_gap' for gap in evidence['gaps']))


if __name__ == '__main__':
    unittest.main()
