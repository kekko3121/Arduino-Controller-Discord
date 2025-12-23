"""
Arduino serial communication handler
Manages serial connection and data exchange with Arduino
Supports dynamic connection/disconnection detection
"""

import asyncio
import serial
import serial.tools.list_ports
from config import SERIAL_CONFIG, APP_CONFIG, setup_logging

logger = setup_logging(__name__)

# Auto-reconnect configuration
RECONNECT_CONFIG = {
    'check_interval': 2,  # Check for Arduino every 2 seconds
    'max_retries': 3,     # Try to connect 3 times before giving up
    'retry_delay': 1,     # Wait 1 second between retries
}


class ArduinoSerialHandler:
    """Manages serial communication with Arduino with auto-reconnect support"""
    
    def __init__(self, port=None):
        self.port = port
        self.baudrate = SERIAL_CONFIG['baudrate']
        self.timeout = SERIAL_CONFIG['timeout']
        self.serial_conn = None
        self.running = False
        self._buffer = ""
        self._connected = False
        self._monitor_task = None
    
    def find_arduino_port(self):
        """Auto-detect Arduino serial port by USB descriptor"""
        ports = serial.tools.list_ports.comports()
        for port_info in ports:
            if 'Arduino' in port_info.description or 'CH340' in port_info.description:
                logger.info(f"Found Arduino: {port_info.device} - {port_info.description}")
                return port_info.device
        return None
    
    def connect(self):
        """Establish connection to Arduino"""
        if self.port is None:
            self.port = self.find_arduino_port()
        
        if self.port is None:
            logger.error("No Arduino found. Available ports:")
            for port in serial.tools.list_ports.comports():
                logger.error(f"  {port.device} - {port.description}")
            self._connected = False
            return False
        
        try:
            self.serial_conn = serial.Serial(
                self.port,
                self.baudrate,
                timeout=self.timeout
            )
            self.running = True
            self._connected = True
            logger.info(f"✓ Connected to Arduino on {self.port}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.running = False
            self._connected = False
            return False
    
    def disconnect(self):
        """Close Arduino connection safely"""
        if self.serial_conn:
            self.running = False
            self._connected = False
            self.serial_conn.close()
            logger.info("Disconnected from Arduino")
    
    def _is_complete_command(self, line):
        """Check if line is a complete command"""
        valid_commands = [
            "BUTTON:MIC:PRESSED",
            "BUTTON:AUDIO:PRESSED",
            "BUTTON:BOTH:PRESSED"
        ]
        return any(cmd in line for cmd in valid_commands)
    
    async def read_data(self):
        """Read and parse commands from Arduino asynchronously"""
        while self.running:
            try:
                if self.serial_conn and self.serial_conn.in_waiting:
                    chunk = self.serial_conn.read(self.serial_conn.in_waiting).decode('utf-8', errors='ignore')
                    self._buffer += chunk
                    
                    # Process complete lines
                    while '\n' in self._buffer:
                        line, self._buffer = self._buffer.split('\n', 1)
                        line = line.strip()
                        if line and self._is_complete_command(line):
                            cmd = self.parse_arduino_command(line)
                            if cmd:
                                yield cmd
                
                await asyncio.sleep(APP_CONFIG['read_interval'])
            except Exception as e:
                logger.error(f"Read error: {e}")
                await asyncio.sleep(APP_CONFIG['retry_interval'])
    
    def parse_arduino_command(self, line):
        """Parse Arduino command and return message dict"""
        try:
            if "BUTTON:MIC:PRESSED" in line:
                return {'type': 'button_pressed', 'action': 'mic'}
            elif "BUTTON:AUDIO:PRESSED" in line:
                return {'type': 'button_pressed', 'action': 'audio'}
            elif "BUTTON:BOTH:PRESSED" in line:
                return {'type': 'button_pressed', 'action': 'toggle_both'}
        except Exception as e:
            logger.error(f"Parse error on '{line}': {e}")
        
        return None
    
    def send_data(self, command):
        """Send command to Arduino
        
        Args:
            command (str): Command to send (e.g., "MIC:ON", "AUDIO:OFF")
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.serial_conn or not self.running:
            return False
        
        try:
            self.serial_conn.write(command.encode() + b'\n')
            return True
        except Exception as e:
            logger.error(f"Send failed: {e}")
            return False
    
    def send_commands(self, commands):
        """Send multiple commands to Arduino
        
        Args:
            commands (list): List of commands to send
            
        Returns:
            bool: True if all successful, False otherwise
        """
        return all(self.send_data(cmd) for cmd in commands)
    
    def is_connected(self):
        """Check if Arduino is currently connected
        
        Returns:
            bool: True if connected and ready, False otherwise
        """
        return self._connected and self.serial_conn is not None and self.running
    
    async def monitor_connection(self):
        """Background task to monitor Arduino connection
        Automatically reconnects when Arduino is plugged in
        """
        while self.running:
            try:
                # If not connected, try to find and connect Arduino
                if not self.is_connected():
                    port = self.find_arduino_port()
                    if port:
                        self.port = port
                        for attempt in range(RECONNECT_CONFIG['max_retries']):
                            if self.connect():
                                logger.info(f"✓ Auto-reconnected to Arduino")
                                break
                            if attempt < RECONNECT_CONFIG['max_retries'] - 1:
                                await asyncio.sleep(RECONNECT_CONFIG['retry_delay'])
                    else:
                        # No Arduino found, check again later
                        logger.debug("Arduino not found, checking again...")
                
                # Check if connection is still alive by checking port availability
                if self.is_connected():
                    try:
                        # Verify port is still valid
                        if not any(p.device == self.port for p in serial.tools.list_ports.comports()):
                            logger.warning("Arduino was unplugged")
                            self.disconnect()
                    except Exception as e:
                        logger.error(f"Connection check failed: {e}")
                        self.disconnect()
                
                # Wait before next check
                await asyncio.sleep(RECONNECT_CONFIG['check_interval'])
            
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(RECONNECT_CONFIG['check_interval'])
