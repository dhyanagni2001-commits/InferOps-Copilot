"""Read-only kubectl execution, plus recorded fixtures that replay real cluster output."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Protocol

from app.config import settings
from app.metrics import TOOL_DURATION

logger = logging.getLogger(__name__)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
READ_ONLY_VERBS = {"get", "logs"}


@dataclass
class CommandResult:
    text: str = ""
    error: Optional[str] = None

    def json(self) -> dict[str, Any]:
        if self.error:
            return {}
        try:
            return json.loads(self.text)
        except json.JSONDecodeError:
            return {}


class CommandRunner(Protocol):
    async def run(self, args: list[str]) -> CommandResult: ...


def command_shape(args: list[str]) -> str:
    """Stable key for a kubectl call that ignores names, namespaces, and selectors."""
    if args and args[0] == "get" and len(args) > 1:
        return f"get {args[1]}"
    return args[0] if args else ""


class KubectlRunner:
    """Run fixed kubectl argument lists. Arguments never pass through a shell."""

    async def run(self, args: list[str]) -> CommandResult:
        if not args or args[0] not in READ_ONLY_VERBS:
            raise ValueError(f"refusing non read-only kubectl command: {args[:1]}")
        shape = command_shape(args)
        started = time.perf_counter()
        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                settings.kubectl_path, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), settings.tool_timeout)
        except asyncio.TimeoutError:
            await _kill(process)
            logger.warning("kubectl_timeout", extra={"command": shape})
            return CommandResult(error=f"kubectl {shape} timed out after {settings.tool_timeout:g}s")
        except asyncio.CancelledError:
            await _kill(process)
            raise
        except FileNotFoundError:
            return CommandResult(error="kubectl is not installed or is not on PATH")
        finally:
            TOOL_DURATION.labels(command=shape).observe(time.perf_counter() - started)

        if process.returncode:
            message = stderr.decode(errors="replace").strip()[-500:]
            logger.warning("kubectl_failed", extra={"command": shape, "error": message})
            return CommandResult(error=message or f"kubectl exited with {process.returncode}")
        text = stdout[: settings.max_tool_output_bytes].decode(errors="replace")
        logger.info("kubectl_completed", extra={"command": shape, "bytes": len(text)})
        return CommandResult(text=text)


async def _kill(process: Optional[asyncio.subprocess.Process]) -> None:
    if process and process.returncode is None:
        process.kill()
        await process.communicate()


@dataclass
class RecordingRunner:
    """Wrap a runner and keep its outputs so they can be saved as a replay fixture."""

    inner: CommandRunner
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def run(self, args: list[str]) -> CommandResult:
        result = await self.inner.run(args)
        self.calls.append({"shape": command_shape(args), "text": _scrub(result.text), "error": result.error})
        return result


def _scrub(text: str) -> str:
    """Drop bulky, noisy metadata from recorded JSON while keeping the real structure."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text

    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: clean(item) for key, item in value.items()
                if key not in {"managedFields", "kubectl.kubernetes.io/last-applied-configuration"}
            }
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    return json.dumps(clean(payload), separators=(",", ":"))


class FixtureRunner:
    """Replay recorded kubectl output for one scenario, keyed by command shape."""

    def __init__(self, scenario: str) -> None:
        payload = json.loads((FIXTURE_DIR / f"{scenario}.json").read_text())
        self.scenario = scenario
        self.calls: dict[str, list[dict[str, Any]]] = {}
        for call in payload["calls"]:
            self.calls.setdefault(call["shape"], []).append(call)

    async def run(self, args: list[str]) -> CommandResult:
        recorded = self.calls.get(command_shape(args))
        if not recorded:
            return CommandResult(error=f"no recorded output for kubectl {command_shape(args)}")
        # Repeated shapes (for example several log calls) replay in recorded order.
        call = recorded.pop(0) if len(recorded) > 1 else recorded[0]
        return CommandResult(text=call["text"], error=call["error"])


def available_fixtures() -> list[str]:
    return sorted(path.stem for path in FIXTURE_DIR.glob("*.json"))


# Workload names used by the controlled scenarios, plus question keywords for free-form demo names.
_KEYWORD_FIXTURES = [
    (("image", "pull", "registry"), "broken-image"),
    (("readiness", "ready", "probe"), "broken-readiness"),
    (("service", "port", "endpoint", "traffic"), "broken-service"),
    (("pending", "schedul", "capacity"), "unschedulable-demo"),
    (("config", "secret", "configmap"), "missing-config"),
    (("crash", "exit", "error log"), "crashloop-demo"),
    (("healthy", "fine", "working"), "healthy-demo"),
]


def fixture_for(workload_name: str, question: str) -> str:
    fixtures = set(available_fixtures())
    if workload_name in fixtures:
        return workload_name
    lowered = question.lower()
    for keywords, fixture in _KEYWORD_FIXTURES:
        if fixture in fixtures and any(word in lowered for word in keywords):
            return fixture
    return "oom-demo"
