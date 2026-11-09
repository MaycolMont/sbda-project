# Comparison: `baseline` → `stats`

Median of warm executions. Speedup = before / after. Same result = identical ordered result hash.

| Query | Before ms | After ms | Speedup | Rows read before | Rows read after | Plans before/after | Same result |
|---|---:|---:|---:|---:|---:|:---:|:---:|
| q01 Retraction-record volume by recorded notice year | 41.4 | 41.3 | 1.00x | 197,757 | 197,758 | 2/2 | yes |
| q02 Journals with the most source records; exact sou | 248.0 | 233.0 | 1.06x | 197,729 | 197,730 | 2/1 | yes |
| q03 Retraction records by year and first-listed subj | 320.5 | 318.2 | 1.01x | 433,440 | 433,440 | 1/1 | yes |
| q04 Retraction records by first-listed author/instit | 279.0 | 282.7 | 0.99x | 310,144 | 310,144 | 1/1 | yes |
| q05 Retraction-reason occurrence coverage by exact s | 830.7 | 841.4 | 0.99x | 716,012 | 716,012 | 2/1 | yes |
| q06 Number of records assigned each article-type lab | 84.6 | 83.7 | 1.01x | 203,268 | 203,268 | 1/1 | yes |
| q07 Publisher coverage by original publication year. | 244.9 | 245.8 | 1.00x | 197,730 | 197,730 | 1/1 | yes |
| q08 Average difference between recorded dates by pub | 125.9 | 126.0 | 1.00x | 263,666 | 263,666 | 2/1 | yes |
| q09 Five most common journal labels per recorded ret | 278.3 | 259.2 | 1.07x | 231,068 | 231,068 | 2/1 | yes |
| q10 Recorded date intervals by primary subject for 2 | 258.4 | 259.4 | 1.00x | 388,654 | 388,654 | 1/1 | yes |
| **Total** | **2711.7** | **2690.9** | **1.01x** | | | | yes |

Plans before/after = number of distinct plans chosen across rounds in each run.
