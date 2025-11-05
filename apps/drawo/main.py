import mmap
import os
import numpy as np
from PIL import Image, ImageDraw
import sys
from select import select
import re
import importlib
import subprocess

# Physical screen dimensions
PHYSICAL_WIDTH = 172
PHYSICAL_HEIGHT = 320
BPP = 16

# Maximum wave height
WAVE_MAX_HEIGHT = 10

LOGICAL_WIDTH = 320
LOGICAL_HEIGHT = 172
EXIT_BTN_SIZE = 40
DRAW_COLOR = (0, 0, 0)
BG_COLOR = (255, 255, 255)
EXIT_COLOR = (255, 0, 0)


class AutoImport:
    @staticmethod
    def import_package(pip_name: str, import_name: str | None = None):
        import_name = import_name or pip_name

        try:
            package = importlib.import_module(import_name)
            print(f"Package '{import_name}' imported successfully.")
            return package
        except ImportError:
            print(
                f"Package '{import_name}' not found. Trying to install '{pip_name}'..."
            )
            AutoImport.install_package(pip_name)

            package = importlib.import_module(import_name)
            print(f"Package '{import_name}' imported successfully after installation.")
            return package

    @staticmethod
    def install_package(pip_name: str):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
            print(f"Package '{pip_name}' installed successfully.")
        except subprocess.CalledProcessError:
            print(f"Failed to install '{pip_name}'. Check network or permissions.")


evdev = AutoImport.import_package("evdev")
InputDevice = evdev.InputDevice
ecodes = evdev.ecodes


class InputDeviceFinder:
    def __init__(self, input_root="/sys/class/input"):
        self.input_root = input_root
        self.event_regex = re.compile(r"event(\d+)")
        self.devices = self._get_event_device_names()

    def _get_event_device_names(self):
        """Scan /sys/class/input to map eventN -> device name"""
        event_map = {}
        for entry in os.scandir(self.input_root):
            if not entry.is_dir():
                continue

            m = self.event_regex.match(entry.name)
            if not m:
                continue

            event_num = int(m.group(1))
            name_path = os.path.join(entry.path, "device", "name")

            if os.path.exists(name_path):
                try:
                    with open(name_path, "r", encoding="utf-8") as f:
                        name = f.readline().strip()
                        if name:
                            event_map[event_num] = name
                except Exception:
                    pass
        return event_map

    def find_devices(self, targets):
        """
        Find devices by name.
        @param targets: dict, e.g. {"rotary": "rotary@0", "key": "gpio_keys"}
        @return: dict, e.g. {"rotary": "/dev/input/event2", ...}
        """
        result = {}
        for role, name in targets.items():
            for n, dev_name in self.devices.items():
                if dev_name == name:
                    result[role] = f"/dev/input/event{n}"
                    break
            else:
                result[role] = name
        return result


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

    def rgb_to_rgb565(self, r, g, b):
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    def clear_screen(self, color=0x0000):
        self.fb_array.fill(color)

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


def read_touch_events(dev):
    tx, ty = None, None
    drawing = False
    last_pos = None

    tracking_id = -1

    while True:
        r, _, _ = select([dev], [], [], 0.05)
        if not r:
            continue

        for event in dev.read():
            if event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH:
                drawing = event.value == 1
                if not drawing:
                    last_pos = None

            elif event.type == ecodes.EV_ABS:
                if event.code == ecodes.ABS_MT_TRACKING_ID:
                    tracking_id = event.value
                    if tracking_id == -1:
                        drawing = False
                        last_pos = None
                elif event.code == ecodes.ABS_MT_POSITION_X:
                    tx = event.value
                elif event.code == ecodes.ABS_MT_POSITION_Y:
                    ty = event.value

            elif event.type == ecodes.EV_SYN:
                if drawing and tx is not None and ty is not None:
                    x = 320 - 1 - ty
                    y = tx

                    yield (x, y, last_pos)
                    last_pos = (x, y)


def main():
    finder = InputDeviceFinder()
    devices = finder.find_devices({"touchpad": "hyn_ts"})
    touch_dev_path = devices.get("touchpad")

    if not touch_dev_path or not os.path.exists(touch_dev_path):
        print(f"Touchpad device not found. Known devices: {finder.devices}")
        sys.exit(1)

    print(f"Using touch device: {touch_dev_path}")

    disp = RGB565Display()
    disp.clear_screen(0x0000)

    canvas = Image.new("RGB", (LOGICAL_WIDTH, LOGICAL_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, EXIT_BTN_SIZE, EXIT_BTN_SIZE), fill=EXIT_COLOR)

    dev = InputDevice(touch_dev_path)
    dev.grab()

    print("Drawing board ready. Touch to draw, tap red square to exit.")

    last_pos = None
    tx, ty = None, None

    disp._display_image(canvas)
    for tx, ty, last_pos in read_touch_events(dev):
        tx = max(0, min(LOGICAL_WIDTH - 1, tx))
        ty = max(0, min(LOGICAL_HEIGHT - 1, ty))

        if tx < EXIT_BTN_SIZE and ty < EXIT_BTN_SIZE:
            print(f"Exit button pressed at ({tx},{ty})")
            dev.ungrab()
            disp.close()
            sys.exit(0)

        if last_pos:
            draw.line([last_pos, (tx, ty)], fill=DRAW_COLOR, width=2)

        disp._display_image(canvas)


if __name__ == "__main__":
    main()
