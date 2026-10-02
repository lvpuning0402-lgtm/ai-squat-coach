import unittest

from feedback.capture_quality import RepCaptureTracker
from feedback.competition_detail import CompetitionDetailEvaluator
from feedback.insights import SessionInsightBuilder
from feedback.performance import SessionPerformanceAnalyzer
from camera.camera import format_phase_scores, _rep_detail_state


def landmarks():
    return {i: {"point": (.5, .5), "visibility": .99}
            for i in (0, 11, 12, 23, 24, 25, 26, 27, 28)}


def phase_rep(bottom_samples=5):
    metrics = dict(samples=8, max_left_inward=.04, max_right_inward=.04,
                   max_symmetry_value=.04, max_head_shift=.04,
                   max_shoulder_tilt=.04, max_hip_tilt=.04, max_center_shift=.04,
                   max_knee_angle_asymmetry=5, max_ascent_sync_error=.04)
    return {"view": "FRONT", **metrics, "total_time": 3, "descent_time": 1,
            "bottom_time": .3, "ascent_time": 1.7,
            "capture_quality": {"pose_quality": "HIGH", "view_quality": "HIGH"},
            "phase_metrics": {"descent": dict(metrics),
                              "bottom": dict(metrics, samples=bottom_samples, max_center_shift=.2),
                              "ascent": dict(metrics)}}


class CaptureEvidenceTests(unittest.TestCase):
    def test_idle_frames_do_not_inflate_rep_evidence(self):
        tracker = RepCaptureTracker()
        for _ in range(100):
            tracker.observe("FRONT", "FRONT", landmarks())
        self.assertEqual(tracker.frames, 0)
        tracker.on_result({"phase": "DESCENDING"}, "FRONT", "FRONT", landmarks())
        tracker.observe("UNKNOWN", "UNKNOWN", {})
        result = {"phase": "STANDING", "rep_completed": True, "rep_summary": {}}
        tracker.on_result(result, "FRONT", "FRONT", landmarks())
        evidence = result["rep_summary"]["capture_quality"]
        self.assertEqual(evidence["frames"], 2)
        self.assertEqual(evidence["pose_quality"], "LOW")
        self.assertIsNone(tracker.view)

    def test_side_uses_active_leg_not_occluded_far_leg(self):
        tracker = RepCaptureTracker()
        points = landmarks()
        for i in (11, 23, 25, 27):
            points[i]["visibility"] = .1
        tracker.on_result({"phase": "DESCENDING"}, "SIDE", "SIDE", points, "RIGHT")
        self.assertEqual(tracker.snapshot()["pose_quality"], "HIGH")
        points[26]["visibility"] = .1
        tracker.observe("SIDE", "SIDE", points, "RIGHT")
        self.assertEqual(tracker.snapshot()["pose_quality"], "LOW")

    def test_abort_discards_previous_capture(self):
        tracker = RepCaptureTracker()
        tracker.on_result({"phase": "DESCENDING"}, "FRONT", "FRONT", {})
        tracker.on_result({"rep_aborted": True}, "FRONT", "FRONT", {})
        tracker.on_result({"phase": "DESCENDING"}, "FRONT", "FRONT", landmarks())
        self.assertEqual(tracker.snapshot()["pose_quality"], "HIGH")
        self.assertEqual(tracker.frames, 1)

    def test_nonfinite_and_out_of_frame_points_are_not_good(self):
        for point in ((float("nan"), .5), (1.1, .5)):
            points = landmarks()
            points[0]["point"] = point
            tracker = RepCaptureTracker()
            tracker.on_result({"phase": "DESCENDING"}, "FRONT", "FRONT", points)
            self.assertEqual(tracker.snapshot()["pose_quality"], "LOW")

    def test_single_bottom_frame_does_not_establish_weakest_phase(self):
        result = CompetitionDetailEvaluator().evaluate(phase_rep(1))
        self.assertEqual(result["phase_scores"]["bottom"]["confidence"], "LOW")
        self.assertEqual(result["detail_confidence"], "LOW")
        self.assertIsNone(result["weakest_phase"])
        self.assertIsNotNone(result["detail_score"])  # diagnostics retained

    def test_complete_capture_allows_high_confidence(self):
        result = CompetitionDetailEvaluator().evaluate(phase_rep())
        self.assertEqual(result["detail_confidence"], "HIGH")
        self.assertEqual(result["weakest_phase"]["phase"], "bottom")

    def test_missing_capture_is_unknown_and_never_high(self):
        rep = phase_rep()
        del rep["capture_quality"]
        result = CompetitionDetailEvaluator().evaluate(rep)
        self.assertEqual(result["confidence_breakdown"]["pose_quality"], "UNKNOWN")
        self.assertEqual(result["detail_confidence"], "MEDIUM")

    def test_poor_capture_does_not_change_raw_score_but_blocks_comparison(self):
        rep = phase_rep()
        good = CompetitionDetailEvaluator().evaluate(rep)
        rep["capture_quality"]["view_quality"] = "LOW"
        poor = CompetitionDetailEvaluator().evaluate(rep)
        self.assertEqual(good["detail_score"], poor["detail_score"])
        self.assertIsNone(poor["weakest_phase"])
        self.assertTrue(all(p["confidence"] == "LOW" for p in poor["phase_scores"].values()))

    def test_many_low_evidence_reps_do_not_make_confident_coach(self):
        reps = [dict(phase_rep(), detail_confidence="LOW", standard_met=True,
                     analysis_valid=True, set_valid=True) for _ in range(6)]
        coach = SessionInsightBuilder().build(reps, {})
        self.assertEqual(coach["confidence"], "LOW")
        self.assertEqual(coach["selected_focus"], "CAPTURE_QUALITY")
        self.assertIsNone(coach["next_set_goal"]["affected_reps"])
        self.assertNotIn("stable", " ".join(coach["ui_lines"]))

    def test_set_compares_same_usable_reps_across_all_phases(self):
        analyzer = SessionPerformanceAnalyzer()
        analyzer.analyze_rep(dict(phase_rep(), rep=1))
        bad = phase_rep(1)
        bad["phase_metrics"]["descent"]["max_center_shift"] = 1
        analyzer.analyze_rep(dict(bad, rep=2))
        summary = analyzer.get_set_summary()
        self.assertEqual(summary["phase_comparable_reps"], 1)
        self.assertEqual(summary["phase_excluded_reps"], 1)
        self.assertEqual(summary["weakest_phase"]["phase"], "bottom")
        self.assertEqual(summary["best_detail_rep"], 1)

    def test_uncertain_phase_ui_avoids_false_precision(self):
        self.assertEqual(format_phase_scores({
            "descent": {"score": 91.3, "confidence": "HIGH"},
            "bottom": {"score": 73.6, "confidence": "LOW"},
            "ascent": {"score": 83.6, "confidence": "MEDIUM"}}),
            "91.3 / -- [LOW] / ~84")
        self.assertEqual(_rep_detail_state({"detail_confidence": "LOW"})[0], "UNSURE")
