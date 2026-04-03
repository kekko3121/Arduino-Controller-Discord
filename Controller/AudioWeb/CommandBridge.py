class CommandBridge:

    # This class serves as a bridge between the AudioState and the ArduinoHandler, translating state changes into commands for 
    # the Arduino and vice versa.
    def __init__(self, audio_state, arduino_handler):
        self.state = audio_state # Instance of AudioState to manage current mute/deafen states
        self.arduino = arduino_handler # Instance of ArduinoSerialHandler to communicate with the Arduino device

    # This method is called when an input is received from the Arduino (e.g., a button press) and updates the state accordingly,
    # then sends the appropriate commands back to the Arduino to update the LED indicators.
    async def handle_arduino_input(self, action):
        """Convert Arduino button action into state changes and send commands back to Arduino"""
        # Parse Arduino message format: "BUTTON:MIC:PRESSED" or "BUTTON:AUDIO:PRESSED"
        action = action.strip().upper()
        
        # Only process valid button commands, ignore initialization messages
        if not action.startswith("BUTTON:"):
            return None
        
        if "BUTTON:MIC:PRESSED" in action:
            button_type = 'mic'
        elif "BUTTON:AUDIO:PRESSED" in action:
            button_type = 'audio'
        else:
            return None
        
        current = await self.state.get_states()
        new_state = current.copy()
        
        if button_type == 'mic':
            new_state = await self.state.update(muted=not current['muted'])
        elif button_type == 'audio':
            new_state = await self.state.update(deafened=not current['deafened'])
        
        commands = [
            f"MIC:{'ON' if new_state['muted'] else 'OFF'}",
            f"AUDIO:{'ON' if new_state['deafened'] else 'OFF'}"
        ]
        
        self.arduino.send_commands(commands)
        return {'action': button_type, 'state': new_state}

    # This method generates the appropriate Arduino commands to set the LED indicators based on the current mute and deafen states.
    def get_arduino_led_commands(self, muted, deafened):
        """Generate serial commands based on state"""
        return [
            f"MIC:{'ON' if muted else 'OFF'}", # Command to set MIC LED based on mute state
            f"AUDIO:{'ON' if deafened else 'OFF'}" # Command to set AUDIO LED based on deafen state
        ]