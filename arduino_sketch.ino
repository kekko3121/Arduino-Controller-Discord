/*
 * Arduino Sketch for Discord Mute Controller
 * 
 * This sketch manages button inputs and LED outputs for a Discord audio controller
 * Two buttons control microphone and audio mute states, with corresponding LED feedback
 * 
 * Hardware Setup:
 * - Button 1 (MIC):   Pin 2 (pulls to GND when pressed)
 * - Button 2 (AUDIO): Pin 3 (pulls to GND when pressed)
 * - LED 1 (MIC):      Pin 11 (HIGH = microphone muted)
 * - LED 2 (AUDIO):    Pin 12 (HIGH = audio muted)
 * 
 * Communication:
 * - Serial @ 9600 baud with Python WebSocket server
 * - Commands from buttons are sent as "BUTTON:MIC:PRESSED" etc
 * - Commands from server are received as "MIC:ON/OFF", "AUDIO:ON/OFF"
 */

// Pin definitions
const int BUTTON_MIC_PIN = 2;
const int BUTTON_AUDIO_PIN = 3;
const int LED_MIC_PIN = 11;
const int LED_AUDIO_PIN = 12;

// Button state tracking
volatile bool buttonMicPressed = false;
volatile bool buttonAudioPressed = false;
volatile unsigned long lastMicInterruptTime = 0;
volatile unsigned long lastAudioInterruptTime = 0;

// LED state tracking
bool ledMicState = false;
bool ledAudioState = false;

// Debounce timing (200ms to prevent false triggers)
unsigned long lastMicDebounceTime = 0;
unsigned long lastAudioDebounceTime = 0;
const unsigned long DEBOUNCE_DELAY = 200;

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  
  // Configure button pins with internal pull-up resistors
  pinMode(BUTTON_MIC_PIN, INPUT_PULLUP);
  pinMode(BUTTON_AUDIO_PIN, INPUT_PULLUP);
  
  // Configure LED pins as outputs
  pinMode(LED_MIC_PIN, OUTPUT);
  pinMode(LED_AUDIO_PIN, OUTPUT);
  
  // Turn off LEDs on startup
  digitalWrite(LED_MIC_PIN, LOW);
  digitalWrite(LED_AUDIO_PIN, LOW);
  
  // Attach interrupt handlers for button pin changes (falling edge when button pressed)
  attachInterrupt(digitalPinToInterrupt(BUTTON_MIC_PIN), buttonMicISR, FALLING);
  attachInterrupt(digitalPinToInterrupt(BUTTON_AUDIO_PIN), buttonAudioISR, FALLING);
  
  delay(1000);
  Serial.println("Arduino initialized - MIC(pin2/led11), AUDIO(pin3/led12)");
}

void loop() {
  // Handle commands from Python server
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    // Process LED control commands from server
    if (command.startsWith("MIC:ON")) {
      ledMicState = true;
      digitalWrite(LED_MIC_PIN, HIGH);
    }
    else if (command.startsWith("MIC:OFF")) {
      ledMicState = false;
      digitalWrite(LED_MIC_PIN, LOW);
    }
    else if (command.startsWith("AUDIO:ON")) {
      ledAudioState = true;
      digitalWrite(LED_AUDIO_PIN, HIGH);
    }
    else if (command.startsWith("AUDIO:OFF")) {
      ledAudioState = false;
      digitalWrite(LED_AUDIO_PIN, LOW);
    }
  }
  
  // Process microphone button press with debouncing
  if (buttonMicPressed) {
    unsigned long currentTime = millis();
    if ((currentTime - lastMicDebounceTime) > DEBOUNCE_DELAY) {
      Serial.println("BUTTON:MIC:PRESSED");
      buttonMicPressed = false;
      lastMicDebounceTime = currentTime;
    }
  }
  
  // Process audio button press with debouncing
  if (buttonAudioPressed) {
    unsigned long currentTime = millis();
    if ((currentTime - lastAudioDebounceTime) > DEBOUNCE_DELAY) {
      Serial.println("BUTTON:AUDIO:PRESSED");
      buttonAudioPressed = false;
      lastAudioDebounceTime = currentTime;
    }
  }
  
  delay(10);
}

// Interrupt service routine for microphone button
// Called when pin 2 goes from HIGH to LOW (button pressed)
void buttonMicISR() {
  unsigned long currentTime = millis();
  // Software debounce: ignore interrupts within DEBOUNCE_DELAY of the last one
  if ((currentTime - lastMicInterruptTime) > DEBOUNCE_DELAY) {
    buttonMicPressed = true;
    lastMicDebounceTime = currentTime;
    lastMicInterruptTime = currentTime;
  }
}

// Interrupt service routine for audio button
// Called when pin 3 goes from HIGH to LOW (button pressed)
void buttonAudioISR() {
  unsigned long currentTime = millis();
  // Software debounce: ignore interrupts within DEBOUNCE_DELAY of the last one
  if ((currentTime - lastAudioInterruptTime) > DEBOUNCE_DELAY) {
    buttonAudioPressed = true;
    lastAudioDebounceTime = currentTime;
    lastAudioInterruptTime = currentTime;
  }
}
