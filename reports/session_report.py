import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean

from feedback.insights import SessionInsightBuilder


class SessionReportExporter:
    """
    导出单次训练报告。

    报告用于训练回顾与开发测试，不用于医学诊断。
    """

    def __init__(
        self,
        output_dir="reports"
    ):
        self.output_dir = Path(
            output_dir
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    @staticmethod
    def _safe_number(
        value
    ):
        if value is None:
            return None

        try:
            return round(
                float(value),
                4
            )
        except (
            TypeError,
            ValueError
        ):
            return value

    @staticmethod
    def _average(
        values
    ):
        cleaned = [
            float(value)
            for value in values
            if value is not None
        ]

        if not cleaned:
            return None

        return round(
            mean(cleaned),
            2
        )

    def build_report(
        self,
        session_id,
        reps,
        summary,
        session_type="TEST",
        diagnostics=None
    ):
        issue_counter = Counter()
        view_counter = Counter()
        scores_by_view = defaultdict(
            list
        )
        tempos_by_view = defaultdict(
            list
        )

        for rep in reps:
            view = rep.get(
                "view",
                "UNKNOWN"
            )

            view_counter[
                view
            ] += 1

            score = rep.get(
                "quality_score"
            )

            if score is not None:
                scores_by_view[
                    view
                ].append(
                    score
                )

            total_time = rep.get(
                "total_time"
            )

            if (
                total_time is not None
                and total_time > 0
            ):
                tempos_by_view[
                    view
                ].append(
                    total_time
                )

            issue_counter.update(
                rep.get(
                    "issues",
                    []
                )
            )

        view_summary = {}

        all_views = sorted(
            set(
                list(
                    view_counter.keys()
                )
                + list(
                    scores_by_view.keys()
                )
            )
        )

        for view in all_views:
            view_summary[
                view
            ] = {
                "reps": view_counter[
                    view
                ],
                "average_score": self._average(
                    scores_by_view[
                        view
                    ]
                ),
                "average_total_time": self._average(
                    tempos_by_view[
                        view
                    ]
                )
            }

        report_context = (
            "TEST_PROTOCOL"
            if session_type == "TEST"
            else "TRAINING_SESSION"
        )

        summary_note = (
            "TEST session: consistency and trend are descriptive only "
            "and may be intentionally distorted by protocol changes."
            if session_type == "TEST"
            else (
                "TRAINING session: consistency and trend can be used "
                "for within-set review."
            )
        )

        coach_feedback = SessionInsightBuilder().build(
            reps,
            summary,
            session_type=session_type
        )

        return {
            "report_version": 1,
            "session_id": session_id,
            "session_type": session_type,
            "report_context": report_context,
            "generated_at": datetime.now().isoformat(
                timespec="seconds"
            ),
            "summary": summary,
            "summary_note": summary_note,
            "coach_feedback": coach_feedback,
            "view_summary": view_summary,
            "issue_counts": dict(
                issue_counter
            ),
            "diagnostics": diagnostics or {},
            "reps": reps,
            "note": (
                "Training feedback only; "
                "not a medical diagnosis."
            )
        }

    def export_json(
        self,
        report,
        stem
    ):
        path = (
            self.output_dir
            / f"{stem}.json"
        )

        with path.open(
            "w",
            encoding="utf-8"
        ) as handle:
            json.dump(
                report,
                handle,
                ensure_ascii=False,
                indent=2
            )

        return path

    def export_csv(
        self,
        report,
        stem
    ):
        path = (
            self.output_dir
            / f"{stem}.csv"
        )

        fieldnames = [
            "rep",
            "view",
            "analysis_valid",
            "confidence_reasons",
            "set_valid",
            "set_exclusion_reasons",
            "standard_profile",
            "standard_scope",
            "standard_met",
            "standard_score",
            "quality_score",
            "quality_label",
            "detail_profile",
            "detail_score",
            "detail_grade",
            "detail_label",
            "detail_warnings",
            "competition_flags",
            "physique_control_score",
            "ipf_proxy_score",
            "descent_time",
            "bottom_time",
            "ascent_time",
            "total_time",
            "issues",
            "min_knee_angle",
            "min_hip_angle",
            "max_trunk_lean",
            "trunk_rom_ratio",
            "max_head_forward",
            "max_ascent_sync_error",
            "max_depth_margin",
            "depth_standard_met",
            "ipf_depth_proxy_met",
            "max_head_shift",
            "max_shoulder_tilt",
            "max_hip_tilt",
            "max_knee_angle_asymmetry",
            "max_center_shift",
            "max_sync_error",
            "max_left_inward",
            "max_right_inward",
            "max_symmetry_value",
            "max_knee_angle",
            "shin_angle_at_min_knee"
        ]

        with path.open(
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames
            )

            writer.writeheader()

            for rep in report[
                "reps"
            ]:
                row = {
                    "rep": rep.get(
                        "rep"
                    ),
                    "view": rep.get(
                        "view"
                    ),
                    "analysis_valid": rep.get(
                        "analysis_valid",
                        True
                    ),
                    "confidence_reasons": "|".join(
                        rep.get(
                            "confidence_reasons",
                            []
                        )
                    ),
                    "set_valid": rep.get(
                        "set_valid",
                        True
                    ),
                    "set_exclusion_reasons": "|".join(
                        rep.get(
                            "set_exclusion_reasons",
                            []
                        )
                    ),
                    "standard_profile": rep.get(
                        "standard_profile"
                    ),
                    "standard_scope": rep.get(
                        "standard_scope"
                    ),
                    "standard_met": rep.get(
                        "standard_met"
                    ),
                    "standard_score": self._safe_number(
                        rep.get(
                            "standard_score"
                        )
                    ),
                    "quality_score": self._safe_number(
                        rep.get(
                            "quality_score"
                        )
                    ),
                    "quality_label": rep.get(
                        "quality_label"
                    ),
                    "detail_profile": rep.get(
                        "detail_profile"
                    ),
                    "detail_score": self._safe_number(
                        rep.get(
                            "detail_score"
                        )
                    ),
                    "detail_grade": rep.get(
                        "detail_grade"
                    ),
                    "detail_label": rep.get(
                        "detail_label"
                    ),
                    "detail_warnings": "|".join(
                        rep.get(
                            "detail_warnings",
                            []
                        )
                    ),
                    "competition_flags": "|".join(
                        rep.get(
                            "competition_flags",
                            []
                        )
                    ),
                    "physique_control_score": self._safe_number(
                        rep.get(
                            "competition_lenses",
                            {}
                        ).get(
                            "physique_control",
                            {}
                        ).get(
                            "score"
                        )
                    ),
                    "ipf_proxy_score": self._safe_number(
                        rep.get(
                            "competition_lenses",
                            {}
                        ).get(
                            "ipf_squat_proxy",
                            {}
                        ).get(
                            "score"
                        )
                    ),
                    "descent_time": self._safe_number(
                        rep.get(
                            "descent_time"
                        )
                    ),
                    "bottom_time": self._safe_number(
                        rep.get(
                            "bottom_time"
                        )
                    ),
                    "ascent_time": self._safe_number(
                        rep.get(
                            "ascent_time"
                        )
                    ),
                    "total_time": self._safe_number(
                        rep.get(
                            "total_time"
                        )
                    ),
                    "issues": "|".join(
                        rep.get(
                            "issues",
                            []
                        )
                    ),
                    "min_knee_angle": self._safe_number(
                        rep.get(
                            "min_knee_angle"
                        )
                    ),
                    "min_hip_angle": self._safe_number(
                        rep.get(
                            "min_hip_angle"
                        )
                    ),
                    "max_trunk_lean": self._safe_number(
                        rep.get(
                            "max_trunk_lean"
                        )
                    ),
                    "trunk_rom_ratio": self._safe_number(
                        rep.get(
                            "trunk_rom_ratio"
                        )
                    ),
                    "max_head_forward": self._safe_number(
                        rep.get(
                            "max_head_forward"
                        )
                    ),
                    "max_ascent_sync_error": self._safe_number(
                        rep.get(
                            "max_ascent_sync_error"
                        )
                    ),
                    "max_depth_margin": self._safe_number(
                        rep.get(
                            "max_depth_margin"
                        )
                    ),
                    "depth_standard_met": rep.get(
                        "depth_standard_met"
                    ),
                    "ipf_depth_proxy_met": rep.get(
                        "ipf_depth_proxy_met"
                    ),
                    "max_head_shift": self._safe_number(
                        rep.get(
                            "max_head_shift"
                        )
                    ),
                    "max_shoulder_tilt": self._safe_number(
                        rep.get(
                            "max_shoulder_tilt"
                        )
                    ),
                    "max_hip_tilt": self._safe_number(
                        rep.get(
                            "max_hip_tilt"
                        )
                    ),
                    "max_knee_angle_asymmetry": self._safe_number(
                        rep.get(
                            "max_knee_angle_asymmetry"
                        )
                    ),
                    "max_center_shift": self._safe_number(
                        rep.get(
                            "max_center_shift"
                        )
                    ),
                    "max_sync_error": self._safe_number(
                        rep.get(
                            "max_sync_error"
                        )
                    ),
                    "max_left_inward": self._safe_number(
                        rep.get(
                            "max_left_inward"
                        )
                    ),
                    "max_right_inward": self._safe_number(
                        rep.get(
                            "max_right_inward"
                        )
                    ),
                    "max_symmetry_value": self._safe_number(
                        rep.get(
                            "max_symmetry_value"
                        )
                    ),
                    "max_knee_angle": self._safe_number(
                        rep.get(
                            "max_knee_angle"
                        )
                    ),
                    "shin_angle_at_min_knee": self._safe_number(
                        rep.get(
                            "shin_angle_at_min_knee"
                        )
                    )
                }

                writer.writerow(
                    row
                )

        return path

    def export_session(
        self,
        session_id,
        reps,
        summary,
        session_type="TEST",
        diagnostics=None
    ):
        report = self.build_report(
            session_id,
            reps,
            summary,
            session_type=session_type,
            diagnostics=diagnostics
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        stem = (
            f"session_{session_id}_{timestamp}"
        )

        json_path = self.export_json(
            report,
            stem
        )

        csv_path = self.export_csv(
            report,
            stem
        )

        return {
            "json": str(
                json_path
            ),
            "csv": str(
                csv_path
            ),
            "report": report
        }
