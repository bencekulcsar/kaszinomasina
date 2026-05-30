# Kaszinomasina
# Raspberry Pi Pico W / RP2040
# MicroPython v1.28.0
#
# Final build:
# - TFT ILI9486 480x320 SPI, RGB888/raw 24-bit image streaming
# - Picture SD mounted at /sd
# - DFPlayer Mini using global track playback command 0x03
# - 3x3 matrix keyboard + standalone A button
# - Main menu
# - Music select
# - Map select
# - Game setup
# - Skill check
# - Core game loop
#
# Required on Pico:
# - main.py
# - sdcard.py
#
# Required on picture SD:
# - booty.raw
# - crystalsong.raw
# - ungoro.raw
# or any 480x320 RGB888 .raw files in /sd root
#
# Required on DFPlayer SD:
# - track 1 = music
# - track 2 = funny soundboard
# - track 3 = laugh soundboard
# - track 4 = sad soundboard
# - track 5 = meme soundboard

from machine import Pin, SPI, UART
import time
import os
import random


# ============================================================
# Pin constants
# ============================================================

DF_TX = 0
DF_RX = 1

TFT_SCK = 2
TFT_MOSI = 3
TFT_MISO = 4
TFT_CS = 5
TFT_DC = 6
TFT_RST = 7
TFT_LED = 8

SD_SCK = 10
SD_MOSI = 11
SD_MISO = 12
SD_CS = 13

ROW0 = 14
ROW1 = 15
ROW2 = 16

COL0 = 17
COL1 = 18
COL2 = 19

BTN_A = 20


# ============================================================
# Display constants
# ============================================================

TFT_WIDTH = 480
TFT_HEIGHT = 320

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 30, 30)
GREEN = (30, 200, 30)
BLUE = (30, 80, 220)
YELLOW = (220, 220, 30)
ORANGE = (220, 140, 0)
DARK = (8, 8, 16)


# ============================================================
# Global state
# ============================================================

sd_mounted = False
dfplayer = None

current_volume = 15
selected_music_track = None
selected_map = None


# ============================================================
# Button label map
# ============================================================

KEY_MAP = {
    (0, 0): "G",
    (0, 1): "H",
    (0, 2): "I",
    (1, 0): "J",
    (1, 1): "B",
    (1, 2): "C",
    (2, 0): "D",
    (2, 1): "E",
    (2, 2): "F",
}


# ============================================================
# Hardware objects
# ============================================================

tft_spi = SPI(
    0,
    baudrate=40_000_000,
    polarity=0,
    phase=0,
    sck=Pin(TFT_SCK),
    mosi=Pin(TFT_MOSI),
    miso=Pin(TFT_MISO),
)

tft_cs = Pin(TFT_CS, Pin.OUT, value=1)
tft_dc = Pin(TFT_DC, Pin.OUT, value=0)
tft_rst = Pin(TFT_RST, Pin.OUT, value=1)
tft_led = Pin(TFT_LED, Pin.OUT, value=0)

sd_spi = SPI(
    1,
    baudrate=1_320_000,
    polarity=0,
    phase=0,
    sck=Pin(SD_SCK),
    mosi=Pin(SD_MOSI),
    miso=Pin(SD_MISO),
)

sd_cs = Pin(SD_CS, Pin.OUT, value=1)

df_uart = UART(
    0,
    baudrate=9600,
    tx=Pin(DF_TX),
    rx=Pin(DF_RX),
)

row_pins = [
    Pin(ROW0, Pin.OUT, value=1),
    Pin(ROW1, Pin.OUT, value=1),
    Pin(ROW2, Pin.OUT, value=1),
]

col_pins = [
    Pin(COL0, Pin.IN, Pin.PULL_UP),
    Pin(COL1, Pin.IN, Pin.PULL_UP),
    Pin(COL2, Pin.IN, Pin.PULL_UP),
]

btn_a = Pin(BTN_A, Pin.IN, Pin.PULL_UP)


# ============================================================
# Tiny 5x7 font
# ============================================================

FONT_5X7 = {
    " ": [0x00, 0x00, 0x00, 0x00, 0x00],
    "!": [0x00, 0x00, 0x5F, 0x00, 0x00],
    ":": [0x00, 0x36, 0x36, 0x00, 0x00],
    "-": [0x08, 0x08, 0x08, 0x08, 0x08],
    ".": [0x00, 0x60, 0x60, 0x00, 0x00],
    "'": [0x00, 0x00, 0x07, 0x00, 0x00],

    "0": [0x3E, 0x51, 0x49, 0x45, 0x3E],
    "1": [0x00, 0x42, 0x7F, 0x40, 0x00],
    "2": [0x42, 0x61, 0x51, 0x49, 0x46],
    "3": [0x21, 0x41, 0x45, 0x4B, 0x31],
    "4": [0x18, 0x14, 0x12, 0x7F, 0x10],
    "5": [0x27, 0x45, 0x45, 0x45, 0x39],
    "6": [0x3C, 0x4A, 0x49, 0x49, 0x30],
    "7": [0x01, 0x71, 0x09, 0x05, 0x03],
    "8": [0x36, 0x49, 0x49, 0x49, 0x36],
    "9": [0x06, 0x49, 0x49, 0x29, 0x1E],

    "A": [0x7E, 0x11, 0x11, 0x11, 0x7E],
    "B": [0x7F, 0x49, 0x49, 0x49, 0x36],
    "C": [0x3E, 0x41, 0x41, 0x41, 0x22],
    "D": [0x7F, 0x41, 0x41, 0x22, 0x1C],
    "E": [0x7F, 0x49, 0x49, 0x49, 0x41],
    "F": [0x7F, 0x09, 0x09, 0x09, 0x01],
    "G": [0x3E, 0x41, 0x49, 0x49, 0x7A],
    "H": [0x7F, 0x08, 0x08, 0x08, 0x7F],
    "I": [0x00, 0x41, 0x7F, 0x41, 0x00],
    "J": [0x20, 0x40, 0x41, 0x3F, 0x01],
    "K": [0x7F, 0x08, 0x14, 0x22, 0x41],
    "L": [0x7F, 0x40, 0x40, 0x40, 0x40],
    "M": [0x7F, 0x02, 0x0C, 0x02, 0x7F],
    "N": [0x7F, 0x04, 0x08, 0x10, 0x7F],
    "O": [0x3E, 0x41, 0x41, 0x41, 0x3E],
    "P": [0x7F, 0x09, 0x09, 0x09, 0x06],
    "Q": [0x3E, 0x41, 0x51, 0x21, 0x5E],
    "R": [0x7F, 0x09, 0x19, 0x29, 0x46],
    "S": [0x46, 0x49, 0x49, 0x49, 0x31],
    "T": [0x01, 0x01, 0x7F, 0x01, 0x01],
    "U": [0x3F, 0x40, 0x40, 0x40, 0x3F],
    "V": [0x1F, 0x20, 0x40, 0x20, 0x1F],
    "W": [0x7F, 0x20, 0x18, 0x20, 0x7F],
    "X": [0x63, 0x14, 0x08, 0x14, 0x63],
    "Y": [0x07, 0x08, 0x70, 0x08, 0x07],
    "Z": [0x61, 0x51, 0x49, 0x45, 0x43],
}


# ============================================================
# Generic helpers
# ============================================================

def clamp(value, minimum, maximum):
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def ceil_int_from_13x(value):
    return (value * 13 + 9) // 10


# ============================================================
# TFT low-level helpers
# ============================================================

def rgb_bytes(r, g, b):
    return bytes((r & 0xFF, g & 0xFF, b & 0xFF))


def tft_write_cmd(cmd):
    tft_cs.value(0)
    tft_dc.value(0)
    tft_spi.write(bytes((cmd,)))
    tft_cs.value(1)


def tft_write_data(data):
    tft_cs.value(0)
    tft_dc.value(1)
    tft_spi.write(data)
    tft_cs.value(1)


def tft_write_cmd_data(cmd, data=None):
    tft_write_cmd(cmd)
    if data:
        tft_write_data(data)


def tft_reset():
    tft_rst.value(1)
    time.sleep_ms(20)
    tft_rst.value(0)
    time.sleep_ms(80)
    tft_rst.value(1)
    time.sleep_ms(120)


def tft_set_window(x0, y0, x1, y1):
    if x0 < 0:
        x0 = 0
    if y0 < 0:
        y0 = 0
    if x1 >= TFT_WIDTH:
        x1 = TFT_WIDTH - 1
    if y1 >= TFT_HEIGHT:
        y1 = TFT_HEIGHT - 1

    if x1 < x0 or y1 < y0:
        return

    tft_write_cmd_data(
        0x2A,
        bytes((
            (x0 >> 8) & 0xFF,
            x0 & 0xFF,
            (x1 >> 8) & 0xFF,
            x1 & 0xFF,
        )),
    )

    tft_write_cmd_data(
        0x2B,
        bytes((
            (y0 >> 8) & 0xFF,
            y0 & 0xFF,
            (y1 >> 8) & 0xFF,
            y1 & 0xFF,
        )),
    )

    tft_write_cmd(0x2C)


# ============================================================
# TFT public functions
# ============================================================

def tft_init():
    print("tft_init()")

    tft_led.value(0)
    tft_reset()

    tft_write_cmd(0x01)
    time.sleep_ms(120)

    tft_write_cmd(0x11)
    time.sleep_ms(120)

    # Confirmed working display mode.
    # 0x66 = 18-bit / 3 bytes per pixel.
    tft_write_cmd_data(0x3A, bytes((0x66,)))

    # Confirmed landscape orientation.
    tft_write_cmd_data(0x36, bytes((0x28,)))

    tft_write_cmd(0x20)
    tft_write_cmd(0x13)
    tft_write_cmd(0x29)
    time.sleep_ms(50)

    tft_led.value(1)


def tft_fill(r, g, b):
    tft_set_window(0, 0, TFT_WIDTH - 1, TFT_HEIGHT - 1)

    pixel = rgb_bytes(r, g, b)
    chunk_pixels = 64
    chunk = pixel * chunk_pixels
    total_pixels = TFT_WIDTH * TFT_HEIGHT

    tft_cs.value(0)
    tft_dc.value(1)

    full_chunks = total_pixels // chunk_pixels
    remain = total_pixels % chunk_pixels

    for _ in range(full_chunks):
        tft_spi.write(chunk)

    if remain:
        tft_spi.write(pixel * remain)

    tft_cs.value(1)


def tft_rect(x, y, w, h, r, g, b):
    if w <= 0 or h <= 0:
        return

    x0 = x
    y0 = y
    x1 = x + w - 1
    y1 = y + h - 1

    if x1 < 0 or y1 < 0 or x0 >= TFT_WIDTH or y0 >= TFT_HEIGHT:
        return

    if x0 < 0:
        x0 = 0
    if y0 < 0:
        y0 = 0
    if x1 >= TFT_WIDTH:
        x1 = TFT_WIDTH - 1
    if y1 >= TFT_HEIGHT:
        y1 = TFT_HEIGHT - 1

    width = x1 - x0 + 1
    height = y1 - y0 + 1
    total_pixels = width * height

    tft_set_window(x0, y0, x1, y1)

    pixel = rgb_bytes(r, g, b)
    chunk_pixels = 64
    chunk = pixel * chunk_pixels

    tft_cs.value(0)
    tft_dc.value(1)

    full_chunks = total_pixels // chunk_pixels
    remain = total_pixels % chunk_pixels

    for _ in range(full_chunks):
        tft_spi.write(chunk)

    if remain:
        tft_spi.write(pixel * remain)

    tft_cs.value(1)


def tft_pixel(x, y, r, g, b):
    if x < 0 or y < 0 or x >= TFT_WIDTH or y >= TFT_HEIGHT:
        return

    tft_set_window(x, y, x, y)
    tft_write_data(rgb_bytes(r, g, b))


def tft_circle(cx, cy, radius, r, g, b):
    if radius <= 0:
        return

    rr = radius * radius

    for dy in range(-radius, radius + 1):
        y = cy + dy

        if y < 0 or y >= TFT_HEIGHT:
            continue

        dx = 0
        while dx * dx + dy * dy <= rr:
            dx += 1

        dx -= 1
        tft_rect(cx - dx, y, dx * 2 + 1, 1, r, g, b)


def tft_char(ch, x, y, r, g, b, bg_r, bg_g, bg_b, scale=1):
    ch = ch.upper()
    columns = FONT_5X7.get(ch, FONT_5X7.get(" "))

    for col_index in range(6):
        if col_index < 5:
            col_bits = columns[col_index]
        else:
            col_bits = 0x00

        for row_index in range(8):
            if col_bits & (1 << row_index):
                color = (r, g, b)
            else:
                color = (bg_r, bg_g, bg_b)

            px = x + col_index * scale
            py = y + row_index * scale

            if scale == 1:
                tft_pixel(px, py, *color)
            else:
                tft_rect(px, py, scale, scale, *color)


def tft_text(text, x, y, r, g, b, bg_r, bg_g, bg_b, scale=1):
    cursor_x = x

    for ch in text:
        if ch == "\n":
            cursor_x = x
            y += 8 * scale
            continue

        tft_char(ch, cursor_x, y, r, g, b, bg_r, bg_g, bg_b, scale)
        cursor_x += 6 * scale


def tft_text_width(text, scale=1):
    return len(text) * 6 * scale


def tft_text_center(text, y, r, g, b, bg_r, bg_g, bg_b, scale=1):
    x = (TFT_WIDTH - tft_text_width(text, scale)) // 2
    tft_text(text, x, y, r, g, b, bg_r, bg_g, bg_b, scale)


def tft_show_image(path):
    try:
        stat = os.stat(path)
        size = stat[6]
        print("Image size:", size)
    except Exception as e:
        print("Image stat error:", e)
        size = -1

    expected_size = TFT_WIDTH * TFT_HEIGHT * 3

    if size != expected_size:
        print("WARNING: image size mismatch")
        print("Expected:", expected_size, "got:", size)

    try:
        f = open(path, "rb")
    except OSError:
        print("Image not found:", path)
        return False

    print("Showing image:", path)

    tft_set_window(0, 0, TFT_WIDTH - 1, TFT_HEIGHT - 1)

    # Confirmed stable SD read chunk.
    buf_size = 480
    total_read = 0

    tft_cs.value(0)
    tft_dc.value(1)

    try:
        while True:
            data = f.read(buf_size)

            if not data:
                break

            total_read += len(data)
            tft_spi.write(data)

    except Exception as e:
        print("Image read error:", e)
        print("Bytes read before error:", total_read)
        tft_cs.value(1)
        f.close()
        return False

    tft_cs.value(1)
    f.close()

    print("Image complete, bytes read:", total_read)
    return True


# ============================================================
# SD card driver
# ============================================================

def sd_init():
    global sd_mounted
    print("sd_init()")

    if sd_mounted:
        print("SD already mounted")
        return True

    try:
        import sdcard

        try:
            os.mkdir("/sd")
            print("Created /sd mount folder")
        except OSError:
            pass

        sd = sdcard.SDCard(sd_spi, sd_cs)

        try:
            os.mount(sd, "/sd")
        except OSError as e:
            print("Mount warning:", e)

        try:
            test_list = os.listdir("/sd")
            print("SD mounted at /sd")
            print("SD root:", test_list)
            sd_mounted = True
            return True
        except OSError as e:
            print("SD mounted but not readable:", e)
            sd_mounted = False
            return False

    except Exception as e:
        print("SD mount failed:", e)
        sd_mounted = False
        return False


def sd_list_files(folder="", extensions=None):
    if not sd_mounted:
        print("SD not mounted")
        return []

    if extensions is None:
        extensions = []

    normalized_exts = []

    for ext in extensions:
        normalized_exts.append(ext.lower())

    if folder:
        folder = folder.strip("/")
        path = "/sd/" + folder
    else:
        path = "/sd"

    try:
        names = os.listdir(path)
    except OSError:
        print("Missing folder:", path)
        return []

    result = []

    for name in names:
        lower = name.lower()

        if not normalized_exts:
            result.append(name)
        else:
            for ext in normalized_exts:
                if lower.endswith(ext):
                    result.append(name)
                    break

    result.sort()
    return result


# ============================================================
# DFPlayer Mini driver
# ============================================================

class DFPlayer:
    def __init__(self, uart):
        self.uart = uart

        time.sleep_ms(300)

        while self.uart.any():
            self.uart.read()

        print("DFPlayer init")
        self.reset()
        self.select_sd()

    def _send(self, cmd, p1=0, p2=0):
        frame = bytearray(10)

        frame[0] = 0x7E
        frame[1] = 0xFF
        frame[2] = 0x06
        frame[3] = cmd & 0xFF
        frame[4] = 0x00
        frame[5] = p1 & 0xFF
        frame[6] = p2 & 0xFF

        checksum = 0 - sum(frame[1:7])
        checksum &= 0xFFFF

        frame[7] = (checksum >> 8) & 0xFF
        frame[8] = checksum & 0xFF
        frame[9] = 0xEF

        self.uart.write(frame)
        time.sleep_ms(80)

        print("DF cmd:", hex(cmd), "p1:", p1, "p2:", p2)

    def reset(self):
        print("DFPlayer reset")
        self._send(0x0C, 0, 0)
        time.sleep_ms(2000)

    def select_sd(self):
        print("DFPlayer select SD")
        self._send(0x09, 0, 2)
        time.sleep_ms(500)

    def set_volume(self, v):
        if v < 0:
            v = 0
        if v > 30:
            v = 30

        self._send(0x06, 0, v)
        print("DFPlayer volume:", v)

    def play_track(self, track):
        # Confirmed working command on this DFPlayer.
        self._send(0x03, 0, track)

    def play_folder_file(self, folder, file):
        # Compatibility wrapper.
        # Folder command 0x0F did not work on this DFPlayer clone.
        self.play_track(file)

    def stop(self):
        self._send(0x16, 0, 0)

    def loop_track(self, folder, file):
        # Best effort loop. Playback itself is confirmed via play_track().
        self.play_track(file)
        time.sleep_ms(200)
        self._send(0x08, 0, file)


def dfplayer_init():
    global dfplayer
    global current_volume

    print("dfplayer_init()")

    try:
        dfplayer = DFPlayer(df_uart)
        dfplayer.set_volume(current_volume)
        print("DFPlayer ready")
    except Exception as e:
        print("DFPlayer init failed:", e)
        dfplayer = None


# ============================================================
# Keyboard scanner
# ============================================================

def scan_keys():
    if btn_a.value() == 0:
        return "A"

    for row in row_pins:
        row.value(1)

    for row_index, row in enumerate(row_pins):
        row.value(0)
        time.sleep_us(50)

        for col_index, col in enumerate(col_pins):
            if col.value() == 0:
                row.value(1)
                return KEY_MAP.get((row_index, col_index))

        row.value(1)

    return None


def wait_key(allowed=None):
    while True:
        key = scan_keys()

        if key is not None:
            if allowed is None or key in allowed:
                time.sleep_ms(30)

                if scan_keys() == key:
                    while scan_keys() is not None:
                        time.sleep_ms(10)

                    time.sleep_ms(30)
                    return key

        time.sleep_ms(10)


def wait_key_timed(allowed=None, timeout_ms=5000):
    start = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        key = scan_keys()

        if key is not None:
            if allowed is None or key in allowed:
                time.sleep_ms(30)

                if scan_keys() == key:
                    while scan_keys() is not None:
                        time.sleep_ms(10)

                    time.sleep_ms(30)
                    return key

        time.sleep_ms(10)

    return None


# ============================================================
# Global controls
# ============================================================

def handle_volume(key):
    global current_volume

    if key == "D":
        current_volume = clamp(current_volume + 3, 0, 30)
    elif key == "E":
        current_volume = clamp(current_volume - 3, 0, 30)
    else:
        return False

    print("Volume:", current_volume)

    if dfplayer is not None:
        dfplayer.set_volume(current_volume)

    return True


def handle_soundboard(key):
    if dfplayer is None:
        return False

    if key == "G":
        track = 2
    elif key == "H":
        track = 3
    elif key == "I":
        track = 4
    elif key == "J":
        track = 5
    else:
        return False

    print("Soundboard:", key, "track:", track)
    dfplayer.play_track(track)
    return True


def wait_with_global_controls(duration_ms):
    start = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), start) < duration_ms:
        key = scan_keys()

        if key is not None:
            time.sleep_ms(30)

            if scan_keys() == key:
                while scan_keys() is not None:
                    time.sleep_ms(10)

                if handle_volume(key):
                    pass
                elif handle_soundboard(key):
                    pass

        time.sleep_ms(10)


# ============================================================
# Shared drawing helpers
# ============================================================

def draw_selected_background():
    if selected_map is not None:
        path = "/sd/" + selected_map
        ok = tft_show_image(path)

        if ok:
            return

        print("Could not draw selected map, falling back to dark")

    tft_fill(*DARK)


def draw_overlay_box():
    tft_rect(35, 55, 410, 210, 0, 0, 0)


# ============================================================
# Main menu
# ============================================================

def draw_main_menu(selected_index):
    menu_items = [
        "START GAME",
        "MAP SELECT",
        "MUSIC SELECT",
    ]

    tft_fill(*DARK)

    tft_text_center("KASZINOMASINA", 35, 255, 255, 255, 8, 8, 16, scale=4)

    y_start = 120
    item_h = 42

    for i, item in enumerate(menu_items):
        y = y_start + i * item_h

        if i == selected_index:
            tft_rect(105, y - 8, 270, 34, 30, 80, 220)
            tft_text_center(item, y, 255, 255, 255, 30, 80, 220, scale=3)
        else:
            tft_text_center(item, y, 180, 180, 180, 8, 8, 16, scale=3)

    vol_text = "VOL " + str(current_volume)
    tft_text(vol_text, 15, 290, 220, 220, 30, 8, 8, 16, scale=2)

    tft_text("B/C MOVE  A OK", 220, 290, 160, 160, 160, 8, 8, 16, scale=2)


def show_main_menu():
    selected_index = 0
    item_count = 3

    draw_main_menu(selected_index)

    while True:
        key = wait_key()

        print("Menu key:", key)

        if handle_volume(key):
            draw_main_menu(selected_index)
            continue

        if handle_soundboard(key):
            continue

        if key == "B":
            selected_index = (selected_index - 1) % item_count
            draw_main_menu(selected_index)

        elif key == "C":
            selected_index = (selected_index + 1) % item_count
            draw_main_menu(selected_index)

        elif key == "A":
            print("Menu selected:", selected_index)
            return selected_index


# ============================================================
# Music select
# ============================================================

def draw_music_select(selected_index, track_names):
    tft_fill(*DARK)

    tft_text_center("MUSIC SELECT", 30, 255, 255, 255, 8, 8, 16, scale=4)

    if not track_names:
        tft_text_center("NO MUSIC", 140, 220, 30, 30, 8, 8, 16, scale=4)
        tft_text_center("PRESS F", 210, 180, 180, 180, 8, 8, 16, scale=2)
        return

    visible_count = 5

    if selected_index < visible_count:
        start = 0
    else:
        start = selected_index - visible_count + 1

    end = start + visible_count

    if end > len(track_names):
        end = len(track_names)

    y_start = 95
    item_h = 38

    for visible_i, track_i in enumerate(range(start, end)):
        y = y_start + visible_i * item_h
        name = track_names[track_i]

        if track_i == selected_index:
            tft_rect(40, y - 7, 400, 32, 30, 80, 220)
            tft_text(name, 55, y, 255, 255, 255, 30, 80, 220, scale=2)
        else:
            tft_text(name, 55, y, 180, 180, 180, 8, 8, 16, scale=2)

    vol_text = "VOL " + str(current_volume)
    tft_text(vol_text, 15, 290, 220, 220, 30, 8, 8, 16, scale=2)

    tft_text("A OK  F BACK", 245, 290, 160, 160, 160, 8, 8, 16, scale=2)


def show_music_select():
    global selected_music_track

    # Track 1 confirmed as music.
    # Tracks 2-5 are used for soundboard.
    music_tracks = [
        ("0001.mp3", 1),
    ]

    selected_index = 0
    track_names = []

    for item in music_tracks:
        track_names.append(item[0])

    draw_music_select(selected_index, track_names)

    while True:
        key = wait_key()

        print("Music key:", key)

        if handle_volume(key):
            draw_music_select(selected_index, track_names)
            continue

        if handle_soundboard(key):
            continue

        if key == "F":
            print("Music select back")
            return

        if not music_tracks:
            continue

        if key == "B":
            selected_index = (selected_index - 1) % len(music_tracks)
            draw_music_select(selected_index, track_names)

        elif key == "C":
            selected_index = (selected_index + 1) % len(music_tracks)
            draw_music_select(selected_index, track_names)

        elif key == "A":
            filename, track_number = music_tracks[selected_index]
            selected_music_track = track_number

            print("Selected music:", filename, "track:", track_number)

            if dfplayer is not None:
                dfplayer.loop_track(1, track_number)

            tft_fill(*DARK)
            tft_text_center("NOW PLAYING", 105, 255, 255, 255, 8, 8, 16, scale=4)
            tft_text_center(filename, 165, 30, 200, 30, 8, 8, 16, scale=3)
            time.sleep_ms(1000)

            return


# ============================================================
# Map select
# ============================================================

def draw_map_select(selected_index, map_files):
    tft_fill(*DARK)

    tft_text_center("MAP SELECT", 30, 255, 255, 255, 8, 8, 16, scale=4)

    if not map_files:
        tft_text_center("NO MAPS", 140, 220, 30, 30, 8, 8, 16, scale=4)
        tft_text_center("PRESS F", 210, 180, 180, 180, 8, 8, 16, scale=2)
        return

    visible_count = 5

    if selected_index < visible_count:
        start = 0
    else:
        start = selected_index - visible_count + 1

    end = start + visible_count

    if end > len(map_files):
        end = len(map_files)

    y_start = 95
    item_h = 38

    for visible_i, map_i in enumerate(range(start, end)):
        y = y_start + visible_i * item_h
        display_name = "MAP " + str(map_i + 1)

        if map_i == selected_index:
            tft_rect(40, y - 7, 400, 32, 30, 80, 220)
            tft_text(display_name, 55, y, 255, 255, 255, 30, 80, 220, scale=2)
            filename = map_files[map_i]
            tft_text(filename, 210, y + 4, 220, 220, 220, 30, 80, 220, scale=1)
        else:
            tft_text(display_name, 55, y, 180, 180, 180, 8, 8, 16, scale=2)
            filename = map_files[map_i]
            tft_text(filename, 210, y + 4, 120, 120, 120, 8, 8, 16, scale=1)

    vol_text = "VOL " + str(current_volume)
    tft_text(vol_text, 15, 290, 220, 220, 30, 8, 8, 16, scale=2)

    tft_text("A OK  F BACK", 245, 290, 160, 160, 160, 8, 8, 16, scale=2)


def show_map_select():
    global selected_map

    map_files = sd_list_files("", [".raw"])

    print("Map files:", map_files)

    selected_index = 0

    draw_map_select(selected_index, map_files)

    while True:
        key = wait_key()

        print("Map key:", key)

        if handle_volume(key):
            draw_map_select(selected_index, map_files)
            continue

        if handle_soundboard(key):
            continue

        if key == "F":
            print("Map select back")
            return

        if not map_files:
            continue

        if key == "B":
            selected_index = (selected_index - 1) % len(map_files)
            draw_map_select(selected_index, map_files)

        elif key == "C":
            selected_index = (selected_index + 1) % len(map_files)
            draw_map_select(selected_index, map_files)

        elif key == "A":
            selected_map = map_files[selected_index]
            path = "/sd/" + selected_map

            print("Selected map:", selected_map)
            print("Preview path:", path)

            ok = tft_show_image(path)

            if not ok:
                tft_fill(40, 0, 0)
                tft_text_center("MAP ERROR", 130, 255, 255, 255, 40, 0, 0, scale=4)
                tft_text_center(selected_map, 190, 255, 255, 255, 40, 0, 0, scale=2)
                time.sleep_ms(1500)
                draw_map_select(selected_index, map_files)
                continue

            time.sleep_ms(1500)
            return


# ============================================================
# Game setup screens
# ============================================================

def setup_player_count():
    player_count = 2

    while True:
        draw_selected_background()
        draw_overlay_box()

        tft_text_center("PLAYER COUNT", 80, 255, 255, 255, 0, 0, 0, scale=4)
        tft_text_center(str(player_count), 140, 30, 200, 30, 0, 0, 0, scale=7)

        tft_text_center("B = +1   C = -1", 225, 220, 220, 30, 0, 0, 0, scale=2)
        tft_text_center("A = CONFIRM", 250, 180, 180, 180, 0, 0, 0, scale=2)

        key = wait_key()
        print("Player count key:", key)

        if handle_volume(key):
            continue

        if handle_soundboard(key):
            continue

        if key == "B":
            player_count = clamp(player_count + 1, 2, 10)

        elif key == "C":
            player_count = clamp(player_count - 1, 2, 10)

        elif key == "A":
            print("Player count selected:", player_count)
            return player_count


def setup_game_value():
    game_value = 1000

    while True:
        draw_selected_background()
        draw_overlay_box()

        tft_text_center("GAME VALUE", 80, 255, 255, 255, 0, 0, 0, scale=4)
        tft_text_center(str(game_value), 140, 30, 200, 30, 0, 0, 0, scale=5)

        tft_text_center("B = +500   C = -500", 225, 220, 220, 30, 0, 0, 0, scale=2)
        tft_text_center("A = CONFIRM", 250, 180, 180, 180, 0, 0, 0, scale=2)

        key = wait_key()
        print("Game value key:", key)

        if handle_volume(key):
            continue

        if handle_soundboard(key):
            continue

        if key == "B":
            game_value = clamp(game_value + 500, 500, 20000)

        elif key == "C":
            game_value = clamp(game_value - 500, 500, 20000)

        elif key == "A":
            print("Game value selected:", game_value)
            return game_value


# ============================================================
# Skill check
# ============================================================

def poll_early_a(duration_ms):
    start = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), start) < duration_ms:
        key = scan_keys()

        if key == "A":
            while scan_keys() is not None:
                time.sleep_ms(10)

            return True

        if key == "D" or key == "E":
            while scan_keys() is not None:
                time.sleep_ms(10)
            handle_volume(key)

        elif key == "G" or key == "H" or key == "I" or key == "J":
            while scan_keys() is not None:
                time.sleep_ms(10)
            handle_soundboard(key)

        time.sleep_ms(10)

    return False


def draw_skill_area():
    tft_rect(130, 45, 220, 230, 0, 0, 0)


def run_skill_check(current_max):
    print("Skill check start, current_max:", current_max)

    draw_skill_area()

    tft_text_center("SKILL CHECK", 55, 255, 255, 255, 0, 0, 0, scale=3)

    tft_circle(240, 160, 60, 220, 30, 30)

    red_wait = random.randint(1000, 3000)
    print("Red wait:", red_wait)

    if poll_early_a(red_wait):
        print("Too early during red")
        draw_skill_area()
        tft_text_center("TOO EARLY!", 140, 220, 30, 30, 0, 0, 0, scale=4)
        time.sleep_ms(800)
        return current_max

    tft_circle(240, 160, 60, 220, 140, 0)

    if poll_early_a(500):
        print("Too early during orange")
        draw_skill_area()
        tft_text_center("TOO EARLY!", 140, 220, 30, 30, 0, 0, 0, scale=4)
        time.sleep_ms(800)
        return current_max

    tft_circle(240, 160, 60, 30, 200, 30)

    start = time.ticks_ms()
    key = wait_key_timed(allowed=["A"], timeout_ms=5000)
    elapsed = time.ticks_diff(time.ticks_ms(), start)

    print("Skill key:", key, "elapsed:", elapsed)

    draw_skill_area()

    if key == "A" and elapsed < 300:
        new_max = ceil_int_from_13x(current_max)

        if new_max < 1:
            new_max = 1

        print("Skill FAST, new_max:", new_max)

        tft_text_center("FAST!", 120, 30, 200, 30, 0, 0, 0, scale=5)
        tft_text_center("NEW MAX " + str(new_max), 185, 255, 255, 255, 0, 0, 0, scale=3)
        time.sleep_ms(1000)

        return new_max

    if key == "A":
        print("Skill OK/SLOW")
        tft_text_center("OK", 135, 255, 255, 255, 0, 0, 0, scale=6)
        time.sleep_ms(800)
    else:
        print("Skill timeout")
        tft_text_center("SLOW", 135, 220, 140, 0, 0, 0, 0, scale=5)
        time.sleep_ms(800)

    return current_max


# ============================================================
# Core game loop
# ============================================================

def wait_for_roll_key():
    while True:
        key = wait_key()
        print("Roll wait key:", key)

        if handle_volume(key):
            return None

        if handle_soundboard(key):
            return None

        if key == "A":
            return True

        if key == "F":
            return False


def draw_game_turn(player, current_max):
    draw_selected_background()
    draw_overlay_box()

    tft_text_center("PLAYER " + str(player), 75, 255, 255, 255, 0, 0, 0, scale=4)
    tft_text_center("RANGE 1-" + str(current_max), 145, 30, 200, 30, 0, 0, 0, scale=3)
    tft_text_center("PRESS A TO ROLL", 215, 255, 255, 255, 0, 0, 0, scale=2)
    tft_text_center("F = MENU", 245, 160, 160, 160, 0, 0, 0, scale=2)


def draw_roll_result(player, result):
    draw_selected_background()
    draw_overlay_box()

    tft_text_center("PLAYER " + str(player), 90, 255, 255, 255, 0, 0, 0, scale=4)
    tft_text_center("ROLLED", 145, 255, 255, 255, 0, 0, 0, scale=3)
    tft_text_center(str(result), 190, 30, 200, 30, 0, 0, 0, scale=5)


def draw_eliminated(player):
    draw_selected_background()
    draw_overlay_box()

    tft_text_center("PLAYER " + str(player), 105, 255, 255, 255, 0, 0, 0, scale=4)
    tft_text_center("ELIMINATED!", 165, 220, 30, 30, 0, 0, 0, scale=4)


def draw_winner(player):
    draw_selected_background()
    draw_overlay_box()

    tft_text_center("GGS", 90, 30, 200, 30, 0, 0, 0, scale=8)
    tft_text_center("PLAYER " + str(player) + " WINS", 175, 255, 255, 255, 0, 0, 0, scale=3)
    tft_text_center("PRESS A FOR MENU", 235, 180, 180, 180, 0, 0, 0, scale=2)


def start_game(player_count, game_value):
    print("start_game core loop")
    print("Players:", player_count)
    print("Game value:", game_value)

    players = []

    for i in range(player_count):
        players.append(i + 1)

    original_value = game_value
    current_max = game_value
    current_player_index = 0

    while True:
        if len(players) <= 0:
            print("No players left, returning")
            return

        if current_player_index >= len(players):
            current_player_index = 0

        current_player = players[current_player_index]

        draw_game_turn(current_player, current_max)

        while True:
            roll_action = wait_for_roll_key()

            if roll_action is True:
                break

            if roll_action is False:
                print("Game cancelled to menu")
                return

            draw_game_turn(current_player, current_max)

        effective_max = current_max

        if current_max <= 10:
            effective_max = run_skill_check(current_max)

        print("Rolling 1 to", effective_max)
        result = random.randint(1, effective_max)
        print("Player", current_player, "rolled:", result)

        current_max = result

        draw_roll_result(current_player, result)
        wait_with_global_controls(2000)

        if result == 1:
            print("Player eliminated:", current_player)

            draw_eliminated(current_player)
            wait_with_global_controls(2500)

            players.pop(current_player_index)

            print("Remaining players:", players)

            if len(players) == 1:
                winner = players[0]

                draw_winner(winner)

                while True:
                    key = wait_key()
                    print("Winner screen key:", key)

                    if handle_volume(key):
                        draw_winner(winner)
                        continue

                    if handle_soundboard(key):
                        continue

                    if key == "A":
                        return

            current_max = original_value
            current_player_index = 0
            continue

        current_player_index += 1

        if current_player_index >= len(players):
            current_player_index = 0


# ============================================================
# Main navigation loop
# ============================================================

def main_loop():
    print("main_loop() final navigation")

    while True:
        selected = show_main_menu()

        if selected == 0:
            player_count = setup_player_count()
            game_value = setup_game_value()
            start_game(player_count, game_value)

        elif selected == 1:
            show_map_select()

        elif selected == 2:
            show_music_select()


# ============================================================
# Startup
# ============================================================

def show_splash():
    tft_fill(*DARK)
    tft_text_center("KASZINOMASINA", 95, 255, 255, 255, 8, 8, 16, scale=4)
    tft_text_center("LOADING...", 155, 30, 200, 30, 8, 8, 16, scale=3)


def main():
    print("Kaszinomasina starting...")

    tft_init()
    show_splash()

    if not sd_init():
        print("SD init failed")
        tft_fill(40, 0, 0)
        tft_text_center("SD ERROR", 130, 255, 255, 255, 40, 0, 0, scale=4)
        tft_text_center("CHECK CARD", 180, 255, 255, 255, 40, 0, 0, scale=3)
        return

    dfplayer_init()

    time.sleep_ms(500)

    print("Init complete")
    main_loop()


try:
    main()
except Exception as e:
    print("CRASH:", e)

    try:
        tft_fill(40, 0, 0)
        tft_text_center("CRASH", 110, 255, 255, 255, 40, 0, 0, scale=4)
        tft_text_center(str(e), 170, 255, 255, 255, 40, 0, 0, scale=2)
    except Exception:
        pass