"""
AI Drone Tutorial - Claude Vision Analysis
==========================================

ใช้ Claude Vision วิเคราะห์ภาพจากกล้องโดรน:
- ตรวจสอบความปลอดภัยของพื้นที่ลงจอด
- นับจำนวนคน/รถ/สิ่งของ
- วิเคราะห์ความเสียหาย (เช่น หลังจากภัยพิบัติ)
- ระบุตำแหน่งที่น่าสนใจ

วิธีรัน:
  python 02_vision_analysis.py --image path/to/image.jpg
  python 02_vision_analysis.py --camera 0  (webcam)
"""

import argparse
import base64
import os
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("ℹ️  opencv ไม่ได้ติดตั้ง (pip install opencv-python)")


# ============================================================
# Vision Analysis Tasks
# ============================================================

ANALYSIS_PROMPTS = {
    "landing_zone": """วิเคราะห์ภาพนี้จากกล้องโดรน เพื่อประเมินความปลอดภัยในการลงจอด:

1. **พื้นที่ลงจอด**: มีพื้นที่ว่างเพียงพอไหม? (ต้องการอย่างน้อย 3×3 เมตร)
2. **สิ่งกีดขวาง**: มีต้นไม้, เสาไฟ, สายไฟ, คน หรือสิ่งกีดขวางอื่นๆ ไหม?
3. **พื้นผิว**: พื้นราบหรือลาดเอียง? แข็งหรืออ่อน?
4. **คะแนนความปลอดภัย**: 1-10 (10 = ปลอดภัยที่สุด)
5. **คำแนะนำ**: ควรลงจอดไหม? ถ้าไม่ เหตุผลคืออะไร?

ตอบเป็นภาษาไทย อย่างกระชับ""",

    "crowd_count": """วิเคราะห์ภาพนี้จากกล้องโดรน:

1. **จำนวนคน**: นับจำนวนคนในภาพ (ประมาณการถ้ามากเกินไป)
2. **ความหนาแน่น**: กระจายตัวหรือรวมกลุ่ม?
3. **พื้นที่**: เป็นพื้นที่ประเภทใด?
4. **ข้อสังเกต**: มีสิ่งผิดปกติหรือน่าสนใจไหม?

ตอบเป็นภาษาไทย อย่างกระชับ""",

    "damage_assessment": """วิเคราะห์ภาพนี้จากโดรนสำรวจความเสียหาย:

1. **ประเภทความเสียหาย**: อาคาร, ถนน, ต้นไม้ล้ม, น้ำท่วม ฯลฯ
2. **ระดับความเสียหาย**: น้อย / ปานกลาง / รุนแรง / วิกฤต
3. **พื้นที่ที่ได้รับผลกระทบ**: ประมาณการ
4. **ความเร่งด่วน**: ต้องการความช่วยเหลือเร่งด่วนไหม?
5. **คำแนะนำ**: ขั้นตอนต่อไปที่ควรทำ

ตอบเป็นภาษาไทย""",

    "general": """วิเคราะห์ภาพนี้จากกล้องโดรนอย่างละเอียด:

1. **ภาพรวม**: เห็นอะไรบ้างในภาพนี้?
2. **วัตถุสำคัญ**: ระบุสิ่งของ, คน, ยานพาหนะ ที่เห็น
3. **สภาพแวดล้อม**: เมือง/ชนบท, กลางวัน/กลางคืน, สภาพอากาศ
4. **ข้อสังเกต**: สิ่งที่น่าสนใจหรือผิดปกติ
5. **ประโยชน์สำหรับโดรน**: ข้อมูลนี้ใช้ประโยชน์อะไรได้บ้าง?

ตอบเป็นภาษาไทย""",
}


class DroneVisionAnalyzer:
    """ระบบวิเคราะห์ภาพด้วย Claude Vision"""

    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = model
        self.analysis_count = 0

    def encode_image(self, image_path: str) -> tuple[str, str]:
        """แปลงรูปภาพเป็น base64"""
        path = Path(image_path)

        # media type
        ext_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = ext_map.get(path.suffix.lower(), "image/jpeg")

        with open(path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")

        return data, media_type

    def encode_cv2_frame(self, frame) -> tuple[str, str]:
        """แปลง OpenCV frame เป็น base64"""
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        data = base64.standard_b64encode(buffer).decode("utf-8")
        return data, "image/jpeg"

    def analyze(self, image_data: str, media_type: str,
                 task: str = "general",
                 custom_prompt: str = None) -> str:
        """
        วิเคราะห์ภาพ

        Args:
            image_data: base64 encoded image
            media_type: MIME type
            task: ประเภทการวิเคราะห์
            custom_prompt: prompt กำหนดเอง

        Returns:
            ผลการวิเคราะห์ (string)
        """
        prompt = custom_prompt or ANALYSIS_PROMPTS.get(task, ANALYSIS_PROMPTS["general"])

        self.analysis_count += 1
        print(f"   🔍 วิเคราะห์ภาพ #{self.analysis_count} (task: {task})...")

        start = time.time()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )

        elapsed = time.time() - start
        result = response.content[0].text
        print(f"   ⏱️  ใช้เวลา: {elapsed:.1f} วินาที")

        return result

    def analyze_file(self, image_path: str, task: str = "general") -> str:
        """วิเคราะห์จากไฟล์รูปภาพ"""
        print(f"📸 โหลดรูปภาพ: {image_path}")
        image_data, media_type = self.encode_image(image_path)
        return self.analyze(image_data, media_type, task)

    def analyze_frame(self, frame, task: str = "general",
                      custom_prompt: str = None) -> str:
        """วิเคราะห์จาก OpenCV frame"""
        image_data, media_type = self.encode_cv2_frame(frame)
        return self.analyze(image_data, media_type, task, custom_prompt)


# ============================================================
# Real-time Analysis Pipeline
# ============================================================

def analyze_camera_realtime(analyzer: DroneVisionAnalyzer,
                             source: int = 0,
                             interval: float = 5.0,
                             task: str = "general"):
    """
    วิเคราะห์ภาพจาก Camera แบบ Real-time

    Args:
        interval: วิเคราะห์ทุก N วินาที
    """
    if not CV2_AVAILABLE:
        print("❌ ต้องการ opencv: pip install opencv-python")
        return

    print(f"📹 เปิดกล้อง {source}")
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"❌ ไม่สามารถเปิดกล้อง {source}")
        return

    print(f"🔄 วิเคราะห์ทุก {interval} วินาที (กด Q หยุด, กด A วิเคราะห์ทันที)")

    last_analysis = 0
    last_result = "รอการวิเคราะห์..."

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # แสดง frame
            display = frame.copy()
            h, w = display.shape[:2]

            # Timer bar
            elapsed = time.time() - last_analysis
            progress = min(elapsed / interval, 1.0)
            bar_w = int(w * progress)
            cv2.rectangle(display, (0, h-8), (bar_w, h), (0, 255, 100), -1)
            cv2.rectangle(display, (0, h-8), (w, h), (100, 100, 100), 1)

            # แสดงผลการวิเคราะห์
            lines = last_result.split("\n")[:8]
            cv2.rectangle(display, (0, 0), (w, min(len(lines) * 22 + 10, h)),
                         (0, 0, 0), -1)

            for i, line in enumerate(lines):
                if line.strip():
                    cv2.putText(display, line[:70], (5, 20 + i * 22),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # Info
            cv2.putText(display, f"Task: {task} | ถัดไป: {max(0, interval-elapsed):.0f}s",
                       (5, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

            cv2.imshow(f"Drone Vision Analysis - {task}", display)

            # Auto analysis
            if time.time() - last_analysis >= interval:
                print(f"\n{'='*50}")
                print(f"🔍 Auto Analysis - {time.strftime('%H:%M:%S')}")
                last_result = analyzer.analyze_frame(frame, task=task)
                print(f"\n📊 ผลการวิเคราะห์:\n{last_result}")
                last_analysis = time.time()

            key = cv2.waitKey(30) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("a"):
                # วิเคราะห์ทันที
                print(f"\n{'='*50}")
                print(f"🔍 Manual Analysis - {time.strftime('%H:%M:%S')}")
                last_result = analyzer.analyze_frame(frame, task=task)
                print(f"\n📊 ผลการวิเคราะห์:\n{last_result}")
                last_analysis = time.time()
            elif key == ord("s"):
                # บันทึกภาพ
                filename = f"capture_{int(time.time())}.jpg"
                cv2.imwrite(filename, frame)
                print(f"\n💾 บันทึก: {filename}")

    except KeyboardInterrupt:
        print("\n⚠️  หยุดโดยผู้ใช้")
    finally:
        cap.release()
        cv2.destroyAllWindows()


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Claude Vision - Drone Image Analysis")
    parser.add_argument("--image", help="path ของรูปภาพ")
    parser.add_argument("--camera", type=int, help="Camera index (0=webcam)")
    parser.add_argument("--task",
                        choices=["general", "landing_zone", "crowd_count", "damage_assessment"],
                        default="general")
    parser.add_argument("--interval", type=float, default=10.0,
                        help="วิเคราะห์ทุก N วินาที (สำหรับ camera)")
    parser.add_argument("--model", default="claude-sonnet-4-6")
    args = parser.parse_args()

    # ตรวจสอบ API Key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ไม่มี ANTHROPIC_API_KEY")
        print("   สร้างไฟล์ .env แล้วใส่: ANTHROPIC_API_KEY=sk-ant-xxx")
        return

    analyzer = DroneVisionAnalyzer(model=args.model)

    print(f"\n🤖 Claude Vision Drone Analyzer")
    print(f"   Model: {args.model}")
    print(f"   Task: {args.task}")

    if args.image:
        # วิเคราะห์จากไฟล์
        result = analyzer.analyze_file(args.image, task=args.task)
        print(f"\n{'='*55}")
        print("📊 ผลการวิเคราะห์:")
        print("="*55)
        print(result)

    elif args.camera is not None:
        # Real-time จากกล้อง
        analyze_camera_realtime(
            analyzer,
            source=args.camera,
            interval=args.interval,
            task=args.task
        )

    else:
        # Interactive mode
        print("\n💡 ไม่ได้ระบุ --image หรือ --camera")
        print("   ตัวอย่าง:")
        print("   python 02_vision_analysis.py --image photo.jpg --task landing_zone")
        print("   python 02_vision_analysis.py --camera 0 --task crowd_count")


if __name__ == "__main__":
    main()
