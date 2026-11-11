import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('harness', Path(__file__).with_name('windows_preview_ci.py'))
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)

class Guards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'sample.txt').write_bytes(b'fixture\n')
        self.rows = [{'path': 'sample.txt', 'bytes': 8, 'sha256': hashlib.sha256(b'fixture\n').hexdigest()}]
        self.expected = hashlib.sha256((json.dumps(self.rows, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()).hexdigest()
        self.write(self.rows)
    def tearDown(self):
        self.temp.cleanup()
    def write(self, rows):
        (self.root/'CANDIDATE_SOURCE.json').write_text(json.dumps({'files':rows,'source_sha256':self.expected}))
    def test_valid(self):
        harness.verify_source(self.root,self.expected)
    def test_forged_label(self):
        (self.root/'sample.txt').write_bytes(b'altered\n')
        self.rows[0]['sha256']=hashlib.sha256(b'altered\n').hexdigest();self.write(self.rows)
        with self.assertRaises(AssertionError):harness.verify_source(self.root,self.expected)
    def test_duplicate(self):
        self.write(self.rows*2)
        with self.assertRaises(AssertionError):harness.verify_source(self.root,self.expected)
    def test_extra(self):
        (self.root/'extra').write_text('x')
        with self.assertRaises(AssertionError):harness.verify_source(self.root,self.expected)
    def test_wrong_size(self):
        self.rows[0]['bytes']=9;self.write(self.rows)
        with self.assertRaises(AssertionError):harness.verify_source(self.root,self.expected)
    def test_unsafe_path(self):
        for name in ('../sample.txt','/sample.txt','C:/sample.txt','sample.txt:stream','sample.txt.','CON','a\\sample.txt'):
            self.rows[0]['path']=name;self.write(self.rows)
            with self.assertRaises(AssertionError):harness.verify_source(self.root,self.expected)
    def test_reparse(self):
        info=type('Info',(),{'st_mode':0o100644,'st_file_attributes':0x400})()
        with patch.object(Path,'lstat',return_value=info):
            with self.assertRaises(AssertionError):harness.no_link(self.root)
    def test_environment_allowlist(self):
        with patch('os.environ', {'SystemRoot':'C:/Windows','PATH':'C:/tools','GITHUB_TOKEN':'not-real','ACTIONS_RUNTIME_TOKEN':'not-real'}):
            env=harness.child_environment(self.root)
            self.assertNotIn('GITHUB_TOKEN',env);self.assertNotIn('ACTIONS_RUNTIME_TOKEN',env)
            self.assertEqual({k.upper():v for k,v in env.items()}['SYSTEMROOT'],'C:/Windows')
            self.assertEqual(env['CLAUDE_CONFIG_DIR'],str(self.root))
    def test_unallowed_values_never_accessed(self):
        class Tripwire(dict):
            def __getitem__(self, key):
                if key in ('GITHUB_TOKEN', 'ACTIONS_RUNTIME_TOKEN'):
                    raise AssertionError('Unallowed value accessed')
                return super().__getitem__(key)
            def items(self):
                raise AssertionError('Environment values enumerated')
        with patch('os.environ', Tripwire({'SystemRoot':'C:/Windows','GITHUB_TOKEN':'not-real','ACTIONS_RUNTIME_TOKEN':'not-real'})):
            env = harness.child_environment(self.root)
            self.assertNotIn('GITHUB_TOKEN', env)
    def test_provider_guard(self):
        with patch('os.environ', {'ANTHROPIC_API_KEY':''}):
            with self.assertRaises(AssertionError):harness.child_environment(self.root)

if __name__ == '__main__':unittest.main()
