import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from spend_outcomes import __version__

ROOT = Path(__file__).resolve().parents[1]


class NativeWrappers(unittest.TestCase):
    def test_python_launcher_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as other:
            result = subprocess.run([sys.executable, str(ROOT / "native/launch.py"), "--version"], cwd=other, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), __version__)

    def test_missing_package_is_explicit(self):
        with tempfile.TemporaryDirectory(prefix="cherry meter ") as temporary:
            native = Path(temporary) / "native"
            native.mkdir()
            shutil.copyfile(ROOT / "native/launch.py", native / "launch.py")
            result = subprocess.run([sys.executable, str(native / "launch.py")], text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("package is missing", result.stderr)

    def test_source_argument_boundaries_and_exit_status(self):
        with tempfile.TemporaryDirectory(prefix="cherry meter ") as temporary:
            root = Path(temporary)
            native = root / "native"
            native.mkdir()
            shutil.copyfile(ROOT / "native/launch.py", native / "launch.py")
            package = root / "spend_outcomes"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "__main__.py").write_text("import json,sys\ndef main():\n    print(json.dumps(sys.argv[1:])); return 7\n", encoding="utf-8")
            args = ["space value", "amp&value", "quote\"value", "--literal"]
            result = subprocess.run([sys.executable, str(native / "launch.py"), *args], text=True, capture_output=True)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(json.loads(result.stdout), args)

    @unittest.skipUnless(os.name == "nt", "Windows-native wrapper")
    def test_windows_cmd_version(self):
        result = subprocess.run(["cmd.exe", "/d", "/c", str(ROOT / "native/cherry-meter.cmd"), "--version"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), __version__)

    @unittest.skipUnless(os.name == "nt", "Windows-native wrapper")
    def test_powershell_version_without_policy_override(self):
        result = subprocess.run(["powershell.exe", "-NoProfile", "-File", str(ROOT / "native/cherry-meter.ps1"), "--version"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), __version__)

    def test_plugin_structure_and_no_autostart(self):
        plugin = ROOT
        manifest = json.loads((plugin / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "cherry-meter")
        self.assertEqual(manifest["version"], __version__)
        for command in ("setup", "report", "checkpoint", "doctor"):
            text = (plugin / "commands" / (command + ".md")).read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\ndescription:"))
        self.assertFalse((plugin / "hooks").exists())
        self.assertNotIn("hooks", manifest)
        self.assertEqual(set(manifest['mcpServers']), {'cherry-meter'})


if __name__ == "__main__":
    unittest.main()
