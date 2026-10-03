"""Where does the Qwen Ambassador route start to bend?

Issues a fixed prompt set at increasing client-side parallelism and reports
latency percentiles plus error rate per level.

Scope: this measures one endpoint, at one time, from one machine. It is not a
capacity claim about the service.
"""
from __future__ import annotations

import json
import pathlib
import statistics
from concurrent.futures import ThreadPoolExecutor

from qwen_client import chat

HERE = pathlib.Path(__file__).parent
LEVELS = [1, 2, 4, 8]
REQUESTS_PER_LEVEL = 8

PROMPT = ("List three practical reasons to pin a model revision when you ship an "
          "inference feature. One short sentence each.")


def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round((pct / 100) * (len(ordered) - 1))))
    return round(ordered[idx], 3)


def one(index: int, level: int) -> dict:
    res = chat(PROMPT, max_tokens=256, effort="low")
    return {
        "level": level,
        "index": index,
        "ok": res["ok"],
        "http_status": res["http_status"],
        "latency_s": res["latency_s"],
        "prompt_tokens": res["usage"].get("prompt_tokens"),
        "completion_tokens": res["usage"].get("completion_tokens"),
        "error": res["error"],
    }


def main() -> int:
    records = []
    for level in LEVELS:
        with ThreadPoolExecutor(max_workers=level) as pool:
            futures = [pool.submit(one, i, level) for i in range(REQUESTS_PER_LEVEL)]
            for fut in futures:
                records.append(fut.result())
        ok = [r for r in records if r["level"] == level and r["ok"]]
        print(f"level={level} ok={len(ok)}/{REQUESTS_PER_LEVEL} "
              f"p50={percentile([r['latency_s'] for r in ok], 50)}s")

    out = HERE / "results"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "raw.jsonl").open("w") as fh:
        for rec in records:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")

    summary = {}
    for level in LEVELS:
        rows = [r for r in records if r["level"] == level]
        ok = [r for r in rows if r["ok"]]
        lat = [r["latency_s"] for r in ok]
        summary[str(level)] = {
            "requests": len(rows),
            "ok": len(ok),
            "error_rate": round(1 - len(ok) / len(rows), 3),
            "p50_latency_s": percentile(lat, 50),
            "p95_latency_s": percentile(lat, 95),
            "mean_latency_s": round(statistics.fmean(lat), 3) if lat else None,
            "mean_completion_tokens": (
                round(statistics.fmean([r["completion_tokens"] or 0 for r in ok]), 1)
                if ok else None
            ),
            "statuses": sorted({r["http_status"] for r in rows}),
        }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("\n=== summary ===")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
