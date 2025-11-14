#!/usr/bin/env python3

import mmap
import struct
import fcntl
from PIL import Image, ImageDraw, ImageFont

class Framebuffer:
    FBIOGET_VSCREENINFO = 0x4600
    FBIOGET_FSCREENINFO = 0x4602

    def __init__(self, fb_device='/dev/fb0', rotation=0, font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', font_size=16):
        self.fb_device = fb_device
        self.fb = None
        self.fbmem = None
        self.width = 0
        self.height = 0
        self.bpp = 0
        self.line_length = 0
        self.rotation = rotation
        self.physical_width = 0
        self.physical_height = 0
        self.font_path = font_path
        self.font_size = font_size
        self.font = None
        self.buffer = None

        self.open()

    def __del__(self):
        self.close()

    def open(self):
        try:
            self.fb = open(self.fb_device, 'r+b', buffering=0)
            vinfo_buf = bytearray(160)
            fcntl.ioctl(self.fb, self.FBIOGET_VSCREENINFO, vinfo_buf)
            self.physical_width = struct.unpack('I', vinfo_buf[0:4])[0]
            self.physical_height = struct.unpack('I', vinfo_buf[4:8])[0]
            self.bpp = struct.unpack('I', vinfo_buf[24:28])[0]
            self.line_length = self.physical_width * self.bpp // 8

            if self.rotation == 90 or self.rotation == 270:
                self.width = self.physical_height
                self.height = self.physical_width
            else:
                self.width = self.physical_width
                self.height = self.physical_height

            screensize = self.line_length * self.physical_height
            self.fbmem = mmap.mmap(self.fb.fileno(), screensize,
                                   mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)

            self.buffer = bytearray(screensize)

            try:
                self.font = ImageFont.truetype(self.font_path, self.font_size)
            except Exception as e:
                print(f"failed to load font {self.font_path}: {e}")
                self.font = ImageFont.load_default()

            return True

        except Exception as e:
            print(f"open framebuffer device failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def close(self):
        if self.fbmem:
            self.fbmem.close()
            self.fbmem = None
        if self.fb:
            self.fb.close()
            self.fb = None
        if self.buffer:
            self.buffer = None

    def swap_buffer(self):
        if not self.fbmem or not self.buffer:
            return
        self.fbmem.seek(0)
        self.fbmem.write(self.buffer)

    def set_font(self, font_path, font_size):
        try:
            self.font = ImageFont.truetype(font_path, font_size)
            self.font_path = font_path
            self.font_size = font_size
            return True
        except Exception as e:
            print(f"Failed to load font {font_path}: {e}")
            return False

    def fill_screen(self, color):
        if not self.buffer:
            print("error: framebuffer not opened")
            return

        r, g, b = color

        if self.bpp == 32:
            pixel = struct.pack('BBBB', b, g, r, 0)
        elif self.bpp == 24:
            pixel = struct.pack('BBB', b, g, r)
        elif self.bpp == 16:
            pixel_value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            pixel = struct.pack('H', pixel_value)
        else:
            print(f"unsupported bits per pixel: {self.bpp}")
            return

        bytes_per_pixel = self.bpp // 8
        for py in range(self.physical_height):
            offset = py * self.line_length
            for px in range(self.physical_width):
                pos = offset + px * bytes_per_pixel
                self.buffer[pos:pos + bytes_per_pixel] = pixel

        self.swap_buffer()

    def draw_pixel(self, x, y, color):
        if not self.buffer:
            return

        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return

        px, py = self._rotate_coords(x, y)
        if px < 0 or px >= self.physical_width or py < 0 or py >= self.physical_height:
            return

        r, g, b = color

        if self.bpp == 32:
            pixel = struct.pack('BBBB', b, g, r, 0)
        elif self.bpp == 24:
            pixel = struct.pack('BBB', b, g, r)
        elif self.bpp == 16:
            pixel_value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            pixel = struct.pack('H', pixel_value)
        else:
            return

        bytes_per_pixel = self.bpp // 8
        offset = py * self.line_length + px * bytes_per_pixel
        self.buffer[offset:offset + bytes_per_pixel] = pixel

    def draw_text(self, x, y, text, color, auto_swap=True):
        if not self.buffer or not self.font:
            return

        bbox = self.font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        offset_y = -bbox[1] if bbox[1] < 0 else 0
        img_height = text_height + offset_y

        img = Image.new('RGBA', (text_width, img_height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        draw.text((-bbox[0], -bbox[1]), text, font=self.font, fill=(*color, 255))

        pixels = img.load()
        for py in range(img_height):
            for px in range(text_width):
                pixel = pixels[px, py]
                if pixel[3] > 128:
                    self.draw_pixel(x + px, y + py, color)

        if auto_swap:
            self.swap_buffer()

    def draw_rect(self, x, y, width, height, color, auto_swap=True):
        for py in range(y, y + height):
            for px in range(x, x + width):
                self.draw_pixel(px, py, color)

        if auto_swap:
            self.swap_buffer()

    def get_text_size(self, text):
        if not self.font:
            return (0, 0)

        bbox = self.font.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if bbox[1] < 0:
            height += -bbox[1]
        return (width, height)

    def _rotate_coords(self, x, y):
        if self.rotation == 0:
            return x, y
        elif self.rotation == 90:
            return self.physical_width - 1 - y, x
        elif self.rotation == 180:
            return self.physical_width - 1 - x, self.physical_height - 1 - y
        elif self.rotation == 270:
            return y, self.physical_height - 1 - x
        else:
            return x, y

    def get_info(self):
        return {
            'device': self.fb_device,
            'width': self.width,
            'height': self.height,
            'bpp': self.bpp,
            'line_length': self.line_length,
            'is_open': self.fbmem is not None
        }

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
