"""File locking utility for cross-platform JSONL operations."""

import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import structlog

logger = structlog.get_logger(__name__)

# Platform-specific locking
if sys.platform == "win32":
    import msvcrt

    def _lock_file(f) -> None:
        """Lock file using Windows msvcrt."""
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        except Exception:
            # If locking fails, continue without lock (best effort)
            pass

    def _unlock_file(f) -> None:
        """Unlock file using Windows msvcrt."""
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except Exception:
            pass
else:
    import fcntl

    def _lock_file(f) -> None:
        """Lock file using fcntl on Unix/Linux."""
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        except Exception:
            pass

    def _unlock_file(f) -> None:
        """Unlock file using fcntl on Unix/Linux."""
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass


@contextmanager
def file_lock(file_path: Path, timeout: float = 10.0) -> Generator[None, None, None]:
    """Context manager for file locking.

    Args:
        file_path: Path to the file to lock.
        timeout: Maximum time to wait for lock in seconds.

    Yields:
        None
    """
    lock_file = file_path.with_suffix(file_path.suffix + ".lock")
    # Ensure parent directory exists
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()

    while True:
        try:
            # Try to create lock file exclusively
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            logger.debug("File locked", path=str(file_path))
            break
        except FileExistsError:
            if time.time() - start_time > timeout:
                # Force remove stale lock
                try:
                    lock_file.unlink(missing_ok=True)
                except Exception:
                    pass
                raise TimeoutError(f"Could not acquire lock on {file_path} within {timeout}s")
            time.sleep(0.1)

    try:
        yield
    finally:
        # Remove lock file
        try:
            lock_file.unlink(missing_ok=True)
        except Exception:
            pass
        logger.debug("File unlocked", path=str(file_path))


@contextmanager
def locked_file(file_path: Path, mode: str = "r", timeout: float = 10.0) -> Generator:
    """Open a file with locking.

    Args:
        file_path: Path to the file to open.
        mode: File open mode.
        timeout: Maximum time to wait for lock in seconds.

    Yields:
        Open file handle with lock held.
    """
    lock_file = file_path.with_suffix(file_path.suffix + ".lock")
    start_time = time.time()

    while True:
        try:
            # Try to create lock file exclusively
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            if time.time() - start_time > timeout:
                try:
                    lock_file.unlink(missing_ok=True)
                except Exception:
                    pass
                raise TimeoutError(f"Could not acquire lock on {file_path} within {timeout}s")
            time.sleep(0.1)

    f = None
    try:
        f = open(file_path, mode)
        _lock_file(f)
        yield f
    finally:
        if f:
            _unlock_file(f)
            f.close()
        try:
            lock_file.unlink(missing_ok=True)
        except Exception:
            pass
