# Import PracticeHUB Into MySQL Workbench

V2 UPDATE: the schema has changed. The live database was refreshed with scripts/refresh_mysql.py, which creates a native SQL backup, replaces the named project tables, imports v2 CSVs with foreign keys enabled, recalculates KPIs and checks parity with SQLite. For later complete refreshes use that Python script, or back up MySQL and run database/mysql_refresh_final.sql from the MySQL terminal client with --local-infile=1. Do not import v2 CSVs into the old v1 tables. The legacy wizard instructions and v1 expected counts below are retained as history; use docs/dataset_final_validation.json for current counts.

This guide imports the final PracticeHUB CSV dataset into MySQL using MySQL Workbench.

## Files

- MySQL schema: `database/mysql_schema.sql`
- Final CSV folder: `data/raw/final/`
- KPI CSV structure: `data/processed/final/monthly_kpis.csv`

## Step 1: Create the Database

1. Open MySQL Workbench.
2. Connect to your local MySQL server.
3. Open `database/mysql_schema.sql`.
4. Run the whole script.
5. Refresh Schemas.
6. You should see a schema called `practicehub`.

## Step 2: Import CSV Files

If your MySQL Workbench version does not have the import wizard, use the terminal import script:

```bash
cd "/Users/barbaraafcaldeira/Documents/Big data module"
mysql --local-infile=1 -u root -p practicehub < database/mysql_import_final.sql
```

If MySQL says `LOAD DATA LOCAL INFILE` is disabled, run this once:

```bash
mysql -u root -p -e "SET GLOBAL local_infile = 1;"
```

Then run the import command again.

If you do have Workbench's import wizard, use the order below.

Import the files in this order:

1. `patients.csv`
2. `clinicians.csv`
3. `clinic_sessions.csv`
4. `appointment_slots.csv`
5. `econsult_requests.csv`
6. `appointments.csv`
7. `incoming_call_volumes.csv`
8. `incoming_call_events.csv`
9. `outgoing_call_attempts.csv`
10. `patient_complaints.csv`
11. `appointment_activity_log.csv`

The unused forecast/evaluation tables and their empty CSVs were retired on 18 October 2026. Current import SQL excludes them; predictions and metrics are stored in result files.

The KPI file is currently headers only, so import it later after KPI rows are populated:

- `data/processed/final/monthly_kpis.csv`

## Step 3: Import Wizard Settings

For each CSV:

1. Right-click the `practicehub` schema.
2. Choose `Table Data Import Wizard`.
3. Select the matching CSV file.
4. Choose `Use existing table`.
5. Select the table with the same name as the CSV file.
6. Confirm that the first row is treated as column names.
7. Run the import.

## Step 4: Check Row Counts

After importing, run:

```sql
USE practicehub;

SELECT 'patients' AS table_name, COUNT(*) AS row_count FROM patients
UNION ALL SELECT 'appointment_slots', COUNT(*) FROM appointment_slots
UNION ALL SELECT 'appointments', COUNT(*) FROM appointments
UNION ALL SELECT 'econsult_requests', COUNT(*) FROM econsult_requests
UNION ALL SELECT 'incoming_call_volumes', COUNT(*) FROM incoming_call_volumes
UNION ALL SELECT 'incoming_call_events', COUNT(*) FROM incoming_call_events
UNION ALL SELECT 'outgoing_call_attempts', COUNT(*) FROM outgoing_call_attempts
UNION ALL SELECT 'patient_complaints', COUNT(*) FROM patient_complaints
UNION ALL SELECT 'appointment_activity_log', COUNT(*) FROM appointment_activity_log;
```

Expected final counts:

| Table | Rows |
|---|---:|
| `patients` | 10,000 |
| `appointment_slots` | 56,376 |
| `appointments` | 46,100 |
| `econsult_requests` | 40,150 |
| `incoming_call_volumes` | 7,830 |
| `incoming_call_events` | 280,492 |
| `outgoing_call_attempts` | 20,451 |
| `patient_complaints` | 353 |
| `appointment_activity_log` | 143,175 |

## Notes

- The data is synthetic and does not contain real patient or NHS activity.
- Importing `incoming_call_events.csv` may take the longest because it is the largest CSV.
- If Workbench struggles with large CSV import, use MySQL command-line import or a Python loader later.
