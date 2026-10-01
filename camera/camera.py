import cv2

from pose.detector import PoseDetector
from pose.view_detector import ViewDetector

from exercises.front_squat import FrontSquatAnalyzer
from exercises.side_squat import SideSquatAnalyzer

from feedback.front_feedback import FrontFeedback
from feedback.performance import SessionPerformanceAnalyzer

from data.database import TrainingDatabase


def get_position_hint(
    view,
    raw_view
):
    if view == "SIDE":
        if raw_view == "SIDE":
            return "POSITION GOOD"
        return "ADJUST TO SIDE"

    if view == "FRONT":
        if raw_view == "FRONT":
            return "POSITION GOOD"
        return "ADJUST TO FRONT"

    return "HOLD POSITION"


def metric_state(
    value,
    good_threshold,
    bad_threshold,
    good_text="OK",
    bad_text="CHECK"
):
    if value <= good_threshold:
        return good_text

    if value >= bad_threshold:
        return bad_text

    return "WATCH"


def format_time(value):
    if value is None:
        return "--"

    return f"{value:.2f}s"


def draw_lines(
    frame,
    lines,
    x=25,
    y=35,
    font_scale=0.50,
    step=28
):
    for line in lines:
        cv2.putText(
            frame,
            str(line),
            (
                x,
                y
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (
                255,
                255,
                255
            ),
            2
        )

        y += step


def draw_set_panel(
    frame,
    performance,
    width
):
    summary = performance.get_set_summary()

    if summary["reps"] == 0:
        return

    lines = [
        "SET SUMMARY",
        f"Reps: {summary['reps']}",
        (
            f"Avg quality: "
            f"{summary['average_score']:.1f}"
        ),
        (
            f"Best rep: "
            f"{summary['best_rep']}"
        ),
        (
            f"Quality trend: "
            f"{summary['quality_change']:+.1f}"
        ),
        (
            f"Tempo trend: "
            f"{summary['tempo_change']:+.1f}%"
        ),
        (
            f"Movement trend: "
            f"{summary['trend']}"
        )
    ]

    panel_x = max(
        25,
        width - 360
    )

    draw_lines(
        frame,
        lines,
        x=panel_x,
        y=35,
        font_scale=0.48,
        step=28
    )


def prepare_performance_rep(
    rep_summary,
    performance
):
    if rep_summary is None:
        return None

    rep_data = dict(
        rep_summary
    )

    # 使用整次训练统一编号。
    rep_data["rep"] = (
        len(performance.reps)
        + 1
    )

    return rep_data


def save_completed_rep(
    rep_summary,
    performance,
    database,
    session_id
):
    rep_data = prepare_performance_rep(
        rep_summary,
        performance
    )

    if rep_data is None:
        return None

    analyzed = performance.analyze_rep(
        rep_data
    )

    try:
        database.save_performance_rep(
            session_id,
            analyzed
        )
    except Exception as error:
        print(
            f"Database rep save warning: {error}"
        )

    print(
        "REP COMPLETE | "
        f"#{analyzed['rep']} | "
        f"{analyzed['view']} | "
        f"Quality {analyzed['quality_score']:.1f} | "
        f"{analyzed['quality_label']}"
    )

    return analyzed


def run_camera():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print(
            "无法打开摄像头"
        )
        return

    detector = PoseDetector()
    view_detector = ViewDetector()

    front_analyzer = FrontSquatAnalyzer()
    side_analyzer = SideSquatAnalyzer()

    front_feedback = FrontFeedback()

    performance = SessionPerformanceAnalyzer()

    database = TrainingDatabase()
    session_id = database.start_session()

    window_name = "AI Sport Coach"

    cv2.namedWindow(
        window_name,
        cv2.WINDOW_NORMAL
    )

    active_leg = None
    last_completed_rep = None

    print(
        "Multi-angle squat analysis enabled"
    )
    print(
        "Phase + tempo + ROM + stability analysis enabled"
    )
    print(
        "Rep / set performance tracking enabled"
    )
    print(
        f"Session ID: {session_id}"
    )
    print(
        "按 Q / ESC 退出"
    )

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                break

            height = frame.shape[0]
            width = frame.shape[1]

            frame, result = detector.detect(
                frame
            )

            nose = detector.get_landmark(
                result,
                0
            )
            left_shoulder = detector.get_landmark(
                result,
                11
            )
            right_shoulder = detector.get_landmark(
                result,
                12
            )
            left_hip = detector.get_landmark(
                result,
                23
            )
            right_hip = detector.get_landmark(
                result,
                24
            )
            left_knee = detector.get_landmark(
                result,
                25
            )
            right_knee = detector.get_landmark(
                result,
                26
            )
            left_ankle = detector.get_landmark(
                result,
                27
            )
            right_ankle = detector.get_landmark(
                result,
                28
            )

            ready = all([
                nose,
                left_shoulder,
                right_shoulder,
                left_hip,
                right_hip,
                left_knee,
                right_knee,
                left_ankle,
                right_ankle
            ])

            if ready:
                (
                    view,
                    view_ratio,
                    raw_view
                ) = view_detector.update(
                    left_shoulder["point"],
                    right_shoulder["point"],
                    left_hip["point"],
                    right_hip["point"],
                    width,
                    height,
                    freeze=False
                )

                position = get_position_hint(
                    view,
                    raw_view
                )

                if view == "FRONT":
                    front_result = front_analyzer.analyze(
                        nose["point"],
                        left_shoulder["point"],
                        right_shoulder["point"],
                        left_hip["point"],
                        right_hip["point"],
                        left_knee["point"],
                        right_knee["point"],
                        left_ankle["point"],
                        right_ankle["point"]
                    )

                    if front_result is not None:
                        front_form = front_feedback.update(
                            left_hip["point"],
                            right_hip["point"],
                            left_knee["point"],
                            right_knee["point"],
                            left_ankle["point"],
                            right_ankle["point"],
                            front_result["phase"]
                        )

                        if (
                            front_result["rep_completed"]
                            and front_result["rep_summary"]
                        ):
                            rep_summary = dict(
                                front_result["rep_summary"]
                            )

                            rep_summary[
                                "left_inward"
                            ] = front_form[
                                "left_value"
                            ]
                            rep_summary[
                                "right_inward"
                            ] = front_form[
                                "right_value"
                            ]
                            rep_summary[
                                "symmetry_value"
                            ] = front_form[
                                "symmetry_value"
                            ]

                            last_completed_rep = (
                                save_completed_rep(
                                    rep_summary,
                                    performance,
                                    database,
                                    session_id
                                )
                            )

                        head_state = metric_state(
                            front_result[
                                "head_shift"
                            ],
                            0.15,
                            0.30,
                            "HEAD OK",
                            "HEAD SHIFT"
                        )

                        shoulder_state = metric_state(
                            front_result[
                                "shoulder_tilt"
                            ],
                            0.08,
                            0.16,
                            "SHOULDERS OK",
                            "SHOULDER TILT"
                        )

                        center_state = metric_state(
                            front_result[
                                "center_shift"
                            ],
                            0.15,
                            0.30,
                            "CENTER OK",
                            "CENTER SHIFT"
                        )

                        sync_state = metric_state(
                            front_result[
                                "shoulder_hip_sync"
                            ],
                            0.08,
                            0.18,
                            "SYNC OK",
                            "SYNC CHECK"
                        )

                        lines = [
                            "Mode: FRONT",
                            (
                                f"View count: "
                                f"{front_result['count']}"
                            ),
                            (
                                f"Session reps: "
                                f"{len(performance.reps)}"
                            ),
                            (
                                f"Phase: "
                                f"{front_result['phase']}"
                            ),
                            (
                                f"ROM: "
                                f"{front_result['rom']:.2f}"
                            ),
                            (
                                f"Shoulder/Hip down: "
                                f"{front_result['shoulder_descent']:.2f} / "
                                f"{front_result['hip_descent']:.2f}"
                            ),
                            (
                                f"Head: "
                                f"{front_result['head_shift']:.2f} "
                                f"{head_state}"
                            ),
                            (
                                f"Shoulder level: "
                                f"{front_result['shoulder_tilt']:.2f} "
                                f"{shoulder_state}"
                            ),
                            (
                                f"Body center: "
                                f"{front_result['center_shift']:.2f} "
                                f"{center_state}"
                            ),
                            (
                                f"Shoulder-Hip sync: "
                                f"{front_result['shoulder_hip_sync']:.2f} "
                                f"{sync_state}"
                            ),
                            (
                                f"Left knee: "
                                f"{front_form['left_state']}"
                            ),
                            (
                                f"Right knee: "
                                f"{front_form['right_state']}"
                            ),
                            (
                                f"Symmetry: "
                                f"{front_form['symmetry_state']} "
                                f"({front_form['symmetry_value']:.2f})"
                            ),
                            (
                                f"L/R inward: "
                                f"{front_form['left_value']:.2f} / "
                                f"{front_form['right_value']:.2f}"
                            )
                        ]

                        if last_completed_rep:
                            lines.extend([
                                "--- LAST REP ---",
                                (
                                    f"Quality: "
                                    f"{last_completed_rep['quality_score']:.1f} "
                                    f"{last_completed_rep['quality_label']}"
                                ),
                                (
                                    f"Tempo D/B/U: "
                                    f"{format_time(last_completed_rep.get('descent_time'))} / "
                                    f"{format_time(last_completed_rep.get('bottom_time'))} / "
                                    f"{format_time(last_completed_rep.get('ascent_time'))}"
                                )
                            ])

                        draw_lines(
                            frame,
                            lines,
                            x=25,
                            y=35,
                            font_scale=0.48,
                            step=27
                        )

                elif view == "SIDE":
                    left_visibility = (
                        left_hip["visibility"]
                        + left_knee["visibility"]
                        + left_ankle["visibility"]
                    ) / 3

                    right_visibility = (
                        right_hip["visibility"]
                        + right_knee["visibility"]
                        + right_ankle["visibility"]
                    ) / 3

                    if left_visibility >= right_visibility:
                        active_leg = "LEFT"
                        shoulder = left_shoulder[
                            "point"
                        ]
                        hip = left_hip[
                            "point"
                        ]
                        knee = left_knee[
                            "point"
                        ]
                        ankle = left_ankle[
                            "point"
                        ]
                    else:
                        active_leg = "RIGHT"
                        shoulder = right_shoulder[
                            "point"
                        ]
                        hip = right_hip[
                            "point"
                        ]
                        knee = right_knee[
                            "point"
                        ]
                        ankle = right_ankle[
                            "point"
                        ]

                    side_result = side_analyzer.analyze(
                        nose["point"],
                        shoulder,
                        hip,
                        knee,
                        ankle
                    )

                    if (
                        side_result["rep_completed"]
                        and side_result["rep_summary"]
                    ):
                        last_completed_rep = (
                            save_completed_rep(
                                side_result["rep_summary"],
                                performance,
                                database,
                                session_id
                            )
                        )

                    trunk_state = metric_state(
                        side_result[
                            "trunk_lean"
                        ],
                        17.0,
                        20.0,
                        "TRUNK OK",
                        "LEANING TOO MUCH"
                    )

                    head_state = metric_state(
                        side_result[
                            "head_forward"
                        ],
                        0.35,
                        0.55,
                        "HEAD OK",
                        "HEAD FORWARD"
                    )

                    sync_state = metric_state(
                        side_result[
                            "shoulder_hip_sync"
                        ],
                        0.20,
                        0.40,
                        "SYNC OK",
                        "HIP/SHOULDER DESYNC"
                    )

                    lines = [
                        "Mode: SIDE",
                        (
                            f"Tracking: "
                            f"{active_leg}"
                        ),
                        (
                            f"View count: "
                            f"{side_result['count']}"
                        ),
                        (
                            f"Session reps: "
                            f"{len(performance.reps)}"
                        ),
                        (
                            f"Phase: "
                            f"{side_result['phase']}"
                        ),
                        (
                            f"Knee: "
                            f"{side_result['knee_angle']:.1f}"
                        ),
                        (
                            f"Hip: "
                            f"{side_result['hip_angle']:.1f}"
                        ),
                        (
                            f"ROM: "
                            f"{side_result['rom_degrees']:.1f} deg"
                        ),
                        (
                            f"Depth: "
                            f"{side_result['depth']}"
                        ),
                        (
                            f"Trunk: "
                            f"{side_result['trunk_lean']:.1f} "
                            f"{trunk_state}"
                        ),
                        (
                            f"Head: "
                            f"{side_result['head_forward']:.2f} "
                            f"{head_state}"
                        ),
                        (
                            f"Shoulder-Hip sync: "
                            f"{side_result['shoulder_hip_sync']:.2f} "
                            f"{sync_state}"
                        )
                    ]

                    if last_completed_rep:
                        lines.extend([
                            "--- LAST REP ---",
                            (
                                f"Quality: "
                                f"{last_completed_rep['quality_score']:.1f} "
                                f"{last_completed_rep['quality_label']}"
                            ),
                            (
                                f"Tempo D/B/U: "
                                f"{format_time(last_completed_rep.get('descent_time'))} / "
                                f"{format_time(last_completed_rep.get('bottom_time'))} / "
                                f"{format_time(last_completed_rep.get('ascent_time'))}"
                            ),
                            (
                                f"Total: "
                                f"{format_time(last_completed_rep.get('total_time'))}"
                            )
                        ])

                    draw_lines(
                        frame,
                        lines,
                        x=25,
                        y=35,
                        font_scale=0.48,
                        step=27
                    )

                else:
                    cv2.putText(
                        frame,
                        "Adjust camera angle",
                        (
                            30,
                            50
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (
                            255,
                            255,
                            255
                        ),
                        2
                    )

                draw_set_panel(
                    frame,
                    performance,
                    width
                )

                cv2.putText(
                    frame,
                    (
                        f"View: {view} | "
                        f"Raw: {raw_view} | "
                        f"Ratio: {view_ratio:.2f}"
                    ),
                    (
                        30,
                        height - 50
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (
                        255,
                        255,
                        255
                    ),
                    2
                )

                cv2.putText(
                    frame,
                    position,
                    (
                        30,
                        height - 20
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (
                        255,
                        255,
                        255
                    ),
                    2
                )

            else:
                cv2.putText(
                    frame,
                    "Body not detected",
                    (
                        30,
                        50
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (
                        255,
                        255,
                        255
                    ),
                    2
                )

            cv2.imshow(
                window_name,
                frame
            )

            key = cv2.waitKey(1) & 0xFF

            if key in (
                ord("q"),
                ord("Q"),
                27
            ):
                break

    finally:
        total_reps = len(
            performance.reps
        )

        good_reps = sum(
            1
            for rep in performance.reps
            if rep.get(
                "quality_score",
                0
            ) >= 75
        )

        try:
            database.finish_session(
                session_id,
                total_reps,
                total_reps,
                good_reps
            )
        except Exception as error:
            print(
                f"Database session save warning: {error}"
            )

        summary = performance.get_set_summary()

        print(
            "SESSION SUMMARY | "
            f"Reps {summary['reps']} | "
            f"Average {summary['average_score']:.1f} | "
            f"Trend {summary['trend']}"
        )

        cap.release()
        cv2.destroyAllWindows()

        print(
            "程序已退出"
        )


if __name__ == "__main__":
    run_camera()
