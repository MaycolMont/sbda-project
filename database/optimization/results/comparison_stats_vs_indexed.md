# Comparison: `stats` → `indexed`

Median of warm executions. Speedup = before / after. Same result = identical ordered result hash.

| Query | Before ms | After ms | Speedup | Rows read before | Rows read after | Plans before/after | Same result |
|---|---:|---:|---:|---:|---:|:---:|:---:|
| q01 Retraction-record volume by recorded notice year | 41.3 | 41.6 | 0.99x | 197,758 | 197,758 | 2/1 | yes |
| q02 Journals with the most source records; exact sou | 233.0 | 232.7 | 1.00x | 197,730 | 197,729 | 1/1 | yes |
| q03 Retraction records by year and first-listed subj | 318.2 | 292.7 | 1.09x | 433,440 | 263,898 | 1/1 | yes |
| q04 Retraction records by first-listed author/instit | 282.7 | 163.4 | 1.73x | 310,144 | 260,776 | 1/1 | yes |
| q05 Retraction-reason occurrence coverage by exact s | 841.4 | 838.4 | 1.00x | 716,012 | 716,012 | 1/1 | yes |
| q06 Number of records assigned each article-type lab | 83.7 | 84.2 | 0.99x | 203,268 | 203,268 | 1/1 | yes |
| q07 Publisher coverage by original publication year. | 245.8 | 246.1 | 1.00x | 197,730 | 197,730 | 1/1 | yes |
| q08 Average difference between recorded dates by pub | 126.0 | 126.4 | 1.00x | 263,666 | 263,666 | 1/1 | yes |
| q09 Five most common journal labels per recorded ret | 259.2 | 262.0 | 0.99x | 231,068 | 231,068 | 1/1 | yes |
| q10 Recorded date intervals by primary subject for 2 | 259.4 | 259.6 | 1.00x | 388,654 | 388,654 | 1/1 | yes |
| **Total** | **2690.9** | **2547.1** | **1.06x** | | | | yes |

Plans before/after = number of distinct plans chosen across rounds in each run.
