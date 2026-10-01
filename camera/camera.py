import cv2

from pose.detector import PoseDetector
from pose.view_detector import ViewDetector

from exercises.front_squat import FrontSquatAnalyzer
from exercises.side_squat import SideSquatAnalyzer

from feedback.front_feedback import FrontFeedback


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


def run_camera():

    # =====================================
    # 摄像头
    # =====================================

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():

        print(
            "无法打开摄像头"
        )

        return

    # =====================================
    # 模块
    # =====================================

    detector = PoseDetector()

    view_detector = ViewDetector()

    front_analyzer = (
        FrontSquatAnalyzer()
    )

    side_analyzer = (
        SideSquatAnalyzer()
    )

    front_feedback = (
        FrontFeedback()
    )

    # =====================================
    # 窗口
    # =====================================

    window_name = (
        "AI Sport Coach"
    )

    cv2.namedWindow(
        window_name,
        cv2.WINDOW_NORMAL
    )

    # =====================================
    # 当前侧面跟踪腿
    # =====================================

    active_leg = None

    print(
        "Multi-angle squat analysis enabled"
    )

    print(
        "按 Q / ESC 退出"
    )

    while True:

        ret, frame = cap.read()

        if not ret:

            break

        height = frame.shape[0]

        width = frame.shape[1]

        # =================================
        # Pose
        # =================================

        frame, result = (
            detector.detect(
                frame
            )
        )

        # =================================
        # 关键点
        # =================================

        nose = detector.get_landmark(
            result,
            0
        )

        left_shoulder = (
            detector.get_landmark(
                result,
                11
            )
        )

        right_shoulder = (
            detector.get_landmark(
                result,
                12
            )
        )

        left_hip = (
            detector.get_landmark(
                result,
                23
            )
        )

        right_hip = (
            detector.get_landmark(
                result,
                24
            )
        )

        left_knee = (
            detector.get_landmark(
                result,
                25
            )
        )

        right_knee = (
            detector.get_landmark(
                result,
                26
            )
        )

        left_ankle = (
            detector.get_landmark(
                result,
                27
            )
        )

        right_ankle = (
            detector.get_landmark(
                result,
                28
            )
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

            # =================================
            # VIEW
            # =================================

            (
                view,
                view_ratio,
                raw_view
            ) = view_detector.update(

                left_shoulder[
                    "point"
                ],

                right_shoulder[
                    "point"
                ],

                left_hip[
                    "point"
                ],

                right_hip[
                    "point"
                ],

                width,

                height,

                freeze=False
            )

            position = (
                get_position_hint(
                    view,
                    raw_view
                )
            )

            # =================================
            # FRONT
            # =================================

            if view == "FRONT":

                front_result = (
                    front_analyzer.analyze(

                        nose["point"],

                        left_shoulder[
                            "point"
                        ],

                        right_shoulder[
                            "point"
                        ],

                        left_hip[
                            "point"
                        ],

                        right_hip[
                            "point"
                        ],

                        left_knee[
                            "point"
                        ],

                        right_knee[
                            "point"
                        ],

                        left_ankle[
                            "point"
                        ],

                        right_ankle[
                            "point"
                        ]
                    )
                )

                if (
                    front_result
                    is not None
                ):

                    front_form = (
                        front_feedback.update(

                            left_hip[
                                "point"
                            ],

                            right_hip[
                                "point"
                            ],

                            left_knee[
                                "point"
                            ],

                            right_knee[
                                "point"
                            ],

                            left_ankle[
                                "point"
                            ],

                            right_ankle[
                                "point"
                            ],

                            front_result[
                                "stage"
                            ]
                        )
                    )

                    y = 40

                    lines = [
                        (
                            "Mode: FRONT"
                        ),

                        (
                            f"Count: "
                            f"{front_result['count']}"
                        ),

                        (
                            f"Stage: "
                            f"{front_result['stage']}"
                        ),

                        (
                            f"Shoulder down: "
                            f"{front_result['shoulder_descent']:.2f}"
                        ),

                        (
                            f"Hip down: "
                            f"{front_result['hip_descent']:.2f}"
                        ),

                        (
                            f"Head shift: "
                            f"{front_result['head_shift']:.2f}"
                        ),

                        (
                            f"Shoulder tilt: "
                            f"{front_result['shoulder_tilt']:.2f}"
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
                            f"{front_form['symmetry_state']}"
                        ),

                        (
                            f"L/R inward: "
                            f"{front_form['left_value']:.2f}"
                            " / "
                            f"{front_form['right_value']:.2f}"
                        )
                    ]

                    for line in lines:

                        cv2.putText(
                            frame,
                            line,
                            (
                                30,
                                y
                            ),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.62,
                            (
                                255,
                                255,
                                255
                            ),
                            2
                        )

                        y += 35

            # =================================
            # SIDE
            # =================================

            elif view == "SIDE":

                # -----------------------------
                # 自动选择可见度高的一侧
                # -----------------------------

                left_visibility = (
                    left_hip[
                        "visibility"
                    ]
                    +
                    left_knee[
                        "visibility"
                    ]
                    +
                    left_ankle[
                        "visibility"
                    ]
                ) / 3

                right_visibility = (
                    right_hip[
                        "visibility"
                    ]
                    +
                    right_knee[
                        "visibility"
                    ]
                    +
                    right_ankle[
                        "visibility"
                    ]
                ) / 3

                if (
                    left_visibility
                    >=
                    right_visibility
                ):

                    active_leg = "LEFT"

                    shoulder = (
                        left_shoulder[
                            "point"
                        ]
                    )

                    hip = (
                        left_hip[
                            "point"
                        ]
                    )

                    knee = (
                        left_knee[
                            "point"
                        ]
                    )

                    ankle = (
                        left_ankle[
                            "point"
                        ]
                    )

                else:

                    active_leg = "RIGHT"

                    shoulder = (
                        right_shoulder[
                            "point"
                        ]
                    )

                    hip = (
                        right_hip[
                            "point"
                        ]
                    )

                    knee = (
                        right_knee[
                            "point"
                        ]
                    )

                    ankle = (
                        right_ankle[
                            "point"
                        ]
                    )

                side_result = (
                    side_analyzer.analyze(
                        nose["point"],
                        shoulder,
                        hip,
                        knee,
                        ankle
                    )
                )

                y = 40

                lines = [
                    (
                        "Mode: SIDE"
                    ),

                    (
                        f"Tracking: "
                        f"{active_leg}"
                    ),

                    (
                        f"Count: "
                        f"{side_result['count']}"
                    ),

                    (
                        f"Stage: "
                        f"{side_result['stage']}"
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
                        f"Trunk: "
                        f"{side_result['trunk_lean']:.1f}"
                    ),

                    (
                        f"Head forward: "
                        f"{side_result['head_forward']:.2f}"
                    ),

                    (
                        f"Depth: "
                        f"{side_result['depth']}"
                    )
                ]

                for line in lines:

                    cv2.putText(
                        frame,
                        line,
                        (
                            30,
                            y
                        ),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        (
                            255,
                            255,
                            255
                        ),
                        2
                    )

                    y += 38

            # =================================
            # TRANSITION
            # =================================

            else:

                cv2.putText(
                    frame,
                    (
                        "Adjust camera angle"
                    ),
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

            # =================================
            # Debug view
            # =================================

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

        key = (
            cv2.waitKey(1)
            &
            0xFF
        )

        if key in (
            ord("q"),
            ord("Q"),
            27
        ):

            break

    cap.release()

    cv2.destroyAllWindows()

    print(
        "程序已退出"
    )


if __name__ == "__main__":

    run_camera()