# AI-Sport-Coach

A local AI-powered sports movement analysis system based on computer vision.

## Current squat standard

The default evaluation profile is:

**GENERAL_STRENGTH**

It is aligned to published strength-and-conditioning guidance rather than to one user's personal calibration data.

Core rules:

- squat to approximately parallel or below;
- knees track over the feet/toes;
- maintain neutral body control;
- hips and shoulders return together during ascent.

Competition depth is referenced to the IPF rule, but webcam landmarks are only an approximation and are not an official referee decision.

See STANDARDS.md for the distinction between:

- external movement standards;
- 2D camera engineering tolerances;
- diagnostic metrics that do not have one universal numeric cutoff.

## Run

    python -m camera.camera

Controls:

- M — switch SIMPLE / DETAIL / DEBUG
- T — switch TEST / TRAINING before the first completed rep
- Q or ESC — finish the set and open the visual session summary
- Q / ESC / Enter on the summary screen — close

## Tests

    python -m unittest discover -s tests

## AI Coach feedback

Completed sets now include a deterministic coaching summary:

- what went well;
- the main technique issue to focus on;
- one concrete cue for the next set;
- a separate formal progress summary for TRAINING sessions.

The coach layer only explains metrics already measured by the pose system. It does not make medical diagnoses, and TEST sessions do not generate formal training-trend conclusions.

Session JSON reports include a `coach_feedback` object. Formal history JSON reports include `progress_feedback`.

The movement report now also includes a secondary `MULTI_COMPETITION_DETAIL` layer.

The detail layer now uses weighted continuous scoring rather than equal fixed
scores. FRONT prioritizes knee tracking and ascent control; SIDE prioritizes
depth and ascent control. Separate IPF proxy and physique-control scores use
their own weights. The exact project weights and score bands are documented in
`STANDARDS.md`.

Each completed squat is also split into **descent / bottom / ascent** scores.
The report stores the phase-specific checks and identifies the weakest phase,
so feedback can say whether the main loss of control happened on the way down,
at the bottom, or during the ascent.

It keeps the hard squat standard separate from additional coaching detail:

- FRONT: shoulder level, hip level, center balance, head control, left/right knee-angle symmetry and knee-height symmetry;
- SIDE: GENERAL depth, IPF depth proxy, ascent control, return-to-upright proxy, head control, knee/hip/trunk/shin angles;
- IFBB/NPC physique judging concepts are used only as a symmetry/balance/presentation-inspired visual-control lens;
- bodybuilding muscularity/conditioning is not scored from squat video, and the physique lens is not an official bodybuilding or squat judging score.

When a set is ended with Q / ESC, the camera window now switches to a visual session summary with:

- valid reps, score and standard pass rate;
- GENERAL depth / IPF proxy rates when SIDE reps are present;
- the main AI Coach focus and next cue;
- a per-rep timeline showing PASS / REVIEW / EXCLUDED, score and issue.

## Training history

    python history.py

Test-session history:

    python history.py --mode TEST --min-reps 1

Training feedback is not a medical diagnosis.

## 校准版更新：证据质量（2026-10-02）

当前是 Squat v1.0 校准版，尚未完成跨人群准确度验证。
自动测试通过只代表已覆盖的程序行为通过，不代表真人评分已经准确。

这次更新：

- 每个 Rep 保存 `capture_quality`：关键点可见率、视角稳定率、采集帧数。
- `confidence_breakdown` 分开报告 pose / view / phase / coverage；次数多不会自动把低质量采集变成 HIGH。
- 最低点只有 1 帧时，保留诊断分数，但阶段显示 `-- [LOW]`；MEDIUM 显示近似整数。
- 三阶段比较只用三阶段均有可用证据的同一批 Rep；报告给出纳入/排除数量。
- LOW 动作不参与 Best Detail；教练优先提示检查采集，不做确定的技术纠正。
- JSON 报告版本升到 3；CSV 增加证据质量字段。旧报告缺少采集数据时显示 UNKNOWN，不补造证据。
- `next_set_goal` 给出一个重点、动作提示和复查标准。当前建议仍是确定性规则生成。

### 你需要做的最小跑测

在项目文件夹的 VS Code 终端执行：

```powershell
git pull --ff-only origin main
python -m unittest discover -s tests
python -m camera.camera
```

保持 TEST 模式。正常、舒适地做正面 3 次，按 Q 结束并截图总结；重新运行，
侧面做 3 次再按 Q。不要刻意膝内扣、强行蹲深或停在最低点来追分。
如有疼痛就停止真人测试；可以先只运行自动测试。

把这两组新生成的 `reports/session_*.json` 和总结截图发回。
记录你实际做了几次、屏幕计了几次即可。若出现 LOW，不用反复加做，
先发报告排查姿态可见度、视角和阶段采样。

若 `git pull --ff-only` 提示本地改动或分支分叉，保留原文件并发终端信息；
不要用 `reset --hard` 覆盖本地训练数据或代码。

## 阶段评分保护更新（2026-10-06）

- 侧面下降/起身时，躯干角度范围只作诊断，不再直接作为“不稳定”扣分。
  保留原权重作为覆盖率分母，避免只剩头部指标时冒充完整阶段评分。
- 若整次达到一般深度标准，但 BOTTOM 采样没有达到，标记
  `BOTTOM_DEPTH_PHASE_MISMATCH`，最低点深度不评分，也不挪用下降阶段的帧数。
- 最低点深度数据缺失时显示不可评估，不当作失败。
- 不完整的阶段证据仍会限制整体置信度、最佳细节动作和教练建议。
  `LOW` 表示本次评估证据不足，不等于动作差。

前一版已知限制：状态机的平滑和连续帧确认可能使 BOTTOM 标签晚于真实最低点。
此更新阻止错误扣分及确定性建议，尚未完成逐帧时间对齐。已有聚合 JSON
不能重建真实最低点附近的帧序列。下一步需要独立验证时间对齐，并重新校准
阶段指标；不能通过放松阈值或复制整次峰值来声称已经修复采样。


## 侧面最低点重新分段（2026-10-06）

侧面计数仍使用原实时状态机。动作结束后，用有限长度的逐帧测量序列，
通过居中的三帧深度中值和峰值附近的连续窗口，重新汇总下降、底部、起身指标。
膝角、髋角、躯干角、胫骨角、头部位置和深度来自同一帧，不混用不同延迟的中值；
起身协同以新底部窗口的末帧重新计算。该窗口是工程近似，不是真实最低点标注。

- 新增 `phase_alignment`：方法、窗口边界、各阶段实际帧数和失败原因。
- 新增 `phase_trace`：相对时间和数值测量，便于离线回放；不包含图像。
- 不插值、不复制帧，单帧底部仍受低采样保护。
- 序列超过 1800 帧、相邻帧间隔超过 0.25 秒或转折不完整时不使用重分段，
  阶段置信度降为 LOW。成功分段也最多为 MEDIUM，等待真人验证。
- 原 `descent_time/bottom_time/ascent_time` 是实时状态机时间，
  `phase_timing_basis=LIVE_STATE_MACHINE` 明确标注；重分段边界见 `phase_alignment`。
- 上一版的深度冲突和躯干范围评分保护仍然有效。侧面下降阶段目前指标不足，
  即使对齐成功，整体仍可能 LOW；这不意味着动作不合格。
- 此节描述最初的 SIDE 更新；FRONT 的独立位移信号方案见后续更新。

旧 session 聚合报告无法重建逐帧序列，不补造对齐结果。更新后只需在 TEST 模式
自然做侧面 3 次，发新 JSON、总结截图和实际次数即可；无需刻意停顿或蹲深。


## 置信度原因说明修正（2026-10-06）

`confidence_breakdown.phase_capture` 现在专指阶段帧数是否充分；新增
`phase_assessment` 表示阶段评价的综合可靠程度。整体 LOW 的保护不变。
当姿态、视角、阶段帧数均充分且对齐成功，但评分指标覆盖不足时，教练和
逐次结果显示 `Assessment limited`，不再误提示用户检查镜头或重复测试。
真实遮挡、采样不足或对齐冲突仍优先提示检查采集。CSV 同步增加新字段。

## 独立阶段观察（2026-10-06）

总结页和实时组摘要按 FRONT / SIDE 分别显示独立阶段观察，MEDIUM 用近似整数，
并标注 D/B/A 各自纳入的次数。某阶段不可评估不会隐藏其他阶段已有的可用结果。
JSON 新增 `summary.phase_observations_by_view`，每项保存纳入次数、排除次数、
动作编号及排除原因。不同视角不混合平均。

独立观察可能来自不同动作子集，不能据此评选最弱阶段。
原来的匹配样本阶段比较、整体 LOW、最佳细节动作及教练保护保持原规则。
例如下降阶段指标不足时，可显示最低点和起身的参考结果，但不会补造下降分数。


## 正面阶段对齐与离线回放（2026-10-06）

FRONT 现用同一帧的肩部/髋部归一化位移确定底部窗口，独立于侧面深度代理。
位移权重沿用实时检测的 0.65/0.35，底部带宽为 0.02 个基准身体高度，属于
待校准的工程参数。计数状态机不变；膝轨迹、膝高、头部、肩线和骨盆指标
随同一帧重新分段。旧实时反馈不再覆盖成功对齐后的阶段指标。
正面也保存 `phase_trace` 与 `phase_alignment`，成功对齐最多 MEDIUM；缺失或
失败时仍受 LOW 保护。整体评分峰值沿用原计算，阶段评分使用同步原始测量，
两者不是同一评分口径，不能直接按差值解释为改善。

离线复核（不会打开摄像头或写入训练数据库）：

```powershell
python -m reports.replay reports/session_35_20261006_004717.json
python -m reports.replay reports/session_35_20261006_004717.json --output reports/replay_session_35.json
```

输出路径必须是新文件，原报告和已有回放报告不会被覆盖。输出标记为
`OFFLINE_REPLAY` 并保存原文件 SHA256。没有逐帧记录的旧报告只重算已有指标，
标记 `LEGACY_AGGREGATES_ONLY`，不伪造阶段对齐。无需将个人报告提交到 GitHub。

本轮真人验证只需：TEST 模式下正面自然 3 次，按 Q 结束，发 JSON、总结截图
和实际次数。不故意内扣、不额外停顿、不追分；出现 LOW 时先发数据，不加做。

## 逐次细节提示排序（2026-10-07）

总结页逐次结果先显示触发当前严重程度的问题（REVIEW 优先于 WATCH），
同级问题按该次动作的加权扣分排序。没有扣分数据的旧报告保留同级原顺序。
这避免了状态为 REVIEW、旁边却显示另一个轻微问题的误导；其余问题仍以
`+N` 标注。LOW 时继续显示采集/评价限制，不输出确定的动作纠正提示。
本次仅调整提示选择，不改变计数、阈值、评分或阶段对齐。

## 中文离线复核报告（2026-10-08）

已有 JSON 可直接生成可双击打开的中文 HTML，无需重新打开摄像头：

```powershell
python -m reports.replay reports/session_36_20261006_215334.json --html reports/review_36.html
Start-Process reports/review_36.html
```

将输入文件名替换为自己的报告。HTML 包含教练反馈、按视角统计的阶段观察、
逐次结果、回放状态与原文件校验值；无外部资源，可离线打开。它是当前代码的
重新计算结果，不是一条新训练记录，不写入数据库。中等置信度显示约数，
低置信度或排除动作隐藏对应分数。每阶段观察不能代替匹配样本的阶段比较。

可同时指定 `--output reports/replay_36.json` 保存机器可读结果。输出必须使用
新路径；已有文件不会覆盖。个人 HTML 已加入忽略规则，不应提交到 GitHub。
回放现在拒绝非列表的逐帧记录及布尔测量值；空列表会重新判定为对齐不可用，
不会沿用旧的 ALIGNED 标记。没有逐帧字段的旧报告仍只复算聚合指标。

## 训练结束自动生成中文报告（2026-10-09）

退出摄像头训练时，`reports` 目录会同时保存同名的 JSON、CSV 和 HTML。
直接双击 HTML 即可查看中文总结，不需要先执行回放命令。新文件名包含微秒，
减少快速连续导出同一训练时的重名。终端会打印三种报告的保存路径。

自动报告标记为“训练总结”，显示本次保存的评分；`reports.replay --html`
仍标记为“离线复核”，两种报告不会混淆。HTML 保存对应 JSON 的 SHA256，
不会重复评分或新增数据库记录。HTML 导出失败会打印原因，已保存的 JSON、CSV
保留，训练总结继续显示。旧报告不自动改写。

更新后的端到端验证：TEST 模式自然完成正面 3 次，按 Q 结束，确认出现同名
三种文件。提交新 JSON、HTML 页面截图和实际次数；不需要刻意改变动作追分。
