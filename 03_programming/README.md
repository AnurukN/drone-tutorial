# บทที่ 3: การ Program Drone

## 🛠️ เครื่องมือหลัก

| เครื่องมือ | ใช้กับ | ภาษา |
|-----------|--------|------|
| **DroneKit** | ArduPilot | Python |
| **pymavlink** | MAVLink protocol | Python |
| **ROS** | Research/Complex | Python/C++ |
| **PX4 MAVSDK** | PX4 | Python/C++ |
| **Parrot SDK** | Parrot Drones | Python/JS |
| **DJI Mobile SDK** | DJI Drones | Swift/Java |

---

## 📁 ไฟล์ในบทนี้

- [`dronekit/01_connect.py`](./dronekit/01_connect.py) - เชื่อมต่อ Drone
- [`dronekit/02_takeoff_land.py`](./dronekit/02_takeoff_land.py) - ขึ้น-ลงจอด
- [`dronekit/03_goto_waypoint.py`](./dronekit/03_goto_waypoint.py) - บินไป GPS Point
- [`dronekit/04_mission.py`](./dronekit/04_mission.py) - Mission อัตโนมัติ
- [`mavlink/01_basic_mavlink.py`](./mavlink/01_basic_mavlink.py) - MAVLink ระดับต่ำ
- [`ros/README.md`](./ros/README.md) - ROS Introduction

---

## ⚡ Quick Start (SITL - ไม่ต้องมีโดรนจริง)

```bash
# Terminal 1: เริ่ม SITL Simulator
pip install dronekit-sitl
dronekit-sitl copter --home=13.7563,100.5018,20,0

# Terminal 2: เชื่อมต่อและ Program
python dronekit/01_connect.py
```

---

➡️ เริ่มต้นจาก [`dronekit/01_connect.py`](./dronekit/01_connect.py)
