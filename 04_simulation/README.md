# บทที่ 4: Simulation (SITL)

## 🖥️ SITL คืออะไร?

**SITL (Software In The Loop)** = Simulate การบินบนคอมพิวเตอร์โดยไม่ต้องมีโดรนจริง

```
┌─────────────────────────────────────────────┐
│                  SITL Stack                  │
│                                              │
│  ┌───────────┐    ┌──────────────────────┐   │
│  │  Python   │───▶│  ArduPilot SITL      │   │
│  │  Script   │◀───│  (Flight Dynamics)   │   │
│  │(DroneKit) │    └──────────┬───────────┘   │
│  └───────────┘               │               │
│                   ┌──────────▼───────────┐   │
│  ┌───────────┐    │  MAVProxy / GCS      │   │
│  │ Mission   │───▶│  (Ground Control)    │   │
│  │ Planner   │    └──────────────────────┘   │
│  └───────────┘                               │
└─────────────────────────────────────────────┘
```

---

## 🚀 วิธีติดตั้ง SITL

### Option 1: dronekit-sitl (ง่ายที่สุด - Windows/Mac/Linux)

```bash
pip install dronekit-sitl

# เริ่ม SITL ที่กรุงเทพฯ
dronekit-sitl copter --home=13.7563,100.5018,20,0
# format: lat,lon,altitude,heading

# Port เริ่มต้น: tcp:127.0.0.1:5760
```

### Option 2: ArduPilot SITL (Linux/WSL - สมจริงกว่า)

```bash
# ใน Ubuntu/WSL
git clone https://github.com/ArduPilot/ardupilot.git
cd ardupilot
./waf configure --board sitl
./waf copter

# เริ่ม SITL
cd ArduCopter
sim_vehicle.py -v ArduCopter --console --map \
  -L "lat=13.7563,lng=100.5018,alt=20,heading=0"
```

### Option 3: Gazebo 3D Simulation (สมจริงที่สุด)

```bash
# ต้อง Linux + ROS
# ดูคู่มือใน https://ardupilot.org/dev/docs/using-gazebo-simulator.html
```

---

## 🎮 เชื่อมต่อกับ SITL

### Terminal 1: เริ่ม SITL
```bash
dronekit-sitl copter --home=13.7563,100.5018,20,0
```

Output:
```
Copter -6 on port 5760, sitting at 13.7563, 100.5018, alt=20, heading=0
```

### Terminal 2: เรียก Script
```bash
# เชื่อมต่อ DroneKit
python ../03_programming/dronekit/01_connect.py --connect tcp:127.0.0.1:5760

# หรือ
python ../03_programming/dronekit/02_takeoff_land.py \
  --connect tcp:127.0.0.1:5760 \
  --altitude 10
```

### Terminal 3: MAVProxy (optional - Ground Control)
```bash
pip install mavproxy
mavproxy.py --master=tcp:127.0.0.1:5760 --console --map
```

---

## 🗺️ Port ที่ใช้

| Port | ใช้กับ |
|------|--------|
| `tcp:5760` | DroneKit, MAVProxy (primary) |
| `udp:14550` | QGroundControl |
| `udp:14551` | Mission Planner |
| `tcp:5763` | Companion Computer |

---

## 🧪 ทดสอบทีละขั้น

### ขั้น 1: ทดสอบเชื่อมต่อ
```bash
dronekit-sitl copter --home=13.7563,100.5018,20,0 &
python ../03_programming/dronekit/01_connect.py
```

### ขั้น 2: ทดสอบ Takeoff
```bash
python ../03_programming/dronekit/02_takeoff_land.py --altitude 15
```

### ขั้น 3: ทดสอบ Waypoint
```bash
python ../03_programming/dronekit/03_goto_waypoint.py --pattern square --size 30
```

### ขั้น 4: ทดสอบ Mission
```bash
python ../03_programming/dronekit/04_mission.py --altitude 20 --area 50
```

---

## 💡 Tips

- SITL ใช้ Simulated time เร็วกว่าจริง (speedup)
- GPS accuracy ใน SITL = perfect (ไม่มี noise)
- ทดสอบ AI features ใน SITL ก่อนบินจริงเสมอ
- ใช้ `--speedup 2` เพื่อ simulate เร็วขึ้น 2x

```bash
dronekit-sitl copter --home=13.7563,100.5018,20,0 --speedup 2
```

---

➡️ **ต่อไป**: [บทที่ 5 - AI กับ Drone](../05_ai_with_drone/README.md)
