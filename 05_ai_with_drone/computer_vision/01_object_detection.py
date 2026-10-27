"""
AI Drone Tutorial - Computer Vision: Object Detection
======================================================

ใช้ YOLOv8 ตรวจจับวัตถุจากกล้อง Drone แบบ Real-time

สิ่งที่จะเรียนรู้:
- โหลด YOLO model
- ตรวจจับวัตถุใน frame
- วาด Bounding Box
- นับจำนวนสิ่งของ
- ส่งข้อมูลไปยัง Flight Controller

ติดตั้ง:
  pip install ultralytics opencv-python

วิธีรัน:
  # ใช้ Webcam
  python 01_object_detection.py --source 0

  # ใช้ Video file
  python 01_object_detection.py --source video.mp4

  # ใช้ RTSP stream จากกล้อง Drone
  python 01_object_detection.py --source rtsp://192.168.1.1/live
"""

import argparse
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️  ultralytics ไม่ได้ติดตั้ง: pip install ultralytics")


# ============================================================
# Object Detector
# ============================================================

class DroneObjectDetector:
    """
    ระบบตรวจจับวัตถุสำหรับ Drone
    ใช้ YOLOv8 สำหรับ Real-time detection
    """

    # สีสำหรับแต่ละ class
    COLORS = {
        "person": (0, 255, 0),       # เขียว
        "car": (0, 0, 255),          # แดง
        "truck": (0, 128, 255),      # ส้ม
        "bicycle": (255, 0, 0),      # น้ำเงิน
        "motorcycle": (255, 0, 128), # ชมพู
        "airplane": (128, 255, 0),   # เหลือง-เขียว
        "dog": (255, 255, 0),        # เหลือง
        "cat": (0, 255, 255),        # ฟ้า
    }
    DEFAULT_COLOR = (200, 200, 200)

    def __init__(self, model_path: str = "yolov8n.pt",
                 confidence: float = 0.5,
                 target_classes: list = None):
        """
        Args:
            model_path: YOLO model (n=nano, s=small, m=medium, l=large, x=xlarge)
            confidence: ความมั่นใจขั้นต่ำ (0-1)
            target_classes: list ของ class ที่สนใจ (None = ทั้งหมด)
        """
        if not YOLO_AVAILABLE:
            raise ImportError("กรุณาติดตั้ง: pip install ultralytics")

        print(f"📦 โหลด YOLO model: {model_path}")
        self.model = YOLO(model_path)
        self.confidence = confidence
        self.target_classes = target_classes

        # Stats
        self.frame_count = 0
        self.detection_history = defaultdict(list)

        print(f"✅ โหลด Model สำเร็จ")
        print(f"   Classes: {len(self.model.names)} วัตถุ")
        print(f"   Confidence threshold: {confidence}")

    def detect(self, frame: np.ndarray) -> tuple[np.ndarray, dict]:
        """
        ตรวจจับวัตถุใน frame

        Args:
            frame: OpenCV frame (BGR)

        Returns:
            (annotated_frame, detection_info)
        """
        self.frame_count += 1

        # Run YOLO inference
        results = self.model(frame, conf=self.confidence, verbose=False)

        # Parse results
        detections = []
        class_counts = defaultdict(int)

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]
                confidence = float(box.conf[0])

                # Filter target classes
                if self.target_classes and class_name not in self.target_classes:
                    continue

                # Bounding box (x1, y1, x2, y2)
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                # Center point
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                detections.append({
                    "class": class_name,
                    "confidence": confidence,
                    "bbox": (x1, y1, x2, y2),
                    "center": (cx, cy),
                    "area": (x2 - x1) * (y2 - y1),
                })

                class_counts[class_name] += 1

        # วาด annotations
        annotated = self._draw_detections(frame.copy(), detections)

        # เพิ่ม Info overlay
        annotated = self._draw_info(annotated, class_counts)

        detection_info = {
            "detections": detections,
            "class_counts": dict(class_counts),
            "total": len(detections),
            "frame": self.frame_count,
        }

        return annotated, detection_info

    def _draw_detections(self, frame: np.ndarray, detections: list) -> np.ndarray:
        """วาด Bounding Box และ Label"""
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            class_name = det["class"]
            conf = det["confidence"]
            cx, cy = det["center"]

            # สี
            color = self.COLORS.get(class_name, self.DEFAULT_COLOR)

            # Bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Label background
            label = f"{class_name} {conf:.0%}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(frame, (x1, y1-th-8), (x1+tw+4, y1), color, -1)

            # Label text
            cv2.putText(frame, label,
                       (x1+2, y1-4),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                       (0, 0, 0), 1)

            # Center point
            cv2.circle(frame, (cx, cy), 4, color, -1)

        return frame

    def _draw_info(self, frame: np.ndarray, class_counts: dict) -> np.ndarray:
        """วาด Info overlay"""
        h, w = frame.shape[:2]

        # Background panel
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (250, 30 + len(class_counts) * 25 + 30),
                     (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Title
        cv2.putText(frame, f"Drone Detection - Frame {self.frame_count}",
                   (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Count แต่ละ class
        y = 45
        for class_name, count in sorted(class_counts.items()):
            color = self.COLORS.get(class_name, self.DEFAULT_COLOR)
            cv2.putText(frame, f"  {class_name}: {count}",
                       (5, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            y += 25

        if not class_counts:
            cv2.putText(frame, "  ไม่พบวัตถุ",
                       (5, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

        # Crosshair ตรงกลาง (จุดศูนย์กลางของกล้อง)
        cx, cy = w // 2, h // 2
        cv2.line(frame, (cx - 20, cy), (cx + 20, cy), (0, 255, 255), 1)
        cv2.line(frame, (cx, cy - 20), (cx, cy + 20), (0, 255, 255), 1)
        cv2.circle(frame, (cx, cy), 30, (0, 255, 255), 1)

        return frame

    def get_largest_detection(self, detections: list,
                               class_filter: str = None) -> dict | None:
        """หาวัตถุที่ใหญ่ที่สุด (อาจอยู่ใกล้ที่สุด)"""
        filtered = [d for d in detections
                   if class_filter is None or d["class"] == class_filter]

        if not filtered:
            return None

        return max(filtered, key=lambda d: d["area"])

    def get_center_offset(self, detection: dict, frame_size: tuple) -> tuple:
        """
        คำนวณ offset จากศูนย์กลางภาพ
        ใช้สำหรับ Follow target หรือ Center frame

        Returns:
            (dx, dy) - offset เป็น pixel (-= ซ้าย/ขึ้น, += ขวา/ลง)
        """
        w, h = frame_size
        frame_cx, frame_cy = w // 2, h // 2

        target_cx, target_cy = detection["center"]

        dx = target_cx - frame_cx
        dy = target_cy - frame_cy

        return dx, dy


# ============================================================
# Main Demo
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Drone Object Detection")
    parser.add_argument("--source", default="0",
                        help="Video source (0=webcam, file path, RTSP URL)")
    parser.add_argument("--model", default="yolov8n.pt",
                        help="YOLO model")
    parser.add_argument("--conf", type=float, default=0.5,
                        help="Confidence threshold")
    parser.add_argument("--classes", nargs="+",
                        help="Target classes (e.g., --classes person car)")
    parser.add_argument("--save", action="store_true",
                        help="บันทึก video output")
    args = parser.parse_args()

    # แปลง source
    source = int(args.source) if args.source.isdigit() else args.source

    # สร้าง Detector
    detector = DroneObjectDetector(
        model_path=args.model,
        confidence=args.conf,
        target_classes=args.classes
    )

    # เปิด Video
    print(f"\n📹 เปิด video source: {source}")
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"❌ ไม่สามารถเปิด: {source}")
        return

    # Video writer (ถ้าต้องการบันทึก)
    writer = None
    if args.save:
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        writer = cv2.VideoWriter(
            "output_detection.mp4",
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps, (w, h)
        )

    print("🎯 เริ่ม Detection... (กด Q เพื่อหยุด)")
    print("-" * 40)

    fps_timer = time.time()
    fps_count = 0
    fps_display = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Video จบแล้ว")
                break

            # ตรวจจับ
            annotated, info = detector.detect(frame)

            # คำนวณ FPS
            fps_count += 1
            if time.time() - fps_timer >= 1.0:
                fps_display = fps_count
                fps_count = 0
                fps_timer = time.time()

            # แสดง FPS
            cv2.putText(annotated, f"FPS: {fps_display}",
                       (annotated.shape[1] - 100, 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                       (0, 255, 0), 2)

            # แสดงผล
            cv2.imshow("Drone Object Detection", annotated)

            # Log ผล
            if info["total"] > 0:
                counts_str = ", ".join(
                    f"{k}:{v}" for k, v in info["class_counts"].items()
                )
                print(f"Frame {info['frame']:4d}: [{counts_str}]", end="\r")

            if writer:
                writer.write(annotated)

            # กด Q หยุด
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except KeyboardInterrupt:
        print("\n⚠️  หยุดโดยผู้ใช้")
    finally:
        cap.release()
        if writer:
            writer.release()
        cv2.destroyAllWindows()

        print(f"\n\n📊 สรุป:")
        print(f"   ประมวลผลทั้งหมด: {detector.frame_count} frames")
        print("✅ เสร็จสิ้น")


if __name__ == "__main__":
    main()
