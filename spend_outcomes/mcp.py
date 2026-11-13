"""Small, bounded stdio MCP adapter. No shell, subprocess, network or CLI dispatch.

Plans bind exact scopes and bytes, but do NOT authenticate human consent. The
host must show the plan and obtain actual permission before applying it. No
grants are persisted. Only the device schema is accepted, never legacy consumers.
"""
import copy
import ctypes
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import sqlite3
import stat
import sys
import tempfile
import threading
import time
from types import SimpleNamespace

from . import __version__
from . import device
from .claude import ClaudeStore
from .codex import observe_codex_views
from .core import digest, encoded, immutable, save_record
from .storage import atomic_bytes, file_lock

PROTOCOL = '2025-06-18'
MAX_MESSAGE = 128 * 1024
MAX_CONFIG = 1024 * 1024
MAX_OUTPUT = 2 * 1024 * 1024
MAX_REPORT = 16 * 1024 * 1024
APPROVAL_NOTICE = ('A matching plan hash guards scope and stale data, not user consent. '
    'Obtain actual user approval for these exact reads and writes before apply=true. '
    'No persistent permission is created.')


class Held(ValueError):
    pass


class Cancelled(Exception):
    pass


def check_cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise Cancelled()


def local_path(value, *, file=False, directory=False, write=False):
    """Ordinary absolute local paths only, with no symlink/reparse components.

    This is not an OS sandbox and cannot defeat a malicious same-user path race.
    Network mounts on POSIX and a blocked local filesystem are not detectable.
    """
    if not isinstance(value, str) or not value or len(value) > 4096 or any(ord(c) < 32 for c in value):
        raise Held('Invalid local path.')
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts or value.startswith(('\\\\', '//')):
        raise Held('Use an absolute local path without traversal or UNC/device syntax.')
    if os.name == 'nt':
        if not re.fullmatch('[A-Za-z]:', path.drive) or any(c in value[2:] for c in ':<>"|?*'):
            raise Held('Use an ordinary local Windows drive path.')
        # Reject mapped network drives before touching any path component.
        if ctypes.windll.kernel32.GetDriveTypeW(str(path.anchor)) not in (2, 3, 5, 6):
            raise Held('MCP requires a known local drive, not a mapped network drive.')
        for part in path.parts[1:]:
            if part.endswith((' ', '.')) or part.split('.')[0].upper() in {
                    'CON', 'PRN', 'AUX', 'NUL', *('COM' + str(i) for i in range(1, 10)),
                    *('LPT' + str(i) for i in range(1, 10))}:
                raise Held('Reserved or ambiguous Windows path component.')
    for component in [*reversed(path.parents), path]:
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise Held('Symlink and reparse path components are not permitted by MCP.')
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise Held('Only ordinary files and directories are permitted.')
    if file and not path.is_file():
        raise Held('The selected file does not exist.')
    if directory and not path.is_dir():
        raise Held('The selected directory does not exist.')
    if write:
        names = {part.lower() for part in path.parts}
        if names & {'startup', 'launchagents', 'launchdaemons'} or '/windows/' in path.as_posix().lower():
            raise Held('Use a private data destination, not an OS or startup directory.')
    return path


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('nonfinite JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def validate_config(config):
    if not isinstance(config, dict) or config.get('schema') != device.SCHEMA or 'telemetry' in config:
        raise Held('MCP accepts only explicit device configurations, not legacy consumers or exports.')
    projects = config.get('projects')
    if not isinstance(projects, dict) or not 1 <= len(projects) <= 20:
        raise Held('Device config requires 1 to 20 explicit projects.')
    device.stamp(config['tracking_start'])
    if not isinstance(config.get('device'), dict) or not isinstance(config['device'].get('label'), str):
        raise Held('Device label is missing.')
    if set(config['device']) - {'label', 'execution_host', 'architecture', 'scope'}:
        raise Held('Unsupported device metadata fields; no values were returned.')
    for value in config['device'].values():
        validate(value, string(2000))
    local_path(config['state'], write=True)
    for key, project in projects.items():
        if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', key) or not isinstance(project, dict) or project.get('permitted') is not True:
            raise Held('Invalid explicitly permitted project.')
        if set(project) - {'permitted', 'workspace', 'additional_workspaces', 'label'}:
            raise Held('Unsupported project metadata fields; no values were returned.')
        if 'label' in project:
            validate(project['label'], string(200))
        local_path(project['workspace'])
        extra = project.get('additional_workspaces', [])
        if not isinstance(extra, list) or len(extra) > 20:
            raise Held('Invalid additional workspaces.')
        for value in extra:
            local_path(value)
    sources = config.get('sources')
    if not isinstance(sources, list) or not 1 <= len(sources) <= 2:
        raise Held('One or two explicit device sources are required.')
    seen = set()
    for source in sources:
        if not isinstance(source, dict) or source.get('permitted') is not True:
            raise Held('Each source must be explicitly permitted.')
        kind = source.get('kind')
        allowed = {'id', 'kind', 'permitted', 'tracking_start'} | ({'roots'} if kind == 'codex' else {'store', 'bindings'})
        if set(source) - allowed:
            raise Held('Unsupported source metadata fields; no values were returned.')
        validate(source.get('id'), string(128))
        if kind not in ('codex', 'claude-otel') or kind in seen or any(k in source for k in ('consumer', 'command', 'export')):
            raise Held('Unsupported or duplicate device source.')
        seen.add(kind)
        device.stamp(source['tracking_start'])
        if kind == 'codex':
            roots = source.get('roots')
            if not isinstance(roots, list) or not 1 <= len(roots) <= 20:
                raise Held('Codex requires 1 to 20 explicit roots.')
            for root in roots:
                local_path(root)
        else:
            path = local_path(source['store'])
            # SQLite may open these siblings even in read-only WAL mode.
            for suffix in ('-wal', '-shm', '-journal'):
                local_path(str(path) + suffix)
            bindings = source.get('bindings', {})
            if not isinstance(bindings, dict) or set(bindings) - {'sessions', 'services'}:
                raise Held('Unsupported Claude workspace bindings.')
            for mapping in bindings.values():
                if not isinstance(mapping, dict) or len(mapping) > 1000:
                    raise Held('Invalid Claude workspace bindings.')
                for workspace in mapping.values():
                    local_path(workspace)
    return config


def read_config(value):
    path = local_path(value, file=True)
    if path.suffix.lower() != '.json':
        raise Held('Select the exact device .json configuration.')
    with path.open('rb') as handle:
        raw = handle.read(MAX_CONFIG + 1)
    if len(raw) > MAX_CONFIG:
        raise Held('Device configuration exceeds 1 MiB.')
    return path, raw, validate_config(strict_json(raw))


def scope(config):
    sources = []
    for source in config['sources']:
        keys = ('id', 'kind', 'permitted', 'tracking_start', 'roots') if source['kind'] == 'codex' else ('id', 'kind', 'permitted', 'tracking_start', 'store', 'bindings')
        sources.append({key: copy.deepcopy(source[key]) for key in keys if key in source})
    projects = {key: {field: copy.deepcopy(project[field]) for field in ('permitted', 'workspace', 'additional_workspaces', 'label') if field in project}
                for key, project in config['projects'].items()}
    return {'sources': sources, 'projects': projects,
            'state': config['state'], 'tracking_start': config['tracking_start'],
            'possible_sqlite_sidecar_writes': [source['store'] + suffix for source in config['sources']
                if source['kind'] == 'claude-otel' for suffix in ('-wal', '-shm')],
            'sqlite_qualification': 'Store opened SQL read-only; no schema/data mutation. SQLite may create/update these sidecars to read current WAL data.'}


def plan_result(plan, args):
    identity = digest(plan)
    if args.get('apply', False):
        if args.get('expected_plan_sha256') != identity:
            raise Held('Plan changed or approval hash is missing. Preview again and obtain approval.')
        return None
    return {'plan': plan, 'plan_sha256': identity, 'approval_notice': APPROVAL_NOTICE, 'applied': False}


def atomic_write_details(paths):
    """Describe existing storage effects; these placeholders never drive I/O."""
    return [{'file': str(path),
             'persistent_lock_file': str(path.with_name('.' + path.name + '.lock')),
             'temporary_file_pattern': str(path.with_name('.' + path.name + '.<random>'))}
            for path in paths]


def observer(source, config, days, through, cancel):
    check_cancel(cancel)
    deadline = time.monotonic() + 15
    def progress():
        check_cancel(cancel)
        if time.monotonic() > deadline:
            raise Held('Source processing deadline exceeded.')
    def guard(path):
        progress()
        return local_path(str(path))
    try:
        if source['kind'] == 'codex':
            return observe_codex_views(source['roots'], config['projects'], days, through,
                source['tracking_start'], max_seconds=10, max_files=256,
                max_file_bytes=2*1024*1024, max_line_bytes=256*1024, path_guard=guard, cancel_check=progress)
        if not Path(source['store']).is_file():
            raise Held('Store missing.')
        paths = [Path(source['store'] + suffix) for suffix in ('', '-wal', '-shm', '-journal')]
        if sum(path.stat().st_size for path in paths if path.exists()) > 64*1024*1024:
            raise Held('Claude store and sidecars exceed 64 MiB input limit.')
        store = ClaudeStore(source['store'], source['tracking_start'], read_only=True, max_rows=50000, path_guard=guard, cancel_check=progress)
        views = store.observe_views(config['projects'], days, through, bindings=source.get('bindings'))
        check_cancel(cancel)
        return views
    except Cancelled:
        raise
    except (OSError, ValueError, KeyError, TypeError, OverflowError, sqlite3.Error):
        missing = device.unavailable(source, source['kind'] + ' unavailable or exceeds safe MCP bounds; usage is unknown, not zero')
        return {'device': missing, 'projects': {key: copy.deepcopy(missing) for key in config['projects']}}


def report(config, days=7, through=None, cancel=None):
    result = device.device_report(config, days, through,
        observer=lambda source, cfg, d, t: observer(source, cfg, d, t, cancel))
    check_cancel(cancel)
    result['qualifications'].append('MCP uses bounded in-process local reads. OS-blocked reads cannot be forcibly interrupted; collector lifecycle was not probed.')
    if len(encoded(result)) > MAX_REPORT:
        raise Held('Report exceeds 16 MiB; no report files were written.')
    return result


def summary(result):
    view = result.pop('view')
    return {**result, 'consumption': view['consumption'], 'coverage': view['coverage'],
            'device': view['device'], 'generated_at': view['generated_at'], 'report_sha256': digest(view),
            'projects': [{**{key: receipt[key] for key in ('selection', 'operator_outcome', 'comparisons')},
                          'consumption': {key: receipt['consumption'][key] for key in ('tokens', 'coverage_status', 'from', 'to', 'days')}}
                         for receipt in view['projects']],
            'tracking_start': view['tracking_start'], 'synthetic': view['synthetic'],
            'sources': [{key: source[key] for key in ('producer', 'status', 'sources', 'coverage') if key in source} for source in view['sources']],
            'qualifications': view['qualifications']}


DECISION_FIELDS = {'contract', 'id', 'actor', 'receipt', 'decision', 'feedback', 'next_action',
                   'review_trigger', 'created_at', 'provenance', 'source_versions', 'supersedes'}
MAX_DECISION = 64 * 1024


def read_decision(path):
    path = local_path(str(path), file=True)
    with path.open('rb') as stream:
        raw = stream.read(MAX_DECISION + 1)
    if len(raw) > MAX_DECISION:
        raise Held('Decision exceeds 64 KiB; no records were changed.')
    record = strict_json(raw)
    if (not isinstance(record, dict) or set(record) - DECISION_FIELDS
            or record.get('contract') != 'pv-decision-v1' or record.get('id') != path.stem
            or record.get('provenance') != 'operator-reported'
            or record.get('decision') not in ('keep', 'change', 'investigate', 'hold')
            or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', record.get('id', ''))
            or not isinstance(record.get('actor'), str) or not record['actor'].strip()
            or not re.fullmatch('[0-9a-f]{64}', record.get('receipt', ''))):
        raise Held('Decision record is malformed or unsupported; no records were changed.')
    device.stamp(record['created_at'])
    return record


def read_device_snapshot(config, value):
    path = local_path(value, file=True)
    expected_parent = local_path(str(Path(config['state']) / 'device-reports'))
    if path.parent != expected_parent or path.suffix != '.json' or not re.fullmatch('[0-9a-f]{64}', path.stem):
        raise Held('Select an exact saved SHA256 JSON report in this config\'s device-reports directory.')
    with path.open('rb') as stream:
        raw = stream.read(MAX_REPORT + 1)
    if len(raw) > MAX_REPORT:
        raise Held('Saved report exceeds 16 MiB.')
    view = strict_json(raw)
    if (not isinstance(view, dict) or view.get('contract') != 'cherry-meter-device-report-v1'
            or view.get('device') != config['device'] or digest(view) != path.stem
            or encoded(view) != raw):
        raise Held('Saved report contract, device metadata or canonical SHA256 does not match.')
    device.stamp(view['generated_at'])
    return path, raw, view


def decision_operation(args, cancel):
    config_path, config_raw, config = read_config(args['config'])
    receipt, receipt_raw, view = read_device_snapshot(config, args['receipt'])
    root = local_path(str(Path(config['state']) / 'decisions'), write=True)
    destination = local_path(str(root / (args['id'] + '.json')), write=True)
    store_lock = local_path(str(root.with_name('.' + root.name + '.lock')), write=True)
    local_path(str(destination.with_name('.' + destination.name + '.lock')), write=True)
    for key in ('actor', 'feedback', 'next_action', 'review_trigger'):
        if not args[key].strip():
            raise Held('Supply your own nonblank actor, reason, next action and review trigger.')
    supersedes = args.get('supersedes')
    if supersedes == args['id']:
        raise Held('A decision cannot supersede itself.')
    previous = local_path(str(root / (supersedes + '.json'))) if supersedes else None
    record = {'contract': 'pv-decision-v1', 'id': args['id'], 'actor': args['actor'],
              'receipt': receipt.stem, 'source_versions': {'report_contract': view['contract'],
                  'report_sha256': receipt.stem, 'device_sha256': digest(view['device']), 'generated_at': view['generated_at']},
              **{key: args[key] for key in ('decision', 'feedback', 'next_action', 'review_trigger')},
              'supersedes': supersedes, 'provenance': 'operator-reported'}
    plan = {'operation': 'cherry_meter_decision', 'config': str(config_path),
            'config_sha256': hashlib.sha256(config_raw).hexdigest(), 'receipt': str(receipt),
            'report_sha256': receipt.stem, 'record': record,
            'reads': [str(config_path), str(receipt), str(destination)] + ([str(previous)] if previous else []),
            'write_details': {'directory': str(root), 'directory_creation': 'Decision directory if missing; config/state already exist.',
                'store_lock_file': str(store_lock), 'atomic_files': atomic_write_details([destination]),
                'qualification': 'Existing decisions are immutable. Exact retries preserve first-save timestamp and bytes. Lock files persist; interruption can leave temporary files or completed writes.'},
            'usage_sources_read': False, 'execution_effects': []}
    preview = plan_result(plan, args)
    if preview is not None:
        return preview
    check_cancel(cancel)
    root.mkdir(exist_ok=True, mode=0o700)
    with file_lock(root):
        check_cancel(cancel)
        if read_config(str(config_path))[1] != config_raw or read_device_snapshot(config, str(receipt))[1] != receipt_raw:
            raise Held('Config or snapshot changed; preview and obtain approval again.')
        if previous:
            old = read_decision(previous)
            provenance = old.get('source_versions')
            if not isinstance(provenance, dict) or provenance.get('device_sha256') != digest(view['device']):
                raise Held('Superseded decision lacks matching device provenance; choose a compatible decision.')
        reused = destination.exists()
        if reused:
            record['created_at'] = read_decision(destination)['created_at']
        else:
            record['created_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
        check_cancel(cancel)
        try:
            save_record(root, record)
        except ValueError as error:
            raise Held('Decision ID already contains different content; choose a new ID.') from error
    return {'record': str(destination), 'decision': record, 'report_sha256': receipt.stem,
            'reused': reused, 'applied': True, 'usage_sources_read': False, 'execution_effects': []}


def decision_history(args, cancel):
    _, _, config = read_config(args['config'])
    root = local_path(str(Path(config['state']) / 'decisions'))
    if root.exists() and not root.is_dir():
        raise Held('The configured decision store is not a directory.')
    if 'id' in args:
        paths = [local_path(str(root / (args['id'] + '.json')), file=True)]
    elif root.exists():
        paths = []
        for path in root.glob('*.json'):
            paths.append(path)
            if len(paths) > 128:
                raise Held('More than 128 decisions; request an exact decision ID.')
        paths.sort()
    else:
        paths = []
    records, size = [], 0
    for path in paths:
        check_cancel(cancel)
        record = read_decision(path)
        size += len(json.dumps(record, ensure_ascii=True).encode('utf-8'))
        if size > 1024 * 1024:
            raise Held('Decision history exceeds 1 MiB; request an exact decision ID.')
        records.append(record)
    return {'decisions': records, 'directory': str(root), 'usage_sources_read': False, 'execution_effects': [],
            'scope': 'Approved config and its decision records only; snapshots and usage sources were not read.'}


def execute(name, args, cancel=None):
    validate_arguments(name, args)
    check_cancel(cancel)
    if name == 'cherry_meter_info':
        return {'version': __version__, 'protocol': PROTOCOL, 'runtime': sys.version.split()[0],
            'tools': [tool['name'] for tool in TOOLS], 'approval_notice': APPROVAL_NOTICE,
            'boundaries': ['No shell, subprocess, HTTP, credentials, source discovery or persistent grants.',
                'Only declared MCP tools run plugin application logic.',
                'Independent helper installation and telemetry settings remain explicit human steps.',
                'Legacy CLI consumer/export/import/show and service operations are not MCP tools.',
                'Tool results are returned to the connected Claude client and may enter its conversation.',
                'Existing native CLI remains independently available; do not execute it from plugin commands.']}
    if name == 'cherry_meter_doctor':
        path, raw, config = read_config(args['config'])
        return {**device.doctor(config), 'config_sha256': hashlib.sha256(raw).hexdigest(),
                'scope': scope(config), 'collector_checked': False, 'config': str(path)}
    if name == 'cherry_meter_decision':
        return decision_operation(args, cancel)
    if name == 'cherry_meter_decisions':
        return decision_history(args, cancel)
    if name == 'cherry_meter_report':
        path, raw, config = read_config(args['config'])
        days, through = args.get('days', 7), args.get('through')
        if through:
            dt.date.fromisoformat(through)
        output = local_path(str(Path(config['state']) / 'device-reports'), write=True)
        plan = {'operation': name, 'config': str(path), 'config_sha256': hashlib.sha256(raw).hexdigest(),
                'scope': scope(config), 'report_directory': str(output), 'days': days,
                'through': through, 'html': args.get('html', True)}
        report_files = [output / '<report-sha256>.json']
        if plan['html']:
            report_files.append(output / '<report-sha256>.html')
        plan['write_details'] = {
            'atomic_files': atomic_write_details(report_files),
            'directory_creation': 'The report directory and any missing parent directories on its path.',
            'possible_sqlite_sidecar_writes': plan['scope']['possible_sqlite_sidecar_writes'],
            'qualification': 'Report filenames use the generated report digest. Each atomic file leaves an adjacent lock file; adjacent temporary files are normally renamed or removed, but interruption can leave them. SQLite sidecar writes do not change store SQL schema/data.'}
        preview = plan_result(plan, args)
        if preview is not None:
            return preview
        view = report(config, days, through, cancel)
        # Recheck the selected bytes before writing; a changed config needs a new plan.
        if read_config(str(path))[1] != raw:
            raise Held('Configuration changed while reading; no report was written.')
        receipt = local_path(str(output / (digest(view) + '.json')), write=True)
        html_path = local_path(str(receipt.with_suffix('.html')), write=True)
        check_cancel(cancel)
        immutable(receipt, view)
        if plan['html']:
            atomic_bytes(html_path, device.render_device(view, config_path=path, receipt_path=receipt).encode('utf-8'))
        return summary({'receipt': str(receipt), 'html': str(html_path) if plan['html'] else None, 'view': view})
    if name == 'cherry_meter_demo':
        root = local_path(args['root'], write=True)
        if root.exists() or not root.parent.is_dir():
            raise Held('Choose a new demo directory whose parent already exists.')
        plan = {'operation': name, 'root': str(root),
                'creates': ['synthetic-project/', 'synthetic-codex/', 'private-demo-state/', 'demo-config.json'],
                'real_usage_read': False}
        state = root / 'private-demo-state'
        store = state / 'claude-metrics.sqlite3'
        plan['write_details'] = {
            'directories': [str(path) for path in (root, root / 'synthetic-project',
                root / 'synthetic-codex', state, state / 'device-reports')],
            'atomic_files': atomic_write_details([root / 'synthetic-codex' / 'synthetic.jsonl',
                root / 'demo-config.json', state / 'device-reports' / '<report-sha256>.json',
                state / 'device-reports' / '<report-sha256>.html']),
            'sqlite_store': str(store),
            'possible_sqlite_sidecar_writes': [str(store) + suffix for suffix in ('-wal', '-shm', '-journal')],
            'qualification': 'All files are inside the new demo root. SQLite creates a synthetic store and may create, update or remove its WAL, shared-memory and journal files. Atomic files leave adjacent lock files; adjacent temporary files are normally renamed or removed, but interruption can leave them. Report filenames use the generated report digest.'}
        preview = plan_result(plan, args)
        if preview is not None:
            return preview
        check_cancel(cancel)
        result = device.create_device_demo(SimpleNamespace(root=root), None,
            report_builder=lambda cfg: report(cfg, cancel=cancel))
        result.pop('checkpoint_argv', None)
        return summary(result)
    if name == 'cherry_meter_setup':
        values = dict(args)
        for key in ('apply', 'expected_plan_sha256'):
            values.pop(key, None)
        config_path = local_path(values['config'], write=True)
        if config_path.suffix.lower() != '.json' or config_path.exists() or not config_path.parent.is_dir():
            raise Held('Choose a new .json configuration in an existing private directory.')
        values['config'] = config_path
        values['state'] = local_path(values['state'], write=True)
        values['workspace'] = local_path(values['workspace'], directory=True)
        values['codex_root'] = [local_path(value) for value in values.pop('codex_roots', [])]
        values['additional_workspace'] = [local_path(value, directory=True) for value in values.pop('additional_workspaces', [])]
        defaults = {'name': None, 'target_tokens': None, 'outcome': None, 'success_criterion': None, 'checkpoints': [], 'claude': False}
        values = {**defaults, **values}
        config = validate_config(device.initialize(SimpleNamespace(**values), [], write=False))
        plan = {'operation': name, 'config': str(config_path), 'configuration': config,
                'creates': [str(config_path)], 'sources_read': False, 'starts_helper': False}
        plan['write_details'] = {
            'direct_exclusive_file': str(config_path), 'atomic_files': [],
            'directory_creation': False, 'sqlite_files': [],
            'qualification': 'Setup writes the new config directly with exclusive creation. It creates no adjacent lock/temporary files, state directory or SQLite files; interruption can leave a partial new config.'}
        preview = plan_result(plan, args)
        if preview is not None:
            return preview
        check_cancel(cancel)
        result = device.initialize(SimpleNamespace(**values), [])
        for key in ('inspect_argv', 'collector_argv'):
            result.pop(key, None)
        return result
    if name == 'cherry_meter_checkpoint':
        path, raw, config = read_config(args['config'])
        project = args['project']
        if project not in config['projects']:
            raise Held('Unknown project.')
        outcome = config.get('project_outcomes', {}).get(project)
        if outcome is None and len(config['projects']) == 1:
            outcome = config.get('outcome')
        if not isinstance(outcome, dict):
            raise Held('No unambiguous outcome is configured for this project.')
        matches = [item for item in outcome.get('checkpoints', []) if isinstance(item, dict) and item.get('id') == args['id']]
        if len(matches) != 1 or not isinstance(outcome.get('history', []), list):
            raise Held('Checkpoint missing, ambiguous or malformed.')
        update = {key: args[key] for key in ('project', 'id', 'status', 'actor', 'note')}
        plan = {'operation': name, 'config': str(path), 'config_sha256': hashlib.sha256(raw).hexdigest(),
                'update': update, 'provenance': 'operator-reported', 'sources_read': False,
                'writes': [str(path), str(path.with_name('.' + path.name + '.lock')),
                           str(path.parent / ('.' + path.name + '.<temporary>'))]}
        preview = plan_result(plan, args)
        if preview is not None:
            return preview
        update.update({'reported_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'provenance': 'operator-reported'})
        matches[0].update({key: value for key, value in update.items() if key != 'project'})
        outcome.setdefault('history', []).append(dict(update))
        data = encoded(config)
        if len(data) > MAX_CONFIG:
            raise Held('Updated config exceeds 1 MiB.')
        local_path(str(path.with_name('.' + path.name + '.lock')), write=True)
        check_cancel(cancel)
        with file_lock(path):
            if read_config(str(path))[1] != raw:
                raise Held('Configuration changed; preview and obtain approval again.')
            descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
            try:
                with os.fdopen(descriptor, 'wb') as handle:
                    handle.write(data); handle.flush(); os.fsync(handle.fileno())
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        return {'config': str(path), 'checkpoint': update, 'sources_read': False}
    raise Held('Unsupported tool.')


def string(maximum=4096, **extra):
    return {'type': 'string', 'minLength': 1, 'maxLength': maximum, **extra}


PATH = string()
APPLY = {'apply': {'type': 'boolean', 'default': False}, 'expected_plan_sha256': string(64, pattern='^[0-9a-f]{64}$')}


def tool(name, description, properties, required=(), read_only=False):
    return {'name': name, 'description': description,
            'inputSchema': {'type': 'object', 'properties': properties, 'required': list(required), 'additionalProperties': False},
            'annotations': {'readOnlyHint': read_only, 'destructiveHint': not read_only,
                            'idempotentHint': read_only, 'openWorldHint': False}}


TOOLS = [
    tool('cherry_meter_info', 'Show version, help and boundaries. Reads no user files.', {}, read_only=True),
    tool('cherry_meter_doctor', 'Read only the exact user-approved device config and path existence. No usage or receiver probe.', {'config': PATH}, ['config'], True),
    tool('cherry_meter_report', 'Preview exact reads/writes; after actual user approval apply the matching plan. Bounded metadata reads; private reports, adjacent lock/temp files, missing output directories and approved SQLite sidecars.',
         {'config': PATH, 'days': {'type': 'integer', 'enum': [7, 30, 90]}, 'through': string(10, pattern=r'^\d{4}-\d{2}-\d{2}$'), 'html': {'type': 'boolean'}, **APPLY}, ['config']),
    tool('cherry_meter_demo', 'Preview a new synthetic demo directory, fixtures, config, reports, adjacent lock/temp files and SQLite store/sidecars; apply after approval. No real usage or settings read.', {'root': PATH, **APPLY}, ['root']),
    tool('cherry_meter_setup', 'Preview explicit device configuration; apply after approval. Directly creates one new config, no lock/temp or SQLite files. Reads no usage, starts no helper.',
         {'config': PATH, 'state': PATH, 'project': string(128, pattern=r'^[A-Za-z0-9_.:-]+$'), 'workspace': PATH,
          'additional_workspaces': {'type': 'array', 'items': PATH, 'maxItems': 20},
          'codex_roots': {'type': 'array', 'items': PATH, 'maxItems': 20}, 'claude': {'type': 'boolean'},
          'device_name': string(200), 'name': string(200), 'tracking_start': string(64),
          'target_tokens': {'type': 'integer', 'minimum': 1, 'maximum': 2**63-1},
          'outcome': string(2000), 'success_criterion': string(2000),
          'checkpoints': {'type': 'array', 'items': string(2000), 'maxItems': 100}, **APPLY},
         ['config', 'state', 'project', 'workspace', 'device_name', 'tracking_start']),
    tool('cherry_meter_checkpoint', 'Preview an exact operator-reported checkpoint; apply after user approval. Never infer acceptance or benefit from usage.',
         {'config': PATH, 'project': string(128), 'id': string(128), 'status': {'type': 'string', 'enum': ['pending', 'in-progress', 'complete', 'blocked']},
          'actor': string(200), 'note': string(2000), **APPLY}, ['config', 'project', 'id', 'status', 'actor', 'note']),
    tool('cherry_meter_decision', 'Read the approved config and exact saved device snapshot to preview a human decision. Apply only after exact read/write approval; writes one immutable pv-decision-v1 in the existing decision store, with declared lock/temp files. No usage reads or work execution.',
         {'config': PATH, 'receipt': PATH, 'id': string(128, pattern=r'^[A-Za-z0-9_.:-]+$'),
          'actor': string(200), 'decision': {'type': 'string', 'enum': ['keep', 'change', 'investigate', 'hold']},
          'feedback': string(2000), 'next_action': string(2000), 'review_trigger': string(2000),
          'supersedes': string(128, pattern=r'^[A-Za-z0-9_.:-]+$'), **APPLY},
         ['config', 'receipt', 'id', 'actor', 'decision', 'feedback', 'next_action', 'review_trigger']),
    tool('cherry_meter_decisions', 'Read an approved config and up to 128 existing decision records in its exact state/decisions directory (1 MiB returned limit), or one exact ID. No usage or snapshot reads, writes, discovery outside that directory or work execution.',
         {'config': PATH, 'id': string(128, pattern=r'^[A-Za-z0-9_.:-]+$')}, ['config'], True)]


def validate(value, schema):
    kind = schema['type']
    valid = {'object': isinstance(value, dict), 'array': isinstance(value, list), 'string': isinstance(value, str),
             'integer': type(value) is int, 'boolean': type(value) is bool}[kind]
    if not valid or ('enum' in schema and value not in schema['enum']):
        raise Held('Tool argument type or choice is invalid.')
    if kind == 'object':
        properties = schema['properties']
        if set(value) - set(properties) or set(schema.get('required', [])) - set(value):
            raise Held('Tool arguments contain missing or unknown fields.')
        for key, item in value.items():
            validate(item, properties[key])
    elif kind == 'array':
        if len(value) > schema['maxItems']:
            raise Held('Too many tool argument items.')
        for item in value:
            validate(item, schema['items'])
    elif kind == 'string':
        if not schema.get('minLength', 0) <= len(value) <= schema.get('maxLength', 4096) or any(ord(c) < 32 for c in value):
            raise Held('Invalid tool argument text length or control characters.')
        if 'pattern' in schema and not re.fullmatch(schema['pattern'], value):
            raise Held('Invalid tool argument format.')
    elif kind == 'integer' and not schema.get('minimum', -2**63) <= value <= schema.get('maximum', 2**63-1):
        raise Held('Tool argument integer is out of range.')


def validate_arguments(name, arguments):
    definition = next((item for item in TOOLS if item['name'] == name), None)
    if definition is None:
        raise Held('Unknown tool.')
    validate(arguments, definition['inputSchema'])


class Server:
    """One serialized operation worker; reader can cancel while work is running.

    At most eight queued requests. Cancellation is cooperative before writes and
    between scan files; a committed write is not rolled back. EOF drains queued
    requests. The host may terminate the process for a blocked OS read.
    """
    def __init__(self, output):
        self.output = output
        self.output_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self.pending = {}
        self.work = queue.Queue(maxsize=8)
        self.initialized = False
        self.ready = False
        self.closed = threading.Event()

    def send(self, identity, *, result=None, error=None):
        data = {'jsonrpc': '2.0', 'id': identity}
        data['error' if error is not None else 'result'] = error if error is not None else result
        raw = json.dumps(data, ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode() + b'\n'
        if len(raw) > MAX_OUTPUT:
            raw = json.dumps({'jsonrpc': '2.0', 'id': identity, 'error': {'code': -32603,
                'message': 'Result exceeds response limit; operation may have completed. Inspect the approved destination before retrying.'}}).encode() + b'\n'
        with self.output_lock:
            if self.closed.is_set():
                return
            try:
                self.output.write(raw); self.output.flush()
            except (BrokenPipeError, OSError):
                self.closed.set()

    def error(self, identity, code, message):
        self.send(identity, error={'code': code, 'message': message})

    def receive(self, message):
        if not isinstance(message, dict) or message.get('jsonrpc') != '2.0' or not isinstance(message.get('method'), str):
            self.error(None, -32600, 'Invalid JSON-RPC request.'); return
        identity = message.get('id')
        is_request = 'id' in message
        if is_request and (type(identity) not in (str, int) or isinstance(identity, str) and len(identity) > 128):
            self.error(None, -32600, 'Invalid request id.'); return
        method, params = message['method'], message.get('params', {})
        if not isinstance(params, dict):
            if is_request:
                self.error(identity, -32602, 'Params must be an object.')
            return
        if not is_request:
            if method == 'notifications/initialized' and self.initialized:
                self.ready = True
            elif method == 'notifications/cancelled':
                key = params.get('requestId')
                if type(key) in (str, int):
                    with self.state_lock:
                        if key in self.pending:
                            self.pending[key].set()
            return
        if method == 'initialize':
            if self.initialized or not isinstance(params.get('protocolVersion'), str) or not isinstance(params.get('capabilities'), dict) or not isinstance(params.get('clientInfo'), dict):
                self.error(identity, -32602, 'Invalid or repeated initialize.'); return
            self.initialized = True
            self.send(identity, result={'protocolVersion': PROTOCOL, 'capabilities': {'tools': {}},
                'serverInfo': {'name': 'cherry-meter', 'version': __version__}, 'instructions': APPROVAL_NOTICE})
            return
        if method == 'ping':
            self.send(identity, result={}); return
        if not self.ready:
            self.error(identity, -32002, 'Initialize the MCP session first.'); return
        if method == 'tools/list':
            if params.get('cursor') is not None:
                self.error(identity, -32602, 'This fixed tool list has no cursor.'); return
            self.send(identity, result={'tools': TOOLS}); return
        if method != 'tools/call':
            self.error(identity, -32601, 'Method not found.'); return
        if set(params) - {'name', 'arguments', '_meta'} or not isinstance(params.get('name'), str):
            self.error(identity, -32602, 'Invalid tool call.'); return
        try:
            validate_arguments(params['name'], params.get('arguments', {}))
        except Held as error:
            self.error(identity, -32602, str(error)); return
        with self.state_lock:
            if identity in self.pending:
                self.error(identity, -32600, 'Duplicate outstanding request id.'); return
            cancel = threading.Event()
            self.pending[identity] = cancel
            try:
                self.work.put_nowait((identity, params, cancel))
            except queue.Full:
                self.pending.pop(identity)
                self.error(identity, -32000, 'Server busy; request was not executed.')

    def worker(self):
        while True:
            item = self.work.get()
            if item is None:
                self.work.task_done(); return
            identity, params, cancel = item
            try:
                if self.closed.is_set():
                    cancel.set()
                result = execute(params['name'], params.get('arguments', {}), cancel)
                self.send(identity, result={'content': [{'type': 'text', 'text': json.dumps(result, ensure_ascii=True, allow_nan=False)}], 'isError': False})
            except Cancelled:
                self.error(identity, -32800, 'Cancelled. Completed writes, if any, are retained; inspect before retrying.')
            except Exception as error:
                # No raw config, source bytes, SQL, traceback or third-party error strings.
                message = str(error) if isinstance(error, Held) else 'Operation held (' + type(error).__name__ + '). Check the exact approved configuration and paths.'
                self.send(identity, result={'content': [{'type': 'text', 'text': message}], 'isError': True})
            finally:
                with self.state_lock:
                    self.pending.pop(identity, None)
                self.work.task_done()


def serve(source, output):
    server = Server(output)
    worker = threading.Thread(target=server.worker, daemon=True)
    worker.start()
    try:
        while not server.closed.is_set():
            raw = source.readline(MAX_MESSAGE + 1)
            if not raw:
                break
            if len(raw) > MAX_MESSAGE:
                with server.state_lock:
                    for cancel in server.pending.values():
                        cancel.set()
                server.error(None, -32700, 'Message exceeds 128 KiB; closing transport.')
                return 2
            try:
                message = strict_json(raw.decode('utf-8'))
            except (ValueError, UnicodeDecodeError, RecursionError):
                server.error(None, -32700, 'Invalid UTF-8 JSON.'); continue
            server.receive(message)
        server.work.put(None)
        worker.join()
        return 1 if server.closed.is_set() else 0
    except (BrokenPipeError, OSError):
        return 1
