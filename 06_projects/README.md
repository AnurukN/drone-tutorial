# บทที่ 6: Projects จริง

## 🚀 Projects ในบทนี้

### 1. Surveillance Drone (โดรนเฝ้าระวัง)
**เหมาะกับ**: Security, งานก่อสร้าง, เกษตร

Features:
- บิน Patrol route อัตโนมัติ
- ตรวจจับคน/รถผิดปกติ
- ส่ง Alert ทาง Line OA / Telegram
- บันทึกวิดีโออัตโนมัติเมื่อเจอเหตุ

```bash
cd surveillance
python main.py --connect tcp:127.0.0.1:5760
```

---

### 2. Follow Me Drone (โดรนติดตามคน)
**เหมาะกับ**: Action camera, Sports, Vlogging

Features:
- ติดตามคนอัตโนมัติด้วย YOLO
- รักษาระยะห่าง
- หลีกสิ่งกีดขวาง
- Claude AI ช่วยตัดสินใจ

---

### 3. Delivery Drone (โดรนส่งของ)
**เหมาะกับ**: ส่งพัสดุ, ยา, อาหาร

Features:
- ติดตาม GPS route
- ตรวจสอบ Landing Zone ด้วย AI
- ปล่อยสินค้าอัตโนมัติ
- รายงานสถานะ

---

## 💡 แนวทางต่อยอด

| ไอเดีย | เทคโนโลยีหลัก |
|--------|--------------|
| โดรนฉีดยา (เกษตร) | GPS Mission + Pump Control |
| นับต้นไม้/พืชผล | Computer Vision + AI |
| สำรวจโครงสร้าง | 3D Mapping + SLAM |
| ส่งพัสดุ | Path Planning + Winch |
| ดับเพลิง | Thermal Camera + Water Release |
| Racing | PID Tuning + ELRS |
| Light Show | Formation Flight + LED |

---

## 📚 Resources

- [ArduPilot Mission Planner](https://ardupilot.org/planner/)
- [PX4 Autopilot Docs](https://docs.px4.io/)
- [ROS Drone Packages](http://wiki.ros.org/mavros)
- [OpenCV Tutorials](https://docs.opencv.org/)
- [Anthropic API Docs](https://docs.anthropic.com/)
- [กฎหมายโดรนไทย (กสทช.)](https://www.nbtc.go.th/)
