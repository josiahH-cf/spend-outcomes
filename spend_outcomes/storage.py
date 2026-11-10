"""Portable advisory locks and atomic local writes; no configuration migration."""
from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
import time


@contextmanager
def file_lock(path, timeout=10):
    """Cooperating processes serialize updates; OS releases locks after a crash."""
    path = Path(path)
    lock = path.with_name('.' + path.name + '.lock')
    if lock.is_symlink():
        raise ValueError('refusing symlinked lock')
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(descriptor, 'r+b', buffering=0) as handle:
        deadline = time.monotonic() + timeout
        while True:
            try:
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (OSError, BlockingIOError):
                if time.monotonic() >= deadline:
                    raise TimeoutError('local writer lock timed out')
                time.sleep(0.025)
        try:
            # Windows byte-range locking permits a byte beyond EOF. Initialize
            # only after acquiring it, so first-use writers cannot race a lock.
            if os.fstat(handle.fileno()).st_size == 0:
                handle.seek(0)
                handle.write(b'0')
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_bytes(path, data, *, replace=False):
    """Publish complete bytes; immutable retries never observe a partial file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError('refusing symlinked output')
    descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        with file_lock(path):
            if path.exists() and not replace:
                if path.read_bytes() != data:
                    raise ValueError('immutable identity conflict: ' + path.name)
            else:
                os.replace(temporary, path)
        return path
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
