# Demo script

1. Start `./scripts/dev.sh` and open `http://localhost:5173`.
2. Submit the default restart question to show the offline OOM diagnosis.
3. Expand both evidence records and point out that citations resolve to returned data.
4. Apply a controlled scenario with `./scripts/run-scenario.sh image-pull-error`.
5. Restart with `DEMO_MODE=false`, select `broken-image`, and run the same question.
6. Show structured backend tool logs.
7. Clean up with `./scripts/cleanup-scenarios.sh`.

State clearly whether the response uses deterministic rules or vLLM. Do not present illustrative or demo-mode output as a measured cluster result.
