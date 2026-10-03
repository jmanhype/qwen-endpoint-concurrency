# No knee up to 8 concurrent — a negative result

**Finding: I could not find the concurrency knee. At 1, 2, 4 and 8 client-side parallel
requests, the route returned 32/32 `200`s with a 0% error rate and flat median latency
(~8 s). The honest headline is "not found in the range tested", not "the service scales".**

Measured on **`Qwen-Ambassador/Qwen3.8-Max`**, one fixed prompt, from one machine.

```
python3 run.py      # 4 levels x 8 requests = 32 real calls
```

## Result

| parallelism | ok | error rate | p50 | p95 | mean completion tokens |
|-------------|----|-----------|-----|-----|------------------------|
| 1 | 8/8 | 0.0% | 8.03 s | 9.62 s | 245.0 |
| 2 | 8/8 | 0.0% | 8.77 s | 9.23 s | 251.0 |
| 4 | 8/8 | 0.0% | 8.67 s | 9.70 s | 249.4 |
| 8 | 8/8 | 0.0% | 7.91 s | 9.61 s | 235.2 |

Every request returned `200`. Median latency did not rise with parallelism; if anything
the 8-wide level was marginally the fastest, which is noise at this N rather than a real
speed-up.

## Reading this honestly

"No knee at 8" is a statement about the search range, not about capacity. Three
explanations fit equally well and this harness cannot separate them:

1. the endpoint genuinely has headroom past 8 concurrent;
2. the work is long enough (~8 s) that queueing at these depths hides inside request
   duration rather than showing up as added latency;
3. latency is dominated by something that is not contention — for example a fixed
   server-side scheduling or model-load cost.

Separating them needs higher parallelism and a arrival-rate sweep, not more repetitions
at the same levels.

## What would make this stronger

- Push past 8 (16, 32, 64) until errors or latency inflation actually appear.
- Run a fixed request *rate* instead of a fixed request *count*, which is the standard way
  to find a queueing knee.
- Repeat across times of day, since shared capacity is the obvious confounder.

## Honest caveats

- **32 requests total, 8 per level, single run.** No variance estimate; a single bad minute
  would show up as a level effect.
- Client-side parallelism, not a controlled load test. The bottleneck may be this client,
  the local network, or the client's HTTP stack rather than the service.
- One fixed prompt. Longer outputs would shift all latencies.
- No `429`/`503` was observed, so I have no evidence either way about the route's
  rate-limit behaviour.

## Files

- `run.py` — threaded harness over a fixed prompt
- `results/raw.jsonl` — 32 raw records with status, latency and usage tokens
- `results/summary.json` — per-level percentiles and error rates
- `receipts.sha256` — hashes of harness and raw logs
