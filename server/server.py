"""
WebSocket server for Arduino-Discord communication
Bridges button commands from Arduino to Discord and LED feedback back
"""

import asyncio
import json
import websockets
from arduino_handler import ArduinoSerialHandler
from config import SERVER_CONFIG, setup_logging

logger = setup_logging(__name__)


class DiscordArduinoServer:
    """WebSocket server managing Arduino-Discord communication"""
    
    def __init__(self):
        self.arduino = ArduinoSerialHandler()
        self.clients = set()
        self.mute_state = False
        self.deafen_state = False
        self._lock = asyncio.Lock()
    
    async def _update_states(self, muted=None, deafened=None):
        """Thread-safe state update"""
        async with self._lock:
            if muted is not None:
                self.mute_state = muted
            if deafened is not None:
                self.deafen_state = deafened
    
    async def _get_states(self):
        """Thread-safe state read"""
        async with self._lock:
            return {
                'muted': self.mute_state,
                'deafened': self.deafen_state
            }
    
    async def read_arduino_task(self):
        """Background task reading Arduino button commands"""
        async for cmd in self.arduino.read_data():
            if cmd and cmd.get('type') == 'button_pressed':
                await self.process_arduino_command(cmd)
    
    async def process_arduino_command(self, cmd):
        """Process and respond to Arduino button press"""
        action = cmd.get('action')
        
        if action == 'mic':
            await self._update_states(muted=not self.mute_state)
            self.arduino.send_data(f"MIC:{'ON' if self.mute_state else 'OFF'}")
            logger.info(f"MIC button → {'MUTED' if self.mute_state else 'UNMUTED'}")
        
        elif action == 'audio':
            await self._update_states(deafened=not self.deafen_state)
            self.arduino.send_data(f"AUDIO:{'ON' if self.deafen_state else 'OFF'}")
            logger.info(f"AUDIO button → {'DEAFENED' if self.deafen_state else 'UNDEAFENED'}")
        
        elif action == 'toggle_both':
            await self._update_states(
                muted=not self.mute_state,
                deafened=not self.deafen_state
            )
            self.arduino.send_commands([
                f"MIC:{'ON' if self.mute_state else 'OFF'}",
                f"AUDIO:{'ON' if self.deafen_state else 'OFF'}"
            ])
            logger.info(f"BOTH button → MIC:{'MUTED' if self.mute_state else 'UNMUTED'}, AUDIO:{'DEAFENED' if self.deafen_state else 'UNDEAFENED'}")
        
        # Broadcast state change to all Discord clients
        states = await self._get_states()
        await self.broadcast({
            'type': 'button_pressed',
            'action': action,
            **states
        })
    
    async def start(self):
        """Start WebSocket server and Arduino task"""
        if not self.arduino.connect():
            logger.warning("Arduino not available - will auto-connect when plugged in")
        
        # Always start the monitor task, it will handle auto-reconnect
        self.arduino.running = True
        
        try:
            async with websockets.serve(
                self.handle_client,
                SERVER_CONFIG['host'],
                SERVER_CONFIG['port']
            ):
                logger.info(f"✓ Server started on ws://127.0.0.1:{SERVER_CONFIG['port']}")
                
                # Run server, Arduino read task, and connection monitor concurrently
                await asyncio.gather(
                    self.read_arduino_task(),
                    self.arduino.monitor_connection(),
                    asyncio.Event().wait()
                )
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.arduino.disconnect()
    
    async def handle_client(self, websocket):
        """Handle WebSocket client connection"""
        client_addr = websocket.remote_address
        self.clients.add(websocket)
        logger.info(f"Client connected: {client_addr}")
        
        try:
            # Send current state to new client
            states = await self._get_states()
            await websocket.send(json.dumps({
                'type': 'state',
                **states
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
        """Process incoming message from Discord plugin"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'state_update':
                # Discord state changed - update Arduino LEDs
                muted = data.get('muted', False)
                deafened = data.get('deafened', False)
                
                await self._update_states(muted=muted, deafened=deafened)
                
                # Send commands to Arduino
                self.arduino.send_commands([
                    f"MIC:{'ON' if muted else 'OFF'}",
                    f"AUDIO:{'ON' if deafened else 'OFF'}"
                ])
                
                # Broadcast to all clients
                await self.broadcast({
                    'type': 'state',
                    'muted': muted,
                    'deafened': deafened
                })
            
            elif msg_type == 'query_state':
                # Send current state to requesting client
                states = await self._get_states()
                await websocket.send(json.dumps({
                    'type': 'state',
                    **states
                }))
        
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {message}")
        except Exception as e:
            logger.error(f"Message processing error: {e}")
    
    async def broadcast(self, data):
        """Send message to all connected clients
        
        Args:
            data (dict): Message data to broadcast
        """
        if not self.clients:
            return
        
        message = json.dumps(data)
        dead_clients = set()
        
        for client in self.clients:
            try:
                await client.send(message)
            except Exception as e:
                logger.debug(f"Broadcast error: {e}")
                dead_clients.add(client)
        
        # Remove disconnected clients
        self.clients -= dead_clients
