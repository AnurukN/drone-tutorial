"""
DroneKit Tutorial - บทที่ 3: บินไปยัง GPS Waypoint
====================================================

สิ่งที่จะเรียนรู้:
- การคำนวณตำแหน่ง GPS
- การสั่งให้โดรนบินไปจุดที่กำหนด
- การตรวจสอบว่าถึงจุดแล้ว
- การบิน Pattern (วงกลม, สี่เหลี่ยม)

วิธีรัน:
  python 03_goto_waypoint.py --connect tcp:127.0.0.1:5760
"""

import argparse
import math
import time
from dronekit import connect, VehicleMode, LocationGlobalRelative
from pymavlink import mavutil


# ============================================================
# Utility Functions
# ============================================================

def get_distance_metres(location1: LocationGlobalRelative,
                         location2: LocationGlobalRelative) -> float:
    """
    คำนวณระยะห่างระหว่าง 2 จุด GPS (เมตร)
    ใช้สูตร Haversine

    Returns:
        ระยะห่าง (เมตร)
    """
    lat1 = math.radians(location1.lat)
    lat2 = math.radians(location2.lat)
    lon1 = math.radians(location1.lon)
    lon2 = math.radians(location2.lon)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    # รัศมีโลก (เมตร)
    R = 6371000
    return R * c


def move_offset(lat: float, lon: float,
                d_north: float, d_east: float) -> tuple:
    """
    คำนวณตำแหน่งใหม่จากการเลื่อน (เมตร)

    Args:
        lat, lon: ตำแหน่งเริ่มต้น
        d_north: เลื่อนทิศเหนือ (เมตร, ลบ = ใต้)
        d_east: เลื่อนทิศตะวันออก (เมตร, ลบ = ตะวันตก)

    Returns:
        (lat_new, lon_new)
    """
    earth_radius = 6378137.0  # เมตร

    d_lat = d_north / earth_radius
    d_lon = d_east / (earth_radius * math.cos(math.pi * lat / 180))

    lat_new = lat + (d_lat * 180 / math.pi)
    lon_new = lon + (d_lon * 180 / math.pi)

    return lat_new, lon_new


# ============================================================
# Navigation Functions
# ============================================================

def arm_and_takeoff(vehicle, altitude: float):
    """ARM และ Takeoff"""
    print(f"🚀 Takeoff สู่ {altitude}m...")

    while not vehicle.is_armable:
        time.sleep(1)

    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True

    while not vehicle.armed:
        time.sleep(0.5)

    vehicle.simple_takeoff(altitude)

    while True:
        alt = vehicle.location.global_relative_frame.alt
        if alt >= altitude * 0.95:
            print(f"   ✅ Takeoff สำเร็จ ({alt:.1f}m)")
            break
        time.sleep(0.5)


def goto(vehicle, location: LocationGlobalRelative,
         speed: float = 5.0, acceptance_radius: float = 1.0):
    """
    บินไปยังตำแหน่ง GPS ที่กำหนด

    Args:
        location: ตำแหน่งเป้าหมาย
        speed: ความเร็ว (m/s)
        acceptance_radius: รัศมีถือว่าถึงจุด (เมตร)
    """
    # ตั้งความเร็ว
    vehicle.airspeed = speed

    # สั่งบินไปจุดเป้าหมาย
    vehicle.simple_goto(location)

    # รอจนกว่าจะถึง
    while True:
        current = vehicle.location.global_relative_frame
        distance = get_distance_metres(current, location)

        print(f"   ระยะเหลือ: {distance:.1f}m | "
              f"Speed: {vehicle.groundspeed:.1f}m/s | "
              f"Alt: {current.alt:.1f}m", end="\r")

        if distance < acceptance_radius:
            print(f"\n   ✅ ถึงจุดเป้าหมาย! (เหลือ {distance:.1f}m)")
            break

        # ตรวจสอบว่ายังอยู่ใน GUIDED mode
        if vehicle.mode.name != "GUIDED":
            print("\n   ⚠️  Mode เปลี่ยน! หยุด navigation")
            break

        time.sleep(0.5)


def fly_square(vehicle, side_length: float, altitude: float, speed: float = 3.0):
    """
    บินเป็นรูปสี่เหลี่ยม

    Args:
        side_length: ความยาวด้าน (เมตร)
        altitude: ความสูง (เมตร)
        speed: ความเร็ว (m/s)
    """
    print(f"\n🔲 บินสี่เหลี่ยม {side_length}m × {side_length}m")

    # จุดเริ่มต้น
    home = vehicle.location.global_relative_frame
    home_lat = home.lat
    home_lon = home.lon

    # 4 มุมของสี่เหลี่ยม
    corners = [
        (side_length, 0, "มุม NE"),
        (side_length, side_length, "มุม NW"),
        (0, side_length, "มุม SW"),
        (0, 0, "กลับจุดเริ่มต้น"),
    ]

    for d_north, d_east, name in corners:
        lat, lon = move_offset(home_lat, home_lon, d_north, d_east)
        target = LocationGlobalRelative(lat, lon, altitude)

        print(f"\n   ➡️  บินไป {name}...")
        goto(vehicle, target, speed=speed)
        time.sleep(1)

    print("   ✅ บินสี่เหลี่ยมครบแล้ว!")


def fly_circle(vehicle, radius: float, altitude: float,
               num_points: int = 16, speed: float = 3.0):
    """
    บินเป็นวงกลม

    Args:
        radius: รัศมี (เมตร)
        num_points: จำนวนจุดในวงกลม
        altitude: ความสูง (เมตร)
        speed: ความเร็ว (m/s)
    """
    print(f"\n⭕ บินวงกลม รัศมี {radius}m")

    home = vehicle.location.global_relative_frame
    home_lat = home.lat
    home_lon = home.lon

    for i in range(num_points + 1):
        angle = (2 * math.pi * i) / num_points
        d_north = radius * math.cos(angle)
        d_east = radius * math.sin(angle)

        lat, lon = move_offset(home_lat, home_lon, d_north, d_east)
        target = LocationGlobalRelative(lat, lon, altitude)

        print(f"   จุดที่ {i+1}/{num_points}: angle={math.degrees(angle):.0f}°", end="\r")
        goto(vehicle, target, speed=speed, acceptance_radius=2.0)

    print("\n   ✅ บินวงกลมครบแล้ว!")


def main():
    parser = argparse.ArgumentParser(description="DroneKit - Waypoint Navigation")
    parser.add_argument("--connect", default="tcp:127.0.0.1:5760")
    parser.add_argument("--altitude", type=float, default=15.0)
    parser.add_argument("--pattern", choices=["square", "circle", "waypoint"],
                        default="square", help="รูปแบบการบิน")
    parser.add_argument("--size", type=float, default=20.0,
                        help="ขนาด (เมตร)")
    args = parser.parse_args()

    vehicle = None
    try:
        print(f"🚁 เชื่อมต่อ: {args.connect}")
        vehicle = connect(args.connect, wait_ready=True)
        print("✅ เชื่อมต่อสำเร็จ\n")

        # Takeoff
        arm_and_takeoff(vehicle, args.altitude)
        time.sleep(2)

        # บินตาม Pattern ที่เลือก
        if args.pattern == "square":
            fly_square(vehicle, args.size, args.altitude)
        elif args.pattern == "circle":
            fly_circle(vehicle, args.size / 2, args.altitude)
        elif args.pattern == "waypoint":
            # ตัวอย่าง: บินไปจุดที่กำหนดเอง
            # เปลี่ยน lat/lon ตามตำแหน่งที่ต้องการ
            home = vehicle.location.global_relative_frame
            lat, lon = move_offset(home.lat, home.lon, 30, 0)
            target = LocationGlobalRelative(lat, lon, args.altitude)
            print(f"\n🎯 บินไป Waypoint: {lat:.6f}, {lon:.6f}")
            goto(vehicle, target, speed=5.0)

        # กลับบ้าน
        print("\n🏠 RTL...")
        vehicle.mode = VehicleMode("RTL")

        while vehicle.armed:
            alt = vehicle.location.global_relative_frame.alt
            print(f"   RTL: {alt:.1f}m", end="\r")
            time.sleep(0.5)

        print("\n✅ ลงจอดสำเร็จ!")

    except KeyboardInterrupt:
        print("\n\n⚠️  หยุดโดยผู้ใช้!")
        if vehicle and vehicle.armed:
            vehicle.mode = VehicleMode("RTL")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if vehicle:
            vehicle.close()


if __name__ == "__main__":
    main()
