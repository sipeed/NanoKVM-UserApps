# NanoKVM-UserApps

NanoKVM-Desk是Sipeed推出的IPKVM产品，拥有AX630为核心（双核<A53@1.2GHz>，内置3Tops NPU）配置了1G LPDDR4内存和32GeMMC，同时支持TF卡扩展，并有可选的wifi、POE配置，除了强大的远程控制功能外，其拥有一块1.47寸触摸显示屏和旋钮，作为桌面摆件的形态有无限的DIY想象空间。

本仓库是开源的UserApp仓库，用户可以使用"APP Hub"功能下载这里的所有应用，当然如果你有任何想法，可以参考下面的文档构建自己的应用，本仓库也欢迎你的投稿，经过我们的基础功能审核后你开发的应用可以被所有NanoKVM-Desk用户下载和使用。

## 如何构建你自己的应用

> 你可以将此文档发送给AI，来辅助生成你自己的应用！

### 项目文件夹的介绍

NanoKVM-Desk UserAPP会扫描 `/userapp` 目录下所有的文件夹，每一个文件夹就是一个APP，文件夹名称就是APP名称。文件夹内至少包含 `main.py` 和 `app.toml`。

`main.py` 是运行的代码，`app.toml` 是配置文件，其内容如下：

```toml
[application]
name = "XXX"                        # 使用文件夹名，启动时显示(必须且与目录名一致)
version = "1.0.0"                   # 用作版本升级，启动时显示(必须为SemVer格式子集 MAJOR.MINOR.PATCH)
descriptions = "Example"            # 用作App简短描述，在下载更新时显示(必须，用于用户快速了解app功能)

[author]
name = "Sipeed-xxx"                 # 填写作者名称，启动时显示(必须)
email = "xxx@sipeed.com"            # 方便用户联系作者(可选)

[interaction]
requires_user_input = false         # 是否需要开放触摸屏以及旋钮事件；若为true，要求程序内必须有主动退出机制(可选)
```

### 屏幕基础信息和使用方法

NanoKVM-Desk的屏幕分辨率为320*172，通过 `/dev/fb0` 访问。设备配备了一个172x320像素的RGB565彩色显示屏，可通过帧缓冲设备 `/dev/fb0` 访问。应用程序可以直接绘制到该显示设备上。

#### 显示特性

- **分辨率**: 172x320 像素（但逻辑屏幕是 320x172 - 见下面的旋转说明）
- **颜色深度**: 16 位 RGB565 格式 (红色 5 位，绿色 6 位，蓝色 5 位)
- **帧缓冲设备**: `/dev/fb0`
- **显示方向**: 物理显示屏为纵向模式，但应用程序通常创建横向图像 (320x172) 并逆时针旋转 90 度以供显示。

#### 基本显示用法

在 Python 应用程序中使用显示设备：

1. **设置物理显示尺寸的常量**:

   ```python
   PHYSICAL_WIDTH = 172
   PHYSICAL_HEIGHT = 320
   BPP = 16  # 每像素位数
   ```

2. **创建与帧缓冲区接口的显示类**:

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

           # 打开帧缓冲设备
           self.fb_fd = os.open(fb_device, os.O_RDWR)
           self.fb_mmap = mmap.mmap(
               self.fb_fd, self.fb_size, mmap.MAP_SHARED, mmap.PROT_WRITE
           )
           self.fb_array = np.frombuffer(self.fb_mmap, dtype=np.uint16).reshape(
               (self.physical_height, self.physical_width)
           )

       def rgb_to_rgb565(self, r, g, b):
           """将 8 位 RGB 转换为 RGB565 格式"""
           return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

       def clear_screen(self, color=0x0000):
           """使用指定颜色清屏"""
           self.fb_array.fill(color)

       def _display_image(self, logical_img):
           """旋转逻辑图像并在物理屏幕上显示"""
           # 将逻辑图像逆时针旋转 90 度以获得物理图像
           physical_img = logical_img.rotate(90, expand=True)

           # 转换为 RGB565 并复制到帧缓冲区
           rgb_array = np.array(physical_img)
           r = (rgb_array[:, :, 0] >> 3).astype(np.uint16)
           g = (rgb_array[:, :, 1] >> 2).astype(np.uint16)
           b = (rgb_array[:, :, 2] >> 3).astype(np.uint16)
           rgb565 = (r << 11) | (g << 5) | b

           # 直接复制整个数组到帧缓冲区
           self.fb_array[:, :] = rgb565

       def close(self):
           """关闭资源"""
           self.fb_mmap.close()
           os.close(self.fb_fd)
   ```

3. **在显示上绘制内容**:

   ```python
   def main():
       display = RGB565Display()
       
       try:
           # 创建逻辑横向图像 (320x172)
           logical_img = Image.new("RGB", (320, 172), (0, 0, 0))
           draw = ImageDraw.Draw(logical_img)

           # 绘制内容 (例如，矩形、文字)
           draw.rectangle([10, 10, 100, 100], fill=(255, 0, 0))  # 红色矩形
           
           # 显示图像
           display._display_image(logical_img)
           
           # 等待一段时间
           import time
           time.sleep(5)
           
       finally:
           display.close()

   if __name__ == "__main__":
       main()
   ```

#### 显示用法的最佳实践

- 始终将逻辑横向图像 (320x172) 逆时针旋转以匹配物理纵向显示 (172x320)
- 尽可能使用高效的绘图方法以减少渲染时间
- 在 `finally` 块或上下文管理器中正确关闭资源，以防止资源泄漏
- 在绘制频繁更新的内容时考虑性能 (例如，动画)

#### 输入事件说明与使用指南

NanoKVM-Desk 系统支持三类输入事件：旋钮旋转、旋钮按压以及触摸输入。

> 当你的应用需要使用输入事件时，必须在 `app.toml` 中声明 `requires_user_input = true`，并且应用本身必须实现明确的退出机制，否则将无法返回到 NanoKVM-UI。
> 如果你的程序不需要触摸或旋钮输入事件，则可将该字段设为 `false` 或直接省略。此时，用户触摸屏幕或按下按键时系统将自动退出当前应用并返回 UI。

##### 输入设备概述

系统中存在以下三类输入设备：

- 旋钮旋转事件
- 旋钮按下/长按/松开事件
- 触摸屏事件

`/dev/input/eventN` 的编号可能因设备枚举顺序不同而变化，因此 **不要依赖固定的 event 编号**。需要通过 sysfs 中的设备名称来动态识别设备。

设备名称可通过以下路径查询：

```
/sys/class/input/eventN/device/name
```

##### 典型设备映射

| 输入类型 | 驱动名         | 上报事件类型             | 说明               |
| ---- | ----------- | ------------------ | ---------------- |
| 旋钮旋转 | `rotary@0`  | EV_REL / REL_X     | 用于增量调节、翻页或焦点移动   |
| 旋钮按键 | `gpio_keys` | EV_KEY (KEY_ENTER) | 支持按下、松开及长按自动重复   |
| 触摸屏  | `hyn_ts`    | EV_ABS / ABS_MT_*  | 上报坐标、压力、触摸点序号等信息 |

##### 使用注意事项

- 不要硬编码 `/dev/input/event0` 这类路径；应在运行时扫描 sysfs 解析设备编号。
- 若未找到目标设备，则返回原始设备名用于提示和诊断。
- 访问 `/dev/input` 设备通常需要 root 权限或 udev 规则放行。

##### Python 示例：动态查找输入设备

```python
import os
import re
from typing import Dict

class InputDeviceFinder:
    """扫描 /sys/class/input，构建 eventN -> 设备名映射，并根据名称解析为对应的 /dev/input/eventN 路径。"""

    def __init__(self, input_root: str = "/sys/class/input") -> None:
        self.input_root = input_root
        self.event_regex = re.compile(r"event(\\d+)$")
        self.devices = self._get_event_device_names()

    def _get_event_device_names(self) -> Dict[int, str]:
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
    # 输出示例： {'rotary': '/dev/input/event0', 'key': '/dev/input/event1', 'touch': '/dev/input/event2'}
```

##### 进一步建议

- 若名称匹配失败，可进一步解析 `/proc/bus/input/devices` 或使用 `udevadm` / `libinput` 获取更丰富的设备信息。
- 用户态程序可使用 `evdev` / `libinput` 读取事件。如果是服务程序，可在启动时缓存设备映射，并在设备变更时重新扫描。

#### 自动加载第三方 Python 库

这种方式适用于：

- 你希望程序“按需加载”依赖

- 你不想在镜像/固件里预置太多库

- 你希望应用能开箱即用，无需用户提前处理依赖

以下是完整可直接使用的类：

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

示例：按需加载 `evdev`，用于处理输入事件：

```python
evdev = AutoImport.import_package("evdev")
InputDevice = evdev.InputDevice
ecodes = evdev.ecodes
```

如果 `evdev` 已安装，则直接导入；如果未安装，将自动执行安装后再继续运行。

### 示例

`apps` 目录中的几个示例，可能帮你更好的构建自己的应用：

- `hello`: 基本显示功能
- `drawo`: 带有触摸屏支持的绘图应用程序

## 贡献到软件源

我们鼓励社区创建并上传他们自己的应用程序到此仓库！这作为 NanoKVM-Desk 的软件源，您的贡献使我们的生态系统更加丰富。

### 如何上传您的应用程序

1. 创建一个 pull request，将您的应用程序放入 `apps` 文件夹
2. 您的应用程序将经过简单的审核流程（作为开源社区，我们只审核基本功能；安全性由开发者保证）
3. 一经批准，您的应用程序将在 NanoKVM-Desk APP Hub 中提供

### 如何上报UserAPP的问题

请在本仓库的issus下报告问题，并@对应app下app.toml的作者
