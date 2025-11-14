#!/usr/bin/env python3

from framebuffer import Framebuffer
from input import TouchScreen, GpioKeys, RotaryEncoder
from uart import UartUI, check_and_fix_serial_module

def run_uart_mode(fb: Framebuffer):
    ui = UartUI(fb)
    ui.draw_ui()
    pressed_button = None

    try:
        with TouchScreen() as touch, GpioKeys() as keys, RotaryEncoder() as rotary:
            print(f"UART Console - Selected: UART{ui.get_uart()}, Baud: {ui.get_baud_rate()}")

            while True:
                touch_event = touch.read_event(timeout=0.01)
                if touch_event:
                    event_type, x, y, touching = touch_event
                    screen_x, screen_y = TouchScreen.map_coords_270(x, y)

                    if event_type == 'touch_down':
                        if ui.terminal_mode:
                            pressed_button = 'back'
                        elif ui.is_exit_button_pressed(screen_x, screen_y):
                            pressed_button = 'exit'
                            ui.draw_exit_button(pressed=True)
                            ui.fb.swap_buffer()
                        elif ui.is_open_button_pressed(screen_x, screen_y):
                            pressed_button = 'open'
                            ui.draw_open_button(pressed=True)
                            ui.fb.swap_buffer()
                        elif ui.is_baud_left_button_pressed(screen_x, screen_y):
                            pressed_button = 'baud_left'
                            ui.draw_baud_buttons(left_pressed=True)
                            ui.fb.swap_buffer()
                        elif ui.is_baud_right_button_pressed(screen_x, screen_y):
                            pressed_button = 'baud_right'
                            ui.draw_baud_buttons(right_pressed=True)
                            ui.fb.swap_buffer()
                        else:
                            pressed_button = None

                    elif event_type == 'touch_up':
                        if pressed_button == 'back':
                            ui.close_serial()
                            print("Return to config menu")
                            pressed_button = None
                        elif pressed_button == 'exit':
                            if ui.is_exit_button_pressed(screen_x, screen_y):
                                print("Exit button clicked")
                                break
                            else:
                                ui.draw_exit_button(pressed=False)
                                ui.fb.swap_buffer()
                            pressed_button = None
                        elif pressed_button == 'open':
                            if ui.is_open_button_pressed(screen_x, screen_y):
                                opened = ui.toggle_open()
                                if opened:
                                    print(f"UART{ui.get_uart()} opened at {ui.get_baud_rate()} baud")
                                else:
                                    print(f"UART{ui.get_uart()} closed")
                            else:
                                ui.draw_open_button(pressed=False)
                                ui.fb.swap_buffer()
                            pressed_button = None
                        elif pressed_button == 'baud_left':
                            if ui.is_baud_left_button_pressed(screen_x, screen_y):
                                if ui.baud_rate_prev():
                                    print(f"Selected: UART{ui.get_uart()}, Baud: {ui.get_baud_rate()}")
                            else:
                                ui.draw_baud_buttons()
                                ui.fb.swap_buffer()
                            pressed_button = None
                        elif pressed_button == 'baud_right':
                            if ui.is_baud_right_button_pressed(screen_x, screen_y):
                                if ui.baud_rate_next():
                                    print(f"Selected: UART{ui.get_uart()}, Baud: {ui.get_baud_rate()}")
                            else:
                                ui.draw_baud_buttons()
                                ui.fb.swap_buffer()
                            pressed_button = None
                        else:
                            if ui.is_uart1_button_pressed(screen_x, screen_y):
                                ui.set_uart(1)
                                print(f"Selected: UART1, Baud: {ui.get_baud_rate()}")
                            elif ui.is_uart2_button_pressed(screen_x, screen_y):
                                ui.set_uart(2)
                                print(f"Selected: UART2, Baud: {ui.get_baud_rate()}")

                key_event = keys.read_event(timeout=0.01)
                if key_event:
                    event_type, key_name, pressed, duration, is_long_press = key_event

                    if event_type == 'key_long_press' and key_name in ('ENTER', 'ESC'):
                        if not ui.terminal_mode:
                            print("Key long pressed, exiting...")
                            break

                    if event_type == 'key_release' and key_name == 'ENTER' and not is_long_press:
                        if ui.terminal_mode:
                            ui.close_serial()
                            print("Return to config menu")
                        else:
                            opened = ui.toggle_open()
                            if opened:
                                print(f"UART{ui.get_uart()} opened at {ui.get_baud_rate()} baud")
                            else:
                                print(f"UART{ui.get_uart()} closed")

                rotary_direction = rotary.read_event(timeout=0.01)
                if rotary_direction and not ui.terminal_mode:
                    if rotary_direction > 0:
                        if ui.baud_rate_next():
                            print(f"Rotary CW: Baud: {ui.get_baud_rate()}")
                    else:
                        if ui.baud_rate_prev():
                            print(f"Rotary CCW: Baud: {ui.get_baud_rate()}")

                if ui.get_open_status():
                    ui.read_serial_data()

                if ui.terminal_mode:
                    ui.flush_terminal_update()

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        ui.close_serial()
        fb.fill_screen((0, 0, 0))

def main():
    fb = Framebuffer(
        '/dev/fb0',
        rotation=270,
        font_size=16,
        font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    )

    check_and_fix_serial_module(fb)

    run_uart_mode(fb)

    return 0

if __name__ == '__main__':
    exit(main())
