#!/usr/bin/env python3
"""Stage and validate the request-led dataset before replacing existing files."""

import argparse
import csv
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from practicehub.dataset_v2 import build, schema_sql, write_sql_assets, validate, KPI_SELECT


def run(profile, seed):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    stage = ROOT / "data/exports" / ("build_" + stamp)
    stage.mkdir(parents=True)
    tables, metadata = build(profile, seed)
    db = stage / "dataset.sqlite"
    with sqlite3.connect(db) as conn:
        conn.executescript(schema_sql("sqlite"))
        for table, rows in tables.items():
            if rows:
                columns = list(rows[0])
                sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
                conn.executemany(sql, (tuple(r[c] for c in columns) for r in rows))
        conn.executescript("CREATE VIEW vw_monthly_core_kpis AS " + KPI_SELECT + ";")
        conn.execute("INSERT INTO monthly_kpis SELECT * FROM vw_monthly_core_kpis")
        conn.commit()
        checks = validate(conn, metadata)
        cur = conn.execute("SELECT * FROM monthly_kpis ORDER BY 1")
        tables["monthly_kpis"] = [dict(zip([c[0] for c in cur.description], r)) for r in cur]
        columns = {t: [r[1] for r in conn.execute(f"PRAGMA table_info({t})")] for t in tables}
    conn.close()
    if not checks["passed"]:
        raise RuntimeError("Validation failed; previous data untouched: " + json.dumps(checks))
    raw, processed = stage / "raw", stage / "processed"
    raw.mkdir()
    processed.mkdir()
    for table, rows in tables.items():
        folder = processed if table == "monthly_kpis" else raw
        with (folder / (table + ".csv")).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns[table])
            writer.writeheader()
            writer.writerows(rows)
    csv_bytes = sum(p.stat().st_size for p in raw.glob("*.csv"))
    if profile == "final" and (csv_bytes < 100_000_000 or db.stat().st_size < 100_000_000):
        raise RuntimeError(f"Size gate failed: CSV {csv_bytes}, DB {db.stat().st_size}; previous data untouched")
    manifest = {**metadata, "validation": checks, "row_counts": {t: len(r) for t, r in tables.items()},
                "sqlite_bytes": db.stat().st_size, "raw_csv_bytes": csv_bytes,
                "csv_sha256": {str(p.relative_to(stage)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(stage.rglob("*.csv"))}}
    archive = ROOT / "data/archives" / stamp
    archive.mkdir(parents=True)
    targets = [(ROOT / "database" / f"practicehub_{profile}.sqlite", db, "database.sqlite"),
               (ROOT / "data/raw" / profile, raw, "raw"),
               (ROOT / "data/processed" / profile, processed, "processed")]
    for target, source, backup_name in targets:
        if target.exists():
            shutil.move(str(target), str(archive / backup_name))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
    for name in ["schema.sql", "mysql_schema.sql", "mysql_import_final.sql", "mysql_kpi_views.sql",
                 "mysql_populate_monthly_kpis.sql", "mysql_validation.sql", "mysql_refresh_final.sql"]:
        old = ROOT / "database" / name
        if old.exists():
            shutil.copy2(old, archive / name)
    write_sql_assets(ROOT)
    manifest["previous_files_archive"] = str(archive)
    report = ROOT / "docs" / f"dataset_{profile}_validation.json"
    report.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"profile": profile, "rows": manifest["row_counts"],
                      "sqlite_MB": round(manifest["sqlite_bytes"] / 1e6, 2),
                      "raw_CSV_MB": round(csv_bytes / 1e6, 2), "validation_passed": checks["passed"],
                      "report": str(report), "archive": str(archive)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["small", "final"], default="small")
    parser.add_argument("--seed", type=int, default=604)
    parser.add_argument("--populate-kpis", action="store_true", help="Compatibility option; v2 always recalculates KPIs")
    args = parser.parse_args()
    run(args.profile, args.seed)
