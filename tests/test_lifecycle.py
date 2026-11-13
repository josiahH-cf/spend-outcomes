import json
import os
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from spend_outcomes.lifecycle import make_plan, write_plan, TASK_NS


class LifecycleTests(unittest.TestCase):
    def windows(self, **overrides):
        options = dict(platform='windows', config_path=r"C:\Private data\O'Brien\config.json",
                       runtime_root=r'C:\Tools with spaces\Cherry Meter',
                       python_path=r'C:\Python 3.12\python.exe', user_id=r'JO\example')
        options.update(overrides)
        return make_plan(**options)

    def mac(self, **overrides):
        options = dict(platform='macos', config_path="/Users/example/Private data/O'Brien/config.json",
                       runtime_root='/Users/example/Tools/Cherry Meter', python_path='/usr/local/bin/python3',
                       uid=501, user_home='/Users/example')
        options.update(overrides)
        return make_plan(**options)

    def test_windows_least_privilege_explicit_argv_and_restart(self):
        plan = self.windows()
        self.assertFalse(plan['content'].startswith('<?xml'))
        self.assertNotIn('encoding=', plan['content'])
        root = ET.fromstring(plan['content']); ns = {'t': TASK_NS}
        get = lambda query: root.find(query, ns).text
        self.assertEqual(get('t:Principals/t:Principal/t:RunLevel'), 'LeastPrivilege')
        self.assertEqual(get('t:Principals/t:Principal/t:LogonType'), 'InteractiveToken')
        self.assertEqual(get('t:Triggers/t:LogonTrigger/t:UserId'), r'JO\example')
        self.assertEqual(get('t:Settings/t:ExecutionTimeLimit'), 'PT0S')
        self.assertEqual(get('t:Settings/t:MultipleInstancesPolicy'), 'IgnoreNew')
        self.assertEqual(get('t:Settings/t:RestartOnFailure/t:Count'), '3')
        self.assertEqual(get('t:Actions/t:Exec/t:Command'), r'C:\Python 3.12\python.exe')
        args = get('t:Actions/t:Exec/t:Arguments')
        self.assertIn('"C:\\Tools with spaces\\Cherry Meter\\native\\launch.py"', args)
        self.assertIn('"C:\\Private data\\O\'Brien\\config.json"', args)
        self.assertNotIn('cmd.exe', plan['content']); self.assertNotIn('powershell', plan['content'])
        self.assertFalse(plan['registered']); self.assertFalse(plan['started'])

    def test_macos_plist_preserves_argument_boundaries(self):
        plan = self.mac()
        data = plistlib.loads(plan['content'].encode())
        self.assertEqual(data['ProgramArguments'], plan['launch_argv'])
        self.assertEqual(data['ProgramArguments'][4], "/Users/example/Private data/O'Brien/config.json")
        self.assertTrue(data['RunAtLoad']); self.assertTrue(data['KeepAlive'])
        self.assertEqual(data['ThrottleInterval'], 30)
        self.assertNotIn('UserName', data); self.assertNotIn('GroupName', data)
        self.assertEqual(plan['install_destination'], '/Users/example/Library/LaunchAgents/local.cherry-meter.plist')

    def test_generation_and_write_do_not_execute_commands(self):
        with tempfile.TemporaryDirectory() as directory, patch('subprocess.run') as run, patch('subprocess.Popen') as popen:
            result = write_plan(self.windows(), Path(directory) / 'review only')
            self.assertTrue(Path(result['plan_file']).is_file())
            self.assertFalse(result['commands_executed'])
            self.assertEqual(result['manual_commands']['install'][0][-1], result['plan_file'])
            self.assertNotIn('/F', result['manual_commands']['install'][0])
            run.assert_not_called(); popen.assert_not_called()
            json.dumps(result)

    def test_idempotent_staging_never_overwrites_conflicting_file(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = self.windows(); first = write_plan(plan, directory); second = write_plan(plan, directory)
            self.assertEqual(first, second)
            changed = self.windows(port=4319)
            with self.assertRaises(ValueError):
                write_plan(changed, directory)
            self.assertEqual(Path(first['plan_file']).read_text(), plan['content'])

    def test_startup_destinations_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            for suffix in ['Library/LaunchAgents', 'Library/LaunchDaemons', 'Start Menu/Programs/Startup',
                           'Windows/System32/Tasks']:
                with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                    write_plan(self.windows(), Path(directory) / suffix)

    def test_invalid_native_paths_accounts_and_identity_refused(self):
        for args in [dict(config_path='relative.json'), dict(runtime_root='/Users/example/runtime'),
                     dict(python_path=r'\\server\share\python.exe'), dict(config_path=r'C:\a\..\b.json'),
                     dict(user_id='SYSTEM'), dict(user_id='BUILTIN\\Administrators'), dict(user_id='DOMAIN\\Administrator'),
                     dict(user_id='S-1-5-32-544'), dict(user_id=None), dict(identity='bad/name'), dict(port=True)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.windows(**args)
        for args in [dict(config_path=r'C:\config.json'), dict(uid=0), dict(uid=None), dict(user_home='/var/root')]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.mac(**args)

    def test_xml_escape_preserves_user_and_path(self):
        plan = self.windows(user_id='DOMAIN\\A&B', config_path=r'C:\Private & Local\config.json')
        root = ET.fromstring(plan['content']); ns = {'t': TASK_NS}
        self.assertEqual(root.find('t:Principals/t:Principal/t:UserId', ns).text, 'DOMAIN\\A&B')
        self.assertIn('Private & Local', root.find('t:Actions/t:Exec/t:Arguments', ns).text)

    def test_macos_manual_commands_are_separate_from_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            result = write_plan(self.mac(), directory)
            self.assertEqual(result['manual_commands']['status'], [['/bin/launchctl', 'print', 'gui/501/local.cherry-meter']])
            self.assertEqual(result['manual_commands']['install'][1][1], '-n')
            self.assertEqual(result['manual_commands']['remove'][-1][-1], result['install_destination'])
            self.assertEqual(result['execution_effects'], [])


if __name__ == '__main__':
    unittest.main()
