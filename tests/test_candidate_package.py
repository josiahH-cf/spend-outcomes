import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.build_candidate import build, collect_source, REQUIRED

ROOT = Path(__file__).resolve().parents[1]


class CandidatePackage(unittest.TestCase):
    def test_contained_readable_source_and_parser_validation(self):
        contents = collect_source(ROOT)
        self.assertTrue(REQUIRED.issubset(contents))
        self.assertNotIn("plugin/.claude-plugin/plugin.json", contents)
        for name, data in contents.items():
            path = Path(name)
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)
            self.assertTrue((ROOT / path).resolve().is_relative_to(ROOT))
            self.assertNotIn(path.suffix, (".pyz", ".zip", ".exe", ".dll", ".pyc"))
            data.decode("utf-8")
            if name.endswith(".py"):
                ast.parse(data.decode("utf-8"))
        for name in ("setup", "demo", "report", "checkpoint", "doctor"):
            text = contents["commands/" + name + ".md"].decode("utf-8").replace("\r\n", "\n")
            self.assertIn("declared `cherry-meter` MCP server", text)
            self.assertIn("cherry_meter_info", text)
            self.assertNotIn("!`", text)
            self.assertNotIn("../", text)
            self.assertTrue(text.startswith("---\ndescription:"))
        launch = contents["native/launch.py"].decode("utf-8")
        self.assertNotIn(".pyz", launch)
        manifest = json.loads(contents[".claude-plugin/plugin.json"])
        self.assertEqual(manifest["author"], {"name": "Josiah Hunter"})
        self.assertNotIn("hooks", manifest)
        self.assertEqual(set(manifest['mcpServers']), {'cherry-meter'})
        option = manifest['userConfig']['python_executable']
        self.assertEqual(option['default'], 'python')
        self.assertTrue(option['required'])
        self.assertIn('not a trust check', option['description'])
        self.assertEqual(manifest['mcpServers']['cherry-meter']['args'],
            ['-I', '-S', '-B', '${CLAUDE_PLUGIN_ROOT}/native/mcp_server.py'])
        self.assertFalse(any(name.startswith('tests/') for name in contents))
        self.assertIn('spend_outcomes/mcp.py', contents)
        self.assertIn('native/mcp_server.py', contents)

    def test_commands_use_only_declared_mcp_tools(self):
        for name in ("setup", "demo", "report", "checkpoint", "doctor"):
            text = (ROOT / "commands" / (name + ".md")).read_text(encoding="utf-8")
            self.assertNotIn("native/launch.py", text)
            self.assertNotIn("$env:CLAUDE_PLUGIN_ROOT", text)
            self.assertNotIn("$CLAUDE_PLUGIN_ROOT/", text)
            self.assertNotIn("Join-Path", text)
            self.assertIn("Never run a shell", text)
            self.assertIn("does not prove human consent", text)
            self.assertIn("expected_plan_sha256", text)
            self.assertNotIn("!`", text)

    def test_deterministic_bundle_invocation_and_file_hashes(self):
        with tempfile.TemporaryDirectory(prefix="cherry source ") as temporary:
            parent = Path(temporary)
            first = parent / "bundle one"
            second = parent / "bundle two"
            one = build(ROOT, first)
            two = build(ROOT, second)
            self.assertEqual(one, two)
            for row in one["files"]:
                data = (first / row["path"]).read_bytes()
                self.assertEqual(data, (second / row["path"]).read_bytes())
                self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"])
            self.assertEqual((first / "CANDIDATE_SOURCE.json").read_bytes(), (second / "CANDIDATE_SOURCE.json").read_bytes())
            unrelated = parent / "unrelated"
            unrelated.mkdir()
            result = subprocess.run([sys.executable, "-B", str(first / "native/launch.py"), "--version"], cwd=unrelated, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertRegex(result.stdout.strip(), r"^\d+\.\d+\.\d+$")
            for command in ("device-init", "device-inspect", "doctor", "collect", "checkpoint"):
                result = subprocess.run([sys.executable, "-B", str(first / "native/launch.py"), command, "--help"], cwd=unrelated, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            demo = subprocess.run([sys.executable, "-B", str(first / "native/launch.py"),
                "device-demo", "--root", str(parent / "synthetic-demo")], cwd=unrelated, capture_output=True, text=True)
            self.assertEqual(demo.returncode, 0, demo.stderr)
            self.assertEqual(json.loads(demo.stdout)["view"]["consumption"]["tokens"], 300)
            self.assertFalse(list(first.rglob("*.pyc")))
            with self.assertRaises(FileExistsError):
                build(ROOT, first)

    def test_output_must_not_modify_source_tree(self):
        with self.assertRaises(ValueError):
            build(ROOT, ROOT / "candidate-forbidden")
        with self.assertRaises(ValueError):
            build(ROOT, ROOT.parent)


if __name__ == "__main__":
    unittest.main()
