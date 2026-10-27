"""
MAVLink Tutorial - ระดับต่ำ (Low-level)
========================================

DroneKit ซ่อนรายละเอียด MAVLink ไว้ แต่บางครั้งต้องใช้ MAVLink โดยตรง
เช่น: ส่งคำสั่งพิเศษ, อ่านข้อมูล custom sensor

สิ่งที่จะเรียนรู้:
- MAVLink message คืออะไร
- การ parse telemetry data
- การส่ง command โดยตรง
- Heartbeat monitoring

วิธีรัน:
  python 01_basic_mavlink.py --connect udp:127.0.0.1:14550
"""

import argparse
import time
import threading
from pymavlink import mavutil


class MAVLinkDrone:
    """Wrapper สำหรับ MAVLink connection"""

    def __init__(self, connection_string: str):
        print(f"🔌 เชื่อมต่อ MAVLink: {connection_string}")
        self.master = mavutil.mavlink_connection(connection_string)

        # รอ Heartbeat
        print("   รอ Heartbeat...")
        self.master.wait_heartbeat()
        print(f"   ✅ Heartbeat! System: {self.master.target_system}, "
              f"Component: {self.master.target_component}")

        self.running = True
        self.telemetry = {}

    def request_data_streams(self):
        """ขอ Telemetry data streams"""

        # RAW Sensors (IMU, GPS)
        self.master.mav.request_data_stream_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_RAW_SENSORS,
            4,  # 4 Hz
            1   # เปิด
        )

        # Extended Status (Battery, etc.)
        self.master.mav.request_data_stream_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_EXTENDED_STATUS,
            2,  # 2 Hz
            1
        )

        # Position (GPS)
        self.master.mav.request_data_stream_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_POSITION,
            4,  # 4 Hz
            1
        )

        # Extra 1 (Attitude)
        self.master.mav.request_data_stream_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_EXTRA1,
            10,  # 10 Hz
            1
        )

        print("   ✅ ขอ Data Streams สำเร็จ")

    def receive_loop(self):
        """Loop รับ MAVLink messages"""
        while self.running:
            try:
                msg = self.master.recv_match(blocking=True, timeout=1)
                if msg is None:
                    continue

                msg_type = msg.get_type()

                # Parse ข้อมูลตาม message type
                if msg_type == "ATTITUDE":
                    self.telemetry["attitude"] = {
                        "roll": msg.roll,
                        "pitch": msg.pitch,
                        "yaw": msg.yaw,
                        "rollspeed": msg.rollspeed,
                        "pitchspeed": msg.pitchspeed,
                        "yawspeed": msg.yawspeed,
                    }

                elif msg_type == "GLOBAL_POSITION_INT":
                    self.telemetry["position"] = {
                        "lat": msg.lat / 1e7,
                        "lon": msg.lon / 1e7,
                        "alt": msg.alt / 1000,  # mm → m
                        "relative_alt": msg.relative_alt / 1000,
                        "vx": msg.vx / 100,  # cm/s → m/s
                        "vy": msg.vy / 100,
                        "vz": msg.vz / 100,
                        "hdg": msg.hdg / 100,  # cdeg → deg
                    }

                elif msg_type == "SYS_STATUS":
                    self.telemetry["battery"] = {
                        "voltage": msg.voltage_battery / 1000,  # mV → V
                        "current": msg.current_battery / 100,  # cA → A
                        "remaining": msg.battery_remaining,  # %
                    }

                elif msg_type == "GPS_RAW_INT":
                    self.telemetry["gps"] = {
                        "fix_type": msg.fix_type,
                        "satellites": msg.satellites_visible,
                        "lat": msg.lat / 1e7,
                        "lon": msg.lon / 1e7,
                        "alt": msg.alt / 1000,
                        "eph": msg.eph,  # horizontal dilution
                        "epv": msg.epv,  # vertical dilution
                    }

                elif msg_type == "HEARTBEAT":
                    mode_mapping = {
                        0: "STABILIZE",
                        2: "ALT_HOLD",
                        3: "AUTO",
                        4: "GUIDED",
                        5: "LOITER",
                        6: "RTL",
                        9: "LAND",
                    }
                    self.telemetry["heartbeat"] = {
                        "mode": mode_mapping.get(msg.custom_mode, f"MODE_{msg.custom_mode}"),
                        "armed": bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED),
                        "system_status": msg.system_status,
                    }

                elif msg_type == "VFR_HUD":
                    self.telemetry["hud"] = {
                        "airspeed": msg.airspeed,
                        "groundspeed": msg.groundspeed,
                        "heading": msg.heading,
                        "throttle": msg.throttle,
                        "alt": msg.alt,
                        "climb": msg.climb,
                    }

            except Exception as e:
                if self.running:
                    print(f"\n   MAVLink receive error: {e}")

    def send_command_long(self, command, param1=0, param2=0, param3=0,
                          param4=0, param5=0, param6=0, param7=0):
        """ส่ง MAV_CMD_LONG"""
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            command,
            0,  # confirmation
            param1, param2, param3, param4, param5, param6, param7
        )

    def arm(self):
        """ARM โดรน"""
        print("   ARM...")
        self.send_command_long(
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            param1=1  # 1=ARM, 0=DISARM
        )

    def disarm(self):
        """DISARM โดรน"""
        print("   DISARM...")
        self.send_command_long(
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            param1=0
        )

    def set_mode(self, mode_name: str):
        """ตั้ง Flight Mode"""
        mode_mapping = {
            "STABILIZE": 0,
            "ALT_HOLD": 2,
            "AUTO": 3,
            "GUIDED": 4,
            "LOITER": 5,
            "RTL": 6,
            "LAND": 9,
        }

        if mode_name not in mode_mapping:
            print(f"   ❌ ไม่รู้จัก Mode: {mode_name}")
            return

        mode_id = mode_mapping[mode_name]
        self.master.set_mode(mode_id)
        print(f"   Mode: {mode_name}")

    def takeoff(self, altitude: float):
        """Takeoff"""
        self.send_command_long(
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            param7=altitude
        )

    def print_telemetry(self):
        """แสดง Telemetry ปัจจุบัน"""
        import math

        print("\n" + "=" * 55)
        print("📊 MAVLink Telemetry")
        print("=" * 55)

        if "heartbeat" in self.telemetry:
            hb = self.telemetry["heartbeat"]
            print(f"Mode: {hb['mode']}")
            print(f"Armed: {'✅ YES' if hb['armed'] else '❌ NO'}")

        if "position" in self.telemetry:
            pos = self.telemetry["position"]
            print(f"\nGPS: {pos['lat']:.6f}, {pos['lon']:.6f}")
            print(f"Altitude: {pos['relative_alt']:.1f} m (relative)")
            print(f"Speed: N={pos['vx']:.1f} E={pos['vy']:.1f} D={pos['vz']:.1f} m/s")
            print(f"Heading: {pos['hdg']:.0f}°")

        if "attitude" in self.telemetry:
            att = self.telemetry["attitude"]
            print(f"\nRoll:  {math.degrees(att['roll']):.1f}°")
            print(f"Pitch: {math.degrees(att['pitch']):.1f}°")
            print(f"Yaw:   {math.degrees(att['yaw']):.1f}°")

        if "battery" in self.telemetry:
            bat = self.telemetry["battery"]
            print(f"\nBattery: {bat['voltage']:.2f}V | "
                  f"{bat['current']:.1f}A | "
                  f"{bat['remaining']}%")

        if "gps" in self.telemetry:
            gps = self.telemetry["gps"]
            fix_names = {0: "NO_GPS", 1: "NO_FIX", 2: "2D_FIX", 3: "3D_FIX", 4: "DGPS"}
            print(f"\nGPS Fix: {fix_names.get(gps['fix_type'], str(gps['fix_type']))}")
            print(f"Satellites: {gps['satellites']}")

        print("=" * 55)

    def close(self):
        """ปิดการเชื่อมต่อ"""
        self.running = False
        self.master.close()


def main():
    parser = argparse.ArgumentParser(description="MAVLink - Basic")
    parser.add_argument("--connect", default="udp:127.0.0.1:14550")
    parser.add_argument("--monitor", type=int, default=10,
                        help="เวลา monitor (วินาที)")
    args = parser.parse_args()

    drone = MAVLinkDrone(args.connect)

    try:
        # ขอ Data Streams
        drone.request_data_streams()

        # เริ่ม receive loop ใน background thread
        recv_thread = threading.Thread(target=drone.receive_loop, daemon=True)
        recv_thread.start()

        # รอให้ข้อมูลมา
        print("\n   รอข้อมูล...")
        time.sleep(3)

        # แสดง Telemetry
        drone.print_telemetry()

        # Monitor แบบ real-time
        print(f"\n📡 Real-time Monitor ({args.monitor} วินาที)...")
        start = time.time()

        while time.time() - start < args.monitor:
            if "hud" in drone.telemetry and "heartbeat" in drone.telemetry:
                hud = drone.telemetry["hud"]
                hb = drone.telemetry["heartbeat"]
                alt = drone.telemetry.get("position", {}).get("relative_alt", 0)

                print(f"   Mode: {hb['mode']:10s} | "
                      f"Alt: {alt:5.1f}m | "
                      f"Spd: {hud['groundspeed']:4.1f}m/s | "
                      f"Hdg: {hud['heading']:3d}° | "
                      f"Thr: {hud['throttle']:3d}%",
                      end="\r")

            time.sleep(0.2)

        print()

    except KeyboardInterrupt:
        print("\n⚠️  หยุดโดยผู้ใช้")
    finally:
        drone.close()
        print("✅ ปิดการเชื่อมต่อ")


if __name__ == "__main__":
    main()
