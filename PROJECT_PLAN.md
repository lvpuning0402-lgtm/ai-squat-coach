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