# บทที่ 2: Hardware & การสร้าง Drone

## 🛒 ชิ้นส่วนที่ต้องซื้อ (Quadcopter 250mm Racing)

### Frame
| ชิ้นส่วน | แนะนำ | ราคาประมาณ |
|---------|-------|------------|
| Frame 250mm | Geprc Mark4 / iFlight | 800-1,500 บาท |
| Frame 450mm (สำหรับถ่ายภาพ) | F450 Clone | 300-600 บาท |

### Flight Controller
| ชิ้นส่วน | แนะนำ | หมายเหตุ |
|---------|-------|---------|
| **Pixhawk 6C** | ราคา ~3,000 บาท | ดีที่สุดสำหรับ ArduPilot |
| **Pixhawk Mini** | ราคา ~2,000 บาท | เล็ก, เหมาะ Racing |
| **Matek F405** | ราคา ~1,500 บาท | ราคาดี |
| **Raspberry Pi + Navio2** | ราคา ~4,000 บาท | โปรแกรมได้เต็มที่ |

### ESC + Motor
```
Motor KV Rating (ใบพัด 5"):
- Racing:  2300-2600 KV
- ถ่ายภาพ: 700-1200 KV
- ขนาดใหญ่: 300-700 KV

สูตร: RPM = KV × Voltage
เช่น: 2300KV × 14.8V (4S) = 34,040 RPM
```

| ชุด | แนะนำ | ใบพัด |
|----|-------|-------|
| **2306 2450KV** + ESC 35A | Racing/Freestyle | 5" |
| **2212 920KV** + ESC 30A | Aerial Photo F450 | 9-10" |
| **4114 320KV** + ESC 40A | Heavy lift | 15" |

### Battery (LiPo)
```
ตัวอย่างชื่อ: 4S 1500mAh 100C
│              │    │      └── Discharge rate
│              │    └───────── ความจุ (ยิ่งมาก บินนาน)
│              └────────────── จำนวน Cell (1S=3.7V)
└───────────────────────────── Series cells
```

| ขนาด | แรงดัน | เหมาะกับ |
|------|--------|---------|
| 3S (11.1V) | 12.6V full | Mini drone |
| 4S (14.8V) | 16.8V full | Racing, Mid-size |
| 6S (22.2V) | 25.2V full | Long range, Heavy |

---

## 🔌 การเดินสาย (Wiring Diagram)

```
Battery (+) ──────────────────────────────────────┐
                                                   │
             ┌─────────────────────────────────────┤
             │                                     │
         ┌───▼───┐   PWM/DSHOT   ┌─────────────┐  │
         │  PDB   │──────────────▶│  ESC 1 (M1) │──┤── Motor 1
         │(Power │               ├─────────────┤  │
         │Dist.  │               │  ESC 2 (M2) │──┤── Motor 2
         │Board) │               ├─────────────┤  │
         └───┬───┘               │  ESC 3 (M3) │──┤── Motor 3
             │                   ├─────────────┤  │
             │ 5V BEC             │  ESC 4 (M4) │──┘── Motor 4
             │                   └─────────────┘
         ┌───▼───────┐
         │  Flight   │◀─── GPS Module
         │Controller │◀─── RC Receiver (SBUS)
         │(Pixhawk)  │◀─── Telemetry Radio
         └───────────┘──▶ Buzzer, LED
```

---

## 🔧 ขั้นตอนการประกอบ

### Step 1: Frame
```
1. ประกอบ Frame ตามคู่มือ
2. ตรวจสอบ arm แต่ละข้างแข็งแรง
3. ติดตั้ง Motor Mount
```

### Step 2: Motor
```
1. ติดมอเตอร์ตาม Frame
2. เดินสายมอเตอร์ผ่าน arm
3. ตรวจทิศหมุน:
   - CW: M1 (ขวาหน้า), M3 (ซ้ายหลัง)
   - CCW: M2 (ซ้ายหน้า), M4 (ขวาหลัง)
```

### Step 3: ESC
```
1. ติด ESC ที่ arm หรือ PDB
2. ต่อสาย Motor 3 เส้นเข้า ESC
3. ต่อสาย ESC เข้า PDB
4. ต่อ Signal wire เข้า FC (MOTOR OUTPUT)
```

### Step 4: Flight Controller
```
1. ติด FC ตรงกลาง Frame (ใช้ anti-vibration mount)
2. ต่อ Receiver → FC (SBUS/PPM port)
3. ต่อ GPS → FC (GPS port)
4. ต่อ Telemetry → FC (TELEM port)
5. ต่อ Battery monitor → FC
```

### Step 5: ตั้งค่า Firmware
```
1. ติด Mission Planner หรือ QGC
2. เชื่อมต่อ FC ผ่าน USB
3. ติดตั้ง Firmware (ArduCopter)
4. ทำ Initial Setup:
   - Accelerometer Calibration
   - Compass Calibration
   - Radio Calibration
   - ESC Calibration
5. ตั้ง PID (ค่าเริ่มต้นก็ใช้ได้)
```

---

## ⚠️ Pre-flight Checklist

```markdown
ก่อนบินทุกครั้ง:
□ แบตเตอรี่ชาร์จเต็ม (> 80%)
□ Propeller ขันแน่น (CW/CCW ถูก)
□ GPS มี Fix (> 6 ดาว)
□ Arm/Disarm ทดสอบได้
□ Mode switch ทำงาน
□ Failsafe ตั้งค่าแล้ว (RTL/Land)
□ พื้นที่โล่ง ไม่มีสิ่งกีดขวาง
□ แจ้งคนรอบข้าง
```

---

## 💡 Companion Computer (Raspberry Pi)

สำหรับการใช้ AI และ Programming ขั้นสูง:

```
Pixhawk ──UART──▶ Raspberry Pi 4
                       │
                 ┌─────▼─────┐
                 │  Camera   │  (AI Processing)
                 └───────────┘
                       │
                 ┌─────▼─────┐
                 │  Python   │  (DroneKit / MAVLink)
                 └───────────┘
```

### เชื่อมต่อ RPi กับ Pixhawk
```bash
# /boot/config.txt - เปิด UART
enable_uart=1

# ใน RPi terminal
sudo apt install python3-pip
pip3 install dronekit
pip3 install pymavlink
```

---

➡️ **ต่อไป**: [บทที่ 3 - การ Program Drone](../03_programming/README.md)
