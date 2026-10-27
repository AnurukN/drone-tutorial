# 🚁 Drone Tutorial: จากพื้นฐานสู่ AI

คู่มือเรียนรู้ Drone แบบครบวงจร ตั้งแต่ความรู้พื้นฐาน การสร้าง การ Program จนถึงการใช้ AI

---

## 📚 สารบัญหลักสูตร

| บท | หัวข้อ | ระดับ |
|----|--------|-------|
| 01 | [พื้นฐาน Drone](./01_basics/README.md) | เริ่มต้น |
| 02 | [Hardware & การสร้าง Drone](./02_hardware/README.md) | เริ่มต้น |
| 03 | [การ Program Drone](./03_programming/README.md) | กลาง |
| 04 | [Simulation (SITL)](./04_simulation/README.md) | กลาง |
| 05 | [AI กับ Drone](./05_ai_with_drone/README.md) | ขั้นสูง |
| 06 | [Projects จริง](./06_projects/README.md) | ขั้นสูง |

---

## 🛠️ สิ่งที่ต้องมีก่อนเริ่ม

### Software
- Python 3.8+
- [ArduPilot SITL](https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html) (สำหรับ simulate)
- [Mission Planner](https://ardupilot.org/planner/) หรือ QGroundControl
- [Gazebo](https://gazebosim.org/) (optional - 3D simulation)

### Python Libraries
```bash
pip install -r requirements.txt
```

### API Keys (สำหรับบท AI)
- Anthropic API Key (Claude)
- OpenAI API Key (optional)

---

## 🗺️ Learning Path

```
[พื้นฐาน] → [Hardware] → [Simulation] → [Programming] → [AI Integration]
    ↓             ↓             ↓               ↓                ↓
  ทฤษฎี      ส่วนประกอบ    ทดสอบ virtual    DroneKit/ROS    Computer Vision
  การบิน      การประกอบ     ก่อนบินจริง      MAVLink          Autonomous Flight
```

---

## ⚠️ ความปลอดภัย

> **สำคัญมาก**: การบินโดรนจริงต้องปฏิบัติตามกฎหมายไทย
> - ต้องขึ้นทะเบียนโดรนกับ กสทช. (น้ำหนัก > 2 กก.)
> - ต้องมีใบอนุญาตนักบิน
> - ห้ามบินในเขตห้ามบิน (สนามบิน, ราชการ)
> - ความสูงไม่เกิน 90 เมตร

---

## 📌 Quick Start

```bash
# Clone หรือเข้าโฟลเดอร์
cd drone-tutorial

# ติดตั้ง dependencies
pip install -r requirements.txt

# เริ่มจากบทที่ 1
cd 01_basics
```

---

## 🔗 Resources เพิ่มเติม

- [ArduPilot Docs](https://ardupilot.org/ardupilot/)
- [PX4 Autopilot](https://px4.io/)
- [DroneKit Python](https://dronekit-python.readthedocs.io/)
- [ROS for Drones](https://www.ros.org/)
- [OpenCV](https://opencv.org/)
