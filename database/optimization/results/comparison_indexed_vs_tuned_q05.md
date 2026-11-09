# Comparison: `indexed` → `tuned_q05`

Median of warm executions. Speedup = before / after. Same result = identical ordered result hash.

| Query | Before ms | After ms | Speedup | Rows read before | Rows read after | Plans before/after | Same result |
|---|---:|---:|---:|---:|---:|:---:|:---:|
| q05 Retraction-reason occurrence coverage by exact s | 838.4 | 316.4 | 2.65x | 716,012 | 785,773 | 1/1 | yes |
| **Total** | **838.4** | **316.4** | **2.65x** | | | | yes |

Plans before/after = number of distinct plans chosen across rounds in each run.
