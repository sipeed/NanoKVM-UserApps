#!/usr/bin/env python3

import subprocess
import time
from typing import Tuple

COLOR_RED = (239, 68, 68)
COLOR_GREEN = (34, 197, 94)
COLOR_BLUE = (59, 130, 246)
COLOR_GRAY = (100, 100, 100)
COLOR_WHITE = (255, 255, 255)
COLOR_DARK_BG = (30, 30, 30)
COLOR_DARK_BORDER = (60, 60, 60)
COLOR_LIGHT_GRAY = (180, 180, 180)

class SambaController:
    @staticmethod
    def check_installed() -> bool:
        try:
            result = subprocess.run(['which', 'smbd'], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    @staticmethod
    def check_running() -> bool:
        try:
            result = subprocess.run(['systemctl', 'is-active', 'smbd'], capture_output=True, text=True)
            return result.stdout.strip() == 'active'
        except:
            return False

    @staticmethod
    def start() -> bool:
        try:
            subprocess.run(['systemctl', 'enable', '--now', 'smbd'], check=True)
            subprocess.run(['systemctl', 'enable', '--now', 'nmbd'], check=True)
            subprocess.run(['systemctl', 'enable', '--now', 'wsdd2'], check=True)
            return True
        except Exception as e:
            print(f"Start failed: {e}")
            return False

    @staticmethod
    def stop() -> bool:
        try:
            subprocess.run(['systemctl', 'disable', '--now', 'smbd'], check=True)
            subprocess.run(['systemctl', 'disable', '--now', 'nmbd'], check=True)
            subprocess.run(['systemctl', 'disable', '--now', 'wsdd2'], check=True)
            return True
        except:
            return False

    @staticmethod
    def get_ip_address() -> str:
        try:
            result = subprocess.run(['ip', '-4', 'addr', 'show', 'eth0'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'inet ' in line:
                        ip = line.strip().split()[1].split('/')[0]
                        return ip

            result = subprocess.run(['hostname', '-I'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                ips = result.stdout.strip().split()
                if ips:
                    return ips[0]
        except:
            pass

        return "Unknown"

class SambaUI:
    def __init__(self, fb):
        self.fb = fb
        self.exit_button_x = 5
        self.exit_button_y = 5
        self.exit_button_w = 35
        self.exit_button_h = 25
        self.status_card_x = 10
        self.status_card_y = 40
        self.status_card_w = 145
        self.status_card_h = 110
        self.button_x = 165
        self.button_y = 55
        self.button_w = 145
        self.button_h = 60
        self.hint_x = 160
        self.hint_y = 130

    def draw_card(self, x: int, y: int, w: int, h: int):
        self.fb.draw_rect(x, y, w, h, COLOR_DARK_BG, auto_swap=False)
        self.fb.draw_rect(x, y, w, 2, COLOR_DARK_BORDER, auto_swap=False)
        self.fb.draw_rect(x, y, 2, h, COLOR_DARK_BORDER, auto_swap=False)
        self.fb.draw_rect(x + w - 2, y, 2, h, COLOR_DARK_BORDER, auto_swap=False)
        self.fb.draw_rect(x, y + h - 2, w, 2, COLOR_DARK_BORDER, auto_swap=False)

    def draw_status(self, status_text: str, color: Tuple[int, int, int]):
        self.draw_card(self.status_card_x, self.status_card_y, self.status_card_w, self.status_card_h)
        self.fb.draw_text(self.status_card_x + 10, self.status_card_y + 15,
                         "Samba Status", COLOR_LIGHT_GRAY, auto_swap=False)
        self.fb.draw_rect(self.status_card_x + 10, self.status_card_y + 40,
                         self.status_card_w - 20, 1, COLOR_DARK_BORDER, auto_swap=False)

        text_x = self.status_card_x + (self.status_card_w - len(status_text) * 8) // 2
        self.fb.draw_text(text_x, self.status_card_y + 55, status_text, color, auto_swap=False)

        dot_x = self.status_card_x + (self.status_card_w - 10) // 2
        dot_y = self.status_card_y + 85
        self.fb.draw_rect(dot_x, dot_y, 10, 10, color, auto_swap=False)

    def draw_button(self, text: str, pressed: bool = False):
        if pressed:
            bg_color = (40, 100, 200)
            border_color = (60, 120, 220)
        else:
            bg_color = COLOR_BLUE
            border_color = (96, 165, 250)

        self.fb.draw_rect(self.button_x, self.button_y, self.button_w, self.button_h,
                         border_color, auto_swap=False)
        self.fb.draw_rect(self.button_x + 3, self.button_y + 3,
                         self.button_w - 6, self.button_h - 6, bg_color, auto_swap=False)

        text_x = self.button_x + (self.button_w - len(text) * 8) // 2
        text_y = self.button_y + (self.button_h - 16) // 2
        self.fb.draw_text(text_x, text_y, text, COLOR_WHITE, auto_swap=False)

    def draw_hint(self, text: str):
        self.fb.draw_rect(self.hint_x, self.hint_y, self.button_w + 25, 25, (0, 0, 0), auto_swap=False)
        text_width = len(text) * 9
        text_x = self.hint_x + (self.button_w - text_width) // 2
        self.fb.draw_text(text_x, self.hint_y, text, COLOR_GRAY, auto_swap=False)

    def draw_exit_button(self, pressed: bool = False):
        if pressed:
            bg_color = (100, 40, 40)
            border_color = (150, 60, 60)
        else:
            bg_color = (60, 60, 60)
            border_color = (100, 100, 100)

        self.fb.draw_rect(self.exit_button_x, self.exit_button_y,
                         self.exit_button_w, self.exit_button_h,
                         border_color, auto_swap=False)
        self.fb.draw_rect(self.exit_button_x + 1, self.exit_button_y + 1,
                         self.exit_button_w - 2, self.exit_button_h - 2,
                         bg_color, auto_swap=False)

        arrow_color = COLOR_WHITE
        arrow_text = "<"
        text_width, text_height = self.fb.get_text_size(arrow_text)
        arrow_x = self.exit_button_x + (self.exit_button_w - text_width) // 2
        arrow_y = self.exit_button_y + (self.exit_button_h - text_height) // 2
        self.fb.draw_text(arrow_x, arrow_y, arrow_text, arrow_color, auto_swap=False)

    def is_exit_button_pressed(self, x: int, y: int) -> bool:
        return (self.exit_button_x <= x <= self.exit_button_x + self.exit_button_w and
                self.exit_button_y <= y <= self.exit_button_y + self.exit_button_h)

    def draw_install_ui(self):
        self.fb.fill_screen((0, 0, 0))
        self.draw_exit_button()
        self.draw_status("Not Installed", COLOR_RED)
        self.draw_button("Install")
        self.fb.swap_buffer()

    def draw_control_ui(self, running: bool, ip_address: str = None):
        self.fb.fill_screen((0, 0, 0))
        self.draw_exit_button()
        status_text, color, button_text = self._get_status_info(running)
        self.draw_status(status_text, color)
        self.draw_button(button_text)

        if running and ip_address:
            hint_text = f"{ip_address}"
            self.draw_hint(hint_text)

        self.fb.swap_buffer()

    def update_control_status(self, running: bool, ip_address: str = None):
        self.fb.draw_rect(self.status_card_x + 10, self.status_card_y + 50,
                         self.status_card_w - 20, 55, COLOR_DARK_BG, auto_swap=False)

        status_text, color, button_text = self._get_status_info(running)
        text_x = self.status_card_x + (self.status_card_w - len(status_text) * 8) // 2
        self.fb.draw_text(text_x, self.status_card_y + 55, status_text, color, auto_swap=False)
        dot_x = self.status_card_x + (self.status_card_w - 10) // 2
        dot_y = self.status_card_y + 85
        self.fb.draw_rect(dot_x, dot_y, 10, 10, color, auto_swap=False)
        self.draw_button(button_text)

        if running and ip_address:
            hint_text = f"{ip_address}"
            self.draw_hint(hint_text)
        else:
            self.fb.draw_rect(self.hint_x, self.hint_y, self.button_w + 25, 25, (0, 0, 0), auto_swap=False)

        self.fb.swap_buffer()

    def _get_status_info(self, running: bool) -> Tuple[str, Tuple[int, int, int], str]:
        if running:
            return "Run", COLOR_GREEN, "Stop"
        else:
            return "Stop", COLOR_RED, "Start"

    def is_button_pressed(self, x: int, y: int) -> bool:
        return (self.button_x <= x <= self.button_x + self.button_w and
                self.button_y <= y <= self.button_y + self.button_h)

class SambaInstaller:
    COLOR_BG = (0, 0, 0)
    COLOR_TEXT_PRIMARY = (240, 240, 240)
    COLOR_TEXT_SECONDARY = (150, 150, 150)
    COLOR_SUCCESS = (34, 197, 94)
    COLOR_ERROR = (239, 68, 68)
    COLOR_WARNING = (251, 191, 36)
    COLOR_PROGRESS_BG = (40, 40, 40)
    COLOR_PROGRESS_FILL = (59, 130, 246)
    COLOR_PROGRESS_BORDER = (80, 80, 80)

    def __init__(self, fb):
        self.fb = fb
        self.progress_bar_height = 22
        self.progress_bar_margin = 20
        self.last_message = ""
        self.last_progress = -1
        self.percent_y = 0
        self.percent_sign_x = 0
        self.bar_x = 0
        self.bar_y = 0
        self.bar_width = 0

    def clear_screen(self, color=None):
        if color is None:
            color = self.COLOR_BG
        self.fb.fill_screen(color)

    def show_progress(self, message, progress=0, color=None):
        if color is None:
            color = self.COLOR_TEXT_PRIMARY

        print(f"{message} {progress}%")

        if message != self.last_message:
            self.clear_screen()

            msg_width, msg_height = self.fb.get_text_size(message)
            center_x = (self.fb.width - msg_width) // 2
            center_y = (self.fb.height - msg_height - self.progress_bar_height - 50) // 2
            self.fb.draw_text(center_x, center_y, message, color, auto_swap=False)

            self.percent_y = center_y + msg_height + 15
            self.bar_y = self.percent_y + 35
            self.bar_width = self.fb.width - 2 * self.progress_bar_margin
            self.bar_x = self.progress_bar_margin

            self.fb.draw_rect(self.bar_x - 2, self.bar_y - 2,
                             self.bar_width + 4, self.progress_bar_height + 4,
                             self.COLOR_PROGRESS_BORDER, auto_swap=False)
            self.fb.draw_rect(self.bar_x, self.bar_y,
                             self.bar_width, self.progress_bar_height,
                             self.COLOR_PROGRESS_BG, auto_swap=False)

            max_num_width, _ = self.fb.get_text_size("100")
            self.percent_sign_x = (self.fb.width + max_num_width) // 2
            self.fb.draw_text(self.percent_sign_x, self.percent_y, "%",
                             self.COLOR_TEXT_SECONDARY, auto_swap=False)

            self.last_message = message
            self.last_progress = -1

        if progress != self.last_progress:
            num_text = str(progress)
            max_num_width, num_height = self.fb.get_text_size("100")
            num_width, _ = self.fb.get_text_size(num_text)
            clear_x = (self.fb.width - max_num_width) // 2 - 5

            self.fb.draw_rect(clear_x, self.percent_y, max_num_width + 5, num_height,
                             self.COLOR_BG, auto_swap=False)

            if progress >= 100:
                num_color = color if color != self.COLOR_TEXT_PRIMARY else self.COLOR_SUCCESS
            else:
                num_color = self.COLOR_TEXT_PRIMARY

            self.fb.draw_text(self.percent_sign_x - num_width, self.percent_y, num_text,
                             num_color, auto_swap=False)

            self.fb.draw_rect(self.bar_x, self.bar_y,
                             self.bar_width, self.progress_bar_height,
                             self.COLOR_PROGRESS_BG, auto_swap=False)

            if progress > 0:
                fill_width = int(self.bar_width * progress / 100)
                if progress >= 100:
                    fill_color = color if color != self.COLOR_TEXT_PRIMARY else self.COLOR_SUCCESS
                else:
                    fill_color = self.COLOR_PROGRESS_FILL

                self.fb.draw_rect(self.bar_x, self.bar_y,
                                 fill_width, self.progress_bar_height,
                                 fill_color, auto_swap=False)

            self.last_progress = progress

        self.fb.swap_buffer()

    def install_samba(self):
        for i in range(0, 101, 10):
            self.show_progress("Starting install...", i)
            time.sleep(0.1)
        time.sleep(0.5)

        for i in range(0, 51, 10):
            self.show_progress("Checking status...", i)
            time.sleep(0.1)

        try:
            result = subprocess.run(['which', 'smbd'],
                                  capture_output=True,
                                  text=True,
                                  timeout=5)
            if result.returncode == 0:
                self.show_progress("Checking status...", 100, self.COLOR_SUCCESS)
                time.sleep(1)
                self.show_progress("Samba installed!", 100, self.COLOR_SUCCESS)
                time.sleep(2)
                return True
        except Exception as e:
            print(f"Check failed: {e}")

        self.show_progress("Checking status...", 100)
        time.sleep(0.5)

        try:
            for i in range(0, 31, 10):
                self.show_progress("Updating packages...", i)
                time.sleep(0.1)

            result = subprocess.run(['apt-get', 'update', '-y'],
                                  capture_output=True,
                                  timeout=300)

            if result.returncode != 0:
                self.show_progress("Update failed!", 100, self.COLOR_ERROR)
                time.sleep(2)
                return False

            self.show_progress("Updating packages...", 100, self.COLOR_SUCCESS)
            time.sleep(0.5)

            for i in range(0, 21, 10):
                self.show_progress("Installing Samba...", i)
                time.sleep(0.1)

            result = subprocess.run(['apt', 'install', '-y', 'samba', 'wsdd2'],
                                  capture_output=True,
                                  timeout=300)

            if result.returncode == 0:
                self.show_progress("Installing Samba...", 100, self.COLOR_SUCCESS)
                time.sleep(1)

                try:
                    override_dir = '/etc/systemd/system/nmbd.service.d'
                    subprocess.run(['mkdir', '-p', override_dir], check=True)
                    override_content = """[Service]
TimeoutStartSec=300s
"""
                    override_file = f'{override_dir}/override.conf'
                    with open(override_file, 'w') as f:
                        f.write(override_content)
                    subprocess.run(['systemctl', 'daemon-reload'], check=True)
                    print("Created nmbd service override configuration")

                    smb_config = """
[kvm]
    comment = KVM Share
    path = /data
    browseable = yes
    writable = yes
    valid users = root
    create mask = 0664
    directory mask = 0775
"""
                    with open('/etc/samba/smb.conf', 'a') as f:
                        f.write(smb_config)
                    print("Added KVM share to smb.conf")
                    proc = subprocess.Popen(['smbpasswd', '-a', '-s', 'root'],
                                          stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
                    proc.communicate(input=b'sipeed\nsipeed\n')
                    subprocess.run(['smbpasswd', '-e', 'root'], check=True)
                    print("Created Samba user 'root' with password 'sipeed'")

                    subprocess.run(['systemctl', 'restart', 'smbd'], check=True)
                    subprocess.run(['systemctl', 'restart', 'nmbd'], check=True)
                    subprocess.run(['systemctl', 'enable', '--now', 'wsdd2'], check=True)

                except Exception as e:
                    print(f"Warning: Failed to configure Samba: {e}")

                self.show_progress("Install success!", 100, self.COLOR_SUCCESS)
                time.sleep(2)
                return True
            else:
                self.show_progress("Install failed!", 100, self.COLOR_ERROR)
                time.sleep(2)
                return False

        except subprocess.TimeoutExpired:
            self.show_progress("Timeout!", 100, self.COLOR_ERROR)
            time.sleep(2)
            return False
        except Exception as e:
            self.show_progress(f"Error: {str(e)[:15]}", 100, self.COLOR_ERROR)
            time.sleep(2)
            return False
