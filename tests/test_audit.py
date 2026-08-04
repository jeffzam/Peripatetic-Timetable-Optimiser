import unittest

from peripatetic_timetable.audit import Severity, audit_timetable, teacher_has_full_name
from peripatetic_timetable.policy import DEFAULT_POLICY
from peripatetic_timetable.repository import TimetableRepository


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.timetable = TimetableRepository().load_baseline()

    def test_corrected_baseline_has_complete_daily_coverage(self):
        issues = audit_timetable(self.timetable)
        self.assertFalse(any(item.code == "DOUBLE_BOOKED" for item in issues))
        self.assertFalse(any(item.code == "MISSING_DAY" for item in issues))

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

    def test_single_name_teacher_is_flagged_for_correction(self):
        issues = audit_timetable(self.timetable)
        issue = next(item for item in issues if item.code == "INCOMPLETE_TEACHER_NAME")
        self.assertEqual(issue.teacher, "Alisichia")
        self.assertEqual(issue.severity, Severity.ERROR)
        self.assertFalse(teacher_has_full_name("Alisichia"))
        self.assertTrue(teacher_has_full_name("Example Teacher"))


if __name__ == "__main__":
    unittest.main()
