import cv2
import numpy as np
import time
import os
from utils import get_screen_resolution, ensure_dir, NEON_GREEN, NEON_BLUE, create_gradient
from gesture import GestureEngine
from gallery import GalleryManager
from ui import UIEngine

class StarkGalleryApp:
    def __init__(self):
        # 1. INIT SCREEN
        self.sh = 720
        self.vw, self.vh = 1280, 720
        self.bg_gradient = create_gradient(self.vh, self.vw)
        
        # 2. INIT ENGINES
        self.gestures = GestureEngine()
        self.gallery = GalleryManager()
        self.ui = UIEngine(self.vw, self.vh)
        
        # 3. APP STATE
        self.running = True
        self.prev_time = time.time()
        self.fps = 0
        self.screenshot_timer = 0
        self.is_fullscreen = False
        
        # Directory for shots
        ensure_dir("screenshots")
        
    def handle_gestures(self, g_data):
        # --- ROTATION (FIST GRAB / SWIPE) ---
        if g_data["swipe"] == "RIGHT":
            self.gallery.target_angle -= (2 * np.pi / max(1, self.gallery.n))
        elif g_data["swipe"] == "LEFT":
            self.gallery.target_angle += (2 * np.pi / max(1, self.gallery.n))
            
        elif g_data["fist"] and g_data["center"] is not None:
            # Grabbing logic
            # Use movement from history
            if len(self.gestures.history) > 2:
                dx = self.gestures.history[-1][0] - self.gestures.history[-2][0]
                self.gallery.target_angle += dx * 5.0
                
        # --- ZOOM (PINCH) ---
        target_zoom = 1.0
        p_dist = g_data["pinch"]
        if p_dist > 0.01:
            target_zoom = 0.5 + p_dist * 8.0
        self.gallery.zoom += (target_zoom - self.gallery.zoom) * 0.08
            
        # --- SCREENSHOT (THUMBS UP) ---
        if g_data["thumbs_up"]:
            self.screenshot_timer += 1
            if self.screenshot_timer == 30: # ~1 second at 30 fps
                self.take_screenshot = True
        else:
            self.screenshot_timer = 0

    def run(self):
        cap = cv2.VideoCapture(0)
        # Force 1280x720 if possible
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        take_screenshot = False
        
        while self.running:
            start_time = time.time()
            ret, frame = cap.read()
            if not ret:
                break
                
            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (self.vw, self.vh))
            
            # --- PROCESS ---
            g_data = self.gestures.process_frame(frame)
            self.handle_gestures(g_data)
            self.gallery.update()
            
            # --- RENDER ---
            # Create a gradient slate for the HUD
            combined = self.bg_gradient.copy()
            overlay = frame.copy()
            
            # 1. 3D Gallery
            combined = self.gallery.render(combined)
            
            # 2. Combine with Webcam
            final = cv2.addWeighted(overlay, 0.15, combined, 0.85, 0)
            
            # 3. HUD
            anim_t = time.time()
            info = {"fps": int(self.fps), "count": self.gallery.n, "anim_t": anim_t}
            final = self.ui.render_hud(final, g_data, info)
            
            # 4. Landmarks (Optional, for debugging)
            # self.gestures.draw_landmarks(final, g_data["landmarks"])
            
            # 5. Screenshot Logic
            if take_screenshot or (g_data["thumbs_up"] and self.screenshot_timer >= 30):
                ts = time.strftime("%Y%m%d-%H%M%S")
                cv2.imwrite(f"screenshots/shot_{ts}.jpg", final)
                # Visual Flash
                final = cv2.addWeighted(final, 0.1, np.full_like(final, 255), 0.9, 0)
                take_screenshot = False
                self.screenshot_timer = 0
            
            # --- DISPLAY & FPS CAP ---
            cv2.imshow("STARK - Interactive 3D Gallery", final)
            
            # Handle keys
            key = cv2.waitKey(1) & 0xFF
            if key == 27: # ESC
                self.running = False
            elif key == ord('f'):
                self.is_fullscreen = not self.is_fullscreen
                prop = cv2.WINDOW_FULLSCREEN if self.is_fullscreen else cv2.WINDOW_NORMAL
                cv2.setWindowProperty("STARK - Interactive 3D Gallery", cv2.WND_PROP_FULLSCREEN, prop)
            elif key == 83 or key == ord('d'): # Right Arrow or 'd'
                self.gallery.target_angle -= (2 * np.pi / max(1, self.gallery.n))
            elif key == 81 or key == ord('a'): # Left Arrow or 'a'
                self.gallery.target_angle += (2 * np.pi / max(1, self.gallery.n))
            
            # FPS Calculation
            end_time = time.time()
            elapsed = end_time - start_time
            # Cap at 30 FPS (~33ms per frame)
            wait = 0.033 - elapsed
            if wait > 0:
                time.sleep(wait)
                
            total_elapsed = time.time() - start_time
            self.fps = 1.0 / total_elapsed if total_elapsed > 0 else 0
            
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    app = StarkGalleryApp()
    app.run()
