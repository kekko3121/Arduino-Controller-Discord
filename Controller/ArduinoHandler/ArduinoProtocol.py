# isolate the protocol parsing logic in a separate class for better maintainability and testability
class ArduinoProtocol:

    # define the mapping of raw command strings to structured command objects
    COMMANDS = {
        "BUTTON:MIC:PRESSED":   {'type': 'button_pressed', 'action': 'mic'},
        "BUTTON:AUDIO:PRESSED": {'type': 'button_pressed', 'action': 'audio'},
        "BUTTON:BOTH:PRESSED":  {'type': 'button_pressed', 'action': 'toggle_both'}
    }

    # parse a raw line from the Arduino and return a structured command object
    @classmethod
    def parse(cls, line):
        for raw, parsed in cls.COMMANDS.items(): # check if the raw command string is present in the line
            if raw in line: # if found, return the corresponding structured command object
                return parsed
        return None