import os

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["PYTORCH_NO_CUDA_MEMORY_CACHING"] = "1"

import time
from typing import List, Tuple, Optional
import sqlite3
import numpy as np
import cv2
from ultralytics import YOLO
import face_recognition

from hesaplamalar import write_stats, update_max, compute_percent, STATS_PATH
from hesaplamalar2 import (
    reset_tracking,
    mark_seen,
    update_missing,
    write_attentions_to_db,
    mark_present,
)

# ---- Yapılandırma ----
DB_PATH = os.environ.get("STUDENT_DB_PATH", "/home/krm/Desktop/dlibenv/OYS/ogrenciler.db")
MODEL_PATH = os.environ.get("YOLO_MODEL_PATH", "/home/krm/Desktop/detectenv/hybrid/best.pt")
IMGSZ = int(os.environ.get("YOLO_IMGSZ", "640"))
DOWNSCALE = float(os.environ.get("DOWNSCALE", "1.0"))
MATCH_THR = float(os.environ.get("MATCH_THR", "0.55"))


# ---- DB yardımcıları (mevcut yapıyla uyumlu) ----
def _to_arr(vec) -> Optional[np.ndarray]:
    if isinstance(vec, np.ndarray):
        v = vec.astype(np.float32, copy=False).reshape(-1)
        return v if v.size == 128 else None
    if isinstance(vec, (list, tuple)):
        v = np.asarray(vec, dtype=np.float32).reshape(-1)
        return v if v.size == 128 else None
    if isinstance(vec, (bytes, bytearray, memoryview)):
        b = bytes(vec) if not isinstance(vec, (bytes, bytearray)) else vec
        if len(b) % 4 == 0:
            arr32 = np.frombuffer(b, dtype=np.float32)
            if arr32.size == 128:
                return arr32.astype(np.float32, copy=False)
        if len(b) % 8 == 0:
            arr64 = np.frombuffer(b, dtype=np.float64)
            if arr64.size == 128:
                return arr64.astype(np.float32)
        try:
            s = b.decode("utf-8", errors="ignore")
            arr = np.fromstring(s, sep=",", dtype=np.float32)
            if arr.size == 128:
                return arr
        except Exception:
            return None
    if isinstance(vec, str):
        s = vec.strip().replace("[", "").replace("]", "")
        arr = np.fromstring(s, sep=",", dtype=np.float32)
        return arr if arr.size == 128 else None
    return None


def load_students(db_path: str) -> List[Tuple[str, str, str, np.ndarray]]:
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT ad, soyad, okul_numarasi, yuz_vektoru FROM ogrenciler")
    rows = cur.fetchall()
    conn.close()

    students = []
    for ad, soyad, okul, vec in rows:
        v = _to_arr(vec)
        if v is None or not np.isfinite(v).all():
            continue
        students.append((ad, soyad, okul, v.astype(np.float32, copy=False)))
    print(f"{len(students)} öğrenci yüklendi (CPU).")
    return students


def match_face(
    encoding: np.ndarray,
    students_list: List[Tuple[str, str, str, np.ndarray]],
    thr: float = 0.55,
):
    """
    En iyi eşleşen öğrencinin ad+soyad'ını ve okul numarasını döndürür.
    Eşik üzerindeyse veya geçersizse 'Bilinmiyor', inf, None döner.
    """
    if encoding is None or encoding.size != 128:
        return "Bilinmiyor", float("inf"), None

    enc = np.asarray(encoding, dtype=np.float32, order="C")
    best_dist = float("inf")
    best_name = "Bilinmiyor"
    best_okul = None

    for ad, soyad, okul, vec in students_list:
        d = float(np.linalg.norm(enc - vec))
        if d < best_dist:
            best_dist = d
            best_name = f"{ad} {soyad}"
            best_okul = okul

    if (not np.isfinite(best_dist)) or best_dist >= thr:
        return "Bilinmiyor", best_dist, None

    return best_name, best_dist, best_okul


def main():
    students = load_students(DB_PATH)
    model = YOLO(MODEL_PATH)
    cap = cv2.VideoCapture(2, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise RuntimeError("Kamera açılamadı.")

    max_faces_seen = 0
    last_write = 0.0

    # Ders başlangıç zamanı ve takip reset'i
    record_start_time = time.time()
    reset_tracking()

    try:
        while True:
            now = time.time()

            ok, frame = cap.read()
            if not ok or frame is None:
                continue

            if DOWNSCALE != 1.0:
                frame = cv2.resize(
                    frame,
                    (
                        int(frame.shape[1] * DOWNSCALE),
                        int(frame.shape[0] * DOWNSCALE),
                    ),
                    interpolation=cv2.INTER_AREA,
                )

            res = model(frame, device="cpu", verbose=False, imgsz=IMGSZ)[0]
            boxes = [] if (res.boxes is None) else res.boxes
            current_faces = int(len(boxes))
            max_faces_seen = update_max(max_faces_seen, current_faces)

            h, w = frame.shape[:2]
            recognized_ids = set()

            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                x1 = max(0, min(x1, w - 1))
                x2 = max(0, min(x2, w - 1))
                y1 = max(0, min(y1, h - 1))
                y2 = max(0, min(y2, h - 1))
                if x2 <= x1 or y2 <= y1:
                    continue

                roi = frame[y1:y2, x1:x2]
                if roi.size == 0:
                    continue

                rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
                encs = face_recognition.face_encodings(rgb, num_jitters=1, model="small")
                if not encs:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(
                        frame,
                        "No encoding",
                        (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 0, 255),
                        2,
                    )
                    continue

                encoding = np.asarray(encs[0], dtype=np.float32).reshape(-1)
                name, dist, okul_no = match_face(encoding, students, thr=MATCH_THR)

                color = (0, 255, 0) if name != "Bilinmiyor" else (0, 0, 255)
                label = f"{name} ({dist:.2f})"
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame,
                    label,
                    (x1, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    color,
                    2,
                )

                # Eğer öğrenci biliniyorsa: yoklama + dikkat takibi
                if okul_no is not None:
                    recognized_ids.add(okul_no)
                    mark_present(okul_no, DB_PATH)
                    mark_seen(okul_no, now)

            # Bu frame'de görünmeyen aktif öğrenciler için 30 sn kaybolma kontrolü
            update_missing(recognized_ids, now, timeout=30.0)

            if now - last_write >= 0.5:
                write_stats(current_faces, max_faces_seen, STATS_PATH)
                last_write = now

            cv2.imshow("YOLOv8 + DLIB (CPU)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        # Ders sonunda dikkat oranlarını DB'ye yaz
        try:
            write_attentions_to_db(record_start_time, DB_PATH)
        except Exception:
            # Burada sessiz geçmek daha güvenli; kamera kapanırken crash istemeyiz.
            pass

        cap.release()
        cv2.destroyAllWindows()
        write_stats(0, max_faces_seen, STATS_PATH)


if __name__ == "__main__":
    main()
