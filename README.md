# Discord Controller with Arduino

An external Arduino-based hardware control system for muting/unmuting microphone and audio in Discord using 2 buttons and 2 LED feedback indicators.

## Architecture

```
Arduino (USB/Serial) 
    ↓
Python Server (WebSocket - port 8765)
    ↓
BetterDiscord Plugin
```

## Hardware

### Arduino Uno Components
- **Button 1 (Microphone)**: Pin 2 (connected to GND when pressed)
- **Button 2 (Audio)**: Pin 3 (connected to GND when pressed)
- **LED 1 (Mic)**: Pin 12 (HIGH = microphone muted)
- **LED 2 (Audio)**: Pin 13 (HIGH = audio muted)

### Wiring Diagram
```
BUTTONS:
Arduino Pin 2  ←→ Microphone Button ←→ GND
Arduino Pin 3  ←→ Audio Button ←→ GND

<<<<<<< HEAD
LEDs:
Arduino Pin 12 ←→ Mic LED anode ←→ 220Ω resistor ←→ GND
Arduino Pin 13 ←→ Audio LED anode ←→ 220Ω resistor ←→ GND

Common GND for all components
```
=======
<img width="1480" height="841" alt="Image" src="https://github.com/user-attachments/assets/93f88a02-26d8-4cb8-9619-c8a0a7c90b57" />

For more information, see the wiring_diagram.pdf included in the project root (detailed Arduino connection diagram).
>>>>>>> 7e205f6 (update readme file)

## Installation

### 1. Arduino Setup

1. Open Arduino IDE
2. Load the sketch: `arduino_sketch.ino`
3. Select "Arduino Uno" board and the COM/ttyUSB port
4. Upload the sketch

### 2. Python Server

Requirements:
```bash
pip install websockets pyserial
```

Start the server:
```bash
python3 arduino_server.py
```

The server:
- Auto-detects the Arduino port
- Starts a WebSocket server on `ws://localhost:8765`
- Routes commands between Arduino and the plugin

### 3. BetterDiscord Plugin

1. Copy `ArduinoController.plugin.js` to:
   - **Windows**: `%APPDATA%\BetterDiscord\plugins\`
   - **Linux**: `~/.config/BetterDiscord/plugins/`
   - **macOS**: `~/Library/Application Support/BetterDiscord/plugins/`

2. Restart Discord (or press `Ctrl+Shift+R`)

3. Enable the plugin in Settings → Plugins → ArduinoMute

## Usage

1. **Start the Python server** (once):
   ```bash
   python3 arduino_server.py
   ```

2. **Open Discord** with the plugin enabled

3. **Press an Arduino button** to toggle mute

4. **LED Indicators**: 
   - **On** (HIGH) = Microphone muted
   - **Off** (LOW) = Microphone active

## Troubleshooting

### Server cannot find Arduino
```
[ERROR] No Arduino found. Available ports:
  /dev/ttyUSB0 - USB2.0-Serial
```

Solution:
1. Verify Arduino is connected via USB
2. Install CH340 drivers if needed

### Plugin cannot connect to server
- Verify the Python server is running
- Check that no firewall blocks port 8765 (localhost)
- Check Discord console for errors (F12 → Console)

## Communication Protocol

### Arduino → Server
```
BUTTON:MIC:PRESSED      // Microphone button pressed
BUTTON:AUDIO:PRESSED    // Audio button pressed
BUTTON:BOTH:PRESSED     // Both buttons pressed
MIC_LED:ON              // Mic LED on confirmation
MIC_LED:OFF             // Mic LED off confirmation
AUDIO_LED:ON            // Audio LED on confirmation
AUDIO_LED:OFF           // Audio LED off confirmation
```

### Server → Arduino
```
MIC:ON                  // Turn on microphone LED
MIC:OFF                 // Turn off microphone LED
AUDIO:ON                // Turn on audio LED
AUDIO:OFF               // Turn off audio LED
```

### Plugin ↔ Server (JSON via WebSocket)
```json
{
  "type": "button_pressed",
  "action": "mic",
  "muted": true,
  "deafened": false
}
```

```json
{
  "type": "state_update",
  "muted": true,
  "deafened": false
}
```

```json
{
  "type": "query_state"
}
```

## Development Notes

- Arduino Baudrate: **9600 bps**
- WebSocket Port: **8765**
- Button Debounce: **50ms**
- Discord Mute Read Timeout: **100ms**
- Reconnection Attempts: **10** (every 2 seconds)
- LED 1: **Pin 12** (Microphone)
- LED 2: **Pin 13** (Audio)
- Button 1: **Pin 2** (Microphone)
- Button 2: **Pin 3** (Audio)

## Features

- ✅ Microphone Mute Toggle (Pin 2 → LED Pin 12)
- ✅ Audio/Deafen Toggle (Pin 3 → LED Pin 13)
- ✅ Bidirectional Discord Synchronization
- ✅ Real-time LED Feedback
- ✅ Auto-reconnection if server goes down
- ✅ Hardware-level Button Debouncing
- ✅ Complete Logging (server and plugin side)

## Version

- **Plugin**: 0.3.0
- **Server**: Python 3.7+
- **Arduino Sketch**: v1.0
- **Arduino**: Uno/Nano (compatible)

## License

  [MIT License](https://choosealicense.com/licenses/mit/)

Copyright (c) 2024 Francesco

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.