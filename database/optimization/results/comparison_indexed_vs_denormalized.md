# Comparison: `indexed` → `denormalized`

Median of warm executions. Speedup = before / after. Same result = identical ordered result hash.

| Query | Before ms | After ms | Speedup | Rows read before | Rows read after | Plans before/after | Same result |
|---|---:|---:|---:|---:|---:|:---:|:---:|
| q01 Retraction-record volume by recorded notice year | 41.6 | 15.1 | 2.76x | 197,758 | 131,849 | 1/1 | yes |
| q02 Journals with the most source records; exact sou | 232.7 | 45.7 | 5.09x | 197,729 | 140,271 | 1/1 | yes |
| q03 Retraction records by year and first-listed subj | 292.7 | 38.3 | 7.65x | 263,898 | 134,081 | 1/1 | yes |
| q04 Retraction records by first-listed author/instit | 163.4 | 25.5 | 6.41x | 260,776 | 131,177 | 1/1 | yes |
| q07 Publisher coverage by original publication year. | 246.1 | 51.2 | 4.81x | 197,730 | 136,271 | 1/1 | yes |
| q08 Average difference between recorded dates by pub | 126.4 | 26.7 | 4.74x | 263,666 | 131,848 | 1/1 | yes |
| q09 Five most common journal labels per recorded ret | 262.0 | 74.7 | 3.51x | 231,068 | 181,828 | 1/1 | yes |
| q10 Recorded date intervals by primary subject for 2 | 259.6 | 34.4 | 7.55x | 388,654 | 114,242 | 1/1 | yes |
| **Total** | **1624.4** | **311.5** | **5.22x** | | | | yes |

Plans before/after = number of distinct plans chosen across rounds in each run.
