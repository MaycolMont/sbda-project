# Database roles

Target MySQL 8.0.46. Apply the scripts in order after the production and staging
schemas exist:

1. `001_create_analyst_views.sql` as the database owner. The views use
   `SQL SECURITY DEFINER`; deploy them as a durable privileged account that
   retains `SELECT` on the underlying production tables.
2. `002_create_roles.sql` as a privileged database administrator. This creates
   roles but intentionally creates no users or passwords.

`academic_admin` receives full privileges on both project schemas for schema,
staging, ETL, and data administration. It does not receive global account
management privileges or `GRANT OPTION`. Account provisioning and role
assignment remain with a MySQL account administrator.

`academic_analyst` receives `SELECT` only on the explicit `analyst_*` views.
The views expose normalized publication, notice, author, country, subject,
article-type, and reason data; they exclude `source_misconduct_flag`,
`etl_record_issue`, `etl_batch`, and the entire raw staging schema. In
particular, analysts cannot retrieve the unverified `is_misconduct` value
through either production tables or staging. The current policy assumes the
team permits analysts to see the source publication and author metadata; the
dataset's precise provenance and license remain unverified.

Create individual user accounts through the team's approved account process,
then grant a role and make it active by default. Use a host pattern restricted
to the approved workstation/network; do not use `%` unless explicitly required:

```sql
GRANT 'academic_analyst' TO 'analyst_user'@'approved-host';
SET DEFAULT ROLE 'academic_analyst' TO 'analyst_user'@'approved-host';
```

Integration tests create temporary random test accounts in the disposable
Docker MySQL instance and verify allowed view reads plus denied access to
sensitive, audit, staging, and write paths. No credentials are committed.
