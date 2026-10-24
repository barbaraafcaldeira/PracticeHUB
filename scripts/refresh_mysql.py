#!/usr/bin/env python3
"""Back up MySQL and import validated v2 CSVs using the existing connection test file."""

import contextlib
import csv
import gzip
import io
import json
import runpy
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, inspect

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from practicehub.dataset_v2 import TABLES, INDEXES, KPI_SELECT, VALIDATION_QUERIES


def refresh():
    manifest=json.loads((ROOT/"docs/dataset_final_validation.json").read_text())
    if not manifest["validation"]["passed"]:
        raise RuntimeError("Local validation must pass before importing")
    import hashlib
    for filename,expected in manifest["csv_sha256"].items():
        csv_path=ROOT/"data"/("processed" if filename.startswith("processed/") else "raw")/"final"/Path(filename).name
        if hashlib.sha256(csv_path.read_bytes()).hexdigest()!=expected:
            raise RuntimeError(f"CSV changed after validation: {csv_path.name}")
    # Reuse the user's configured engine, without logging connection secrets.
    with contextlib.redirect_stdout(io.StringIO()):
        scope=runpy.run_path(str(ROOT/"analysis_code/01_connect_to_mysql.py"))
    old_engine=scope["engine"]
    if old_engine.url.database!='practicehub':
        raise RuntimeError("Existing connection must point to practicehub")
    engine=create_engine(old_engine.url,connect_args={"local_infile":True})
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup=ROOT/"data/archives"/stamp/"practicehub_mysql_before_v2.sql.gz"
    backup.parent.mkdir(parents=True)
    # A native SQL backup includes existing table definitions, data and views.
    raw=engine.raw_connection()
    driver=raw.driver_connection
    cursor=driver.cursor()
    cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT")
    catalog=inspect(engine)
    names=catalog.get_table_names()
    views=catalog.get_view_names()
    with gzip.open(backup,"wt",encoding="utf-8") as f:
        f.write("USE practicehub;\nSET FOREIGN_KEY_CHECKS=0;\n")
        for view in views:
            f.write(f"DROP VIEW IF EXISTS `{view}`;\n")
        for name in reversed(names):
            f.write(f"DROP TABLE IF EXISTS `{name}`;\n")
        for name in names:
            cursor.execute(f"SHOW CREATE TABLE `{name}`")
            f.write(cursor.fetchone()[1]+";\n")
            cursor.execute(f"SELECT * FROM `{name}`")
            while True:
                rows=cursor.fetchmany(500)
                if not rows:
                    break
                values=",".join(driver.literal(tuple(row)) for row in rows)
                f.write(f"INSERT INTO `{name}` VALUES {values};\n")
        for view in views:
            cursor.execute(f"SHOW CREATE VIEW `{view}`")
            f.write(cursor.fetchone()[1]+";\n")
        f.write("SET FOREIGN_KEY_CHECKS=1;\n")
    driver.commit()
    print("MySQL backup:",backup,flush=True)
    cursor.execute("SELECT @@GLOBAL.local_infile")
    old_local=cursor.fetchone()[0]
    if not old_local:
        cursor.execute("SET GLOBAL local_infile=1")
    try:
        # Drop only project-owned views and tables, child first.
        for view in ["vw_executive_kpis_latest_month","vw_monthly_gp_capacity","vw_monthly_econsults",
                     "vw_monthly_telephone","vw_monthly_access_complaints","vw_monthly_outgoing_calls","vw_monthly_core_kpis"]:
            cursor.execute(f"DROP VIEW IF EXISTS {view}")
        for table in reversed(TABLES):
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        for table,fields in TABLES.items():
            cursor.execute(f"CREATE TABLE {table} ({fields}) ENGINE=InnoDB")
        for name,(table,cols) in INDEXES.items():
            cursor.execute(f"CREATE INDEX {name} ON {table} ({cols})")
        local=sqlite3.connect(ROOT/"database/practicehub_final.sqlite")
        for table in TABLES:
            if table=='monthly_kpis':
                continue
            cols=[r[1] for r in local.execute(f"PRAGMA table_info({table})")]
            path=str(ROOT/"data/raw/final"/(table+'.csv'))
            variables=', '.join('@'+c for c in cols)
            setters=', '.join(c+"=NULLIF(@"+c+",'')" for c in cols)
            statement=f"""LOAD DATA LOCAL INFILE %s INTO TABLE {table}
                CHARACTER SET utf8mb4 FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
                LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES ({variables}) SET {setters}"""
            cursor.execute(statement,(path,))
            warning_count=cursor.warning_count
            if warning_count:
                raise RuntimeError(f"Import warnings for {table}: {warning_count}; backup retained at {backup}")
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            actual=cursor.fetchone()[0]
            if actual!=manifest['row_counts'][table]:
                raise RuntimeError(f"Row-count mismatch for {table}")
            print(table,actual,flush=True)
        # SQL assets are generated; execute the view and refresh portions separately.
        cursor.execute("CREATE VIEW vw_monthly_core_kpis AS "+KPI_SELECT)
        for name in ["vw_monthly_gp_capacity","vw_monthly_econsults","vw_monthly_telephone",
                     "vw_monthly_access_complaints","vw_monthly_outgoing_calls"]:
            cursor.execute(f"CREATE VIEW {name} AS SELECT * FROM vw_monthly_core_kpis")
        cursor.execute("CREATE VIEW vw_executive_kpis_latest_month AS SELECT * FROM vw_monthly_core_kpis WHERE kpi_month=(SELECT MAX(kpi_month) FROM vw_monthly_core_kpis)")
        cursor.execute("INSERT INTO monthly_kpis SELECT * FROM vw_monthly_core_kpis")
        driver.commit()
        errors={}
        for name,query in VALIDATION_QUERIES.items():
            cursor.execute(query)
            errors[name]=cursor.fetchone()[0]
        cursor.execute("SELECT * FROM monthly_kpis ORDER BY kpi_month")
        live=cursor.fetchall()
        expected=local.execute("SELECT * FROM monthly_kpis ORDER BY kpi_month").fetchall()
        errors['monthly_kpi_parity']=sum(any(str(a)!=str(b) if isinstance(a,str) else
                                           (a is None)!=(b is None) or (a is not None and abs(float(a)-float(b))>.001)
                                           for a,b in zip(x,y)) for x,y in zip(live,expected))+abs(len(live)-len(expected))
        if any(errors.values()):
            raise RuntimeError("MySQL validation failed: "+json.dumps(errors))
        report={"version":manifest['version'],"passed":True,"checks":errors,"monthly_rows":len(live),
                "backup":str(backup),"csv_sha256":manifest['csv_sha256']}
        (ROOT/"docs/mysql_refresh_validation.json").write_text(json.dumps(report,indent=2)+"\n")
        local.close()
        print("MySQL refresh and KPI parity validation passed",flush=True)
    finally:
        if not old_local:
            cursor.execute("SET GLOBAL local_infile=0")
        cursor.close()
        raw.close()
        engine.dispose()
        old_engine.dispose()


if __name__=='__main__':
    try:
        refresh()
    except Exception as error:
        # Driver errors may include connection details; never print engine URLs or passwords.
        print("Refresh stopped:",type(error).__name__,str(error) if isinstance(error,RuntimeError) else "See the retained backup; no connection secrets displayed.")
        raise SystemExit(1)
