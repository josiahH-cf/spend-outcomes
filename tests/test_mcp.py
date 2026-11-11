import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from spend_outcomes import mcp
from spend_outcomes.claude import ClaudeStore
from spend_outcomes.codex import parse_codex_file, _walk_guarded

ROOT = Path(__file__).resolve().parents[1]


def apply(name, arguments):
    preview = mcp.execute(name, arguments)
    return mcp.execute(name, {**arguments, 'apply': True, 'expected_plan_sha256': preview['plan_sha256']})


class MCPTools(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='cherry mcp ')
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def demo(self):
        return apply('cherry_meter_demo', {'root': str(self.root / 'demo')})

    def test_preview_has_no_effects_and_hash_is_not_consent(self):
        args = {'root': str(self.root / 'demo')}
        plan = mcp.execute('cherry_meter_demo', args)
        self.assertFalse(Path(args['root']).exists())
        self.assertIn('not user consent', plan['approval_notice'])
        with self.assertRaises(mcp.Held):
            mcp.execute('cherry_meter_demo', {**args, 'apply': True})
        with self.assertRaises(mcp.Held):
            mcp.execute('cherry_meter_demo', {**args, 'root': str(self.root / 'other'), 'apply': True, 'expected_plan_sha256': plan['plan_sha256']})

    def test_demo_report_checkpoint_never_spawn_or_connect(self):
        with patch('subprocess.run', side_effect=AssertionError('subprocess forbidden')), patch('subprocess.Popen', side_effect=AssertionError('spawn forbidden')), patch('socket.socket', side_effect=AssertionError('network forbidden')):
            demo = self.demo()
            self.assertTrue(demo['synthetic'])
            self.assertEqual(demo['consumption']['tokens'], 300)
            self.assertNotIn('checkpoint_argv', demo)
            config = demo['config']
            diagnosis = mcp.execute('cherry_meter_doctor', {'config': config})
            self.assertFalse(diagnosis['sources_read'])
            plan = mcp.execute('cherry_meter_report', {'config': config})
            sidecars = plan['plan']['scope']['possible_sqlite_sidecar_writes']
            self.assertEqual(len(sidecars), 2)
            self.assertTrue(sidecars[0].endswith('-wal'))
            result = apply('cherry_meter_report', {'config': config})
            self.assertEqual(result['consumption']['tokens'], 300)
            self.assertTrue(Path(result['html']).is_file())
            self.assertNotIn('Refresh explicitly', Path(result['html']).read_text(encoding='utf-8'))
            update = apply('cherry_meter_checkpoint', {'config': config, 'project': 'demo', 'id': 'review',
                'status': 'complete', 'actor': 'Test operator', 'note': 'Reviewed synthetic sample'})
            self.assertEqual(update['checkpoint']['provenance'], 'operator-reported')
            value = json.loads(Path(config).read_bytes())
            self.assertEqual(len(value['outcome']['history']), 1)
            self.assertTrue(Path(demo['receipt']).is_file())

    def test_setup_creates_only_config_and_refuses_overwrite(self):
        workspace = self.root / 'work'; workspace.mkdir()
        args = {'config': str(self.root / 'device.json'), 'state': str(self.root / 'state'),
                'project': 'test', 'workspace': str(workspace), 'device_name': 'Synthetic',
                'tracking_start': '2026-11-01T00:00:00+00:00', 'claude': True}
        preview = mcp.execute('cherry_meter_setup', args)
        self.assertFalse(Path(args['config']).exists())
        self.assertFalse(Path(args['state']).exists())
        details = preview['plan']['write_details']
        self.assertEqual(details['direct_exclusive_file'], args['config'])
        self.assertEqual(details['atomic_files'], [])
        self.assertEqual(details['sqlite_files'], [])
        self.assertFalse(details['directory_creation'])
        before = set(self.root.rglob('*'))
        with patch('tempfile.mkstemp', side_effect=AssertionError('setup must not create temporary files')), patch('spend_outcomes.storage.file_lock', side_effect=AssertionError('setup must not create lock files')), patch('sqlite3.connect', side_effect=AssertionError('setup must not open SQLite')):
            result = mcp.execute('cherry_meter_setup', {**args, 'apply': True, 'expected_plan_sha256': preview['plan_sha256']})
        self.assertEqual(set(self.root.rglob('*')) - before, {Path(args['config'])})
        self.assertFalse(result['sources_read'])
        self.assertFalse(Path(args['state']).exists())
        self.assertNotIn('collector_argv', result)
        with self.assertRaises(mcp.Held):
            apply('cherry_meter_setup', args)

    def test_demo_and_report_plans_describe_actual_ancillary_files(self):
        root = self.root / 'demo'
        args = {'root': str(root)}
        preview = mcp.execute('cherry_meter_demo', args)
        self.assertFalse(root.exists())
        details = preview['plan']['write_details']
        store = root / 'private-demo-state' / 'claude-metrics.sqlite3'
        self.assertEqual(details['sqlite_store'], str(store))
        self.assertEqual(details['possible_sqlite_sidecar_writes'],
                         [str(store) + suffix for suffix in ('-wal', '-shm', '-journal')])
        temporary_files = []
        sqlite_files = set()
        original_mkstemp = tempfile.mkstemp
        original_connect = sqlite3.connect

        def remember_sqlite_files():
            sqlite_files.update(str(path) for path in store.parent.glob(store.name + '*'))

        class RecordingConnection(sqlite3.Connection):
            def execute(self, *args, **kwargs):
                result = super().execute(*args, **kwargs)
                remember_sqlite_files()
                return result

            def executescript(self, *args, **kwargs):
                result = super().executescript(*args, **kwargs)
                remember_sqlite_files()
                return result

            def close(self):
                remember_sqlite_files()
                return super().close()

        def connect(*args, **kwargs):
            return original_connect(*args, **kwargs, factory=RecordingConnection)

        def mkstemp(*args, **kwargs):
            descriptor, path = original_mkstemp(*args, **kwargs)
            temporary_files.append(Path(path))
            return descriptor, path

        with patch('tempfile.mkstemp', side_effect=mkstemp), patch('sqlite3.connect', side_effect=connect):
            result = mcp.execute('cherry_meter_demo', {**args, 'apply': True,
                'expected_plan_sha256': preview['plan_sha256']})
        identity = Path(result['receipt']).stem
        atomic_files = details['atomic_files']
        self.assertEqual(len(atomic_files), 4)
        self.assertEqual(len(temporary_files), 4)
        expected_files = {str(store), *details['possible_sqlite_sidecar_writes']}
        for entry in atomic_files:
            target = Path(entry['file'].replace('<report-sha256>', identity))
            lock = Path(entry['persistent_lock_file'].replace('<report-sha256>', identity))
            pattern = Path(entry['temporary_file_pattern'].replace('<report-sha256>', identity))
            self.assertTrue(target.is_file())
            self.assertTrue(lock.is_file())
            self.assertTrue(any(path.parent == pattern.parent and
                path.name.startswith(pattern.name.replace('<random>', '')) for path in temporary_files))
            expected_files.update((str(target), str(lock)))
        self.assertTrue(all(not path.exists() for path in temporary_files))
        self.assertLessEqual({str(path) for path in root.rglob('*') if path.is_file()}, expected_files)
        self.assertEqual({str(root), *(str(path) for path in root.rglob('*') if path.is_dir())}, set(details['directories']))
        self.assertLessEqual(sqlite_files, {str(store), *details['possible_sqlite_sidecar_writes']})
        self.assertTrue({str(store) + '-wal', str(store) + '-shm'}.issubset(sqlite_files))

        report_args = {'config': result['config'], 'html': False}
        report_preview = mcp.execute('cherry_meter_report', report_args)
        report_details = report_preview['plan']['write_details']
        self.assertEqual(len(report_details['atomic_files']), 1)
        self.assertEqual(report_details['possible_sqlite_sidecar_writes'], [str(store) + '-wal', str(store) + '-shm'])
        before = {path for path in root.rglob('*') if path.is_file()}
        database_before = store.read_bytes()
        temporary_files.clear()
        with patch('tempfile.mkstemp', side_effect=mkstemp), patch('sqlite3.connect', side_effect=connect):
            report_result = mcp.execute('cherry_meter_report', {**report_args, 'apply': True,
                'expected_plan_sha256': report_preview['plan_sha256']})
        receipt = Path(report_result['receipt'])
        entry = report_details['atomic_files'][0]
        lock = Path(entry['persistent_lock_file'].replace('<report-sha256>', receipt.stem))
        self.assertEqual(Path(entry['file'].replace('<report-sha256>', receipt.stem)), receipt)
        self.assertEqual({path for path in root.rglob('*') if path.is_file()} - before, {receipt, lock})
        self.assertEqual(len(temporary_files), 1)
        self.assertEqual(temporary_files[0].parent, receipt.parent)
        self.assertTrue(temporary_files[0].name.startswith('.' + receipt.name + '.'))
        self.assertFalse(temporary_files[0].exists())
        self.assertIsNone(report_result['html'])
        self.assertEqual(database_before, store.read_bytes())

    def test_ancillary_descriptions_are_bound_into_approval_hashes(self):
        workspace = self.root / 'work'; workspace.mkdir()
        setup = {'config': str(self.root / 'device.json'), 'state': str(self.root / 'state'),
                 'project': 'test', 'workspace': str(workspace), 'device_name': 'Synthetic',
                 'tracking_start': '2026-11-01T00:00:00+00:00', 'claude': True}
        demo = self.demo()
        for name, arguments in (
                ('cherry_meter_setup', setup),
                ('cherry_meter_demo', {'root': str(self.root / 'another-demo')}),
                ('cherry_meter_report', {'config': demo['config']})):
            preview = mcp.execute(name, arguments)
            old_plan = copy.deepcopy(preview['plan'])
            old_plan.pop('write_details')
            old_hash = mcp.digest(old_plan)
            self.assertNotEqual(old_hash, preview['plan_sha256'])
            before = {path: path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
            with self.assertRaises(mcp.Held):
                mcp.execute(name, {**arguments, 'apply': True, 'expected_plan_sha256': old_hash})
            after = {path: path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
            self.assertEqual(before, after)

    def test_changed_config_rejects_stale_report_and_checkpoint(self):
        demo = self.demo(); args = {'config': demo['config']}
        plan = mcp.execute('cherry_meter_report', args)
        path = Path(demo['config']); config = json.loads(path.read_bytes())
        config['device']['label'] = 'Changed'; path.write_text(json.dumps(config), encoding='utf-8')
        with self.assertRaises(mcp.Held):
            mcp.execute('cherry_meter_report', {**args, 'apply': True, 'expected_plan_sha256': plan['plan_sha256']})

    def test_rejects_unknown_tools_fields_legacy_and_relative_paths(self):
        for name in ('collect', 'inspect', 'show', 'consumer', 'lifecycle-plan'):
            with self.assertRaises(mcp.Held):mcp.execute(name, {})
        for value in ('relative.json', '../secret.json', '\\\\server\\share\\config.json', '//server/share/config.json'):
            with self.assertRaises(mcp.Held):mcp.execute('cherry_meter_doctor', {'config': value})
        with self.assertRaises(mcp.Held):mcp.execute('cherry_meter_info', {'command': 'anything'})
        config = self.root / 'device.json'; config.write_text('{"telemetry":{"consumer":"evil.py"}}')
        with self.assertRaises(mcp.Held):mcp.execute('cherry_meter_doctor', {'config': str(config)})
        config.write_bytes(b'x' * (mcp.MAX_CONFIG + 1))
        with self.assertRaises(mcp.Held):mcp.execute('cherry_meter_doctor', {'config': str(config)})

    def test_rejects_reparse_ancestor_before_resolving(self):
        path = self.root / 'link' / 'device.json'
        real = Path.lstat
        def lstat(selected, *args, **kwargs):
            if selected == path.parent:
                return type('Stat', (), {'st_mode': 0o40700, 'st_file_attributes': 0x400})()
            return real(selected, *args, **kwargs)
        with patch.object(Path, 'lstat', lstat), patch.object(Path, 'resolve', side_effect=AssertionError('must not resolve')):
            with self.assertRaises(mcp.Held):mcp.local_path(str(path))

    @unittest.skipUnless(os.name == 'nt', 'Windows drive classification')
    def test_mapped_drive_rejected_before_stat(self):
        with patch('ctypes.windll.kernel32.GetDriveTypeW', return_value=4), patch.object(Path, 'lstat', side_effect=AssertionError('remote stat forbidden')):
            with self.assertRaises(mcp.Held):mcp.local_path('Z:\\private\\device.json')

    def test_unknown_fields_never_returned_to_client(self):
        demo=self.demo(); path=Path(demo['config']); original=json.loads(path.read_bytes())
        for mutate in (lambda c:c['sources'][0].update({'headers':{'Authorization':'SYNTHETIC_PRIVATE_FIELD'}}),
                       lambda c:c['projects']['demo'].update({'private_note':'SYNTHETIC_PRIVATE_FIELD'}),
                       lambda c:c['device'].update({'private_note':'SYNTHETIC_PRIVATE_FIELD'}),
                       lambda c:c['sources'][0].update({'id':{'private_note':'SYNTHETIC_PRIVATE_FIELD'}}),
                       lambda c:c['sources'][0].update({'bindings':{'Authorization':'SYNTHETIC_PRIVATE_FIELD'}}),
                       lambda c:c['sources'][1].update({'roots':[{'secret':'SYNTHETIC_PRIVATE_FIELD'}]})):
            config=copy.deepcopy(original); mutate(config); path.write_text(json.dumps(config),encoding='utf-8')
            for name in ('cherry_meter_doctor','cherry_meter_report'):
                with self.assertRaises(mcp.Held) as caught:mcp.execute(name,{'config':str(path)})
                self.assertNotIn('SYNTHETIC_PRIVATE_FIELD',str(caught.exception))

    def test_malicious_metadata_workspace_never_normalized(self):
        path = self.root / 'sample.jsonl'
        rows = [{'type': 'session_meta', 'timestamp': '2026-11-01T00:00:01Z', 'payload': {'id': 'test', 'cwd': '\\\\server\\share'}}]
        path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n')
        with patch('spend_outcomes.codex._normal', side_effect=AssertionError('untrusted path normalized')):
            value = parse_codex_file(path, path_guard=lambda p: mcp.local_path(str(p)))
        self.assertIsNone(value['workspace'])
        if os.name == 'nt':self.assertIn('unsupported_workspace_path', value['issues'])

    def test_guarded_scan_never_follows_entry_to_classify_it(self):
        class Entry:
            name='linked'; path=str(self.root/'linked')
            def stat(self, *, follow_symlinks):
                self_test.assertFalse(follow_symlinks)
                return SimpleNamespace(st_mode=0o40700, st_file_attributes=0x400)
            def is_dir(self, **kwargs):
                raise AssertionError('classification must use no-follow stat')
        class Scan:
            def __enter__(self):return iter([Entry()])
            def __exit__(self,*args):pass
        self_test=self; issues=[]; checked=[]
        with patch('spend_outcomes.codex.os.scandir',return_value=Scan()):
            rows=list(_walk_guarded(self.root,lambda value:checked.append(value),time.monotonic()+10,issues))
        self.assertEqual(rows,[(str(self.root),[],[])])
        self.assertIn('unsupported_source_path',issues)
        self.assertEqual(checked,[self.root])

    def test_sql_readonly_preserves_data_and_reads_live_wal(self):
        path = self.root / 'store.sqlite3'
        start = '2026-11-01T00:00:00+00:00'
        ClaudeStore(path, start)
        db = sqlite3.connect(path)
        try:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute("INSERT INTO issues VALUES('test-live-wal')"); db.commit()
            before = path.read_bytes()
            reader = ClaudeStore(path, start, read_only=True, max_rows=10)
            self.assertIn('test-live-wal', reader._snapshot()[1])
            self.assertEqual(before, path.read_bytes())
            with reader._connect() as connection:
                with self.assertRaises(sqlite3.OperationalError):connection.execute('DELETE FROM issues')
        finally:db.close()

    def test_snapshot_and_cancel_limits(self):
        path = self.root / 'store.sqlite3'; start = '2026-11-01T00:00:00+00:00'
        ClaudeStore(path, start)
        reader = ClaudeStore(path, start, read_only=True, max_rows=1)
        with self.assertRaises(ValueError):reader._snapshot()
        cancel = threading.Event(); cancel.set()
        with self.assertRaises(mcp.Cancelled):mcp.execute('cherry_meter_demo', {'root': str(self.root / 'demo')}, cancel)
        self.assertFalse((self.root / 'demo').exists())

    def test_oversized_sqlite_cell_rejected_before_snapshot(self):
        path=self.root/'store.sqlite3'; start='2026-11-01T00:00:00+00:00'
        ClaudeStore(path,start)
        with sqlite3.connect(path) as connection:
            connection.execute('INSERT INTO issues VALUES(?)',('x'*32769,))
        connection.close()
        with self.assertRaises(ValueError):ClaudeStore(path,start,read_only=True,max_rows=50000)

    def test_metadata_view_rejected_without_evaluating_expression(self):
        path=self.root/'store.sqlite3'; start='2026-11-01T00:00:00+00:00'
        ClaudeStore(path,start)
        connection=sqlite3.connect(path)
        connection.executescript("DROP TABLE metadata; CREATE VIEW metadata AS SELECT 'tracking_start' AS key, audit_probe() AS value;")
        connection.close()
        calls=[]; original=sqlite3.connect
        class WithoutSetlimit:
            def __init__(self, connection):self.connection=connection
            def __getattr__(self, name):
                if name=='setlimit':raise AttributeError(name)
                return getattr(self.connection,name)
            def __enter__(self):self.connection.__enter__();return self
            def __exit__(self,*args):return self.connection.__exit__(*args)
        def connect(*args,**kwargs):
            connection=original(*args,**kwargs)
            connection.create_function('audit_probe',0,lambda:calls.append(True) or start)
            return WithoutSetlimit(connection)
        with patch('sqlite3.connect',side_effect=connect):
            with self.assertRaises(ValueError):ClaudeStore(path,start,read_only=True,max_rows=50000)
        self.assertEqual(calls,[])

    def test_annotations_are_honest(self):
        for tool in mcp.TOOLS:
            self.assertFalse(tool['annotations']['openWorldHint'])
            self.assertEqual(tool['annotations']['readOnlyHint'], tool['name'] in ('cherry_meter_info', 'cherry_meter_doctor'))


class MCPProtocol(unittest.TestCase):
    def requests(self, tail):
        return [{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'test','version':'1'}}},
                {'jsonrpc':'2.0','method':'notifications/initialized'}, *tail]

    def run_stream(self, messages):
        output = io.BytesIO()
        code = mcp.serve(io.BytesIO(b''.join(json.dumps(item).encode()+b'\n' for item in messages)), output)
        return code, [json.loads(line) for line in output.getvalue().splitlines()]

    def test_initialize_list_call_and_notifications(self):
        code, rows = self.run_stream(self.requests([
            {'jsonrpc':'2.0','id':2,'method':'tools/list'},
            {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'cherry_meter_info','arguments':{}}},
            {'jsonrpc':'2.0','method':'unknown_notification'}]))
        self.assertEqual(code, 0)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['result']['protocolVersion'], '2025-06-18')
        self.assertEqual(len(rows[1]['result']['tools']), 6)
        self.assertFalse(rows[2]['result']['isError'])

    def test_errors_and_initialization_order(self):
        code, rows = self.run_stream([[], {'jsonrpc':'2.0','id':2,'method':'tools/list'}])
        self.assertEqual([row['error']['code'] for row in rows], [-32600,-32002])
        for raw in (b'{bad}\n', b'{"jsonrpc":"2.0","jsonrpc":"2.0"}\n', b'\xff\n', b'NaN\n'):
            output=io.BytesIO(); mcp.serve(io.BytesIO(raw), output)
            self.assertEqual(json.loads(output.getvalue())['error']['code'], -32700)
        output=io.BytesIO()
        self.assertEqual(mcp.serve(io.BytesIO(b'x'*(mcp.MAX_MESSAGE+1)), output), 2)

    def test_real_isolated_stdio_launcher(self):
        messages=self.requests([{'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'cherry_meter_info'}}])
        with tempfile.TemporaryDirectory(prefix="mcp unrelated '") as cwd:
            result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'native/mcp_server.py')],
                input=''.join(json.dumps(item)+'\n' for item in messages),text=True,capture_output=True,cwd=cwd,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        self.assertEqual(len([json.loads(line) for line in result.stdout.splitlines()]),2)

    def test_queued_request_can_cancel_before_writing(self):
        output=io.BytesIO(); server=mcp.Server(output)
        for item in self.requests([]):server.receive(item)
        server.receive({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'cherry_meter_info'}})
        server.receive({'jsonrpc':'2.0','method':'notifications/cancelled','params':{'requestId':3}})
        server.work.put(None); server.worker()
        rows=[json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(rows[-1]['error']['code'],-32800)

    def test_request_queue_is_bounded_and_duplicate_ids_rejected(self):
        output=io.BytesIO(); server=mcp.Server(output)
        for item in self.requests([]):server.receive(item)
        request={'jsonrpc':'2.0','method':'tools/call','params':{'name':'cherry_meter_info'}}
        for identity in range(10,19):server.receive({**request,'id':identity})
        server.receive({**request,'id':10})
        self.assertEqual(server.work.qsize(),8)
        self.assertEqual(len(server.pending),8)
        rows=[json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(rows[-2]['error']['code'],-32000)
        self.assertEqual(rows[-1]['error']['code'],-32600)

    def test_broken_output_closes_cleanly_without_executing_tools(self):
        class ClosedOutput:
            def write(self,value):raise BrokenPipeError()
        raw=b''.join(json.dumps(item).encode()+b'\n' for item in self.requests([
            {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'cherry_meter_info'}}]))
        with patch('spend_outcomes.mcp.execute',side_effect=AssertionError('tool must not execute after transport closed')):
            self.assertEqual(mcp.serve(io.BytesIO(raw),ClosedOutput()),1)


if __name__ == '__main__':unittest.main()
