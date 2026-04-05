import asyncio
import signal
from typing import List, Optional
from Config.config import setup_logging, APP_CONFIG
from ArduinoHandler.AudioHardware import PortScanner, SerialInterface
from AudioWeb.AudioState import AudioState
from AudioWeb.CommandBridge import CommandBridge
from AudioWeb.WebSocket import WebSocket

logger = setup_logging(__name__)

# Timing constants
ARDUINO_CHECK_INTERVAL = 2
ARDUINO_READ_INTERVAL = APP_CONFIG.get('read_interval', 0.1)


async def main() -> None:
    """
    Main application entry point orchestrating all system components.
    
    Initializes the audio state, serial hardware interface, command bridge,
    and WebSocket server, then runs three concurrent tasks:
    - Monitor Arduino connection status
    - Read and process Arduino input
    - Start the WebSocket server for Discord plugin communication
    """
    # Initialize core components
    state = AudioState()
    serial_hw = SerialInterface()
    
    # Validate hardware initialization
    if serial_hw is None:
        logger.error("Failed to initialize serial interface")
        return
    
    # Initialize the command bridge (connects state management to hardware)
    bridge = CommandBridge(state, serial_hw)
    
    # Initialize the WebSocket server (handles Discord plugin communication)
    server = WebSocket(bridge, state)

    logger.info("System started. Initializing hardware monitoring and server...")

    # Create concurrent tasks for system operations
    tasks: List[asyncio.Task] = [
        asyncio.create_task(
            monitor_arduino_connection(serial_hw),
            name="arduino_monitor"
        ),
        asyncio.create_task(
            arduino_read_loop(serial_hw, bridge, server),
            name="arduino_reader"
        ),
        asyncio.create_task(
            server.start(),
            name="websocket_server"
        ),
    ]

    try:
        # Run all tasks concurrently until one fails or is cancelled
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("System shutdown initiated.")
    except Exception as e:
        logger.error(f"Unexpected error in task execution: {e}", exc_info=True)
    finally:
        # Cleanup: cancel all pending tasks and close hardware connections
        for task in tasks:
            if not task.done():
                task.cancel()
        
        # Wait for all tasks to complete cancellation
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Close serial connection and release resources
        serial_hw.close()
        logger.info("Hardware connection closed. Application terminated.")

async def monitor_arduino_connection(hw: SerialInterface) -> None:
    """
    Monitor Arduino hardware connection status and auto-reconnect on disconnection.
    
    Periodically checks if the Arduino is connected and attempts to reconnect
    if the connection is lost. Uses PortScanner to locate the Arduino on available ports.
    
    Args:
        hw: The SerialInterface instance managing hardware communication
    """
    while True:
        try:
            if not hw.is_connected():
                port = PortScanner.find_arduino()
                if port:
                    if hw.open(port):
                        logger.info(f"Arduino reconnected at port {port}")
                    else:
                        logger.warning(f"Failed to open port {port}")
                else:
                    logger.debug("Arduino not detected. Retrying...")
            
            await asyncio.sleep(ARDUINO_CHECK_INTERVAL)
        except Exception as e:
            logger.error(f"Error monitoring Arduino connection: {e}", exc_info=True)
            await asyncio.sleep(ARDUINO_CHECK_INTERVAL)

async def arduino_read_loop(hw, bridge, server):
    """Legge i dati seriali e li distribuisce"""
    while True:
        if hw.is_connected():
            line = hw.read_line()
            if line:
                result = await bridge.handle_arduino_input(line)
                if result:
                    action = result.get('action')
                    new_state = result.get('state')
                    logger.info(f"Arduino command: {action} → {new_state}")
                    await server.broadcast({
                        'type': 'button_pressed',
                        'action': action,
                        **new_state
                    })
        await asyncio.sleep(APP_CONFIG['read_interval'])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass