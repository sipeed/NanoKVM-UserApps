import mmap
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import time
import math

# Physical screen dimensions
PHYSICAL_WIDTH = 172
PHYSICAL_HEIGHT = 320
BPP = 16

# Maximum wave height
WAVE_MAX_HEIGHT = 10

class RGB565Display:
    def __init__(self, fb_device="/dev/fb0"):
        self.physical_width = PHYSICAL_WIDTH
        self.physical_height = PHYSICAL_HEIGHT
        self.bpp = BPP
        self.fb_size = self.physical_width * self.physical_height * (self.bpp // 8)

        # Open framebuffer device
        self.fb_fd = os.open(fb_device, os.O_RDWR)
        self.fb_mmap = mmap.mmap(
            self.fb_fd, self.fb_size, mmap.MAP_SHARED, mmap.PROT_WRITE
        )
        self.fb_array = np.frombuffer(self.fb_mmap, dtype=np.uint16).reshape(
            (self.physical_height, self.physical_width)
        )
        
        # Load fonts
        self._load_fonts()
        
        # Wave animation parameters
        self.wave_phase = 0.0

    def _load_fonts(self):
        """Load fonts"""
        try:
            self.font_timer = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56
            )
            self.font_status = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22
            )
        except:
            try:
                self.font_timer = ImageFont.truetype(
                    "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf", 56
                )
                self.font_status = ImageFont.truetype(
                    "/usr/share/fonts/truetype/freefont/FreeMono.ttf", 22
                )
            except:
                print("Warning: Unable to load system fonts, using default font")
                self.font_timer = ImageFont.load_default()
                self.font_status = ImageFont.load_default()

    def rgb_to_rgb565(self, r, g, b):
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    def clear_screen(self, color=0x0000):
        self.fb_array.fill(color)

    def format_time(self, seconds):
        """Format time as MM:SS"""
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def draw_wave_pattern(self, progress, is_work=True):
        """
        Draw water wave effect - mask version
        progress: progress value between 0-1
        is_work: True for work mode (red), False for rest mode (green)
        """
        # Create logical size image (landscape 320x172)
        logical_img = Image.new("RGB", (320, 172), (0, 0, 0))  # Black background
        draw = ImageDraw.Draw(logical_img)
        
        # HSV color configuration
        if is_work:
            # Red color scheme: hue 0-10 degrees, saturation from high to low, value from high to low
            base_hue = 5        # Base hue (red)
            sat_range = (0.7, 0.9)  # Saturation range: from high to low
            val_range = (0.95, 0.5) # Value range: from bright to dark
        else:
            # Green color scheme: hue 120-130 degrees, saturation from high to low, value from high to low
            base_hue = 125      # Base hue (green)
            sat_range = (0.8, 0.4)  # Saturation range: from high to low
            val_range = (0.9, 0.8)  # Value range: from bright to dark
        
        # Calculate liquid height (from full screen to 0)
        liquid_height = int(172 * (1 - progress))
        
        # Draw water wave effect
        if liquid_height > 0:
            # Calculate wave amplitude: sin
            wave_amplitude = int(WAVE_MAX_HEIGHT * math.sin(progress * math.pi))
            
            # Update wave phase to create animation effect
            self.wave_phase += 0.15
            
            # 1. First draw complete gradient rectangle including wave height
            total_liquid_height = liquid_height + wave_amplitude
            total_liquid_height2 = liquid_height + (wave_amplitude * 3)

            liquid_top = 172 - total_liquid_height
            liquid_top2 = 172 - total_liquid_height2

            # Create smooth gradient using HSV color space
            for y in range(liquid_top2, 172):
                # Calculate current row's relative position in liquid (0-1)
                row_progress = (y - liquid_top2) / total_liquid_height2

                # Calculate HSV values
                saturation = sat_range[0] + (sat_range[1] - sat_range[0]) * row_progress
                value = val_range[0] + (val_range[1] - val_range[0]) * row_progress
                
                # HSV to RGB
                h = base_hue / 360.0
                s = saturation
                v = value
                
                # HSV to RGB conversion
                if s == 0.0:
                    r = g = b = v
                else:
                    h *= 6.0
                    i = int(h)
                    f = h - i
                    p = v * (1.0 - s)
                    q = v * (1.0 - s * f)
                    t = v * (1.0 - s * (1.0 - f))
                    
                    if i == 0:
                        r, g, b = v, t, p
                    elif i == 1:
                        r, g, b = q, v, p
                    elif i == 2:
                        r, g, b = p, v, t
                    elif i == 3:
                        r, g, b = p, q, v
                    elif i == 4:
                        r, g, b = t, p, v
                    else:
                        r, g, b = v, p, q
                
                # Convert to 0-255 range
                r, g, b = int(r * 255), int(g * 255), int(b * 255)
                
                # Draw this row
                draw.line([(0, y), (320, y)], fill=(r, g, b))
            
            # 2. Calculate wave contour, create black mask to "erase" the part above the wave
            wave_points = []
            for x in range(0, 321, 2):
                # Composite wave: two sine waves with different frequencies superimposed
                wave1 = math.sin(x * 0.05 + self.wave_phase) * wave_amplitude
                wave2 = math.sin(x * 0.03 + self.wave_phase * 1.3) * (wave_amplitude * 0.6)
                wave_height = wave1 + wave2
                
                # Calculate wave surface y-coordinate (from top)
                wave_y = 172 - total_liquid_height + int(wave_height)
                wave_points.append((x, wave_y))
            
            # 3. Create black polygon to erase the part above the wave
            erase_points = wave_points + [(320, 0), (0, 0)]
            draw.polygon(erase_points, fill=(0, 0, 0))
            
            # 4. Draw wave highlight lines
            for i in range(len(wave_points) - 1):
                x1, y1 = wave_points[i]
                x2, y2 = wave_points[i + 1]
                
                # Calculate wave slope
                slope = y2 - y1
                
                # Add highlight effect on wave surface (only on uphill parts)
                if slope > 0:  # Uphill part
                    # Calculate highlight strength
                    highlight_strength = min(1.0, 0.3 + abs(slope) * 0.1)
                    
                    # Calculate HSV for highlight position
                    highlight_h = base_hue / 360.0
                    highlight_s = max(0, sat_range[0] - 0.2)  # Reduce saturation
                    highlight_v = min(1.0, val_range[0] + 0.2)  # Increase value
                    
                    # HSV to RGB
                    if highlight_s == 0.0:
                        hr, hg, hb = highlight_v, highlight_v, highlight_v
                    else:
                        highlight_h *= 6.0
                        hi = int(highlight_h)
                        hf = highlight_h - hi
                        hp = highlight_v * (1.0 - highlight_s)
                        hq = highlight_v * (1.0 - highlight_s * hf)
                        ht = highlight_v * (1.0 - highlight_s * (1.0 - hf))
                        
                        if hi == 0:
                            hr, hg, hb = highlight_v, ht, hp
                        elif hi == 1:
                            hr, hg, hb = hq, highlight_v, hp
                        elif hi == 2:
                            hr, hg, hb = hp, highlight_v, ht
                        elif hi == 3:
                            hr, hg, hb = hp, hq, highlight_v
                        elif hi == 4:
                            hr, hg, hb = ht, hp, highlight_v
                        else:
                            hr, hg, hb = highlight_v, hp, hq
                    
                    hr, hg, hb = int(hr * 255), int(hg * 255), int(hb * 255)
                    
                    # Draw highlight line
                    draw.line([(x1, y1), (x2, y2)], fill=(hr, hg, hb), width=2)
            # Draw liquid_top debug lines
            # draw.line([(0, liquid_top), (320, liquid_top)], fill=(255, 255, 255), width=1)
            # draw.line([(0, liquid_top2), (320, liquid_top2)], fill=(0, 0, 255), width=1)

        # Draw countdown text
        timer_text = self.format_time(int(25 * 60 * (1-progress)) if is_work else int(5 * 60 * (1-progress)))
        bbox = draw.textbbox((0, 0), timer_text, font=self.font_timer)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x_text = (320 - text_width) // 2
        y_text = (172 - text_height) // 2 - 30
        
        draw.text((x_text, y_text), timer_text, fill=(255, 255, 255), font=self.font_timer)

        # Draw status text
        status_text = "Working..." if is_work else "Resting..."
        bbox_status = draw.textbbox((0, 0), status_text, font=self.font_status)
        status_width = bbox_status[2] - bbox_status[0]
        x_status = (320 - status_width) // 2
        y_status = y_text + text_height + 25
        
        draw.text((x_status, y_status), status_text, fill=(255, 255, 255), font=self.font_status)

        # Convert to physical image and display
        self._display_image(logical_img)

    def _display_image(self, logical_img):
        """Rotate logical image and display on physical screen"""
        # Rotate logical image 90 degrees counterclockwise to get physical image
        physical_img = logical_img.rotate(90, expand=True)

        # Convert to RGB565 and copy to framebuffer
        rgb_array = np.array(physical_img)
        r = (rgb_array[:, :, 0] >> 3).astype(np.uint16)
        g = (rgb_array[:, :, 1] >> 2).astype(np.uint16)
        b = (rgb_array[:, :, 2] >> 3).astype(np.uint16)
        rgb565 = (r << 11) | (g << 5) | b

        # Directly copy entire array to framebuffer
        self.fb_array[:, :] = rgb565

    def close(self):
        self.fb_mmap.close()
        os.close(self.fb_fd)


class PomodoroTimer:
    def __init__(self, display):
        self.display = display
        self.work_time = 25 * 60  # 25 minutes work
        self.break_time = 5 * 60  # 5 minutes rest
        # self.work_time = 10  # 10s test
        # self.break_time = 10  # 10s test
        self.is_work_mode = True
        self.current_time = self.work_time
        self.start_time = time.time()
        
    def update(self):
        """Update timer status"""
        elapsed = time.time() - self.start_time
        remaining = max(0, self.current_time - elapsed)
        
        if remaining <= 0:
            # Switch mode
            self.is_work_mode = not self.is_work_mode
            self.current_time = self.work_time if self.is_work_mode else self.break_time
            self.start_time = time.time()
            remaining = self.current_time
            
            # Mode switch notification
            mode_name = "Work" if self.is_work_mode else "Rest"
            print(f"Switched to {mode_name} mode")
        
        # Calculate progress (0-1)
        if self.is_work_mode:
            progress = 1 - (remaining / self.work_time)
        else:
            progress = 1 - (remaining / self.break_time)
        
        # Draw interface
        self.display.draw_wave_pattern(progress, self.is_work_mode)
        
        return remaining
    
    def get_current_mode(self):
        """Get current mode"""
        return "Work" if self.is_work_mode else "Rest"


def main():
    # Initialize display
    display = RGB565Display()
    
    try:
        # Create pomodoro timer
        pomodoro = PomodoroTimer(display)
        
        print("Pomodoro timer started!")
        print("Work: 25 minutes, Rest: 5 minutes")
        print("Press Ctrl+C to exit")
        
        while True:
            remaining = pomodoro.update()
            
            # Console output status
            mode = pomodoro.get_current_mode()
            minutes = int(remaining) // 60
            seconds = int(remaining) % 60
            progress = 1 - (remaining / (25*60 if pomodoro.is_work_mode else 5*60))
            
            print(f"\r{mode} mode - Remaining: {minutes:02d}:{seconds:02d} - Progress: {progress*100:.1f}%", 
                  end="", flush=True)
            
            # Control refresh rate
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n\nPomodoro timer stopped")
    except Exception as e:
        print(f"\nProgram runtime error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up resources
        display.close()
        print("Program exited")


if __name__ == "__main__":
    main()