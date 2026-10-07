from feedback.capture_quality import weakest_confidence, assessment_limited
from collections import Counter


class SessionInsightBuilder:
    """
    把工程指标转换为用户能直接理解的训练反馈。

    原则：
    - 只解释程序已经测到的数据；
    - 不做医学诊断；
    - TEST 不生成训练趋势结论；
    - 优先给出一个主要改进点，避免一次塞太多提示。
    """

    ISSUE_PRIORITY = [
        "KNEE_TRACKING",
        "DEPTH",
        "SYNC",
    ]

    ISSUE_TEXT_ZH = {
        "KNEE_TRACKING": "膝盖轨迹",
        "DEPTH": "下蹲深度",
        "SYNC": "起身协同",
        "NONE": "暂无明显主要问题",
    }

    ISSUE_CUE_ZH = {
        "KNEE_TRACKING": (
            "下一组优先让膝盖始终跟随脚尖方向，"
            "保持自然动作，不要为了测试故意内扣。"
        ),
        "DEPTH": (
            "下一组优先把髋部下沉到大腿接近平行或更低，"
            "保持自然节奏和舒适范围。"
        ),
        "SYNC": (
            "下一组起身时让肩部和髋部一起向上，"
            "避免一端明显提前启动。"
        ),
        "NONE": (
            "保持当前动作模式即可，不需要为了提高分数刻意改变动作。"
        ),
    }

    ISSUE_UI = {
        "KNEE_TRACKING": "Knee tracking",
        "DEPTH": "Squat depth",
        "SYNC": "Ascent control",
        "NONE": "No major issue",
    }

    ISSUE_CUE_UI = {
        "KNEE_TRACKING": "Keep knees tracking over feet",
        "DEPTH": "Reach parallel with control",
        "SYNC": "Raise hips and shoulders together",
        "NONE": "Keep the same movement pattern",
    }


    DETAIL_TEXT_ZH = {
        "shoulder_level": "肩线水平",
        "hip_level": "骨盆水平",
        "center_balance": "身体重心稳定",
        "head_control": "头颈控制",
        "knee_angle_symmetry": "左右膝屈曲对称",
        "knee_height_symmetry": "左右膝高度对称",
        "lockout_proxy": "站起锁定完成度",
        "ipf_depth_proxy": "IPF 深度代理",
        "general_depth": "通用训练深度",
        "knee_tracking": "膝盖轨迹",
        "ascent_control": "起身协同",
        "trunk_stability": "躯干稳定",
    }

    DETAIL_CUE_ZH = {
        "shoulder_level": "下一组注意两侧肩线保持更平稳，避免明显一高一低。",
        "hip_level": "下一组注意骨盆左右保持稳定，不要让一侧明显先下沉或先抬起。",
        "center_balance": "下一组让身体重心尽量留在双脚中间，减少左右晃动。",
        "head_control": "下一组保持头颈随躯干稳定移动，避免明显前探或侧偏。",
        "knee_angle_symmetry": "下一组注意左右腿同时下蹲和起身，减少两侧膝屈曲差异。",
        "knee_height_symmetry": "下一组注意左右腿受力和下降节奏更一致。",
        "lockout_proxy": "下一组站起时完成完整伸展后再结束动作。",
        "ipf_depth_proxy": "如果目标是力量举比赛深度，再下沉到髋部明显低于膝部的代理位置。",
        "general_depth": "下一组把髋部下沉到大腿接近平行或更低。",
        "knee_tracking": "下一组优先让膝盖始终跟随脚尖方向。",
        "ascent_control": "下一组起身时让肩部和髋部一起向上。",
        "trunk_stability": "下一组保持躯干角度变化更平滑，避免阶段内突然前倒或突然抬胸。",
    }

    DETAIL_UI = {
        "shoulder_level": "Shoulder level",
        "hip_level": "Hip level",
        "center_balance": "Center balance",
        "head_control": "Head control",
        "knee_angle_symmetry": "Knee symmetry",
        "knee_height_symmetry": "Leg symmetry",
        "lockout_proxy": "Lockout proxy",
        "ipf_depth_proxy": "IPF depth proxy",
        "general_depth": "General depth",
        "knee_tracking": "Knee tracking",
        "ascent_control": "Ascent control",
        "trunk_stability": "Trunk stability",
    }

    PHASE_TEXT_ZH = {
        "descent": "下降阶段",
        "bottom": "最低点阶段",
        "ascent": "上升阶段",
    }

    PHASE_UI = {
        "descent": "Descent",
        "bottom": "Bottom",
        "ascent": "Ascent",
    }

    PHASE_CUE_ZH = {
        "descent": (
            "下降阶段保持受控，优先减少左右偏移并让双腿同步屈曲。"
        ),
        "bottom": (
            "最低点优先保持深度、骨盆和双腿稳定，再开始起身。"
        ),
        "ascent": (
            "上升阶段让肩髋同步向上，同时保持膝盖轨迹并完整站直。"
        ),
    }

    @staticmethod
    def _valid_reps(
        reps
    ):
        return [
            rep
            for rep in reps
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

    @staticmethod
    def _rate(
        count,
        total
    ):
        if total <= 0:
            return 0.0

        return round(
            count
            / total
            * 100.0,
            1
        )

    def _main_issue(
        self,
        valid_reps
    ):
        counter = Counter()

        for rep in valid_reps:
            counter.update(
                rep.get(
                    "issues",
                    []
                )
            )

        if not counter:
            return (
                "NONE",
                0,
                0.0
            )

        priority = {
            issue: index
            for index, issue
            in enumerate(
                self.ISSUE_PRIORITY
            )
        }

        issue, count = sorted(
            counter.items(),
            key=lambda item: (
                -item[1],
                priority.get(
                    item[0],
                    len(
                        priority
                    )
                )
            )
        )[0]

        return (
            issue,
            count,
            self._rate(
                count,
                len(
                    valid_reps
                )
            )
        )

    def _detail_focus(
        self,
        valid_reps
    ):
        breakdown = {}

        for rep in valid_reps:
            checks = rep.get(
                "detail_checks",
                {}
            )

            for warning in rep.get(
                "detail_warnings",
                []
            ):
                state = checks.get(
                    warning,
                    {}
                ).get(
                    "state",
                    "WATCH"
                )

                if warning not in breakdown:
                    breakdown[
                        warning
                    ] = {
                        "watch": 0,
                        "review": 0,
                        "total": 0
                    }

                if state == "REVIEW":
                    breakdown[
                        warning
                    ][
                        "review"
                    ] += 1
                else:
                    breakdown[
                        warning
                    ][
                        "watch"
                    ] += 1

                breakdown[
                    warning
                ][
                    "total"
                ] += 1

        if not breakdown:
            return (
                "NONE",
                0,
                0.0,
                "NONE"
            )

        key, counts = sorted(
            breakdown.items(),
            key=lambda item: (
                -item[
                    1
                ][
                    "review"
                ],
                -item[
                    1
                ][
                    "total"
                ],
                item[
                    0
                ]
            )
        )[0]

        severity = (
            "REVIEW"
            if counts[
                "review"
            ] > 0
            else "WATCH"
        )

        return (
            key,
            counts[
                "total"
            ],
            self._rate(
                counts[
                    "total"
                ],
                len(
                    valid_reps
                )
            ),
            severity
        )

    def build(
        self,
        reps,
        summary,
        session_type="TEST"
    ):
        valid_reps = self._valid_reps(
            reps
        )

        total = len(
            valid_reps
        )

        if total == 0:
            return {
                "headline": "暂无可分析的完整动作。",
                "overview": (
                    "这次没有形成有效 Rep，"
                    "先确认身体完整入镜并完成一次完整下蹲和站起。"
                ),
                "strength": None,
                "focus": "暂无动作质量结论。",
                "next_action": (
                    "下一次先完成 2～3 个自然动作，"
                    "不要为了测试刻意改变姿势。"
                ),
                "confidence": "LOW",
                "test_protocol": (
                    session_type == "TEST"
                ),
                "ui_lines": [
                    "No valid completed reps",
                    "Focus: tracking / full movement",
                    "Complete natural reps first",
                ],
            }

        pass_count = sum(
            1
            for rep in valid_reps
            if rep.get(
                "standard_met",
                False
            )
        )

        pass_rate = self._rate(
            pass_count,
            total
        )

        front_reps = [
            rep
            for rep in valid_reps
            if rep.get(
                "view"
            ) == "FRONT"
        ]

        side_reps = [
            rep
            for rep in valid_reps
            if rep.get(
                "view"
            ) == "SIDE"
        ]

        ascent_passes = sum(
            1
            for rep in valid_reps
            if rep.get(
                "standard_checks",
                {}
            ).get(
                "ascent_control",
                False
            )
        )

        knee_failures = sum(
            1
            for rep in front_reps
            if not rep.get(
                "standard_checks",
                {}
            ).get(
                "knee_tracking",
                True
            )
        )

        depth_passes = sum(
            1
            for rep in side_reps
            if rep.get(
                "standard_checks",
                {}
            ).get(
                "depth",
                False
            )
        )

        (
            main_issue,
            issue_count,
            issue_rate
        ) = self._main_issue(
            valid_reps
        )

        (
            detail_focus,
            detail_focus_count,
            detail_focus_rate,
            detail_focus_severity
        ) = self._detail_focus(
            valid_reps
        )

        detail_review_count = sum(
            1 for rep in valid_reps
            if detail_focus in rep.get("detail_warnings", [])
            and rep.get("detail_checks", {}).get(detail_focus, {}).get("state") == "REVIEW"
        )
        detail_watch_count = detail_focus_count - detail_review_count

        weakest_phase_data = summary.get(
            "weakest_phase"
        ) or {}

        phase_focus = weakest_phase_data.get(
            "phase"
        )
        phase_focus_score = weakest_phase_data.get(
            "score"
        )

        top_deductions = summary.get(
            "top_detail_deductions",
            []
        )
        top_deduction = (
            top_deductions[
                0
            ]
            if top_deductions
            else None
        )

        phase_deductions = summary.get(
            "phase_deduction_summary",
            {}
        )
        phase_reason = None

        if phase_focus:
            phase_items = phase_deductions.get(
                phase_focus,
                []
            )

            if phase_items:
                phase_reason = phase_items[
                    0
                ]

        overview = (
            f"本组完成 {total} 次有效动作，"
            f"{pass_count} 次通过当前标准"
            f"（{pass_rate:.0f}%）。"
        )

        strengths = []

        if (
            ascent_passes
            == total
            and total >= 2
        ):
            strengths.append(
                f"起身阶段控制稳定，{ascent_passes}/{total} 次通过。"
            )

        if (
            front_reps
            and knee_failures == 0
        ):
            strengths.append(
                f"正面膝盖轨迹稳定，{len(front_reps)}/{len(front_reps)} 次通过。"
            )

        if (
            side_reps
            and depth_passes == len(
                side_reps
            )
        ):
            strengths.append(
                f"侧面深度稳定，{depth_passes}/{len(side_reps)} 次达到通用训练深度。"
            )

        if not strengths:
            if pass_rate >= 70.0:
                strengths.append(
                    "大多数动作已经通过当前标准。"
                )
            elif summary.get(
                "excluded_reps",
                0
            ) == 0:
                strengths.append(
                    "本组数据完整，没有明显跟踪异常被排除。"
                )

        strength = (
            strengths[
                0
            ]
            if strengths
            else "本组已获得足够数据，可以继续针对主要问题训练。"
        )

        if main_issue == "KNEE_TRACKING":
            focus = (
                f"{issue_count}/{total} 次动作出现膝盖向内偏移，"
                "这是当前最需要优先处理的标准问题。"
            )
        elif main_issue == "DEPTH":
            if side_reps:
                focus = (
                    f"侧面 {depth_passes}/{len(side_reps)} 次达到通用训练深度，"
                    "当前主要限制是下蹲深度。"
                )
            else:
                focus = (
                    f"{issue_count}/{total} 次动作出现深度问题。"
                )
        elif main_issue == "SYNC":
            focus = (
                f"{issue_count}/{total} 次动作的起身阶段肩髋协同需要改善。"
            )
        elif detail_focus != "NONE":
            detail_label = self.DETAIL_TEXT_ZH.get(
                detail_focus,
                detail_focus
            )
            focus = (
                f"硬性标准已通过，但 {detail_focus_count}/{total} 次动作"
                f"出现“{detail_label}”细节提示"
                f"（需复核 {detail_review_count} 次，留意 {detail_watch_count} 次）。"
            )
        elif (
            top_deduction
            and top_deduction.get(
                "average_lost_points",
                0.0
            ) >= 0.5
        ):
            deduction_name = top_deduction.get(
                "name",
                "detail"
            )
            deduction_label = self.DETAIL_TEXT_ZH.get(
                deduction_name,
                deduction_name
            )
            focus = (
                "当前没有反复出现的硬性问题，"
                f"细节分的主要损失来自“{deduction_label}”，"
                f"平均约 -{top_deduction.get('average_lost_points', 0.0):.1f} 分。"
            )
        else:
            focus = "当前没有反复出现的主要标准问题或细节提示。"

        if (
            phase_focus
            and phase_focus_score is not None
        ):
            phase_label = self.PHASE_TEXT_ZH.get(
                phase_focus,
                phase_focus
            )

            focus += (
                f" 分阶段看，{phase_label}平均分最低"
                f"（{phase_focus_score:.1f}）。"
            )

            if (
                phase_reason
                and phase_reason.get(
                    "average_lost_points",
                    0.0
                ) >= 0.3
            ):
                reason_name = phase_reason.get(
                    "name",
                    "detail"
                )
                reason_label = self.DETAIL_TEXT_ZH.get(
                    reason_name,
                    reason_name
                )

                focus += (
                    f" 该阶段主要扣分来自“{reason_label}”，"
                    f"平均约 -{phase_reason.get('average_lost_points', 0.0):.1f} 分。"
                )

        if main_issue != "NONE":
            selected_focus = main_issue
            selected_label_zh = self.ISSUE_TEXT_ZH.get(
                main_issue,
                main_issue
            )
            selected_label_ui = self.ISSUE_UI.get(
                main_issue,
                main_issue
            )
            next_action = self.ISSUE_CUE_ZH.get(
                main_issue,
                self.ISSUE_CUE_ZH[
                    "NONE"
                ]
            )
        elif detail_focus != "NONE":
            selected_focus = detail_focus
            selected_label_zh = self.DETAIL_TEXT_ZH.get(
                detail_focus,
                detail_focus
            )
            selected_label_ui = self.DETAIL_UI.get(
                detail_focus,
                detail_focus
            )
            next_action = self.DETAIL_CUE_ZH.get(
                detail_focus,
                "下一组继续保持自然动作，并优先改善这一项细节。"
            )
        else:
            selected_focus = "NONE"
            selected_label_zh = "当前动作"
            selected_label_ui = "No major issue"
            next_action = self.ISSUE_CUE_ZH[
                "NONE"
            ]

        if (
            phase_focus
            and phase_focus in self.PHASE_CUE_ZH
            and main_issue == "NONE"
        ):
            next_action += (
                " "
                + self.PHASE_CUE_ZH[
                    phase_focus
                ]
            )

        if session_type == "TEST":
            if main_issue != "NONE":
                headline = (
                    f"测试结果：主要关注 {selected_label_zh}。"
                )
            elif detail_focus != "NONE":
                headline = (
                    f"测试结果：标准通过，但细节可优化——{selected_label_zh}。"
                )
            else:
                headline = "测试结果：当前主要标准项和细节表现稳定。"
        else:
            if main_issue == "NONE" and detail_focus == "NONE":
                headline = "本组动作整体稳定，可以保持当前技术模式。"
            elif main_issue != "NONE":
                headline = (
                    f"本组优先改善：{selected_label_zh}。"
                )
            else:
                headline = (
                    f"本组标准通过，下一步优化：{selected_label_zh}。"
                )

        if total >= 5:
            confidence = "HIGH"
        elif total >= 3:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        evidence_confidence = weakest_confidence([
            rep.get("detail_confidence", "MEDIUM") for rep in valid_reps
        ])
        confidence = weakest_confidence([confidence, evidence_confidence])
        # Repeating uncertain measurements does not create reliable evidence.
        capture_limited = evidence_confidence == "LOW"
        model_limited = capture_limited and all(
            assessment_limited(rep) for rep in valid_reps
            if rep.get("detail_confidence") == "LOW"
        )
        if capture_limited:
            headline = "本组测量证据不足，先检查拍摄条件。"
            strength = "已记录动作次数；动作质量结论需要复核。"
            focus = "姿态可见度、视角或阶段采样不足，暂不据此判断技术问题。"
            next_action = "下一组保持全身入镜、镜头固定，按自然节奏完成动作；无需故意做错或增加次数。"
            selected_focus = "CAPTURE_QUALITY"
            selected_label_ui = "Check capture quality"
            phase_focus = phase_focus_score = phase_reason = top_deduction = None

        if model_limited:
            headline = "本组采集可用，阶段评分指标尚不完整。"
            focus = "姿态、视角和阶段采样可用；当前阶段评分模型覆盖不足，暂不作完整技术评价。"
            next_action = "保留本次报告供校准，无需为此调整镜头或重复动作；等待评分模型完善。"
            selected_focus = "ASSESSMENT_LIMITED"
            selected_label_ui = "Assessment limited"

        ui_lines = [
            (
                f"Standard {pass_count}/{total} "
                f"({pass_rate:.0f}%)"
            ),
            (
                "Focus: "
                + selected_label_ui
            ),
        ]

        if main_issue != "NONE":
            ui_lines.append(
                self.ISSUE_CUE_UI.get(
                    main_issue,
                    "Keep movement controlled"
                )
            )
        elif detail_focus != "NONE":
            ui_lines.append(
                "Detail: "
                + selected_label_ui
            )
        else:
            ui_lines.append(
                "Keep the same movement pattern"
            )

        if (
            phase_focus
            and phase_focus_score is not None
        ):
            ui_lines.append(
                (
                    "Weak phase: "
                    + self.PHASE_UI.get(
                        phase_focus,
                        phase_focus
                    )
                    + f" {phase_focus_score:.1f}"
                )
            )

        if phase_reason:
            reason_name = phase_reason.get(
                "name",
                "detail"
            )
            ui_lines.append(
                (
                    "Why: "
                    + self.DETAIL_UI.get(
                        reason_name,
                        reason_name
                    )
                    + f" -{phase_reason.get('average_lost_points', 0.0):.1f}"
                )
            )

        if capture_limited:
            ui_lines = [f"Recorded {total} reps", "Evidence: LOW",
                        "Focus: capture / phase sampling", "Use natural movement; review capture"]
        if model_limited:
            ui_lines = [f"Recorded {total} reps", "Evidence: LOW",
                        "Focus: assessment coverage", "Capture usable; no retest needed"]
        goal = {
            "focus": selected_focus,
            "cue": next_action,
            "phase": phase_focus,
            "evidence_confidence": evidence_confidence,
            "affected_reps": issue_count if main_issue != "NONE" else detail_focus_count,
            "evaluated_reps": total,
            "success_criterion": (
                "先获得完整三阶段和可用的姿态、视角证据，再比较动作质量。"
                if capture_limited else
                "相同视角和拍摄条件下，保持自然动作，观察该问题的出现比例是否下降。"
                if selected_focus != "NONE" else
                "保持当前自然动作，复查下一组结果是否一致。"
            ),
        }
        if capture_limited:
            goal["affected_reps"] = None
        if model_limited:
            goal["success_criterion"] = "完善阶段评分指标后，用已保存的逐帧数据复核。"

        if phase_reason:
            goal["phase_average_lost_points"] = phase_reason.get("average_lost_points")
            goal["phase_metric"] = phase_reason.get("name")

        return {
            "headline": headline,
            "next_set_goal": goal,
            "evidence_confidence": evidence_confidence,
            "overview": overview,
            "strength": strength,
            "focus": focus,
            "next_action": next_action,
            "confidence": confidence,
            "test_protocol": (
                session_type == "TEST"
            ),
            "main_issue": main_issue,
            "main_issue_rate": issue_rate,
            "detail_focus": detail_focus,
            "detail_focus_rate": detail_focus_rate,
            "detail_focus_severity": detail_focus_severity,
            "detail_focus_counts": {"review": detail_review_count, "watch": detail_watch_count,
                                    "total": detail_focus_count},
            "selected_focus": selected_focus,
            "phase_focus": phase_focus,
            "phase_focus_score": phase_focus_score,
            "phase_reason": phase_reason,
            "top_deduction": top_deduction,
            "standard_pass_rate": pass_rate,
            "metrics": {
                "valid_reps": total,
                "standard_passes": pass_count,
                "front_reps": len(
                    front_reps
                ),
                "front_knee_tracking_failures": knee_failures,
                "side_reps": len(
                    side_reps
                ),
                "side_depth_passes": depth_passes,
                "ascent_control_passes": ascent_passes,
            },
            "ui_lines": ui_lines,
        }


class ProgressInsightBuilder:
    """
    把正式 TRAINING 历史趋势转换为简洁文字。
    """

    @staticmethod
    def _change_text(
        value
    ):
        if value is None:
            return None

        direction = (
            "提高"
            if value > 0
            else "下降"
            if value < 0
            else "持平"
        )

        return (
            f"{direction} {abs(value):.1f}"
            if value != 0
            else "基本持平"
        )

    def build(
        self,
        progress
    ):
        if (
            not progress
            or progress.get(
                "sessions",
                0
            ) == 0
        ):
            return {
                "headline": "正式训练数据还不够。",
                "summary": (
                    "完成至少一次 TRAINING 后，"
                    "这里会开始生成长期动作趋势。"
                ),
                "focus": "暂无趋势结论。",
                "next_action": "继续积累正式训练数据。",
            }

        trend = progress.get(
            "trend",
            "COLLECTING"
        )

        score_change = progress.get(
            "score_change"
        )

        if trend == "IMPROVING":
            headline = "最近正式训练表现高于此前基线。"
        elif trend == "DECLINING":
            headline = "最近正式训练表现低于此前基线。"
        elif trend == "STABLE":
            headline = "最近正式训练表现与此前基线基本稳定。"
        else:
            headline = "正在建立正式训练基线。"

        change_text = self._change_text(
            score_change
        )

        if change_text is None:
            summary = (
                f"最新平均分 {progress.get('latest_average_score', 0.0):.1f}，"
                "目前还没有足够的历史基线做比较。"
            )
        else:
            summary = (
                f"最新平均分 {progress.get('latest_average_score', 0.0):.1f}，"
                f"相比此前基线{change_text}。"
            )

        issue = progress.get(
            "latest_top_issue",
            "NONE"
        )

        if issue == "NONE":
            focus = "最新训练没有反复出现的主要问题。"
            next_action = "保持当前技术模式，并继续积累正式训练数据。"
        else:
            issue_rate = progress.get(
                "latest_top_issue_rate",
                0.0
            )

            label = SessionInsightBuilder.ISSUE_TEXT_ZH.get(
                issue,
                issue
            )

            focus = (
                f"最新训练中最常见的问题是{label}，"
                f"出现率约 {issue_rate:.0f}%。"
            )

            next_action = SessionInsightBuilder.ISSUE_CUE_ZH.get(
                issue,
                "下一次训练优先改善这一项。"
            )

        return {
            "headline": headline,
            "summary": summary,
            "focus": focus,
            "next_action": next_action,
            "trend": trend,
        }
