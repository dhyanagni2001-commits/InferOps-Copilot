"""Container log formatting helpers."""


def summarize_logs(text: str, max_lines: int) -> str:
    lines = text.splitlines()[-max_lines:]
    return "\n".join(lines) if lines else "The container returned no log lines."
