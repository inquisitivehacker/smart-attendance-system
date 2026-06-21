"""
Benchmark Script for Raspberry Pi 5.
Measures isolated component performance to validate throughput and latency requirements.
"""
import time
import os
import queue
import psutil
import statistics
import threading

# Ensure project root is in python path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db, SessionLocal
from src.services.face_service import FaceService
from src.repositories.student_repo import StudentRepository
from src.repositories.student_state_repo import StudentStateRepository
from src.config import settings

def benchmark_database_latency(db, iterations=100):
    print("\n--- Benchmarking Database Lookup Latency ---")
    repo = StudentRepository(db)
    
    all_students = repo.get_all()
    if not all_students:
        print("No students in DB. Skipping.")
        return
        
    test_id = all_students[0].id
    
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        repo.get_by_id(test_id)
        latencies.append(time.perf_counter() - start)
        
    avg_ms = statistics.mean(latencies) * 1000
    print(f"Average Lookup Latency: {avg_ms:.2f} ms")


def benchmark_state_update(db, iterations=100):
    print("\n--- Benchmarking State Update Latency ---")
    repo = StudentStateRepository(db)
    
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        repo.set_state("TEST-ID", "ACTIVE", "Room-1")
        latencies.append(time.perf_counter() - start)
        
    avg_ms = statistics.mean(latencies) * 1000
    print(f"Average State Update Latency: {avg_ms:.2f} ms")


def benchmark_face_verification():
    print("\n--- Benchmarking Face Verification ---")
    start = time.perf_counter()
    face_service = FaceService(known_faces_dir=settings.known_faces_dir, tolerance=settings.face_tolerance)
    print(f"Initialization / Profile Load Time: {time.perf_counter() - start:.2f} seconds")
    
    if face_service.profile_count == 0:
        print("No face profiles loaded. Skipping verification benchmark.")
        return
        
    import glob
    import cv2
    import face_recognition
    
    images = glob.glob(f"{settings.known_faces_dir}/*/*.jpg") + glob.glob(f"{settings.known_faces_dir}/*/*.png")
    if not images:
        print("No images found to test verification.")
        return
        
    test_image_path = images[0]
    frame = face_recognition.load_image_file(test_image_path)
    # Convert RGB (from face_recognition) to BGR for our face_service which expects BGR from cv2
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    
    expected_id = os.path.basename(os.path.dirname(test_image_path))
    
    latencies = []
    for _ in range(10): # 10 iterations is enough for slow face rec
        start = time.perf_counter()
        face_service.verify(frame_bgr, expected_id)
        latencies.append(time.perf_counter() - start)
        
    avg_ms = statistics.mean(latencies) * 1000
    print(f"Average Face Verification Time: {avg_ms:.2f} ms")

def benchmark_queue_throughput():
    print("\n--- Benchmarking Queue Throughput ---")
    test_queue = queue.Queue(maxsize=200)
    
    def worker():
        while True:
            item = test_queue.get()
            if item is None:
                break
            test_queue.task_done()

    t = threading.Thread(target=worker)
    t.start()
    
    start = time.perf_counter()
    for i in range(10000):
        test_queue.put(i)
    
    test_queue.join()
    test_queue.put(None)
    t.join()
    
    duration = time.perf_counter() - start
    print(f"Processed 10,000 queue items in {duration:.4f} seconds ({10000/duration:.0f} items/sec)")

def print_system_stats():
    print("\n--- System Resource Usage ---")
    process = psutil.Process(os.getpid())
    print(f"CPU Usage (Process): {process.cpu_percent()}%")
    print(f"CPU Usage (System): {psutil.cpu_percent()}%")
    print(f"Memory Usage (Process): {process.memory_info().rss / 1024 / 1024:.2f} MB")
    print(f"Memory Usage (System): {psutil.virtual_memory().percent}%")


def run_all():
    print("Starting Phase 2 Benchmarks...")
    init_db()
    db = SessionLocal()
    
    try:
        benchmark_database_latency(db)
        benchmark_state_update(db)
        benchmark_queue_throughput()
        benchmark_face_verification()
        print_system_stats()
    finally:
        db.close()
        print("\nBenchmarks Complete.")

if __name__ == "__main__":
    run_all()
