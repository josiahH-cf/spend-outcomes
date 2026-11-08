"""Public-v1 behavior: direct Codex input, local outcomes, and deterministic builds."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from io import BytesIO

from scripts.hn_delivery import build


ROOT = Path(__file__).resolve().parents[1]


def write_session(path, workspace, *, session="session-1", secret="PRIVATE PROMPT"):
    rows = [
        {"timestamp":"2026-11-07T10:00:00Z","type":"session_meta",
         "payload":{"id":session,"cwd":str(workspace),"instructions":secret}},
        {"timestamp":"2026-11-07T10:01:00Z","type":"turn_context",
         "payload":{"model":"gpt-public-test","user_message":secret}},
        {"timestamp":"2026-11-07T10:02:00Z","type":"event_msg","payload":{"type":"token_count","info":{
            "total_token_usage":{"input_tokens":80,"cached_input_tokens":10,"output_tokens":20,
                                 "reasoning_output_tokens":5,"total_tokens":100},
            "last_token_usage":{"input_tokens":80,"cached_input_tokens":10,"output_tokens":20,
                                "reasoning_output_tokens":5,"total_tokens":100}}}},
        # Repeated cumulative snapshot: not another 100 tokens.
        {"timestamp":"2026-11-07T10:02:00Z","type":"event_msg","payload":{"type":"token_count","info":{
            "total_token_usage":{"input_tokens":80,"cached_input_tokens":10,"output_tokens":20,
                                 "reasoning_output_tokens":5,"total_tokens":100},
            "last_token_usage":{"input_tokens":80,"cached_input_tokens":10,"output_tokens":20,
                                "reasoning_output_tokens":5,"total_tokens":100}}}},
        {"timestamp":"2026-11-08T10:02:00Z","type":"event_msg","payload":{"type":"token_count","info":{
            "total_token_usage":{"input_tokens":110,"cached_input_tokens":15,"output_tokens":40,
                                 "reasoning_output_tokens":8,"total_tokens":150},
            "last_token_usage":{"input_tokens":30,"cached_input_tokens":5,"output_tokens":20,
                                "reasoning_output_tokens":3,"total_tokens":50}}}},
        # Copied/out-of-order cumulative history must not rewind the active counter.
        {"timestamp":"2026-11-06T10:02:00Z","type":"event_msg","payload":{"type":"token_count","info":{
            "total_token_usage":{"input_tokens":95,"cached_input_tokens":12,"output_tokens":25,
                                 "reasoning_output_tokens":6,"total_tokens":120}}}},
        # A compaction response is separately observed once, despite repeated markers.
        {"timestamp":"2026-11-08T10:03:00Z","type":"token_usage_record","payload":{
            "thread_id":session,"response_id":"compact-1","usage":{
                "input_tokens":10,"cached_input_tokens":2,"output_tokens":5,
                "reasoning_output_tokens":1,"total_tokens":15}}},
        {"timestamp":"2026-11-08T10:04:00Z","type":"compacted","payload":{"compaction_response_id":"compact-1"}},
        {"timestamp":"2026-11-08T10:05:00Z","type":"compacted","payload":{"compaction_response_id":"compact-1"}},
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row)+"\n" for row in rows), encoding="utf-8")


class PublicV1Tests(unittest.TestCase):
    def cli(self, cwd, *args, ok=True):
        command=list(map(str,args)) if args and Path(str(args[0])).name.startswith("python") else ["python3", "-m", "spend_outcomes", *map(str,args)]
        result = subprocess.run(
            command,
            cwd=cwd, text=True, capture_output=True,
            env={**os.environ,"PYTHONPATH":str(ROOT)},
        )
        self.assertEqual(result.returncode, 0 if ok else 2, result.stderr+"\ncommand="+repr(command))
        return json.loads(result.stdout if ok else result.stderr)

    def test_direct_codex_setup_checkpoint_and_prior_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);workspace=root/"project";workspace.mkdir()
            logs=root/"codex";write_session(logs/"sessions"/"one.jsonl", workspace)
            # A copied history has the same event identities and remains non-additive.
            (logs/"archive").mkdir();(logs/"archive"/"copy.jsonl").write_bytes((logs/"sessions"/"one.jsonl").read_bytes())
            config=root/"private"/"config.json";config.parent.mkdir();state=root/"state"
            created=self.cli(root,"init","--config",config,"--project","demo","--name","Demo Project",
                "--workspace",workspace,"--codex-root",logs,"--state",state,"--target-tokens","200",
                "--outcome","Ship the useful thing","--success-criterion","A person can use it",
                "--checkpoint","first-report=Open the first report")
            self.assertEqual(config.stat().st_mode & 0o777,0o600)
            self.assertNotIn("project_id",json.loads(config.read_text())["projects"]["demo"])
            first=self.cli(root,"inspect","--config",config,"--project","demo","--state",state,"--html","--through","2026-11-08")
            self.assertEqual(first["view"]["consumption"]["tokens"],165)
            self.assertEqual(first["view"]["comparisons"][0]["remainder"],35)
            self.assertEqual(first["view"]["operator_outcome"]["checkpoints"][0]["status"],"pending")
            old_json=Path(first["receipt"]).read_bytes();old_html=Path(first["html"]).read_bytes()
            updated=self.cli(root,"checkpoint","--config",config,"--project","demo","--id","first-report",
                             "--status","complete","--actor","operator","--note","Opened and reviewed")
            self.assertEqual(updated["execution_effects"],[])
            second=self.cli(root,"inspect","--config",config,"--project","demo","--state",state,"--html","--through","2026-11-08")
            self.assertNotEqual(first["receipt"],second["receipt"])
            self.assertEqual(second["view"]["operator_outcome"]["checkpoints"][0]["status"],"complete")
            self.assertEqual(Path(first["receipt"]).read_bytes(),old_json)
            self.assertEqual(Path(first["html"]).read_bytes(),old_html)
            self.assertNotIn("PRIVATE PROMPT",json.dumps(second))
            self.assertNotIn(b"PRIVATE PROMPT",Path(second["receipt"]).read_bytes())
            self.assertNotIn(b"PRIVATE PROMPT",Path(second["html"]).read_bytes())
            self.cli(root,"target","--config",config,"--project","demo","--tokens","160","--actor","operator")
            self.cli(root,"outcome","--config",config,"--project","demo","--statement","Ship and learn",
                     "--success-criterion","A person can use and review it","--actor","operator")
            third=self.cli(root,"inspect","--config",config,"--project","demo","--state",state,"--through","2026-11-08")
            self.assertEqual(third["view"]["comparisons"][0]["excess"],5)
            self.assertEqual(third["view"]["operator_outcome"]["statement"],"Ship and learn")
            revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
            archive=root/"spend-outcomes.pyz";archive.write_bytes(build(ROOT,revision)["bytes"])
            archived=self.cli(root,sys.executable,archive,"inspect","--config",config,"--project","demo",
                              "--state",root/"archive-state","--through","2026-11-08")
            self.assertEqual(archived["view"]["consumption"]["tokens"],165)

    def test_partial_codex_source_keeps_observation_but_refuses_full_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);workspace=root/"project";workspace.mkdir();logs=root/"codex"
            write_session(logs/"one.jsonl",workspace)
            with (logs/"one.jsonl").open("a",encoding="utf-8") as handle:handle.write("{malformed\n")
            config=root/"config.json";state=root/"state"
            self.cli(root,"init","--config",config,"--project","demo","--workspace",workspace,
                     "--codex-root",logs,"--state",state,"--target-tokens","200")
            report=self.cli(root,"inspect","--config",config,"--project","demo","--state",state,
                            "--through","2026-11-08")
            self.assertEqual(report["view"]["consumption"]["tokens"],165)
            self.assertEqual(report["view"]["consumption"]["coverage_status"],"partial")
            self.assertEqual(report["view"]["comparisons"][0]["status"],"unknown")
            self.assertIn("partial",report["view"]["comparisons"][0]["reason"].lower())

    def test_archive_is_deterministic_and_bound_to_exact_commit(self):
        revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
        first=build(ROOT,revision);second=build(ROOT,revision)
        self.assertEqual(first["bytes"],second["bytes"])
        self.assertEqual(first["sha256"],hashlib.sha256(first["bytes"]).hexdigest())
        with zipfile.ZipFile(BytesIO(first["bytes"])) as archive:
            self.assertEqual(json.loads(archive.read("SOURCE.json"))["source_revision"],revision)
            self.assertNotIn("tests/test_public_v1.py",archive.namelist())
            self.assertTrue(all(item.date_time==(2020,1,1,0,0,0) for item in archive.infolist()))

    def test_synthetic_demo_and_public_setup_surfaces(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/"demo"
            result=self.cli(Path(directory),"demo","--root",root)
            self.assertTrue(Path(result["html"]).is_file())
            self.assertEqual(json.loads(Path(result["receipt"]).read_text())["consumption"]["tokens"],700)
            self.cli(Path(directory),*result["checkpoint_argv"])
            refused=self.cli(Path(directory),"demo","--root",root,ok=False)
            self.assertIn("exists",refused["reason"])
        readme=(ROOT/"README.md").read_text()
        prompt=(ROOT/"CUSTOMER_SETUP_PROMPT.md").read_text()
        for value in ("Set up with an AI assistant","Manual setup","sha256sum -c SHA256SUMS","operator-reported"):
            self.assertIn(value,readme)
        for value in ("one decision at a time","ask for approval","Do not install system","partial coverage"):
            self.assertIn(value,prompt)


if __name__ == "__main__":
    unittest.main()
