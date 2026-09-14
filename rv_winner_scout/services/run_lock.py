"""Run lock manager to prevent concurrent scout runs."""

import os
import time
from typing import Optional
from rv_winner_scout.config.settings import Settings, get_settings
from rv_winner_scout.domain.exceptions import RunLockActiveError


class RunLock:
    """Acquires exclusive filesystem lock for the scout execution lifespan."""

    def __init__(self, lock_file: Optional[str] = None, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        if lock_file:
            self.lock_path = lock_file
        else:
            os.makedirs(self.settings.data_dir, exist_ok=True)
            self.lock_path = os.path.join(self.settings.data_dir, ".run.lock")
        self.fd: Optional[int] = None

    def acquire(self) -> None:
        # Check if lock file exists and whether it's stale (> 2 hours)
        if os.path.exists(self.lock_path):
            try:
                mtime = os.path.getmtime(self.lock_path)
                if (time.time() - mtime) > 7200:
                    # Stale lock: remove safely
                    os.remove(self.lock_path)
                else:
                    raise RunLockActiveError(
                        f"Active run lock found at {self.lock_path}. Another run may be in progress."
                    )
            except OSError:
                pass

        try:
            self.fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            pid = str(os.getpid()).encode("utf-8")
            os.write(self.fd, pid)
        except (OSError, FileExistsError) as e:
            raise RunLockActiveError(f"Could not acquire run lock at {self.lock_path}: {e}") from e

    def release(self) -> None:
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None

        if os.path.exists(self.lock_path):
            try:
                os.remove(self.lock_path)
            except OSError:
                pass

    def __enter__(self) -> "RunLock":
        self.acquire()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.release()
