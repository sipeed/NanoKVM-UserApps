#!/usr/bin/env python3

import struct
import os
import select
import time
from typing import Optional, Tuple, Callable

class InputDevice:
    EVENT_FORMAT = 'llHHi'
    EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

    EV_SYN = 0x00
    EV_KEY = 0x01
    EV_ABS = 0x03

    def __init__(self, device_path: str):
        self.device_path = device_path
        self.device = None

    def open(self) -> bool:
        try:
            import fcntl
            self.device = open(self.device_path, 'rb')
            flags = fcntl.fcntl(self.device, fcntl.F_GETFL)
            fcntl.fcntl(self.device, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            return True
        except Exception as e:
            print(f"Failed to open device {self.device_path}: {e}")
            return False

    def close(self):
        if self.device:
            self.device.close()
            self.device = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

class GpioKeys(InputDevice):
    KEY_UP = 103
    KEY_DOWN = 108
    KEY_LEFT = 105
    KEY_RIGHT = 106
    KEY_ENTER = 28
    KEY_ESC = 1

    KEY_NAMES = {
        103: 'UP',
        108: 'DOWN',
        105: 'LEFT',
        106: 'RIGHT',
        28: 'ENTER',
        1: 'ESC',
    }

    def __init__(self, device_path='/dev/input/by-path/platform-gpio_keys-event'):
        super().__init__(device_path)
        self._pending_key_code = None
        self._pending_key_pressed = False
        self._key_press_times = {}
        self._long_press_triggered = {}
        self._long_press_threshold = 2

    def read_event(self, timeout: float = 0) -> Optional[Tuple[str, str, bool, float, bool]]:
        if not self.device:
            return None

        try:
            for key_code, press_time in list(self._key_press_times.items()):
                if key_code not in self._long_press_triggered:
                    duration = time.time() - press_time
                    if duration >= self._long_press_threshold:
                        self._long_press_triggered[key_code] = True
                        key_name = self.KEY_NAMES.get(key_code, f'KEY_{key_code}')
                        return ('key_long_press', key_name, True, duration, True)

            if timeout is not None:
                ready, _, _ = select.select([self.device], [], [], timeout)
                if not ready:
                    return None

            while True:
                data = self.device.read(self.EVENT_SIZE)
                if len(data) < self.EVENT_SIZE:
                    return None

                _, _, ev_type, code, value = struct.unpack(self.EVENT_FORMAT, data)

                if ev_type == self.EV_KEY:
                    if value == 1:
                        self._pending_key_code = code
                        self._pending_key_pressed = True
                        self._key_press_times[code] = time.time()
                        self._long_press_triggered.pop(code, None)
                    elif value == 0:
                        self._pending_key_code = code
                        self._pending_key_pressed = False

                elif ev_type == self.EV_SYN:
                    if self._pending_key_code is not None:
                        key_code = self._pending_key_code
                        key_name = self.KEY_NAMES.get(key_code, f'KEY_{key_code}')
                        pressed = self._pending_key_pressed

                        duration = 0.0
                        is_long_press = False

                        if pressed:
                            self._pending_key_code = None
                            return ('key_press', key_name, True, 0.0, False)
                        else:
                            if key_code in self._key_press_times:
                                duration = time.time() - self._key_press_times[key_code]
                                is_long_press = key_code in self._long_press_triggered
                                del self._key_press_times[key_code]
                                self._long_press_triggered.pop(key_code, None)

                            self._pending_key_code = None
                            return ('key_release', key_name, False, duration, is_long_press)
                    return None

        except BlockingIOError:
            return None
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"Read event error: {e}")
            return None

    def wait_for_key(self, timeout: Optional[float] = None) -> Optional[str]:
        start_time = time.time() if timeout is not None else None

        while True:
            event = self.read_event(timeout=0.1)
            if event and event[0] == 'key_press':
                return event[1]

            if start_time is not None and time.time() - start_time > timeout:
                return None

class TouchScreen(InputDevice):
    ABS_X = 0x00
    ABS_Y = 0x01
    ABS_MT_POSITION_X = 0x35
    ABS_MT_POSITION_Y = 0x36
    BTN_TOUCH = 0x14a

    def __init__(self, device_path='/dev/input/by-path/platform-4857000.i2c-event', logical_width=320, logical_height=172):
        super().__init__(device_path)
        self.logical_width = logical_width
        self.logical_height = logical_height

        self.current_x = 0
        self.current_y = 0
        self.is_touching = False
        self.touch_start_x = 0
        self.touch_start_y = 0

        self._pending_touch_down = False
        self._pending_touch_up = False

    @staticmethod
    def map_coords_270(touch_x: int, touch_y: int,
                      logical_width: int = 320,
                      logical_height: int = 172) -> Tuple[int, int]:
        screen_x = max(0, min(logical_width - 1, logical_width - 1 - touch_y))
        screen_y = max(0, min(logical_height - 1, touch_x))
        return screen_x, screen_y

    def _process_event(self, ev_type: int, code: int, value: int):
        if ev_type == self.EV_ABS:
            if code in (self.ABS_X, self.ABS_MT_POSITION_X):
                self.current_x = value
            elif code in (self.ABS_Y, self.ABS_MT_POSITION_Y):
                self.current_y = value
        elif ev_type == self.EV_KEY and code == self.BTN_TOUCH:
            if value == 1:
                self.is_touching = True
                self._pending_touch_down = True
                self._pending_touch_up = False
            elif value == 0:
                self.is_touching = False
                self._pending_touch_down = False
                self._pending_touch_up = True

    def _get_synchronized_event(self) -> Optional[Tuple[str, int, int, bool]]:
        if self._pending_touch_down:
            self._pending_touch_down = False
            self.touch_start_x = self.current_x
            self.touch_start_y = self.current_y
            return ('touch_down', self.current_x, self.current_y, True)
        elif self._pending_touch_up:
            self._pending_touch_up = False
            return ('touch_up', self.current_x, self.current_y, False)
        elif self.is_touching:
            return ('touch_move', self.current_x, self.current_y, True)
        return None

    def read_event(self, timeout: float = 0) -> Optional[Tuple[str, int, int, bool]]:
        if not self.device:
            return None

        try:
            if timeout is not None:
                ready, _, _ = select.select([self.device], [], [], timeout)
                if not ready:
                    return None

            while True:
                data = self.device.read(self.EVENT_SIZE)
                if len(data) < self.EVENT_SIZE:
                    return None

                _, _, ev_type, code, value = struct.unpack(self.EVENT_FORMAT, data)

                if ev_type == self.EV_SYN:
                    return self._get_synchronized_event()

                self._process_event(ev_type, code, value)

        except BlockingIOError:
            return None
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"Read event error: {e}")
            return None

    def read_all_events(self, callback: Optional[Callable] = None):
        while True:
            event = self.read_event(timeout=0.1)
            if event and callback:
                callback(*event)

    def wait_for_touch(self, timeout: Optional[float] = None) -> Optional[Tuple[int, int]]:
        start_time = time.time() if timeout is not None else None

        while True:
            event = self.read_event(timeout=0.1)
            if event and event[0] == 'touch_down':
                return (event[1], event[2])

            if start_time is not None and time.time() - start_time > timeout:
                return None

    def is_in_rect(self, x: int, y: int, x1: int, y1: int, x2: int, y2: int) -> bool:
        return x1 <= x <= x2 and y1 <= y <= y2
