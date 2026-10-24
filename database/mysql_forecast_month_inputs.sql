-- Separate analytical inputs only. No operational tables are changed.
USE practicehub;
CREATE TABLE IF NOT EXISTS forecast_month_inputs (
    kpi_month DATE PRIMARY KEY,
    same_day_gp_requests INTEGER NOT NULL,
    routine_gp_requests INTEGER NOT NULL,
    opening_days INTEGER NOT NULL,
    bank_holidays INTEGER NOT NULL,
    opening_mondays INTEGER NOT NULL,
    input_source VARCHAR(100) NOT NULL,
    created_at_utc DATETIME NOT NULL,
    CHECK (same_day_gp_requests >= 0 AND routine_gp_requests >= 0),
    CHECK (opening_days BETWEEN 1 AND 31),
    CHECK (bank_holidays BETWEEN 0 AND 31),
    CHECK (opening_mondays BETWEEN 0 AND 5)
);

CREATE TABLE IF NOT EXISTS forecast_month_input_corrections (
    correction_id VARCHAR(36) PRIMARY KEY,
    kpi_month DATE NOT NULL,
    before_values TEXT NOT NULL,
    after_values TEXT NOT NULL,
    reason VARCHAR(500) NOT NULL,
    corrected_at_utc DATETIME NOT NULL
);
