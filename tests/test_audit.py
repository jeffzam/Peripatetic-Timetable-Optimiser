import unittest

from peripatetic_timetable.audit import Severity, audit_timetable
from peripatetic_timetable.policy import DEFAULT_POLICY
from peripatetic_timetable.repository import TimetableRepository


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.timetable = TimetableRepository().load_baseline()

    def test_source_conflict_and_missing_day_are_visible(self):
        issues = audit_timetable(self.timetable)
        codes = {(item.code, item.teacher, item.day) for item in issues}
        self.assertIn(("DOUBLE_BOOKED", "Alisichia", "Thursday"), codes)
        self.assertTrue(
            any(item.code == "MISSING_DAY" and item.teacher == "Alisichia" for item in issues)
        )

    def test_pe_rsp_capacity_formula(self):
        self.assertEqual(DEFAULT_POLICY.required_pe_rsp_days(6), 2)
        self.assertEqual(DEFAULT_POLICY.required_pe_rsp_days(12), 4)
        self.assertEqual(DEFAULT_POLICY.required_pe_rsp_days(20), 7)

    def test_baseline_has_no_pe_rsp_capacity_error(self):
        issues = audit_timetable(self.timetable)
        self.assertFalse(
            any(
                item.code == "PE_RSP_CAPACITY" and item.severity == Severity.ERROR
                for item in issues
            )
        )


if __name__ == "__main__":
    unittest.main()
