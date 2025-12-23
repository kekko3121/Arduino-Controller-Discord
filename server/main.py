#!/usr/bin/env python3
"""
Arduino Discord Controller - Main Entry Point
WebSocket server bridging Arduino button commands to Discord
"""

import asyncio
from server import DiscordArduinoServer
from config import setup_logging

logger = setup_logging(__name__)


async def main():
    """Application entry point"""
    logger.info("Starting Arduino Discord Controller Server")
    server = DiscordArduinoServer()
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
