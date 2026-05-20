# main.py — ST7796S/ILI9486 display + TF card reader + DFPlayer Mini
# Raspberry Pi Pico W — OPTIMISED FOR SPEED
#
# REQUIRES: sdcard.py on the Pico
#
# Wiring:
#   Display:    SCK=GP2  MOSI=GP3  MISO=GP4  CS=GP5  DC=GP6  RST=GP7  LED=GP8(100ohm)
#   TF reader:  SCK=GP10 MOSI=GP11 MISO=GP12 CS=GP13  VCC=3.3V  GND=GND
#   DFPlayer:   RX=GP0(1kohm)  TX=GP1  VCC=3.3V  GND=GND

import machine

# Overclock Pico to 250MHz (default is 125MHz)
# If the Pico crashes or behaves strangely, lower to 200000000
machine.freq(250000000)

from machine import SPI, Pin, UART
import time, os

TFT_SCK=2;  TFT_MOSI=3;  TFT_MISO=4
TFT_CS=5;   TFT_DC=6;    TFT_RST=7;  TFT_LED=8
SD_SCK=10;  SD_MOSI=11;  SD_MISO=12;  SD_CS=13
DF_TX=0;    DF_RX=1

# 4 rows of pixels = 480 * 3 * 4 = 5760 bytes
SD_BUFFER_SIZE = 480 * 3 * 4

# SD card speed — if mount fails drop this to 4000000
SD_SPEED = 8000000


class TFT:
    WIDTH  = 480
    HEIGHT = 320

    def __init__(self):
        self.spi = SPI(0, baudrate=40000000, polarity=0, phase=0,
                       sck=Pin(TFT_SCK), mosi=Pin(TFT_MOSI), miso=Pin(TFT_MISO))
        self.cs  = Pin(TFT_CS,  Pin.OUT, value=1)
        self.dc  = Pin(TFT_DC,  Pin.OUT, value=1)
        self.rst = Pin(TFT_RST, Pin.OUT, value=1)
        self.led = Pin(TFT_LED, Pin.OUT, value=0)
        self._init()
        self.led.value(1)

    def _cmd(self, c):
        self.dc.value(0)
        self.cs.value(0)
        self.spi.write(bytes([c]))
        self.cs.value(1)

    def _dat(self, *a):
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(bytes(a))
        self.cs.value(1)

    def _init(self):
        self.rst.value(0); time.sleep_ms(20)
        self.rst.value(1); time.sleep_ms(150)
        self._cmd(0x11); time.sleep_ms(120)
        self._cmd(0x3A); self._dat(0x66)
        self._cmd(0x36); self._dat(0x28)
        self._cmd(0x29); time.sleep_ms(20)

    def _win(self, x0, y0, x1, y1):
        self._cmd(0x2A)
        self._dat(x0>>8, x0&0xFF, x1>>8, x1&0xFF)
        self._cmd(0x2B)
        self._dat(y0>>8, y0&0xFF, y1>>8, y1&0xFF)
        self._cmd(0x2C)

    def fill_screen(self, r, g, b):
        self._win(0, 0, self.WIDTH-1, self.HEIGHT-1)
        chunk = bytes([r, g, b] * 64)
        total = self.WIDTH * self.HEIGHT
        self.dc.value(1)
        self.cs.value(0)
        for _ in range(total // 64):
            self.spi.write(chunk)
        rem = total % 64
        if rem:
            self.spi.write(bytes([r, g, b] * rem))
        self.cs.value(1)

    def show_raw(self, path):
        """
        Stream a raw RGB888 file directly to display.
        No header, no conversion — just raw bytes.
        Generate on PC:
            from PIL import Image
            img = Image.open("image.bmp").convert("RGB").resize((480,320))
            open("0001.raw","wb").write(img.tobytes())
        """
        try:
            f = open(path, 'rb')
        except OSError:
            print("ERROR: cannot open", path)
            return False

        t = time.ticks_ms()
        self._win(0, 0, self.WIDTH-1, self.HEIGHT-1)
        self.dc.value(1)
        self.cs.value(0)

        buf = bytearray(SD_BUFFER_SIZE)
        while True:
            n = f.readinto(buf)
            if not n:
                break
            self.spi.write(buf if n == SD_BUFFER_SIZE else buf[:n])

        self.cs.value(1)
        f.close()
        print("Image OK in {}ms".format(time.ticks_diff(time.ticks_ms(), t)))
        return True

    def show_bmp(self, path):
        """Fallback BMP loader."""
        try:
            f = open(path, 'rb')
        except OSError:
            print("ERROR: cannot open", path); return False
        hdr = f.read(54)
        if hdr[:2] != b'BM': print("ERROR: not a BMP"); f.close(); return False
        bpp = hdr[28] | (hdr[29] << 8)
        if bpp != 24: print("ERROR: need 24-bit BMP"); f.close(); return False
        w   = hdr[18]|(hdr[19]<<8)|(hdr[20]<<16)|(hdr[21]<<24)
        h   = hdr[22]|(hdr[23]<<8)|(hdr[24]<<16)|(hdr[25]<<24)
        off = hdr[10]|(hdr[11]<<8)|(hdr[12]<<16)|(hdr[13]<<24)
        rsz = w * 3
        pad = (4 - (rsz % 4)) % 4
        print("BMP: {}x{}".format(w, h))
        t = time.ticks_ms()
        self._win(0, 0, self.WIDTH-1, self.HEIGHT-1)
        self.dc.value(1); self.cs.value(0)
        out = bytearray(rsz)
        CHUNK = 48
        for row in range(h-1, -1, -1):
            base = off + row * (rsz + pad)
            for col in range(0, w, CHUNK):
                count = min(CHUNK, w - col)
                f.seek(base + col * 3)
                raw = f.read(count * 3)
                for px in range(count):
                    i = px * 3; j = (col + px) * 3
                    out[j]=raw[i+2]; out[j+1]=raw[i+1]; out[j+2]=raw[i]
            self.spi.write(out)
        self.cs.value(1); f.close()
        print("BMP OK in {}ms".format(time.ticks_diff(time.ticks_ms(), t)))
        return True


class DFPlayer:
    def __init__(self):
        self.uart = UART(0, baudrate=9600, tx=Pin(DF_TX), rx=Pin(DF_RX),
                         bits=8, parity=None, stop=1)
        time.sleep_ms(1000)

    def _send(self, cmd, p1=0, p2=0):
        pay = [0xFF, 0x06, cmd, 0x00, p1, p2]
        cs  = ((~sum(pay)) + 1) & 0xFFFF
        self.uart.write(bytes([0x7E] + pay + [cs>>8, cs&0xFF, 0xEF]))
        time.sleep_ms(100)

    def reset(self):
        self._send(0x0C); time.sleep_ms(2000); print("DFPlayer: reset")

    def select_sd(self):
        self._send(0x09, 0, 2); time.sleep_ms(500); print("DFPlayer: SD")

    def volume(self, v):
        self._send(0x06, 0, max(0, min(30, v))); print("DFPlayer: vol", v)

    def play_track(self, n):
        self._send(0x03, 0, n); print("DFPlayer: track", n)


def mount_sd():
    try:
        import sdcard
    except ImportError:
        print("ERROR: sdcard.py missing"); return False
    try:
        spi = SPI(1, baudrate=SD_SPEED, polarity=0, phase=0,
                  sck=Pin(SD_SCK), mosi=Pin(SD_MOSI), miso=Pin(SD_MISO))
        sd = sdcard.SDCard(spi, Pin(SD_CS))
        os.mount(sd, '/sd')
        print("SD mounted at {}MHz: {}".format(SD_SPEED//1000000, os.listdir('/sd')))
        return True
    except Exception as e:
        print("SD mount failed:", e)
        print("Try lowering SD_SPEED at the top of the file")
        return False


def main():
    print("\n=== Pico W startup @ {}MHz ===\n".format(machine.freq()//1000000))

    print("[1/3] Mounting SD card...")
    sd_ok = mount_sd()

    print("\n[2/3] Init display...")
    tft = TFT()
    tft.fill_screen(0, 0, 0)

    if sd_ok:
        files = os.listdir('/sd')
        if '0001.raw' in files:
            print("Loading /sd/0001.raw ...")
            tft.show_raw('/sd/0001.raw')
        elif '0001.rgb' in files:
            print("Loading /sd/0001.rgb ...")
            tft.show_raw('/sd/0001.rgb')
        elif '0001.bmp' in files:
            print("Loading /sd/0001.bmp ...")
            tft.show_bmp('/sd/0001.bmp')
        else:
            print("No image found on SD card")
            tft.fill_screen(0, 60, 180)
    else:
        print("No SD — blue test screen")
        tft.fill_screen(0, 60, 180)

    print("\n[3/3] Init DFPlayer...")
    df = DFPlayer()
    df.reset()
    df.select_sd()
    df.volume(15)
    df.play_track(1)

    print("\n=== Done ===")


main()
