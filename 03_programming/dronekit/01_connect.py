"""
DroneKit Tutorial - บทที่ 1: การเชื่อมต่อ Drone
================================================

วิธีรัน:
  # เชื่อมต่อ SITL (Simulator)
  python 01_connect.py --connect tcp:127.0.0.1:5760

  # เชื่อมต่อโดรนจริงผ่าน Serial
  python 01_connect.py --connect /dev/ttyUSB0,57600

  # เชื่อมต่อผ่าน UDP
  python 01_connect.py --connect udp:127.0.0.1:14550
"""

import argparse
import time
from dronekit import connect, VehicleMode


def connect_drone(connection_string: str):
    """เชื่อมต่อกับ Drone และแสดงข้อมูล"""

    print(f"🚁 กำลังเชื่อมต่อกับ Drone: {connection_string}")

    # เชื่อมต่อ - wait_ready=True รอจนกว่า drone พร้อม
    vehicle = connect(connection_string, wait_ready=True, timeout=60)

    print("✅ เชื่อมต่อสำเร็จ!\n")

    return vehicle


def print_vehicle_info(vehicle):
    """แสดงข้อมูล Vehicle"""

    print("=" * 50)
    print("📊 ข้อมูล Drone")
    print("=" * 50)

    # ข้อมูลพื้นฐาน
    print(f"Autopilot:     {vehicle.version}")
    print(f"Flight Mode:   {vehicle.mode.name}")
    print(f"Armed:         {vehicle.armed}")
    print(f"System Status: {vehicle.system_status.state}")

    # ตำแหน่ง GPS
    print("\n📍 ตำแหน่ง GPS:")
    if vehicle.location.global_frame.lat:
        loc = vehicle.location.global_frame
        print(f"  Latitude:  {loc.lat:.6f}")
        print(f"  Longitude: {loc.lon:.6f}")
        print(f"  Altitude:  {loc.alt:.2f} m (MSL)")
    else:
        print("  ยังไม่มี GPS Fix")

    # ความสูงจากพื้น
    print(f"\n🏔️  ความสูงจากพื้น: {vehicle.location.global_relative_frame.alt:.2f} m")

    # ทิศทาง
    print(f"\n🧭 Heading: {vehicle.heading}°")

    # แรงดันไฟ
    print(f"\n🔋 แรงดันไฟ: {vehicle.battery.voltage:.2f} V")
    print(f"   กระแสไฟ: {vehicle.battery.current:.2f} A")
    print(f"   ระดับ:   {vehicle.battery.level}%")

    # Attitude (การเอียง)
    att = vehicle.attitude
    print(f"\n📐 Attitude:")
    print(f"  Roll:  {att.roll:.3f} rad ({att.roll * 57.3:.1f}°)")
    print(f"  Pitch: {att.pitch:.3f} rad ({att.pitch * 57.3:.1f}°)")
    print(f"  Yaw:   {att.yaw:.3f} rad ({att.yaw * 57.3:.1f}°)")

    # Velocity
    vel = vehicle.velocity
    print(f"\n💨 ความเร็ว:")
    print(f"  Vx: {vel[0]:.2f} m/s  Vy: {vel[1]:.2f} m/s  Vz: {vel[2]:.2f} m/s")

    # Airspeed / Groundspeed
    print(f"\n🌀 Airspeed:   {vehicle.airspeed:.2f} m/s")
    print(f"   Groundspeed: {vehicle.groundspeed:.2f} m/s")

    # GPS Info
    gps = vehicle.gps_0
    print(f"\n🛰️  GPS:")
    print(f"  Fix Type: {gps.fix_type} (3=3D Fix)")
    print(f"  Satellites: {gps.satellites_visible}")

    print("=" * 50)


def monitor_live(vehicle, duration: int = 10):
    """ดูข้อมูลแบบ Real-time"""

    print(f"\n📡 Real-time Monitoring ({duration} วินาที)...")
    print("-" * 40)

    start = time.time()
    while time.time() - start < duration:
        loc = vehicle.location.global_relative_frame
        att = vehicle.attitude

        print(
            f"Alt: {loc.alt:5.1f}m | "
            f"Roll: {att.roll*57.3:6.1f}° | "
            f"Pitch: {att.pitch*57.3:6.1f}° | "
            f"Bat: {vehicle.battery.voltage:.1f}V",
            end="\r"
        )
        time.sleep(0.5)

    print("\n")


def main():
    parser = argparse.ArgumentParser(description="DroneKit - เชื่อมต่อ Drone")
    parser.add_argument(
        "--connect",
        default="tcp:127.0.0.1:5760",
        help="Connection string (default: tcp:127.0.0.1:5760)"
    )
    args = parser.parse_args()

    vehicle = None
    try:
        # เชื่อมต่อ
        vehicle = connect_drone(args.connect)

        # แสดงข้อมูล
        print_vehicle_info(vehicle)

        # Monitor แบบ real-time
        monitor_live(vehicle, duration=10)

    except KeyboardInterrupt:
        print("\n⚠️  หยุดโดยผู้ใช้")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if vehicle:
            print("🔌 ปิดการเชื่อมต่อ...")
            vehicle.close()
            print("✅ ปิดแล้ว")


if __name__ == "__main__":
    main()
