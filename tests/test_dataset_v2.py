"""Check request identity, repeat-contact aggregation and deterministic generation."""

import hashlib
import json
import sqlite3
import sys
import unittest
from collections import defaultdict
from contextlib import closing
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from practicehub.dataset_v2 import build, schema_sql, KPI_SELECT, validate, intake_schedule, holidays
from datetime import date,timedelta


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables,cls.meta=build("small",604)

    def connection(self):
        conn=sqlite3.connect(":memory:")
        conn.executescript(schema_sql("sqlite"))
        for table,rows in self.tables.items():
            if rows:
                columns=list(rows[0])
                conn.executemany(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                                 [tuple(r[c] for c in columns) for r in rows])
        conn.execute("CREATE VIEW vw_monthly_core_kpis AS "+KPI_SELECT)
        conn.execute("INSERT INTO monthly_kpis SELECT * FROM vw_monthly_core_kpis")
        return conn

    def test_same_seed_same_records(self):
        second,_=build("small",604)
        digest=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest(self.tables),digest(second))

    def test_retired_result_tables_are_not_recreated(self):
        for name in ("forecast_results", "model_evaluations"):
            self.assertNotIn(name, self.tables)
            self.assertNotIn(f"CREATE TABLE {name}", schema_sql("mysql"))
            self.assertNotIn(f"CREATE TABLE {name}", schema_sql("sqlite"))

    def test_pathways_have_variable_mix_and_distinct_monthly_changes(self):
        days=[date(2024,1,1)+timedelta(days=i) for i in range(366)]
        days=[d for d in days if d.weekday()<5 and d not in holidays(2024)]
        monthly=defaultdict(lambda:defaultdict(int))
        for day,counts in intake_schedule(days,604,1).items():
            for kind,count in counts.items():
                monthly[day.month][kind]+=count
        shares=[monthly[m]['Same-day GP']/(monthly[m]['Same-day GP']+monthly[m]['Routine GP']) for m in range(1,13)]
        self.assertGreater(max(shares)-min(shares),.05)
        self.assertTrue(any((monthly[m]['Same-day GP']-monthly[m-1]['Same-day GP'])*
                            (monthly[m]['Routine GP']-monthly[m-1]['Routine GP'])<0 for m in range(2,13)))

    def test_duplicate_contact_not_duplicate_demand(self):
        with closing(self.connection()) as c:
            before=c.execute("SELECT SUM(gp_requests),SUM(morning_call_gp_requests),SUM(incoming_calls_offered) FROM vw_monthly_core_kpis").fetchone()
            original=c.execute("SELECT * FROM incoming_call_events WHERE request_id IS NOT NULL LIMIT 1").fetchone()
            copy=list(original)
            copy[0]=999999
            c.execute("INSERT INTO incoming_call_events VALUES ("+','.join('?' for _ in copy)+")",copy)
            after=c.execute("SELECT SUM(gp_requests),SUM(morning_call_gp_requests),SUM(incoming_calls_offered) FROM vw_monthly_core_kpis").fetchone()
            self.assertEqual(before[:2],after[:2])
            self.assertEqual(before[2]+1,after[2])

    def test_valid_data_and_detect_patient_corruption(self):
        with closing(self.connection()) as c:
            self.assertTrue(validate(c,self.meta)["passed"])
            c.execute("UPDATE appointments SET patient_id=CASE WHEN patient_id=1 THEN 2 ELSE 1 END WHERE appointment_id=1")
            result=validate(c,self.meta)
            self.assertFalse(result["passed"])
            self.assertEqual(result["appointment_patient_mismatch"],1)

    def test_complaints_do_not_become_requests(self):
        with closing(self.connection()) as c:
            before=c.execute("SELECT SUM(gp_requests) FROM vw_monthly_core_kpis").fetchone()[0]
            row=list(c.execute("SELECT * FROM patient_complaints LIMIT 1").fetchone())
            row[0]=999999
            c.execute("INSERT INTO patient_complaints VALUES ("+','.join('?' for _ in row)+")",row)
            after=c.execute("SELECT SUM(gp_requests) FROM vw_monthly_core_kpis").fetchone()[0]
            self.assertEqual(before,after)


if __name__=='__main__':
    unittest.main()
