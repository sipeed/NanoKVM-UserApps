#!/usr/bin/env python3

from framebuffer import Framebuffer
from samba import SambaController, SambaUI, SambaInstaller, COLOR_BLUE, COLOR_RED, COLOR_GREEN, COLOR_WHITE
from input import TouchScreen, GpioKeys
import time
import threading

def toggle_samba_service(ui: SambaUI, running: bool) -> bool:
    controller = SambaController()

    if running:
        print("Stopping Samba...")
        ui.draw_status("Stopping...", COLOR_BLUE)
        ui.fb.swap_buffer()

        if controller.stop():
            print("Samba stopped")
            return False
        else:
            ui.draw_status("Stop Failed", COLOR_RED)
            ui.fb.swap_buffer()
            time.sleep(2)
            return running
    else:
        print("Starting Samba...")
        ui.draw_status("Starting...", COLOR_BLUE)
        ui.fb.swap_buffer()

        if controller.start():
            print("Samba started")
            ip_address = controller.get_ip_address()
            print(f"Access via: {ip_address}")
            return True
        else:
            ui.draw_status("Start Failed", COLOR_RED)
            ui.fb.swap_buffer()
            time.sleep(2)
            return running

def install_samba_package(fb: Framebuffer, ui: SambaUI) -> bool:
    print("Installing Samba...")
    ui.draw_status("Installing...", COLOR_BLUE)
    ui.fb.swap_buffer()

    installer = SambaInstaller(fb)
    success = installer.install_samba()

    if success:
        print("Samba installed successfully")
        return True
    else:
        print("Samba installation failed")
        ui.draw_install_ui()
        return False

def run_control_mode(fb: Framebuffer):
    ui = SambaUI(fb)
    controller = SambaController()
    running = controller.check_running()
    ip_address = controller.get_ip_address() if running else None
    ui.draw_control_ui(running, ip_address)
    operation_lock = threading.Lock()

    def toggle_in_thread(current_running):
        nonlocal running, ip_address
        new_running = toggle_samba_service(ui, current_running)
        if new_running != current_running:
            running = new_running
            ip_address = controller.get_ip_address() if running else None
        ui.update_control_status(running, ip_address)
        operation_lock.release()

    try:
        with TouchScreen() as touch, GpioKeys() as keys:
            print("Samba Control started")
            print(f"Current status: {'Run' if running else 'Stop'}")
            if running:
                print(f"Access via: {ip_address}")

            while True:
                touch_event = touch.read_event(timeout=0.01)
                if touch_event:
                    event_type, x, y, touching = touch_event
                    screen_x, screen_y = TouchScreen.map_coords_270(x, y)

                    if event_type == 'touch_down':
                        if ui.is_exit_button_pressed(screen_x, screen_y):
                            ui.draw_exit_button(pressed=True)
                            ui.fb.swap_buffer()
                        elif ui.is_button_pressed(screen_x, screen_y):
                            if not operation_lock.acquire(blocking=False):
                                continue

                            _, _, button_text = ui._get_status_info(running)
                            ui.draw_button(button_text, pressed=True)
                            ui.fb.swap_buffer()

                            thread = threading.Thread(target=toggle_in_thread, args=(running,))
                            thread.daemon = True
                            thread.start()

                    elif event_type == 'touch_up':
                        if ui.is_exit_button_pressed(screen_x, screen_y):
                            break

                key_event = keys.read_event(timeout=0.01)
                if key_event:
                    event_type, key_name, pressed, duration, is_long_press = key_event

                    if event_type == 'key_long_press' and key_name in ('ENTER', 'ESC'):
                        break

                    elif event_type == 'key_release' and key_name == 'ENTER' and not is_long_press:
                        if not operation_lock.acquire(blocking=False):
                            continue

                        thread = threading.Thread(target=toggle_in_thread, args=(running,))
                        thread.daemon = True
                        thread.start()

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        fb.fill_screen((0, 0, 0))

def run_install_mode(fb: Framebuffer) -> bool:
    ui = SambaUI(fb)
    ui.draw_install_ui()

    operation_lock = threading.Lock()
    should_exit = [False]
    user_cancelled = [False]

    def install_in_thread():
        success = install_samba_package(fb, ui)
        should_exit[0] = success
        operation_lock.release()

    try:
        with TouchScreen() as touch, GpioKeys() as keys:
            while True:
                touch_event = touch.read_event(timeout=0.01)
                if touch_event:
                    event_type, x, y, touching = touch_event
                    screen_x, screen_y = TouchScreen.map_coords_270(x, y)

                    if event_type == 'touch_down':
                        if ui.is_exit_button_pressed(screen_x, screen_y):
                            ui.draw_exit_button(pressed=True)
                            ui.fb.swap_buffer()
                        elif ui.is_button_pressed(screen_x, screen_y):
                            if not operation_lock.acquire(blocking=False):
                                continue

                            ui.draw_button("Install", pressed=True)
                            ui.fb.swap_buffer()

                            thread = threading.Thread(target=install_in_thread)
                            thread.daemon = True
                            thread.start()

                    elif event_type == 'touch_up':
                        if ui.is_exit_button_pressed(screen_x, screen_y):
                            user_cancelled[0] = True
                            break

                if should_exit[0]:
                    break

                key_event = keys.read_event(timeout=0.01)
                if key_event:
                    event_type, key_name, pressed, duration, is_long_press = key_event

                    if event_type == 'key_long_press' and key_name in ('ENTER', 'ESC'):
                        user_cancelled[0] = True
                        break

                    elif event_type == 'key_release' and key_name == 'ENTER' and not is_long_press:
                        if not operation_lock.acquire(blocking=False):
                            continue

                        thread = threading.Thread(target=install_in_thread)
                        thread.daemon = True
                        thread.start()

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        user_cancelled[0] = True
    finally:
        fb.fill_screen((0, 0, 0))

    return not user_cancelled[0]

def main():
    fb = Framebuffer(
        '/dev/fb0',
        rotation=270,
        font_size=16,
        font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    )

    controller = SambaController()

    while True:
        if controller.check_installed():
            run_control_mode(fb)
            break
        else:
            install_success = run_install_mode(fb)
            if not install_success:
                print("User cancelled installation")
                break

    return 0

if __name__ == '__main__':
    exit(main())
