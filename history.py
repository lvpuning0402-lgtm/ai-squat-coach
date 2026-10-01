from data.database import TrainingDatabase
from reports.history_report import HistoryReportExporter


def print_history():
    database = TrainingDatabase()

    history = database.get_training_history(
        limit=10
    )

    progress = database.get_progress_summary(
        limit=10
    )

    print()
    print(
        "=== TRAINING HISTORY ==="
    )

    if not history:
        print(
            "No completed training sessions yet."
        )
        return

    for session in history:
        print(
            f"Session #{session['session_id']} | "
            f"Reps {session['reps']} | "
            f"FRONT {session['front_reps']} | "
            f"SIDE {session['side_reps']} | "
            f"Avg {session['average_score']:.1f} | "
            f"Good {session['good_rate']:.1f}% | "
            f"Issue {session['top_issue']}"
        )

    print()
    print(
        "=== PROGRESS ==="
    )
    print(
        f"Latest session: "
        f"#{progress['latest_session_id']}"
    )
    print(
        f"Latest average: "
        f"{progress['latest_average_score']:.1f}"
    )
    print(
        f"Score change: "
        f"{progress['score_change']:+.1f}"
    )
    print(
        f"Good-rate change: "
        f"{progress['good_rate_change']:+.1f}%"
    )
    print(
        f"Trend: "
        f"{progress['trend']}"
    )
    print(
        f"Latest main issue: "
        f"{progress['latest_top_issue']}"
    )

    exporter = HistoryReportExporter()

    paths = exporter.export_history(
        history,
        progress
    )

    print()
    print(
        "HISTORY REPORT | "
        f"JSON {paths['json']} | "
        f"CSV {paths['csv']}"
    )


if __name__ == "__main__":
    print_history()
