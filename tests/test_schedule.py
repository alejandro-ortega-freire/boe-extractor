import unittest
from datetime import date
from tempfile import TemporaryDirectory
from pathlib import Path

from source.models import SummaryModule
from source.holiday_workbook import (
    CUSTOM_HOLIDAY_PLACEHOLDER,
    load_custom_holidays,
    write_holiday_template,
)
from source.schedule import calculate_schedule, default_start_date, format_holiday_note


class ScheduleTests(unittest.TestCase):
    def test_partial_session_carries_hours_to_next_item(self):
        modules = [
            SummaryModule(text="MF0001_1: Primer módulo (50 horas)", ufs=[]),
            SummaryModule(text="MF0002_1: Segundo módulo (10 horas)", ufs=[]),
        ]

        schedule = calculate_schedule(modules, 6, date(2026, 5, 25))

        self.assertEqual(schedule["dates_by_code"]["MF0001_1"]["text"], "25/05/2026 - 04/06/2026 (2)")
        self.assertEqual(schedule["dates_by_code"]["MF0002_1"]["text"], "04/06/2026 (4) - 05/06/2026")

    def test_default_start_date_is_next_working_monday(self):
        self.assertEqual(
            default_start_date(date(2026, 5, 20), custom_holidays={}),
            date(2026, 5, 25)
        )

    def test_custom_holidays_xlsx_supports_optional_name(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "festivos.xlsx"
            write_holiday_template(
                path,
                data_rows=[
                    ("24/06/2026", "San Juan"),
                    ("09/09/2026", ""),
                ],
            )

            holidays = load_custom_holidays(path)

        self.assertEqual(holidays[date(2026, 6, 24)], "San Juan")
        self.assertEqual(holidays[date(2026, 9, 9)], CUSTOM_HOLIDAY_PLACEHOLDER)

    def test_custom_holidays_are_skipped_and_listed_in_note(self):
        modules = [
            SummaryModule(text="MF0001_1: Primer módulo (12 horas)", ufs=[]),
        ]
        custom_holidays = {
            date(2026, 5, 26): "Festivo personalizado",
        }

        schedule = calculate_schedule(
            modules,
            6,
            date(2026, 5, 25),
            custom_holidays=custom_holidays,
        )

        self.assertEqual(schedule["dates_by_code"]["MF0001_1"]["text"], "25/05/2026 - 27/05/2026")
        self.assertIn(
            "26/05/2026 (Festivo personalizado)",
            format_holiday_note(schedule)
        )


if __name__ == "__main__":
    unittest.main()
