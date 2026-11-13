"""Contained stdio MCP entrypoint; never launch the independent CLI or helper."""
import pathlib
import sys


def main():
    sys.dont_write_bytecode = True
    if sys.version_info < (3, 10):
        print("Cherry Meter MCP requires an existing Python 3.10+ runtime.", file=sys.stderr)
        return 2
    root = pathlib.Path(__file__).resolve().parent.parent
    if not (root / "spend_outcomes" / "mcp.py").is_file():
        print("Cherry Meter MCP package is missing.", file=sys.stderr)
        return 2
    sys.path.insert(0, str(root))
    from spend_outcomes.mcp import serve
    return serve(sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    raise SystemExit(main())
