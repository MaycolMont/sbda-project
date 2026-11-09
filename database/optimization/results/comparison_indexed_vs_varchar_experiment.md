# Comparison: `indexed` → `varchar_experiment`

Median of warm executions. Speedup = before / after. Same result = identical ordered result hash.

| Query | Before ms | After ms | Speedup | Rows read before | Rows read after | Plans before/after | Same result |
|---|---:|---:|---:|---:|---:|:---:|:---:|
| q01 Retraction-record volume by recorded notice year | 41.6 | 46.1 | 0.90x | 197,758 | 197,758 | 1/2 | yes |
| q02 Journals with the most source records; exact sou | 232.7 | 149.0 | 1.56x | 197,729 | 197,729 | 1/1 | yes |
| q03 Retraction records by year and first-listed subj | 292.7 | 320.1 | 0.91x | 263,898 | 263,898 | 1/1 | yes |
| q04 Retraction records by first-listed author/instit | 163.4 | 176.7 | 0.92x | 260,776 | 260,776 | 1/1 | yes |
| q05 Retraction-reason occurrence coverage by exact s | 838.4 | 710.6 | 1.18x | 716,012 | 716,012 | 1/1 | yes |
| q06 Number of records assigned each article-type lab | 84.2 | 91.4 | 0.92x | 203,268 | 203,268 | 1/1 | yes |
| q07 Publisher coverage by original publication year. | 246.1 | 233.8 | 1.05x | 197,730 | 197,729 | 1/1 | yes |
| q08 Average difference between recorded dates by pub | 126.4 | 137.8 | 0.92x | 263,666 | 263,666 | 1/1 | yes |
| q09 Five most common journal labels per recorded ret | 262.0 | 279.8 | 0.94x | 231,068 | 231,067 | 1/1 | yes |
| q10 Recorded date intervals by primary subject for 2 | 259.6 | 252.2 | 1.03x | 388,654 | 388,654 | 1/1 | yes |
| **Total** | **2547.1** | **2397.5** | **1.06x** | | | | yes |

Plans before/after = number of distinct plans chosen across rounds in each run.
