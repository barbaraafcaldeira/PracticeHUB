# PracticeHUB KPI Queries

V2: mysql_kpi_views.sql now creates the views AND refreshes monthly_kpis. Read kpi_definitions_v2.md for request cohorts, denominators and the historical reporting cutoff. All v2 counts come from linked request records; the former estimated_gp_appointment_demand_signal has been removed. Forecast outputs are intentionally empty.

The main KPI logic is in:

- `database/mysql_kpi_views.sql`
- `database/mysql_populate_monthly_kpis.sql`

## Create KPI Views

Run this in MySQL Workbench or from Terminal:

```bash
cd "/Users/barbaraafcaldeira/Documents/Big data module"
/usr/local/mysql/bin/mysql -u root -p practicehub < database/mysql_kpi_views.sql
```

## Main Views

| View | Purpose |
|---|---|
| `vw_monthly_gp_capacity` | GP sessions, slots, utilisation, booked appointments, DNAs, cancellations. |
| `vw_monthly_econsults` | eConsult volume, GP recommendation rate, resolved-without-appointment rate. |
| `vw_monthly_outgoing_calls` | Outgoing call attempts, answer rate, and appointments booked after outgoing calls. |
| `vw_monthly_telephone` | Incoming calls, answer rate, wait time, outgoing call workload. |
| `vw_monthly_access_complaints` | Appointment-access complaints and complaint rates. |
| `vw_monthly_core_kpis` | Combined monthly KPI dashboard view. |
| `vw_executive_kpis_latest_month` | Small executive KPI set for the latest month. |

## Check The Monthly KPI View

```sql
USE practicehub;

SELECT *
FROM vw_monthly_core_kpis
ORDER BY kpi_month;
```

## Check Executive KPIs

```sql
USE practicehub;

SELECT *
FROM vw_executive_kpis_latest_month;
```

## Populate The Physical KPI Table

Only do this after the views look correct:

```bash
cd "/Users/barbaraafcaldeira/Documents/Big data module"
/usr/local/mysql/bin/mysql -u root -p practicehub < database/mysql_populate_monthly_kpis.sql
```

This fills the `monthly_kpis` table from `vw_monthly_core_kpis`.
