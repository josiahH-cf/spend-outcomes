import concurrent.futures
from contextlib import closing
import datetime as dt
import http.client
import hashlib
import json
from pathlib import Path
import sqlite3
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

from spend_outcomes.claude import ClaudeStore, IDENTITY_SCHEMA_VERSION
from spend_outcomes.collector import make_server


START = '2026-11-01T00:00:00Z'


def ns(day, hour=0):
    return str(int(dt.datetime(2026, 11, day, hour, tzinfo=dt.timezone.utc).timestamp() * 1e9))


def attr(key, value):
    return {'key': key, 'value': {'stringValue': value}}


def payload(value=10, day=3, start=2, kind='input', session='s1', workspace=None, temporality=2):
    attrs = [attr('type', kind), attr('session.id', session), attr('model', 'claude-test'),
             attr('prompt', 'PRIVATE_SENTINEL'), attr('query_source', 'main')]
    if workspace:
        attrs.append(attr('workspace.path', str(workspace)))
    return {'resourceMetrics': [{'resource': {'attributes': [attr('service.name', 'claude-code'),
                attr('secret', 'PRIVATE_SENTINEL')]}, 'scopeMetrics': [{'metrics': [{
                'name': 'claude_code.token.usage', 'description': 'PRIVATE_SENTINEL',
                'sum': {'aggregationTemporality': temporality, 'isMonotonic': True,
                'dataPoints': [{'startTimeUnixNano': ns(start), 'timeUnixNano': ns(day),
                'asInt': str(value), 'attributes': attrs}]}}]}]}]}


class ClaudeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = self.root / 'project'
        self.workspace.mkdir()
        self.projects = {'demo': {'permitted': True, 'workspace': str(self.workspace)}}
        self.store = ClaudeStore(self.root / 'claude.sqlite', START)

    def tearDown(self):
        self.temp.cleanup()

    def view(self, selected=None, **kw):
        return self.store.observe(self.projects, selected, days=10, through='2026-11-10', **kw)

    def tokens(self, view=None):
        return (view or self.view())['projects'][0]['period']['tokens']

    def test_cumulative_replay_reorder_and_restart(self):
        self.store.ingest(payload(30, day=4))
        self.store.ingest(payload(10, day=3))
        self.store.ingest(payload(30, day=4))
        self.store.ingest(payload(7, day=6, start=5))
        self.assertEqual(self.tokens(), 37)
        reopened = ClaudeStore(self.store.path, START)
        self.assertEqual(self.tokens(reopened.observe(self.projects, days=10, through='2026-11-10')), 37)
        with self.assertRaises(ValueError):
            ClaudeStore(self.store.path, '2026-11-02T00:00:00Z')

    def test_disjoint_cache_classes_and_private_allowlist(self):
        for kind, value in [('input', 10), ('output', 4), ('cacheRead', 7), ('cacheCreation', 3)]:
            self.store.ingest(payload(value, kind=kind))
        self.assertEqual(self.tokens(), 24)
        with closing(sqlite3.connect(self.store.path)) as db:
            raw = '\n'.join(db.iterdump())
        self.assertNotIn('PRIVATE_SENTINEL', raw)
        self.assertNotIn('prompt', raw)
        self.assertEqual(self.view()['sources'][0]['entrypoint_qualification'], 'unverified')

    def test_explicit_binding_and_unassigned_device_report(self):
        self.store.ingest(payload())
        self.assertEqual(self.tokens(), 10)
        self.assertEqual(self.tokens(self.view('demo')), 0)
        self.assertEqual(self.tokens(self.view('demo', bindings={'sessions': {'s1': str(self.workspace)}})), 10)
        self.assertEqual(self.tokens(self.view('demo', bindings={'services': {'claude-code': str(self.workspace)}})), 10)
        self.assertEqual(self.view()['coverage']['unassigned_events'], 1)

    def test_observed_workspace_cannot_be_overridden(self):
        self.store.ingest(payload(workspace=self.root / 'other'))
        bound = self.view('demo', bindings={'sessions': {'s1': str(self.workspace)}})
        self.assertEqual(self.tokens(bound), 0)

    def test_tracking_start_excludes_history(self):
        self.store = ClaudeStore(self.root / 'late.sqlite', '2026-11-03T12:00:00Z')
        self.store.ingest(payload(10, day=3))
        self.store.ingest(payload(30, day=4))
        self.store.ingest(payload(35, day=5))
        self.assertEqual(self.tokens(), 5)
        self.assertIn('pretracking_cumulative_baseline_excluded', self.view()['coverage']['issues'])

    def test_delta_idempotency_overlap_and_tracking(self):
        self.store.ingest(payload(10, day=3, start=2, temporality=1))
        self.store.ingest(payload(10, day=3, start=2, temporality=1))
        self.store.ingest(payload(4, day=4, start=3, temporality=1))
        self.store.ingest(payload(20, day=5, start=2, temporality=1))
        self.assertEqual(self.tokens(), 14)
        self.assertIn('overlapping_delta_intervals', self.view()['coverage']['issues'])

    def test_integral_double_metrics_and_fraction_rejection(self):
        data = payload()
        point = data['resourceMetrics'][0]['scopeMetrics'][0]['metrics'][0]['sum']['dataPoints'][0]
        del point['asInt']
        point['asDouble'] = 10.0
        self.store.ingest(data)
        self.assertEqual(self.tokens(), 10)
        point['asDouble'] = 0.5
        with self.assertRaises(ValueError):
            self.store.ingest(data)

    def test_conflicting_duplicate_is_qualified(self):
        self.store.ingest(payload(10))
        self.store.ingest(payload(12))
        self.assertEqual(self.tokens(), 0)
        self.assertEqual(self.view()['conflicts']['total'], 1)
        self.store.ingest(payload(20, day=4))
        self.assertEqual(self.tokens(), 0)
        self.store.ingest(payload(25, day=5))
        self.assertEqual(self.tokens(), 5)

    def test_empty_store_is_unknown_not_zero(self):
        view = self.view()
        self.assertEqual(view['status'], 'unavailable')
        self.assertIsNone(self.tokens(view))
        self.assertIsNone(view['projects'][0]['period']['unpriced_tokens'])

    def test_report_window_crossing_cumulative_and_delta_excluded(self):
        self.store.ingest(payload(1000, day=10, start=2))
        view = self.store.observe(self.projects, days=7, through='2026-11-10')
        self.assertEqual(self.tokens(view), 0)
        self.assertIn('metric_interval_spans_report_window_start', view['coverage']['issues'])
        self.store.ingest(payload(500, day=3, start=2))
        view = self.store.observe(self.projects, days=7, through='2026-11-10')
        self.assertEqual(self.tokens(view), 0)
        self.store.ingest(payload(800, day=5, start=2))
        view = self.store.observe(self.projects, days=7, through='2026-11-10')
        self.assertEqual(self.tokens(view), 200)
        self.store.ingest(payload(300, day=5, start=2, session='delta', temporality=1))
        view = self.store.observe(self.projects, days=7, through='2026-11-10')
        self.assertEqual(self.tokens(view), 200)

    def test_rejected_payload_is_atomic(self):
        good = payload(10)
        bad = payload(-2)['resourceMetrics'][0]
        good['resourceMetrics'].append(bad)
        with self.assertRaises(ValueError):
            self.store.ingest(good)
        self.assertIsNone(self.tokens())
        for bad in ({'resourceLogs': []}, {'resourceMetrics': [], 'resourceLogs': []}):
            with self.assertRaises(ValueError):
                self.store.ingest(bad)

    def test_concurrent_writers_keep_all_sessions(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda n: self.store.ingest(payload(n + 1, session='s' + str(n))), range(24)))
        self.assertEqual(sum(x['inserted'] for x in results), 24)
        self.assertEqual(self.tokens(), sum(range(1, 25)))

    def test_official_query_sources_are_independent_series(self):
        for query in ('main', 'subagent', 'auxiliary'):
            data = payload(10)
            attributes = data['resourceMetrics'][0]['scopeMetrics'][0]['metrics'][0]['sum']['dataPoints'][0]['attributes']
            attributes[:] = [item for item in attributes if item['key'] != 'query_source']
            attributes.append(attr('query_source', query))
            self.store.ingest(data)
        self.assertEqual(self.tokens(), 30)
        rows = self.view()['projects'][0]['period']['provider_models']
        self.assertEqual({row['query_source'] for row in rows}, {'main', 'subagent', 'auxiliary'})

    def test_optional_dimensions_preserve_distinct_streams(self):
        dimensions = {'speed': 'fast', 'effort': 'high', 'agent.name': 'reviewer', 'skill.name': 'build',
            'plugin.name': 'plugin', 'marketplace.name': 'market', 'mcp_server.name': 'server', 'mcp_tool.name': 'tool'}
        self.store.ingest(payload(10))
        for key, value in dimensions.items():
            data = payload(10)
            data['resourceMetrics'][0]['scopeMetrics'][0]['metrics'][0]['sum']['dataPoints'][0]['attributes'].append(attr(key, value))
            self.store.ingest(data)
        self.assertEqual(self.tokens(), 90)
        rows = self.view()['projects'][0]['period']['provider_models']
        self.assertEqual(len(rows), 9)
        for key, value in dimensions.items():
            self.assertTrue(any(row['dimensions'].get(key) == value for row in rows))

    def test_resource_scope_and_version_identity_not_display_guessing(self):
        self.store.ingest(payload(10))
        data = payload(10)
        resource = data['resourceMetrics'][0]
        resource['resource']['attributes'][0] = attr('service.name', 'claude-code-desktop')
        resource['resource']['attributes'].extend([attr('service.version', '2.1.100'),
            attr('app.version', '2.1.101'), attr('app.entrypoint', 'desktop')])
        resource['scopeMetrics'][0]['scope'] = {'name': 'com.anthropic.claude_code', 'version': '1'}
        self.store.ingest(data)
        resource['scopeMetrics'][0]['scope']['version'] = '2'
        self.store.ingest(data)
        self.assertEqual(self.tokens(), 30)
        rows = self.view()['projects'][0]['period']['provider_models']
        desktop = [row for row in rows if row['service'] == 'claude-code-desktop']
        self.assertEqual({row['scope_version'] for row in desktop}, {'1', '2'})
        self.assertTrue(all(row['entrypoint'] == 'desktop' and row['service_version'] == '2.1.100'
                            and row['app_version'] == '2.1.101' for row in desktop))
        self.assertEqual(next(row for row in rows if row['service'] == 'claude-code')['entrypoint'], 'unknown')

    def test_private_identity_fingerprint_distinguishes_without_raw_storage(self):
        for user in ('PRIVATE_EMAIL_A@example.test', 'PRIVATE_EMAIL_B@example.test'):
            data = payload(10)
            data['resourceMetrics'][0]['scopeMetrics'][0]['metrics'][0]['sum']['dataPoints'][0]['attributes'].append(attr('user.email', user))
            self.store.ingest(data)
        self.assertEqual(self.tokens(), 20)
        with closing(sqlite3.connect(self.store.path)) as db:
            stored = '\n'.join(db.iterdump())
        self.assertNotIn('PRIVATE_EMAIL', stored)
        self.assertNotIn('PRIVATE_EMAIL', json.dumps(self.view()))
        self.assertIn('not anonymization', self.view()['sources'][0]['identity_privacy'])

    def test_unknown_dimensions_fail_closed_with_visible_issue(self):
        for location in ('point', 'resource', 'scope'):
            data = payload(10)
            resource = data['resourceMetrics'][0]
            attributes = resource['scopeMetrics'][0]['metrics'][0]['sum']['dataPoints'][0]['attributes']
            if location == 'resource':
                attributes = resource['resource']['attributes']
            if location == 'scope':
                resource['scopeMetrics'][0]['scope'] = {'attributes': []}
                attributes = resource['scopeMetrics'][0]['scope']['attributes']
            attributes.append(attr('new.series.dimension', 'PRIVATE_UNKNOWN_SENTINEL'))
            with self.assertRaises(ValueError):
                self.store.ingest(data)
        self.assertIsNone(self.tokens())
        self.assertIn('unsupported_metric_attribute', self.view()['coverage']['issues'])
        with closing(sqlite3.connect(self.store.path)) as db:
            stored = '\n'.join(db.iterdump())
        self.assertNotIn('PRIVATE_UNKNOWN_SENTINEL', stored)

    def test_legacy_store_replay_is_held_without_mutating_old_rows(self):
        self.store.ingest(payload(10))
        with closing(sqlite3.connect(self.store.path)) as db:
            dimensions = json.loads(db.execute('SELECT dimensions FROM points').fetchone()[0])
            dimensions.pop('series_family')
            dimensions.pop('scope.name')
            dimensions.pop('scope.version')
            old_json = json.dumps(dimensions, sort_keys=True, separators=(',', ':'))
            old_stream = hashlib.sha256(old_json.encode()).hexdigest()
            db.execute('UPDATE points SET stream=?, dimensions=?', (old_stream, old_json))
            db.execute("DELETE FROM metadata WHERE key='identity_schema_version'")
            db.commit()
            original = db.execute('SELECT * FROM points').fetchall()
        reopened = ClaudeStore(self.store.path, START)
        with self.assertRaisesRegex(ValueError, 'Explicitly authorize a new store'):
            reopened.ingest(payload(10))
        with closing(sqlite3.connect(self.store.path)) as db:
            self.assertEqual(db.execute('SELECT * FROM points').fetchall(), original)
            self.assertIsNone(db.execute("SELECT value FROM metadata WHERE key='identity_schema_version'").fetchone())
        view = reopened.observe(self.projects, days=10, through='2026-11-10')
        self.assertEqual(self.tokens(view), 10)
        self.assertIn('legacy_identity_schema_requires_explicit_cutover', view['coverage']['issues'])
        fresh = ClaudeStore(self.root / 'fresh.sqlite', START)
        fresh.ingest(payload(10))
        self.assertEqual(self.tokens(fresh.observe(self.projects, days=10, through='2026-11-10')), 10)
        with closing(sqlite3.connect(fresh.path)) as db:
            self.assertEqual(db.execute("SELECT value FROM metadata WHERE key='identity_schema_version'").fetchone(), (IDENTITY_SCHEMA_VERSION,))

    def test_temporality_change_same_interval_tombstones_both_orders(self):
        for first, second in ((1, 2), (2, 1)):
            store = ClaudeStore(self.root / ('same-' + str(first) + '.sqlite'), START)
            store.ingest(payload(10, temporality=first))
            store.ingest(payload(10, temporality=second))
            view = store.observe(self.projects, days=10, through='2026-11-10')
            self.assertEqual(self.tokens(view), 0)
            self.assertIn('conflicting_duplicate', view['coverage']['issues'])

    def test_temporality_change_shifted_epoch_quarantines_both_orders(self):
        for first, second in ((1, 2), (2, 1)):
            store = ClaudeStore(self.root / ('shift-' + str(first) + '.sqlite'), START)
            store.ingest(payload(10, day=3, start=2, temporality=first))
            store.ingest(payload(10, day=5, start=4, temporality=second))
            view = store.observe(self.projects, days=10, through='2026-11-10')
            self.assertEqual(self.tokens(view), 0)
            self.assertIn('temporality_changed_stream_quarantined', view['coverage']['issues'])

    def test_equivalent_unit_aliases_cannot_duplicate_usage(self):
        for unit in ('', 'token', 'tokens', '{token}'):
            data = payload(10)
            data['resourceMetrics'][0]['scopeMetrics'][0]['metrics'][0]['unit'] = unit
            self.store.ingest(data)
        self.assertEqual(self.tokens(), 10)
        with closing(sqlite3.connect(self.store.path)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM points').fetchone()[0], 1)

    def test_device_project_views_share_one_snapshot_during_ingestion(self):
        self.store.ingest(payload(10, workspace=self.workspace))
        derive = self.store._observe_snapshot
        calls = []

        def interleave(*args, **kwargs):
            result = derive(*args, **kwargs)
            calls.append(result)
            if len(calls) == 1:
                self.store.ingest(payload(20, day=4, workspace=self.workspace))
            return result

        with patch.object(self.store, '_observe_snapshot', side_effect=interleave):
            views = self.store.observe_views(self.projects, days=10, through='2026-11-10')
        self.assertEqual(self.tokens(views['device']), 10)
        self.assertEqual(self.tokens(views['projects']['demo']), 10)
        self.assertEqual(views['device']['generation'], views['projects']['demo']['generation'])
        self.assertEqual(self.tokens(), 20)

    def test_loopback_receiver_rejects_logs_and_accepts_metrics(self):
        with self.assertRaises(ValueError):
            make_server(self.store, '0.0.0.0')
        server = make_server(self.store, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            def post(path, body, headers=None):
                connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
                connection.request('POST', path, json.dumps(body), headers or {'Content-Type': 'application/json'})
                response = connection.getresponse()
                status = response.status
                response.read()
                connection.close()
                return status
            self.assertEqual(post('/v1/logs', {'resourceLogs': []}), 404)
            self.assertEqual(post('/v1/metrics', {'resourceLogs': []}), 400)
            self.assertEqual(post('/v1/metrics', payload(), {'Content-Type': 'application/json', 'Origin': 'http://example.test'}), 415)
            self.assertEqual(post('/v1/metrics', payload()), 200)
            self.assertEqual(self.tokens(), 10)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)

    def test_rejected_bounded_posts_drain_delayed_body_before_close(self):
        server = make_server(self.store, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        cases = [('/v1/metrics', 'Origin: http://example.test\r\n', 415),
                 ('/v1/logs', '', 404),
                 ('/v1/metrics', 'Content-Encoding: gzip\r\n', 415)]
        try:
            with patch.object(self.store, 'ingest', wraps=self.store.ingest) as ingest:
                for path, extra, expected in cases:
                    body = b'REJECTED_CONTENT_NEVER_PARSED' * 128
                    with socket.create_connection(('127.0.0.1', server.server_port), timeout=3) as connection:
                        headers = ('POST ' + path + ' HTTP/1.1\r\nHost: localhost\r\n'
                            'Content-Type: application/json\r\nContent-Length: ' + str(len(body)) + '\r\n' + extra + '\r\n')
                        connection.sendall(headers.encode() + body[:17])
                        # A rejected body still in flight must not be cut off by
                        # an early close/reset. The old handler replied here.
                        connection.settimeout(0.05)
                        with self.assertRaises(socket.timeout):
                            connection.recv(1)
                        connection.settimeout(3)
                        connection.sendall(body[17:])
                        response = http.client.HTTPResponse(connection)
                        response.begin()
                        self.assertEqual(response.status, expected)
                        response.read()
                        response.close()
                ingest.assert_not_called()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)


if __name__ == '__main__':
    unittest.main()
