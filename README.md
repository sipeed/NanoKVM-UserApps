# NanoKVM-UserApps

NanoKVM-Desk is an IP-KVM product developed by Sipeed, featuring an AX630 as its core (dual-core <A53@1.2GHz>, built-in 3TOPS NPU), configured with 1GB LPDDR4 memory and 32GB eMMC, while supporting TF card expansion, and optional WiFi and POE configurations. In addition to powerful remote control functions, it has a 1.47-inch touch display and rotary knob, offering infinite DIY possibilities as a desktop accessory.

This repository is an open-source UserApp repository. Users can download all applications from here using the "APP Hub" feature. If you have any ideas, you can refer to the documentation below to build your own applications. This repository welcomes your contributions as well. After our basic functionality review, your developed applications can be downloaded and used by all NanoKVM-Desk users.

## How to Build Your Own Application

> You can send this document to an AI to assist in generating your own application!

### Project Folder Introduction

NanoKVM-Desk UserAPP scans all folders in the `/userapp` directory, with each folder representing an app. The folder name serves as the app name. Each folder must contain at least `main.py` and `app.toml`.

`main.py` is the executable code, and `app.toml` is the configuration file with the following content:

```toml
[application]
name = "XXX"                        # Use folder name, displayed on startup (required and must match directory name)
version = "1.0.0"                   # Used for version upgrade, displayed on startup (required for checking updates, must be SemVer subset MAJOR.MINOR.PATCH format)
descriptions = "Example"            # Short app description, displayed during download/update (required for users to quickly understand app functionality)

[author]
name = "Sipeed-xxx"                 # Fill in author name, displayed on startup (required)
email = "xxx@sipeed.com"            # Facilitates user contact with author (optional)

[interaction]
requires_user_input = false         # Whether to require access to touch screen and rotary events; if true, program must have explicit exit mechanism (optional)
```

### Screen Information and Usage

The NanoKVM-Desk screen has a resolution of 320x172 and is accessible via `/dev/fb0`. The device features a 172x320 pixel RGB565 color display, accessible via the framebuffer device `/dev/fb0`. Applications can draw directly to this display using the framebuffer interface.

#### Display Characteristics

- **Resolution**: 172x320 pixels (but logical screen is 320x172 - see rotation below)
- **Color Depth**: 16-bit RGB565 format (5 bits red, 6 bits green, 5 bits blue)
- **Framebuffer Device**: `/dev/fb0`
- **Display Orientation**: The physical display is in portrait mode, but applications typically create landscape images (320x172) and rotate them 90 degrees counterclockwise for display.

#### Basic Display Usage

To use the display in your Python application:

1. **Set up constants** for the physical display dimensions:

   ```python
   PHYSICAL_WIDTH = 172
   PHYSICAL_HEIGHT = 320
   BPP = 16  # Bits per pixel
   ```

2. **Create a display class** that interfaces with the framebuffer:

   ```python
   import mmap
   import os
   import numpy as np
   from PIL import Image, ImageDraw

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
           """Convert 8-bit RGB to RGB565 format"""
           return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

       def clear_screen(self, color=0x0000):
           """Clear screen with specified color"""
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
           """Close resources"""
           self.fb_mmap.close()
           os.close(self.fb_fd)
   ```

3. **Draw content** to the display:

   ```python
   def main():
       display = RGB565Display()
       
       try:
           # Create a logical landscape image (320x172)
           logical_img = Image.new("RGB", (320, 172), (0, 0, 0))
           draw = ImageDraw.Draw(logical_img)

           # Draw your content (e.g., rectangles, text)
           draw.rectangle([10, 10, 100, 100], fill=(255, 0, 0))  # Red rectangle
           
           # Display the image
           display._display_image(logical_img)
           
           # Wait for some time
           import time
           time.sleep(5)
           
       finally:
           display.close()

   if __name__ == "__main__":
       main()
   ```

#### Best Practices for Display Usage

- Always rotate logical landscape images (320x172) counterclockwise to match the physical portrait display (172x320)
- Use efficient drawing methods when possible to minimize rendering time
- Close resources properly in a `finally` block or context manager to prevent resource leaks
- Consider performance when drawing frequently updated content (e.g., animations)

#### Input Events Information and Usage

NanoKVM-Desk has three types of input events: rotary rotation, rotary press, and touch.

> When using input events, you need to declare `requires_user_input = true` in `app.toml`, and your program must have an explicit exit mechanism, otherwise you cannot exit to NanoKVM-UI;
> If your program doesn't need touch or rotary input events, configure the field as `requires_user_input = false` or omit it, and NanoKVM-UI will exit the program when the screen is touched or the button is pressed.

##### Input Devices Description

This system uses three input devices: rotary rotation events, rotary press/hold/release events, and a touch screen. The `/dev/input/eventN` numbering is dynamic and may change between boots due to device enumeration order; therefore you must not rely on fixed event numbers. Use the kernel-registered device name under sysfs (`/sys/class/input/eventN/device/name`) to reliably identify devices.

##### Typical device mapping (example)

- Rotary rotation (relative): driver name `rotary@0`, reports EV_REL / REL_X, used for incremental adjustments, paging or focus movement.
- Rotary button (press/hold/release): driver name `gpio_keys`, reports EV_KEY (KEY_ENTER), supports press/release and key repeat for long press.
- Touchscreen: driver name `hyn_ts`, reports multitouch events (EV_ABS, ABS_MT_*), including coordinates, pressure and tracking id.

##### Behavior notes

- Do not hard-code `/dev/input/event0` style paths; resolve the mapping at runtime by inspecting sysfs.
- If a device name is not found, returning the original name helps diagnostics (indicates device not ready or different name).
- Accessing `/dev/input` devices usually requires root privileges or proper udev rules to grant access.

##### Complete Python example

```python
import os
import re
from typing import Dict

class InputDeviceFinder:
    """Scan /sys/class/input, build eventN -> device name map, and resolve devices by name to /dev/input/eventN."""

    def __init__(self, input_root: str = "/sys/class/input") -> None:
        self.input_root = input_root
        self.event_regex = re.compile(r"event(\d+)$")
        self.devices = self._get_event_device_names()

    def _get_event_device_names(self) -> Dict[int, str]:
        """Return a mapping { event_num: device_name } by scanning input_root."""
        event_map: Dict[int, str] = {}

        try:
            for entry in os.scandir(self.input_root):
                if not entry.is_dir():
                    continue

                m = self.event_regex.match(entry.name)
                if not m:
                    continue

                try:
                    event_num = int(m.group(1))
                except ValueError:
                    continue

                name_path = os.path.join(entry.path, "device", "name")
                if not os.path.exists(name_path):
                    continue

                try:
                    with open(name_path, "r", encoding="utf-8") as f:
                        name = f.readline().strip()
                        if name:
                            event_map[event_num] = name
                except Exception:
                    continue
        except FileNotFoundError:
            pass

        return event_map

    def find_devices(self, targets: Dict[str, str]) -> Dict[str, str]:
        """Resolve device names to /dev/input/eventN paths.

        @param targets: e.g. {"rotary": "rotary@0", "key": "gpio_keys"}
        @return: e.g. {"rotary": "/dev/input/event2", ...}
                 If not found, the value will be the original name for troubleshooting.
        """
        result: Dict[str, str] = {}

        for role, name in targets.items():
            found = False
            for n, dev_name in self.devices.items():
                if dev_name == name:
                    result[role] = f"/dev/input/event{n}"
                    found = True
                    break
            if not found:
                result[role] = name

        return result


if __name__ == "__main__":
    finder = InputDeviceFinder()
    devices = finder.find_devices({
        "rotary": "rotary@0",
        "key": "gpio_keys",
        "touch": "hyn_ts",
    })

    print("Detected devices:", devices)
    # Example output: Detected devices: {'rotary': '/dev/input/event0', 'key': '/dev/input/event1', 'touch': '/dev/input/event2'}
```

##### Additional recommendations

- For increased robustness, when name lookup fails, try parsing `/proc/bus/input/devices` or use `udevadm`/`libinput` to obtain richer device metadata.
- In user-space programs, open `/dev/input/eventX` via `evdev`/`libinput` libraries to read events. For services, consider caching the mapping for a short time and re-scan on device changes.

#### Automatic Loading of Third-Party Python Libraries

This approach is suitable when:

- You want your application to load dependencies only when they are needed.
- You prefer not to pre-package many libraries in your system image or firmware.
- You want the application to run out-of-the-box without requiring users to install dependencies manually.

The following class can be used directly:

```python
import importlib
import subprocess
import sys

class AutoImport:
    @staticmethod
    def import_package(pip_name: str, import_name: str | None = None):
        import_name = import_name or pip_name

        try:
            package = importlib.import_module(import_name)
            print(f"Package '{import_name}' imported successfully.")
            return package
        except ImportError:
            print(f"Package '{import_name}' not found. Trying to install '{pip_name}'...")
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
```

Example: Load `evdev` on demand for handling input events:

```python
evdev = AutoImport.import_package("evdev")
InputDevice = evdev.InputDevice
ecodes = evdev.ecodes
```

If `evdev` is already installed, it will be imported directly. Otherwise, it will be installed automatically before continuing.

## Contributing to the Software Repository

We encourage the community to create and upload their own applications to this repository! This serves as the software source for NanoKVM-Desk, and your contributions make our ecosystem richer.

### How to Upload Your Application

1. Create a pull request with your application in the `apps` folder
2. Your application will go through a simple review process (as an open source community, we only review basic functionality; security is the responsibility of the developer)
3. Once approved, your application will be available in the NanoKVM-Desk APP Hub

### How to Report UserAPP Issues

Please report issues in the issues section of this repository, and @ the author specified in the app.toml file of the corresponding app.

### Examples

Several examples in the `apps` directory may help you better build your own applications:

- `hello`: Basic display functionality
- `drawo`: Drawing application with touch screen support
