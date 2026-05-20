# MicroPython `machine` Module — C Source Reference

## What This Is

The user writes MicroPython for a **Raspberry Pi Pico W (RP2040 + CYW43 WiFi/BLE chip)** using Thonny IDE. The MicroPython firmware's underlying C source code is **not in this repository** — it is indexed in a separate repository and accessible to the agent via the **engramd MCP server**.

## Why the C Source Matters

When the user writes:

```python
from machine import Pin, SPI, I2C, PWM, ADC, UART, Timer
```

…they are calling into C functions compiled into the MicroPython firmware on the Pico W. There is no `machine.py` anywhere — the module is implemented entirely in C. Understanding the C source helps the agent give better advice about timing, pin multiplexing, DMA, buffer sizes, hardware limitations, and edge cases that are invisible from the Python API alone.

## How to Access the C Source (engramd)

The MicroPython C source code (v1.28.0, rp2 port) is indexed and searchable via the **engramd MCP server**. Use the following engramd tools to look up implementation details:

- **`search_semantic`** — Find code by concept. Example: "how does SPI initialization work on rp2", "PWM frequency calculation", "CYW43 WiFi connection handling"
- **`search_keyword`** — Find exact terms. Example: `machine_spi_init`, `gpio_set_function`, `cyw43_wifi_connect`
- **`go_to_definition`** — Jump to a function/class definition. Example: find where `machine_pin_obj_init_helper` is defined
- **`find_references`** — Find all usages of a symbol
- **`get_file_context`** — Read a specific file after identifying it via search
- **`list_files`** — Browse the repository structure
- **`list_repos`** — Confirm which repos are indexed

**Always search engramd first** when you need to understand what a Python call does at the hardware level, check pin constraints, verify default values, or debug hardware behavior.

## Architecture Overview

```
User's .py code (runs on Pico W)
        │
        ▼
MicroPython interpreter (C, on Pico W firmware)
        │
        ├──▶ machine module (C, frozen into firmware)
        │           │
        │           ▼
        │    RP2040 hardware registers
        │
        └──▶ network / CYW43 driver (C, frozen into firmware)
                    │
                    ▼
             CYW43 WiFi/BLE chip (connected via SPI on GP23-GP25, GP29)
```

The Python API is a thin wrapper. The real behavior — defaults, constraints, error handling — lives in the C source.

## Key Files Map

When the user uses a Python class, search engramd for the corresponding C implementation:

| Python usage             | C source file to search for            |
|--------------------------|----------------------------------------|
| `machine.Pin`            | `machine_pin.c` in `ports/rp2/`       |
| `machine.SPI`            | `machine_spi.c` in `ports/rp2/`       |
| `machine.I2C`            | `machine_i2c.c` in `ports/rp2/`       |
| `machine.ADC`            | `machine_adc.c` in `ports/rp2/`       |
| `machine.PWM`            | `machine_pwm.c` in `ports/rp2/`       |
| `machine.UART`           | `machine_uart.c` in `ports/rp2/`      |
| `machine.Timer`          | `machine_timer.c` in `ports/rp2/`     |
| `machine.WDT`            | `machine_wdt.c` in `ports/rp2/`       |
| `machine.SoftI2C`        | `machine_i2c.c` in `extmod/`          |
| `machine.SoftSPI`        | `machine_spi.c` in `extmod/`          |
| `rp2.PIO`, `StateMachine`| `rp2_pio.c` in `ports/rp2/`           |
| `rp2.DMA`                | `rp2_dma.c` in `ports/rp2/`           |
| `network.WLAN`           | `network_cyw43.c` in `extmod/`        |
| CYW43 driver             | files in `lib/cyw43-driver/`           |
| `socket`, `ssl`          | `modsocket.c`, `modtls_*.c` in `extmod/` |
| `onewire`, `neopixel`    | `modonewire.c` in `extmod/`           |
| `bluetooth`              | `modbluetooth.c` in `extmod/`, btstack in `lib/btstack/` |
| TCP/IP stack             | `lib/lwip/`                            |
| TLS/SSL crypto           | `lib/mbedtls/`                         |
| USB serial               | `lib/tinyusb/`                         |
| RP2040 hardware HAL      | `lib/pico-sdk/`                        |

Shared/cross-port machine infrastructure lives in `extmod/`.
RP2-specific implementations override or extend those in `ports/rp2/`.

## How to Use This Reference

### When helping with Pin configuration
Search engramd for `machine_pin.c` to understand:
- Valid GPIO numbers and their hardware functions
- Pin pull-up/pull-down behavior and defaults
- IRQ trigger modes and handler registration
- **Pico W reserved pins:** GP23 (CYW43 SPI CS), GP24 (CYW43 SPI data/IRQ), GP25 (CYW43 SPI CS/LED — the onboard LED is NOT directly on GP25 like regular Pico, it's behind the WiFi chip), GP29 (CYW43 SPI CLK / also VSYS ADC input)
- To control the **onboard LED on Pico W**, use `machine.Pin("LED", machine.Pin.OUT)` or `network.WLAN().config()` — NOT `Pin(25)`

### When helping with SPI/I2C
Search engramd for `machine_spi.c` / `machine_i2c.c` to understand:
- Which SPI/I2C hardware blocks exist (SPI0, SPI1, I2C0, I2C1)
- Default and valid pin assignments for each bus
- Baud rate limits and clock calculations
- DMA usage and buffer constraints

### When helping with PWM
Search engramd for `machine_pwm.c` to understand:
- PWM slice/channel mapping (two GPIOs share one slice)
- Frequency and duty cycle resolution limits
- How `freq()` and `duty_u16()` interact with the hardware divider

### When helping with ADC
Search engramd for `machine_adc.c` to understand:
- Valid ADC pins (GP26-GP28 on Pico W — **GP29 is used by CYW43 and not freely available for ADC**, unlike regular Pico)
- Internal temperature sensor (ADC channel 4)
- 12-bit resolution scaled to 16-bit (`read_u16()`)
- Conversion timing

### When helping with WiFi / networking
Search engramd for `network_cyw43.c` and the CYW43 driver to understand:
- `network.WLAN(network.STA_IF)` for station mode, `network.AP_IF` for access point
- Connection lifecycle: `active()` → `connect()` → poll `status()` / `isconnected()`
- The CYW43 chip communicates with the RP2040 via SPI using GP23-GP25, GP29 — these pins are unavailable for user GPIO
- Power management modes and their effect on latency
- The onboard LED is controlled through the CYW43 chip: use `Pin("LED")` not `Pin(25)`

### When helping with PIO
Search engramd for `rp2_pio.c` to understand:
- State machine allocation and instruction memory management
- How `asm_pio` programs are loaded and configured
- Pin mapping (set, out, sideset, in, jmp)
- IRQ flag behavior between state machines

### When helping with Bluetooth
Search engramd for `modbluetooth.c` and `lib/btstack/` to understand:
- BLE peripheral and central role setup
- GATT service and characteristic definitions
- Connection and advertising parameters

## Available Modules in Firmware

The following modules are compiled into the user's MicroPython v1.28.0 firmware (confirmed via `help('modules')`):

`_asyncio`, `asyncio/*`, `heapq`, `select`, `_boot`, `_boot_fat`, `_onewire`, `_rp2`, `_thread`, `_webrepl`, `aioble/*`, `binascii`, `bluetooth`, `builtins`, `cmath`, `collections`, `cryptolib`, `deflate`, `dht`, `ds18x20`, `errno`, `framebuf`, `gc`, `hashlib`, `io`, `json`, `lwip`, `machine`, `math`, `micropython`, `mip`, `neopixel`, `network`, `ntptime`, `onewire`, `os`, `platform`, `random`, `re`, `requests`, `select`, `socket`, `ssl`, `struct`, `sys`, `time`, `tls`, `uasyncio`, `uctypes`, `urequests`, `vfs`, `webrepl`, `webrepl_setup`, `websocket`

## Important Constraints to Remember

1. **RP2040 has 2 SPI blocks, 2 I2C blocks, 2 UART blocks, 2 PIO blocks (4 state machines each), 8 PWM slices (16 channels), 4 ADC channels + temperature sensor.**
2. **Pico W pin reservations:** GP23, GP24, GP25, and GP29 are used internally by the CYW43 WiFi chip and are **not available for general use**. The onboard LED is behind the CYW43 — use `Pin("LED")`, not `Pin(25)`.
3. **GPIO pins are multiplexed** — one pin can be SPI, I2C, UART, PWM, or PIO, but only one function at a time. The C source shows `gpio_set_function()` calls that reveal which function wins.
4. **Soft variants** (`SoftI2C`, `SoftSPI`) are bit-banged in C and work on any available GPIO but are slower. Hardware variants require specific pins.
5. **The `machine` module version is the MicroPython firmware version** — there is no separate versioning. The user is on **MicroPython v1.28.0**.
6. **WiFi operations are blocking by default.** `network.WLAN.connect()` returns immediately but connection isn't instant — poll `isconnected()` or `status()` in a loop.

## When engramd Doesn't Have What You Need

If you search engramd and cannot find a relevant file, module, or library — for example a third-party MicroPython driver, an external hardware library, or a part of the MicroPython source tree that wasn't indexed — **tell the user directly**. Explain:

1. What you were looking for and why (e.g., "I tried to find the ILI9341 display driver source to check the SPI initialization sequence, but it's not indexed in engramd.")
2. That the user needs to **add the missing repository to engramd** so you can access it. This is a manual step the user must do themselves — you cannot add repos to engramd on their behalf.
3. Suggest which specific GitHub repo they should add (if you know it), so they can index it.

**Example response when a repo is missing:**

> "I can't find the `sdcard.py` driver source in engramd. If you want me to look at its internals, you'll need to add the `micropython/micropython-lib` repository (or whichever repo contains it) to your engramd MCP server. Once it's indexed, I'll be able to search through it."

The currently indexed repos should cover the core MicroPython firmware and its key dependencies (rp2 port, pico-sdk, cyw43-driver, lwip, mbedtls, tinyusb, btstack, micropython-lib). If the user installs additional third-party libraries on their Pico W (e.g., display drivers, sensor libraries, custom modules), those won't be in engramd unless explicitly added.

## What NOT to Do

- **Do not suggest importing or modifying the C files from Python.** They cannot be changed without recompiling the firmware.
- **Do not confuse this with CPython.** The `machine` module does not exist in standard Python. Code using it runs only on MicroPython on a microcontroller.
- **Do not treat files found via engramd as part of the user's project.** They are read-only reference material from the MicroPython firmware source.

## User's Setup

- **Board:** Raspberry Pi Pico W (RP2040 + CYW43439 WiFi/BLE)
- **Firmware:** MicroPython v1.28.0
- **IDE:** Thonny (connected via USB serial, COM3)
- **Connection:** Board CDC @ COM3
- **Filesystem on Pico W:** LittleFS2, with `/lib` for user-installed modules
- **Key difference from regular Pico:** GP23-GP25 and GP29 are reserved for WiFi chip, onboard LED is accessed via `Pin("LED")` not `Pin(25)`
- **C source reference:** Indexed in engramd MCP server (not stored locally in this repo)