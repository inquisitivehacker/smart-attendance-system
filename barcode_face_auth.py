import cv2
import mediapipe as mp
import numpy as np
import os
import serial
import time
import glob
import face_recognition
import csv
from datetime import datetime

# ------------------- PRODUCTION CONFIG -------------------
# Updated to match your specific port
SERIAL_PORT = "/dev/cu.usbmodem1101"   
BAUD_RATE = 9600
KNOWN_FACES_DIR = "known_faces"
FACE_RECOG_TOLERANCE = 0.50  # Slightly looser for real-world reliability
# --- NEW CONFIG ---
# Auto-generate filename based on date (e.g., Attendance_2026-02-09.csv)
DAILY_REPORT_FILE = f"Attendance_{datetime.now().strftime('%Y-%m-%d')}.csv"
# --- REAL WORLD CONFIG ---
COOLDOWN_SECONDS = 600  # 10 Minutes (Prevents double scanning)
last_valid_scan = {}    # Memory: {'Student_ID': timestamp}

def speak(text):
    # Mac-exclusive text-to-speech (runs in background with &)
    os.system(f"say '{text}' &")

# --- 1. SMART SCHEDULER ---
def get_current_slot():
    now = datetime.now()
    minutes = now.hour * 60 + now.minute 
    
    # Define your college slots (Start Minute, End Minute)
    # 8:45 = 525 min, 9:45 = 585 min, etc.
    slots = [
        ("Hour 1", 525, 585),  # 08:45 - 09:45
        ("Hour 2", 585, 645),  # 09:45 - 10:45
        ("Break",  645, 660),  # 10:45 - 11:00
        ("Hour 3", 660, 720),  # 11:00 - 12:00
        ("Hour 4", 720, 780),  # 12:00 - 01:00
        ("Lunch",  780, 840),  # 01:00 - 02:00
        ("Hour 5", 840, 890),  # 02:00 - 02:50
        ("Hour 6", 890, 940)   # 02:50 - 03:40
    ]
    for name, start, end in slots:
        if start <= minutes < end:
            return name
    return "After Hours"

# --- 2. LOGGING WITH SLOTS ---
# Create file with "Slot" column if it doesn't exist
if not os.path.exists(DAILY_REPORT_FILE):
    with open(DAILY_REPORT_FILE, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Student_ID", "Name", "Time", "Slot", "Status"])

def log_attendance(student_id, name, status):
    current_slot = get_current_slot()
    timestamp = datetime.now().strftime("%H:%M:%S")
    current_time = time.time()
    
    # --- PROXY / DUPLICATE CHECK ---
    if status == "PRESENT":
        last_time = last_valid_scan.get(student_id, 0)
        if current_time - last_time < COOLDOWN_SECONDS:
            print(f"⏳ IGNORING DUPLICATE: {name} (Wait {int((COOLDOWN_SECONDS - (current_time-last_time))/60)}m)")
            speak("Already marked")
            return False # <--- RETURN FALSE (Duplicate)
        
        # Valid scan -> Update memory
        last_valid_scan[student_id] = current_time

    try:
        with open(DAILY_REPORT_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([student_id, name, timestamp, current_slot, status])
        print(f"📝 Marked {status} for {name} in {current_slot}")
        return True # <--- RETURN TRUE (Success)
    except Exception as e:
        print(f"⚠️ Logging Error: {e}")
        return False

# ------------------- 2. LOAD DATABASE -------------------
print("\n--- SECURITY SYSTEM BOOT ---")
print(f"Target Port: {SERIAL_PORT}")
print("Loading biometric database...")

known_encodings = []
known_names = []

for person_folder in os.listdir(KNOWN_FACES_DIR):
    person_path = os.path.join(KNOWN_FACES_DIR, person_folder)
    if not os.path.isdir(person_path):
        continue

    encodings = []
    # Load all jpg/png images for this person
    valid_images = glob.glob(f"{person_path}/*.jpg") + glob.glob(f"{person_path}/*.png")+ glob.glob(f"{person_path}/*.jpeg")
    
    for img_path in valid_images:
        image = face_recognition.load_image_file(img_path)
        face_enc = face_recognition.face_encodings(image)
        if face_enc:
            encodings.append(face_enc[0])

    if encodings:
        # Create an average encoding for better accuracy
        known_encodings.append(np.mean(encodings, axis=0))
        known_names.append(person_folder)
        print(f"  ✓ Loaded Profile: {person_folder}")

print(f"System Ready: {len(known_names)} profiles active.")

# ------------------- 3. HARDWARE LINK -------------------
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2) # Give Arduino 2 seconds to wake up (Essential!)
except serial.SerialException:
    print(f"\n❌ CRITICAL ERROR: Could not connect to {SERIAL_PORT}")
    print("👉 Check your cable or run 'ls /dev/cu.*' to find the new port name.")
    exit()

cap = cv2.VideoCapture(0)
mp_face_mesh = mp.solutions.face_mesh

print("---------------------------------------------")
print("   WAITING FOR CARD SCAN... (Scan now)")
print("---------------------------------------------\n")

# ------------------- 4. MAIN SECURITY LOOP -------------------
with mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=False,
    min_detection_confidence=0.5,
) as face_mesh:

    while True:
        try:
            # READ SERIAL (Blocking - waits here until scanner beeps)
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
            else:
                time.sleep(0.1)
                continue
        except serial.SerialException:
            continue

        # IGNORE NOISE (Startup messages, empty lines)
        if len(line) < 3 or "ready" in line.lower():
            continue
        
        # --- INPUT VALIDATION (NOISE FILTER) ---
        # Ignore chips packets (usually 13 digits) or noise (< 5 chars)
        if len(line) > 12 or len(line) < 5:
            print(f"🗑️ IGNORED NOISE: {line} (Invalid Length)")
            continue
            
        # Optional: Check for College Prefix (e.g., if all IDs start with '22' or '21')
        if not line.startswith(("21", "22","23", "SET")): 
            print(f"⚠️ IGNORED: {line} (Wrong Batch Format)")
            continue

        # --- NEW SCAN DETECTED ---
        scanned_id = line

        # --- NEW SCAN DETECTED ---
        scanned_id = line
        print(f"\n💳 PROCESSING ID: {scanned_id}")
        
        # UI: Open window immediately
        cv2.namedWindow("Attendance", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Attendance", 640, 480)
        
        start_time = time.time()
        verified = False
        detected_name = "Scanning..."
        
        # --- FAST TRACK: 5 Second Window (Seamless) ---
        while time.time() - start_time < 5 and not verified:
            ret, frame = cap.read()
            if not ret: break
            
            # Fast Face Match (1/4 scale)
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            face_locs = face_recognition.face_locations(rgb_small)
            if face_locs:
                face_encs = face_recognition.face_encodings(rgb_small, face_locs)
                if face_encs:
                    dists = face_recognition.face_distance(known_encodings, face_encs[0])
                    if min(dists) < FACE_RECOG_TOLERANCE:
                        match_idx = np.argmin(dists)
                        detected_name = known_names[match_idx]
                        
                        # Match Found? Verify & Break Loop Immediately
                        if detected_name == scanned_id:
                            verified = True
            
            # UI Feedback (Simple & Fast)
            display = frame.copy()
            cv2.putText(display, f"{'VERIFIED' if verified else 'LOOK AT CAMERA'}", 
                       (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0) if verified else (0,165,255), 2)
            cv2.imshow("Attendance", display)
            cv2.waitKey(1)

        # --- INSTANT DECISION ---
        if verified:
            ser.write(b"APPROVED\n")
            if log_attendance(scanned_id, detected_name, "PRESENT"):
                speak(f"Welcome {detected_name}")
            
            # Green Flash (1.5s)
            display[:] = (0, 255, 0)
            cv2.putText(display, f"Welcome {detected_name}", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
            cv2.putText(display, f"Slot: {get_current_slot()}", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,0), 2)
            cv2.imshow("Attendance", display)
            cv2.waitKey(1500) 
        else:
            ser.write(b"DENIED\n")
            log_attendance(scanned_id, "Unknown", "ABSENT")
            speak("Access Denied")
            
            # Red Flash (1.5s)
            display[:] = (0, 0, 255)
            cv2.putText(display, "ACCESS DENIED", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255,255,255), 3)
            cv2.imshow("Attendance", display)
            cv2.waitKey(1500)

        cv2.destroyAllWindows()
        cv2.waitKey(1) 
        print("System reset. Ready for next scan.\n")

cap.release()
ser.close()