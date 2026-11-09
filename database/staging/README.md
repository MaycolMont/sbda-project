# Raw staging import

This is a lossless raw import boundary, not the normalized production schema.
`001_create_staging.sql` targets MySQL 8.0.46 using InnoDB and `utf8mb4`;
Workbench 8.0 is the team's modeling client. The SQL avoids `CHECK` constraints
for compatibility across MySQL 8.0 minor releases.

For local integration tests, the optional Compose service pins MySQL 8.0.46 and
binds only to loopback port 3307, avoiding the existing local MySQL service on
3306. It has no persistent volume; `docker compose down` discards the test
database with the container. In PowerShell from the repository root:

```powershell
python -m pip install -r scripts\requirements.txt
$env:MYSQL_ROOT_PASSWORD = [guid]::NewGuid().ToString('N')
docker compose -f database\staging\docker-compose.yml up -d --wait
$env:MYSQL_HOST = "localhost"
$env:MYSQL_TEST_HOST = $env:MYSQL_HOST
$env:MYSQL_PORT = "3307"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = $env:MYSQL_ROOT_PASSWORD
python tests\integration\test_staging_mysql.py
python scripts\load_staging.py
python scripts\run_etl.py --staging-batch-id <staging-batch-uuid>
docker compose -f database\staging\docker-compose.yml down
```

The integration test applies both the staging and production schema scripts to
the disposable container and loads the tracked CSV through the staging and
normalized ETL paths. For Workbench, connect to `127.0.0.1:3307` as `root` using
the value in `MYSQL_ROOT_PASSWORD`, then open and review the schema scripts.
Do not reuse a production password for this local disposable container.

The loader uses the tracked CSV by default. Override it with
`--input <path>` or choose an explicit UUID with `--batch-id <uuid>`. Each default
run creates a new batch, even for an identical checksum; a repeated explicit UUID
fails instead of appending to an existing batch. Passwords are read only from
`MYSQL_PASSWORD`, never from command-line arguments.

The loader validates the exact documented CSV header and row widths, checks that
the file does not change while loading, and imports each data row as text without
trimming, placeholder conversion, list splitting, type conversion, or duplicate
removal. `source_row_number` is the one-based logical CSV record ordinal after
the header (quoted multiline fields count as one record). An import is
transactional: success records the row count and completion time; failure rolls
back its staged rows, marks the batch failed, and raises the error.

The batch metadata records source filename, checksum, byte size, UTC timestamps,
status, and row count. The raw row stores every source column unchanged. Empty
CSV cells remain empty strings. The source CSV itself is never modified.
