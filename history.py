import argparse

from data.database import TrainingDatabase
from reports.history_report import HistoryReportExporter
from feedback.insights import ProgressInsightBuilder


def format_change(
    value,
    suffix=""
):
    if value is None:
        return "--"

    return (
        f"{value:+.1f}"
        f"{suffix}"
    )


def format_score(
    value
):
    if value is None:
        return "--"

    return f"{value:.1f}"


def print_history(
    mode="TRAINING",
    min_reps=3
):
    database = TrainingDatabase()

    session_type = (
        None
        if mode == "ALL"
        else mode
    )

    history = database.get_training_history(
        limit=10,
        session_type=session_type,
        min_reps=min_reps
    )

    print()
    print(
        f"=== {mode} HISTORY ==="
    )

    if not history:
        print(
            "No matching completed sessions yet."
        )
        return

    for session in history:
        print(
            f"Session #{session['session_id']} | "
            f"{session['session_type']} | "
            f"Reps {session['reps']} | "
            f"FRONT {session['front_reps']} "
            f"({format_score(session['front_average_score'])}) | "
            f"SIDE {session['side_reps']} "
            f"({format_score(session['side_average_score'])}) | "
            f"Avg {session['average_score']:.1f} | "
            f"Good {session['good_rate']:.1f}% | "
            f"Issue {session['top_issue']}"
        )

    if mode != "TRAINING":
        return

    progress = database.get_progress_summary(
        limit=10,
        baseline_sessions=3,
        min_reps=min_reps
    )

    print()
    print(
        "=== FORMAL PROGRESS ==="
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
        f"Previous baseline: "
        f"{format_score(progress['baseline_average_score'])}"
    )
    print(
        f"Score change: "
        f"{format_change(progress['score_change'])}"
    )
    print(
        f"Good-rate change: "
        f"{format_change(progress['good_rate_change'], '%')}"
    )
    print(
        f"Trend: "
        f"{progress['trend']}"
    )
    print(
        f"FRONT: "
        f"{progress['front']['trend']} | "
        f"{format_change(progress['front']['score_change'])}"
    )
    print(
        f"SIDE: "
        f"{progress['side']['trend']} | "
        f"{format_change(progress['side']['score_change'])}"
    )
    print(
        f"Latest main issue: "
        f"{progress['latest_top_issue']} "
        f"({progress['latest_top_issue_rate']:.1f}%)"
    )
    print(
        f"Issue-rate change: "
        f"{format_change(progress['issue_rate_change'], '%')}"
    )

    feedback = ProgressInsightBuilder().build(
        progress
    )

    print()
    print(
        "=== AI COACH PROGRESS ==="
    )
    print(
        feedback[
            "headline"
        ]
    )
    print(
        feedback[
            "summary"
        ]
    )
    print(
        "当前重点："
        + feedback[
            "focus"
        ]
    )
    print(
        "下一次训练："
        + feedback[
            "next_action"
        ]
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


def main():
    parser = argparse.ArgumentParser(
        description=(
            "View AI Sport Coach session history."
        )
    )

    parser.add_argument(
        "--mode",
        choices=[
            "TRAINING",
            "TEST",
            "ALL"
        ],
        default="TRAINING"
    )

    parser.add_argument(
        "--min-reps",
        type=int,
        default=None
    )

    args = parser.parse_args()

    min_reps = (
        args.min_reps
        if args.min_reps is not None
        else (
            3
            if args.mode == "TRAINING"
            else 1
        )
    )

    print_history(
        mode=args.mode,
        min_reps=max(
            1,
            min_reps
        )
    )


if __name__ == "__main__":
    main()
