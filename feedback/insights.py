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

        for issue in self.ISSUE_PRIORITY:
            if issue in counter:
                count = counter[
                    issue
                ]
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

        issue, count = counter.most_common(
            1
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
                    "No completed reps",
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
                "这是当前最需要优先处理的动作问题。"
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
        else:
            focus = "当前没有反复出现的主要标准问题。"

        if session_type == "TEST":
            headline = (
                f"测试结果：主要关注 {self.ISSUE_TEXT_ZH.get(main_issue, main_issue)}。"
                if main_issue != "NONE"
                else "测试结果：当前主要标准项表现稳定。"
            )
        else:
            if pass_rate >= 90.0:
                headline = "本组动作整体稳定，可以保持当前技术模式。"
            elif main_issue != "NONE":
                headline = (
                    f"本组优先改善："
                    f"{self.ISSUE_TEXT_ZH.get(main_issue, main_issue)}。"
                )
            else:
                headline = "本组没有明显反复出现的技术问题。"

        if total >= 5:
            confidence = "HIGH"
        elif total >= 3:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        ui_lines = [
            (
                f"Standard {pass_count}/{total} "
                f"({pass_rate:.0f}%)"
            ),
            (
                "Focus: "
                + self.ISSUE_UI.get(
                    main_issue,
                    main_issue
                )
            ),
        ]

        if main_issue != "NONE":
            ui_lines.append(
                self.ISSUE_CUE_UI.get(
                    main_issue,
                    "Keep movement controlled"
                )
            )
        else:
            ui_lines.append(
                "Keep the same movement pattern"
            )

        return {
            "headline": headline,
            "overview": overview,
            "strength": strength,
            "focus": focus,
            "next_action": self.ISSUE_CUE_ZH.get(
                main_issue,
                self.ISSUE_CUE_ZH[
                    "NONE"
                ]
            ),
            "confidence": confidence,
            "test_protocol": (
                session_type == "TEST"
            ),
            "main_issue": main_issue,
            "main_issue_rate": issue_rate,
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
