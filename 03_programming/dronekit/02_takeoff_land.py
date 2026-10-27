"""
DroneKit Tutorial - บทที่ 2: ขึ้น-ลงจอด (Takeoff & Land)
==========================================================

สิ่งที่จะเรียนรู้:
- วิธี ARM Drone
- การ Takeoff ไปความสูงที่กำหนด
- การ Land และ RTL (Return to Launch)
- การตรวจสอบความปลอดภัย

วิธีรัน:
  python 02_takeoff_land.py --connect tcp:127.0.0.1:5760 --altitude 10
"""

import argparse
import time
from dronekit import connect, VehicleMode, LocationGlobalRelative


def arm_and_takeoff(vehicle, target_altitude: float):
    """
    ARM Drone และ Takeoff ไปความสูงที่กำหนด

    Args:
        vehicle: DroneKit vehicle object
        target_altitude: ความสูงเป้าหมาย (เมตร)
    """

    print("🔧 กำลังเตรียม Takeoff...")

    # รอให้ GPS พร้อม
    print("   รอ GPS Fix...")
    while not vehicle.home_location:
        cmds = vehicle.commands
        cmds.download()
        cmds.wait_ready()
        if not vehicle.home_location:
            print("   ยังไม่มี Home Location, รอ...")
            time.sleep(1)

    print(f"   Home: {vehicle.home_location}")

    # ตรวจสอบว่า Drone Armable
    print("   ตรวจสอบ Pre-arm checks...")
    while not vehicle.is_armable:
        print(f"   รอ Armable... (GPS: {vehicle.gps_0.fix_type}, "
              f"Status: {vehicle.system_status.state})")
        time.sleep(1)

    print("   ✅ พร้อม ARM")

    # ตั้ง Mode เป็น GUIDED
    print("   ตั้ง Mode: GUIDED")
    vehicle.mode = VehicleMode("GUIDED")
    while vehicle.mode.name != "GUIDED":
        time.sleep(0.5)

    # ARM
    print("   กำลัง ARM...")
    vehicle.armed = True
    while not vehicle.armed:
        print("   รอ ARM...")
        time.sleep(0.5)

    print("   ✅ ARM สำเร็จ! มอเตอร์หมุน")
    time.sleep(2)

    # TAKEOFF
    print(f"\n🚀 Takeoff สู่ความสูง {target_altitude} เมตร...")
    vehicle.simple_takeoff(target_altitude)

    # รอให้ถึงความสูงเป้าหมาย
    while True:
        current_alt = vehicle.location.global_relative_frame.alt
        print(f"   ความสูงปัจจุบัน: {current_alt:.1f} m / {target_altitude} m", end="\r")

        # ถึง 95% ของเป้าหมายถือว่าสำเร็จ
        if current_alt >= target_altitude * 0.95:
            print(f"\n   ✅ ถึงความสูงเป้าหมาย: {current_alt:.1f} m")
            break

        time.sleep(0.5)


def hover(vehicle, duration: int = 5):
    """Hover อยู่กับที่"""
    print(f"\n⏸️  Hover {duration} วินาที...")

    start = time.time()
    while time.time() - start < duration:
        remaining = duration - (time.time() - start)
        alt = vehicle.location.global_relative_frame.alt
        print(f"   Hovering... {remaining:.0f}s | Alt: {alt:.1f}m | "
              f"Mode: {vehicle.mode.name}", end="\r")
        time.sleep(0.5)

    print()


def land(vehicle):
    """ลงจอด"""
    print("\n🛬 กำลังลงจอด...")
    vehicle.mode = VehicleMode("LAND")

    while vehicle.armed:
        alt = vehicle.location.global_relative_frame.alt
        print(f"   ลงจอด... ความสูง: {alt:.1f} m", end="\r")
        time.sleep(0.5)

    print("\n   ✅ ลงจอดสำเร็จ! DISARM แล้ว")


def return_to_launch(vehicle):
    """กลับจุดเริ่มต้น (RTL)"""
    print("\n🏠 Return to Launch (RTL)...")
    vehicle.mode = VehicleMode("RTL")

    # รอจนกว่าจะถึงบ้านและลงจอด
    while vehicle.armed:
        loc = vehicle.location.global_relative_frame
        print(f"   RTL... Alt: {loc.alt:.1f}m | Mode: {vehicle.mode.name}", end="\r")
        time.sleep(0.5)

    print("\n   ✅ RTL สำเร็จ!")


def main():
    parser = argparse.ArgumentParser(description="DroneKit - Takeoff & Land")
    parser.add_argument("--connect", default="tcp:127.0.0.1:5760")
    parser.add_argument("--altitude", type=float, default=10.0,
                        help="ความสูง Takeoff (เมตร)")
    parser.add_argument("--hover", type=int, default=5,
                        help="เวลา Hover (วินาที)")
    parser.add_argument("--rtl", action="store_true",
                        help="ใช้ RTL แทน LAND")
    args = parser.parse_args()

    vehicle = None
    try:
        print(f"🚁 เชื่อมต่อ: {args.connect}")
        vehicle = connect(args.connect, wait_ready=True)
        print("✅ เชื่อมต่อสำเร็จ\n")

        # แสดงข้อมูลเบื้องต้น
        print(f"Mode: {vehicle.mode.name} | Battery: {vehicle.battery.voltage:.1f}V")

        # Takeoff
        arm_and_takeoff(vehicle, args.altitude)

        # Hover
        hover(vehicle, args.hover)

        # ลงจอด
        if args.rtl:
            return_to_launch(vehicle)
        else:
            land(vehicle)

    except KeyboardInterrupt:
        print("\n\n⚠️  หยุดโดยผู้ใช้!")
        if vehicle and vehicle.armed:
            print("   ⚠️  EMERGENCY LAND!")
            vehicle.mode = VehicleMode("LAND")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if vehicle and vehicle.armed:
            print("   ⚠️  EMERGENCY LAND!")
            vehicle.mode = VehicleMode("LAND")
    finally:
        if vehicle:
            vehicle.close()
            print("🔌 ปิดการเชื่อมต่อ")


if __name__ == "__main__":
    main()
