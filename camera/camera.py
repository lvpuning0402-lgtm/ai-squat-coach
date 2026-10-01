from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from pose.detector import PoseDetector
from pose.view_detector import ViewDetector

from exercises.front_squat import FrontSquatAnalyzer
from exercises.side_squat import SideSquatAnalyzer

from feedback.front_feedback import FrontFeedback
from feedback.performance import SessionPerformanceAnalyzer
from feedback.insights import SessionInsightBuilder

from data.database import TrainingDatabase
from reports.session_report import SessionReportExporter
from reports.history_report import HistoryReportExporter
from standards.squat_standard import (
    STANDARD_NAME,
    VISION_TOLERANCE,
)
from standards.competition_profiles import DETAIL_TOLERANCE


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


def detail_lower_state(
    value,
    good_max,
    review_min
):
    if value is None:
        return "INFO"

    if value <= good_max:
        return "PASS"

    if value >= review_min:
        return "REVIEW"

    return "WATCH"


def detail_higher_state(
    value,
    pass_min,
    review_below
):
    if value is None:
        return "INFO"

    if value >= pass_min:
        return "PASS"

    if value < review_below:
        return "REVIEW"

    return "WATCH"


def ascent_control_state(
    value,
    phase
):
    if (
        value is None
        or phase != "ASCENDING"
    ):
        return "READY"

    return metric_state(
        value,
        VISION_TOLERANCE[
            "ascent_progress_good_max"
        ],
        VISION_TOLERANCE[
            "ascent_progress_bad_min"
        ],
        "OK",
        "CHECK"
    )


def format_time(value):
    if value is None:
        return "--"

    return f"{value:.2f}s"


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

    confidence_text = (
        "VALID"
        if analyzed.get(
            "analysis_valid",
            True
        )
        else "EXCLUDED"
    )

    print(
        "REP COMPLETE | "
        f"#{analyzed['rep']} | "
        f"{analyzed['view']} | "
        f"Quality {analyzed['quality_score']:.1f} | "
        f"{analyzed['quality_label']} | "
        f"{confidence_text}"
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


def _rep_timeline_line(
    rep
):
    rep_number = rep.get(
        "rep",
        "-"
    )
    view = rep.get(
        "view",
        "UNKNOWN"
    )

    valid = (
        rep.get(
            "analysis_valid",
            True
        )
        and rep.get(
            "set_valid",
            True
        )
    )

    if not valid:
        status = "EXCLUDED"
    elif rep.get(
        "standard_met",
        False
    ):
        status = "PASS"
    else:
        status = "REVIEW"

    score = rep.get(
        "quality_score"
    )

    score_text = (
        f"{float(score):.1f}"
        if score is not None
        else "--"
    )

    issues = rep.get(
        "issues",
        []
    )

    detail_warnings = rep.get(
        "detail_warnings",
        []
    )

    if issues:
        issue_text = ", ".join(
            str(issue).replace(
                "_",
                " "
            )
            for issue in issues
        )
    elif detail_warnings:
        issue_text = (
            "DETAIL "
            + str(
                detail_warnings[
                    0
                ]
            ).replace(
                "_",
                " "
            )
        )
    else:
        issue_text = "OK"

    try:
        rep_text = (
            f"#{int(rep_number):02d}"
        )
    except (
        TypeError,
        ValueError
    ):
        rep_text = "#--"

    return (
        f"{rep_text}  "
        f"{view:<5}  "
        f"{status:<8}  "
        f"{score_text:>5}  "
        f"{issue_text}"
    )


def build_session_summary_frame(
    reps,
    summary,
    session_type,
    width=1080,
    height=720
):
    frame = np.full(
        (
            height,
            width,
            3
        ),
        24,
        dtype=np.uint8
    )

    coach_feedback = SessionInsightBuilder().build(
        reps,
        summary,
        session_type=session_type
    )

    margin = 28
    gap = 18
    column_width = (
        width
        - margin * 2
        - gap
    ) // 2

    draw_text(
        frame,
        "AI SPORT COACH",
        margin,
        44,
        scale=0.82,
        thickness=2
    )

    draw_text(
        frame,
        "SESSION COMPLETE",
        margin,
        74,
        scale=0.52,
        thickness=1
    )

    draw_text(
        frame,
        f"{session_type}  |  {STANDARD_NAME}",
        width - 330,
        48,
        scale=0.46,
        thickness=1
    )

    result_lines = [
        (
            f"Valid reps: "
            f"{summary.get('valid_reps', 0)}/"
            f"{summary.get('reps', 0)}"
        ),
        (
            f"Average score: "
            f"{summary.get('average_score', 0.0):.1f}"
        ),
        (
            f"Standard pass: "
            f"{summary.get('standard_passes', 0)}/"
            f"{summary.get('valid_reps', 0)} "
            f"({summary.get('standard_pass_rate', 0.0):.0f}%)"
        ),
        (
            f"Detail score: "
            f"{summary.get('average_detail_score', 0.0):.1f}"
        ),
        (
            f"Detail watch: "
            f"{summary.get('detail_watch_reps', 0)}/"
            f"{summary.get('valid_reps', 0)}"
        ),
        (
            f"Best rep: #"
            f"{summary.get('best_rep') or '--'}"
        ),
    ]

    if summary.get(
        "side_reps",
        0
    ) > 0:
        result_lines.extend([
            (
                f"General depth: "
                f"{summary.get('side_depth_passes', 0)}/"
                f"{summary.get('side_reps', 0)} "
                f"({summary.get('side_depth_pass_rate', 0.0):.0f}%)"
            ),
            (
                f"IPF proxy: "
                f"{summary.get('side_ipf_proxy_passes', 0)}/"
                f"{summary.get('side_reps', 0)} "
                f"({summary.get('side_ipf_proxy_rate', 0.0):.0f}%)"
            ),
        ])

    if session_type == "TRAINING":
        result_lines.extend([
            (
                f"Consistency: "
                f"{summary.get('consistency_label', 'NO DATA')}"
            ),
            (
                f"Set trend: "
                f"{summary.get('trend', 'NO DATA')}"
            ),
        ])
    else:
        result_lines.append(
            "TEST protocol: no formal trend"
        )

    result_height = draw_panel(
        frame,
        "RESULT",
        result_lines,
        margin,
        104,
        column_width,
        line_height=25,
        title_height=32
    )

    coach_lines = [
        coach_feedback[
            "ui_lines"
        ][0],
        coach_feedback[
            "ui_lines"
        ][1],
        coach_feedback[
            "ui_lines"
        ][2],
        (
            f"Confidence: "
            f"{coach_feedback.get('confidence', 'LOW')}"
        ),
    ]

    if coach_feedback.get(
        "main_issue",
        "NONE"
    ) != "NONE":
        coach_lines.append(
            (
                f"Issue rate: "
                f"{coach_feedback.get('main_issue_rate', 0.0):.0f}%"
            )
        )
    else:
        coach_lines.append(
            "No repeated standard issue"
        )

    coach_height = draw_panel(
        frame,
        "AI COACH",
        coach_lines,
        margin
        + column_width
        + gap,
        104,
        column_width,
        line_height=25,
        title_height=32
    )

    timeline_reps = reps[
        -7:
    ]

    timeline_lines = [
        "REP   VIEW   STATUS    SCORE   ISSUE"
    ]

    timeline_lines.extend(
        _rep_timeline_line(
            rep
        )
        for rep in timeline_reps
    )

    if len(
        reps
    ) > len(
        timeline_reps
    ):
        timeline_lines.append(
            (
                f"Showing last "
                f"{len(timeline_reps)} "
                f"of {len(reps)} reps"
            )
        )

    timeline_y = (
        104
        + max(
            result_height,
            coach_height
        )
        + 18
    )

    draw_panel(
        frame,
        "REP TIMELINE",
        timeline_lines,
        margin,
        timeline_y,
        width - margin * 2,
        line_height=22,
        title_height=32
    )

    draw_text(
        frame,
        "Q / ESC / ENTER = CLOSE",
        margin,
        height - 20,
        scale=0.40,
        thickness=1
    )

    return frame


def show_session_summary_screen(
    window_name,
    reps,
    summary,
    session_type
):
    summary_frame = build_session_summary_frame(
        reps,
        summary,
        session_type
    )

    try:
        cv2.imshow(
            window_name,
            summary_frame
        )

        print(
            "训练总结页面已显示，"
            "按 Q / ESC / Enter 关闭。"
        )

        while True:
            key = (
                cv2.waitKey(
                    50
                )
                & 0xFF
            )

            if key in (
                ord("q"),
                ord("Q"),
                27,
                10,
                13
            ):
                break

            try:
                visible = cv2.getWindowProperty(
                    window_name,
                    cv2.WND_PROP_VISIBLE
                )

                if visible < 1:
                    break
            except cv2.error:
                break

    except cv2.error as error:
        print(
            f"Session summary screen warning: {error}"
        )


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
    performance,
    session_type
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

    coach_feedback = SessionInsightBuilder().build(
        performance.reps,
        summary,
        session_type=session_type
    )

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
            (
                f"Reps: {summary['valid_reps']}/"
                f"{summary['reps']} valid"
            ),
            f"Average score: {summary['average_score']:.1f}",
            (
                f"Standard: {summary['standard_passes']}/"
                f"{summary['valid_reps']} pass "
                f"({summary['standard_pass_rate']:.0f}%)"
            )
        ]

        if summary.get(
            "side_reps",
            0
        ) > 0:
            set_lines.extend([
                (
                    f"Depth: {summary['side_depth_passes']}/"
                    f"{summary['side_reps']} general "
                    f"({summary['side_depth_pass_rate']:.0f}%)"
                ),
                (
                    f"IPF proxy: "
                    f"{summary['side_ipf_proxy_passes']}/"
                    f"{summary['side_reps']} "
                    f"({summary['side_ipf_proxy_rate']:.0f}%)"
                )
            ])

        set_lines.extend([
            f"Best rep: #{summary['best_rep']}",
            f"Main issue: {summary['top_issue']}"
        ])

        if session_type == "TRAINING":
            set_lines.extend([
                f"Trend: {summary['trend']}",
                f"Consistency: {summary['consistency_label']}"
            ])
        else:
            set_lines.append(
                "Trend/consistency: N/A in TEST"
            )

        set_lines.extend([
            "Coach: "
            + coach_feedback[
                "ui_lines"
            ][1],
            coach_feedback[
                "ui_lines"
            ][2]
        ])

    last_lines = []
    if last_completed_rep:
        last_lines = [
            (
                f"Rep #{last_completed_rep['rep']}  "
                f"{last_completed_rep['view']}"
            ),
            (
                f"Standard: "
                + (
                    "PASS"
                    if last_completed_rep.get(
                        "standard_met",
                        False
                    )
                    else "REVIEW"
                )
            ),
            (
                f"Quality: "
                f"{last_completed_rep['quality_score']:.1f}  "
                f"{last_completed_rep['quality_label']}"
            ),
            (
                f"Detail: "
                f"{last_completed_rep.get('detail_score', 0.0):.1f}  "
                f"{last_completed_rep.get('detail_label', 'INFO')}"
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

    session_type = "TEST"

    database = TrainingDatabase()
    session_id = database.start_session(
        session_type=session_type
    )

    report_exporter = SessionReportExporter()
    history_exporter = HistoryReportExporter()

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

    user_requested_exit = False
    display_mode_index = 0

    depth_capture_dir = Path(
        "reports"
    ) / "depth_captures"
    depth_capture_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    previous_side_depth_margin = None
    depth_capture_pending = []
    depth_capture_index = 0
    last_depth_capture_frame = {
        "GENERAL_PARALLEL": -1000,
        "IPF_PROXY": -1000
    }
    depth_capture_notice = None
    depth_capture_notice_frames = 0

    session_diagnostics = {
        "frames_total": 0,
        "body_ready_frames": 0,
        "front_frames": 0,
        "side_frames": 0,
        "transition_frames": 0,
        "unknown_frames": 0,
        "front_aborts": 0,
        "side_aborts": 0,
        "front_baseline_resets": 0,
        "side_baseline_resets": 0,
        "last_view": "UNKNOWN",
        "last_front_phase": None,
        "last_side_phase": None,
        "max_front_descent": 0.0,
        "min_side_knee_angle": None,
        "max_side_depth_margin": None
    }

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
        "按 T 切换 TEST / TRAINING（完成第一个 Rep 前）"
    )
    print(
        "按 Q / ESC 结束并查看本组总结"
    )

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                break

            session_diagnostics[
                "frames_total"
            ] += 1

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
                session_diagnostics[
                    "body_ready_frames"
                ] += 1

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

                session_diagnostics[
                    "last_view"
                ] = view

                if view == "FRONT":
                    session_diagnostics[
                        "front_frames"
                    ] += 1
                elif view == "SIDE":
                    session_diagnostics[
                        "side_frames"
                    ] += 1
                elif view == "TRANSITION":
                    session_diagnostics[
                        "transition_frames"
                    ] += 1
                else:
                    session_diagnostics[
                        "unknown_frames"
                    ] += 1

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
                        session_diagnostics[
                            "last_front_phase"
                        ] = front_result[
                            "phase"
                        ]
                        session_diagnostics[
                            "max_front_descent"
                        ] = max(
                            session_diagnostics[
                                "max_front_descent"
                            ],
                            front_result.get(
                                "combined_descent",
                                0.0
                            )
                        )

                        if front_result.get(
                            "rep_aborted",
                            False
                        ):
                            session_diagnostics[
                                "front_aborts"
                            ] += 1

                        if front_result.get(
                            "baseline_reset",
                            False
                        ):
                            session_diagnostics[
                                "front_baseline_resets"
                            ] += 1

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

                        sync_state = ascent_control_state(
                            front_result.get(
                                "ascent_sync_error"
                            ),
                            front_result[
                                "phase"
                            ]
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
                                f"Ascent control: "
                                f"{sync_state}"
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

                        head_detail = detail_lower_state(
                            front_result[
                                "head_shift"
                            ],
                            DETAIL_TOLERANCE[
                                "head_shift_good_max"
                            ],
                            DETAIL_TOLERANCE[
                                "head_shift_review_min"
                            ]
                        )

                        shoulder_detail = detail_lower_state(
                            front_result[
                                "shoulder_tilt"
                            ],
                            DETAIL_TOLERANCE[
                                "shoulder_tilt_good_max"
                            ],
                            DETAIL_TOLERANCE[
                                "shoulder_tilt_review_min"
                            ]
                        )

                        hip_detail = detail_lower_state(
                            front_result[
                                "hip_tilt"
                            ],
                            DETAIL_TOLERANCE[
                                "hip_tilt_good_max"
                            ],
                            DETAIL_TOLERANCE[
                                "hip_tilt_review_min"
                            ]
                        )

                        center_detail = detail_lower_state(
                            front_result[
                                "center_shift"
                            ],
                            DETAIL_TOLERANCE[
                                "center_shift_good_max"
                            ],
                            DETAIL_TOLERANCE[
                                "center_shift_review_min"
                            ]
                        )

                        knee_sym_detail = detail_lower_state(
                            front_result[
                                "knee_angle_asymmetry"
                            ],
                            DETAIL_TOLERANCE[
                                "knee_angle_asym_good_max"
                            ],
                            DETAIL_TOLERANCE[
                                "knee_angle_asym_review_min"
                            ]
                        )

                        detail_form_lines = [
                            (
                                f"Knees "
                                f"{front_form['left_state']} / "
                                f"{front_form['right_state']}"
                            ),
                            (
                                "Ascent sync "
                                + (
                                    f"{front_result['ascent_sync_error']:.2f}"
                                    if front_result.get(
                                        "ascent_sync_error"
                                    ) is not None
                                    else "--"
                                )
                                + f" [{sync_state}]"
                            ),
                            (
                                f"Shoulder level "
                                f"{front_result['shoulder_tilt']:.2f} "
                                f"[{shoulder_detail}]"
                            ),
                            (
                                f"Hip level "
                                f"{front_result['hip_tilt']:.2f} "
                                f"[{hip_detail}]"
                            ),
                            (
                                f"Center balance "
                                f"{front_result['center_shift']:.2f} "
                                f"[{center_detail}]"
                            ),
                            (
                                f"Head control "
                                f"{front_result['head_shift']:.2f} "
                                f"[{head_detail}]"
                            ),
                            (
                                f"Knee symmetry "
                                f"{front_result['knee_angle_asymmetry']:.1f} deg "
                                f"[{knee_sym_detail}]"
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
                                f"Knee L/R: "
                                f"{front_result['left_knee_angle']:.1f} / "
                                f"{front_result['right_knee_angle']:.1f}"
                            ),
                            (
                                f"Hip tilt: "
                                f"{front_result['hip_tilt']:.3f}"
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

                    session_diagnostics[
                        "last_side_phase"
                    ] = side_result[
                        "phase"
                    ]

                    current_knee = side_result.get(
                        "knee_angle"
                    )
                    if current_knee is not None:
                        previous_min = session_diagnostics[
                            "min_side_knee_angle"
                        ]
                        session_diagnostics[
                            "min_side_knee_angle"
                        ] = (
                            current_knee
                            if previous_min is None
                            else min(
                                previous_min,
                                current_knee
                            )
                        )

                    current_depth_margin = side_result.get(
                        "depth_margin"
                    )
                    if current_depth_margin is not None:
                        previous_max = session_diagnostics[
                            "max_side_depth_margin"
                        ]
                        session_diagnostics[
                            "max_side_depth_margin"
                        ] = (
                            current_depth_margin
                            if previous_max is None
                            else max(
                                previous_max,
                                current_depth_margin
                            )
                        )

                        general_depth_min = VISION_TOLERANCE[
                            "general_depth_margin_min"
                        ]
                        ipf_depth_min = VISION_TOLERANCE[
                            "ipf_depth_margin_min"
                        ]

                        crossing_labels = []

                        if (
                            previous_side_depth_margin
                            is not None
                            and side_result[
                                "phase"
                            ] in (
                                "DESCENDING",
                                "BOTTOM"
                            )
                        ):
                            if (
                                previous_side_depth_margin
                                < general_depth_min
                                <= current_depth_margin
                            ):
                                crossing_labels.append(
                                    "GENERAL_PARALLEL"
                                )

                            if (
                                previous_side_depth_margin
                                < ipf_depth_min
                                <= current_depth_margin
                            ):
                                crossing_labels.append(
                                    "IPF_PROXY"
                                )

                        for crossing_label in crossing_labels:
                            label_last_frame = (
                                last_depth_capture_frame.get(
                                    crossing_label,
                                    -1000
                                )
                            )

                            if (
                                session_diagnostics[
                                    "frames_total"
                                ]
                                - label_last_frame
                                < 12
                            ):
                                continue

                            depth_capture_pending.append({
                                "label": crossing_label,
                                "margin": float(
                                    current_depth_margin
                                ),
                                "knee_angle": float(
                                    side_result[
                                        "knee_angle"
                                    ]
                                ),
                                "hip_angle": float(
                                    side_result[
                                        "hip_angle"
                                    ]
                                ),
                                "pose_frame": frame.copy()
                            })

                            last_depth_capture_frame[
                                crossing_label
                            ] = session_diagnostics[
                                "frames_total"
                            ]

                        previous_side_depth_margin = float(
                            current_depth_margin
                        )

                    if side_result.get(
                        "rep_aborted",
                        False
                    ):
                        session_diagnostics[
                            "side_aborts"
                        ] += 1

                    if side_result.get(
                        "baseline_reset",
                        False
                    ):
                        session_diagnostics[
                            "side_baseline_resets"
                        ] += 1

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

                    sync_state = ascent_control_state(
                        side_result.get(
                            "ascent_sync_error"
                        ),
                        side_result[
                            "phase"
                        ]
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
                            f"Ascent control: "
                            f"{sync_state}"
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

                    side_head_detail = detail_lower_state(
                        side_result[
                            "head_forward"
                        ],
                        DETAIL_TOLERANCE[
                            "side_head_forward_good_max"
                        ],
                        DETAIL_TOLERANCE[
                            "side_head_forward_review_min"
                        ]
                    )

                    ipf_state = (
                        "READY"
                        if side_result[
                            "phase"
                        ] == "STANDING"
                        else (
                            "PASS"
                            if side_result[
                                "ipf_depth_proxy_met"
                            ]
                            else "REVIEW"
                        )
                    )

                    detail_form_lines = [
                        (
                            f"Depth "
                            f"{side_result['depth']}"
                        ),
                        (
                            f"IPF depth proxy "
                            f"[{ipf_state}]"
                        ),
                        (
                            "Ascent sync "
                            + (
                                f"{side_result['ascent_sync_error']:.2f}"
                                if side_result.get(
                                    "ascent_sync_error"
                                ) is not None
                                else "--"
                            )
                            + f" [{sync_state}]"
                        ),
                        (
                            f"Knee angle "
                            f"{side_result['knee_angle']:.1f} deg [INFO]"
                        ),
                        (
                            f"Hip angle "
                            f"{side_result['hip_angle']:.1f} deg [INFO]"
                        ),
                        (
                            f"Trunk lean "
                            f"{side_result['trunk_lean']:.1f} deg [INFO]"
                        ),
                        (
                            f"Shin angle "
                            f"{side_result['shin_angle']:.1f} deg [INFO]"
                        ),
                        (
                            f"Head control "
                            f"{side_result['head_forward']:.2f} "
                            f"[{side_head_detail}]"
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
                            f"Shin angle: "
                            f"{side_result['shin_angle']:.1f}"
                        ),
                        (
                            f"Depth margin: "
                            f"{side_result['depth_margin']:.3f}"
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

            simple_lines = [
                f"Standard: {STANDARD_NAME}",
                f"Session: {session_type}"
            ] + simple_lines

            detail_live_lines = [
                f"Standard: {STANDARD_NAME}",
                f"Session: {session_type}"
            ] + detail_live_lines

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
                performance,
                session_type
            )

            draw_text(
                frame,
                (
                    f"UI: {display_mode}  |  "
                    f"M = UI  |  T = {session_type}"
                ),
                16,
                camera_height - 12,
                scale=0.34,
                thickness=1
            )

            if depth_capture_pending:
                captures_to_save = list(
                    depth_capture_pending
                )
                depth_capture_pending.clear()

                for capture in captures_to_save:
                    depth_capture_index += 1

                    timestamp = datetime.now().strftime(
                        "%Y%m%d_%H%M%S_%f"
                    )

                    capture_stem = (
                        f"session_{session_id}_depth_"
                        f"{depth_capture_index:02d}_"
                        f"{capture['label']}_"
                        f"{timestamp}"
                    )

                    pose_path = (
                        depth_capture_dir
                        / f"{capture_stem}_pose.png"
                    )
                    ui_path = (
                        depth_capture_dir
                        / f"{capture_stem}_ui.png"
                    )

                    cv2.imwrite(
                        str(
                            pose_path
                        ),
                        capture[
                            "pose_frame"
                        ]
                    )

                    cv2.imwrite(
                        str(
                            ui_path
                        ),
                        frame
                    )

                    depth_capture_notice = (
                        "AUTO CAPTURE "
                        f"{capture['label']} "
                        f"margin "
                        f"{capture['margin']:+.3f}"
                    )
                    depth_capture_notice_frames = 45

                    print(
                        "AUTO DEPTH CAPTURE | "
                        f"{capture['label']} | "
                        f"margin "
                        f"{capture['margin']:+.3f} | "
                        f"knee "
                        f"{capture['knee_angle']:.1f} | "
                        f"hip "
                        f"{capture['hip_angle']:.1f} | "
                        f"POSE {pose_path} | "
                        f"UI {ui_path}"
                    )

            if (
                depth_capture_notice
                and depth_capture_notice_frames > 0
            ):
                draw_text(
                    frame,
                    depth_capture_notice,
                    16,
                    camera_height - 36,
                    scale=0.43,
                    thickness=2
                )
                depth_capture_notice_frames -= 1

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
                ord("t"),
                ord("T")
            ):
                if len(
                    performance.reps
                ) == 0:
                    session_type = (
                        "TRAINING"
                        if session_type == "TEST"
                        else "TEST"
                    )

                    database.set_session_type(
                        session_id,
                        session_type
                    )

                    front_analyzer.reset()
                    front_feedback.reset()
                    side_analyzer.reset()

                    side_switch_candidate = None
                    side_switch_frames = 0
                    side_leg_switched = False

                    print(
                        "SESSION MODE -> "
                        f"{session_type}"
                    )
                else:
                    print(
                        "Session mode locked after first completed rep."
                    )

            if key in (
                ord("q"),
                ord("Q"),
                27
            ):
                user_requested_exit = True
                break

    finally:
        total_reps = len(
            performance.reps
        )

        summary = performance.get_set_summary()

        valid_reps = [
            rep
            for rep in performance.reps
            if (
                rep.get(
                    "analysis_valid",
                    True
                )
                and rep.get(
                    "set_valid",
                    True
                )
            )
        ]

        good_reps = sum(
            1
            for rep in valid_reps
            if rep.get(
                "standard_met",
                False
            )
        )

        try:
            database.finish_session(
                session_id,
                total_reps,
                len(
                    valid_reps
                ),
                good_reps
            )
        except Exception as error:
            print(
                f"Database session save warning: {error}"
            )

        if session_type == "TRAINING":
            print(
                "SESSION SUMMARY | "
                f"Reps {summary['reps']} | "
                f"Average {summary['average_score']:.1f} | "
                f"Valid {summary['valid_reps']}/{summary['reps']} | "
                f"Standard {summary['standard_passes']}/"
                f"{summary['valid_reps']} "
                f"({summary['standard_pass_rate']:.1f}%) | "
                f"Consistency {summary['consistency_label']} | "
                f"Trend {summary['trend']} | "
                f"Issue {summary['top_issue']}"
            )
        else:
            print(
                "TEST SUMMARY | "
                f"Reps {summary['reps']} | "
                f"Average {summary['average_score']:.1f} | "
                f"Valid {summary['valid_reps']}/{summary['reps']} | "
                f"Standard {summary['standard_passes']}/"
                f"{summary['valid_reps']} "
                f"({summary['standard_pass_rate']:.1f}%) | "
                f"Depth {summary['side_depth_passes']}/"
                f"{summary['side_reps']} general | "
                f"IPF proxy {summary['side_ipf_proxy_passes']}/"
                f"{summary['side_reps']} | "
                f"Issue {summary['top_issue']}"
            )

        try:
            if total_reps == 0:
                if (
                    session_diagnostics[
                        "body_ready_frames"
                    ] == 0
                ):
                    session_diagnostics[
                        "zero_rep_reason"
                    ] = "BODY_NOT_DETECTED"
                elif (
                    session_diagnostics[
                        "front_frames"
                    ] == 0
                    and session_diagnostics[
                        "side_frames"
                    ] == 0
                ):
                    session_diagnostics[
                        "zero_rep_reason"
                    ] = "NO_STABLE_FRONT_OR_SIDE_VIEW"
                else:
                    session_diagnostics[
                        "zero_rep_reason"
                    ] = "NO_COMPLETED_REP"
            else:
                session_diagnostics[
                    "zero_rep_reason"
                ] = None

            report_paths = report_exporter.export_session(
                session_id,
                performance.reps,
                summary,
                session_type=session_type,
                diagnostics=session_diagnostics
            )

            print(
                "SESSION REPORT | "
                f"JSON {report_paths['json']} | "
                f"CSV {report_paths['csv']}"
            )

            coach_feedback = report_paths[
                "report"
            ][
                "coach_feedback"
            ]

            print()
            print(
                "=== AI COACH ==="
            )
            print(
                coach_feedback[
                    "headline"
                ]
            )
            print(
                coach_feedback[
                    "overview"
                ]
            )
            if coach_feedback.get(
                "strength"
            ):
                print(
                    "做得好的地方："
                    + coach_feedback[
                        "strength"
                    ]
                )
            print(
                "当前重点："
                + coach_feedback[
                    "focus"
                ]
            )
            print(
                "下一组建议："
                + coach_feedback[
                    "next_action"
                ]
            )
        except Exception as error:
            print(
                f"Session report warning: {error}"
            )

        if session_type == "TRAINING":
            try:
                history = database.get_training_history(
                    limit=10
                )

                progress = database.get_progress_summary(
                    limit=10
                )

                history_paths = history_exporter.export_history(
                    history,
                    progress
                )

                print(
                    "TRAINING PROGRESS | "
                    f"Sessions {progress['sessions']} | "
                    f"Latest {progress['latest_average_score']:.1f} | "
                    f"Vs baseline "
                    f"{format_change(progress['score_change'])} | "
                    f"Trend {progress['trend']}"
                )

                print(
                    "FRONT PROGRESS | "
                    f"{progress['front']['trend']} | "
                    f"Change "
                    f"{format_change(progress['front']['score_change'])}"
                )

                print(
                    "SIDE PROGRESS | "
                    f"{progress['side']['trend']} | "
                    f"Change "
                    f"{format_change(progress['side']['score_change'])}"
                )

                print(
                    "HISTORY REPORT | "
                    f"JSON {history_paths['json']} | "
                    f"CSV {history_paths['csv']}"
                )

                progress_feedback = history_paths[
                    "report"
                ][
                    "progress_feedback"
                ]

                print()
                print(
                    "=== AI COACH PROGRESS ==="
                )
                print(
                    progress_feedback[
                        "headline"
                    ]
                )
                print(
                    progress_feedback[
                        "summary"
                    ]
                )
                print(
                    "当前重点："
                    + progress_feedback[
                        "focus"
                    ]
                )
                print(
                    "下一次训练："
                    + progress_feedback[
                        "next_action"
                    ]
                )

            except Exception as error:
                print(
                    f"History report warning: {error}"
                )
        else:
            print(
                "TEST SESSION | "
                "Excluded from formal training progress."
            )

        if user_requested_exit:
            show_session_summary_screen(
                window_name,
                performance.reps,
                summary,
                session_type
            )

        cap.release()
        cv2.destroyAllWindows()

        print(
            "程序已退出"
        )


if __name__ == "__main__":
    run_camera()
