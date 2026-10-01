import sqlite3
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

    def add_session(
        self,
        database,
        session_type,
        scores,
        views,
        issues=None
    ):
        session_id = database.start_session(
            session_type=session_type
        )

        issue_lists = (
            issues
            if issues is not None
            else [
                []
                for _ in scores
            ]
        )

        good_reps = 0

        for index, (
            score,
            view,
            rep_issues
        ) in enumerate(
            zip(
                scores,
                views,
                issue_lists
            ),
            start=1
        ):
            database.save_performance_rep(
                session_id,
                self.build_rep(
                    index,
                    score,
                    view,
                    rep_issues
                )
            )

            if score >= 75:
                good_reps += 1

        database.finish_session(
            session_id,
            len(
                scores
            ),
            len(
                scores
            ),
            good_reps
        )

        return session_id

    def test_test_sessions_do_not_enter_formal_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = TrainingDatabase(
                Path(
                    temp_dir
                )
                / "training.db"
            )

            test_session = self.add_session(
                database,
                "TEST",
                [
                    20.0,
                    30.0,
                    40.0
                ],
                [
                    "FRONT",
                    "FRONT",
                    "SIDE"
                ]
            )

            training_session = self.add_session(
                database,
                "TRAINING",
                [
                    80.0,
                    85.0,
                    90.0
                ],
                [
                    "FRONT",
                    "FRONT",
                    "SIDE"
                ]
            )

            history = database.get_training_history(
                limit=10
            )

            self.assertEqual(
                len(
                    history
                ),
                1
            )
            self.assertEqual(
                history[0][
                    "session_id"
                ],
                training_session
            )
            self.assertNotEqual(
                history[0][
                    "session_id"
                ],
                test_session
            )

    def test_short_training_session_is_excluded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = TrainingDatabase(
                Path(
                    temp_dir
                )
                / "training.db"
            )

            short_session = self.add_session(
                database,
                "TRAINING",
                [
                    95.0,
                    95.0
                ],
                [
                    "FRONT",
                    "SIDE"
                ]
            )

            history = database.get_training_history(
                limit=10
            )

            self.assertEqual(
                history,
                []
            )

            all_training = database.get_training_history(
                limit=10,
                session_type="TRAINING",
                min_reps=1
            )

            self.assertEqual(
                all_training[0][
                    "session_id"
                ],
                short_session
            )

    def test_progress_uses_previous_three_session_baseline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = TrainingDatabase(
                Path(
                    temp_dir
                )
                / "training.db"
            )

            for score in [
                70.0,
                80.0,
                90.0
            ]:
                self.add_session(
                    database,
                    "TRAINING",
                    [
                        score,
                        score,
                        score
                    ],
                    [
                        "FRONT",
                        "FRONT",
                        "SIDE"
                    ]
                )

            latest_session = self.add_session(
                database,
                "TRAINING",
                [
                    100.0,
                    100.0,
                    100.0
                ],
                [
                    "FRONT",
                    "FRONT",
                    "SIDE"
                ]
            )

            progress = database.get_progress_summary(
                limit=10,
                baseline_sessions=3
            )

            self.assertEqual(
                progress[
                    "latest_session_id"
                ],
                latest_session
            )
            self.assertEqual(
                progress[
                    "baseline_average_score"
                ],
                80.0
            )
            self.assertEqual(
                progress[
                    "score_change"
                ],
                20.0
            )
            self.assertEqual(
                progress[
                    "trend"
                ],
                "IMPROVING"
            )

            self.assertEqual(
                progress[
                    "front"
                ][
                    "baseline_score"
                ],
                80.0
            )
            self.assertEqual(
                progress[
                    "front"
                ][
                    "score_change"
                ],
                20.0
            )

            self.assertEqual(
                progress[
                    "side"
                ][
                    "trend"
                ],
                "INSUFFICIENT"
            )

    def test_issue_frequency_change_is_tracked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = TrainingDatabase(
                Path(
                    temp_dir
                )
                / "training.db"
            )

            self.add_session(
                database,
                "TRAINING",
                [
                    80.0,
                    82.0,
                    84.0
                ],
                [
                    "FRONT",
                    "FRONT",
                    "SIDE"
                ],
                [
                    [
                        "SHOULDER"
                    ],
                    [],
                    []
                ]
            )

            self.add_session(
                database,
                "TRAINING",
                [
                    82.0,
                    84.0,
                    86.0
                ],
                [
                    "FRONT",
                    "FRONT",
                    "SIDE"
                ],
                [
                    [],
                    [],
                    []
                ]
            )

            self.add_session(
                database,
                "TRAINING",
                [
                    84.0,
                    86.0,
                    88.0
                ],
                [
                    "FRONT",
                    "FRONT",
                    "SIDE"
                ],
                [
                    [],
                    [],
                    []
                ]
            )

            self.add_session(
                database,
                "TRAINING",
                [
                    70.0,
                    72.0,
                    74.0
                ],
                [
                    "FRONT",
                    "FRONT",
                    "SIDE"
                ],
                [
                    [
                        "SHOULDER"
                    ],
                    [
                        "SHOULDER"
                    ],
                    []
                ]
            )

            progress = database.get_progress_summary(
                limit=10,
                baseline_sessions=3
            )

            self.assertEqual(
                progress[
                    "latest_top_issue"
                ],
                "SHOULDER"
            )
            self.assertAlmostEqual(
                progress[
                    "latest_top_issue_rate"
                ],
                66.7,
                places=1
            )
            self.assertGreater(
                progress[
                    "issue_rate_change"
                ],
                50.0
            )

    def test_old_schema_is_migrated_to_test_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = (
                Path(
                    temp_dir
                )
                / "training.db"
            )

            connection = sqlite3.connect(
                database_path
            )
            cursor = connection.cursor()

            cursor.execute(
                """
                CREATE TABLE sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    total_reps INTEGER DEFAULT 0,
                    analyzed_reps INTEGER DEFAULT 0,
                    good_reps INTEGER DEFAULT 0,
                    good_rate REAL DEFAULT 0,
                    notes TEXT
                )
                """
            )

            cursor.execute(
                """
                INSERT INTO sessions (
                    start_time,
                    end_time
                )
                VALUES (
                    '2026-01-01T10:00:00',
                    '2026-01-01T10:10:00'
                )
                """
            )

            connection.commit()
            connection.close()

            database = TrainingDatabase(
                database_path
            )

            session = database.get_session_summary(
                1
            )

            self.assertEqual(
                session[
                    "session_type"
                ],
                "TEST"
            )

    def test_obvious_legacy_outlier_is_excluded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = TrainingDatabase(
                Path(
                    temp_dir
                )
                / "training.db"
            )

            session_id = database.start_session(
                session_type="TRAINING"
            )

            for rep_number in range(
                1,
                4
            ):
                rep = self.build_rep(
                    rep_number,
                    90.0,
                    "FRONT",
                    []
                )

                rep["max_center_shift"] = 0.05
                rep["max_sync_error"] = 0.10
                rep["max_left_inward"] = 0.0
                rep["max_right_inward"] = 0.0

                database.save_performance_rep(
                    session_id,
                    rep
                )

            corrupted = self.build_rep(
                4,
                50.0,
                "FRONT",
                [
                    "CENTER"
                ]
            )
            corrupted[
                "total_time"
            ] = 100.0
            corrupted[
                "max_center_shift"
            ] = 1.10
            corrupted[
                "max_sync_error"
            ] = 0.20
            corrupted[
                "max_left_inward"
            ] = 0.30
            corrupted[
                "max_right_inward"
            ] = 0.40

            database.save_performance_rep(
                session_id,
                corrupted
            )

            database.finish_session(
                session_id,
                4,
                4,
                3
            )

            history = database.get_training_history(
                limit=10
            )

            self.assertEqual(
                history[0][
                    "reps"
                ],
                3
            )
            self.assertEqual(
                history[0][
                    "excluded_reps"
                ],
                1
            )
            self.assertEqual(
                history[0][
                    "average_score"
                ],
                90.0
            )

    def test_relative_rom_outlier_is_excluded_from_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = TrainingDatabase(
                Path(
                    temp_dir
                )
                / "training.db"
            )

            session_id = database.start_session(
                session_type="TRAINING"
            )

            rom_values = [
                0.129,
                0.485,
                0.476,
                0.471,
                0.450,
                0.495,
                0.468
            ]

            for index, rom in enumerate(
                rom_values,
                start=1
            ):
                rep = self.build_rep(
                    index,
                    95.0,
                    "FRONT",
                    []
                )

                rep["rom"] = rom
                rep["max_center_shift"] = 0.05
                rep["max_sync_error"] = 0.14
                rep["max_left_inward"] = 0.0
                rep["max_right_inward"] = 0.0

                database.save_performance_rep(
                    session_id,
                    rep
                )

            database.finish_session(
                session_id,
                7,
                7,
                7
            )

            history = database.get_training_history(
                limit=10
            )

            self.assertEqual(
                history[0]["reps"],
                6
            )
            self.assertEqual(
                history[0]["excluded_reps"],
                1
            )


if __name__ == "__main__":
    unittest.main()
