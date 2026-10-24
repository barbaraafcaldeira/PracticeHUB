USE practicehub;
START TRANSACTION;
DELETE FROM monthly_kpis;
INSERT INTO monthly_kpis SELECT * FROM vw_monthly_core_kpis;
COMMIT;
SELECT COUNT(*) AS monthly_kpi_rows FROM monthly_kpis;
