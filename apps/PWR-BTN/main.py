#!/usr/bin/env python3

from framebuffer import Framebuffer
from input import TouchScreen, GpioKeys
from atx import AtxController, AtxUI

def run_atx_mode(fb: Framebuffer):
    controller = AtxController()
    ui = AtxUI(fb)

    controller.start_monitoring()

    ui.draw_ui(controller.get_power_status())
    last_power_status = controller.get_power_status()
    pressed_button = None

    try:
        with TouchScreen() as touch, GpioKeys() as keys:
            print("ATX Control started")

            while True:
                current_status = controller.get_power_status()
                if current_status != last_power_status:
                    last_power_status = current_status
                    ui.update_power_status(current_status)

                touch_event = touch.read_event(timeout=0.01)
                if touch_event:
                    event_type, x, y, touching = touch_event
                    screen_x, screen_y = TouchScreen.map_coords_270(x, y)

                    if event_type == 'touch_down':
                        if ui.is_exit_button_pressed(screen_x, screen_y):
                            pressed_button = 'exit'
                            ui.draw_exit_button(pressed=True)
                            ui.fb.swap_buffer()

                        elif ui.is_power_button_pressed(screen_x, screen_y):
                            pressed_button = 'power'
                            controller.press_power()
                            ui.draw_power_button(pressed=True)
                            ui.draw_button_status('Power pressed')

                        elif ui.is_reset_button_pressed(screen_x, screen_y):
                            pressed_button = 'reset'
                            controller.press_reset()
                            ui.draw_reset_button(pressed=True)
                            ui.draw_button_status('Reset pressed')

                    elif event_type == 'touch_up':
                        if pressed_button == 'exit' and ui.is_exit_button_pressed(screen_x, screen_y):
                            print("Exit button clicked")
                            break

                        elif pressed_button == 'power' and ui.is_power_button_pressed(screen_x, screen_y):
                            controller.release_power()
                            ui.draw_power_button(pressed=False)
                            ui.draw_button_status('Power released')

                        elif pressed_button == 'reset' and ui.is_reset_button_pressed(screen_x, screen_y):
                            controller.release_reset()
                            ui.draw_reset_button(pressed=False)
                            ui.draw_button_status('Reset released')

                        pressed_button = None

                key_event = keys.read_event(timeout=0.01)
                if key_event:
                    event_type, key_name, pressed, duration, is_long_press = key_event

                    if event_type == 'key_release' and key_name in ('ENTER', 'ESC'):
                        print("Key released, exiting...")
                        break

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        controller.stop_monitoring()
        fb.fill_screen((0, 0, 0))

def main():
    fb = Framebuffer(
        '/dev/fb0',
        rotation=270,
        font_size=16,
        font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    )

    run_atx_mode(fb)

    return 0


if __name__ == '__main__':
    exit(main())
