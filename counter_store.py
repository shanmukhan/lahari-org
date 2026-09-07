"""Persistence for the lahari.org visitor counter.

Deliberately stdlib-only (no Flask/SQLite/etc.) since this backs a single
counter for a personal static site running as a small systemd service on a
Raspberry Pi (see rpi-setup's configure-lahari.sh) — a whole framework or
database would be pure overhead for one integer.
"""

import fcntl
import json
import os
import tempfile


class CounterStore:
    """A single integer counter persisted to a JSON file.

    Safe for concurrent use from multiple threads/processes: increments take
    an exclusive lock on a sidecar `.lock` file, and writes are atomic
    (write-to-temp-file then os.replace) so a crash mid-write can never leave
    a truncated/corrupt counter file behind.
    """

    def __init__(self, path: str):
        self.path = path

    def get(self) -> int:
        return self._read()

    def increment_and_get(self) -> int:
        directory = os.path.dirname(self.path) or "."
        os.makedirs(directory, exist_ok=True)
        lock_path = self.path + ".lock"
        with open(lock_path, "w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                count = self._read() + 1
                self._write(count)
                return count
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

    def _read(self) -> int:
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
            return int(data.get("count", 0))
        except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError):
            return 0

    def _write(self, count: int) -> None:
        directory = os.path.dirname(self.path) or "."
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".counter-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump({"count": count}, f)
            os.replace(tmp_path, self.path)
        except BaseException:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
