import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import materialize_sources as subject


class MaterializationTests(unittest.TestCase):
    def spec(self):
        data = b'a\nb\n'
        blob = hashlib.sha1(b'blob 4\0' + data).hexdigest()
        row = {'path': 'docs/a.md', 'mode': '100644', 'git_blob': blob,
               'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        package = [{k: row[k] for k in ('path', 'bytes', 'sha256')}]
        encoded = (json.dumps(package, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
        return data, {'files': [row], 'source_tree': subject.tree_hash([row]),
                      'package_paths': ['docs/a.md'], 'package_source_sha256': hashlib.sha256(encoded).hexdigest()}

    def fake_git(self, data, spec, extra=''):
        def run(root, *args):
            if args[0] == 'ls-tree':
                row = spec['files'][0]
                return (f"100644 blob {row['git_blob']}\tdocs/a.md\0" + extra).encode()
            if args[0] == 'cat-file':
                return data
            return b'1234567890\n'
        return run

    def test_safe_relative_names(self):
        for name in ('../a', '/a', 'C:/a', 'a\\b', './a', 'a//b', ''):
            with self.subTest(name=name), self.assertRaises(ValueError):
                subject.safe_path(name)

    def test_frozen_manifests_reconstruct_exact_trees(self):
        manifest = json.loads(Path(__file__).with_name('expected-source.json').read_text())
        for name in ('preview', 'baseline'):
            self.assertEqual(subject.tree_hash(manifest[name]['files']), manifest[name]['source_tree'])

    def test_materializes_exact_blob_bytes_not_checkout_newlines(self):
        data, spec = self.spec()
        with tempfile.TemporaryDirectory() as directory, patch.object(subject, 'git', self.fake_git(data, spec)):
            output = Path(directory) / 'new'
            result = subject.materialize(Path(directory), spec, output, True)
            self.assertEqual((output / 'docs/a.md').read_bytes(), data)
            self.assertEqual(result['files'], 1)

    def test_byte_change_and_unexpected_source_fail_closed(self):
        data, spec = self.spec()
        for content, extra in ((data + b'x', ''), (data, '100644 blob ' + '0' * 40 + '\tprivate.md\0')):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as directory:
                with patch.object(subject, 'git', self.fake_git(content, spec, extra)), self.assertRaises(ValueError):
                    subject.materialize(Path(directory), spec, Path(directory) / 'new', True)


if __name__ == '__main__':
    unittest.main()
