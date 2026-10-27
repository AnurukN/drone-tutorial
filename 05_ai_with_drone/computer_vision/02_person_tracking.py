"""
AI Drone Tutorial - Person Tracking (Follow Me)
===============================================

ระบบ Follow Me: โดรนติดตามคนอัตโนมัติ

สิ่งที่จะเรียนรู้:
- ตรวจจับและ Track คนด้วย YOLO
- คำนวณ offset จากศูนย์กลาง
- แปลง visual offset → drone command
- Proportional Control (P-Controller)

วิธีรัน:
  # ทดสอบกับ Webcam (ไม่เชื่อมต่อ Drone)
  python 02_person_tracking.py --source 0 --dry-run

  # เชื่อมต่อ Drone จริง
  python 02_person_tracking.py --source 0 --connect tcp:127.0.0.1:5760
"""

import argparse
import time

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
# P-Controller สำหรับ Drone Control
# ============================================================

class PIDController:
    """Simple P/PD Controller สำหรับ Drone"""

    def __init__(self, kp: float, kd: float = 0.0, output_limit: float = 1.0):
        self.kp = kp
        self.kd = kd
        self.output_limit = output_limit
        self.last_error = 0
        self.last_time = time.time()

    def update(self, error: float) -> float:
        now = time.time()
        dt = now - self.last_time

        p_out = self.kp * error
        d_out = self.kd * (error - self.last_error) / max(dt, 0.001)

        output = p_out + d_out
        output = max(-self.output_limit, min(self.output_limit, output))

        self.last_error = error
        self.last_time = now

        return output


# ============================================================
# Person Tracker
# ============================================================

class PersonTracker:
    """
    ระบบติดตามคนด้วย YOLO
    คำนวณ drone command จากตำแหน่งคนในภาพ
    """

    def __init__(self, model_path: str = "yolov8n.pt",
                 frame_width: int = 640,
                 frame_height: int = 480):

        if not YOLO_AVAILABLE:
            raise ImportError("pip install ultralytics")

        self.model = YOLO(model_path)
        self.frame_w = frame_width
        self.frame_h = frame_height

        # Dead zone (% ของภาพ) - ไม่สั่งถ้าอยู่ในโซนนี้
        self.dead_zone_x = 0.1  # 10% ของความกว้าง
        self.dead_zone_y = 0.15  # 15% ของความสูง
        self.dead_zone_size = 0.15  # 15% ของความสูงสำหรับ altitude

        # Controllers
        self.yaw_ctrl = PIDController(kp=0.003, kd=0.001, output_limit=0.5)
        self.pitch_ctrl = PIDController(kp=0.003, kd=0.001, output_limit=0.5)
        self.throttle_ctrl = PIDController(kp=0.002, kd=0.0005, output_limit=0.3)

        # Target size (% ของ frame height) - รักษาระยะห่าง
        self.target_size_ratio = 0.4  # คนควรสูงประมาณ 40% ของภาพ

        # Tracking state
        self.tracking = False
        self.target_id = None

        print("✅ PersonTracker พร้อม")

    def find_target(self, frame: np.ndarray) -> dict | None:
        """ตรวจจับและเลือกเป้าหมาย (คนที่ใหญ่ที่สุด)"""

        results = self.model(frame, classes=[0], conf=0.6, verbose=False)

        best_detection = None
        max_area = 0

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                area = (x2 - x1) * (y2 - y1)
                conf = float(box.conf[0])

                if area > max_area:
                    max_area = area
                    best_detection = {
                        "bbox": (x1, y1, x2, y2),
                        "center": ((x1 + x2) // 2, (y1 + y2) // 2),
                        "height": y2 - y1,
                        "area": area,
                        "confidence": conf,
                    }

        return best_detection

    def compute_commands(self, detection: dict) -> dict:
        """
        คำนวณ Drone Commands จาก Detection

        Returns:
            dict ของ commands: yaw, pitch, throttle, roll
            ค่าช่วง -1.0 ถึง 1.0
        """
        cx, cy = detection["center"]
        person_height = detection["height"]

        # คำนวณ offset จากศูนย์กลางภาพ
        # normalize เป็น -1 ถึง 1
        dx = (cx - self.frame_w / 2) / (self.frame_w / 2)
        dy = (cy - self.frame_h / 2) / (self.frame_h / 2)

        # คำนวณ size error (สำหรับ throttle/distance)
        size_ratio = person_height / self.frame_h
        size_error = self.target_size_ratio - size_ratio

        # Apply dead zone
        if abs(dx) < self.dead_zone_x:
            dx = 0
        if abs(dy) < self.dead_zone_y:
            dy = 0
        if abs(size_error) < self.dead_zone_size:
            size_error = 0

        # P-Controller output
        yaw = self.yaw_ctrl.update(dx)        # หมุนตามคน (ซ้าย/ขวา)
        throttle = self.throttle_ctrl.update(-dy)  # ขึ้น/ลงตามระดับคน
        pitch = self.pitch_ctrl.update(-size_error)  # บินเข้า/ออกตามระยะห่าง

        return {
            "yaw": yaw,
            "pitch": pitch,
            "throttle": throttle,
            "roll": 0.0,
            "dx_pixels": cx - self.frame_w // 2,
            "dy_pixels": cy - self.frame_h // 2,
            "size_ratio": size_ratio,
            "size_error": size_error,
        }

    def draw_tracking(self, frame: np.ndarray, detection: dict,
                      commands: dict) -> np.ndarray:
        """วาด Tracking visualization"""

        x1, y1, x2, y2 = detection["bbox"]
        cx, cy = detection["center"]

        # Tracking box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # เส้นจากศูนย์กลางไปหาเป้าหมาย
        frame_cx = self.frame_w // 2
        frame_cy = self.frame_h // 2
        cv2.arrowedLine(frame, (frame_cx, frame_cy), (cx, cy),
                        (0, 255, 255), 2, tipLength=0.1)

        # Crosshair กลางภาพ
        cv2.line(frame, (frame_cx - 30, frame_cy), (frame_cx + 30, frame_cy),
                (0, 255, 255), 1)
        cv2.line(frame, (frame_cx, frame_cy - 30), (frame_cx, frame_cy + 30),
                (0, 255, 255), 1)

        # Dead zone rectangle
        dz_w = int(self.dead_zone_x * self.frame_w)
        dz_h = int(self.dead_zone_y * self.frame_h)
        cv2.rectangle(frame,
                     (frame_cx - dz_w, frame_cy - dz_h),
                     (frame_cx + dz_w, frame_cy + dz_h),
                     (100, 100, 255), 1)

        # Confidence
        cv2.putText(frame, f"Person {detection['confidence']:.0%}",
                   (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Commands info
        info_lines = [
            f"TRACKING: ACTIVE",
            f"Yaw:    {commands['yaw']:+.2f}",
            f"Pitch:  {commands['pitch']:+.2f}",
            f"Throt:  {commands['throttle']:+.2f}",
            f"Size:   {commands['size_ratio']:.0%}",
        ]

        # Background
        cv2.rectangle(frame, (0, 0), (180, 160), (0, 0, 0), -1)

        for i, line in enumerate(info_lines):
            color = (0, 255, 0) if i == 0 else (200, 200, 200)
            cv2.putText(frame, line, (5, 20 + i * 27),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)

        return frame

    def draw_searching(self, frame: np.ndarray) -> np.ndarray:
        """แสดง Searching state"""
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2

        # Scanning animation
        tick = int(time.time() * 2) % 8
        for i in range(8):
            angle = i * 45
            r = 60
            import math
            x = int(cx + r * math.cos(math.radians(angle)))
            y = int(cy + r * math.sin(math.radians(angle)))
            alpha = 255 if i == tick else 80
            cv2.circle(frame, (x, y), 5, (0, alpha, 0), -1)

        cv2.putText(frame, "SEARCHING...", (cx - 70, cy + 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 0), 2)

        return frame


# ============================================================
# Drone Controller Integration
# ============================================================

class DroneFollowMe:
    """ระบบ Follow Me แบบ Complete"""

    def __init__(self, connection_string: str = None,
                 dry_run: bool = True):
        self.dry_run = dry_run
        self.vehicle = None

        if not dry_run and connection_string:
            if not DRONEKIT_AVAILABLE:
                raise ImportError("pip install dronekit")

            print(f"🚁 เชื่อมต่อ Drone: {connection_string}")
            self.vehicle = connect(connection_string, wait_ready=True)
            print("✅ เชื่อมต่อสำเร็จ")

    def send_velocity(self, vx: float, vy: float, vz: float, yaw_rate: float = 0):
        """
        ส่งคำสั่งความเร็วไปยัง Drone (GUIDED mode)

        Args:
            vx: ความเร็วหน้า/หลัง (m/s)
            vy: ความเร็วซ้าย/ขวา (m/s)
            vz: ความเร็วขึ้น/ลง (m/s, - = ขึ้น)
            yaw_rate: อัตราหมุน (rad/s)
        """
        if self.dry_run:
            print(f"[DRY RUN] Velocity: vx={vx:.2f} vy={vy:.2f} "
                  f"vz={vz:.2f} yaw={yaw_rate:.2f}")
            return

        if not self.vehicle:
            return

        msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
            0,       # time_boot_ms
            0, 0,    # target system, target component
            mavutil.mavlink.MAV_FRAME_BODY_NED,  # ใช้ body frame (หน้าโดรน = x)
            0b0000111111000111,  # type_mask: velocity only
            0, 0, 0,             # x, y, z (ไม่ใช้)
            vx, vy, vz,          # vx, vy, vz
            0, 0, 0,             # ax, ay, az
            0, yaw_rate          # yaw, yaw_rate
        )
        self.vehicle.send_mavlink(msg)

    def apply_commands(self, commands: dict, max_speed: float = 2.0):
        """แปลง normalized commands (-1..1) เป็น velocity"""
        vx = commands["pitch"] * max_speed    # หน้า/หลัง
        vy = commands["roll"] * max_speed     # ซ้าย/ขวา
        vz = -commands["throttle"] * max_speed  # ขึ้น/ลง (กลับทิศ)
        yaw_rate = commands["yaw"] * 0.5     # rad/s

        self.send_velocity(vx, vy, vz, yaw_rate)

    def close(self):
        if self.vehicle:
            self.vehicle.close()


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Drone Person Tracking (Follow Me)")
    parser.add_argument("--source", default="0")
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--connect", default=None,
                        help="Drone connection string")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="ทดสอบโดยไม่เชื่อมต่อ Drone จริง")
    parser.add_argument("--max-speed", type=float, default=1.5,
                        help="ความเร็วสูงสุด (m/s)")
    args = parser.parse_args()

    source = int(args.source) if args.source.isdigit() else args.source

    # สร้าง Objects
    tracker = PersonTracker(model_path=args.model,
                           frame_width=640, frame_height=480)
    drone = DroneFollowMe(connection_string=args.connect,
                         dry_run=args.dry_run or args.connect is None)

    # เปิด Camera
    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print(f"❌ ไม่สามารถเปิด: {source}")
        return

    print("\n🎯 Follow Me Active!")
    print("   กด Q หยุด | กด SPACE เริ่ม/หยุด tracking")
    print("   DRY RUN:", args.dry_run or args.connect is None)

    tracking_enabled = True
    last_cmd_time = time.time()
    CMD_INTERVAL = 0.1  # ส่งคำสั่งทุก 100ms

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # หาเป้าหมาย
            detection = tracker.find_target(frame) if tracking_enabled else None

            if detection:
                # คำนวณคำสั่ง
                commands = tracker.compute_commands(detection)

                # แสดง visualization
                frame = tracker.draw_tracking(frame, detection, commands)

                # ส่งคำสั่งไปยัง Drone (rate-limited)
                if time.time() - last_cmd_time >= CMD_INTERVAL:
                    drone.apply_commands(commands, max_speed=args.max_speed)
                    last_cmd_time = time.time()
            else:
                if tracking_enabled:
                    frame = tracker.draw_searching(frame)
                    # Stop drone เมื่อไม่เห็นเป้าหมาย
                    if time.time() - last_cmd_time >= CMD_INTERVAL:
                        drone.send_velocity(0, 0, 0, 0)
                        last_cmd_time = time.time()

            # Status bar
            status = "TRACKING ON" if tracking_enabled else "TRACKING OFF"
            cv2.putText(frame, status,
                       (frame.shape[1] - 180, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                       (0, 255, 0) if tracking_enabled else (0, 0, 255), 2)

            cv2.imshow("Drone Follow Me", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord(" "):
                tracking_enabled = not tracking_enabled
                print(f"\nTracking: {'ON' if tracking_enabled else 'OFF'}")

    except KeyboardInterrupt:
        print("\n⚠️  หยุดโดยผู้ใช้")
    finally:
        # หยุดโดรน
        drone.send_velocity(0, 0, 0, 0)
        cap.release()
        cv2.destroyAllWindows()
        drone.close()
        print("✅ เสร็จสิ้น")


if __name__ == "__main__":
    main()
