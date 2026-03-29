import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from utils import NEON_GREEN, NEON_BLUE, NEON_PINK, BG_MODAL, WHITE

class UIEngine:
    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        # Load a standard font or fallback
        try:
            import platform
            font_path = "arial.ttf"
            if platform.system() == "Windows":
                font_path = "C:\\Windows\\Fonts\\arial.ttf"
            self.font = ImageFont.truetype(font_path, 20)
            self.font_lg = ImageFont.truetype(font_path, 32)
        except:
            self.font = ImageFont.load_default()
            self.font_lg = ImageFont.load_default()

    def draw_glass_panel(self, frame, x, y, w, h, title="HUD"):
        # 1. Blur the background (Glassmorphism)
        roi = frame[y:y+h, x:x+w]
        blur = cv2.GaussianBlur(roi, (25, 25), 0)
        frame[y:y+h, x:x+w] = cv2.addWeighted(roi, 0.3, blur, 0.7, 0)
        
        # 2. Border with Glow
        self.draw_glow_rect(frame, (x, y), (x+w, y+h), NEON_GREEN, thickness=1, glow=6)
        
        # 3. Title Bar
        cv2.rectangle(frame, (x, y-30), (x+w, y), NEON_GREEN, -1)
        self.draw_text_pil(frame, title, (x+10, y-28), color=(0,0,0), size="small")

    def draw_glow_rect(self, frame, pt1, pt2, color, thickness=2, glow=12):
        overlay = frame.copy()
        for i in range(glow, 0, -2):
            alpha = 0.05
            cv2.rectangle(overlay, pt1, pt2, color, thickness + i)
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        cv2.rectangle(frame, pt1, pt2, color, thickness)

    def draw_text_pil(self, frame, text, pos, color=WHITE, size="small"):
        # Convert CV2 (BGR) to PIL (RGB)
        rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        draw = ImageDraw.Draw(pil_img)
        
        font = self.font if size == "small" else self.font_lg
        draw.text(pos, text, font=font, fill=color)
        
        # Convert back
        new_frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        np.copyto(frame, new_frame)

    def draw_neon_glow(self, frame, x1, y1, x2, y2, color=NEON_GREEN):
        """Simulates a neon rectangle with a outer glow."""
        # Main thick blur for glow
        for i in range(1, 4):
            thick = 4 + i*4
            alpha = 1.0 / (i + 1)
            temp = frame.copy()
            cv2.rectangle(temp, (x1, y1), (x2, y2), color, thick)
            cv2.addWeighted(frame, 1-alpha, temp, alpha, 0, frame)
        # Central bright line
        cv2.rectangle(frame, (x1, y1), (x2, y2), WHITE, 1)

    def render_hud(self, frame, gestures, info):
        h, w = frame.shape[:2]
        anim_t = info.get('anim_t', 0)
        
        # Top Bar
        self.draw_glass_panel(frame, 20, 50, 420, 100, title="STARK SYSTEMS - GALLERY v2.0")
        
        # Bottom Navigation Info
        self.draw_glass_panel(frame, w-440, h-120, 420, 100, title="CONTROLS")
        self.draw_text_pil(frame, "PINCH: ZOOM | SWIPE: NAV | FIST: GRAB", (w-430, h-90))
        
        # Gesture Feedback Ring with Pulse
        if gestures["center"] is not None:
            cx, cy = int(gestures["center"][0] * w), int(gestures["center"][1] * h)
            
            p_dist = gestures["pinch"]
            color = NEON_GREEN if p_dist > 0.05 else NEON_PINK
            
            # Pulse Effect
            pulse = int(20 + 10 * np.sin(anim_t * 5))
            cv2.circle(frame, (cx, cy), pulse, color, 2)
            cv2.circle(frame, (cx, cy), 15, color, -1)
            
            if gestures["fist"]:
                self.draw_text_pil(frame, "[ GRABBED ]", (cx-50, cy-50), color=NEON_BLUE)
            elif gestures["thumbs_up"]:
                self.draw_text_pil(frame, "READY TO SCAN", (cx-60, cy-50), color=NEON_PINK)
        
        # Info readout
        cv2.putText(frame, "SYSTEM ACTIVE", (30, 85), cv2.FONT_HERSHEY_DUPLEX, 0.7, NEON_GREEN, 1)
        self.draw_text_pil(frame, f"FPS: {info.get('fps', 0)}", (30, 105))
        self.draw_text_pil(frame, f"ITEMS: {info.get('count', 0)}", (30, 130))
        
        return frame
