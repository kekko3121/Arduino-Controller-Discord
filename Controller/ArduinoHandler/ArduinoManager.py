from Controller.ArduinoHandler.AudioHardware import SerialInterface, PortScanner
import asyncio
from Controller.Config.config import setup_logging

logger = setup_logging(__name__) # Assuming setup_logging is defined in config.py

# ArduinoManager is responsible for managing the connection to the Arduino device
class ArduinoManager:

    # initialize the ArduinoManager with a SerialInterface and a connection status flag
    def __init__(self):
        self.interface = SerialInterface() # create an instance of SerialInterface to handle serial communication
        self.connected = False # flag to track whether the Arduino is currently connected

    # continuously monitor for the Arduino connection and attempt to connect if not already connected
    async def monitor_connection(self):
        while True:
            if not self.connected: # if not currently connected, try to find and connect to the Arduino
                port = PortScanner.find_arduino() # use PortScanner to find the correct serial port for the Arduino
                if port and self.interface.open(port): # if a port is found and the connection is successfully opened
                    self.connected = True # update the connection status flag
                    logger.info("Arduino collegato!") # log a message indicating that the Arduino is connected
            await asyncio.sleep(2)