import json
import asyncio
import websockets
from Config.config import setup_logging, APP_CONFIG, SERVER_CONFIG

logger = setup_logging(__name__)

# WebSocket server to handle communication between Arduino and Discord plugin
class WebSocket:

    # Initialize with references to bridge and state manager
    def __init__(self, bridge, state_manager):
        self.bridge = bridge # Instance of CommandBridge to handle command translation between Arduino and Discord
        self.state = state_manager # Instance of AudioState to manage current mute/deafen states
        self.clients = set() # Set to track connected WebSocket clients for broadcasting state updates
    
    async def start(self):
        """Inizia il server WebSocket e lo tiene in esecuzione"""
        logger.info(f"Server avviato su ws://{SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}")
        
        # websockets.serve crea il server e usa handle_client per ogni nuova connessione
        async with websockets.serve(
            self.handle_client, 
            SERVER_CONFIG['host'], 
            SERVER_CONFIG['port']
        ):
            # Questo mantiene il server attivo indefinitamente
            await asyncio.Future()

    # Broadcast a message to all connected clients
    async def broadcast(self, data):
        if not self.clients:
            return
        
        message = json.dumps(data)

        # Use asyncio.gather to send the message to all clients concurrently, handling any exceptions that may occur
        await asyncio.gather(*[client.send(message) for client in self.clients], return_exceptions=True)

    # Main server loop to accept WebSocket connections and run tasks concurrently
    async def handle_client(self, websocket):
        self.clients.add(websocket)
        try:
            # Send current state to new client upon connection
            await websocket.send(json.dumps({'type': 'state', **await self.state.get_states()}))
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get('type') == 'state_update':
                        muted, deafened = data.get('muted'), data.get('deafened')
                        await self.state.update(muted, deafened)
                        self.bridge.arduino.send_commands(self.bridge.get_arduino_led_commands(muted, deafened))
                        await self.broadcast({'type': 'state', 'muted': muted, 'deafened': deafened})
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON message")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            self.clients.discard(websocket)