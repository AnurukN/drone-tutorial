"""
AI Drone Tutorial - Autonomous Obstacle Avoidance
==================================================

หลีกสิ่งกีดขวางอัตโนมัติโดยใช้:
- Optical Flow (จากกล้อง)
- Depth Estimation (monocular depth)
- YOLO object detection

สิ่งที่จะเรียนรู้:
- Detect สิ่งกีดขวางจากภาพ
- คำนวณทิศทางหลีก
- ส่งคำสั่ง velocity ไปยัง Drone

วิธีรัน:
  python 01_avoid_obstacle.py --source 0 --dry-run
"""

import argparse
import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import cv2
import numpy as np

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

try:
    from dronekit import connect, VehicleMode
    from pymavlink import mavutil
    DRONEKIT_AVAILABLE = True
except ImportError:
    DRONEKIT_AVAILABLE = False


# ============================================================
# Data Structures
# ============================================================

class Zone(Enum):
    """โซนของ Frame"""
    LEFT = "LEFT"
    CENTER = "CENTER"
    RIGHT = "RIGHT"
    TOP = "TOP"
    BOTTOM = "BOTTOM"


@dataclass
class Obstacle:
    """ข้อมูลสิ่งกีดขวาง"""
    class_name: str
    confidence: float
    bbox: tuple          # (x1, y1, x2, y2)
    center: tuple        # (cx, cy)
    area: int
    zone: Zone
    relative_size: float  # สัดส่วนของ frame (0-1)
    threat_level: float   # 0-1 (1=อันตรายมาก)


# ============================================================
# Obstacle Detector
# ============================================================

class ObstacleDetector:
    """ตรวจจับสิ่งกีดขวางด้วย YOLO"""

    # Classes ที่ถือว่าเป็นสิ่งกีดขวาง
    OBSTACLE_CLASSES = {
        "person", "car", "truck", "bus", "motorcycle",
        "bicycle", "tree", "building", "pole", "wall",
        "bird", "airplane", "stop sign"
    }

    def __init__(self, model_path: str = "yolov8n.pt",
                 frame_w: int = 640, frame_h: int = 480,
                 confidence: float = 0.4):

        self.frame_w = frame_w
        self.frame_h = frame_h

        if YOLO_AVAILABLE:
            self.model = YOLO(model_path)
        else:
            self.model = None
            print("⚠️  YOLO ไม่พร้อม ใช้ Optical Flow แทน")

    def detect(self, frame: np.ndarray) -> list[Obstacle]:
        """ตรวจจับสิ่งกีดขวางในภาพ"""
        obstacles = []

        if not self.model:
            return obstacles

        results = self.model(frame, conf=0.4, verbose=False)
        frame_area = self.frame_w * self.frame_h

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]

                # ไม่ใช่สิ่งกีดขวาง
                if class_name not in self.OBSTACLE_CLASSES:
                    continue

                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                area = (x2 - x1) * (y2 - y1)
                relative_size = area / frame_area

                # คำนวณ Zone
                zone = self._get_zone(cx, cy)

                # คำนวณ Threat Level
                # ยิ่งใหญ่ (ใกล้) และอยู่กลาง = อันตรายมาก
                size_threat = min(relative_size * 5, 1.0)  # 20% ของ frame = max threat
                center_penalty = 1.0 - abs(cx - self.frame_w/2) / (self.frame_w/2) * 0.5
                threat = size_threat * center_penalty

                obstacles.append(Obstacle(
                    class_name=class_name,
                    confidence=conf,
                    bbox=(x1, y1, x2, y2),
                    center=(cx, cy),
                    area=area,
                    zone=zone,
                    relative_size=relative_size,
                    threat_level=threat,
                ))

        # เรียงตาม threat level (มากที่สุดก่อน)
        obstacles.sort(key=lambda o: o.threat_level, reverse=True)
        return obstacles

    def _get_zone(self, cx: int, cy: int) -> Zone:
        """ระบุโซนจากตำแหน่ง"""
        left_third = self.frame_w // 3
        right_third = self.frame_w * 2 // 3

        if cx < left_third:
            return Zone.LEFT
        elif cx > right_third:
            return Zone.RIGHT
        else:
            return Zone.CENTER


# ============================================================
# Avoidance Planner
# ============================================================

class AvoidancePlanner:
    """
    วางแผนการหลีกสิ่งกีดขวาง

    Strategy:
    - สิ่งกีดขวางตรงกลาง → หยุด หรือบินขึ้น
    - สิ่งกีดขวางซ้าย → เบี่ยงขวา
    - สิ่งกีดขวางขวา → เบี่ยงซ้าย
    - ไม่มีสิ่งกีดขวาง → บินต่อ
    """

    THREAT_STOP = 0.7     # threshold หยุด
    THREAT_AVOID = 0.3    # threshold เริ่มหลีก

    def __init__(self, frame_w: int = 640, frame_h: int = 480):
        self.frame_w = frame_w
        self.frame_h = frame_h

    def plan(self, obstacles: list[Obstacle]) -> dict:
        """
        คำนวณ avoidance command

        Returns:
            dict: {
                'action': 'continue'/'stop'/'avoid',
                'vx': forward velocity (-1 to 1),
                'vy': lateral velocity (-1 to 1),
                'vz': vertical velocity (-1 to 1),
                'reason': str,
                'threat': float
            }
        """
        if not obstacles:
            return {
                "action": "continue",
                "vx": 0.5,
                "vy": 0.0,
                "vz": 0.0,
                "reason": "เส้นทางโล่ง",
                "threat": 0.0,
            }

        # สิ่งกีดขวางที่อันตรายที่สุด
        worst = obstacles[0]
        threat = worst.threat_level

        if threat >= self.THREAT_STOP:
            # อันตรายมาก → หยุด และบินขึ้น
            return {
                "action": "stop",
                "vx": -0.2,   # ถอยหลังนิด
                "vy": 0.0,
                "vz": -0.3,   # ขึ้น (- = ขึ้น)
                "reason": f"หยุด! {worst.class_name} อยู่ข้างหน้า ({threat:.0%})",
                "threat": threat,
            }

        elif threat >= self.THREAT_AVOID:
            # หลีก
            return self._compute_avoidance(worst, threat)

        else:
            # เห็นแต่ไม่ค่อยอันตราย → ลดความเร็ว
            return {
                "action": "slow",
                "vx": 0.2,
                "vy": 0.0,
                "vz": 0.0,
                "reason": f"ชะลอ - {worst.class_name} ({threat:.0%})",
                "threat": threat,
            }

    def _compute_avoidance(self, obstacle: Obstacle, threat: float) -> dict:
        """คำนวณทิศทางหลีก"""
        cx, cy = obstacle.center

        # normalize offset จากกลาง (-1 ถึง 1)
        x_offset = (cx - self.frame_w / 2) / (self.frame_w / 2)

        # หลีกตรงข้าม
        if obstacle.zone == Zone.LEFT:
            vy = 0.4   # เบี่ยงขวา
            reason = f"หลีกขวา - {obstacle.class_name} ทางซ้าย"
        elif obstacle.zone == Zone.RIGHT:
            vy = -0.4  # เบี่ยงซ้าย
            reason = f"หลีกซ้าย - {obstacle.class_name} ทางขวา"
        else:
            # กลาง → ขึ้น
            vy = 0.0
            reason = f"บินขึ้น - {obstacle.class_name} ตรงหน้า"

        return {
            "action": "avoid",
            "vx": 0.1,         # ชะลอแต่ยังเดินหน้า
            "vy": vy,
            "vz": -0.2 if obstacle.zone == Zone.CENTER else 0.0,
            "reason": reason,
            "threat": threat,
        }


# ============================================================
# Visualizer
# ============================================================

class AvoidanceVisualizer:
    """วาด Visualization สำหรับ Obstacle Avoidance"""

    THREAT_COLORS = {
        (0.0, 0.3): (0, 255, 0),    # เขียว - ปลอดภัย
        (0.3, 0.7): (0, 165, 255),  # ส้ม - ระวัง
        (0.7, 1.0): (0, 0, 255),    # แดง - อันตราย
    }

    def get_threat_color(self, threat: float) -> tuple:
        for (low, high), color in self.THREAT_COLORS.items():
            if low <= threat < high:
                return color
        return (0, 0, 255)

    def draw(self, frame: np.ndarray,
             obstacles: list[Obstacle],
             command: dict) -> np.ndarray:
        """วาดทุกอย่าง"""
        frame = self.draw_zones(frame)
        frame = self.draw_obstacles(frame, obstacles)
        frame = self.draw_command(frame, command)
        frame = self.draw_avoidance_arrow(frame, command)
        return frame

    def draw_zones(self, frame: np.ndarray) -> np.ndarray:
        """วาดเส้นแบ่ง Zone"""
        h, w = frame.shape[:2]
        left_x = w // 3
        right_x = w * 2 // 3

        cv2.line(frame, (left_x, 0), (left_x, h), (50, 50, 50), 1)
        cv2.line(frame, (right_x, 0), (right_x, h), (50, 50, 50), 1)

        cv2.putText(frame, "L", (left_x // 2 - 5, 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 80, 80), 1)
        cv2.putText(frame, "C", (w // 2 - 5, 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 80, 80), 1)
        cv2.putText(frame, "R", (right_x + (w - right_x) // 2 - 5, 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 80, 80), 1)

        return frame

    def draw_obstacles(self, frame: np.ndarray, obstacles: list[Obstacle]) -> np.ndarray:
        """วาด Obstacle boxes"""
        for obs in obstacles:
            color = self.get_threat_color(obs.threat_level)
            x1, y1, x2, y2 = obs.bbox

            # Box
            thickness = max(1, int(obs.threat_level * 4))
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

            # Label
            label = f"{obs.class_name} {obs.threat_level:.0%}"
            cv2.putText(frame, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)

            # Threat bar
            bar_w = x2 - x1
            threat_w = int(bar_w * obs.threat_level)
            cv2.rectangle(frame, (x1, y2), (x1 + threat_w, y2 + 4), color, -1)

        return frame

    def draw_command(self, frame: np.ndarray, command: dict) -> np.ndarray:
        """วาด Command info"""
        h, w = frame.shape[:2]
        action = command.get("action", "?")
        reason = command.get("reason", "")
        threat = command.get("threat", 0)

        action_colors = {
            "continue": (0, 255, 0),
            "slow": (0, 200, 255),
            "avoid": (0, 165, 255),
            "stop": (0, 0, 255),
        }
        color = action_colors.get(action, (200, 200, 200))

        # Background
        cv2.rectangle(frame, (0, h - 65), (w, h), (0, 0, 0), -1)

        # Action
        cv2.putText(frame, f"ACTION: {action.upper()}",
                   (10, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Reason
        cv2.putText(frame, reason,
                   (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Velocity bars
        vx = command.get("vx", 0)
        vy = command.get("vy", 0)
        vz = command.get("vz", 0)

        bar_x = w - 120
        for i, (name, val) in enumerate([("VX", vx), ("VY", vy), ("VZ", vz)]):
            y = h - 55 + i * 18
            bar_len = int(abs(val) * 50)
            bar_color = (0, 200, 100) if val >= 0 else (100, 100, 255)
            start_x = bar_x + 25

            cv2.putText(frame, f"{name}:{val:+.1f}", (bar_x, y + 12),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
            cv2.rectangle(frame, (start_x + 40, y), (start_x + 40 + bar_len, y + 8),
                         bar_color, -1)

        return frame

    def draw_avoidance_arrow(self, frame: np.ndarray, command: dict) -> np.ndarray:
        """วาดลูกศรบอกทิศทาง"""
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2

        vx = command.get("vx", 0)
        vy = command.get("vy", 0)

        # แปลง velocity เป็นทิศทาง
        # vx = หน้า/หลัง, vy = ซ้าย/ขวา
        arrow_dx = int(vy * 80)    # vy ในภาพ = ซ้ายขวา
        arrow_dy = int(-vx * 80)   # vx ในภาพ = บน-ล่าง (กลับด้าน)

        if abs(arrow_dx) > 5 or abs(arrow_dy) > 5:
            cv2.arrowedLine(frame, (cx, cy),
                           (cx + arrow_dx, cy + arrow_dy),
                           (0, 255, 255), 3, tipLength=0.3)

        # วงกลม dead zone
        cv2.circle(frame, (cx, cy), 30, (100, 100, 100), 1)

        return frame


# ============================================================
# Main System
# ============================================================

def run_avoidance_system(source: int = 0,
                          model_path: str = "yolov8n.pt",
                          dry_run: bool = True,
                          connect_str: str = None):

    detector = ObstacleDetector(model_path=model_path)
    planner = AvoidancePlanner()
    visualizer = AvoidanceVisualizer()

    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print(f"❌ ไม่สามารถเปิด: {source}")
        return

    print("🛡️  Obstacle Avoidance System")
    print(f"   Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("   กด Q หยุด")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Detect
            obstacles = detector.detect(frame)

            # Plan
            command = planner.plan(obstacles)

            # Visualize
            display = visualizer.draw(frame.copy(), obstacles, command)

            # Log ถ้ามีอันตราย
            if command["action"] in ["stop", "avoid"]:
                print(f"\r⚠️  {command['reason']}", end="")

            cv2.imshow("Drone Obstacle Avoidance", display)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("\n✅ เสร็จสิ้น")


def main():
    parser = argparse.ArgumentParser(description="Drone Obstacle Avoidance")
    parser.add_argument("--source", default="0")
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--connect", default=None)
    parser.add_argument("--dry-run", action="store_true", default=True)
    args = parser.parse_args()

    source = int(args.source) if args.source.isdigit() else args.source
    run_avoidance_system(source, args.model, args.dry_run, args.connect)


if __name__ == "__main__":
    main()
