"""Launch the contained readable source package without installation."""
import pathlib
import sys


def main():
    # Installed plugin content remains readable source; do not add bytecode files.
    sys.dont_write_bytecode = True
    if sys.version_info < (3, 10):
        print("Cherry Meter requires an existing Python 3.10 or newer runtime.", file=sys.stderr)
        return 2
    root = pathlib.Path(__file__).resolve().parent.parent
    package = root / "spend_outcomes" / "__main__.py"
    if package.is_file():
        sys.path.insert(0, str(root))
        from spend_outcomes.__main__ import main as application
        return application()
    print("Cherry Meter package is missing. Keep native/ beside the matching readable spend_outcomes source package.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
