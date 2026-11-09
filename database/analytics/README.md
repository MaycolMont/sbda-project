# Analytical queries

`001_analytical_queries.sql` contains ten MySQL 8.0.46 queries and uses only
the `analyst_*` views. Each query joins multiple views and orders its result.
The set includes aggregate/grouped summaries, two CTE-based analyses, and a
multi-condition date-interval analysis.

Counts refer to source-record observations, not distinct DOI values or resolved
real-world publications. Journal, publisher, country, subject, type, and reason
labels are exact source labels; spelling variants are not consolidated.
`DATEDIFF` results are differences between recorded dates, which can be
approximate, not claims about exact elapsed time. The unverified
`is_misconduct` flag is excluded from all queries.

The integration test executes all ten queries in disposable MySQL against a
small normalized fixture and checks that every query returns rows. The
full-dataset ETL is tested separately, and query 10 is also measured on that
snapshot as documented in `database/optimization/README.md`. These checks do
not constitute reported analytical findings; full query result sets are not
stored.
