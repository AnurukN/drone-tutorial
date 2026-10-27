# บทที่ 5: AI กับ Drone

## 🤖 AI ช่วยอะไร Drone ได้บ้าง?

```
                    ┌─────────────────────┐
                    │      DRONE AI       │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼──────┐    ┌──────────▼──────────┐  ┌───────▼───────┐
│  Computer    │    │   Autonomous        │  │  AI Decision  │
│  Vision      │    │   Navigation        │  │  Making       │
│              │    │                     │  │  (Claude AI)  │
│ • ตรวจจับวัตถุ│    │ • Path Planning     │  │               │
│ • Track คน  │    │ • Obstacle Avoid    │  │ • วิเคราะห์ภาพ │
│ • อ่านป้าย   │    │ • Formation Flight  │  │ • ตัดสินใจ    │
│ • นับสิ่งของ  │    │ • SLAM              │  │ • รายงาน     │
└──────────────┘    └─────────────────────┘  └───────────────┘
```

---

## 📁 ไฟล์ในบทนี้

| ไฟล์ | หัวข้อ |
|-----|--------|
| [`computer_vision/01_object_detection.py`](./computer_vision/01_object_detection.py) | ตรวจจับวัตถุด้วย YOLO |
| [`computer_vision/02_person_tracking.py`](./computer_vision/02_person_tracking.py) | ติดตามคน |
| [`autonomous_navigation/01_avoid_obstacle.py`](./autonomous_navigation/01_avoid_obstacle.py) | หลีกสิ่งกีดขวาง |
| [`claude_ai/01_drone_assistant.py`](./claude_ai/01_drone_assistant.py) | AI Assistant สำหรับ Drone |
| [`claude_ai/02_vision_analysis.py`](./claude_ai/02_vision_analysis.py) | วิเคราะห์ภาพจากกล้องด้วย Claude |

---

## 🔧 Setup

```bash
# ติดตั้ง AI libraries
pip install ultralytics opencv-python anthropic python-dotenv

# สร้าง .env
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
```

---

## 🏗️ Architecture: AI Drone System

```
Camera ──▶ OpenCV ──▶ YOLO Detection ──▶ ┐
                                          │
GPS ──────▶ DroneKit ───────────────────▶ ├──▶ Decision Engine ──▶ Flight Commands
                                          │    (Python Logic /
Sensors ──▶ MAVLink ──────────────────▶ ┘     Claude AI)
```

---

➡️ เริ่มจาก [`computer_vision/01_object_detection.py`](./computer_vision/01_object_detection.py)
