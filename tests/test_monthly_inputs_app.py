"""Presentation workflow test, with all writes redirected to an isolated database."""

from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))
from practicehub.dashboard import read_database
from practicehub.monthly_inputs import read_corrections, read_inputs

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


@unittest.skipIf(AppTest is None, "Requires the dashboard environment")
class MonthlyInputAppTests(unittest.TestCase):
    def test_save_january_generate_february_and_use_capacity_without_live_database_writes(self):
        import monthly_inputs_ui
        data = read_database("SQLite")
        engine = create_engine("sqlite:///:memory:", poolclass=StaticPool,
                               connect_args={"check_same_thread": False})
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"PRACTICEHUB_SOURCE": "MySQL"}), \
                 patch("practicehub.dashboard.read_database", return_value=data), \
                 patch("monthly_inputs_ui.mysql_engine", return_value=engine), \
                 patch.object(engine, "dispose"), \
                 patch("practicehub.monthly_inputs.ROOT", Path(folder)):
                monthly_inputs_ui.monthly_inputs.clear()
                app = AppTest.from_file(str(ROOT / "app" / "PracticeHUB.py"), default_timeout=60).run()
                app.radio(key="page").set_value("Monthly inputs").run()
                self.assertFalse(app.exception)
                next(item for item in app.number_input if item.label == "Same-day GP requests").set_value(2400)
                next(item for item in app.number_input if item.label == "Routine GP requests").set_value(850)
                next(item for item in app.checkbox if item.label == "Counts cover the entire completed month").set_value(True)
                next(item for item in app.button if item.label == "Save completed month").click().run()
                self.assertFalse(app.exception)
                self.assertEqual(len(read_inputs(engine)), 1)
                self.assertIn("Generate February 2026 forecast", [header.value for header in app.subheader])
                next(item for item in app.checkbox if item.label == "Planned opening calendar confirmed").set_value(True)
                next(item for item in app.button if item.label == "Generate forecast").click().run()
                self.assertFalse(app.exception)
                self.assertFalse(app.error)
                self.assertTrue(any("Generated February 2026" in item.value for item in app.success))
                app.radio(key="page").set_value("Next-month forecast").run()
                self.assertFalse(app.exception)
                self.assertTrue(any("January 2026" in item.value for item in app.success))
                app.radio(key="page").set_value("Session calculator").run()
                self.assertFalse(app.exception)
                self.assertFalse(app.error)
                self.assertEqual(len(read_inputs(engine)), 1)
                app.radio(key="page").set_value("Monthly inputs").run()
                next(item for item in app.number_input if item.label == "Corrected routine GP requests").set_value(900)
                next(item for item in app.text_input if item.label == "Reason for correction").set_value("Correct January total")
                next(item for item in app.checkbox if item.label == "I confirm these corrected totals cover the entire completed month").set_value(True)
                next(item for item in app.button if item.label == "Save correction").click().run()
                self.assertFalse(app.exception)
                self.assertFalse(app.error)
                self.assertEqual(read_inputs(engine).routine_gp_requests.iloc[0], 900)
                self.assertEqual(len(read_corrections(engine)), 1)
                app.radio(key="page").set_value("Session calculator").run()
                self.assertFalse(app.exception)
                self.assertTrue(any("has not been generated" in item.value for item in app.warning))
                monthly_inputs_ui.monthly_inputs.clear()
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
