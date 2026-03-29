import mediapipe as mp
import cv2
import numpy as np
from collections import deque

class GestureEngine:
    def __init__(self, max_hands=1, confidence=0.7):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=confidence,
            min_tracking_confidence=0.6
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.history = deque(maxlen=15)
        self.state = "NONE"
        self.pinch_val = 0.0
        self.fist_val = False
        self.thumbs_up = False
        
    def process_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        
        gestures = {
            "pinch": 0.0,
            "fist": False,
            "thumbs_up": False,
            "swipe": None,
            "center": None,
            "landmarks": None
        }
        
        if results.multi_hand_landmarks:
            # We focus on the first hand for now
            hlm = results.multi_hand_landmarks[0]
            gestures["landmarks"] = hlm
            
            lm = hlm.landmark
            h, w, _ = frame.shape
            
            def get_pt(idx): return np.array([lm[idx].x, lm[idx].y])
            
            thumb_tip = get_pt(4)
            index_tip = get_pt(8)
            middle_tip = get_pt(12)
            ring_tip = get_pt(16)
            pinky_tip = get_pt(20)
            
            # Center Calculation (Hand Palm center roughly at landmark 9)
            center = get_pt(9)
            gestures["center"] = center
            self.history.append(center)
            
            # 1. PINCH DETECTION
            dist = np.linalg.norm(thumb_tip - index_tip)
            gestures["pinch"] = dist
            
            # 2. FIST DETECTION
            # If finger tips are below their MCP joints (5, 9, 13, 17) in screen space?
            # MediaPipe y increases downwards.
            fingers_folded = [
                lm[8].y > lm[6].y,   # Index
                lm[12].y > lm[10].y, # Middle
                lm[16].y > lm[14].y, # Ring
                lm[20].y > lm[18].y  # Pinky
            ]
            gestures["fist"] = all(fingers_folded)
            
            # 3. THUMBS UP
            # Thumb tip is significantly above other landmarks and thumb is extended
            thumb_up = (lm[4].y < lm[3].y < lm[2].y) and all(fingers_folded)
            gestures["thumbs_up"] = thumb_up
            
            # 4. SWIPE DETECTION
            if len(self.history) >= 10:
                dx = self.history[-1][0] - self.history[0][0]
                if abs(dx) > 0.15:
                    gestures["swipe"] = "RIGHT" if dx > 0 else "LEFT"
                    self.history.clear() # Clear to prevent continuous swiping
                    
        return gestures

    def draw_landmarks(self, frame, hlm):
        if hlm:
            self.mp_draw.draw_landmarks(
                frame, hlm, self.mp_hands.HAND_CONNECTIONS,
                self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                self.mp_draw.DrawingSpec(color=(0, 0, 255), thickness=2)
            )
