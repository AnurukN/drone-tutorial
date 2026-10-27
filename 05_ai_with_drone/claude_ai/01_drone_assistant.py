"""
AI Drone Tutorial - Claude AI Drone Assistant
=============================================

ใช้ Claude AI เป็น "สมอง" ของโดรน:
- รับคำสั่งภาษาธรรมชาติ → แปลงเป็น Drone Commands
- วิเคราะห์สถานการณ์และตัดสินใจ
- รายงานสถานะแบบ Conversational

ตัวอย่าง:
  "บินไปทางเหนือ 50 เมตร แล้วถ่ายภาพ"
  "กลับบ้าน แบตใกล้หมดแล้ว"
  "หลีกสิ่งกีดขวางทางซ้าย"

วิธีรัน:
  python 01_drone_assistant.py --connect tcp:127.0.0.1:5760
"""

import argparse
import json
import os
import time
from typing import Any

import anthropic
from dotenv import load_dotenv

load_dotenv()

try:
    from dronekit import connect, VehicleMode, LocationGlobalRelative
    import math
    DRONEKIT_AVAILABLE = True
except ImportError:
    DRONEKIT_AVAILABLE = False


# ============================================================
# Drone Tools (ฟังก์ชันที่ Claude เรียกใช้ได้)
# ============================================================

class DroneController:
    """Controller สำหรับ Claude AI ใช้สั่งโดรน"""

    def __init__(self, vehicle=None, dry_run: bool = True):
        self.vehicle = vehicle
        self.dry_run = dry_run
        self.home_location = None
        self.mission_log = []

    def log(self, action: str, result: str):
        """บันทึก action"""
        entry = {"time": time.strftime("%H:%M:%S"), "action": action, "result": result}
        self.mission_log.append(entry)
        print(f"  [{entry['time']}] {action} → {result}")

    def get_status(self) -> dict:
        """ดูสถานะโดรนปัจจุบัน"""
        if self.dry_run or not self.vehicle:
            return {
                "mode": "GUIDED",
                "armed": True,
                "altitude": 15.0,
                "latitude": 13.7563,
                "longitude": 100.5018,
                "battery_voltage": 12.4,
                "battery_percent": 78,
                "gps_satellites": 8,
                "airspeed": 3.2,
                "heading": 45,
            }

        loc = self.vehicle.location.global_relative_frame
        bat = self.vehicle.battery

        return {
            "mode": self.vehicle.mode.name,
            "armed": self.vehicle.armed,
            "altitude": round(loc.alt, 1),
            "latitude": round(loc.lat, 6),
            "longitude": round(loc.lon, 6),
            "battery_voltage": round(bat.voltage, 2),
            "battery_percent": bat.level,
            "gps_satellites": self.vehicle.gps_0.satellites_visible,
            "airspeed": round(self.vehicle.airspeed, 1),
            "heading": self.vehicle.heading,
        }

    def takeoff(self, altitude: float) -> str:
        """ขึ้นบินสู่ความสูงที่กำหนด"""
        if altitude < 2 or altitude > 120:
            return f"ความสูงไม่ถูกต้อง: {altitude}m (ต้อง 2-120 เมตร)"

        if self.dry_run or not self.vehicle:
            self.log("TAKEOFF", f"Takeoff สู่ {altitude}m [DRY RUN]")
            return f"Takeoff สู่ {altitude} เมตร (Simulated)"

        try:
            self.vehicle.mode = VehicleMode("GUIDED")
            self.vehicle.armed = True
            time.sleep(1)
            self.vehicle.simple_takeoff(altitude)

            # รอ
            while self.vehicle.location.global_relative_frame.alt < altitude * 0.9:
                time.sleep(0.5)

            self.log("TAKEOFF", f"ถึง {altitude}m")
            return f"Takeoff สำเร็จ อยู่ที่ {altitude} เมตร"
        except Exception as e:
            return f"Takeoff ล้มเหลว: {e}"

    def land(self) -> str:
        """ลงจอด"""
        if self.dry_run or not self.vehicle:
            self.log("LAND", "ลงจอด [DRY RUN]")
            return "เริ่มลงจอด (Simulated)"

        try:
            self.vehicle.mode = VehicleMode("LAND")
            while self.vehicle.armed:
                time.sleep(0.5)
            self.log("LAND", "ลงจอดสำเร็จ")
            return "ลงจอดสำเร็จ"
        except Exception as e:
            return f"ลงจอดล้มเหลว: {e}"

    def return_to_home(self) -> str:
        """กลับจุดเริ่มต้น (RTL)"""
        if self.dry_run or not self.vehicle:
            self.log("RTL", "กลับบ้าน [DRY RUN]")
            return "กำลังกลับจุดเริ่มต้น (RTL) [Simulated]"

        self.vehicle.mode = VehicleMode("RTL")
        return "กำลังกลับจุดเริ่มต้น (RTL)"

    def fly_to_gps(self, latitude: float, longitude: float,
                    altitude: float, speed: float = 5.0) -> str:
        """บินไปยังตำแหน่ง GPS"""
        if self.dry_run or not self.vehicle:
            self.log("GOTO", f"→ ({latitude:.4f}, {longitude:.4f}) {altitude}m [DRY RUN]")
            return f"บินไปยัง ({latitude:.6f}, {longitude:.6f}) ที่ {altitude}m"

        target = LocationGlobalRelative(latitude, longitude, altitude)
        self.vehicle.simple_goto(target, groundspeed=speed)
        return f"กำลังบินไปยัง ({latitude:.6f}, {longitude:.6f}) ที่ {altitude}m"

    def fly_direction(self, direction: str, distance: float,
                      altitude: float = None) -> str:
        """บินตามทิศทาง (น/ส/ออก/ตก) ระยะทางที่กำหนด"""
        dir_map = {
            "เหนือ": (1, 0), "north": (1, 0),
            "ใต้": (-1, 0), "south": (-1, 0),
            "ออก": (0, 1), "east": (0, 1),
            "ตะวันออก": (0, 1),
            "ตก": (0, -1), "west": (0, -1),
            "ตะวันตก": (0, -1),
        }

        direction_lower = direction.lower()
        d_coeff = None
        for key, val in dir_map.items():
            if key in direction_lower:
                d_coeff = val
                break

        if not d_coeff:
            return f"ไม่รู้จักทิศทาง: {direction}"

        if self.dry_run or not self.vehicle:
            self.log("FLY_DIR", f"→ {direction} {distance}m [DRY RUN]")
            return f"บินไป{direction} {distance} เมตร (Simulated)"

        # คำนวณ GPS ใหม่
        loc = self.vehicle.location.global_relative_frame
        earth_r = 6378137.0
        d_north, d_east = d_coeff[0] * distance, d_coeff[1] * distance

        new_lat = loc.lat + (d_north / earth_r) * (180 / math.pi)
        new_lon = loc.lon + (d_east / (earth_r * math.cos(math.pi * loc.lat / 180))) * (180 / math.pi)
        new_alt = altitude if altitude else loc.alt

        target = LocationGlobalRelative(new_lat, new_lon, new_alt)
        self.vehicle.simple_goto(target)

        return f"กำลังบินไป{direction} {distance} เมตร"

    def set_speed(self, speed: float) -> str:
        """ตั้งความเร็ว"""
        if speed < 0 or speed > 15:
            return f"ความเร็วไม่ถูกต้อง: {speed} (0-15 m/s)"

        if self.dry_run or not self.vehicle:
            return f"ตั้งความเร็ว {speed} m/s (Simulated)"

        self.vehicle.airspeed = speed
        return f"ตั้งความเร็ว {speed} m/s"

    def change_altitude(self, altitude: float) -> str:
        """เปลี่ยนความสูง"""
        if altitude < 2 or altitude > 120:
            return f"ความสูงไม่ถูกต้อง: {altitude}m"

        if self.dry_run or not self.vehicle:
            return f"เปลี่ยนความสูงเป็น {altitude}m (Simulated)"

        loc = self.vehicle.location.global_relative_frame
        target = LocationGlobalRelative(loc.lat, loc.lon, altitude)
        self.vehicle.simple_goto(target)
        return f"กำลังเปลี่ยนความสูงเป็น {altitude} เมตร"

    def trigger_camera(self) -> str:
        """ถ่ายภาพ"""
        self.log("CAMERA", "ถ่ายภาพ")
        return "ถ่ายภาพแล้ว ✓"

    def get_mission_log(self) -> list:
        """ดู Mission Log"""
        return self.mission_log


# ============================================================
# Claude AI Drone Assistant
# ============================================================

# Tool definitions ที่ Claude ใช้ได้
DRONE_TOOLS = [
    {
        "name": "get_status",
        "description": "ดูสถานะโดรนปัจจุบัน รวมถึงตำแหน่ง, ความสูง, แบตเตอรี่, โหมดการบิน",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "takeoff",
        "description": "สั่งให้โดรนขึ้นบินสู่ความสูงที่กำหนด (เมตร)",
        "input_schema": {
            "type": "object",
            "properties": {
                "altitude": {
                    "type": "number",
                    "description": "ความสูงเป้าหมาย (เมตร) ช่วง 2-120"
                }
            },
            "required": ["altitude"]
        }
    },
    {
        "name": "land",
        "description": "สั่งให้โดรนลงจอด ณ ตำแหน่งปัจจุบัน",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "return_to_home",
        "description": "สั่งให้โดรนกลับจุดเริ่มต้น (RTL) อัตโนมัติ",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "fly_direction",
        "description": "บินไปในทิศทางที่กำหนดเป็นระยะทาง (เมตร)",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "description": "ทิศทาง: เหนือ, ใต้, ออก/ตะวันออก, ตก/ตะวันตก"
                },
                "distance": {
                    "type": "number",
                    "description": "ระยะทาง (เมตร)"
                },
                "altitude": {
                    "type": "number",
                    "description": "ความสูง (เมตร) - ถ้าไม่ระบุจะใช้ความสูงปัจจุบัน"
                }
            },
            "required": ["direction", "distance"]
        }
    },
    {
        "name": "fly_to_gps",
        "description": "บินไปยังพิกัด GPS ที่กำหนด",
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude"},
                "longitude": {"type": "number", "description": "Longitude"},
                "altitude": {"type": "number", "description": "ความสูง (เมตร)"},
                "speed": {"type": "number", "description": "ความเร็ว m/s (default 5)"}
            },
            "required": ["latitude", "longitude", "altitude"]
        }
    },
    {
        "name": "change_altitude",
        "description": "เปลี่ยนความสูงการบิน",
        "input_schema": {
            "type": "object",
            "properties": {
                "altitude": {"type": "number", "description": "ความสูงใหม่ (เมตร)"}
            },
            "required": ["altitude"]
        }
    },
    {
        "name": "set_speed",
        "description": "ตั้งความเร็วการบิน",
        "input_schema": {
            "type": "object",
            "properties": {
                "speed": {"type": "number", "description": "ความเร็ว (m/s) 0-15"}
            },
            "required": ["speed"]
        }
    },
    {
        "name": "trigger_camera",
        "description": "ถ่ายภาพด้วยกล้องโดรน",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    }
]


class DroneAIAssistant:
    """
    AI Assistant สำหรับโดรน
    รับคำสั่งภาษาไทย/อังกฤษ → แปลงเป็น drone commands
    """

    SYSTEM_PROMPT = """คุณคือ AI Assistant ควบคุมโดรน (Drone AI Pilot)

ความสามารถ:
- รับคำสั่งภาษาไทยหรืออังกฤษ
- แปลงคำสั่งเป็นการกระทำโดรนที่ปลอดภัย
- รายงานสถานะและผลลัพธ์อย่างชัดเจน
- ตรวจสอบความปลอดภัยก่อนทุกคำสั่ง

กฎความปลอดภัย:
1. ตรวจสอบแบตเตอรี่ก่อนทุก mission (< 20% → กลับบ้านทันที)
2. ความสูงสูงสุด 120 เมตร
3. ตรวจสอบ GPS Fix ก่อนบิน
4. รายงานทุก action ที่ทำ
5. ถ้าไม่แน่ใจ ให้ถามก่อน ห้ามเดาเอง

รูปแบบการตอบ:
- สั้น กระชับ ชัดเจน
- บอกสิ่งที่กำลังทำ
- บอกผลลัพธ์
- แจ้งเตือนถ้ามีความเสี่ยง"""

    def __init__(self, controller: DroneController,
                 model: str = "claude-sonnet-4-6"):
        self.controller = controller
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = model
        self.conversation_history = []

    def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute drone tool ที่ Claude เรียก"""
        tool_map = {
            "get_status": lambda: json.dumps(self.controller.get_status(), ensure_ascii=False),
            "takeoff": lambda: self.controller.takeoff(tool_input.get("altitude", 10)),
            "land": self.controller.land,
            "return_to_home": self.controller.return_to_home,
            "fly_direction": lambda: self.controller.fly_direction(
                tool_input.get("direction", ""),
                tool_input.get("distance", 0),
                tool_input.get("altitude")
            ),
            "fly_to_gps": lambda: self.controller.fly_to_gps(
                tool_input.get("latitude", 0),
                tool_input.get("longitude", 0),
                tool_input.get("altitude", 10),
                tool_input.get("speed", 5.0)
            ),
            "change_altitude": lambda: self.controller.change_altitude(tool_input.get("altitude", 10)),
            "set_speed": lambda: self.controller.set_speed(tool_input.get("speed", 5)),
            "trigger_camera": self.controller.trigger_camera,
        }

        handler = tool_map.get(tool_name)
        if handler:
            return str(handler())
        return f"ไม่รู้จัก tool: {tool_name}"

    def chat(self, user_message: str) -> str:
        """ส่ง message และรับ response จาก Claude"""

        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Agentic loop
        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.SYSTEM_PROMPT,
                tools=DRONE_TOOLS,
                messages=self.conversation_history
            )

            # ถ้าหยุดเพราะมี tool_use
            if response.stop_reason == "tool_use":
                # เพิ่ม assistant response
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })

                # Execute tools
                tool_results = []
                for content_block in response.content:
                    if content_block.type == "tool_use":
                        tool_name = content_block.name
                        tool_input = content_block.input
                        tool_id = content_block.id

                        print(f"  🔧 เรียก: {tool_name}({tool_input})")
                        result = self.execute_tool(tool_name, tool_input)
                        print(f"     → {result}")

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result
                        })

                # เพิ่ม tool results
                self.conversation_history.append({
                    "role": "user",
                    "content": tool_results
                })

                # วน loop ต่อ

            else:
                # End_turn - ได้ final response
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text += block.text

                self.conversation_history.append({
                    "role": "assistant",
                    "content": final_text
                })

                return final_text


# ============================================================
# Interactive CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Claude AI Drone Assistant")
    parser.add_argument("--connect", default=None,
                        help="Drone connection string")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--model", default="claude-sonnet-4-6")
    args = parser.parse_args()

    # ตรวจสอบ API Key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ไม่มี ANTHROPIC_API_KEY")
        print("   ตั้งค่า: export ANTHROPIC_API_KEY=your-key")
        print("   หรือสร้างไฟล์ .env แล้วใส่: ANTHROPIC_API_KEY=your-key")
        return

    # เชื่อมต่อ Drone
    vehicle = None
    dry_run = args.dry_run or args.connect is None

    if not dry_run and DRONEKIT_AVAILABLE:
        print(f"🚁 เชื่อมต่อ: {args.connect}")
        vehicle = connect(args.connect, wait_ready=True)
        print("✅ เชื่อมต่อสำเร็จ")

    # สร้าง Controller และ Assistant
    controller = DroneController(vehicle=vehicle, dry_run=dry_run)
    assistant = DroneAIAssistant(controller=controller, model=args.model)

    print("\n" + "=" * 55)
    print("🤖 Claude AI Drone Assistant")
    print("=" * 55)
    print(f"Model: {args.model}")
    print(f"Mode: {'DRY RUN (Simulated)' if dry_run else 'LIVE DRONE'}")
    print("\nคำสั่งตัวอย่าง:")
    print("  'ดูสถานะโดรน'")
    print("  'ขึ้นบิน 20 เมตร'")
    print("  'บินไปทางเหนือ 30 เมตร'")
    print("  'ถ่ายภาพแล้วกลับบ้าน'")
    print("  'แบตเหลือเท่าไหร่ ปลอดภัยไหม'")
    print("\nพิมพ์ 'quit' หรือ 'ออก' เพื่อหยุด")
    print("=" * 55)

    try:
        while True:
            print()
            user_input = input("คุณ: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "ออก", "หยุด"]:
                print("👋 ลาก่อน!")
                break

            if user_input.lower() == "log":
                print("\n📋 Mission Log:")
                for entry in controller.get_mission_log():
                    print(f"  [{entry['time']}] {entry['action']}: {entry['result']}")
                continue

            print(f"\n🤖 Assistant: ", end="", flush=True)
            response = assistant.chat(user_input)
            print(response)

    except KeyboardInterrupt:
        print("\n\n⚠️  หยุดโดยผู้ใช้")
    finally:
        if vehicle:
            vehicle.close()
        print("✅ เสร็จสิ้น")


if __name__ == "__main__":
    main()
