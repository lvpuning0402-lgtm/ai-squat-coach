import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean


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
        summary
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

        return {
            "report_version": 1,
            "session_id": session_id,
            "generated_at": datetime.now().isoformat(
                timespec="seconds"
            ),
            "summary": summary,
            "view_summary": view_summary,
            "issue_counts": dict(
                issue_counter
            ),
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
            "quality_score",
            "quality_label",
            "descent_time",
            "bottom_time",
            "ascent_time",
            "total_time",
            "issues",
            "min_knee_angle",
            "min_hip_angle",
            "max_trunk_lean",
            "max_head_forward",
            "max_head_shift",
            "max_shoulder_tilt",
            "max_center_shift",
            "max_sync_error",
            "max_left_inward",
            "max_right_inward",
            "max_symmetry_value"
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
                    "quality_score": self._safe_number(
                        rep.get(
                            "quality_score"
                        )
                    ),
                    "quality_label": rep.get(
                        "quality_label"
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
                    "max_head_forward": self._safe_number(
                        rep.get(
                            "max_head_forward"
                        )
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
        summary
    ):
        report = self.build_report(
            session_id,
            reps,
            summary
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
