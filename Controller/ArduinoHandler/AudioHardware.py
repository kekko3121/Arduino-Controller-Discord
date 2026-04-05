import serial
import serial.tools.list_ports
from Config.config import setup_logging

logger = setup_logging(__name__)

# Static class to scan for Arduino ports
class PortScanner:

    # Static method to find Arduino port
    @staticmethod
    def find_arduino():
        ports = serial.tools.list_ports.comports()
        
        for p in ports:
            if any(k in p.description or k in p.device for k in ['Arduino', 'CH340', 'USB', 'ACM', 'ttyACM']): 
                logger.info(f"Arduino found on {p.device}")
                return p.device
        
        return None

# Class to manage serial communication with Arduino
class SerialInterface:
    def __init__(self, baudrate=9600):
        self.conn = None # Serial connection object, initialized as None until a connection is established
        self.baudrate = baudrate # Baud rate for serial communication, default is 9600
        self._buffer = ""  # Buffer for incomplete lines

    def open(self, port):
        try:
            # Attempt to open a serial connection to the specified port with the configured baud rate and a timeout 
            # for non-blocking reads. If successful, store the connection object and return True. If it fails, log the error and 
            # return False.
            self.conn = serial.Serial(port, self.baudrate, timeout=1)
            self._buffer = ""  # Reset buffer on new connection
            return True # Return True if connection is successfully opened
        except Exception as e:
            logger.error(f"Error opening port: {e}") # Log any exceptions that occur during connection attempt
            return False

    # Method to write data to the Arduino. It checks if the connection is open before attempting to write, and sends the data 
    # followed by a newline character.
    def write(self, data):
        if self.conn and self.conn.is_open:
            self.conn.write(f"{data}\n".encode())

    # Method to read a complete line from the Arduino, buffering incomplete data until a newline character is received. It checks if the
    def read_line(self):
        if not self.conn or not self.conn.is_open:
            return None
        
        try:
            if self.conn.in_waiting:
                chunk = self.conn.read(self.conn.in_waiting).decode('utf-8', errors='ignore')
                self._buffer += chunk
                
                if '\n' in self._buffer:
                    line, self._buffer = self._buffer.split('\n', 1)
                    line = line.strip()
                    if line:
                        return line
        except Exception as e:
            logger.error(f"Serial read error: {e}")
        
        return None

    # Check if the connection is active
    def is_connected(self):
        return self.conn is not None and self.conn.is_open

    # Method to send a list of commands to the Arduino by writing each command to the serial connection
    def send_commands(self, commands):
        for command in commands:
            self.write(command)

    # Method to close the serial connection if it is open, and log a message indicating that the connection has been closed
    def close(self):
        if self.conn and self.conn.is_open:
            self.conn.close()
            logger.info("Serial connection closed")