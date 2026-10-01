import csv
import json
from datetime import datetime
from pathlib import Path


class HistoryReportExporter:
    """
    导出多次训练历史与趋势摘要。
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

    def build_report(
        self,
        history,
        progress
    ):
        return {
            "report_version": 1,
            "generated_at": datetime.now().isoformat(
                timespec="seconds"
            ),
            "progress": progress,
            "sessions": history,
            "note": (
                "Training feedback only; "
                "not a medical diagnosis."
            )
        }

    def export_json(
        self,
        report
    ):
        path = (
            self.output_dir
            / "history_latest.json"
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
        history
    ):
        path = (
            self.output_dir
            / "history_latest.csv"
        )

        fieldnames = [
            "session_id",
            "session_type",
            "start_time",
            "end_time",
            "reps",
            "front_reps",
            "side_reps",
            "average_score",
            "front_average_score",
            "side_average_score",
            "good_rate",
            "average_total_time",
            "top_issue",
            "issue_rates"
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

            for session in history:
                row = {
                    key: session.get(
                        key
                    )
                    for key in fieldnames
                }

                row["issue_rates"] = json.dumps(
                    session.get(
                        "issue_rates",
                        {}
                    ),
                    ensure_ascii=False
                )

                writer.writerow(
                    row
                )

        return path

    def export_history(
        self,
        history,
        progress
    ):
        report = self.build_report(
            history,
            progress
        )

        json_path = self.export_json(
            report
        )

        csv_path = self.export_csv(
            history
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
