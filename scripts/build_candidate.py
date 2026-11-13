"""Build an uninstalled, readable-source plugin directory; never publish or install."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

DIRECTORIES = (".claude-plugin", "commands", "spend_outcomes", "native", "docs")
FILES = ("LICENSE", "README.md", "PRIVACY.md", "scripts/build_candidate.py")
SUFFIXES = {".json", ".md", ".py", ".ps1", ".cmd"}
REQUIRED = {".claude-plugin/plugin.json", ".claude-plugin/marketplace.json", "native/launch.py", "native/mcp_server.py", "spend_outcomes/mcp.py", "spend_outcomes/__init__.py",
            "spend_outcomes/__main__.py", "commands/setup.md", "commands/report.md",
            "commands/checkpoint.md", "commands/doctor.md", "commands/demo.md",
            "commands/decision.md", "commands/decisions.md", "spend_outcomes/report_view.py"}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def collect_source(root):
    root = Path(root).resolve(strict=True)
    selected = set()
    for name in DIRECTORIES:
        directory = root / name
        if directory.is_symlink() or not directory.resolve().is_relative_to(root):
            raise ValueError("source directory escapes plugin root: " + name)
        if not directory.is_dir():
            raise ValueError("missing source directory: " + name)
        for path in directory.rglob("*"):
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError("source link is not allowed: " + str(path.relative_to(root)))
            if path.is_file() and "__pycache__" not in path.parts:
                relative = path.relative_to(root).as_posix()
                if path.suffix in SUFFIXES or relative == "native/cherry-meter":
                    selected.add(relative)
    selected.update(FILES)
    if not REQUIRED.issubset(selected):
        raise ValueError("candidate is missing required contained runtime files")
    contents = {}
    for name in sorted(selected):
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("source file escapes plugin root: " + name)
        data = path.read_bytes()
        text = data.decode("utf-8")
        if "\x00" in text:
            raise ValueError("binary content is not allowed: " + name)
        if name.endswith(".py"):
            ast.parse(text, filename=name)
        if name.endswith(".json"):
            json.loads(text)
        contents[name] = data
    manifest = json.loads(contents[".claude-plugin/plugin.json"])
    if manifest.get("name") != "cherry-meter" or not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-rc\.[1-9][0-9]*)?", manifest.get("version", "")):
        raise ValueError("invalid plugin name/version")
    catalog = json.loads(contents[".claude-plugin/marketplace.json"])
    if (not isinstance(catalog, dict)
            or set(catalog) != {"name", "description", "owner", "plugins"}
            or catalog.get("name") != "cherry-meter-preview"
            or catalog.get("owner") != {"name": "josiahH-cf"}
            or not isinstance(catalog.get("description"), str) or not catalog["description"].strip()
            or not isinstance(catalog.get("plugins"), list) or len(catalog["plugins"]) != 1):
        raise ValueError("candidate marketplace must be the reviewed preview catalog")
    entry = catalog["plugins"][0]
    if (not isinstance(entry, dict) or set(entry) != {"name", "source", "description"}
            or entry.get("name") != manifest["name"] or entry.get("source") != "./"
            or not isinstance(entry.get("description"), str) or not entry["description"].strip()):
        raise ValueError("candidate marketplace must contain only the root plugin without overrides")
    tree = ast.parse(contents["spend_outcomes/__init__.py"].decode("utf-8"))
    versions = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)]
    if versions != [manifest["version"]]:
        raise ValueError("plugin version must match the contained runtime version")
    if manifest.get("author", {}).get("name") != "Josiah Hunter":
        raise ValueError("author must match verified LICENSE attribution")
    if any(key in manifest for key in ("hooks", "lspServers", "experimental")):
        raise ValueError("candidate must not introduce hooks or other execution components")
    expected = {"cherry-meter": {"command": "${user_config.python_executable}",
        "args": ["-I", "-S", "-B", "${CLAUDE_PLUGIN_ROOT}/native/mcp_server.py"]}}
    if manifest.get('mcpServers') != expected:
        raise ValueError("candidate must declare only the isolated contained MCP server")
    python_option = manifest.get('userConfig', {}).get('python_executable', {})
    if (python_option.get('type') != 'string' or python_option.get('required') is not True
            or python_option.get('default') != 'python'):
        raise ValueError("Python option must declare its reviewable python default and retain the explicit override")
    return contents


def build(root, output):
    root = Path(root).resolve(strict=True)
    output = Path(output).absolute()
    resolved = output.resolve()
    if resolved.is_relative_to(root) or root.is_relative_to(resolved):
        raise ValueError("output must be a new directory outside the source checkout")
    contents = collect_source(root)
    rows = [{"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in sorted(contents.items())]
    metadata = {"contract": "cherry-meter-source-candidate-v1", "files": rows,
                "source_sha256": hashlib.sha256(encoded(rows)).hexdigest(),
                "status": "uninstalled-unpublished-source-candidate"}
    output.mkdir(parents=True, exist_ok=False)
    for name, data in contents.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
    with (output / "CANDIDATE_SOURCE.json").open("xb") as stream:
        stream.write(encoded(metadata))
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.root, args.output)
    except (OSError, ValueError, SyntaxError) as error:
        parser.exit(2, str(error) + "\n")
    print(json.dumps({"output": str(args.output.absolute()), "source_sha256": result["source_sha256"],
                      "files": len(result["files"]), "installed": False, "published": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
