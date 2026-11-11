"""Synthetic clean-profile QA. No downloads, auth, model calls or host settings writes.
Run on a fresh hosted Windows admin VM; this is not consumer Windows11 coverage.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import stat
import re


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def no_link(path):
    info = path.lstat()
    assert not stat.S_ISLNK(info.st_mode) and not (getattr(info, 'st_file_attributes', 0) & 0x400), 'Reparse/link entry rejected'
    return info


def verify_source(root, expected):
    no_link(root)
    for ancestor in root.parents:
        no_link(ancestor)
    metadata = root / 'CANDIDATE_SOURCE.json'
    no_link(metadata)
    manifest = json.loads(metadata.read_text(encoding='utf-8'))
    rows = manifest['files']
    assert isinstance(rows, list) and rows
    seen = set()
    for item in rows:
        assert set(item) == {'path', 'bytes', 'sha256'}
        name = item['path']
        assert isinstance(name, str) and name.isascii() and name != 'CANDIDATE_SOURCE.json'
        assert not any(c in name for c in ('\\', ':', '\x00'))
        parts = name.split('/')
        assert all(part and part not in ('.', '..') and not part.endswith((' ', '.')) for part in parts)
        assert not any(part.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *('COM'+str(i) for i in range(1,10)), *('LPT'+str(i) for i in range(1,10))} for part in parts)
        assert name.casefold() not in seen, 'Duplicate payload path'
        seen.add(name.casefold())
        assert type(item['bytes']) is int and item['bytes'] >= 0
        assert isinstance(item['sha256'], str) and re.fullmatch('[0-9a-f]{64}', item['sha256'])
        path = root
        for part in parts:
            path = path / part
            no_link(path)
        assert path.is_file() and path.stat().st_size == item['bytes']
        assert digest(path) == item['sha256'], name
    assert rows == sorted(rows, key=lambda row: row['path']), 'Noncanonical row order'
    encoded = (json.dumps(rows, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    actual_digest = hashlib.sha256(encoded).hexdigest()
    assert actual_digest == expected == manifest['source_sha256'], 'Unexpected source identity'
    actual = set()
    pending = [root]
    while pending:
        directory = pending.pop()
        for entry in directory.iterdir():
            info = no_link(entry)
            if stat.S_ISDIR(info.st_mode):
                pending.append(entry)
            else:
                assert stat.S_ISREG(info.st_mode), 'Nonregular payload entry'
                actual.add(entry.relative_to(root).as_posix())
    assert actual == {row['path'] for row in rows} | {'CANDIDATE_SOURCE.json'}, 'Unexpected payload files'
    return manifest


def child_environment(profile):
    forbidden = ('ANTHROPIC_', 'CLAUDE_CODE_OAUTH', 'CLAUDE_CODE_USE_', 'OTEL_')
    assert not any(key.startswith(forbidden) or key in {'CLAUDE_CONFIG_DIR', 'CLAUDE_CODE_ENABLE_TELEMETRY'} for key in os.environ), 'Unexpected provider/export/profile variable'
    allowed = {'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATH', 'PATHEXT', 'TEMP', 'TMP',
               'USERPROFILE', 'HOMEDRIVE', 'HOMEPATH', 'APPDATA', 'LOCALAPPDATA',
               'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMW6432', 'PROGRAMDATA',
               'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS', 'OS', 'SYSTEMDRIVE'}
    env = {key: os.environ[key] for key in os.environ if key.upper() in allowed}
    env.update({'CLAUDE_CONFIG_DIR': str(profile), 'DISABLE_AUTOUPDATER': '1',
                'DISABLE_TELEMETRY': '1', 'DISABLE_ERROR_REPORTING': '1',
                'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1'})
    return env


def main():
    parser = argparse.ArgumentParser()
    for name in ('preview', 'baseline', 'preview-digest', 'baseline-digest', 'python', 'claude', 'work-root'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    assert os.name == 'nt', 'Windows qualification only'
    runner = Path(os.environ['RUNNER_TEMP']).resolve(strict=True)
    preview = Path(args.preview).resolve(strict=True)
    baseline = Path(args.baseline).resolve(strict=True)
    python = Path(args.python).resolve(strict=True)
    claude = Path(args.claude).resolve(strict=True)
    assert python.is_file() and claude.is_file()
    verify_source(preview, args.preview_digest)
    verify_source(baseline, args.baseline_digest)
    work_root = Path(args.work_root).resolve()
    assert work_root.is_relative_to(runner) and work_root != runner, 'Work root must be inside RUNNER_TEMP'
    work_root.mkdir(parents=True, exist_ok=False)
    base = work_root
    profile = base / 'profile'; profile.mkdir()
    workspace = base / 'workspace'; workspace.mkdir()
    env = child_environment(profile)
    evidence = {'qualification': 'Isolated unauthenticated Windows profile and direct stdio. Host provenance must be established by caller or job metadata; not stock Windows11/non-admin or authenticated Claude execution.', 'steps': []}

    def save():
        (base / 'qa-evidence.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')

    def run(argv, stdin=None):
        result = subprocess.run([str(x) for x in argv], cwd=workspace, env=env,
                                input=stdin, text=True, capture_output=True, timeout=60)
        evidence['steps'].append({'argv': [str(x) for x in argv], 'exit': result.returncode,
                                  'stdout': result.stdout, 'stderr': result.stderr})
        save()
        assert result.returncode == 0, result.stderr + result.stdout
        return result.stdout

    assert run([python, '-I', '-S', '-B', '-c', 'import sys;print(sys.version.split()[0])']).strip() == '3.12.10'
    assert run([claude, '--version']).strip() == '2.1.287 (Claude Code)'
    # CLI plugin-management commands do not invoke inference or require a login.
    run([claude, 'plugin', 'marketplace', 'add', preview, '--json'])
    plugin = 'cherry-meter@cherry-meter-preview'
    run([claude, 'plugin', 'install', plugin, '--scope', 'user', '--config', 'python_executable=' + str(python), '--json'])

    def installed(key, version, source_digest):
        registry = json.loads((profile / 'plugins/installed_plugins.json').read_text())
        record = registry['plugins'][key][0]
        assert record['version'] == version
        root = Path(record['installPath']).resolve(strict=True)
        assert root.is_relative_to(profile)
        verify_source(root, source_digest)
        options = json.loads((profile / 'settings.json').read_text())['pluginConfigs'][key]['options']
        assert options['python_executable'] == str(python)
        return root

    root = installed(plugin, '1.2.1-rc.1', args.preview_digest)
    manifest = json.loads((root / '.claude-plugin/plugin.json').read_text())
    server = manifest['mcpServers']['cherry-meter']
    assert server['command'] == '${user_config.python_executable}'
    assert server['args'] == ['-I', '-S', '-B', '${CLAUDE_PLUGIN_ROOT}/native/mcp_server.py']
    server_argv = [python, *[x.replace('${CLAUDE_PLUGIN_ROOT}', str(root)) for x in server['args']]]

    def call(name, arguments):
        messages = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'synthetic-hosted-qa', 'version': '1'}}}, {'jsonrpc': '2.0', 'method': 'notifications/initialized'}, {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': name, 'arguments': arguments}}]
        rows = [json.loads(x) for x in run(server_argv, ''.join(json.dumps(m) + '\n' for m in messages)).splitlines()]
        result = next(x['result'] for x in rows if x.get('id') == 2)
        assert not result.get('isError'), result
        return json.loads(result['content'][0]['text'])

    def apply(name, values):
        plan = call(name, values)
        # These fixture-only reads/writes are expressly authorized by the QA task.
        evidence.setdefault('synthetic_plans', []).append(plan); save()
        return call(name, {**values, 'apply': True, 'expected_plan_sha256': plan['plan_sha256']})

    assert call('cherry_meter_info', {})['version'] == '1.2.1-rc.1'
    demo = apply('cherry_meter_demo', {'root': str(base / 'synthetic-demo')})
    assert demo['synthetic'] and demo['consumption']['tokens'] == 300
    report = apply('cherry_meter_report', {'config': demo['config']})
    assert report['consumption']['tokens'] == 300
    retained = {str(p.relative_to(base)): digest(p) for p in (base / 'synthetic-demo').rglob('*') if p.is_file()}
    market = base / 'lifecycle-marketplace'; (market / '.claude-plugin').mkdir(parents=True)
    for version, source in (('1.2.0', baseline), ('1.2.1-rc.1', preview)):
        shutil.copytree(source, market / 'plugins' / version)
    name = 'cherry-meter-preview-lifecycle'; key = 'cherry-meter@' + name

    def catalog(version):
        (market / '.claude-plugin/marketplace.json').write_text(json.dumps({'name': name, 'owner': {'name': 'Cherry Meter QA'}, 'plugins': [{'name': 'cherry-meter', 'source': './plugins/' + version}]}), encoding='utf-8')

    catalog('1.2.0')
    run([claude, 'plugin', 'marketplace', 'add', market, '--json'])
    run([claude, 'plugin', 'install', key, '--scope', 'user', '--config', 'python_executable=' + str(python), '--json'])
    installed(key, '1.2.0', args.baseline_digest)
    for version in ('1.2.1-rc.1', '1.2.0', '1.2.1-rc.1'):
        catalog(version)
        run([claude, 'plugin', 'marketplace', 'update', name, '--json'])
        run([claude, 'plugin', 'update', key, '--scope', 'user', '--json'])
        installed(key, version, args.baseline_digest if version == '1.2.0' else args.preview_digest)
        assert all(digest(base / p) == value for p, value in retained.items())
    evidence.update({'passed': True, 'preview_digest': args.preview_digest, 'baseline_digest': args.baseline_digest, 'synthetic_tokens': 300, 'preserved_files': len(retained), 'local_directory_semantics': 'Catalog source switches plus registry/cache updates; not immutable runtime pinning', 'excluded': ['Previously denied PowerShell wrapper test', 'WSL', 'Authentication and inference', 'Public Git acquisition', 'Consumer Windows11/non-admin install']})
    save()
    print(json.dumps({'passed': True, 'python': '3.12.10', 'claude': '2.1.287', 'preview_version': '1.2.1-rc.1', 'preview_digest': args.preview_digest, 'baseline_digest': args.baseline_digest, 'synthetic_tokens': 300, 'preserved_files': len(retained), 'lifecycle': ['1.2.0', '1.2.1-rc.1', '1.2.0', '1.2.1-rc.1'], 'qualification': evidence['qualification']}, sort_keys=True))


if __name__ == '__main__':
    main()
