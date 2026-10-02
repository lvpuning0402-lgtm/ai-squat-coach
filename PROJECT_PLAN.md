# AI-Sport-Coach Project Plan

## 1. Project Goal

AI-Sport-Coach is a local computer-vision-based sports movement analysis system.

The first version focuses on side-view squat analysis using a normal computer webcam.

The system should be able to:

- Detect the user's body pose
- Count squat repetitions
- Identify squat movement phases
- Analyze squat depth
- Analyze torso posture
- Analyze movement tempo
- Give simple real-time feedback
- Save workout records locally

---

## 2. Target Environment

### Hardware

- Windows laptop
- Built-in or USB webcam
- No wearable sensors required

### Software

- Windows 11
- Python 3.12
- VS Code
- Git / GitHub

---

## 3. V1.0 Scope

### Core Features

1. Camera input
2. Human pose detection
3. Joint angle calculation
4. Squat repetition counting
5. Squat phase recognition
6. Squat depth analysis
7. Torso angle analysis
8. Movement tempo analysis
9. Real-time feedback
10. Local workout history

---

## 4. Squat Movement States

The first version will recognize:

- Standing
- Descending
- Bottom
- Ascending

A complete repetition is:

Standing → Descending → Bottom → Ascending → Standing

---

## 5. Pose Analysis

Important body landmarks:

- Shoulder
- Hip
- Knee
- Ankle

Important measurements:

- Knee angle
- Hip angle
- Torso angle
- Squat depth
- Movement duration

---

## 6. Camera Requirements

Before training begins, the system should check:

- Full body is visible
- Hip is visible
- Knee is visible
- Ankle is visible
- User is approximately side-facing
- Camera distance is suitable

Possible feedback:

- Move farther from camera
- Full body not visible
- Turn sideways
- Ready to start

---

## 7. Technology Stack

- Python
- OpenCV
- MediaPipe
- NumPy
- SQLite

Future UI:

- Streamlit or another desktop/web interface

---

## 8. Project Structure

camera/
- Camera input and camera validation

pose/
- Pose detection
- Joint angle calculation

exercises/
- Exercise state machines and movement logic

feedback/
- Movement quality evaluation

data/
- Workout history and SQLite database

models/
- MediaPipe model files

tests/
- Automated tests

app.py
- Main program entry point

---

## 9. Development Stages

### Stage 1
Camera and pose detection

### Stage 2
Joint angle calculation

### Stage 3
Squat state machine

### Stage 4
Squat depth and torso analysis

### Stage 5
Real-time feedback

### Stage 6
Workout data storage

### Stage 7
User interface

### Stage 8
Testing and optimization

---

## 10. Not Included in V1.0

The first version will NOT include:

- User accounts
- Cloud server
- Mobile application
- Social features
- Medical diagnosis
- Large language model chatbot
- Multiple exercise types

These may be considered in later versions.
---

## 11. 接手后的交付与验收顺序（2026-10-02）

状态用可验收事项记录，不再用未经定义的完成百分比。

1. **本轮：采集证据与保守反馈** — 已实现逐 Rep 可见度/视角记录、三阶段
   证据约束、低可信提示、Best Detail 筛选、报告 v3 和针对性自动测试。
   真人验收待用户正面/侧面各一组自然动作。
2. **下一轮：真实数据校准** — 核对计数、阶段采样、分数排序和逐项扣分。
   先复用已导出的数据，必要时补录短视频；不要求故意做疼痛或极端错误动作。
3. **误报治理** — 根据复现证据处理遮挡、镜头倾斜、偏离中心、侧面偏转、
   动作速度和身材差异；每类修复配回归案例，不统一放宽阈值。
4. **Coach 与产品界面** — 将已验证的主要问题、发生次数和下一组目标用
   中文结果页呈现，支持逐 Rep 展开；不把低可信诊断当作明确纠正意见。
5. **正式历史与打包** — TRAINING 趋势按视角、配置、评分版本和证据质量
   分组；Windows 启动/退出/摄像头故障验收后再标记 Squat v1.0。
6. **多动作平台** — Squat 验收后再抽象共享接口，逐个扩展动作；本轮
   不宣称已经完成硬拉、卧推或全平台架构。

发布门槛：自动测试通过 + 真人自然动作验收 + 已知误报有说明 + 报告可追溯。
