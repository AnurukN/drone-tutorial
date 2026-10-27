"""
DroneKit Tutorial - บทที่ 4: Mission Planning (Auto Mode)
=========================================================

สิ่งที่จะเรียนรู้:
- การสร้าง Mission (Waypoint list)
- อัปโหลด Mission ไปยัง Drone
- เริ่ม/หยุด Auto Mission
- Download Mission จาก Drone

วิธีรัน:
  python 04_mission.py --connect tcp:127.0.0.1:5760
"""

import argparse
import math
import time
from dronekit import connect, VehicleMode, LocationGlobalRelative, Command
from pymavlink import mavutil


def move_offset(lat, lon, d_north, d_east):
    """คำนวณ GPS offset (เมตร)"""
    earth_radius = 6378137.0
    d_lat = d_north / earth_radius
    d_lon = d_east / (earth_radius * math.cos(math.pi * lat / 180))
    return lat + (d_lat * 180 / math.pi), lon + (d_lon * 180 / math.pi)


def create_survey_mission(vehicle, altitude: float = 20.0, area_size: float = 50.0):
    """
    สร้าง Survey Mission (ถ่ายภาพแบบ Grid)

    รูปแบบ:
    ┌──────────────────────┐
    │→→→→→→→→→→→→→→→→→→→→│
    │←←←←←←←←←←←←←←←←←←│
    │→→→→→→→→→→→→→→→→→→→→│
    └──────────────────────┘
    """
    print("📋 สร้าง Survey Mission...")

    home = vehicle.location.global_relative_frame
    home_lat = home.lat
    home_lon = home.lon

    cmds = vehicle.commands
    cmds.clear()

    # Waypoint 0: Takeoff
    cmds.add(Command(
        0, 0, 0,
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0, 0,
        0, 0, 0, 0,  # param1-4
        home_lat, home_lon, altitude  # x, y, z
    ))

    # Survey Grid Pattern
    rows = 4
    spacing = area_size / rows

    for row in range(rows):
        d_north = row * spacing

        # สลับทิศทางแต่ละแถว (lawnmower pattern)
        if row % 2 == 0:
            # บินจาก West → East
            d_east_start = 0
            d_east_end = area_size
        else:
            # บินจาก East → West
            d_east_start = area_size
            d_east_end = 0

        # จุดเริ่มต้นของแถว
        lat1, lon1 = move_offset(home_lat, home_lon, d_north, d_east_start)
        cmds.add(Command(
            0, 0, 0,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
            0, 0,
            0, 2, 0, 0,  # hold, acceptance_radius, pass_radius, yaw
            lat1, lon1, altitude
        ))

        # จุดสิ้นสุดของแถว + ถ่ายภาพ
        lat2, lon2 = move_offset(home_lat, home_lon, d_north, d_east_end)
        cmds.add(Command(
            0, 0, 0,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
            mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
            0, 0,
            0, 2, 0, 0,
            lat2, lon2, altitude
        ))

        # คำสั่งถ่ายภาพ (Camera Trigger)
        cmds.add(Command(
            0, 0, 0,
            mavutil.mavlink.MAV_FRAME_MISSION,
            mavutil.mavlink.MAV_CMD_DO_SET_CAM_TRIGG_DIST,
            0, 0,
            10, 0, 0, 0,  # ถ่ายทุก 10 เมตร
            0, 0, 0
        ))

    # RTL กลับบ้าน
    cmds.add(Command(
        0, 0, 0,
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
        0, 0,
        0, 0, 0, 0,
        0, 0, 0
    ))

    # อัปโหลด Mission
    print(f"   อัปโหลด {len(cmds)} commands...")
    cmds.upload()

    print(f"   ✅ Mission อัปโหลดสำเร็จ ({len(cmds)} waypoints)")
    return len(cmds)


def run_mission(vehicle):
    """เริ่ม Auto Mission"""

    print("\n▶️  เริ่ม Auto Mission...")

    # ARM
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True

    while not vehicle.armed:
        time.sleep(0.5)

    print("   ARM สำเร็จ")

    # เปลี่ยนเป็น AUTO mode
    vehicle.mode = VehicleMode("AUTO")

    while vehicle.mode.name != "AUTO":
        time.sleep(0.5)

    print("   Mode: AUTO")


def monitor_mission(vehicle):
    """ติดตาม Mission Progress"""

    print("\n📊 ติดตาม Mission...")
    print("-" * 60)

    last_wp = -1

    while True:
        mode = vehicle.mode.name
        current_wp = vehicle.commands.next
        total_wp = vehicle.commands.count
        loc = vehicle.location.global_relative_frame
        speed = vehicle.groundspeed

        # แสดงเมื่อเปลี่ยน Waypoint
        if current_wp != last_wp:
            print(f"\n   🎯 Waypoint {current_wp}/{total_wp}")
            last_wp = current_wp

        print(f"   WP: {current_wp}/{total_wp} | "
              f"Alt: {loc.alt:.1f}m | "
              f"Speed: {speed:.1f}m/s | "
              f"Mode: {mode}   ", end="\r")

        # Mission สิ้นสุดเมื่อลงจอดแล้ว
        if not vehicle.armed and mode in ["RTL", "LAND", "LOITER"]:
            print("\n\n   ✅ Mission สำเร็จ!")
            break

        # Mode เปลี่ยน (อาจ interrupt)
        if mode not in ["AUTO", "RTL", "LAND"]:
            print(f"\n\n   ⚠️  Mission หยุด (Mode: {mode})")
            break

        time.sleep(1)


def download_mission(vehicle):
    """Download Mission จาก Drone"""

    print("\n📥 Download Mission จาก Drone...")
    cmds = vehicle.commands
    cmds.download()
    cmds.wait_ready()

    print(f"   พบ {cmds.count} waypoints:")
    print("-" * 50)

    cmd_names = {
        22: "TAKEOFF",
        16: "WAYPOINT",
        20: "RETURN_TO_LAUNCH",
        21: "LAND",
        206: "CAM_TRIGG_DIST",
    }

    for i, cmd in enumerate(cmds):
        cmd_name = cmd_names.get(cmd.command, f"CMD_{cmd.command}")
        print(f"   {i:3d}: {cmd_name:20s} | "
              f"lat={cmd.x:.6f} lon={cmd.y:.6f} alt={cmd.z:.1f}m")

    return cmds


def main():
    parser = argparse.ArgumentParser(description="DroneKit - Auto Mission")
    parser.add_argument("--connect", default="tcp:127.0.0.1:5760")
    parser.add_argument("--altitude", type=float, default=20.0)
    parser.add_argument("--area", type=float, default=50.0,
                        help="ขนาดพื้นที่ Survey (เมตร)")
    parser.add_argument("--download-only", action="store_true",
                        help="Download mission เท่านั้น ไม่บิน")
    args = parser.parse_args()

    vehicle = None
    try:
        print(f"🚁 เชื่อมต่อ: {args.connect}")
        vehicle = connect(args.connect, wait_ready=True)
        print("✅ เชื่อมต่อสำเร็จ\n")

        if args.download_only:
            download_mission(vehicle)
            return

        # สร้างและอัปโหลด Mission
        create_survey_mission(vehicle, args.altitude, args.area)

        # รอผู้ใช้ confirm
        input("\n⚠️  กด Enter เพื่อเริ่ม Mission (หรือ Ctrl+C เพื่อยกเลิก)...")

        # เริ่ม Mission
        run_mission(vehicle)

        # ติดตาม
        monitor_mission(vehicle)

    except KeyboardInterrupt:
        print("\n\n⚠️  ยกเลิก Mission!")
        if vehicle and vehicle.armed:
            print("   RTL...")
            vehicle.mode = VehicleMode("RTL")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if vehicle:
            vehicle.close()
            print("\n🔌 ปิดการเชื่อมต่อ")


if __name__ == "__main__":
    main()
