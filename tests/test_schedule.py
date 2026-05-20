import unittest
from datetime import date

from source.models import SummaryModule
from source.schedule import calculate_schedule, default_start_date


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
            default_start_date(date(2026, 5, 20)),
            date(2026, 5, 25)
        )


if __name__ == "__main__":
    unittest.main()
