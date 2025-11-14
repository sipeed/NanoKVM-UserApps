#!/usr/bin/env python3

import sys
import time
import os
import subprocess
from importlib.metadata import distributions
from framebuffer import Framebuffer

install_pyserial = False
try:
    from serial import Serial
except ImportError:
    install_pyserial = True

COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (128, 128, 128)
COLOR_DARK_GRAY = (64, 64, 64)
COLOR_BLACK = (0, 0, 0)
COLOR_BLUE = (80, 160, 213)
COLOR_GREEN = (80, 213, 83)
COLOR_YELLOW = (255, 255, 0)

def check_and_fix_serial_module(fb: Framebuffer):
    global install_pyserial
    installed_packages = {dist.metadata['Name'].lower() for dist in distributions()}

    has_serial = 'serial' in installed_packages

    if install_pyserial:
        fb.fill_screen(COLOR_BLACK)
        text = "Installing pyserial package..."
        text_w, text_h = fb.get_text_size(text)
        fb.draw_text((320 - text_w) // 2, (172 - text_h) // 2, text, COLOR_WHITE)
        fb.swap_buffer()

    if has_serial:
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "serial"],
                     check=False, capture_output=True)

    if install_pyserial:
        print("Installing pyserial...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "--force-reinstall", "pyserial"],
                              check=False, capture_output=True, text=True)
        if result.returncode == 0:
            print("Successfully installed pyserial. Restarting...")
            time.sleep(1)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print(f"Failed to install pyserial: {result.stderr}")
            time.sleep(3)
            sys.exit(1)

    return True

class UartUI:
    def __init__(self, fb: Framebuffer):
        self.fb = fb
        self.exit_button_x = 5
        self.exit_button_y = 5
        self.exit_button_w = 35
        self.exit_button_h = 25
        self.title_y = 10

        self.uart1_btn_x = 15
        self.uart1_btn_y = 45
        self.uart1_btn_w = 90
        self.uart1_btn_h = 40

        self.uart2_btn_x = 15
        self.uart2_btn_y = 95
        self.uart2_btn_w = 90
        self.uart2_btn_h = 40

        self.baud_left_btn_x = 120
        self.baud_left_btn_y = 45
        self.baud_left_btn_w = 35
        self.baud_left_btn_h = 40

        self.baud_display_x = 120
        self.baud_display_y = 95
        self.baud_display_w = 90
        self.baud_display_h = 40

        self.baud_right_btn_x = 175
        self.baud_right_btn_y = 45
        self.baud_right_btn_w = 35
        self.baud_right_btn_h = 40

        self.open_btn_x = 225
        self.open_btn_y = 45
        self.open_btn_w = 80
        self.open_btn_h = 90

        self.baud_rates = [9600, 19200, 38400, 57600, 115200, 230400]

        self.selected_uart = 1
        self.selected_baud_index = 4
        self.is_opened = False
        self.serial_port = None
        self.terminal_mode = False

        self.original_font_path = self.fb.font_path
        self.original_font_size = self.fb.font_size

        self.terminal_font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
        self.terminal_font_size = 12

        self.char_width, self.char_height = self.fb.get_text_size("W")

        from PIL import ImageFont
        try:
            terminal_font = ImageFont.truetype(self.terminal_font_path, self.terminal_font_size)
            bbox = terminal_font.getbbox("M")
            self.terminal_char_width = bbox[2] - bbox[0]
            self.terminal_char_height = bbox[3] - bbox[1] + 2
        except:
            self.terminal_char_width = self.char_width
            self.terminal_char_height = self.char_height
            self.terminal_font_path = None

        self.terminal_lines = []
        self.max_lines = 172 // self.terminal_char_height - 1
        self.max_chars_per_line = (320 - 10) // self.terminal_char_width - 1
        self.current_line = ""
        self.last_displayed_lines = []
        self.update_pending = False
        self.pending_display_lines = []

        self.data_area_y = 145
        self.data_area_w = 310
        self.data_area_h = 22

        self.data_buffer = ""
        self.max_display_chars = 50

    def draw_exit_button(self, pressed: bool = False):
        if pressed:
            bg_color = (100, 40, 40)
            border_color = (150, 60, 60)
        else:
            bg_color = (60, 60, 60)
            border_color = (100, 100, 100)

        self.fb.draw_rect(
            self.exit_button_x, self.exit_button_y,
            self.exit_button_w, self.exit_button_h,
            border_color, auto_swap=False
        )

        self.fb.draw_rect(
            self.exit_button_x + 1, self.exit_button_y + 1,
            self.exit_button_w - 2, self.exit_button_h - 2,
            bg_color, auto_swap=False
        )

        arrow_text = "<"
        text_w, text_h = self.fb.get_text_size(arrow_text)
        arrow_x = self.exit_button_x + (self.exit_button_w - text_w) // 2
        arrow_y = self.exit_button_y + (self.exit_button_h - text_h) // 2

        self.fb.draw_text(arrow_x, arrow_y, arrow_text, COLOR_WHITE, auto_swap=False)

    def draw_title(self):
        title = "UART Console"
        title_w, title_h = self.fb.get_text_size(title)
        title_x = (320 - title_w) // 2

        self.fb.draw_text(title_x, self.title_y, title, COLOR_WHITE, auto_swap=False)

    def draw_uart_buttons(self):
        uart1_selected = (self.selected_uart == 1)
        bg_color1 = COLOR_BLUE if uart1_selected else (60, 60, 60)
        border_color1 = (100, 180, 230) if uart1_selected else COLOR_GRAY

        self.fb.draw_rect(self.uart1_btn_x, self.uart1_btn_y,
                         self.uart1_btn_w, self.uart1_btn_h,
                         border_color1, auto_swap=False)
        self.fb.draw_rect(self.uart1_btn_x + 2, self.uart1_btn_y + 2,
                         self.uart1_btn_w - 4, self.uart1_btn_h - 4,
                         bg_color1, auto_swap=False)

        text = "UART1"
        text_w, text_h = self.fb.get_text_size(text)
        text_x = self.uart1_btn_x + (self.uart1_btn_w - text_w) // 2
        text_y = self.uart1_btn_y + (self.uart1_btn_h - text_h) // 2
        self.fb.draw_text(text_x, text_y, text, COLOR_WHITE, auto_swap=False)

        uart2_selected = (self.selected_uart == 2)
        bg_color2 = COLOR_BLUE if uart2_selected else (60, 60, 60)
        border_color2 = (100, 180, 230) if uart2_selected else COLOR_GRAY

        self.fb.draw_rect(self.uart2_btn_x, self.uart2_btn_y,
                         self.uart2_btn_w, self.uart2_btn_h,
                         border_color2, auto_swap=False)
        self.fb.draw_rect(self.uart2_btn_x + 2, self.uart2_btn_y + 2,
                         self.uart2_btn_w - 4, self.uart2_btn_h - 4,
                         bg_color2, auto_swap=False)

        text = "UART2"
        text_w, text_h = self.fb.get_text_size(text)
        text_x = self.uart2_btn_x + (self.uart2_btn_w - text_w) // 2
        text_y = self.uart2_btn_y + (self.uart2_btn_h - text_h) // 2
        self.fb.draw_text(text_x, text_y, text, COLOR_WHITE, auto_swap=False)

    def draw_baud_buttons(self, left_pressed: bool = False, right_pressed: bool = False):
        if left_pressed:
            left_bg_color = (100, 100, 100)
            left_border_color = (140, 140, 140)
        else:
            left_bg_color = (60, 60, 60)
            left_border_color = COLOR_GRAY

        self.fb.draw_rect(self.baud_left_btn_x, self.baud_left_btn_y,
                         self.baud_left_btn_w, self.baud_left_btn_h,
                         left_border_color, auto_swap=False)
        self.fb.draw_rect(self.baud_left_btn_x + 2, self.baud_left_btn_y + 2,
                         self.baud_left_btn_w - 4, self.baud_left_btn_h - 4,
                         left_bg_color, auto_swap=False)

        left_text = "<"
        text_w, text_h = self.fb.get_text_size(left_text)
        text_x = self.baud_left_btn_x + (self.baud_left_btn_w - text_w) // 2
        text_y = self.baud_left_btn_y + (self.baud_left_btn_h - text_h) // 2
        self.fb.draw_text(text_x, text_y, left_text, COLOR_WHITE, auto_swap=False)

        if right_pressed:
            right_bg_color = (100, 100, 100)
            right_border_color = (140, 140, 140)
        else:
            right_bg_color = (60, 60, 60)
            right_border_color = COLOR_GRAY

        self.fb.draw_rect(self.baud_right_btn_x, self.baud_right_btn_y,
                         self.baud_right_btn_w, self.baud_right_btn_h,
                         right_border_color, auto_swap=False)
        self.fb.draw_rect(self.baud_right_btn_x + 2, self.baud_right_btn_y + 2,
                         self.baud_right_btn_w - 4, self.baud_right_btn_h - 4,
                         right_bg_color, auto_swap=False)

        right_text = ">"
        text_w, text_h = self.fb.get_text_size(right_text)
        text_x = self.baud_right_btn_x + (self.baud_right_btn_w - text_w) // 2
        text_y = self.baud_right_btn_y + (self.baud_right_btn_h - text_h) // 2
        self.fb.draw_text(text_x, text_y, right_text, COLOR_WHITE, auto_swap=False)

        self.fb.draw_rect(self.baud_display_x, self.baud_display_y,
                         self.baud_display_w, self.baud_display_h,
                         COLOR_GREEN, auto_swap=False)
        self.fb.draw_rect(self.baud_display_x + 2, self.baud_display_y + 2,
                         self.baud_display_w - 4, self.baud_display_h - 4,
                         COLOR_DARK_GRAY, auto_swap=False)

        baud_text = str(self.baud_rates[self.selected_baud_index])
        text_w, text_h = self.fb.get_text_size(baud_text)
        text_x = self.baud_display_x + (self.baud_display_w - text_w) // 2
        text_y = self.baud_display_y + (self.baud_display_h - text_h) // 2
        self.fb.draw_text(text_x, text_y, baud_text, COLOR_WHITE, auto_swap=False)

    def draw_open_button(self, pressed: bool = False):
        if self.is_opened:
            if pressed:
                bg_color = (150, 40, 40)
                border_color = (200, 60, 60)
            else:
                bg_color = (213, 80, 80)
                border_color = (230, 100, 100)
            btn_text = "CLOSE"
        else:
            if pressed:
                bg_color = (40, 150, 40)
                border_color = (60, 200, 60)
            else:
                bg_color = COLOR_GREEN
                border_color = (100, 230, 100)
            btn_text = "OPEN"

        self.fb.draw_rect(self.open_btn_x, self.open_btn_y,
                         self.open_btn_w, self.open_btn_h,
                         border_color, auto_swap=False)
        self.fb.draw_rect(self.open_btn_x + 2, self.open_btn_y + 2,
                         self.open_btn_w - 4, self.open_btn_h - 4,
                         bg_color, auto_swap=False)

        text_w, text_h = self.fb.get_text_size(btn_text)
        text_x = self.open_btn_x + (self.open_btn_w - text_w) // 2
        text_y = self.open_btn_y + (self.open_btn_h - text_h) // 2
        self.fb.draw_text(text_x, text_y, btn_text, COLOR_WHITE, auto_swap=False)

    def draw_data_area(self):
        self.fb.draw_rect(self.data_area_x, self.data_area_y,
                         self.data_area_w, self.data_area_h,
                         COLOR_YELLOW, auto_swap=False)

        self.fb.draw_rect(self.data_area_x + 1, self.data_area_y + 1,
                         self.data_area_w - 2, self.data_area_h - 2,
                         COLOR_BLACK, auto_swap=False)

        if self.data_buffer:
            display_text = self.data_buffer[-self.max_display_chars:]
            text_w, text_h = self.fb.get_text_size(display_text)
            text_x = self.data_area_x + 3
            text_y = self.data_area_y + (self.data_area_h - text_h) // 2
            self.fb.draw_text(text_x, text_y, display_text, COLOR_GREEN, auto_swap=False)

    def draw_terminal(self):
        self.fb.fill_screen(COLOR_BLACK)
        self.last_displayed_lines = []

        y_offset = 5
        for i, line in enumerate(self.terminal_lines):
            if i >= self.max_lines:
                break
            self.fb.draw_text(5, y_offset + i * self.terminal_char_height, line, COLOR_GREEN, auto_swap=False)

        self.fb.swap_buffer()

    def update_terminal_incremental(self, display_lines):
        has_changes = False
        changes = []

        for i in range(max(len(display_lines), len(self.last_displayed_lines))):
            current_line = display_lines[i] if i < len(display_lines) else ""
            last_line = self.last_displayed_lines[i] if i < len(self.last_displayed_lines) else None

            if current_line != last_line:
                has_changes = True
                changes.append(i)

        if not has_changes:
            return

        y_offset = 5

        for i in changes:
            current_line = display_lines[i] if i < len(display_lines) else ""

            self.fb.draw_rect(
                0, y_offset + i * self.terminal_char_height,
                320, self.terminal_char_height,
                COLOR_BLACK, auto_swap=False
            )

            if current_line:
                self.fb.draw_text(5, y_offset + i * self.terminal_char_height,
                                current_line, COLOR_GREEN, auto_swap=False)

        self.last_displayed_lines = display_lines.copy()
        self.fb.swap_buffer()

    def draw_ui(self):
        if self.terminal_mode:
            self.draw_terminal()
        else:
            self.fb.fill_screen(COLOR_BLACK)
            self.draw_title()
            self.draw_uart_buttons()
            self.draw_baud_buttons()
            self.draw_open_button()
            self.draw_exit_button()
            self.fb.swap_buffer()

    def is_exit_button_pressed(self, x: int, y: int) -> bool:
        return (self.exit_button_x <= x <= self.exit_button_x + self.exit_button_w and
                self.exit_button_y <= y <= self.exit_button_y + self.exit_button_h)

    def is_uart1_button_pressed(self, x: int, y: int) -> bool:
        return (self.uart1_btn_x <= x <= self.uart1_btn_x + self.uart1_btn_w and
                self.uart1_btn_y <= y <= self.uart1_btn_y + self.uart1_btn_h)

    def is_uart2_button_pressed(self, x: int, y: int) -> bool:
        return (self.uart2_btn_x <= x <= self.uart2_btn_x + self.uart2_btn_w and
                self.uart2_btn_y <= y <= self.uart2_btn_y + self.uart2_btn_h)

    def is_baud_left_button_pressed(self, x: int, y: int) -> bool:
        return (self.baud_left_btn_x <= x <= self.baud_left_btn_x + self.baud_left_btn_w and
                self.baud_left_btn_y <= y <= self.baud_left_btn_y + self.baud_left_btn_h)

    def is_baud_right_button_pressed(self, x: int, y: int) -> bool:
        return (self.baud_right_btn_x <= x <= self.baud_right_btn_x + self.baud_right_btn_w and
                self.baud_right_btn_y <= y <= self.baud_right_btn_y + self.baud_right_btn_h)

    def is_open_button_pressed(self, x: int, y: int) -> bool:
        return (self.open_btn_x <= x <= self.open_btn_x + self.open_btn_w and
                self.open_btn_y <= y <= self.open_btn_y + self.open_btn_h)

    def baud_rate_prev(self):
        if self.selected_baud_index > 0:
            self.selected_baud_index -= 1
            self.draw_baud_buttons()
            self.fb.swap_buffer()
            return True
        return False

    def baud_rate_next(self):
        if self.selected_baud_index < len(self.baud_rates) - 1:
            self.selected_baud_index += 1
            self.draw_baud_buttons()
            self.fb.swap_buffer()
            return True
        return False

    def get_baud_button_at(self, x: int, y: int) -> int:
        return None

    def set_uart(self, uart_num: int):
        if uart_num in (1, 2):
            self.selected_uart = uart_num
            self.draw_uart_buttons()
            self.fb.swap_buffer()

    def set_baud_rate(self, baud: int):
        if baud in self.baud_rates:
            self.selected_baud_index = self.baud_rates.index(baud)
            self.draw_baud_buttons()
            self.fb.swap_buffer()

    def get_uart(self) -> int:
        return self.selected_uart

    def get_baud_rate(self) -> int:
        return self.baud_rates[self.selected_baud_index]

    def open_serial(self):
        if self.serial_port and self.serial_port.is_open:
            return True

        try:
            port = f"/dev/ttyS{self.selected_uart}"  # UART1=/dev/ttyS1, UART2=/dev/ttyS2
            self.serial_port = Serial(
                port=port,
                baudrate=self.get_baud_rate(),
                bytesize=8,
                parity='N',
                stopbits=1,
                xonxoff=False,
                rtscts=False,
                timeout=0.1
            )
            self.is_opened = True
            self.terminal_mode = True
            self.terminal_lines = []
            self.current_line = ""
            self.data_buffer = ""

            if self.terminal_font_path:
                self.fb.set_font(self.terminal_font_path, self.terminal_font_size)

            self.draw_terminal()
            return True
        except Exception as e:
            print(f"Failed to open {port}: {e}")
            self.is_opened = False
            return False

    def close_serial(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.serial_port = None
        self.is_opened = False
        self.terminal_mode = False

        if self.terminal_font_path:
            self.fb.set_font(self.original_font_path, self.original_font_size)

        self.draw_ui()

    def toggle_open(self):
        if self.is_opened:
            self.close_serial()
        else:
            self.open_serial()
        return self.is_opened

    def get_open_status(self) -> bool:
        return self.is_opened

    def read_serial_data(self):
        if not self.serial_port or not self.serial_port.is_open:
            return

        try:
            waiting = self.serial_port.in_waiting
            if waiting > 0:
                data = self.serial_port.read(waiting)
                text = data.decode('utf-8', errors='ignore')

                if self.terminal_mode:
                    for char in text:
                        if char == '\n' or char == '\r':
                            if self.current_line:
                                self.terminal_lines.append(self.current_line)
                                self.current_line = ""
                                if len(self.terminal_lines) > self.max_lines * 2:
                                    self.terminal_lines = self.terminal_lines[-self.max_lines:]
                        else:
                            self.current_line += char
                            if len(self.current_line) >= self.max_chars_per_line:
                                self.terminal_lines.append(self.current_line)
                                self.current_line = ""

                    display_lines = self.terminal_lines[-self.max_lines:].copy()
                    if self.current_line:
                        display_lines.append(self.current_line)

                    self.update_pending = True
                    self.pending_display_lines = display_lines
                else:
                    self.data_buffer += text
                    if len(self.data_buffer) > 1000:
                        self.data_buffer = self.data_buffer[-1000:]
                    self.draw_data_area()
                    self.fb.swap_buffer()
        except Exception as e:
            print(f"Serial read error: {e}")

    def flush_terminal_update(self):
        if self.update_pending and self.terminal_mode:
            self.update_terminal_incremental(self.pending_display_lines)
            self.update_pending = False
