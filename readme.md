#  Smart Biometric Attendance System (IoT + AI)

> **A "Production-Grade" 2-Factor Authentication System for University Campuses.**
> Integrates Barcode Scanning (IoT) with Facial Recognition (AI) to eliminate proxy attendance and automate logging.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?style=flat&logo=opencv&logoColor=white)
![Arduino](https://img.shields.io/badge/Hardware-Arduino%20Uno-00979D?style=flat&logo=arduino&logoColor=white)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success)

##  Overview

This project is a seamless, high-security attendance solution designed for university environments. Unlike traditional systems that rely solely on ID cards (prone to theft/sharing) or manual roll calls (slow), this system enforces **2-Factor Authentication**:
1.  **Something you have:** Physical ID Card (Barcode).
2.  **Something you are:** Biometric Face Data.

The system processes students in **<2 seconds**, automatically assigns attendance to the correct lecture slot (e.g., "Hour 1"), and generates audit-ready CSV reports.

---

##  Key Features

###  Security & Anti-Fraud
* **2-Factor Verification:** Access is granted *only* if the Scanned ID matches the Detected Face.
* **Anti-Proxy Cooldown:** Prevents "pass-back" fraud. Once marked, a student ID is blocked for 10 minutes.
* **Intruder Capture:** Automatically saves a timestamped "Selfie" of any unauthorized person attempting to scan a valid card.
* **Noise Filtering:** Intelligently ignores non-ID barcodes (e.g., snack packets, library books) using length and prefix validation.

### ⚡ Seamless Experience
* **Smart Scheduling:** Automatically detects the current lecture hour (e.g., 08:45-09:45) and logs it in the report.
* **Audio Feedback:** "Headless" operation with Text-to-Speech ("Welcome Adheem" / "Access Denied"), allowing students to keep walking without stopping to check the screen.
* **Instant Visual Feedback:** Green/Red flash on screen for immediate confirmation.

### 📊 Automated Admin
* **Daily CSV Reports:** Generates `Attendance_YYYY-MM-DD.csv` automatically.
* **Detailed Logging:** Tracks Time, Student ID, Name, Lecture Slot, and Verification Status.

---

## 🛠️ Hardware Stack

* **Compute:** MacBook / Laptop (Running the Python Core).
* **Microcontroller:** Arduino Uno R3.
* **Interface:** USB Host Shield 2.0 (For connecting the scanner to Arduino).
* **Input 1:** RetSol LS-450A Barcode Scanner (USB).
* **Input 2:** Built-in Webcam or Logitech C920.
* **Output:** Built-in Speakers (Audio Feedback) & Screen (Visual Dashboard).

---
