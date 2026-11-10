"""Explicit device-local collection and reporting, independent of report sessions."""
import argparse
import datetime as dt
import html
import http.client
import json
import os
from pathlib import Path
import platform
import re
import sqlite3
import subprocess
import sys

from .core import digest, encoded, immutable, inspect, read_export
from .storage import atomic_bytes, file_lock

SCHEMA = 'cherry-meter-device-v1'


def stamp(value):
    result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('tracking start must include its UTC offset')
    return result.astimezone(dt.timezone.utc).isoformat()


def add_parsers(sub):
    init = sub.add_parser('device-init', help='Create explicit native device bindings; read no sources')
    init.add_argument('--config', type=Path, required=True)
    init.add_argument('--state', type=Path, required=True)
    init.add_argument('--project', required=True)
    init.add_argument('--workspace', type=Path, required=True)
    init.add_argument('--additional-workspace', type=Path, action='append')
    init.add_argument('--codex-root', type=Path, action='append')
    init.add_argument('--claude', action='store_true', help='Permit prospective Claude metrics in this device store')
    init.add_argument('--name')
    init.add_argument('--device-name', default='This device')
    init.add_argument('--tracking-start', help='Explicit UTC start; defaults to now. No historical Claude import.')
    init.add_argument('--target-tokens', type=int)
    init.add_argument('--outcome')
    init.add_argument('--success-criterion')
    init.add_argument('--checkpoint', dest='checkpoints', action='append')
    report = sub.add_parser('device-inspect', help='Snapshot all configured sources in one private device report')
    report.add_argument('--config', type=Path, required=True)
    report.add_argument('--days', type=int, choices=[7, 30, 90], default=7)
    report.add_argument('--through')
    report.add_argument('--html', action='store_true')
    doctor = sub.add_parser('doctor', help='Inspect explicit binding readiness without reading usage')
    doctor.add_argument('--config', type=Path, required=True)
    collect = sub.add_parser('collect', help='Run the foreground metrics-only loopback receiver')
    collect.add_argument('--config', type=Path, required=True)
    collect.add_argument('--port', type=int, default=4318)
    health = sub.add_parser('collector-health', help='Check only the local receiver and retained lifecycle evidence')
    health.add_argument('--config', type=Path, required=True)
    health.add_argument('--port', type=int, default=4318)
    plan = sub.add_parser('lifecycle-plan', help='Write reviewable user-level scheduler files; never register or start them')
    plan.add_argument('--config', type=Path, required=True)
    plan.add_argument('--platform', choices=['windows', 'macos'], required=True)
    plan.add_argument('--runtime-root', required=True)
    plan.add_argument('--python', dest='python_path', required=True)
    plan.add_argument('--output', type=Path, required=True)
    plan.add_argument('--port', type=int, default=4318)
    plan.add_argument('--identity', default='cherry-meter')
    plan.add_argument('--user-id')
    plan.add_argument('--uid', type=int)
    plan.add_argument('--user-home')
    demo = sub.add_parser('device-demo', help='Create clearly synthetic tandem data; never read real usage')
    demo.add_argument('--root', type=Path, required=True)
    export = sub.add_parser('export-plan', help='Show a metrics-only configuration proposal; never read or change client settings')
    export.add_argument('--port', type=int, default=4318)
    export.add_argument('--entrypoint', choices=['cli', 'vscode', 'desktop'], default='cli')


def load_config(path):
    config = read_export(path)
    if config.get('schema') != SCHEMA:
        raise ValueError('expected device config; existing v1 configs remain usable with inspect')
    if not isinstance(config.get('projects'), dict) or not config['projects']:
        raise ValueError('at least one explicit project binding is required')
    for key, project in config['projects'].items():
        if project.get('permitted') is not True or not project.get('workspace'):
            raise ValueError('project requires explicit permitted workspace binding: ' + key)
    sources = config.get('sources')
    if not isinstance(sources, list) or not sources:
        raise ValueError('at least one explicitly permitted source is required')
    kinds = []
    for source in sources:
        if source.get('permitted') is not True or source.get('kind') not in ('codex', 'claude-otel'):
            raise ValueError('source kind or explicit permission is invalid')
        if source['kind'] in kinds:
            raise ValueError('combine roots in one source binding to prevent overlapping source totals')
        kinds.append(source['kind'])
        stamp(source['tracking_start'])
        if source['kind'] == 'codex' and not source.get('roots'):
            raise ValueError('Codex requires at least one explicit root')
        if source['kind'] == 'claude-otel' and not source.get('store'):
            raise ValueError('Claude requires its explicit private store')
    if not Path(config['state']).is_absolute():
        raise ValueError('device state must be an absolute private path')
    return config


def initialize(args, invocation, *, write=True):
    if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', args.project):
        raise ValueError('invalid local project key')
    if not args.codex_root and not args.claude:
        raise ValueError('choose --codex-root, --claude, or both')
    workspace = args.workspace.expanduser().absolute()
    extra = [path.expanduser().absolute() for path in args.additional_workspace or []]
    if not workspace.is_dir() or any(not path.is_dir() for path in extra):
        raise ValueError('explicit project workspaces must already exist')
    if args.target_tokens is not None and args.target_tokens <= 0:
        raise ValueError('target tokens must be positive')
    if not args.outcome and (args.success_criterion or args.checkpoints):
        raise ValueError('success criterion and checkpoints require an outcome')
    now = stamp(args.tracking_start or dt.datetime.now(dt.timezone.utc).isoformat())
    state = args.state.expanduser().absolute()
    config = {'schema': SCHEMA, 'device': {'label': args.device_name, 'execution_host': platform.system(),
              'architecture': platform.machine(), 'scope': 'this execution device only; remote hosts excluded'},
              'tracking_start': now, 'state': str(state), 'sources': [],
              'projects': {args.project: {'permitted': True, 'workspace': str(workspace),
                          'additional_workspaces': list(map(str, extra)), 'label': args.name or args.project}},
              'targets': {}}
    if args.codex_root:
        config['sources'].append({'id': 'codex-local', 'kind': 'codex', 'permitted': True,
            'roots': [str(path.expanduser().absolute()) for path in args.codex_root], 'tracking_start': now})
    if args.claude:
        config['sources'].append({'id': 'claude-local', 'kind': 'claude-otel', 'permitted': True,
            'store': str(state / 'claude-metrics.sqlite3'), 'tracking_start': now,
            'bindings': {'sessions': {}, 'services': {}}})
    if args.target_tokens:
        config['targets'][args.project] = [{'kind': 'numeric', 'unit': 'tokens', 'meaning': 'observed',
                                           'amount': args.target_tokens, 'window': 'rolling-7-days'}]
    if args.outcome:
        if not args.outcome.strip() or not args.success_criterion or not args.success_criterion.strip():
            raise ValueError('outcome requires a nonblank success criterion')
        checkpoints = []
        seen = set()
        for value in args.checkpoints or []:
            key, separator, text = value.partition('=')
            if not separator or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', key) or key in seen or not text.strip():
                raise ValueError('checkpoint requires a unique ID=description')
            seen.add(key)
            checkpoints.append({'id': key, 'text': text, 'status': 'pending', 'provenance': 'operator-reported'})
        config['outcome'] = {'statement': args.outcome, 'success_criterion': args.success_criterion,
                             'checkpoints': checkpoints, 'history': [], 'provenance': 'operator-reported'}
    path = args.config.expanduser().absolute()
    if not write:
        return config
    # No parent creation, source reads, store creation, or existing-config mutation.
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as handle:
        handle.write(encoded(config)); handle.flush(); os.fsync(handle.fileno())
    return {'config': str(path), 'tracking_start': now, 'sources_read': False,
            'inspect_argv': [*invocation, 'device-inspect', '--config', str(path), '--html'],
            'collector_argv': [*invocation, 'collect', '--config', str(path)] if args.claude else None,
            'next_steps': ['Review explicit source bindings before inspecting.',
                          'Claude metrics must be configured separately for each supported launch path.',
                          'No client, OS startup, plugin or telemetry settings were changed.'], 'execution_effects': []}


def unavailable(source, reason):
    return {'contract': 'spend-outcomes-observation-v1', 'producer': 'cherry-meter-device',
            'status': 'unavailable', 'projects': [], 'sources': [{**source, 'status': 'unavailable'}],
            'coverage': {'status': 'unavailable', 'issues': [reason]},
            'generation': {}, 'conflicts': {'total': 0, 'items': []}}


def codex_scan(source, config, days, through):
    """Process timeout also bounds a blocked filesystem read on Windows and Mac."""
    code = ('import json,sys; sys.path.insert(0,sys.argv[1]); '
            'from spend_outcomes.codex import observe_codex_views; '
            'a=json.load(sys.stdin); print(json.dumps(observe_codex_views(**a)))')
    payload = {'roots': source['roots'], 'projects': config['projects'],
               'days': days, 'through': through, 'tracking_start': source['tracking_start']}
    result = subprocess.run([sys.executable, '-B', '-c', code, str(Path(__file__).resolve().parents[1])],
        input=json.dumps(payload), capture_output=True, text=True, timeout=35, check=True)
    return json.loads(result.stdout)


def observe_source(source, config, selected, days, through):
    views = observe_source_views(source, config, days, through)
    return views['device'] if selected is None else views['projects'][selected]


def observe_source_views(source, config, days, through):
    def missing(reason):
        return {'device': unavailable(source, reason),
                'projects': {key: unavailable(source, reason) for key in config['projects']}}
    try:
        if source['kind'] == 'codex':
            return codex_scan(source, config, days, through)
        if not Path(source['store']).is_file():
            return missing('Claude collector has not created its store; usage is unknown, not zero')
        from .claude import ClaudeStore
        views = ClaudeStore(source['store'], source['tracking_start']).observe_views(
            config['projects'], days, through, bindings=source.get('bindings'))
        from .runtime import read_lifecycle
        lifecycle = read_lifecycle(source['store'])
        for observation in [views['device'], *views['projects'].values()]:
            observation['collector_lifecycle'] = lifecycle
        return views
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, OverflowError, sqlite3.Error) as error:
        # Do not surface subprocess output or unexpected input bytes in reports.
        return missing(source['kind'] + ' observation failed: ' + type(error).__name__)


def merge_observations(observations, selected, days, through):
    end = dt.date.fromisoformat(through) if through else dt.datetime.now(dt.timezone.utc).date()
    start = end - dt.timedelta(days=days - 1)
    periods = [row['period'] for item in observations if item.get('status') != 'unavailable'
               for row in item.get('projects', []) if row.get('period')]
    known = [period for period in periods if period.get('tokens') is not None
             and period.get('coverage_status') != 'unavailable']
    statuses = [item.get('coverage', {}).get('status', 'unknown') for item in observations]
    coverage = 'complete' if all(value == 'complete' for value in statuses) else 'partial' if known else 'unavailable'
    models = []
    daily = {}
    for item in observations:
        client = 'codex' if item.get('producer') == 'spend-outcomes-codex' else 'claude-code'
        for row in item.get('projects', []):
            period = row.get('period') or {}
            for model in period.get('provider_models', []):
                models.append({**model, 'client': model.get('client', client),
                               'account': model.get('account', 'unknown'),
                               'service_route': model.get('service_route', 'unknown')})
            for day in period.get('daily', []):
                aggregate = daily.setdefault(day['date'], {'date': day['date'], 'tokens': 0})
                aggregate['tokens'] += day.get('tokens', 0)
    period = {'from_day': start.isoformat(), 'to_day': end.isoformat(), 'days': days,
              'tokens': sum(item['tokens'] for item in known) if known else None,
              'unpriced_tokens': sum(item['tokens'] for item in known) if known else None,
              'api_equivalent_cost_usd': None, 'coverage_status': coverage,
              'basis': 'Observed source-normalized token volume; inclusive UTC dates; not billing equivalence',
              'daily': sorted(daily.values(), key=lambda item: item['date']), 'provider_models': models}
    issues = [issue for item in observations for issue in item.get('coverage', {}).get('issues', [])]
    conflicts = [conflict for item in observations for conflict in item.get('conflicts', {}).get('items', [])]
    return {'contract': 'spend-outcomes-observation-v1', 'producer': 'cherry-meter-device',
            'status': 'current' if coverage == 'complete' else coverage,
            'generation': {'finished_at': dt.datetime.now(dt.timezone.utc).isoformat()},
            'projects': [{'project_id': selected or 'device', 'project_code': selected or 'device',
                          'attribution': 'workspace-evidence' if selected else 'device-observed', 'period': period}],
            'coverage': {'status': coverage, 'issues': issues},
            'sources': [row for item in observations for row in item.get('sources', [])],
            'source_observations': observations, 'conflicts': {'total': len(conflicts), 'items': conflicts},
            'pricing': {'status': 'unavailable'}, 'collection': {'roots': 'explicit-only'},
            'units': {'tokens': 'Per-source normalized volume; client identities retained; no billing claim'}}


def device_report(config, days=7, through=None, *, observer=None):
    # The MCP adapter supplies a bounded in-process, read-only observer. The
    # independent CLI retains its process-isolated scanner and existing behavior.
    observe = observer or observe_source_views
    views = [observe(source, config, days, through) for source in config['sources']]
    observations = [view['device'] for view in views]
    combined = merge_observations(observations, None, days, through)
    projects = []
    for key, project in config['projects'].items():
        selected = [view['projects'][key] for view in views]
        merged = merge_observations(selected, key, days, through)
        binding = {'project_id': key, 'telemetry_project_id': key, 'association': 'exact', 'days': days}
        outcome = config.get('project_outcomes', {}).get(key)
        if len(config['projects']) == 1:
            outcome = outcome or config.get('outcome')
        receipt = inspect(merged, binding, config.get('targets', {}).get(key, []), local_outcome=outcome)
        receipt['selection']['label'] = project.get('label', key)
        projects.append(receipt)
    return {'contract': 'cherry-meter-device-report-v1', 'synthetic': config.get('synthetic') is True, 'device': config['device'],
            'tracking_start': config['tracking_start'], 'generated_at': combined['generation']['finished_at'],
            'consumption': combined['projects'][0]['period'], 'coverage': combined['coverage'],
            'sources': observations, 'projects': projects,
            'qualifications': ['Device totals and project views are non-additive.',
                'Each source is captured once for all views; source collection clocks can differ.',
                'Remote execution hosts are not included merely because a local desktop or IDE launched them.',
                'Client, exact model, service and account identity are not merged into billing categories.',
                'Missing sources are unknown; usable observations from other sources are retained.',
                'Native GUI/IDE delivery, continuous collector uptime and platform installation remain unqualified.',
                'No prompts, responses, code or tool outputs are stored. No dollar estimate is claimed.']}


def render_device(report, refresh_command=None):
    def esc(value):
        return html.escape(str(value if value is not None else 'Unknown'), quote=True)
    pieces = ['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">',
        '<title>Cherry Meter device report</title><style>body{font:17px/1.5 system-ui;max-width:65rem;margin:auto;padding:2rem;background:#fafbf9;color:#172b36}article,details{border:1px solid #ccd6d8;padding:1rem;margin:1rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>',
        '<h1>Cherry Meter: ' + esc(report['device']['label']) + '</h1>',
        '<p>Tracking start: ' + esc(report['tracking_start']) + '</p>',
        '<p>Saved report: ' + esc(report['generated_at']) + '. Opening this report does not refresh it.</p>',
        '<h2>Device observations</h2><p>Observed tokens: ' + esc(report['consumption']['tokens']) +
        '. Coverage: ' + esc(report['coverage']['status']) + '.</p>', '<h2>Client and model</h2>']
    if report.get('synthetic'):
        pieces.insert(4, '<p><strong>Synthetic demonstration only. No real usage was read or measured.</strong></p>')
    for row in report['consumption']['provider_models']:
        pieces.append('<p>' + esc(row.get('client')) + ' / ' + esc(row.get('model')) + ': ' +
            esc(row.get('tokens')) + ' tokens. Service: ' + esc(row.get('service_name', row.get('service'))) +
            '. Account: ' + esc(row.get('account')) + '.</p>')
        if row.get('client') == 'claude-code':
            pieces.append('<p>Request category: ' + esc(row.get('query_source')) +
                '. Entrypoint: ' + esc(row.get('entrypoint')) + '. App version: ' +
                esc(row.get('app_version')) + '. Service version: ' + esc(row.get('service_version')) + '.</p>')
    pieces.append('<h2>Source coverage</h2>')
    for source in report['sources']:
        name = {'spend-outcomes-codex': 'Codex', 'cherry-meter-claude': 'Claude Code'}.get(source.get('producer'), 'Configured source')
        pieces.append('<article><h3>' + esc(name) + '</h3><p>Status: ' + esc(source.get('status')) + '</p>')
        for row in source.get('sources', []):
            pieces.append('<p>Tracking start: ' + esc(row.get('tracking_start')) + '</p>')
            if 'files' in row:
                pieces.append('<p>Files examined: ' + esc(row['files']) + '</p>')
            if 'last_received' in row:
                pieces.append('<p>Last metric received: ' + esc(row['last_received']) + '</p>')
            if 'entrypoint_qualification' in row:
                pieces.append('<p>Client launch-path qualification: ' + esc(row['entrypoint_qualification']) + '</p>')
        for issue in source.get('coverage', {}).get('issues', []):
            pieces.append('<p>' + esc(str(issue).replace('_', ' ')) + '</p>')
        lifecycle = source.get('collector_lifecycle')
        if lifecycle:
            pieces.append('<p>Collector lifecycle: ' + esc(lifecycle['status'].replace('_', ' ')) + '</p>')
            if lifecycle.get('gaps'):
                pieces.append('<p>Unobserved intervals between collector runs: ' + esc(len(lifecycle['gaps'])) + '</p>')
        pieces.append('</article>')
    for receipt in report['projects']:
        pieces.append('<article><h2>Project: ' + esc(receipt['selection']['label']) + '</h2><p>Observed tokens: ' +
            esc(receipt['consumption']['tokens']) + '</p>')
        for comparison in receipt['comparisons']:
            pieces.append('<p>Advisory target: ' + esc(comparison['status']) + '. ' + esc(comparison['reason']) + '</p>')
        outcome = receipt.get('operator_outcome')
        if outcome:
            pieces.append('<p>Operator-reported outcome: ' + esc(outcome['statement']) + '</p>')
            for checkpoint in outcome.get('checkpoints', []):
                pieces.append('<p>' + esc(checkpoint['text']) + ': ' + esc(checkpoint['status']) + '</p>')
        pieces.append('</article>')
    pieces.extend('<p>' + esc(item) + '</p>' for item in report['qualifications'])
    if refresh_command:
        from .__main__ import command_text
        pieces.append('<h2>Refresh explicitly</h2><pre>' + esc(command_text(refresh_command)) + '</pre>')
    pieces.append('<details><summary>Private measurement record</summary><pre>' +
                  esc(encoded(report).decode('utf-8')) + '</pre></details></html>')
    return ''.join(pieces)


def doctor(config):
    sources = []
    for source in config['sources']:
        paths = source.get('roots', []) if source['kind'] == 'codex' else [source['store']]
        sources.append({'id': source['id'], 'kind': source['kind'], 'tracking_start': source['tracking_start'],
                        'paths': [{'path': path, 'exists': Path(path).exists()} for path in paths],
                        'entrypoint_qualification': 'unverified'})
    return {'device': config['device'], 'runtime': {'python': platform.python_version(), 'system': platform.system()},
            'sources': sources, 'sources_read': False, 'settings_changed': False,
            'qualifications': ['Path existence does not establish readability, completeness or source freshness.',
                'Windows private files inherit directory ACLs; POSIX mode bits do not enforce Windows confidentiality.',
                'Run client-specific controlled exports to qualify CLI, desktop and IDE independently.']}


def create_device_demo(args, invocation, *, report_builder=None):
    """Offline reviewer fixture with 120 Codex + 180 Claude tokens, not real usage."""
    from .claude import ClaudeStore
    root = args.root.expanduser().absolute()
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    workspace = root / 'synthetic-project'; workspace.mkdir()
    logs = root / 'synthetic-codex'; logs.mkdir()
    state = root / 'private-demo-state'
    current = dt.datetime.now(dt.timezone.utc).replace(microsecond=0) - dt.timedelta(seconds=2)
    start = current - dt.timedelta(days=7)
    stamp_text = current.isoformat()
    config = {'schema': SCHEMA, 'synthetic': True, 'tracking_start': start.isoformat(), 'state': str(state),
        'device': {'label': 'Synthetic device demonstration', 'scope': 'synthetic fixtures only'},
        'projects': {'demo': {'permitted': True, 'workspace': str(workspace), 'label': 'Synthetic tandem project'}},
        'sources': [{'id': 'synthetic-codex', 'kind': 'codex', 'permitted': True,
                    'roots': [str(logs)], 'tracking_start': start.isoformat()},
                   {'id': 'synthetic-claude', 'kind': 'claude-otel', 'permitted': True,
                    'store': str(state / 'claude-metrics.sqlite3'), 'tracking_start': start.isoformat()}],
        'targets': {'demo': [{'kind': 'numeric', 'unit': 'tokens', 'meaning': 'observed',
                             'amount': 500, 'window': 'rolling-7-days'}]},
        'outcome': {'statement': 'Review the synthetic device report', 'success_criterion': 'Distinguish sources and gaps',
                    'provenance': 'operator-reported', 'history': [],
                    'checkpoints': [{'id': 'review', 'text': 'Review the sample', 'status': 'pending',
                                     'provenance': 'operator-reported'}]}}
    rows = [{'timestamp': stamp_text, 'type': 'session_meta', 'payload': {'id': 'synthetic-codex', 'cwd': str(workspace)}},
            {'timestamp': stamp_text, 'type': 'turn_context', 'payload': {'model': 'synthetic-codex-model'}},
            {'timestamp': stamp_text, 'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {
                'total_token_usage': {'input_tokens': 100, 'output_tokens': 20, 'cached_input_tokens': 30, 'total_tokens': 120},
                'last_token_usage': {'input_tokens': 100, 'output_tokens': 20, 'cached_input_tokens': 30, 'total_tokens': 120}}}}]
    atomic_bytes(logs / 'synthetic.jsonl', ''.join(json.dumps(row) + '\n' for row in rows).encode())
    points = []
    for kind, count in [('input', 100), ('output', 20), ('cacheRead', 40), ('cacheCreation', 20)]:
        values = {'session.id': 'synthetic-claude', 'model': 'synthetic-claude-model', 'type': kind,
                  'query_source': 'main', 'workspace.path': str(workspace)}
        points.append({'attributes': [{'key': key, 'value': {'stringValue': value}} for key, value in values.items()],
                       'startTimeUnixNano': str(int((current - dt.timedelta(seconds=1)).timestamp() * 1e9)),
                       'timeUnixNano': str(int(current.timestamp() * 1e9)), 'asInt': str(count)})
    payload = {'resourceMetrics': [{'resource': {'attributes': [
        {'key': 'service.name', 'value': {'stringValue': 'claude-code'}},
        {'key': 'app.entrypoint', 'value': {'stringValue': 'synthetic-fixture'}}]},
        'scopeMetrics': [{'metrics': [{'name': 'claude_code.token.usage', 'sum': {
            'aggregationTemporality': 1, 'isMonotonic': True, 'dataPoints': points}}]}]}]}
    ClaudeStore(config['sources'][1]['store'], start.isoformat()).ingest(payload)
    path = immutable(root / 'demo-config.json', config)
    report = (report_builder or device_report)(config)
    receipt = immutable(state / 'device-reports' / (digest(report) + '.json'), report)
    html_path = receipt.with_suffix('.html')
    refresh = [*invocation, 'device-inspect', '--config', str(path), '--html'] if invocation is not None else None
    atomic_bytes(html_path, render_device(report, refresh).encode('utf-8'))
    return {'synthetic': True, 'real_usage_read': False, 'config': str(path), 'receipt': str(receipt),
            'html': str(html_path), 'expected_tokens': {'codex': 120, 'claude-code': 180, 'device': 300},
            'checkpoint_argv': [*invocation, 'checkpoint', '--config', str(path), '--project', 'demo',
                                '--id', 'review', '--status', 'complete', '--actor', 'operator',
                                '--note', 'Reviewed the synthetic sample'] if invocation is not None else None, 'view': report}


def run_command(args, invocation):
    if args.cmd == 'export-plan':
        from .export_plan import make_export_plan
        return make_export_plan(args.port, args.entrypoint)
    if args.cmd == 'device-demo':
        return create_device_demo(args, invocation)
    if args.cmd == 'device-init':
        return initialize(args, invocation)
    config = load_config(args.config)
    if args.cmd == 'doctor':
        return doctor(config)
    if args.cmd in ('collect', 'collector-health', 'lifecycle-plan'):
        sources = [source for source in config['sources'] if source['kind'] == 'claude-otel']
        if len(sources) != 1:
            raise ValueError('collector requires exactly one permitted Claude metrics store')
        source = sources[0]
        if not 1 <= args.port <= 65535:
            raise ValueError('port must be between 1 and 65535')
        if args.cmd == 'lifecycle-plan':
            from .lifecycle import make_plan, write_plan
            plan = make_plan(args.platform, str(args.config.resolve()), args.runtime_root, args.python_path,
                port=args.port, identity=args.identity, user_id=args.user_id, uid=args.uid, user_home=args.user_home)
            return write_plan(plan, args.output)
        from .runtime import CollectorRun, read_lifecycle, store_identity
        if args.cmd == 'collector-health':
            connection = http.client.HTTPConnection('127.0.0.1', args.port, timeout=2)
            try:
                connection.request('GET', '/health')
                response = connection.getresponse()
                raw = response.read(16385)
                if response.status != 200 or len(raw) > 16384:
                    raise ValueError('unexpected receiver response')
                decoded = json.loads(raw)
                if not isinstance(decoded, dict):
                    raise ValueError('unexpected receiver response shape')
                keys = ('service','status','store_identity','runtime_version','run_id','started_at','last_heartbeat','meaning')
                health = {key: decoded[key] for key in keys if key in decoded}
                if any(not isinstance(value, str) or len(value)>512 for value in health.values()):
                    raise ValueError('unexpected receiver field')
                if (health.get('service') != 'cherry-meter' or health.get('status') != 'listening'
                        or health.get('store_identity') != store_identity(source['store'])):
                    raise ValueError('receiver does not identify the configured store')
                from . import __version__
                health['matches_current_runtime'] = health.get('runtime_version') == __version__
            except (OSError, ValueError, http.client.HTTPException) as error:
                health = {'status': 'unreachable_or_mismatched', 'reason': type(error).__name__}
            finally:
                connection.close()
            return {'receiver': health, 'lifecycle': read_lifecycle(source['store']), 'usage_sources_read': False}
        from .claude import ClaudeStore
        from .collector import make_server
        store = ClaudeStore(source['store'], source['tracking_start'])
        store.require_ingest_ready()
        lock = Path(source['store']).with_name(Path(source['store']).name + '.collector')
        with file_lock(lock, timeout=0):
            lifecycle = CollectorRun(store.path)
            server = None
            try:
                server = make_server(store, port=args.port, lifecycle=lifecycle)
                print(json.dumps({'status': 'listening', 'endpoint': 'http://127.0.0.1:' + str(args.port) + '/v1/metrics',
                                  'protocol': 'http/json', 'scope': 'metrics only; local processes can submit data'}), flush=True)
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                if server:
                    server.server_close()
                lifecycle.finish()
        return {'status': 'stopped', 'store': source['store']}
    report = device_report(config, args.days, args.through)
    path = immutable(Path(config['state']) / 'device-reports' / (digest(report) + '.json'), report)
    html_path = None
    if args.html:
        html_path = path.with_suffix('.html')
        refresh = [*invocation, 'device-inspect', '--config', str(args.config.resolve()),
                   '--days', str(args.days), '--html']
        if args.through:
            refresh += ['--through', args.through]
        atomic_bytes(html_path, render_device(report, refresh).encode('utf-8'))
    return {'receipt': str(path), 'html': str(html_path) if html_path else None, 'view': report}
