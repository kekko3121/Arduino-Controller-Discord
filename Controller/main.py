import asyncio
from Config.config import setup_logging, APP_CONFIG, SERVER_CONFIG
from ArduinoHandler.AudioHardware import PortScanner, SerialInterface
from AudioWeb.AudioState import AudioState
from AudioWeb.CommandBridge import CommandBridge
from AudioWeb.WebSocket import WebSocket

logger = setup_logging(__name__)

async def main():
    # 1. Inizializzazione dei componenti base
    state = AudioState()
    serial_hw = SerialInterface()
    
    # 2. Inizializzazione del "Cervello" (Bridge)
    # Il bridge ha bisogno di accedere allo stato e all'hardware
    bridge = CommandBridge(state, serial_hw)
    
    # 3. Inizializzazione del Server WebSocket
    # Il server ha bisogno del bridge per reagire ai messaggi di Discord
    server = WebSocket(bridge, state)

    logger.info("System started. Starting hardware monitoring...")

    # 4. Definizione dei Task concorrenti
    tasks = [
        # Task 1: Gestione della connessione fisica e auto-reconnect
        asyncio.create_task(monitor_arduino_connection(serial_hw)),
        
        # Task 2: Lettura dei dati dall'Arduino e invio al Bridge
        asyncio.create_task(arduino_read_loop(serial_hw, bridge, server)),
        
        # Task 3: Avvio del Server WebSocket per Discord
        asyncio.create_task(server.start())
    ]

    try:
        # Esegue tutti i task finché uno non fallisce o viene interrotto
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Tasks interrupted.")
    except Exception as e:
        logger.error(f"Errore nei task: {e}", exc_info=True)
    finally:
        # Cleanup: cancella i task e chiude la connessione seriale
        for task in tasks:
            if not task.done():
                task.cancel()
        serial_hw.close()
        logger.info("Serial connection closed. Program terminated.")

async def monitor_arduino_connection(hw):
    """Ciclo infinito che controlla se l'Arduino è collegato"""
    while True:
        if not hw.is_connected():
            port = PortScanner.find_arduino()
            if port:
                if hw.open(port):
                    logger.info(f"Arduino connected on {port}")
                else:
                    logger.error(f"Failed to open port {port}")
            else:
                logger.debug("Waiting for Arduino...")
        await asyncio.sleep(2) # Controlla ogni 2 secondi

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