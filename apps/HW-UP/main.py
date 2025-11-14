#!/usr/bin/env python3
"""
环出芯片程序更新应用
控制320x172屏幕显示更新进度和结果
"""

import os
import time
import struct
import mmap
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import select
import glob

# 屏幕参数
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 172
FB_DEVICE = '/dev/fb0'

# 物理屏幕尺寸 (需要根据实际硬件调整)
PHYSICAL_WIDTH = 172
PHYSICAL_HEIGHT = 320
BPP = 16

# 触摸控制全局变量
TOUCH_DISABLED = 0  # 1=禁用触摸退出，0=启用触摸退出

# 颜色定义 (基于十六进制RGB值)
COLOR_HEX_SOFT_GREEN = 0x3AFF47    # 柔和绿色 RGB(58, 255, 71)
COLOR_HEX_SOFT_RED = 0xFF272B      # 柔和红色 RGB(255, 39, 43)
COLOR_HEX_BLACK = 0x000000         # 黑色 RGB(0, 0, 0)
COLOR_HEX_WHITE = 0xFFFFFF         # 白色 RGB(255, 255, 255)

# 从十六进制颜色计算RGB分量
def hex_to_rgb(hex_color):
    r = (hex_color >> 16) & 0xFF
    g = (hex_color >> 8) & 0xFF
    b = hex_color & 0xFF
    return (r, g, b)

def rgb_to_rgb565(r, g, b):
    """将RGB颜色转换为RGB565格式"""
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

# 计算RGB565颜色值
COLOR_SOFT_GREEN = rgb_to_rgb565(*hex_to_rgb(COLOR_HEX_SOFT_GREEN))
COLOR_SOFT_RED = rgb_to_rgb565(*hex_to_rgb(COLOR_HEX_SOFT_RED))
COLOR_BLACK = rgb_to_rgb565(*hex_to_rgb(COLOR_HEX_BLACK))
COLOR_WHITE = rgb_to_rgb565(*hex_to_rgb(COLOR_HEX_WHITE))

# 计算渐变颜色RGB元组
GRADIENT_SOFT_GREEN = hex_to_rgb(COLOR_HEX_SOFT_GREEN)
GRADIENT_SOFT_RED = hex_to_rgb(COLOR_HEX_SOFT_RED)

def unload_lt6911_driver():
    """卸载lt6911驱动"""
    try:
        print("正在卸载lt6911驱动...")
        result = subprocess.run('rmmod lt6911_manage', 
                              shell=True,
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        if result.returncode == 0:
            print("lt6911驱动卸载成功")
            return True
        else:
            print(f"lt6911驱动卸载失败: {result.stderr}")
            # 如果驱动未加载，也认为是成功的
            if "Module lt6911_manage is not currently loaded" in result.stderr:
                print("驱动未加载，继续执行")
                return True
            return False
    except subprocess.TimeoutExpired:
        print("卸载lt6911驱动超时")
        return False
    except Exception as e:
        print(f"卸载lt6911驱动时出错: {e}")
        return False

def load_lt6911_driver():
    """加载lt6911驱动"""
    try:
        print("正在加载lt6911驱动...")
        result = subprocess.run('insmod /kvmcomm/ko/lt6911_manage.ko', 
                              shell=True,
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        if result.returncode == 0:
            print("lt6911驱动加载成功")
            return True
        else:
            print(f"lt6911驱动加载失败: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("加载lt6911驱动超时")
        return False
    except Exception as e:
        print(f"加载lt6911驱动时出错: {e}")
        return False

class TouchMonitor:
    """触摸事件监控器"""
    def __init__(self):
        self.touch_device = self._find_touch_device()
        self.touch_fd = None
        if self.touch_device:
            try:
                self.touch_fd = open(self.touch_device, 'rb')
                print(f"成功打开触摸设备: {self.touch_device}")
            except Exception as e:
                print(f"打开触摸设备失败: {e}")
                self.touch_fd = None
    
    def _find_touch_device(self):
        """查找名为hyn_ts的触摸设备"""
        for event_dev in glob.glob('/dev/input/event*'):
            try:
                device_name_path = f"/sys/class/input/{os.path.basename(event_dev)}/device/name"
                if os.path.exists(device_name_path):
                    with open(device_name_path, 'r') as f:
                        name = f.read().strip()
                    if name == 'hyn_ts':
                        print(f"找到触摸设备: {event_dev}")
                        return event_dev
            except Exception as e:
                print(f"检查设备 {event_dev} 时出错: {e}")
                continue
        print("未找到名为 'hyn_ts' 的触摸设备")
        return None
    
    def check_touch_event(self, timeout=1):
        """检查触摸事件，返回True表示有触摸事件"""
        if not self.touch_fd:
            print("触摸设备未打开")
            return False
        
        if TOUCH_DISABLED:
            print("触摸禁用")
            return False
        
        try:
            # 使用select检查是否有数据可读
            print(f"等待触摸事件，超时: {timeout}秒")  # 调试信息
            rlist, _, _ = select.select([self.touch_fd], [], [], timeout)
            if rlist:
                # 读取完整的输入事件数据结构 (24字节)
                data = self.touch_fd.read(24)
                if len(data) == 24:
                    # 解析输入事件 (struct input_event)
                    sec, usec, type, code, value = struct.unpack('LLHHi', data)
                    print(f"收到输入事件: type={type}, code={code}, value={value}, time={sec}.{usec}")
                    
                    # 简化：任何事件都认为是触摸
                    if type in [1, 3]:  # EV_KEY 或 EV_ABS
                        print("检测到触摸事件")
                        return True
                else:
                    print(f"读取的数据长度不正确: {len(data)} 字节")
            else:
                print("select超时，无触摸事件")  # 调试信息
                pass
        except Exception as e:
            print(f"读取触摸事件时出错: {e}")
        
        return False
    
    def close(self):
        """关闭触摸设备"""
        if self.touch_fd:
            self.touch_fd.close()
            print("触摸设备已关闭")

class RGB565Display:
    def __init__(self, fb_device="/dev/fb0"):
        self.physical_width = PHYSICAL_WIDTH
        self.physical_height = PHYSICAL_HEIGHT
        self.bpp = BPP
        self.fb_size = self.physical_width * self.physical_height * (self.bpp // 8)

        # 打开framebuffer设备
        self.fb_fd = os.open(fb_device, os.O_RDWR)
        self.fb_mmap = mmap.mmap(
            self.fb_fd, self.fb_size, mmap.MAP_SHARED, mmap.PROT_WRITE
        )
        self.fb_array = np.frombuffer(self.fb_mmap, dtype=np.uint16).reshape(
            (self.physical_height, self.physical_width)
        )
        
        # 加载字体
        self._load_fonts()

    def _load_fonts(self):
        """加载字体"""
        try:
            self.font_large = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24
            )
            self.font_medium = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18
            )
            self.font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14
            )
        except Exception as e:
            print(f"字体加载失败: {e}")
            try:
                # 尝试备用字体
                self.font_large = ImageFont.truetype(
                    "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf", 24
                )
                self.font_medium = ImageFont.truetype(
                    "/usr/share/fonts/truetype/freefont/FreeMono.ttf", 18
                )
                self.font_small = ImageFont.truetype(
                    "/usr/share/fonts/truetype/freefont/FreeMono.ttf", 14
                )
            except:
                print("警告: 无法加载系统字体，使用默认字体")
                self.font_large = ImageFont.load_default()
                self.font_medium = ImageFont.load_default()
                self.font_small = ImageFont.load_default()

    def rgb_to_rgb565(self, r, g, b):
        """将RGB颜色转换为RGB565格式"""
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    def clear_screen(self, color=0x0000):
        """清屏"""
        self.fb_array.fill(color)

    def draw_countdown_screen(self, seconds_remaining):
        """绘制倒计时屏幕"""
        # 创建逻辑尺寸图像（横屏320x172）
        logical_img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), (0, 0, 0))  # 黑色背景
        draw = ImageDraw.Draw(logical_img)

        # 第一行提示文字
        line1_text = "Updating loop-out chip"
        bbox1 = draw.textbbox((0, 0), line1_text, font=self.font_medium)
        text1_width = bbox1[2] - bbox1[0]
        x_text1 = (SCREEN_WIDTH - text1_width) // 2
        y_text1 = SCREEN_HEIGHT // 2 - 40
        
        draw.text((x_text1, y_text1), line1_text, fill=(255, 255, 255), font=self.font_medium)

        # 第二行提示文字
        line2_text = "program in"
        bbox2 = draw.textbbox((0, 0), line2_text, font=self.font_medium)
        text2_width = bbox2[2] - bbox2[0]
        x_text2 = (SCREEN_WIDTH - text2_width) // 2
        y_text2 = y_text1 + 25
        
        draw.text((x_text2, y_text2), line2_text, fill=(255, 255, 255), font=self.font_medium)

        # 绘制倒计时数字
        countdown_text = f"{seconds_remaining}s"
        bbox = draw.textbbox((0, 0), countdown_text, font=self.font_large)
        text_width = bbox[2] - bbox[0]
        x_countdown = (SCREEN_WIDTH - text_width) // 2
        y_countdown = SCREEN_HEIGHT // 2 + 10
        
        draw.text((x_countdown, y_countdown), countdown_text, fill=(255, 255, 255), font=self.font_large)

        # 绘制轻触屏幕退出提示
        exit_text = "Touch screen to exit"
        bbox_exit = draw.textbbox((0, 0), exit_text, font=self.font_small)
        exit_width = bbox_exit[2] - bbox_exit[0]
        x_exit = (SCREEN_WIDTH - exit_width) // 2
        y_exit = SCREEN_HEIGHT - 25
        
        draw.text((x_exit, y_exit), exit_text, fill=(128, 128, 128), font=self.font_small)

        # 转换为物理图像并显示
        self._display_image(logical_img)

    def draw_updating_screen(self):
        """绘制更新中屏幕"""
        logical_img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), (0, 0, 0))  # 黑色背景
        draw = ImageDraw.Draw(logical_img)

        # 绘制"Updating..."文字
        updating_text = "Updating..."
        bbox = draw.textbbox((0, 0), updating_text, font=self.font_large)
        text_width = bbox[2] - bbox[0]
        x_text = (SCREEN_WIDTH - text_width) // 2
        y_text = SCREEN_HEIGHT // 2 - 15
        
        draw.text((x_text, y_text), updating_text, fill=(255, 255, 255), font=self.font_large)

        self._display_image(logical_img)

    def draw_success_screen(self):
        """绘制成功屏幕"""
        logical_img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), GRADIENT_SOFT_GREEN)  # 使用统一的柔和绿色背景
        draw = ImageDraw.Draw(logical_img)

        # 绘制成功文字
        success_text = "Update Successful"
        bbox = draw.textbbox((0, 0), success_text, font=self.font_large)
        text_width = bbox[2] - bbox[0]
        x_text = (SCREEN_WIDTH - text_width) // 2
        y_text = SCREEN_HEIGHT // 2
        
        draw.text((x_text, y_text), success_text, fill=(255, 255, 255), font=self.font_large)

        # 绘制对勾图标
        self._draw_success_icon(draw, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 35)

        # 绘制倒计时提示
        countdown_text = "Exiting in 5s"
        bbox = draw.textbbox((0, 0), countdown_text, font=self.font_small)
        text_width = bbox[2] - bbox[0]
        x_countdown = (SCREEN_WIDTH - text_width) // 2
        y_countdown = SCREEN_HEIGHT - 25
        
        draw.text((x_countdown, y_countdown), countdown_text, fill=(255, 255, 255), font=self.font_small)

        self._display_image(logical_img)

    def draw_failure_screen(self):
        """绘制失败屏幕"""
        logical_img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), GRADIENT_SOFT_RED)  # 使用统一的柔和红色背景
        draw = ImageDraw.Draw(logical_img)

        # 绘制失败文字
        failure_text = "Update Failed"
        bbox = draw.textbbox((0, 0), failure_text, font=self.font_large)
        text_width = bbox[2] - bbox[0]
        x_text = (SCREEN_WIDTH - text_width) // 2
        y_text = SCREEN_HEIGHT // 2
        
        draw.text((x_text, y_text), failure_text, fill=(255, 255, 255), font=self.font_large)

        # 绘制警告图标
        self._draw_warning_icon(draw, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 35)

        # 绘制重试提示
        retry_text = "Retrying in 5s"
        bbox = draw.textbbox((0, 0), retry_text, font=self.font_small)
        text_width = bbox[2] - bbox[0]
        x_retry = (SCREEN_WIDTH - text_width) // 2
        y_retry = SCREEN_HEIGHT - 25
        
        draw.text((x_retry, y_retry), retry_text, fill=(255, 255, 255), font=self.font_small)

        self._display_image(logical_img)

    def _draw_warning_icon(self, draw, center_x, center_y):
        """绘制警告图标（三角形感叹号）"""
        # 绘制三角形
        triangle_size = 20
        points = [
            (center_x, center_y - triangle_size),
            (center_x - triangle_size, center_y + triangle_size),
            (center_x + triangle_size, center_y + triangle_size)
        ]
        draw.polygon(points, fill=(255, 255, 0), outline=(255, 255, 255))
        
        # 绘制感叹号
        draw.rectangle([center_x-2, center_y-5, center_x+2, center_y+5], fill=(0, 0, 0))
        draw.rectangle([center_x-2, center_y+10, center_x+2, center_y+12], fill=(0, 0, 0))

    def _draw_success_icon(self, draw, center_x, center_y):
        """绘制成功图标（对勾）"""
        # 绘制圆圈
        circle_radius = 15
        draw.ellipse([
            center_x - circle_radius, center_y - circle_radius,
            center_x + circle_radius, center_y + circle_radius
        ], fill=(255, 255, 255), outline=(255, 255, 255))
        
        # 绘制对勾
        check_color = GRADIENT_SOFT_GREEN  # 使用统一的柔和绿色对勾
        draw.line([
            (center_x - 8, center_y),
            (center_x - 2, center_y + 6),
            (center_x + 8, center_y - 6)
        ], fill=check_color, width=3)

    def transition_color(self, start_color, end_color, steps=30, delay=0.03):
        """颜色渐变过渡（使用统一的柔和颜色定义）"""
        # 定义渐变目标颜色的RGB值
        gradient_colors = {
            COLOR_SOFT_GREEN: GRADIENT_SOFT_GREEN,
            COLOR_SOFT_RED: GRADIENT_SOFT_RED
        }
        
        # 获取目标颜色的RGB值，如果未定义则使用默认计算
        if end_color in gradient_colors:
            target_rgb = gradient_colors[end_color]
            start_r, start_g, start_b = 0, 0, 0  # 从黑色开始
            
            for i in range(steps + 1):
                progress = i / steps
                r = int(start_r + (target_rgb[0] - start_r) * progress)
                g = int(start_g + (target_rgb[1] - start_g) * progress)
                b = int(start_b + (target_rgb[2] - start_b) * progress)
                
                current_color = self.rgb_to_rgb565(r, g, b)
                self.clear_screen(current_color)
                time.sleep(delay)
        else:
            # 默认渐变计算（用于其他颜色）
            start_r = (start_color >> 11) & 0x1F
            start_g = (start_color >> 5) & 0x3F
            start_b = start_color & 0x1F
            
            end_r = (end_color >> 11) & 0x1F
            end_g = (end_color >> 5) & 0x3F
            end_b = end_color & 0x1F
            
            for i in range(steps + 1):
                progress = i / steps
                r = int(start_r + (end_r - start_r) * progress)
                g = int(start_g + (end_g - start_g) * progress)
                b = int(start_b + (end_b - start_b) * progress)
                
                current_color = self.rgb_to_rgb565(r, g, b)
                self.clear_screen(current_color)
                time.sleep(delay)

    def _display_image(self, logical_img):
        """将逻辑图像旋转并显示到物理屏幕"""
        # 将逻辑图像逆时针旋转90度得到物理图像
        physical_img = logical_img.rotate(90, expand=True)

        # 转换为RGB565并复制到framebuffer
        rgb_array = np.array(physical_img)
        r = (rgb_array[:, :, 0] >> 3).astype(np.uint16)
        g = (rgb_array[:, :, 1] >> 2).astype(np.uint16)
        b = (rgb_array[:, :, 2] >> 3).astype(np.uint16)
        rgb565 = (r << 11) | (g << 5) | b

        # 直接复制整个数组到framebuffer
        self.fb_array[:, :] = rgb565

    # def close(self):
    #     """关闭显示资源"""
    #     self.fb_mmap.close()
    #     os.close(self.fb_fd)

    def close(self):
        """关闭显示资源"""
        try:
            # 首先删除numpy数组的引用
            if hasattr(self, 'fb_array'):
                del self.fb_array
            
            # 然后关闭mmap
            if hasattr(self, 'fb_mmap'):
                self.fb_mmap.close()
            
            # 最后关闭文件描述符
            if hasattr(self, 'fb_fd'):
                os.close(self.fb_fd)
                
            print("显示资源已释放")
        except Exception as e:
            print(f"关闭显示资源时出错: {e}")

def run_update_script():
    """运行更新脚本并捕获输出"""
    script_path = "/userapp/HW-UP/nanokvm_update_86102"
    bin_file = "/userapp/HW-UP/nanokvm_86102R2[43].bin"
    
    try:
        # 确保有可执行权限
        subprocess.check_call(['chmod', '+x', script_path])

        # 执行更新脚本
        process = subprocess.Popen(
            [script_path, bin_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # 实时读取输出
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                if "Firmware write completed" in output:
                    return True
                if "Failed" in output:
                    return False
        
        # 检查最终返回码
        return process.returncode == 0
        
    except Exception as e:
        print(f"执行更新脚本时出错: {e}")
        return False

def main():
    """主程序"""
    print("启动环出芯片程序更新应用")
    
    display = RGB565Display()
    touch_monitor = TouchMonitor()
    
    try:
        # 初始黑色屏幕
        display.clear_screen(0x0000)
        
        # 10秒倒计时（检查触摸事件）
        for i in range(10, 0, -1):
            display.draw_countdown_screen(i)
            if touch_monitor.check_touch_event(timeout=1):
                print("检测到触摸事件,直接退出")
                return 0

        # 卸载lt6911驱动
        unload_lt6911_driver()
        lt6911_driver_is_unloaded = True
        time.sleep(1)  # 等待驱动完全卸载

        while True:
            # 显示"Updating..."屏幕
            display.draw_updating_screen()
            
            # 执行更新脚本（更新过程中禁用触摸退出）
            global TOUCH_DISABLED
            TOUCH_DISABLED = 1
            print("更新过程中禁用触摸退出")
            
            update_success = run_update_script()
            
            # 更新完成后启用触摸退出
            TOUCH_DISABLED = 0
            print("更新完成，启用触摸退出")
            
            if update_success:
                # 渐变到柔和绿色并显示成功
                display.transition_color(0x0000, COLOR_SOFT_GREEN)
                display.draw_success_screen()
                
                # 5秒倒计时，期间检查触摸事件
                for i in range(5, 0, -1):
                    if touch_monitor.check_touch_event(timeout=1):
                        print("检测到触摸事件，提前退出")
                        break
                return 0
            else:
                # 渐变到柔和红色并显示失败
                display.transition_color(0x0000, COLOR_SOFT_RED)
                display.draw_failure_screen()
                
                # 5秒倒计时，期间检查触摸事件
                for i in range(5, 0, -1):
                    if touch_monitor.check_touch_event(timeout=1):
                        print("检测到触摸事件，提前退出")
                        return 0
                continue

    except KeyboardInterrupt:
        print("\n程序被用户中断")
        return 1
    except Exception as e:
        print(f"程序运行错误: {e}")
        return 1
    finally:
        if lt6911_driver_is_unloaded:
            load_lt6911_driver()
        # 清理资源
        display.close()
        touch_monitor.close()
        print("程序退出")

if __name__ == "__main__":
    sys.exit(main())