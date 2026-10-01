import tempfile
import unittest
from pathlib import Path

from data.database import TrainingDatabase


class TrainingHistoryTests(unittest.TestCase):
    def build_rep(
        self,
        rep,
        score,
        view,
        issues=None
    ):
        return {
            "rep": rep,
            "view": view,
            "quality_score": score,
            "quality_label": "GOOD",
            "total_time": 2.5,
            "issues": issues or []
        }

    def test_history_and_progress(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = (
                Path(
                    temp_dir
                )
                / "training.db"
            )

            database = TrainingDatabase(
                database_path
            )

            first_session = database.start_session()

            database.save_performance_rep(
                first_session,
                self.build_rep(
                    1,
                    70.0,
                    "FRONT",
                    [
                        "KNEE_TRACKING"
                    ]
                )
            )
            database.save_performance_rep(
                first_session,
                self.build_rep(
                    2,
                    80.0,
                    "SIDE",
                    []
                )
            )

            database.finish_session(
                first_session,
                2,
                2,
                1
            )

            second_session = database.start_session()

            database.save_performance_rep(
                second_session,
                self.build_rep(
                    1,
                    88.0,
                    "FRONT",
                    []
                )
            )
            database.save_performance_rep(
                second_session,
                self.build_rep(
                    2,
                    92.0,
                    "SIDE",
                    []
                )
            )

            database.finish_session(
                second_session,
                2,
                2,
                2
            )

            history = database.get_training_history(
                limit=10
            )

            self.assertEqual(
                len(
                    history
                ),
                2
            )

            self.assertEqual(
                history[0][
                    "session_id"
                ],
                second_session
            )
            self.assertEqual(
                history[0][
                    "front_reps"
                ],
                1
            )
            self.assertEqual(
                history[0][
                    "side_reps"
                ],
                1
            )
            self.assertEqual(
                history[0][
                    "average_score"
                ],
                90.0
            )

            self.assertEqual(
                history[1][
                    "top_issue"
                ],
                "KNEE_TRACKING"
            )

            progress = (
                database.get_progress_summary(
                    limit=10
                )
            )

            self.assertEqual(
                progress[
                    "latest_session_id"
                ],
                second_session
            )
            self.assertEqual(
                progress[
                    "score_change"
                ],
                15.0
            )
            self.assertEqual(
                progress[
                    "trend"
                ],
                "IMPROVING"
            )


if __name__ == "__main__":
    unittest.main()
