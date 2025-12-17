#!/usr/bin/env python3
"""
WebSocket Server for Arduino-Discord communication via BetterDiscord Plugin
Relays button commands from Arduino to Discord and LED feedback back to Arduino
"""

import asyncio
import json
import serial
import serial.tools.list_ports
import logging
from websockets.server import serve

# Configure logging - only essential messages
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Server configuration
CONFIG = {
    'port': 8765,
    'baudrate': 9600,
    'timeout': 1,
}

class ArduinoSerialHandler:
    """Manages serial communication with Arduino"""
    
    def __init__(self, port=None, baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.running = False
    
    def find_arduino_port(self):
        """Auto-detect Arduino serial port"""
        ports = serial.tools.list_ports.comports()
        for port_info in ports:
            if 'Arduino' in port_info.description or 'CH340' in port_info.description:
                logger.info(f"Found: {port_info.device} - {port_info.description}")
                return port_info.device
        return None
    
    def connect(self):
        """Connect to Arduino"""
        if self.port is None:
            self.port = self.find_arduino_port()
        
        if self.port is None:
            logger.error("No Arduino found. Available ports:")
            for port in serial.tools.list_ports.comports():
                logger.error(f"  {port.device} - {port.description}")
            return False
        
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=CONFIG['timeout'])
            logger.info(f"✓ Connected to Arduino on {self.port}")
            self.running = True
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close Arduino connection"""
        if self.serial_conn:
            self.serial_conn.close()
            self.running = False
            logger.info("Disconnected from Arduino")
    
    async def read_data(self):
        """Read and parse commands from Arduino"""
        while self.running:
            try:
                if self.serial_conn and self.serial_conn.in_waiting:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    if line:
                        yield self.parse_arduino_command(line)
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Read error: {e}")
                await asyncio.sleep(1)
    
    def parse_arduino_command(self, line):
        """Convert Arduino command strings to message format"""
        if line.startswith("BUTTON:MIC:PRESSED"):
            return {'type': 'button_pressed', 'action': 'mic'}
        elif line.startswith("BUTTON:AUDIO:PRESSED"):
            return {'type': 'button_pressed', 'action': 'audio'}
        elif line.startswith("BUTTON:BOTH:PRESSED"):
            return {'type': 'button_pressed', 'action': 'toggle_both'}
        return None
    
    def send_data(self, data):
        """Send command to Arduino"""
        if self.serial_conn and self.running:
            try:
                self.serial_conn.write(data.encode() + b'\n')
                return True
            except Exception as e:
                logger.error(f"Send failed: {e}")
                return False
        return False


class DiscordArduinoServer:
    """WebSocket server bridging Arduino and Discord"""
    
    def __init__(self):
        self.arduino = ArduinoSerialHandler()
        self.clients = set()
        self.mute_state = False
        self.deafen_state = False
    
    async def read_arduino_task(self):
        """Background task to read Arduino commands"""
        async for cmd in self.arduino.read_data():
            if cmd and cmd.get('type') == 'button_pressed':
                await self.process_arduino_command(cmd)
    
    async def process_arduino_command(self, cmd):
        """Process button press from Arduino"""
        action = cmd.get('action')
        
        if action == 'mic':
            self.mute_state = not self.mute_state
            self.arduino.send_data(f"MIC:{'ON' if self.mute_state else 'OFF'}")
            logger.info(f"MIC button pressed → {'MUTED' if self.mute_state else 'UNMUTED'}")
        
        elif action == 'audio':
            self.deafen_state = not self.deafen_state
            self.arduino.send_data(f"AUDIO:{'ON' if self.deafen_state else 'OFF'}")
            logger.info(f"AUDIO button pressed → {'DEAFENED' if self.deafen_state else 'UNDEAFENED'}")
        
        elif action == 'toggle_both':
            self.mute_state = not self.mute_state
            self.deafen_state = not self.deafen_state
            self.arduino.send_data(f"MIC:{'ON' if self.mute_state else 'OFF'}")
            self.arduino.send_data(f"AUDIO:{'ON' if self.deafen_state else 'OFF'}")
            logger.info(f"BOTH button pressed → MIC: {'MUTED' if self.mute_state else 'UNMUTED'}, AUDIO: {'DEAFENED' if self.deafen_state else 'UNDEAFENED'}")
        
        # Broadcast state change to all connected Discord clients
        await self.broadcast({
            'type': 'button_pressed',
            'action': action,
            'muted': self.mute_state,
            'deafened': self.deafen_state
        })

    async def start(self):
        """Start WebSocket server"""
        if not self.arduino.connect():
            logger.warning("Arduino not available - running in demo mode")
        
        async with serve(self.handle_client, "0.0.0.0", CONFIG['port'], reuse_port=True):
            logger.info(f"✓ Server started on ws://127.0.0.1:{CONFIG['port']}")
            await asyncio.gather(
                self.read_arduino_task(),
                asyncio.Event().wait()
            )
    
    async def handle_client(self, websocket, path):
        """Handle new WebSocket client connection"""
        client_addr = websocket.remote_address
        self.clients.add(websocket)
        logger.info(f"Client connected: {client_addr}")
        
        try:
            # Send current state to new client
            await websocket.send(json.dumps({
                'type': 'state',
                'muted': self.mute_state,
                'deafened': self.deafen_state
            }))
            
            # Process incoming messages
            async for message in websocket:
                await self.process_message(websocket, message)
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            self.clients.discard(websocket)
            logger.info(f"Client disconnected: {client_addr}")
    
    async def process_message(self, websocket, message):
        """Process message from Discord plugin"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'state_update':
                # Discord state changed - update Arduino LEDs
                self.mute_state = data.get('muted', False)
                self.deafen_state = data.get('deafened', False)
                self.arduino.send_data(f"MIC:{'ON' if self.mute_state else 'OFF'}")
                self.arduino.send_data(f"AUDIO:{'ON' if self.deafen_state else 'OFF'}")
                
                # Broadcast to all clients
                await self.broadcast({
                    'type': 'state',
                    'muted': self.mute_state,
                    'deafened': self.deafen_state
                })
            
            elif msg_type == 'query_state':
                # Send current state to requesting client
                await websocket.send(json.dumps({
                    'type': 'state',
                    'muted': self.mute_state,
                    'deafened': self.deafen_state
                }))
        
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {message}")
    
    async def broadcast(self, data):
        """Send message to all connected clients"""
        if self.clients:
            message = json.dumps(data)
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )


async def main():
    """Server entry point"""
    server = DiscordArduinoServer()
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
