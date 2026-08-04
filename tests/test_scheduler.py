import copy
import unittest

from peripatetic_timetable.models import RebalanceRequest
from peripatetic_timetable.scheduler import RebalanceEngine, subjects_compatible
from peripatetic_timetable.storage import load_baseline

class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.data = load_baseline()

    def test_pe_and_pe_rsp_are_compatible(self):
        self.assertTrue(subjects_compatible("PE", "PE/RSP"))
        self.assertFalse(subjects_compatible("Art", "Music"))

    def test_current_school_detects_baseline_assignment(self):
        self.assertEqual(RebalanceEngine(self.data).current_school("Rebecca Bonello", "Monday"), "Attard")

    def test_batch_swap_moves_both_teachers(self):
        result = RebalanceEngine(self.data).solve_batch([RebalanceRequest("Rebecca Bonello", "Monday")])
        self.assertTrue(result.succeeded, result.error)
        change = result.changes[0]
        engine = RebalanceEngine(result.data)
        self.assertEqual(engine.current_school("Rebecca Bonello", "Monday"), change.target_school)
        self.assertEqual(engine.current_school(change.swap_teacher, "Monday"), "Attard")

    def test_lock_blocks_teacher_removal(self):
        data = copy.deepcopy(self.data)
        data["locks"].append({"teacher": "Rebecca Bonello", "day": "Monday", "school": "Attard"})
        result = RebalanceEngine(data).solve_batch([RebalanceRequest("Rebecca Bonello", "Monday")])
        self.assertFalse(result.succeeded)
        self.assertIn("locked", result.error)

    def test_restrictions_apply_only_on_selected_days(self):
        data = copy.deepcopy(self.data)
        data["teacher_restrictions"].append(
            {"teacher": "Rebecca Bonello", "school": "Dingli", "days": "Monday", "reason": "test"})
        engine = RebalanceEngine(data)
        self.assertTrue(engine._is_restricted("Rebecca Bonello", "Dingli", "Monday", data))
        self.assertFalse(engine._is_restricted("Rebecca Bonello", "Dingli", "Tuesday", data))

    def test_weekly_rule_can_block_all_candidates(self):
        data = copy.deepcopy(self.data)
        data["weekly_rules"].append(
            {"teacher": "Rebecca Bonello", "school": "Attard", "type": "EXACT", "times": 5})
        result = RebalanceEngine(data).solve_batch([RebalanceRequest("Rebecca Bonello", "Monday")])
        self.assertFalse(result.succeeded)

if __name__ == "__main__":
    unittest.main()
