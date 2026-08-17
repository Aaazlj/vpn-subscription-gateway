#!/usr/bin/env python3
"""In-memory ring buffer of recent logs, exposed via /api/logs."""
from __future__ import annotations
import collections
import sys
import threading
import time


class LogBuffer:
    """Thread-safe ring buffer of log entries, teeing from stdout/stderr."""

    def __init__(self, maxlen: int = 500):
        self._buf = collections.deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr

    def add(self, level: str, message: str) -> None:
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "level": level,
            "message": message.rstrip("\n\r"),
        }
        with self._lock:
            self._buf.append(entry)

    def snapshot(self, limit: int | None = None) -> list:
        with self._lock:
            items = list(self._buf)
        if limit:
            items = items[-limit:]
        return items

    # ---- tee file-like ----

    class _Tee:
        def __init__(self, owner: "LogBuffer", target, level: str):
            self.owner = owner
            self.target = target
            self.level = level
            self._partial = ""

        def write(self, data) -> int:
            self.target.write(data)
            self.target.flush()
            self._partial += data
            while "\n" in self._partial:
                line, self._partial = self._partial.split("\n", 1)
                if line.strip():
                    self.owner.add(self.level, line)
            return len(data)

        def flush(self):
            if hasattr(self.target, "flush"):
                self.target.flush()
            if self._partial.strip():
                self.owner.add(self.level, self._partial)
                self._partial = ""

        def isatty(self):
            return getattr(self.target, "isatty", lambda: False)()

        def fileno(self):
            return self.target.fileno()

    def attach(self) -> None:
        sys.stdout = self._Tee(self, self._orig_stdout, "info")
        sys.stderr = self._Tee(self, self._orig_stderr, "error")

    def detach(self) -> None:
        sys.stdout = self._orig_stdout
        sys.stderr = self._orig_stderr


_buffer: LogBuffer | None = None


def get_buffer() -> LogBuffer:
    global _buffer
    if _buffer is None:
        _buffer = LogBuffer()
    return _buffer


def attach() -> LogBuffer:
    buf = get_buffer()
    buf.attach()
    return buf


def snapshot(limit: int | None = None) -> list:
    return get_buffer().snapshot(limit)
