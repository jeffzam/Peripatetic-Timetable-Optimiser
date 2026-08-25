import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openpyxl import load_workbook

from peripatetic_timetable.exports import export_excel
from peripatetic_timetable.repository import TimetableRepository


class ExcelExportTests(unittest.TestCase):
    def test_excel_export_contains_all_reports_and_complete_timetable(self):
        timetable = TimetableRepository().load_baseline()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "timetable.xlsx"
            export_excel(timetable, path)
            workbook = load_workbook(path, read_only=True)
            self.assertEqual(
                workbook.sheetnames,
                [
                    "Timetable",
                    "Teacher Movement",
                    "Coverage Audit",
                    "Policy Audit",
                    "Staffing Notes",
                    "Change Log",
                ],
            )
            sheet = workbook["Timetable"]
            self.assertEqual(sheet["A4"].value, "Attard")
            self.assertEqual(sheet["B4"].value, "20 classes")
            self.assertIn("Rebecca Bonello", sheet["C4"].value)
            self.assertEqual(sheet.max_row, 9)
            self.assertEqual(sheet.max_column, 7)
            workbook.close()


if __name__ == "__main__":
    unittest.main()
