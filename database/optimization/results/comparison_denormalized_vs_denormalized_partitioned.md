# Comparison: `denormalized` → `denormalized_partitioned`

Median of warm executions. Speedup = before / after. Same result = identical ordered result hash.

| Query | Before ms | After ms | Speedup | Rows read before | Rows read after | Plans before/after | Same result |
|---|---:|---:|---:|---:|---:|:---:|:---:|
| q01 Retraction-record volume by recorded notice year | 15.1 | 15.2 | 1.00x | 131,849 | 131,870 | 1/1 | yes |
| q02 Journals with the most source records. | 45.7 | 44.8 | 1.02x | 140,271 | 140,292 | 1/1 | yes |
| q03 Retraction records by year and first-listed subj | 38.3 | 36.9 | 1.04x | 134,081 | 134,102 | 1/1 | yes |
| q04 Retraction records by first-listed author/instit | 25.5 | 25.2 | 1.01x | 131,177 | 131,198 | 1/1 | yes |
| q07 Publisher coverage by original publication year. | 51.2 | 51.2 | 1.00x | 136,271 | 136,292 | 1/1 | yes |
| q08 Average difference between recorded dates by pub | 26.7 | 26.9 | 0.99x | 131,848 | 131,869 | 1/1 | yes |
| q09 Five most common journal labels per recorded ret | 74.7 | 72.3 | 1.03x | 181,828 | 181,849 | 1/1 | yes |
| q10 Recorded date intervals by primary subject for 2 | 34.4 | 31.4 | 1.09x | 114,242 | 96,548 | 1/1 | yes |
| **Total** | **311.5** | **304.0** | **1.02x** | | | | yes |

Plans before/after = number of distinct plans chosen across rounds in each run.
