"""Capture evidence, separate from movement scores (engineering heuristics)."""
import math

PHASES = ("descent", "bottom", "ascent")
RANK = {"UNKNOWN": 0, "LOW": 0, "MEDIUM": 1, "HIGH": 2}


def weakest_confidence(labels):
    return min(labels, key=lambda label: RANK.get(label, 0), default="LOW")


def rate_label(rate):
    return "HIGH" if rate >= .95 else "MEDIUM" if rate >= .80 else "LOW"


class RepCaptureTracker:
    """Track only an active rep; waiting/standing frames cannot inflate quality."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.view = None
        self.frames = self.pose_good = self.view_good = 0
        self.gap = self.max_gap = 0

    def observe(self, view, raw_view, landmarks, active_leg=None):
        if self.view is None:
            return
        self.frames += 1
        self.view_good += view == self.view and raw_view == self.view
        indices = [0, 11, 12, 23, 24, 25, 26, 27, 28]
        if self.view == "SIDE":
            indices = [0, 12, 24, 26, 28] if active_leg == "RIGHT" else [0, 11, 23, 25, 27]
        def visible(index):
            item = landmarks.get(index) or {}
            point = item.get("point", ())
            visibility = item.get("visibility", 0)
            return (isinstance(visibility, (int, float)) and math.isfinite(visibility)
                    and visibility >= .60 and len(point) == 2
                    and all(math.isfinite(v) and 0 <= v <= 1 for v in point))
        good = all(visible(index) for index in indices)
        self.pose_good += good
        self.gap = 0 if good else self.gap + 1
        self.max_gap = max(self.max_gap, self.gap)

    def on_result(self, result, view, raw_view, landmarks, active_leg=None):
        if not result:
            return
        if result.get("rep_aborted") or result.get("baseline_reset"):
            self.reset()
            return
        if self.view is None and result.get("phase") in ("DESCENDING", "BOTTOM", "ASCENDING"):
            self.view = view
            self.observe(view, raw_view, landmarks, active_leg)
        if result.get("rep_completed"):
            if result.get("rep_summary") is not None:
                result["rep_summary"]["capture_quality"] = self.snapshot()
            self.reset()

    def snapshot(self):
        pose_rate = self.pose_good / self.frames if self.frames else 0
        view_rate = self.view_good / self.frames if self.frames else 0
        return {"version": 1, "frames": self.frames,
                "pose_good_fraction": round(pose_rate, 4),
                "view_good_fraction": round(view_rate, 4),
                "max_low_visibility_run": self.max_gap,
                "pose_quality": rate_label(pose_rate),
                "view_quality": rate_label(view_rate)}


def assess_evidence(rep, result):
    capture = rep.get("capture_quality") or {}
    pose = capture.get("pose_quality", "UNKNOWN")
    view = capture.get("view_quality", "UNKNOWN")
    pose = pose if pose in RANK else "UNKNOWN"
    view = view if view in RANK else "UNKNOWN"
    phases = result.get("phase_scores", {})
    phase = weakest_confidence([phases.get(p, {}).get("confidence", "LOW") for p in PHASES])
    coverage = result.get("detail_coverage", 0)
    metric = "HIGH" if coverage >= .9 else "MEDIUM" if coverage >= .7 else "LOW"
    # Legacy reports have no capture telemetry: unknown is never promoted to HIGH.
    overall = weakest_confidence(["MEDIUM" if x == "UNKNOWN" else x
                                   for x in (pose, view, phase, metric)])
    reasons = list(dict.fromkeys(
        reason for data in phases.values()
        for reason in data.get("confidence_reasons", [])
    ))
    if pose == "UNKNOWN" or view == "UNKNOWN":
        reasons.append("CAPTURE_TELEMETRY_MISSING")
    if pose == "LOW":
        reasons.append("POSE_VISIBILITY_LOW")
    if view == "LOW":
        reasons.append("VIEW_UNSTABLE")
    sampling = weakest_confidence([
        "LOW" if phases.get(p, {}).get("samples", 0) < 2 else
        "HIGH" if phases[p]["samples"] >= (2 if p == "bottom" else 4) else "MEDIUM"
        for p in PHASES
    ])
    if sampling != "HIGH":
        reasons.append("PHASE_CAPTURE_INCOMPLETE" if sampling == "LOW" else "PHASE_CAPTURE_LIMITED")
    if any(data.get("coverage", 0) < .7 for data in phases.values()):
        reasons.append("PHASE_METRIC_COVERAGE_LIMITED")
    if metric != "HIGH":
        reasons.append("METRIC_COVERAGE_LIMITED")
    return {"pose_quality": pose, "view_quality": view, "phase_capture": sampling, "phase_assessment": phase,
            "metric_coverage": metric, "overall": overall, "reasons": reasons}


def assessment_limited(rep):
    """Only attribute LOW to the model when capture and timing are evidenced."""
    evidence = rep.get("confidence_breakdown", {})
    reasons = set(evidence.get("reasons", []))
    allowed = {"TRUNK_RANGE_DIAGNOSTIC_ONLY", "PHASE_ALIGNMENT_HEURISTIC",
               "PHASE_METRIC_COVERAGE_LIMITED"}
    return (rep.get("detail_confidence") == "LOW"
            and all(evidence.get(key) == "HIGH"
                    for key in ("pose_quality", "view_quality", "phase_capture"))
            and rep.get("phase_alignment", {}).get("status") == "ALIGNED"
            and "PHASE_METRIC_COVERAGE_LIMITED" in reasons
            and reasons <= allowed)
