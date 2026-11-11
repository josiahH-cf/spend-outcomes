import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from scripts.build_candidate import build, collect_source
from scripts.hn_delivery import build as build_archive
from spend_outcomes import __version__


ROOT = Path(__file__).resolve().parents[1]


class Marketplace(unittest.TestCase):
    def test_root_catalog_is_contained_and_version_has_one_authority(self):
        source = collect_source(ROOT)
        catalog = json.loads(source['.claude-plugin/marketplace.json'])
        manifest = json.loads(source['.claude-plugin/plugin.json'])
        self.assertEqual(catalog['name'], 'cherry-meter-preview')
        self.assertEqual(catalog['owner'], {'name': 'josiahH-cf'})
        self.assertEqual(len(catalog['plugins']), 1)
        entry = catalog['plugins'][0]
        self.assertEqual(entry['name'], manifest['name'])
        self.assertEqual(entry['source'], './')
        self.assertEqual(set(entry), {'name', 'source', 'description'})
        self.assertEqual(manifest['version'], __version__)
        self.assertEqual(__version__, '1.2.1-rc.1')
        self.assertIn('Windows AMD64', manifest['description'])
        self.assertIn('docs/windows-preview.md', source)

    def test_candidate_version_guard_accepts_only_stable_or_numbered_rc(self):
        with tempfile.TemporaryDirectory(prefix='cherry version guard ') as temporary:
            root = Path(temporary) / 'source'
            build(ROOT, root)
            manifest_path = root / '.claude-plugin/plugin.json'
            init_path = root / 'spend_outcomes/__init__.py'
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            for version in ('1.2.0', '1.2.1-rc.1', '1.2.1-rc.12'):
                manifest['version'] = version
                manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
                init_path.write_text('__version__ = ' + repr(version) + '\n', encoding='utf-8')
                collect_source(root)
            for version in ('1.2', 'v1.2.1', '01.2.1', '1.2.1-rc.0', '1.2.1-rc.01',
                            '1.2.1-rc', '1.2.1-anything', '1.2.1+build', '../1.2.1',
                            '1\u0662.2.1', '1.2.1-rc.1\u0662'):
                with self.subTest(version=version):
                    manifest['version'] = version
                    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
                    init_path.write_text('__version__ = ' + repr(version) + '\n', encoding='utf-8')
                    with self.assertRaisesRegex(ValueError, 'invalid plugin name/version'):
                        collect_source(root)

    def test_archive_version_guard_matches_source_package(self):
        for version, accepted in (('1.2.0', True), ('1.2.1-rc.1', True),
                                  ('1.2.1-rc.12', True), ('1.2.1-rc.0', False),
                                  ('01.2.1', False), ('1.2.1-arbitrary', False),
                                  ('1\u0662.2.1', False), ('1.2.1-rc.1\u0662', False)):
            with self.subTest(version=version):
                data = ('__version__ = ' + repr(version) + '\n').encode('utf-8')
                buffer = io.BytesIO()
                with tarfile.open(fileobj=buffer, mode='w') as archive:
                    entry = tarfile.TarInfo('spend_outcomes/__init__.py')
                    entry.size = len(data)
                    archive.addfile(entry, io.BytesIO(data))
                with patch('scripts.hn_delivery.subprocess.run'), patch(
                        'scripts.hn_delivery.subprocess.check_output', return_value=buffer.getvalue()):
                    if accepted:
                        self.assertEqual(build_archive(ROOT, 'a' * 40)['version'], version)
                    else:
                        with self.assertRaisesRegex(ValueError, 'version is missing or invalid'):
                            build_archive(ROOT, 'a' * 40)

    def test_builder_requires_demo_and_exact_contained_catalog(self):
        with tempfile.TemporaryDirectory(prefix='cherry catalog guard ') as temporary:
            root = Path(temporary) / 'source'
            build(ROOT, root)
            for name in ('.claude-plugin/marketplace.json', 'commands/demo.md'):
                path = root / name
                saved = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(ValueError, 'missing required'):
                    collect_source(root)
                path.write_bytes(saved)
            path = root / '.claude-plugin/marketplace.json'
            original = path.read_bytes()
            changes = [
                lambda c: c.update(name='claude-plugins-official'),
                lambda c: c['plugins'].append(dict(c['plugins'][0])),
                lambda c: c['plugins'][0].update(source='../outside'),
                lambda c: c['plugins'][0].update(source={'source': 'command', 'command': 'anything'}),
                lambda c: c['plugins'][0].update(version='1.2.0'),
                lambda c: c['plugins'][0].update(hooks={}),
            ]
            for change in changes:
                catalog = json.loads(original)
                change(catalog)
                path.write_text(json.dumps(catalog), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'candidate marketplace'):
                    collect_source(root)


if __name__ == '__main__':
    unittest.main()
