"""Container log bounding."""

from __future__ import annotations

ERROR_MARKERS = ("error", "exception", "traceback", "fatal", "panic", "killed", "failed", "not found", "refused")


def bound_logs(text: str, max_lines: int) -> list[str]:
    return [line[:500] for line in text.splitlines()[-max_lines:]]


def error_lines(lines: list[str], limit: int = 5) -> list[str]:
    matches = [line for line in lines if any(marker in line.lower() for marker in ERROR_MARKERS)]
    return matches[-limit:]


def summarize_logs(lines: list[str]) -> str:
    return "\n".join(lines) if lines else "The container returned no log lines."
