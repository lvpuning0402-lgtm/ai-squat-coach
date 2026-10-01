import cv2

from pose.detector import PoseDetector
from pose.view_detector import ViewDetector

from exercises.front_squat import FrontSquatAnalyzer
from exercises.side_squat import SideSquatAnalyzer

from feedback.front_feedback import FrontFeedback
from feedback.performance import SessionPerformanceAnalyzer

from data.database import TrainingDatabase


DISPLAY_MODES = [
    "SIMPLE",
    "DETAIL",
    "DEBUG"
]


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


def update_side_leg_tracking(
    active_leg,
    left_visibility,
    right_visibility,
    switch_candidate,
    switch_frames,
    side_analyzer
):
    preferred_leg = (
        "LEFT"
        if left_visibility >= right_visibility
        else "RIGHT"
    )

    switched = False

    if active_leg is None:
        active_leg = preferred_leg
        switch_candidate = None
        switch_frames = 0
        side_analyzer.reset()

        return (
            active_leg,
            switch_candidate,
            switch_frames,
            True
        )

    if side_analyzer.phase != "STANDING":
        return (
            active_leg,
            None,
            0,
            False
        )

    if active_leg == "LEFT":
        active_visibility = left_visibility
        other_visibility = right_visibility
        other_leg = "RIGHT"
    else:
        active_visibility = right_visibility
        other_visibility = left_visibility
        other_leg = "LEFT"

    emergency_switch = (
        active_visibility < 0.20
        and other_visibility > 0.65
    )

    normal_switch = (
        other_visibility
        - active_visibility
        >= 0.18
    )

    if emergency_switch:
        active_leg = other_leg
        switch_candidate = None
        switch_frames = 0
        side_analyzer.reset()
        switched = True

    elif normal_switch:
        if switch_candidate == other_leg:
            switch_frames += 1
        else:
            switch_candidate = other_leg
            switch_frames = 1

        if switch_frames >= 10:
            active_leg = other_leg
            switch_candidate = None
            switch_frames = 0
            side_analyzer.reset()
            switched = True

    else:
        switch_candidate = None
        switch_frames = 0

    return (
        active_leg,
        switch_candidate,
        switch_frames,
        switched
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


def draw_transparent_panel(
    frame,
    x,
    y,
    width,
    height,
    alpha=0.56
):
    overlay = frame.copy()

    cv2.rectangle(
        overlay,
        (
            x,
            y
        ),
        (
            x + width,
            y + height
        ),
        (
            15,
            15,
            15
        ),
        -1
    )

    cv2.addWeighted(
        overlay,
        alpha,
        frame,
        1 - alpha,
        0,
        frame
    )

    cv2.rectangle(
        frame,
        (
            x,
            y
        ),
        (
            x + width,
            y + height
        ),
        (
            85,
            85,
            85
        ),
        1
    )


def draw_text(
    frame,
    text,
    x,
    y,
    scale=0.47,
    thickness=1
):
    cv2.putText(
        frame,
        str(text),
        (
            x,
            y
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (
            245,
            245,
            245
        ),
        thickness,
        cv2.LINE_AA
    )


def draw_panel(
    frame,
    title,
    lines,
    x,
    y,
    width,
    line_height=23,
    title_height=29
):
    panel_height = (
        title_height
        + 16
        + line_height * len(lines)
    )

    draw_transparent_panel(
        frame,
        x,
        y,
        width,
        panel_height
    )

    draw_text(
        frame,
        title,
        x + 14,
        y + 23,
        scale=0.58,
        thickness=2
    )

    cv2.line(
        frame,
        (
            x + 12,
            y + title_height
        ),
        (
            x + width - 12,
            y + title_height
        ),
        (
            105,
            105,
            105
        ),
        1
    )

    text_y = (
        y
        + title_height
        + 24
    )

    for line in lines:
        draw_text(
            frame,
            line,
            x + 14,
            text_y,
            scale=0.46,
            thickness=1
        )

        text_y += line_height

    return panel_height


def draw_interface(
    frame,
    display_mode,
    view,
    raw_view,
    view_ratio,
    position,
    simple_lines,
    detail_live_lines,
    detail_form_lines,
    debug_lines,
    last_completed_rep,
    performance
):
    height = frame.shape[0]
    width = frame.shape[1]

    margin = 16
    gap = 14
    footer_space = 32

    # 统一卡片宽度，确保左右两列不会重叠。
    column_width = max(
        220,
        (
            width
            - margin * 2
            - gap
        ) // 2
    )

    left_x = margin
    right_x = (
        width
        - margin
        - column_width
    )

    top_y = margin

    summary = performance.get_set_summary()

    if display_mode == "SIMPLE":
        simple_status = [
            f"Mode: {view}",
            f"{position}"
        ] + simple_lines

        simple_width = min(
            280,
            width - margin * 2
        )

        draw_panel(
            frame,
            "AI SPORT COACH",
            simple_status,
            left_x,
            top_y,
            simple_width,
            line_height=24
        )

        if last_completed_rep:
            last_lines = [
                (
                    f"Rep #{last_completed_rep['rep']}  "
                    f"{last_completed_rep['quality_label']}"
                ),
                (
                    f"Quality: "
                    f"{last_completed_rep['quality_score']:.1f}"
                )
            ]

            last_height = (
                31
                + 16
                + 23 * len(last_lines)
            )

            draw_panel(
                frame,
                "LAST REP",
                last_lines,
                right_x,
                height
                - footer_space
                - last_height,
                column_width,
                line_height=23
            )

        return

    live_lines = [
        f"View: {view}",
        f"{position}"
    ] + detail_live_lines

    live_height = draw_panel(
        frame,
        "LIVE",
        live_lines,
        left_x,
        top_y,
        column_width,
        line_height=21
    )

    form_height = draw_panel(
        frame,
        "FORM",
        detail_form_lines,
        right_x,
        top_y,
        column_width,
        line_height=21
    )

    set_lines = []
    if summary["reps"] > 0:
        set_lines = [
            f"Reps: {summary['reps']}",
            f"Average: {summary['average_score']:.1f}",
            f"Best rep: #{summary['best_rep']}",
            f"Trend: {summary['trend']}",
            f"Main issue: {summary['top_issue']}"
        ]

    last_lines = []
    if last_completed_rep:
        last_lines = [
            (
                f"Rep #{last_completed_rep['rep']}  "
                f"{last_completed_rep['view']}"
            ),
            (
                f"Quality: "
                f"{last_completed_rep['quality_score']:.1f}  "
                f"{last_completed_rep['quality_label']}"
            ),
            (
                f"D/B/U: "
                f"{format_time(last_completed_rep.get('descent_time'))} / "
                f"{format_time(last_completed_rep.get('bottom_time'))} / "
                f"{format_time(last_completed_rep.get('ascent_time'))}"
            ),
            (
                f"Total: "
                f"{format_time(last_completed_rep.get('total_time'))}"
            )
        ]

    if display_mode == "DETAIL":
        if set_lines:
            set_height = (
                31
                + 16
                + 23 * len(set_lines)
            )

            draw_panel(
                frame,
                "SET SUMMARY",
                set_lines,
                left_x,
                height
                - footer_space
                - set_height,
                column_width,
                line_height=23
            )

        if last_lines:
            last_height = (
                31
                + 16
                + 23 * len(last_lines)
            )

            draw_panel(
                frame,
                "LAST REP",
                last_lines,
                right_x,
                height
                - footer_space
                - last_height,
                column_width,
                line_height=23
            )

        return

    # DEBUG 模式采用四角商务布局：
    # 左上 LIVE，右上 FORM，左下 DEBUG，右下 SET / LAST REP。
    # 中央动作主体区域完全留空。
    debug_lines_to_draw = debug_lines[:10]

    debug_width = max(
        220,
        int(
            column_width * 0.82
        )
    )

    debug_height = (
        29
        + 14
        + 18 * len(debug_lines_to_draw)
    )

    debug_y = (
        height
        - footer_space
        - debug_height
    )

    min_debug_y = (
        top_y
        + live_height
        + gap
    )

    debug_y = max(
        min_debug_y,
        debug_y
    )

    draw_panel(
        frame,
        "DEBUG DATA",
        debug_lines_to_draw,
        left_x,
        debug_y,
        debug_width,
        line_height=18,
        title_height=29
    )

    right_bottom = (
        height
        - footer_space
    )

    if last_lines:
        last_height = (
            31
            + 16
            + 21 * len(last_lines)
        )

        last_y = (
            right_bottom
            - last_height
        )

        draw_panel(
            frame,
            "LAST REP",
            last_lines,
            right_x,
            last_y,
            column_width,
            line_height=21
        )

        right_bottom = (
            last_y
            - gap
        )

    if set_lines:
        set_height = (
            31
            + 16
            + 21 * len(set_lines)
        )

        set_y = (
            right_bottom
            - set_height
        )

        min_set_y = (
            top_y
            + form_height
            + gap
        )

        if set_y >= min_set_y:
            draw_panel(
                frame,
                "SET SUMMARY",
                set_lines,
                right_x,
                set_y,
                column_width,
                line_height=21
            )

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
    side_switch_candidate = None
    side_switch_frames = 0
    side_leg_switched = False

    last_view_state = None
    last_completed_rep = None

    display_mode_index = 0

    print(
        "Multi-angle squat analysis enabled"
    )
    print(
        "Three-level UI enabled: SIMPLE / DETAIL / DEBUG"
    )
    print(
        f"Session ID: {session_id}"
    )
    print(
        "按 M 切换显示模式"
    )
    print(
        "按 Q / ESC 退出"
    )

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                break

            camera_height = frame.shape[0]
            camera_width = frame.shape[1]

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

            view = "UNKNOWN"
            raw_view = "UNKNOWN"
            view_ratio = 0.0
            position = "BODY NOT DETECTED"

            simple_lines = [
                "Waiting for body..."
            ]

            detail_live_lines = [
                "Waiting for body..."
            ]

            detail_form_lines = [
                "Keep full body visible"
            ]

            debug_lines = [
                "No debug data"
            ]

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
                    camera_width,
                    camera_height,
                    freeze=False
                )

                # 只要平滑后的原始视角进入中间区，
                # 就立即停止 FRONT / SIDE 动作分析。
                # 这样转身过程中不会沿用旧视角，更不会提前分析新视角。
                if raw_view == "TRANSITION":
                    effective_view = "TRANSITION"
                else:
                    effective_view = view

                if effective_view != last_view_state:
                    if effective_view == "TRANSITION":
                        front_analyzer.reset()
                        front_feedback.reset()
                        side_analyzer.reset()

                        side_switch_candidate = None
                        side_switch_frames = 0
                        side_leg_switched = False

                    elif (
                        last_view_state == "TRANSITION"
                        and effective_view == "FRONT"
                    ):
                        front_analyzer.reset()
                        front_feedback.reset()

                    elif (
                        last_view_state == "TRANSITION"
                        and effective_view == "SIDE"
                    ):
                        side_analyzer.reset()

                        side_switch_candidate = None
                        side_switch_frames = 0
                        side_leg_switched = False

                    last_view_state = effective_view

                view = effective_view

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
                            front_result["phase"],
                            front_result["rep_completed"]
                        )

                        if (
                            front_result["rep_completed"]
                            and front_result["rep_summary"]
                        ):
                            rep_summary = dict(
                                front_result["rep_summary"]
                            )

                            front_rep_metrics = (
                                front_form.get(
                                    "rep_metrics"
                                )
                                or {}
                            )

                            rep_summary.update(
                                front_rep_metrics
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
                            "OK",
                            "SHIFT"
                        )

                        shoulder_state = metric_state(
                            front_result[
                                "shoulder_tilt"
                            ],
                            0.08,
                            0.16,
                            "OK",
                            "TILT"
                        )

                        center_state = metric_state(
                            front_result[
                                "center_shift"
                            ],
                            0.15,
                            0.30,
                            "OK",
                            "SHIFT"
                        )

                        sync_state = metric_state(
                            front_result[
                                "shoulder_hip_sync"
                            ],
                            0.08,
                            0.18,
                            "OK",
                            "CHECK"
                        )

                        simple_lines = [
                            (
                                f"Phase: "
                                f"{front_result['phase']}"
                            ),
                            (
                                f"Reps: "
                                f"{len(performance.reps)}"
                            ),
                            (
                                f"Knees: "
                                f"{front_form['left_state']} / "
                                f"{front_form['right_state']}"
                            ),
                            (
                                f"Symmetry: "
                                f"{front_form['symmetry_state']}"
                            )
                        ]

                        detail_live_lines = [
                            (
                                f"Phase: "
                                f"{front_result['phase']}"
                            ),
                            (
                                f"Reps: "
                                f"{len(performance.reps)}"
                            ),
                            (
                                f"ROM: "
                                f"{front_result['rom']:.2f}"
                            )
                        ]

                        detail_form_lines = [
                            (
                                f"Head "
                                f"{front_result['head_shift']:.2f} "
                                f"[{head_state}]"
                            ),
                            (
                                f"Shoulders "
                                f"{front_result['shoulder_tilt']:.2f} "
                                f"[{shoulder_state}]"
                            ),
                            (
                                f"Center "
                                f"{front_result['center_shift']:.2f} "
                                f"[{center_state}]"
                            ),
                            (
                                f"Sync "
                                f"{front_result['shoulder_hip_sync']:.2f} "
                                f"[{sync_state}]"
                            ),
                            (
                                f"Knees "
                                f"{front_form['left_state']} / "
                                f"{front_form['right_state']}"
                            ),
                            (
                                f"Symmetry "
                                f"{front_form['symmetry_state']}"
                            )
                        ]

                        debug_lines = [
                            (
                                f"Raw view: "
                                f"{raw_view}"
                            ),
                            (
                                f"View ratio: "
                                f"{view_ratio:.2f}"
                            ),
                            (
                                f"Shoulder down: "
                                f"{front_result['shoulder_descent']:.3f}"
                            ),
                            (
                                f"Hip down: "
                                f"{front_result['hip_descent']:.3f}"
                            ),
                            (
                                f"Avg knee angle: "
                                f"{front_result['average_knee_angle']:.1f}"
                            ),
                            (
                                f"Inward L/R: "
                                f"{front_form['left_value']:.2f} / "
                                f"{front_form['right_value']:.2f}"
                            ),
                            (
                                f"Symmetry value: "
                                f"{front_form['symmetry_value']:.2f}"
                            ),
                            (
                                f"Velocity: "
                                f"{front_result['descent_velocity']:.4f}"
                            ),
                            (
                                f"Scale: "
                                f"{front_result['body_scale_ratio']:.2f}"
                            ),
                            (
                                f"Baseline reset: "
                                f"{front_result['baseline_reset']}"
                            )
                        ]

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

                    (
                        active_leg,
                        side_switch_candidate,
                        side_switch_frames,
                        side_leg_switched
                    ) = update_side_leg_tracking(
                        active_leg,
                        left_visibility,
                        right_visibility,
                        side_switch_candidate,
                        side_switch_frames,
                        side_analyzer
                    )

                    if active_leg == "LEFT":
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
                        "OK",
                        "TOO MUCH"
                    )

                    head_state = metric_state(
                        side_result[
                            "head_forward"
                        ],
                        0.35,
                        0.55,
                        "OK",
                        "FORWARD"
                    )

                    sync_state = metric_state(
                        side_result[
                            "shoulder_hip_sync"
                        ],
                        0.20,
                        0.40,
                        "OK",
                        "CHECK"
                    )

                    simple_lines = [
                        (
                            f"Phase: "
                            f"{side_result['phase']}"
                        ),
                        (
                            f"Reps: "
                            f"{len(performance.reps)}"
                        ),
                        (
                            f"Depth: "
                            f"{side_result['depth']}"
                        ),
                        (
                            f"Trunk: "
                            f"{trunk_state}"
                        )
                    ]

                    detail_live_lines = [
                        (
                            f"Phase: "
                            f"{side_result['phase']}"
                        ),
                        (
                            f"Reps: "
                            f"{len(performance.reps)}"
                        ),
                        (
                            f"Depth: "
                            f"{side_result['depth']}"
                        ),
                        (
                            f"ROM: "
                            f"{side_result['rom_degrees']:.1f} deg"
                        )
                    ]

                    detail_form_lines = [
                        (
                            f"Trunk "
                            f"{side_result['trunk_lean']:.1f} "
                            f"[{trunk_state}]"
                        ),
                        (
                            f"Head "
                            f"{side_result['head_forward']:.2f} "
                            f"[{head_state}]"
                        ),
                        (
                            f"Sync "
                            f"{side_result['shoulder_hip_sync']:.2f} "
                            f"[{sync_state}]"
                        )
                    ]

                    debug_lines = [
                        (
                            f"Raw view: "
                            f"{raw_view}"
                        ),
                        (
                            f"View ratio: "
                            f"{view_ratio:.2f}"
                        ),
                        (
                            f"Tracking: "
                            f"{active_leg}"
                        ),
                        (
                            f"Visibility L/R: "
                            f"{left_visibility:.2f} / "
                            f"{right_visibility:.2f}"
                        ),
                        (
                            f"Knee angle: "
                            f"{side_result['knee_angle']:.1f}"
                        ),
                        (
                            f"Hip angle: "
                            f"{side_result['hip_angle']:.1f}"
                        ),
                        (
                            f"Knee velocity: "
                            f"{side_result['knee_velocity']:.3f}"
                        ),
                        (
                            f"Scale: "
                            f"{side_result['body_scale_ratio']:.2f}"
                        ),
                        (
                            f"Baseline reset: "
                            f"{side_result['baseline_reset']}"
                        ),
                        (
                            f"Leg switched: "
                            f"{side_leg_switched}"
                        )
                    ]

                else:
                    simple_lines = [
                        "Adjust camera angle"
                    ]

                    detail_live_lines = [
                        "Adjust camera angle"
                    ]

                    detail_form_lines = [
                        "Turn FRONT or SIDE"
                    ]

                    debug_lines = [
                        f"Raw view: {raw_view}",
                        f"View ratio: {view_ratio:.2f}"
                    ]

            display_mode = DISPLAY_MODES[
                display_mode_index
            ]

            draw_interface(
                frame,
                display_mode,
                view,
                raw_view,
                view_ratio,
                position,
                simple_lines,
                detail_live_lines,
                detail_form_lines,
                debug_lines,
                last_completed_rep,
                performance
            )

            draw_text(
                frame,
                f"UI: {display_mode}  |  M = switch",
                16,
                camera_height - 12,
                scale=0.34,
                thickness=1
            )

            cv2.imshow(
                window_name,
                frame
            )

            key = cv2.waitKey(1) & 0xFF

            if key in (
                ord("m"),
                ord("M")
            ):
                display_mode_index = (
                    display_mode_index
                    + 1
                ) % len(
                    DISPLAY_MODES
                )

                print(
                    "UI MODE -> "
                    f"{DISPLAY_MODES[display_mode_index]}"
                )

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
            f"Trend {summary['trend']} | "
            f"Issue {summary['top_issue']}"
        )

        cap.release()
        cv2.destroyAllWindows()

        print(
            "程序已退出"
        )


if __name__ == "__main__":
    run_camera()
