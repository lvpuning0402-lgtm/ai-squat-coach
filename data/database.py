import sqlite3
import json
from datetime import datetime
from pathlib import Path


class TrainingDatabase:
    def __init__(
        self,
        database_path="data/training.db"
    ):
        self.database_path = Path(
            database_path
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.create_tables()

    def connect(self):
        connection = sqlite3.connect(
            self.database_path
        )

        connection.row_factory = sqlite3.Row

        return connection

    def create_tables(self):
        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
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

        # 旧版单次动作表，保留兼容。
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                rep_number INTEGER NOT NULL,
                min_knee_angle REAL,
                stable_trunk_lean REAL,
                trunk_analyzed INTEGER DEFAULT 0,
                depth_ok INTEGER,
                trunk_ok INTEGER,
                result TEXT,
                issues TEXT,
                created_at TEXT,
                FOREIGN KEY(session_id)
                REFERENCES sessions(id)
            )
            """
        )

        # 新版通用动作表现表。
        # FRONT / SIDE 都可以存完整 JSON 指标。
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS performance_reps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                rep_number INTEGER NOT NULL,
                view TEXT,
                quality_score REAL,
                quality_label TEXT,
                total_time REAL,
                issues TEXT,
                metrics_json TEXT,
                created_at TEXT,
                FOREIGN KEY(session_id)
                REFERENCES sessions(id)
            )
            """
        )

        connection.commit()
        connection.close()

    def start_session(self):
        connection = self.connect()
        cursor = connection.cursor()

        start_time = datetime.now().isoformat(
            timespec="seconds"
        )

        cursor.execute(
            """
            INSERT INTO sessions (
                start_time
            )
            VALUES (?)
            """,
            (
                start_time,
            )
        )

        session_id = cursor.lastrowid

        connection.commit()
        connection.close()

        print(
            f"Training session started: {session_id}"
        )

        return session_id

    def save_rep(
        self,
        session_id,
        rep_data
    ):
        """
        兼容旧版深蹲记录。
        """
        connection = self.connect()
        cursor = connection.cursor()

        issues = json.dumps(
            rep_data.get(
                "issues",
                []
            ),
            ensure_ascii=False
        )

        trunk_value = rep_data.get(
            "stable_trunk_lean"
        )

        trunk_analyzed = rep_data.get(
            "trunk_analyzed",
            trunk_value is not None
        )

        depth_ok = rep_data.get(
            "depth_ok"
        )

        trunk_ok = rep_data.get(
            "trunk_ok"
        )

        created_at = datetime.now().isoformat(
            timespec="seconds"
        )

        cursor.execute(
            """
            INSERT INTO reps (
                session_id,
                rep_number,
                min_knee_angle,
                stable_trunk_lean,
                trunk_analyzed,
                depth_ok,
                trunk_ok,
                result,
                issues,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                rep_data.get("rep"),
                rep_data.get(
                    "min_knee_angle"
                ),
                trunk_value,
                int(
                    bool(
                        trunk_analyzed
                    )
                ),
                (
                    None
                    if depth_ok is None
                    else int(
                        bool(
                            depth_ok
                        )
                    )
                ),
                (
                    None
                    if trunk_ok is None
                    else int(
                        bool(
                            trunk_ok
                        )
                    )
                ),
                rep_data.get(
                    "result"
                ),
                issues,
                created_at
            )
        )

        connection.commit()
        connection.close()

    def save_performance_rep(
        self,
        session_id,
        rep_data
    ):
        """
        保存新版 FRONT / SIDE 单次动作表现。
        """
        connection = self.connect()
        cursor = connection.cursor()

        issues = json.dumps(
            rep_data.get(
                "issues",
                []
            ),
            ensure_ascii=False
        )

        metrics_json = json.dumps(
            rep_data,
            ensure_ascii=False
        )

        created_at = datetime.now().isoformat(
            timespec="seconds"
        )

        cursor.execute(
            """
            INSERT INTO performance_reps (
                session_id,
                rep_number,
                view,
                quality_score,
                quality_label,
                total_time,
                issues,
                metrics_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                rep_data.get("rep"),
                rep_data.get("view"),
                rep_data.get(
                    "quality_score"
                ),
                rep_data.get(
                    "quality_label"
                ),
                rep_data.get(
                    "total_time"
                ),
                issues,
                metrics_json,
                created_at
            )
        )

        connection.commit()
        connection.close()

    def finish_session(
        self,
        session_id,
        total_reps,
        analyzed_reps,
        good_reps
    ):
        if analyzed_reps > 0:
            good_rate = (
                good_reps
                / analyzed_reps
            ) * 100
        else:
            good_rate = 0.0

        end_time = datetime.now().isoformat(
            timespec="seconds"
        )

        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE sessions
            SET
                end_time = ?,
                total_reps = ?,
                analyzed_reps = ?,
                good_reps = ?,
                good_rate = ?
            WHERE id = ?
            """,
            (
                end_time,
                total_reps,
                analyzed_reps,
                good_reps,
                good_rate,
                session_id
            )
        )

        connection.commit()
        connection.close()

        print(
            f"Training session saved: {session_id}"
        )

    def get_recent_sessions(
        self,
        limit=10
    ):
        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM sessions
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                limit,
            )
        )

        rows = cursor.fetchall()

        connection.close()

        return [
            dict(row)
            for row in rows
        ]

    def get_session_reps(
        self,
        session_id
    ):
        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM reps
            WHERE session_id = ?
            ORDER BY rep_number ASC
            """,
            (
                session_id,
            )
        )

        rows = cursor.fetchall()
        connection.close()

        results = []

        for row in rows:
            item = dict(row)

            try:
                item["issues"] = json.loads(
                    item["issues"]
                )
            except Exception:
                item["issues"] = []

            results.append(
                item
            )

        return results

    def get_performance_reps(
        self,
        session_id
    ):
        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM performance_reps
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (
                session_id,
            )
        )

        rows = cursor.fetchall()
        connection.close()

        results = []

        for row in rows:
            item = dict(row)

            try:
                item["issues"] = json.loads(
                    item["issues"]
                )
            except Exception:
                item["issues"] = []

            try:
                item["metrics"] = json.loads(
                    item["metrics_json"]
                )
            except Exception:
                item["metrics"] = {}

            results.append(
                item
            )

        return results

    def get_session_summary(
        self,
        session_id
    ):
        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM sessions
            WHERE id = ?
            """,
            (
                session_id,
            )
        )

        row = cursor.fetchone()
        connection.close()

        if row is None:
            return None

        return dict(
            row
        )

    def get_total_statistics(self):
        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*) AS session_count,
                COALESCE(
                    SUM(total_reps),
                    0
                ) AS total_reps,
                COALESCE(
                    SUM(good_reps),
                    0
                ) AS total_good_reps,
                COALESCE(
                    SUM(analyzed_reps),
                    0
                ) AS total_analyzed_reps
            FROM sessions
            WHERE end_time IS NOT NULL
            """
        )

        row = cursor.fetchone()
        connection.close()

        result = dict(
            row
        )

        analyzed = result[
            "total_analyzed_reps"
        ]
        good = result[
            "total_good_reps"
        ]

        if analyzed > 0:
            result[
                "overall_good_rate"
            ] = (
                good / analyzed
            ) * 100
        else:
            result[
                "overall_good_rate"
            ] = 0.0

        return result
