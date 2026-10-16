"""Measure diagnostic API latency and throughput under concurrent load.

The API rate-limits each token (RATE_LIMIT_PER_MINUTE, default 20); raise it on the target
deployment before benchmarking or the run measures 429 responses.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx

from evaluation.metrics import latency_summary
from evaluation.sse import completed_result

DEFAULT_REQUEST = {"question": "Why does this deployment keep restarting?", "namespace": "inferops-demo",
                   "workload": {"kind": "Deployment", "name": "oom-demo"}}


async def benchmark(url: str, token: str, total: int, concurrency: int, request: dict) -> dict:
    durations: list[float] = []
    errors: dict[str, int] = {}
    queue: asyncio.Queue[int] = asyncio.Queue()
    for index in range(total):
        queue.put_nowait(index)

    async def worker(client: httpx.AsyncClient) -> None:
        while not queue.empty():
            queue.get_nowait()
            started = time.perf_counter()
            try:
                response = await client.post(f"{url}/api/diagnose", headers={"Authorization": f"Bearer {token}"}, json=request)
                response.raise_for_status()
                completed_result(response.text)
                durations.append((time.perf_counter() - started) * 1000)
            except Exception as exc:  # count every failure class instead of aborting the run
                key = f"HTTP {exc.response.status_code}" if isinstance(exc, httpx.HTTPStatusError) else type(exc).__name__
                errors[key] = errors.get(key, 0) + 1

    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=120) as client:
        await asyncio.gather(*(worker(client) for _ in range(concurrency)))
    elapsed = time.perf_counter() - started
    return {"requests": total, "concurrency": concurrency, "succeeded": len(durations), "errors": errors,
            "throughput_rps": round(len(durations) / elapsed, 2), **latency_summary(durations)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8081")
    parser.add_argument("--token", default="dev-token")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 4])
    parser.add_argument("--workload", default="oom-demo")
    parser.add_argument("--output")
    args = parser.parse_args()
    request = DEFAULT_REQUEST | {"workload": {"kind": "Deployment", "name": args.workload}}
    with httpx.Client() as client:
        config = client.get(f"{args.url}/api/config").json()
    runs = [asyncio.run(benchmark(args.url.rstrip("/"), args.token, args.count, level, request)) for level in args.concurrency]
    report = {"backend": config, "workload": args.workload, "runs": runs}
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
