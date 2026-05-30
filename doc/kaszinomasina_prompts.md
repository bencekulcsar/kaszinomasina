# Kaszinomasina — AI Programming Prompt List

## Hardware Context (include in every prompt)
- **Board:** Raspberry Pi Pico W (RP2040), MicroPython v1.28.0
- **Display:** ILI9486 4" TFT SPI 480×320, RGB666 (18-bit)
- **Audio:** DFPlayer Mini via UART0 (TX=GP0, RX=GP1), volume range 0–30
- **SD card (images):** SPI1 (SCK=GP10, MOSI=GP11, MISO=GP12, CS=GP13)
- **Matrix keyboard:** 3×3 matrix (rows: GP14/15/16, cols: GP17/18/19) + standalone button A on GP20
- **Reserved pins:** GP23, GP24, GP25, GP29 (WiFi chip — do not use)

---

## Prompt 1 — Project Skeleton & Hardware Init

```
You are writing MicroPython for a Raspberry Pi Pico W (RP2040), MicroPython v1.28.0.

Set up the project skeleton for a game called "Kaszinomasina". Create a single main.py file with the following:

1. Import all necessary MicroPython modules (machine, time, os, random, etc.).

2. Define all pin constants:
   - DFPlayer Mini: DF_TX=0, DF_RX=1 (UART0)
   - TFT Display (SPI0): TFT_SCK=2, TFT_MOSI=3, TFT_MISO=4, TFT_CS=5, TFT_DC=6, TFT_RST=7, TFT_LED=8
   - SD card reader (SPI1): SD_SCK=10, SD_MOSI=11, SD_MISO=12, SD_CS=13
   - Matrix keyboard rows: ROW0=14, ROW1=15, ROW2=16
   - Matrix keyboard cols: COL0=17, COL1=18, COL2=19
   - Standalone button A: BTN_A=20

3. Define the button label map for the 3×3 matrix. Layout (row, col) → label:
   (0,0)=G  (0,1)=H  (0,2)=I
   (1,0)=J  (1,1)=B  (1,2)=C
   (2,0)=D  (2,1)=E  (2,2)=F

4. Initialize hardware:
   - SPI0 for TFT at 40MHz
   - SPI1 for SD card at 1.32MHz (to be increased after init)
   - UART0 for DFPlayer at 9600 baud
   - Matrix row pins as OUTPUT (default HIGH)
   - Matrix col pins as INPUT with pull-up
   - Button A as INPUT with pull-up

5. Add placeholder functions for each major module: tft_init(), sd_init(), dfplayer_init(), scan_keys(), main_loop().

6. Add a main() entry point that calls all init functions then calls main_loop().

Do not implement the logic yet — just the skeleton, constants, and hardware init.
```

---

## Prompt 2 — TFT Display Driver

```
Continue building main.py for Kaszinomasina on Raspberry Pi Pico W, MicroPython v1.28.0.

Implement the TFT display driver for the ILI9486 480×320 SPI display (RGB666, 18-bit colour). Use SPI0 already initialized on GP2–GP8.

Implement the following TFT class methods:

1. `tft_init()` — hardware reset sequence, send ILI9486 init commands, turn on backlight.

2. `tft_fill(r, g, b)` — fill the entire screen with a solid colour. Use chunked writes (e.g. 64 pixels at a time) to avoid large allocations.

3. `tft_text(text, x, y, r, g, b, bg_r, bg_g, bg_b, scale=1)` — draw text at position (x, y) using an 8×8 built-in font (use framebuf or a simple bitmap font). Text colour is (r,g,b), background colour is (bg_r,bg_g,bg_b). Support a scale multiplier.

4. `tft_rect(x, y, w, h, r, g, b)` — draw a filled rectangle.

5. `tft_circle(cx, cy, radius, r, g, b)` — draw a filled circle using the midpoint circle algorithm.

6. `tft_show_image(path)` — stream a raw RGB888 .rgb file from the SD card directly to the display using a read buffer (e.g. 4×480×3 bytes). Set window first, then stream bytes. Return False if file not found.

All drawing functions must operate directly over SPI — no framebuffer in RAM for the full screen (too large for Pico). Use DC/CS pin toggling correctly for commands vs data.
```

---

## Prompt 3 — SD Card & DFPlayer Drivers

```
Continue building main.py for Kaszinomasina on Raspberry Pi Pico W, MicroPython v1.28.0.

Implement two driver modules as classes or grouped functions:

### SD Card driver
Use the sdcard.py module (already available on the Pico filesystem) to mount the SD card on SPI1 (GP10–GP13) at /sd.

Implement:
- `sd_init()` — mounts the SD card at /sd. Prints error and returns False if it fails.
- `sd_list_files(folder, extensions)` — returns a sorted list of filenames in /sd/<folder>/ that match any of the given extensions (e.g. ['.rgb', '.bmp'] or ['.mp3']). Returns empty list if folder missing.

### DFPlayer Mini driver
Communicate via UART0 (TX=GP0, RX=GP1) at 9600 baud.

Implement a DFPlayer class with:
- `__init__()` — init UART, wait 1000ms, call reset(), then select_sd().
- `_send(cmd, p1, p2)` — send a 10-byte DFPlayer command frame with checksum.
- `reset()` — send reset command (0x0C), wait 2000ms.
- `select_sd()` — send source select command (0x09, p2=2), wait 500ms.
- `set_volume(v)` — set volume 0–30 (clamp). Command 0x06.
- `play_folder_file(folder, file)` — play a specific file in a folder. Command 0x0F, p1=folder number, p2=file number.
- `stop()` — stop playback. Command 0x16.
- `loop_track(folder, file)` — play a track and set it to loop. Use command 0x08 for single repeat after play_folder_file.

DFPlayer SD card folder structure:
- Folder 01 = background music tracks (01/0001.mp3, 01/0002.mp3, …)
- Folder 02 = funny soundboard clips
- Folder 03 = laugh soundboard clips
- Folder 04 = sad soundboard clips
- Folder 05 = meme soundboard clips
```

---

## Prompt 4 — Keyboard Scanner & Button Debounce

```
Continue building main.py for Kaszinomasina on Raspberry Pi Pico W, MicroPython v1.28.0.

Implement the keyboard input system.

### 3×3 Matrix scanner
Rows are OUTPUT pins (GP14, GP15, GP16), columns are INPUT pins with pull-up (GP17, GP18, GP19).
Scanning: pull one row LOW at a time, read all 3 columns. A pressed key reads LOW on its column.

Button label map by (row, col):
  (0,0)=G  (0,1)=H  (0,2)=I
  (1,0)=J  (1,1)=B  (1,2)=C
  (2,0)=D  (2,1)=E  (2,2)=F

Button A is a standalone INPUT with pull-up on GP20. It reads LOW when pressed.

Implement:
- `scan_keys()` — scans the full matrix plus button A. Returns the label of the first pressed key ('A','B','C','D','E','F','G','H','I','J'), or None if nothing is pressed.
- `wait_key(allowed=None)` — blocks until one of the allowed key labels is pressed (or any key if allowed=None). Returns the key label. Includes 30ms debounce and waits for key release before returning.
- `wait_key_timed(allowed=None, timeout_ms=5000)` — same as wait_key but returns None if timeout_ms elapses with no press. Used for skill check timing.

Button functions reference:
- A = main action / roll / confirm
- B = navigate up / increase value
- C = navigate down / decrease value
- D = volume up (+3 out of 30)
- E = volume down (-3 out of 30)
- F = back / cancel
- G = soundboard "funny"
- H = soundboard "laugh"
- I = soundboard "sad"
- J = soundboard "meme"
```

---

## Prompt 5 — Main Menu

```
Continue building main.py for Kaszinomasina on Raspberry Pi Pico W, MicroPython v1.28.0.

Implement the main menu screen.

The main menu has 3 options:
1. Start Game
2. Map Select
3. Music Select

Display requirements:
- Fill screen with a dark background colour.
- Draw the title "KASZINOMASINA" centred near the top.
- List the 3 menu items vertically centred on screen.
- Highlight the currently selected item (e.g. draw a filled rectangle behind it in a different colour, or use a different text colour).
- Selected index starts at 0 (Start Game).

Controls:
- B = move selection up (wraps around)
- C = move selection down (wraps around)
- A = confirm selection → navigate to the corresponding screen
- D / E = volume up / down (call dfplayer.set_volume(), update a global current_volume variable, clamp 0–30, step size 3)

Implement as a function `show_main_menu()` that loops until A is pressed, then returns the selected index (0, 1, or 2).

Volume control (D/E) must work from any menu screen — implement it as a helper `handle_volume(key)` that can be called whenever D or E is detected.

Soundboard buttons (G, H, I, J) must also work from any screen — implement `handle_soundboard(key)` that plays a random file from the corresponding DFPlayer folder (02=funny, 03=laugh, 04=sad, 05=meme). To pick a random file, maintain a count per folder (scan once at startup using sd_list_files on the DFPlayer SD, or hardcode a max count per folder — use whichever is simpler on Pico).
```

---

## Prompt 6 — Music Select Screen

```
Continue building main.py for Kaszinomasina on Raspberry Pi Pico W, MicroPython v1.28.0.

Implement the Music Select screen, reached from the main menu.

Behaviour:
- On entry, scan /sd/01/ on the DFPlayer's SD for .mp3 files using the DFPlayer folder numbering. Since the DFPlayer SD is not mounted as a filesystem (it's accessed only via UART commands), the music file list must come from a separate source. Use the Pico's SD card: scan /sd/music/ for .mp3 filenames to build the display list. The filenames are used only for display — playback uses DFPlayer folder 01 track numbers.
- Show a scrollable list of track filenames. Display up to 5 tracks at a time on screen.
- Currently selected track is highlighted.
- Show "Music Select" as a title at the top.

Controls:
- B = move selection up
- C = move selection down
- A = confirm: store selected track index (1-based) in a global selected_music_track variable, start looping that track via dfplayer.loop_track(1, track_number), update screen to show "Now playing: <filename>", then after 1 second return to main menu.
- F = go back to main menu without changing the current track.
- D / E = volume (call handle_volume).
- G / H / I / J = soundboard (call handle_soundboard).

Implement as a function `show_music_select()`.
```

---

## Prompt 7 — Map Select Screen

```
Continue building main.py for Kaszinomasina on Raspberry Pi Pico W, MicroPython v1.28.0.

Implement the Map Select screen, reached from the main menu.

Behaviour:
- On entry, scan /sd/maps/ on the Pico SD card for .rgb files using sd_list_files(). Build a list of map filenames sorted alphabetically.
- Display a scrollable list showing "Map 1", "Map 2", "Map 3" etc. (not the raw filename). Display up to 5 maps at a time.
- Show "Map Select" as a title at the top.
- Currently selected map is highlighted.

Controls:
- B = move selection up
- C = move selection down
- A = confirm: store the selected filename in a global selected_map variable. Call tft_show_image('/sd/maps/' + selected_map) to preview the map immediately as a full background. After 1500ms, redraw the map select screen and return to main menu.
- F = go back to main menu without changing the current map.
- D / E = volume.
- G / H / I / J = soundboard.

The selected_map persists as the background for all game screens until changed again here.

Implement as a function `show_map_select()`.
```

---

## Prompt 8 — Game Setup: Player Count & Game Value

```
Continue building main.py for Kaszinomasina on Raspberry Pi Pico W, MicroPython v1.28.0.

Implement the two game setup screens shown after "Start Game" is selected from the main menu.

### Screen 1: Player Count
- Display the selected map as background (call tft_show_image if selected_map is set, else fill with dark colour).
- Draw text overlay: "Player Count:" on one line, the current value (large, centred) on the next line, and "B = +1   C = -1   A = Confirm" at the bottom.
- Default value: 2. Minimum: 2. Maximum: 10.
- B increases by 1, C decreases by 1 (clamped).
- A confirms and proceeds to Screen 2.
- D/E = volume, G/H/I/J = soundboard.

### Screen 2: Game Value
- Same background logic.
- Draw text overlay: "Game Value:" on one line, current value (large, centred) below, "B = +500   C = -500   A = Confirm" at the bottom.
- Default value: 1000. Minimum: 500. Maximum: 20000. Step: 500.
- B increases by 500, C decreases by 500 (clamped).
- A confirms and calls start_game(player_count, game_value).
- D/E = volume, G/H/I/J = soundboard.

Implement as functions `setup_player_count()` → returns int, and `setup_game_value()` → returns int.
```

---

## Prompt 9 — Skill Check

```
Continue building main.py for Kaszinomasina on Raspberry Pi Pico W, MicroPython v1.28.0.

Implement the skill check mini-game as a function `run_skill_check(current_max)`.

Trigger condition: skill check only runs when current_max <= 10.

Behaviour:
1. Clear the centre of the screen (draw a dark rectangle in the middle area, roughly 200×200 pixels centred on the 480×320 display).
2. Draw a large filled circle in the centre. Sequence:
   - RED circle: draw immediately, wait a random time between 1000ms and 3000ms.
   - ORANGE circle: draw over the red one, wait 500ms.
   - GREEN circle: draw over the orange one — this is the moment the player must press A.
3. If the player presses A BEFORE the green circle appears (i.e. during red or orange phase):
   - Penalty: no modifier applied. Draw a brief "TOO EARLY!" text on screen for 800ms.
   - Return current_max unchanged.
4. Once green appears, start a timer. Use wait_key_timed(allowed=['A'], timeout_ms=5000).
   - If A is pressed in < 300ms: FAST result.
     - new_max = ceil(current_max * 1.3), minimum 1.
     - Draw "FAST! New max: <new_max>" on screen for 1000ms.
     - Return new_max.
   - If A is pressed between 300ms and 700ms, or not pressed within 5000ms: no modifier.
     - Draw "OK" or "SLOW" on screen for 800ms.
     - Return current_max unchanged.
5. Circle size: radius ~60px. Centred at (240, 160).
6. Colours: RED=(220,30,30), ORANGE=(220,140,0), GREEN=(30,200,30).

During the red and orange wait phases, poll for early button A press using scan_keys() in a loop with time.ticks_ms() to track elapsed time.

Return value: the (possibly modified) max value to use for the roll.
```

---

## Prompt 10 — Core Game Loop

```
Continue building main.py for Kaszinomasina on Raspberry Pi Pico W, MicroPython v1.28.0.

Implement the core game loop as `start_game(player_count, game_value)`.

State:
- players = list of player numbers, e.g. [1, 2, 3, ...] up to player_count.
- original_value = game_value (never changes, used to reset each round).
- current_max = game_value (changes each roll).
- current_player_index = 0, advances each turn, wraps around remaining players.

Each turn:
1. Draw background (tft_show_image if selected_map set, else dark fill).
2. Draw overlay text:
   - "Player <N>'s turn" (large, centred upper area)
   - "Range: 1 - <current_max>" (centred middle)
   - "Press A to roll" (centred lower area)
3. Wait for A button press (also handle D/E/G/H/I/J while waiting).
4. If current_max <= 10: call run_skill_check(current_max) and use the returned value as the effective max for this roll only (do not update current_max yet).
5. Roll: result = random.randint(1, effective_max).
6. Update current_max = result.
7. Display roll result:
   - Redraw background.
   - Draw "Player <N> rolled: <result>" (large, centred).
   - Wait 2000ms.
8. If result == 1:
   - Draw "Player <N> is eliminated!" centred on screen for 2500ms.
   - Remove player N from the players list.
   - If len(players) == 1:
     - Draw "GGS" large and centred.
     - Draw "Press A for menu" below it.
     - Wait for A press, then return to main menu (call show_main_menu()).
   - Else (more than 1 player remains):
     - Reset current_max = original_value.
     - Reset current_player_index to 0 (or wrap if needed).
     - Continue the loop with remaining players.
9. If result != 1:
   - Advance current_player_index to next player (wrapping).
   - Continue the loop.

D/E (volume) and G/H/I/J (soundboard) must work during the "Press A to roll" wait phase.
```

---

## Prompt 11 — Wiring It All Together & Startup

```
Continue building main.py for Kaszinomasina on Raspberry Pi Pico W, MicroPython v1.28.0.

Implement the top-level startup sequence and wire all screens together.

Global state variables to declare at the top of the file:
- selected_map = None  (set by map select screen)
- selected_music_track = None  (set by music select screen)
- current_volume = 15  (default volume, 0–30)

Startup sequence in main():
1. Call tft_init() — initialize and clear display, show a splash screen: fill screen dark, draw "KASZINOMASINA" centred, draw "Loading..." below it.
2. Call sd_init() — mount SD card. If it fails, display "SD ERROR" on screen and halt.
3. Call dfplayer_init() — init DFPlayer, set volume to current_volume.
4. Show splash for a total of 2000ms then transition to main menu.

Main navigation loop:
- call show_main_menu() → returns 0, 1, or 2.
  - 0 → setup_player_count() → setup_game_value() → start_game()
  - 1 → show_map_select()
  - 2 → show_music_select()
- After any sub-screen returns, loop back to show_main_menu().

Make sure the entry point at the bottom of the file is:
    try:
        main()
    except Exception as e:
        print("CRASH:", e)
        # optionally display error on TFT
```

---

## Notes for the AI programmer

- **Do not use framebuf for full-screen rendering** — the 480×320×3 byte buffer (~460KB) exceeds Pico RAM. Draw directly over SPI in chunks.
- **All text rendering** should use a small fixed font (8×8 or similar), scaled up with the scale parameter for large text.
- **No async/threading** — use polling loops everywhere. The Pico handles one thing at a time.
- **SD card for images** is mounted at `/sd/` via sdcard.py on SPI1. DFPlayer has its own SD card accessed only via UART commands — these are two separate storage devices.
- **DFPlayer folder/file numbers are 1-based** (folder 01, file 0001).
- **Music loops automatically** after being selected; it should survive screen transitions without being restarted unless the user picks a new track.
- **Soundboard (G/H/I/J)** interrupts music momentarily — the DFPlayer will resume looping after the clip finishes if loop mode was set. Test this behaviour; if the DFPlayer stops after a soundboard clip, re-issue the loop command after a short delay.
- **Skill check** only triggers when current_max ≤ 10 and modifies only the effective max for that single roll.
- **Pin GP23, GP24, GP25, GP29 are reserved** for the WiFi chip — never assign them to anything.
