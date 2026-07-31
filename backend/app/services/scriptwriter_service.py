import json
import random

class ScriptwriterService:
    @staticmethod
    def generate_storyboard(plan_title: str, vibe: str, duration_sec: int) -> dict:
        """Mock AI LLM generation for storyboard"""
        print(f"[MOCK AI] Generating storyboard for {plan_title}")
        num_scenes = duration_sec // 5  # Roughly 5 secs per scene
        
        scenes = []
        for i in range(1, num_scenes + 1):
            scenes.append({
                "scene_order": i,
                "duration_sec": 5.0,
                "frame_type": random.choice(["close-up", "medium", "wide"]),
                "setting": "DAFA Showroom",
                "voiceover": f"Đây là phân cảnh số {i} giới thiệu {plan_title}",
                "on_screen_text": "Kính cường lực DAFA",
                "sound_effect": "Whoosh",
                "music_note": "Trending TikTok Audio",
                "editor_note": "Chỉnh màu sáng, tốc độ 1.2x",
                "safe_zone_warning": "Tránh góc dưới bên phải (vùng caption TikTok)"
            })
            
        return {
            "total_duration_seconds": duration_sec,
            "hook_description": "Cảnh quay cận cảnh sản phẩm cực nét 4K",
            "overall_notes": f"Vibe chủ đạo: {vibe}. Nhạc nền phải khớp beat.",
            "scenes": scenes
        }

    @staticmethod
    def export_pdf(script_id: int) -> str:
        """Mock PDF export"""
        return f"https://dafaglass.com/exports/script_{script_id}.pdf"
        
    @staticmethod
    def export_excel(script_id: int) -> str:
        """Mock Excel export"""
        return f"https://dafaglass.com/exports/script_{script_id}.xlsx"
