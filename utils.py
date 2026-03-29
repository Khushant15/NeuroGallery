import cv2
import numpy as np
import os
import ctypes
import time

# --- COLORS (B-G-R) ---
NEON_GREEN = (57, 255, 20)
NEON_BLUE = (255, 255, 0)  # Cyan-ish / Aqua
NEON_CYAN = (255, 255, 10)
NEON_YELLOW = (20, 255, 255)
NEON_PINK = (147, 20, 255)
BG_MODAL = (30, 25, 20)  # Dark slate for glassmorphism
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

def get_screen_resolution():
    try:
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return 1280, 720  # Fallback

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def lerp(a, b, t):
    return a + (b - a) * t

def create_gradient(h, w):
    """Creates a dark cinematic vertical gradient."""
    bg = np.zeros((h, w, 3), dtype=np.uint8)
    for i in range(h):
        # Darker top (10,15,20) to slightly lighter bottom (30,40,50)
        c1 = int(10 + (i/h)*20)
        c2 = int(15 + (i/h)*25)
        c3 = int(20 + (i/h)*30)
        bg[i, :] = (c1, c2, c3)
    return bg

class EMA:
    """Exponential Moving Average for smoothing signals."""
    def __init__(self, alpha=0.5):
        self.alpha = alpha
        self.value = None

    def update(self, next_value):
        if self.value is None:
            self.value = next_value
        else:
            self.value = self.alpha * next_value + (1 - self.alpha) * self.value
        return self.value
