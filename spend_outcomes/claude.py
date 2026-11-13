"""Prospective, metadata-only Claude OTLP/HTTP JSON observations.

Only the token sum and a fixed attribution allowlist reach SQLite. No raw
request, resource, metric, log, prompt, or response payload is retained.
"""
import datetime as dt
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
import stat

from .codex import _inside, _project_roots


CLASSES = {'input': 'input_tokens', 'output': 'output_tokens',
           'cacheRead': 'cached_input_tokens', 'cacheCreation': 'cache_write_tokens'}
ATTRIBUTES = {'model', 'type', 'session.id', 'service.name', 'service.instance.id',
              'workspace', 'workspace.path', 'request.type', 'query_source', 'speed', 'effort',
              'agent.name', 'skill.name', 'plugin.name', 'marketplace.name',
              'mcp_server.name', 'mcp_tool.name', 'app.entrypoint', 'service.version',
              'app.version', 'ccr.session.id', 'terminal.type', 'os.type', 'os.version',
              'host.arch', 'wsl.version', 'telemetry.sdk.name', 'telemetry.sdk.version',
              'telemetry.sdk.language'}
PRIVATE_IDENTITIES = {'organization.id', 'user.account_uuid', 'user.account_id',
                      'user.id', 'user.email', 'vcs.repository.url.full', 'vcs.owner.name',
                      'vcs.repository.name', 'vcs.provider.name'}
# Content is never a valid metric-series identity, including when a sender tries
# to supply it as an attribute. Do not hash it or persist its key or value.
CONTENT_ATTRIBUTES = {'prompt', 'body', 'response', 'instructions', 'tool.text',
                      'prompt.body', 'response.body', 'secret'}
IDENTITY_SCHEMA_VERSION = 'claude-otlp-series-v2'
LEGACY_CUTOVER_MESSAGE = ('Claude store uses legacy or unsupported accounting identities; ingest is held. '
    'Keep this store unchanged for historical reports. Explicitly authorize a new store and '
    'a prospective tracking-start cutover before collecting again; do not replay into the legacy store.')


class UnsupportedMetricAttribute(ValueError):
    pass


def _stamp(value):
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('tracking start requires timezone')
    return parsed.astimezone(dt.timezone.utc)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _attrs(items):
    result = {}
    private = {}
    if not isinstance(items, list) or len(items) > 128:
        raise ValueError('invalid metric attributes')
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('invalid metric attribute')
        key = item.get('key')
        if key in CONTENT_ATTRIBUTES:
            continue
        if key not in ATTRIBUTES and key not in PRIVATE_IDENTITIES:
            raise UnsupportedMetricAttribute('unsupported metric attribute')
        value = item.get('value', {}).get('stringValue')
        if (not isinstance(value, str) or not value or len(value) > 1024
                or any(ord(c) < 32 for c in value) or key in result or key in private):
            raise ValueError('invalid attribution attribute')
        (private if key in PRIVATE_IDENTITIES else result)[key] = value
    if private:
        result['private_identity_fingerprint'] = hashlib.sha256(_json(private).encode()).hexdigest()
    if 'request.type' in result:
        legacy = result.pop('request.type')
        if 'query_source' in result and result['query_source'] != legacy:
            raise ValueError('conflicting legacy query source')
        result['query_source'] = legacy
    if 'query_source' in result and result['query_source'] not in ('main', 'subagent', 'auxiliary'):
        raise ValueError('unsupported query_source')
    return result


def _integer(value):
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        value = int(value)
    if type(value) is not int or not 0 <= value <= 2**63 - 1:
        raise ValueError('invalid nonnegative integer')
    return value


def _counter(point):
    if ('asInt' in point) == ('asDouble' in point):
        raise ValueError('one numeric token value required')
    if 'asInt' in point:
        return _integer(point['asInt'])
    value = point['asDouble']
    if (type(value) not in (int, float) or not math.isfinite(value)
            or value < 0 or value > 2**53 or int(value) != value):
        raise ValueError('token count must be an exact nonnegative integer')
    return int(value)


class ClaudeStore:
    def __init__(self, path, tracking_start, *, read_only=False, max_rows=None, path_guard=None, cancel_check=None):
        self.path = Path(path)
        self.start = _stamp(tracking_start)
        self.start_ns = int(self.start.timestamp() * 1_000_000_000)
        self.read_only = read_only
        self.max_rows = max_rows
        self.path_guard = path_guard
        self.cancel_check = cancel_check
        if read_only:
            # SQL read-only, not a no-filesystem-write guarantee: SQLite may
            # create/update -wal/-shm sidecars. MCP includes them in approval.
            if not stat.S_ISREG(self.path.stat().st_mode):
                raise ValueError('Claude store must be a regular existing file')
            with self._connect() as db:
                self._validate_read_schema(db)
                old = db.execute("SELECT value FROM metadata WHERE key='tracking_start'").fetchone()
                if old != (self.start.isoformat(),):
                    raise ValueError('existing Claude store tracking start differs')
            return
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self._connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS points(
                  stream TEXT NOT NULL, start INTEGER NOT NULL, stamp INTEGER NOT NULL,
                  temporality INTEGER NOT NULL, value INTEGER NOT NULL, dimensions TEXT NOT NULL,
                  PRIMARY KEY(stream,start,stamp));
                CREATE TABLE IF NOT EXISTS issues(code TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS conflicted_points(
                  stream TEXT NOT NULL, start INTEGER NOT NULL, stamp INTEGER NOT NULL,
                  PRIMARY KEY(stream,start,stamp));
            ''')
            db.execute('BEGIN IMMEDIATE')
            old = db.execute("SELECT value FROM metadata WHERE key='tracking_start'").fetchone()
            normalized = self.start.isoformat()
            if old and old[0] != normalized:
                raise ValueError('existing Claude store tracking start differs')
            db.execute("INSERT OR IGNORE INTO metadata VALUES('tracking_start',?)", (normalized,))
            identity_version = db.execute("SELECT value FROM metadata WHERE key='identity_schema_version'").fetchone()
            if not identity_version and not db.execute('SELECT 1 FROM points LIMIT 1').fetchone():
                # Only a fresh, empty store may adopt new accounting identities.
                # Never retag a nonempty historical store and thereby allow replay.
                db.execute("INSERT INTO metadata VALUES('identity_schema_version',?)", (IDENTITY_SCHEMA_VERSION,))
        self.path.chmod(0o600)

    @contextmanager
    def _connect(self):
        if self.read_only:
            db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True, timeout=2)
        else:
            db = sqlite3.connect(self.path, timeout=10)
        try:
            if self.read_only:
                db.execute('PRAGMA query_only=ON')
                if hasattr(db, 'setlimit'):
                    db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 256*1024)
                deadline = time.monotonic() + 10
                db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
            else:
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('PRAGMA busy_timeout=10000')
            with db:
                yield db
        finally:
            db.close()

    def ingest(self, payload):
        """Validate an entire metrics request, then transact sanitized points only."""
        with self._connect() as db:
            self._require_current_identity(db)
        try:
            return self._ingest(payload)
        except UnsupportedMetricAttribute:
            with self._connect() as db:
                db.execute("INSERT OR IGNORE INTO issues VALUES('unsupported_metric_attribute')")
            raise

    def require_ingest_ready(self):
        """Fail before listening when an explicit accounting cutover is required."""
        with self._connect() as db:
            self._require_current_identity(db)

    @staticmethod
    def _require_current_identity(db):
        version = db.execute("SELECT value FROM metadata WHERE key='identity_schema_version'").fetchone()
        if version != (IDENTITY_SCHEMA_VERSION,):
            raise ValueError(LEGACY_CUTOVER_MESSAGE)

    def _ingest(self, payload):
        if not isinstance(payload, dict) or set(payload) != {'resourceMetrics'}:
            raise ValueError('only OTLP resourceMetrics is supported')
        resources = payload['resourceMetrics']
        if not isinstance(resources, list) or len(resources) > 128:
            raise ValueError('invalid resourceMetrics')
        points = []
        ignored = 0
        for resource in resources:
            attrs = _attrs(resource.get('resource', {}).get('attributes', []))
            scopes = resource.get('scopeMetrics', [])
            if not isinstance(scopes, list) or len(scopes) > 128:
                raise ValueError('invalid scopeMetrics')
            for scope in scopes:
                scope_meta = scope.get('scope', {})
                scope_identity = _attrs(scope_meta.get('attributes', []))
                for scope_key in ('name', 'version'):
                    value = scope_meta.get(scope_key, '')
                    if not isinstance(value, str) or len(value) > 1024 or any(ord(c) < 32 for c in value):
                        raise ValueError('invalid scope identity')
                    scope_identity[scope_key] = value
                metrics = scope.get('metrics', [])
                if not isinstance(metrics, list) or len(metrics) > 256:
                    raise ValueError('invalid metrics')
                for metric in metrics:
                    if metric.get('name') != 'claude_code.token.usage':
                        ignored += 1
                        continue
                    unit = metric.get('unit', '')
                    if unit not in ('', 'token', 'tokens', '{token}'):
                        raise ValueError('unsupported token metric unit')
                    total = metric.get('sum', {})
                    temporality = total.get('aggregationTemporality')
                    temporality = {'AGGREGATION_TEMPORALITY_DELTA': 1,
                                   'AGGREGATION_TEMPORALITY_CUMULATIVE': 2}.get(temporality, temporality)
                    if type(temporality) is not int or temporality not in (1, 2) or total.get('isMonotonic') is not True:
                        raise ValueError('token metric requires monotonic delta or cumulative sum')
                    datapoints = total.get('dataPoints', [])
                    if not isinstance(datapoints, list):
                        raise ValueError('invalid token points')
                    for point in datapoints:
                        if len(points) >= 10000:
                            raise ValueError('too many token points')
                        point_attrs = _attrs(point.get('attributes', []))
                        dims = {**attrs, **point_attrs}
                        if dims.get('type') not in CLASSES or not dims.get('session.id'):
                            raise ValueError('token point requires supported type and session.id')
                        if not dims.get('model') or not dims.get('service.name'):
                            raise ValueError('token point requires model and service.name')
                        if dims['service.name'] not in ('claude-code', 'claude-code-desktop'):
                            raise ValueError('unsupported Claude service.name')
                        start = _integer(point.get('startTimeUnixNano'))
                        stamp = _integer(point.get('timeUnixNano'))
                        value = _counter(point)
                        if not 0 < start <= stamp <= time.time_ns() + 300_000_000_000:
                            raise ValueError('invalid token interval')
                        if point.get('flags', 0) != 0:
                            raise ValueError('unsupported token data flags')
                        if stamp < self.start_ns:
                            continue
                        identity = {'resource': attrs, 'scope': scope_identity, 'point': point_attrs,
                                    'metric': {'name': metric['name'], 'unit': 'token', 'monotonic': True}}
                        stream = hashlib.sha256(_json(identity).encode()).hexdigest()
                        family = {**identity, 'resource': {k: v for k, v in attrs.items() if k != 'type'},
                                  'point': {k: v for k, v in point_attrs.items() if k != 'type'}}
                        dims['series_family'] = hashlib.sha256(_json(family).encode()).hexdigest()
                        dims['scope.name'] = scope_identity['name'] or 'unknown'
                        dims['scope.version'] = scope_identity['version'] or 'unknown'
                        dimensions = _json(dims)
                        points.append((stream, start, stamp, temporality, value, dimensions))
        inserted = duplicates = 0
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self._require_current_identity(db)
            for point in points:
                old = db.execute('SELECT temporality,value FROM points WHERE stream=? AND start=? AND stamp=?', point[:3]).fetchone()
                if old:
                    duplicates += 1
                    if old != point[3:5]:
                        db.execute("INSERT OR IGNORE INTO issues VALUES('conflicting_duplicate')")
                        db.execute('INSERT OR IGNORE INTO conflicted_points VALUES(?,?,?)', point[:3])
                    continue
                db.execute('INSERT INTO points VALUES(?,?,?,?,?,?)', point)
                inserted += 1
            if points:
                db.execute("INSERT OR REPLACE INTO metadata VALUES('last_received',?)", (dt.datetime.now(dt.timezone.utc).isoformat(),))
        return {'inserted': inserted, 'duplicates': duplicates, 'ignored_metrics': ignored}

    def observe(self, projects, selected=None, days=7, through=None, bindings=None):
        """Read one project or all device activity; explicit bindings fill missing workspace.

        bindings is {'sessions': {session_id: workspace}, 'services': {service_name: workspace}}.
        Session bindings take precedence. Observed workspace evidence is never overridden.
        """
        return self._observe_snapshot(self._snapshot(), projects, selected, days, through, bindings)

    @staticmethod
    def _validate_read_schema(db):
        # Check before ANY user-table SELECT, including constructor metadata.
        # Python 3.10 lacks Connection.setlimit; do not rely on that extra guard.
        expected = {'points': ['stream','start','stamp','temporality','value','dimensions'],
                    'issues': ['code'], 'metadata': ['key','value'],
                    'conflicted_points': ['stream','start','stamp']}
        for table, columns in expected.items():
            definition = db.execute('SELECT type,sql FROM sqlite_master WHERE name=?', (table,)).fetchone()
            if not definition or definition[0] != 'table' or 'VIRTUAL' in definition[1].upper():
                raise ValueError('expected ordinary Claude store tables')
            fields = db.execute('PRAGMA table_xinfo(' + table + ')').fetchall()
            if [field[1] for field in fields] != columns or any(field[6] for field in fields):
                raise ValueError('unexpected Claude table columns')
            condition = ' OR '.join('length(CAST(' + column + ' AS BLOB)) > 32768' for column in columns)
            if db.execute('SELECT 1 FROM ' + table + ' WHERE ' + condition + ' LIMIT 1').fetchone():
                raise ValueError('Claude store cell exceeds bounded snapshot limit')

    def _snapshot(self):
        """One SQLite read transaction, shared by every derived report view."""
        with self._connect() as db:
            db.execute('BEGIN')
            if self.max_rows is not None:
                self._validate_read_schema(db)
            snapshot_bytes = 0
            def bounded(sql):
                nonlocal snapshot_bytes
                cursor = db.execute(sql)
                rows = cursor.fetchall() if self.max_rows is None else cursor.fetchmany(self.max_rows + 1)
                if self.max_rows is not None and len(rows) > self.max_rows:
                    raise ValueError('Claude store exceeds bounded snapshot limit')
                if self.max_rows is not None:
                    snapshot_bytes += sum(len(value.encode('utf-8')) if isinstance(value, str) else len(value) if isinstance(value, bytes) else 8 for row in rows for value in row)
                    if snapshot_bytes > 16*1024*1024:
                        raise ValueError('Claude snapshot exceeds bounded byte limit')
                return rows
            rows = bounded('SELECT stream,start,stamp,temporality,value,dimensions FROM points ORDER BY stream,start,stamp')
            issues = {row[0] for row in bounded('SELECT code FROM issues')}
            metadata = dict(bounded('SELECT key,value FROM metadata'))
            conflicted = set(bounded('SELECT stream,start,stamp FROM conflicted_points'))
        return rows, issues, metadata, conflicted, dt.datetime.now(dt.timezone.utc)

    def observe_views(self, projects, days=7, through=None, bindings=None):
        """Derive device and permitted project views from exactly one snapshot."""
        snapshot = self._snapshot()
        return {'device': self._observe_snapshot(snapshot, projects, None, days, through, bindings),
                'projects': {key: self._observe_snapshot(snapshot, projects, key, days, through, bindings)
                             for key, project in projects.items()
                             if project.get('permitted') is True and _project_roots(project)}}

    def _observe_snapshot(self, snapshot, projects, selected, days, through, bindings):
        if type(days) is not int or days <= 0:
            raise ValueError('positive bounded day window required')
        rows, snapshot_issues, metadata, conflicted, observed_at = snapshot
        issues = set(snapshot_issues)
        if metadata.get('identity_schema_version') != IDENTITY_SCHEMA_VERSION:
            issues.add('legacy_identity_schema_requires_explicit_cutover')
        end = dt.date.fromisoformat(through) if through else observed_at.date()
        start = end - dt.timedelta(days=days - 1)
        window_start_ns = int(dt.datetime.combine(start, dt.time.min, dt.timezone.utc).timestamp() * 1_000_000_000)
        mappings = {key: _project_roots(value) for key, value in projects.items() if value.get('permitted') is True}
        if selected is not None and (selected not in mappings or not mappings[selected]):
            raise ValueError('selected project requires explicit workspace')
        bindings = bindings or {}
        # Exported samples cannot prove uninterrupted application or collector coverage.
        issues.add('entrypoint_and_export_delivery_not_independently_qualified')
        if self.start.date() > start:
            issues.add('tracking_started_after_window_start')
        if not rows:
            issues.add('no_claude_token_metrics_received')
        if metadata.get('last_received') and (observed_at - _stamp(metadata['last_received'])).total_seconds() > 300:
            issues.add('no_recent_metric_delivery')
        events = []
        previous = {}
        delta_intervals = {}
        temporalities = {}
        for stream, epoch, stamp, temporality, value, dimensions in rows:
            if self.cancel_check:self.cancel_check()
            temporalities.setdefault(stream, set()).add(temporality)
        mixed_streams = {stream for stream, kinds in temporalities.items() if len(kinds) > 1}
        if mixed_streams:
            issues.add('temporality_changed_stream_quarantined')
        for stream, epoch, stamp, temporality, value, dimensions in rows:
            if self.cancel_check:self.cancel_check()
            # A provider changing representation does not create new usage. Until
            # an explicit epoch/cutover reconciler exists, hold the entire stream
            # rather than choosing whichever representation arrived first.
            if stream in mixed_streams:
                continue
            dims = json.loads(dimensions)
            key = (stream, epoch)
            prior = previous.get(key)
            if (stream, epoch, stamp) in conflicted:
                # Never select an arbitrary conflicting value. A later cumulative
                # point must establish a fresh baseline before differences resume.
                previous[key] = (stamp, None, temporality)
                continue
            if prior and prior[2] != temporality:
                issues.add('temporality_changed_within_stream')
                continue
            amount = value
            excluded = False
            interval_start = prior[0] if temporality == 2 and prior else epoch
            if temporality == 2:
                if prior:
                    if prior[1] is None:
                        issues.add('cumulative_baseline_after_conflict')
                        excluded = True
                    elif value < prior[1]:
                        issues.add('counter_reset_without_new_start')
                        excluded = True
                    else:
                        amount = value - prior[1]
                elif epoch < self.start_ns:
                    excluded = True
                    issues.add('pretracking_cumulative_baseline_excluded')
            elif temporality == 1:
                intervals = delta_intervals.setdefault(stream, [])
                if any(epoch < right and stamp > left for left, right in intervals):
                    excluded = True
                    issues.add('overlapping_delta_intervals')
                else:
                    intervals.append((epoch, stamp))
            previous[key] = (stamp, value, temporality)
            if interval_start < window_start_ns <= stamp:
                issues.add('metric_interval_spans_report_window_start')
                excluded = True
            if excluded:
                continue
            if stamp < self.start_ns:
                continue
            if temporality == 1 and epoch < self.start_ns:
                issues.add('delta_spans_tracking_start')
                continue
            # Cumulative intervals crossing the tracking boundary are not wholly prospective.
            if temporality == 2 and prior and prior[0] < self.start_ns:
                issues.add('cumulative_interval_spans_tracking_start')
                continue
            day = dt.datetime.fromtimestamp(stamp / 1e9, dt.timezone.utc).date().isoformat()
            if start.isoformat() <= day <= end.isoformat():
                events.append((dims, day, amount))
        models = {}; daily = {}; totals = {key: 0 for key in CLASSES.values()}
        unassigned = ambiguous = out_of_scope = 0
        for dims, day, amount in events:
            if self.cancel_check:self.cancel_check()
            workspace = dims.get('workspace.path') or dims.get('workspace')
            if not workspace:
                workspace = bindings.get('sessions', {}).get(dims['session.id']) or bindings.get('services', {}).get(dims['service.name'])
            if workspace and self.path_guard:
                try:self.path_guard(workspace)
                except ValueError:
                    workspace=None
                    issues.add('unsupported_workspace_path')
            matches = [key for key, roots in mappings.items() if workspace and any(_inside(workspace, root) for root in roots)]
            if not matches:
                unassigned += 1
            elif len(matches) > 1:
                ambiguous += 1
            if selected is not None and matches != [selected]:
                out_of_scope += 1
                continue
            identity = dims.get('series_family')
            if identity is None:
                issues.add('legacy_series_identity_unqualified')
                identity = hashlib.sha256(_json({key: value for key, value in dims.items() if key != 'type'}).encode()).hexdigest()
            model = models.setdefault(identity, {'provider': 'anthropic', 'client': 'claude-code',
                'service': dims['service.name'], 'model': dims['model'],
                'query_source': dims.get('query_source', 'unknown'),
                'request_type': dims.get('query_source', 'unknown'),
                'entrypoint': dims.get('app.entrypoint', 'unknown'),
                'service_version': dims.get('service.version', 'unknown'),
                'app_version': dims.get('app.version', 'unknown'),
                'scope_name': dims.get('scope.name', 'unknown'),
                'scope_version': dims.get('scope.version', 'unknown'),
                'series_identity': identity,
                'dimensions': {key: dims[key] for key in ('query_source', 'speed', 'effort', 'agent.name',
                    'skill.name', 'plugin.name', 'marketplace.name', 'mcp_server.name', 'mcp_tool.name') if key in dims},
                'account': 'unknown', 'tokens': 0, **{key: 0 for key in CLASSES.values()}})
            model['tokens'] += amount
            model[CLASSES[dims['type']]] += amount
            totals[CLASSES[dims['type']]] += amount
            row = daily.setdefault(day, {'date': day, 'tokens': 0})
            row['tokens'] += amount
        if unassigned:
            issues.add('workspace_unassigned')
        if ambiguous:
            issues.add('workspace_ambiguous')
        count = sum(row['tokens'] for row in models.values()) if rows else None
        status = 'partial' if rows else 'unavailable'
        period = {'from_day': start.isoformat(), 'to_day': end.isoformat(), 'days': days,
            'tokens': count, 'unpriced_tokens': count, 'api_equivalent_cost_usd': None,
            'basis': 'prospective Claude metric intervals; disjoint input, output, cache read and cache creation',
            'coverage_status': status, 'daily': sorted(daily.values(), key=lambda row: row['date']),
            'provider_models': list(models.values()), 'token_classes': totals, 'events': len(events)}
        source = {'kind': 'claude', 'status': status, 'tracking_start': metadata['tracking_start'],
                  'last_received': metadata.get('last_received'), 'transport': 'otlp-http-json',
                  'entrypoint_qualification': 'unverified',
                  'identity_schema_version': metadata.get('identity_schema_version'),
                  'identity_privacy': 'private identity fingerprints are not anonymization; keep store and reports private'}
        return {'contract': 'spend-outcomes-observation-v1', 'producer': 'cherry-meter-claude', 'status': status,
            'generation': {'finished_at': observed_at.isoformat()},
            'projects': [{'project_id': selected or 'device', 'project_code': selected or 'device',
                          'attribution': 'workspace-evidence' if selected else 'device-local', 'period': period}],
            'sources': [source], 'coverage': {'status': status, 'issues': sorted(issues),
                'unassigned_events': unassigned, 'ambiguous_events': ambiguous, 'out_of_scope_events': out_of_scope},
            'conflicts': {'total': int('conflicting_duplicate' in issues), 'items':
                [{'source': 'claude', 'detail': 'conflicting_duplicate'}] if 'conflicting_duplicate' in issues else []},
            'units': {'tokens': 'input plus output plus cache read plus cache creation; disjoint classes'},
            'collection': {'triggered': False, 'roots': 'explicit-only'}, 'pricing': {'status': 'unavailable'},
            'accounting': {'coverage_gaps': sorted(issues)}}
