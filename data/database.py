import sqlite3
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean


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

    @staticmethod
    def ensure_column(
        cursor,
        table_name,
        column_name,
        column_sql
    ):
        cursor.execute(
            f"PRAGMA table_info({table_name})"
        )

        existing_columns = {
            row[1]
            for row in cursor.fetchall()
        }

        if column_name not in existing_columns:
            cursor.execute(
                f"ALTER TABLE {table_name} "
                f"ADD COLUMN {column_name} {column_sql}"
            )

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

        self.ensure_column(
            cursor,
            "sessions",
            "session_type",
            "TEXT NOT NULL DEFAULT 'TEST'"
        )

        # 旧数据全部视为测试/开发数据，避免污染正式训练趋势。
        cursor.execute(
            """
            UPDATE sessions
            SET session_type = 'TEST'
            WHERE session_type IS NULL
               OR session_type = ''
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

    def start_session(
        self,
        session_type="TEST"
    ):
        connection = self.connect()
        cursor = connection.cursor()

        start_time = datetime.now().isoformat(
            timespec="seconds"
        )

        cursor.execute(
            """
            INSERT INTO sessions (
                start_time,
                session_type
            )
            VALUES (?, ?)
            """,
            (
                start_time,
                session_type,
            )
        )

        session_id = cursor.lastrowid

        connection.commit()
        connection.close()

        print(
            f"Training session started: "
            f"{session_id} [{session_type}]"
        )

        return session_id

    def set_session_type(
        self,
        session_id,
        session_type
    ):
        connection = self.connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE sessions
            SET session_type = ?
            WHERE id = ?
            """,
            (
                session_type,
                session_id
            )
        )

        connection.commit()
        connection.close()

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


    @staticmethod
    def _stored_rep_is_reliable(
        rep
    ):
        metrics = rep.get(
            "metrics",
            {}
        )

        explicit_valid = metrics.get(
            "analysis_valid"
        )

        if explicit_valid is False:
            return False

        total_time = metrics.get(
            "total_time",
            rep.get(
                "total_time"
            )
        )

        if total_time is not None:
            try:
                total_time = float(
                    total_time
                )
            except (
                TypeError,
                ValueError
            ):
                total_time = None

        if (
            total_time is not None
            and (
                total_time <= 0.35
                or total_time > 12.0
            )
        ):
            return False

        view = rep.get(
            "view",
            metrics.get(
                "view",
                "UNKNOWN"
            )
        )

        if view == "FRONT":
            inward = max(
                float(
                    metrics.get(
                        "max_left_inward",
                        0.0
                    )
                    or 0.0
                ),
                float(
                    metrics.get(
                        "max_right_inward",
                        0.0
                    )
                    or 0.0
                )
            )

            center = float(
                metrics.get(
                    "max_center_shift",
                    0.0
                )
                or 0.0
            )

            sync = float(
                metrics.get(
                    "max_sync_error",
                    0.0
                )
                or 0.0
            )

            if (
                inward > 1.0
                or center > 1.25
                or sync > 0.80
            ):
                return False

        elif view == "SIDE":
            trunk = float(
                metrics.get(
                    "max_trunk_lean",
                    0.0
                )
                or 0.0
            )
            head = float(
                metrics.get(
                    "max_head_forward",
                    0.0
                )
                or 0.0
            )
            sync = float(
                metrics.get(
                    "max_sync_error",
                    0.0
                )
                or 0.0
            )

            if (
                trunk > 80.0
                or head > 2.0
                or sync > 1.5
            ):
                return False

        return True

    @staticmethod
    def _median(
        values
    ):
        cleaned = sorted(
            float(value)
            for value in values
            if value is not None
        )

        if not cleaned:
            return None

        middle = len(
            cleaned
        ) // 2

        if len(
            cleaned
        ) % 2:
            return cleaned[
                middle
            ]

        return (
            cleaned[
                middle - 1
            ]
            + cleaned[
                middle
            ]
        ) / 2

    def _filter_relative_session_outliers(
        self,
        reps
    ):
        """
        过滤同一 session、同一视角下明显偏离本组模式的 Rep。
        """
        reliable = list(
            reps
        )

        excluded_ids = set()

        for view in (
            "FRONT",
            "SIDE"
        ):
            view_reps = [
                rep
                for rep in reliable
                if rep.get(
                    "view"
                ) == view
            ]

            if len(
                view_reps
            ) < 4:
                continue

            tempo_median = self._median([
                rep.get(
                    "total_time"
                )
                for rep in view_reps
            ])

            rom_key = (
                "rom"
                if view == "FRONT"
                else "rom_degrees"
            )

            rom_median = self._median([
                rep.get(
                    "metrics",
                    {}
                ).get(
                    rom_key
                )
                for rep in view_reps
            ])

            for rep in view_reps:
                total_time = rep.get(
                    "total_time"
                )

                if (
                    tempo_median
                    and total_time
                ):
                    tempo_ratio = (
                        float(
                            total_time
                        )
                        / tempo_median
                    )

                    if (
                        tempo_ratio < 0.45
                        or tempo_ratio > 2.20
                    ):
                        excluded_ids.add(
                            rep[
                                "id"
                            ]
                        )
                        continue

                rom_value = rep.get(
                    "metrics",
                    {}
                ).get(
                    rom_key
                )

                if (
                    rom_median
                    and rom_value
                ):
                    rom_ratio = (
                        float(
                            rom_value
                        )
                        / rom_median
                    )

                    if (
                        rom_ratio < 0.55
                        or rom_ratio > 1.80
                    ):
                        excluded_ids.add(
                            rep[
                                "id"
                            ]
                        )

        return [
            rep
            for rep in reliable
            if rep.get(
                "id"
            ) not in excluded_ids
        ]

    def get_training_history(
        self,
        limit=10,
        session_type="TRAINING",
        min_reps=3
    ):
        """
        返回最近若干次有效训练的聚合历史。

        正式趋势默认只统计 TRAINING：
        - TEST 不进入正式趋势
        - 少于 min_reps 的 session 不进入正式趋势
        """
        sessions = self.get_recent_sessions(
            max(
                limit * 6,
                limit
            )
        )

        history = []

        for session in sessions:
            if session.get(
                "end_time"
            ) is None:
                continue

            if (
                session_type is not None
                and session.get(
                    "session_type",
                    "TEST"
                ) != session_type
            ):
                continue

            all_reps = self.get_performance_reps(
                session["id"]
            )

            absolute_reliable_reps = [
                rep
                for rep in all_reps
                if self._stored_rep_is_reliable(
                    rep
                )
            ]

            reps = self._filter_relative_session_outliers(
                absolute_reliable_reps
            )

            if len(
                reps
            ) < min_reps:
                continue

            scores = [
                rep["quality_score"]
                for rep in reps
                if rep.get(
                    "quality_score"
                ) is not None
            ]

            tempos = [
                rep["total_time"]
                for rep in reps
                if (
                    rep.get(
                        "total_time"
                    ) is not None
                    and rep["total_time"] > 0
                )
            ]

            front_scores = [
                rep["quality_score"]
                for rep in reps
                if (
                    rep.get(
                        "view"
                    ) == "FRONT"
                    and rep.get(
                        "quality_score"
                    ) is not None
                )
            ]

            side_scores = [
                rep["quality_score"]
                for rep in reps
                if (
                    rep.get(
                        "view"
                    ) == "SIDE"
                    and rep.get(
                        "quality_score"
                    ) is not None
                )
            ]

            view_counts = Counter(
                rep.get(
                    "view",
                    "UNKNOWN"
                )
                for rep in reps
            )

            issue_counter = Counter()

            for rep in reps:
                issue_counter.update(
                    rep.get(
                        "issues",
                        []
                    )
                )

            issue_rates = {
                issue: round(
                    count
                    / len(
                        reps
                    )
                    * 100.0,
                    1
                )
                for issue, count
                in issue_counter.items()
            }

            average_score = (
                round(
                    mean(
                        scores
                    ),
                    1
                )
                if scores
                else 0.0
            )

            average_total_time = (
                round(
                    mean(
                        tempos
                    ),
                    2
                )
                if tempos
                else 0.0
            )

            front_average_score = (
                round(
                    mean(
                        front_scores
                    ),
                    1
                )
                if front_scores
                else None
            )

            side_average_score = (
                round(
                    mean(
                        side_scores
                    ),
                    1
                )
                if side_scores
                else None
            )

            top_issue = (
                issue_counter.most_common(
                    1
                )[0][0]
                if issue_counter
                else "NONE"
            )

            history.append({
                "session_id": session[
                    "id"
                ],
                "session_type": session.get(
                    "session_type",
                    "TEST"
                ),
                "start_time": session.get(
                    "start_time"
                ),
                "end_time": session.get(
                    "end_time"
                ),
                "reps": len(
                    reps
                ),
                "excluded_reps": (
                    len(
                        all_reps
                    )
                    - len(
                        reps
                    )
                ),
                "front_reps": view_counts.get(
                    "FRONT",
                    0
                ),
                "side_reps": view_counts.get(
                    "SIDE",
                    0
                ),
                "average_score": average_score,
                "front_average_score": front_average_score,
                "side_average_score": side_average_score,
                "good_rate": round(
                    float(
                        session.get(
                            "good_rate",
                            0.0
                        )
                        or 0.0
                    ),
                    1
                ),
                "average_total_time": average_total_time,
                "top_issue": top_issue,
                "issue_rates": issue_rates
            })

            if len(
                history
            ) >= limit:
                break

        return history

    @staticmethod
    def _trend_from_change(
        change
    ):
        if change is None:
            return "COLLECTING"

        if change >= 5.0:
            return "IMPROVING"

        if change <= -5.0:
            return "DECLINING"

        return "STABLE"

    def get_progress_summary(
        self,
        limit=10,
        baseline_sessions=3,
        min_reps=3
    ):
        """
        汇总正式训练趋势。

        与最近 1 场相比过于敏感，因此改为：
        - 最新正式训练
        - 对比之前最多 baseline_sessions 场正式训练均值
        - FRONT / SIDE 分开计算
        - 少量 Rep 不参与正式趋势
        """
        history = self.get_training_history(
            limit=limit,
            session_type="TRAINING",
            min_reps=min_reps
        )

        empty_view = {
            "latest_score": None,
            "baseline_score": None,
            "score_change": None,
            "trend": "NO DATA",
            "latest_reps": 0,
            "baseline_sessions": 0
        }

        if not history:
            return {
                "sessions": 0,
                "latest_session_id": None,
                "latest_average_score": 0.0,
                "baseline_average_score": None,
                "score_change": None,
                "latest_good_rate": 0.0,
                "baseline_good_rate": None,
                "good_rate_change": None,
                "latest_top_issue": "NONE",
                "latest_top_issue_rate": 0.0,
                "issue_rate_change": None,
                "trend": "NO DATA",
                "front": dict(
                    empty_view
                ),
                "side": dict(
                    empty_view
                )
            }

        latest = history[
            0
        ]

        baseline = history[
            1:
            1 + baseline_sessions
        ]

        baseline_average_score = (
            round(
                mean(
                    item[
                        "average_score"
                    ]
                    for item in baseline
                ),
                1
            )
            if baseline
            else None
        )

        baseline_good_rate = (
            round(
                mean(
                    item[
                        "good_rate"
                    ]
                    for item in baseline
                ),
                1
            )
            if baseline
            else None
        )

        score_change = (
            round(
                latest[
                    "average_score"
                ]
                - baseline_average_score,
                1
            )
            if baseline_average_score is not None
            else None
        )

        good_rate_change = (
            round(
                latest[
                    "good_rate"
                ]
                - baseline_good_rate,
                1
            )
            if baseline_good_rate is not None
            else None
        )

        latest_top_issue = latest[
            "top_issue"
        ]

        latest_top_issue_rate = (
            latest[
                "issue_rates"
            ].get(
                latest_top_issue,
                0.0
            )
            if latest_top_issue != "NONE"
            else 0.0
        )

        if (
            latest_top_issue != "NONE"
            and baseline
        ):
            baseline_issue_rate = mean(
                item[
                    "issue_rates"
                ].get(
                    latest_top_issue,
                    0.0
                )
                for item in baseline
            )

            issue_rate_change = round(
                latest_top_issue_rate
                - baseline_issue_rate,
                1
            )
        else:
            issue_rate_change = None

        def build_view_progress(
            view_name,
            score_key,
            reps_key
        ):
            latest_score = latest.get(
                score_key
            )
            latest_reps = latest.get(
                reps_key,
                0
            )

            if (
                latest_score is None
                or latest_reps < 2
            ):
                return {
                    "latest_score": latest_score,
                    "baseline_score": None,
                    "score_change": None,
                    "trend": "INSUFFICIENT",
                    "latest_reps": latest_reps,
                    "baseline_sessions": 0
                }

            baseline_scores = [
                item[
                    score_key
                ]
                for item in baseline
                if (
                    item.get(
                        score_key
                    ) is not None
                    and item.get(
                        reps_key,
                        0
                    ) >= 2
                )
            ]

            if not baseline_scores:
                return {
                    "latest_score": latest_score,
                    "baseline_score": None,
                    "score_change": None,
                    "trend": "COLLECTING",
                    "latest_reps": latest_reps,
                    "baseline_sessions": 0
                }

            baseline_score = round(
                mean(
                    baseline_scores
                ),
                1
            )

            change = round(
                latest_score
                - baseline_score,
                1
            )

            return {
                "latest_score": latest_score,
                "baseline_score": baseline_score,
                "score_change": change,
                "trend": self._trend_from_change(
                    change
                ),
                "latest_reps": latest_reps,
                "baseline_sessions": len(
                    baseline_scores
                )
            }

        front_progress = build_view_progress(
            "FRONT",
            "front_average_score",
            "front_reps"
        )

        side_progress = build_view_progress(
            "SIDE",
            "side_average_score",
            "side_reps"
        )

        return {
            "sessions": len(
                history
            ),
            "latest_session_id": latest[
                "session_id"
            ],
            "latest_average_score": latest[
                "average_score"
            ],
            "baseline_average_score": baseline_average_score,
            "score_change": score_change,
            "latest_good_rate": latest[
                "good_rate"
            ],
            "baseline_good_rate": baseline_good_rate,
            "good_rate_change": good_rate_change,
            "latest_top_issue": latest_top_issue,
            "latest_top_issue_rate": latest_top_issue_rate,
            "issue_rate_change": issue_rate_change,
            "trend": self._trend_from_change(
                score_change
            ),
            "front": front_progress,
            "side": side_progress
        }
