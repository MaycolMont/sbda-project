# Raw staging import

This is a lossless raw import boundary, not the normalized production schema.
`001_create_staging.sql` targets MySQL 8.0 using InnoDB and `utf8mb4`; the exact
minor version and Workbench version still need confirmation before deployment.
The SQL avoids `CHECK` constraints for compatibility across MySQL 8.0 minor
releases.

From the repository root:

```powershell
python -m pip install -r scripts\requirements.txt
mysql --default-character-set=utf8mb4 -u <user> -p < database\staging\001_create_staging.sql
$env:MYSQL_HOST = "localhost"
$env:MYSQL_PORT = "3306"
$env:MYSQL_USER = "<user>"
$env:MYSQL_PASSWORD = "<password>"
python scripts\load_staging.py
```

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
