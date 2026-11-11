"""Recreate audited public source bytes from local Git objects. No downloads."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], timeout=30)


def safe_path(value):
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or '..' in path.parts or '\\' in value
            or ':' in value or str(path) != value):
        raise ValueError('Unsafe source path')
    return path


def tree_hash(rows):
    root = {}
    for row in rows:
        parts = safe_path(row['path']).parts
        node = root
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        if parts[-1] in node:
            raise ValueError('Duplicate source path')
        node[parts[-1]] = (row['mode'], row['git_blob'])

    def digest(node):
        body = b''
        for name, value in sorted(node.items(), key=lambda p: (p[0] + ('/' if isinstance(p[1], dict) else '')).encode()):
            mode, sha = ('40000', digest(value)) if isinstance(value, dict) else value
            body += mode.encode() + b' ' + name.encode('utf-8') + b'\0' + bytes.fromhex(sha)
        return hashlib.sha1(b'tree ' + str(len(body)).encode() + b'\0' + body).hexdigest()
    return digest(root)


def materialize(repository, spec, destination, preview):
    rows = spec['files']
    if tree_hash(rows) != spec['source_tree']:
        raise ValueError('Manifest does not reconstruct audited Git tree')
    actual = {}
    for raw in git(repository, 'ls-tree', '-rz', 'HEAD').split(b'\0'):
        if not raw:
            continue
        meta, name = raw.split(b'\t', 1)
        mode, kind, blob = meta.decode().split()
        actual[name.decode('utf-8')] = (mode, kind, blob)
    expected = {row['path'] for row in rows}
    extras = set(actual) - expected
    if extras and (not preview or any(not (p.startswith('qa/') or p == '.github/workflows/windows-preview-qa.yml') for p in extras)):
        raise ValueError('Unexpected files outside the CI-only additions')
    if not expected.issubset(actual):
        raise ValueError('Missing audited source files')
    destination.mkdir(parents=True, exist_ok=False)
    for row in rows:
        name = str(safe_path(row['path']))
        if row['mode'] not in ('100644', '100755') or actual[name] != (row['mode'], 'blob', row['git_blob']):
            raise ValueError('Git source identity differs: ' + name)
        data = git(repository, 'cat-file', 'blob', row['git_blob'])
        data.decode('utf-8')
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256'] or blob != row['git_blob']:
            raise ValueError('Source byte mismatch: ' + name)
        target = destination.joinpath(*PurePosixPath(name).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
    package_rows = [{k: row[k] for k in ('path', 'bytes', 'sha256')}
                    for row in rows if row['path'] in spec['package_paths']]
    encoded = (json.dumps(package_rows, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    if len(package_rows) != len(spec['package_paths']) or hashlib.sha256(encoded).hexdigest() != spec['package_source_sha256']:
        raise ValueError('Package identity mismatch')
    return {'source_tree': spec['source_tree'], 'files': len(rows),
            'package_source_sha256': spec['package_source_sha256'],
            'checked_out_commit': git(repository, 'rev-parse', 'HEAD').decode().strip()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('preview-repo', 'baseline-repo', 'manifest', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    runner = Path(os.environ['RUNNER_TEMP']).resolve(strict=True)
    output = args.output.resolve()
    if output == runner or not output.is_relative_to(runner) or output.exists():
        raise ValueError('Output must be a new path strictly inside RUNNER_TEMP')
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    if manifest['schema'] != 'cherry-meter-hosted-ci-source-v1':
        raise ValueError('Unexpected source contract')
    result = {}
    for name, repo in (('preview', args.preview_repo), ('baseline', args.baseline_repo)):
        result[name] = materialize(repo.resolve(strict=True), manifest[name], output / name, name == 'preview')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
