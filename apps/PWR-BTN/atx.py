#!/usr/bin/env python3

from framebuffer import Framebuffer
import math
import threading
import select
import time
import os

COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (128, 128, 128)
COLOR_DARK_GRAY = (64, 64, 64)
COLOR_BLACK = (0, 0, 0)
COLOR_GREEN = (80, 213, 83)
COLOR_RED = (213, 80, 80)
COLOR_BLUE = (80, 160, 213)
COLOR_LIGHT_GRAY = (160, 160, 160)

class AtxController:
    GPIO_POWER_STATUS = "/sys/class/gpio/gpio75/value"
    GPIO_EDGE_PATH = "/sys/class/gpio/gpio75/edge"
    GPIO_POWER_BUTTON = "/sys/class/gpio/gpio7/value"
    GPIO_RESET_BUTTON = "/sys/class/gpio/gpio35/value"

    def __init__(self):
        self.power_on = False
        self._running = False
        self._monitor_thread = None
        self._lock = threading.Lock()
        self._gpio_fd = None
        self._setup_gpio_edge()
        self._read_gpio_once()

    def _setup_gpio_edge(self):
        try:
            if os.path.exists(self.GPIO_EDGE_PATH):
                with open(self.GPIO_EDGE_PATH, 'w') as f:
                    f.write('both')
                print("GPIO edge configured: both")
        except Exception as e:
            print(f"Warning: Could not configure GPIO edge: {e}")

    def _read_gpio_once(self):
        try:
            if os.path.exists(self.GPIO_POWER_STATUS):
                with open(self.GPIO_POWER_STATUS, 'r') as f:
                    value = f.read().strip()
                    self.power_on = (value == '0')
                    print(f"Initial GPIO value: {value}, power_on: {self.power_on}")
            else:
                print(f"GPIO file not found: {self.GPIO_POWER_STATUS}")
        except Exception as e:
            print(f"Error reading initial GPIO: {e}")

    def start_monitoring(self):
        if self._running:
            return

        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_gpio_epoll, daemon=True)
        self._monitor_thread.start()
        print("GPIO monitoring started (epoll mode)")

    def stop_monitoring(self):
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        if self._gpio_fd:
            try:
                os.close(self._gpio_fd)
            except:
                pass
        print("GPIO monitoring stopped")

    def _monitor_gpio_epoll(self):
        try:
            self._gpio_fd = os.open(self.GPIO_POWER_STATUS, os.O_RDONLY | os.O_NONBLOCK)
            epoll = select.epoll()
            epoll = select.epoll()
            epoll.register(self._gpio_fd, select.EPOLLIN | select.EPOLLET | select.EPOLLPRI)
            os.lseek(self._gpio_fd, 0, os.SEEK_SET)
            os.read(self._gpio_fd, 64)

            print("Epoll monitoring loop started")

            while self._running:
                events = epoll.poll(timeout=1.0)

                if not self._running:
                    break

                for fd, event in events:
                    if fd == self._gpio_fd:
                        os.lseek(self._gpio_fd, 0, os.SEEK_SET)
                        value = os.read(self._gpio_fd, 64).decode().strip()
                        new_status = (value == '0')

                        with self._lock:
                            if new_status != self.power_on:
                                self.power_on = new_status
                                print(f"[EPOLL] Power status changed: {'ON' if self.power_on else 'OFF'}")

            epoll.unregister(self._gpio_fd)
            epoll.close()

        except Exception as e:
            print(f"Error in epoll monitoring: {e}")
            self._monitor_gpio_polling()

    def _monitor_gpio_polling(self):
        while self._running:
            try:
                if os.path.exists(self.GPIO_POWER_STATUS):
                    with open(self.GPIO_POWER_STATUS, 'r') as f:
                        value = f.read().strip()
                        new_status = (value == '0')

                        with self._lock:
                            if new_status != self.power_on:
                                self.power_on = new_status
                                print(f"[POLL] Power status changed: {'ON' if self.power_on else 'OFF'}")
            except Exception as e:
                print(f"Error reading GPIO: {e}")

            time.sleep(0.1)

    def get_power_status(self) -> bool:
        with self._lock:
            return self.power_on

    def _write_gpio(self, gpio_path: str, value: str):
        try:
            if os.path.exists(gpio_path):
                with open(gpio_path, 'w') as f:
                    f.write(value)
            else:
                print(f"GPIO file not found: {gpio_path}")
        except Exception as e:
            print(f"Error writing GPIO {gpio_path}: {e}")

    def press_power(self):
        print("Power button pressed")
        self._write_gpio(self.GPIO_POWER_BUTTON, '1')

    def release_power(self):
        print("Power button released")
        self._write_gpio(self.GPIO_POWER_BUTTON, '0')

    def press_reset(self):
        print("Reset button pressed")
        self._write_gpio(self.GPIO_RESET_BUTTON, '1')

    def release_reset(self):
        print("Reset button released")
        self._write_gpio(self.GPIO_RESET_BUTTON, '0')

class AtxUI:
    def __init__(self, fb: Framebuffer):
        self.fb = fb
        self.exit_button_x = 5
        self.exit_button_y = 5
        self.exit_button_w = 35
        self.exit_button_h = 25
        self.title_y = 10
        self.status_x = 20
        self.status_y = 50
        self.status_w = 80
        self.status_h = 100
        self.reset_btn_x = 120
        self.reset_btn_y = 50
        self.reset_btn_w = 80
        self.reset_btn_h = 60
        self.power_btn_x = 220
        self.power_btn_y = 50
        self.power_btn_w = 80
        self.power_btn_h = 60
        self.button_status_y = max(self.reset_btn_y + self.reset_btn_h,
                                   self.power_btn_y + self.power_btn_h) + 20

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
        title = "Power Button"
        title_w, title_h = self.fb.get_text_size(title)
        title_x = (320 - title_w) // 2

        self.fb.draw_text(title_x, self.title_y, title, COLOR_WHITE, auto_swap=False)

    def draw_power_icon(self, center_x: int, center_y: int, size: int, color: tuple):
        thickness = 3
        radius = size // 2

        for angle in range(45, 225):
            rad = math.radians(angle)
            for r in range(radius - thickness, radius):
                x = int(center_x + r * math.cos(rad))
                y = int(center_y + r * math.sin(rad))
                self.fb.draw_pixel(x, y, color)

        for angle in range(315, 405):
            rad = math.radians(angle % 360)
            for r in range(radius - thickness, radius):
                x = int(center_x + r * math.cos(rad))
                y = int(center_y + r * math.sin(rad))
                self.fb.draw_pixel(x, y, color)

        line_height = size // 2 + 2
        line_width = thickness
        line_x = center_x - line_width // 2
        line_y = center_y - radius - 2

        self.fb.draw_rect(
            line_x, line_y,
            line_width, line_height,
            color, auto_swap=False
        )

    def draw_power_status(self, power_on: bool, auto_swap: bool = True):
        status_color = COLOR_GREEN if power_on else COLOR_RED

        self.fb.draw_rect(
            self.status_x, self.status_y,
            self.status_w, self.status_h,
            COLOR_GRAY, auto_swap=False
        )

        self.fb.draw_rect(
            self.status_x + 2, self.status_y + 2,
            self.status_w - 4, self.status_h - 4,
            COLOR_DARK_GRAY, auto_swap=False
        )

        icon_size = 40
        icon_center_x = self.status_x + self.status_w // 2
        icon_center_y = self.status_y + 35

        self.draw_power_icon(icon_center_x, icon_center_y, icon_size, status_color)

        status_text = "ON" if power_on else "OFF"
        text_w, text_h = self.fb.get_text_size(status_text)
        text_x = self.status_x + (self.status_w - text_w) // 2
        text_y = icon_center_y + icon_size // 2 + 15

        self.fb.draw_text(text_x, text_y, status_text, COLOR_WHITE, auto_swap=False)

        if auto_swap:
            self.fb.swap_buffer()

    def draw_reset_button(self, pressed: bool = False):
        if pressed:
            bg_color = (100, 80, 40)
            border_color = (150, 120, 60)
        else:
            bg_color = (60, 60, 60)
            border_color = (213, 160, 80)

        self.fb.draw_rect(
            self.reset_btn_x, self.reset_btn_y,
            self.reset_btn_w, self.reset_btn_h,
            border_color, auto_swap=False
        )

        self.fb.draw_rect(
            self.reset_btn_x + 2, self.reset_btn_y + 2,
            self.reset_btn_w - 4, self.reset_btn_h - 4,
            bg_color, auto_swap=False
        )

        btn_text = "RESET"
        text_w, text_h = self.fb.get_text_size(btn_text)
        text_x = self.reset_btn_x + (self.reset_btn_w - text_w) // 2
        text_y = self.reset_btn_y + (self.reset_btn_h - text_h) // 2

        self.fb.draw_text(text_x, text_y, btn_text, COLOR_WHITE, auto_swap=False)

    def draw_power_button(self, pressed: bool = False):
        if pressed:
            bg_color = (40, 80, 100)
            border_color = (60, 120, 150)
        else:
            bg_color = (60, 60, 60)
            border_color = COLOR_BLUE

        self.fb.draw_rect(
            self.power_btn_x, self.power_btn_y,
            self.power_btn_w, self.power_btn_h,
            border_color, auto_swap=False
        )

        self.fb.draw_rect(
            self.power_btn_x + 2, self.power_btn_y + 2,
            self.power_btn_w - 4, self.power_btn_h - 4,
            bg_color, auto_swap=False
        )

        btn_text = "POWER"
        text_w, text_h = self.fb.get_text_size(btn_text)
        text_x = self.power_btn_x + (self.power_btn_w - text_w) // 2
        text_y = self.power_btn_y + (self.power_btn_h - text_h) // 2

        self.fb.draw_text(text_x, text_y, btn_text, COLOR_WHITE, auto_swap=False)

    def draw_button_status(self, status_text: str, auto_swap: bool = True):
        buttons_start_x = self.reset_btn_x
        buttons_end_x = self.power_btn_x + self.power_btn_w
        buttons_width = buttons_end_x - buttons_start_x

        clear_y = self.button_status_y
        clear_height = 20
        self.fb.draw_rect(
            buttons_start_x, clear_y,
            buttons_width, clear_height,
            COLOR_BLACK, auto_swap=False
        )

        if status_text:
            text_w, text_h = self.fb.get_text_size(status_text)
            text_x = buttons_start_x + (buttons_width - text_w) // 2
            text_y = clear_y
            self.fb.draw_text(text_x, text_y, status_text, COLOR_LIGHT_GRAY, auto_swap=False)

        if auto_swap:
            self.fb.swap_buffer()

    def draw_ui(self, power_on: bool):
        self.fb.fill_screen(COLOR_BLACK)
        self.draw_exit_button()
        self.draw_title()
        self.draw_power_status(power_on, auto_swap=False)
        self.draw_reset_button()
        self.draw_power_button()
        self.fb.swap_buffer()

    def update_power_status(self, power_on: bool):
        self.draw_power_status(power_on, auto_swap=True)

    def is_exit_button_pressed(self, x: int, y: int) -> bool:
        return (self.exit_button_x <= x <= self.exit_button_x + self.exit_button_w and
                self.exit_button_y <= y <= self.exit_button_y + self.exit_button_h)

    def is_reset_button_pressed(self, x: int, y: int) -> bool:
        return (self.reset_btn_x <= x <= self.reset_btn_x + self.reset_btn_w and
                self.reset_btn_y <= y <= self.reset_btn_y + self.reset_btn_h)

    def is_power_button_pressed(self, x: int, y: int) -> bool:
        return (self.power_btn_x <= x <= self.power_btn_x + self.power_btn_w and
                self.power_btn_y <= y <= self.power_btn_y + self.power_btn_h)
