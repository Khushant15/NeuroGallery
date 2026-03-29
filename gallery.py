import cv2
import numpy as np
import os
import glob
import math
from utils import lerp, NEON_GREEN, NEON_BLUE

class GalleryManager:
    def __init__(self, path="gallery", thumb_size=(256, 170)):
        self.path = path
        self.thumb_size = thumb_size
        self.images = self.load_images()
        self.current_angle = 0.0
        self.target_angle = 0.0
        self.zoom = 1.0
        self.selected_idx = 0
        self.n = len(self.images)
        self.thumbnails = []
        self._prepare_thumbnails()

    def load_images(self):
        images = []
        extensions = ["*.jpg", "*.jpeg", "*.png"]
        files = []
        for ext in extensions:
            files.extend(glob.glob(os.path.join(self.path, ext)))
        
        for f in sorted(files):
            img = cv2.imread(f)
            if img is not None:
                images.append(img)
        return images

    def _prepare_thumbnails(self):
        for img in self.images:
            thumb = cv2.resize(img, self.thumb_size, interpolation=cv2.INTER_AREA)
            # Create a blurred version for background depth
            blurred = cv2.GaussianBlur(thumb, (15, 15), 5)
            self.thumbnails.append({
                "raw": thumb,
                "blur": blurred
            })

    def update(self):
        # Cinematic Smoothing (0.08 factor)
        self.current_angle += (self.target_angle - self.current_angle) * 0.08
        
        # Update selected index based on closest to front (theta ~ PI/2)
        # Assuming front is theta = PI/2 (90 deg)
        best_diff = 1000
        for i in range(self.n):
            theta = (2 * np.pi * i / self.n) + self.current_angle
            wrapped_theta = (theta + np.pi) % (2 * np.pi) - np.pi # Range [-PI, PI]
            diff = abs(wrapped_theta - (np.pi/2))
            if diff < best_diff:
                best_diff = diff
                self.selected_idx = i

    def render(self, frame, center_pos=None):
        h, w, _ = frame.shape
        cx, cy = w // 2, h // 2
        radius = int(250 * self.zoom)
        depth_scale = 180 * self.zoom
        
        # Sort images by Z (Depth)
        render_order = []
        for i in range(self.n):
            theta = (2 * np.pi * i / self.n) + self.current_angle
            # Standard carousel: x = R*cos, z = R*sin (y is vertical)
            # We want depth to be Z
            x_pos = cx + radius * np.cos(theta)
            y_pos = cy + radius * np.sin(theta) * 0.3 # Flat ellipse
            z_pos = depth_scale * np.sin(theta)
            
            # Distance from camera (let camera be at front)
            # Higher Z means closer to viewer
            scale = 1.0 + (z_pos / depth_scale) * 0.4
            render_order.append((z_pos, i, x_pos, y_pos, scale))
            
        render_order.sort(key=lambda x: x[0]) # Further first
        
        for z, idx, x, y, scale in render_order:
            is_selected = (idx == self.selected_idx)
            thumb_data = self.thumbnails[idx]
            
            # Use blurred or raw based on depth
            # z ranges from -depth_scale to +depth_scale
            # Normalize to 0 (far) to 1 (near)
            norm_z = (z + depth_scale) / (2 * depth_scale)
            
            img = thumb_data["raw"] if norm_z > 0.6 else thumb_data["blur"]
            
            # Final Resizing
            nw, nh = int(self.thumb_size[0] * scale), int(self.thumb_size[1] * scale)
            res_img = cv2.resize(img, (nw, nh))
            
            # Darken if far
            alpha = 0.3 + 0.7 * norm_z
            if not is_selected:
                res_img = (res_img * alpha).astype(np.uint8)
            else:
                # Add highlighting for selected
                cv2.rectangle(res_img, (0,0), (nw, nh), NEON_BLUE, 4)
                
            # Place on frame (simple addWeighted or direct)
            ix, iy = int(x - nw // 2), int(y - nh // 2)
            
            # ROI boundaries
            x1, y1 = max(0, ix), max(0, iy)
            x2, y2 = min(w, ix + nw), min(h, iy + nh)
            
            if x1 < x2 and y1 < y2:
                # Local sub-image area
                sx, sy = x1 - ix, y1 - iy
                ew, eh = x2 - x1, y2 - y1
                
                roi = frame[y1:y2, x1:x2]
                img_roi = res_img[sy:sy+eh, sx:sx+ew]
                
                if is_selected:
                    frame[y1:y2, x1:x2] = cv2.addWeighted(roi, 0.1, img_roi, 0.9, 0)
                    # Center Focus Highlight
                    cv2.circle(frame, (int(x), int(y)), int(120 * scale), (0, 255, 255), 2)
                else:
                    # Shadow Effect (Offet)
                    sy_off, sx_off = 12, 12
                    s_x1, s_y1 = max(0, ix+sx_off), max(0, iy+sy_off)
                    s_x2, s_y2 = min(w, ix+nw+sx_off), min(h, iy+nh+sy_off)
                    if s_x1 < s_x2 and s_y1 < s_y2:
                        s_roi = frame[s_y1:s_y2, s_x1:s_x2]
                        shadow = np.zeros_like(s_roi)
                        frame[s_y1:s_y2, s_x1:s_x2] = cv2.addWeighted(s_roi, 0.7, shadow, 0.3, 0)

                    frame[y1:y2, x1:x2] = cv2.addWeighted(roi, 0.4, img_roi, 0.6, 0)
                
                # Reflection Effect
                ref_h = nh // 2
                ry1 = iy + nh
                ry2 = min(h, ry1 + ref_h)
                if ry1 < ry2:
                    ref_roi = frame[ry1:ry2, x1:x2]
                    # Flip and Blur
                    reflection = cv2.flip(res_img, 0)[:ry2-ry1, sx:sx+ew]
                    reflection = cv2.GaussianBlur(reflection, (11, 11), 0)
                    frame[ry1:ry2, x1:x2] = cv2.addWeighted(ref_roi, 0.7, reflection, 0.3, 0)
                    
        return frame
