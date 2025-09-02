"""Main entry point for MCP server."""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.settings import settings
from src.mcp.server import ITGlueMCPServer
from src.mcp.websocket_server import WebSocketMCPServer
from src.utils.logging import setup_logging

# Global server instance for signal handling
server_instance = None


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logger = logging.getLogger(__name__)
    logger.info(f"Received signal {sig}, shutting down...")

    if server_instance:
        # Cancel all running tasks
        for task in asyncio.all_tasks():
            task.cancel()

    sys.exit(0)


async def main():
    """Main entry point."""
    global server_instance

    # Setup logging
    setup_logging(level=settings.log_level)
    logger = logging.getLogger(__name__)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Create server instance
        logger.info("Initializing IT Glue MCP Server...")
        server_instance = ITGlueMCPServer()

        # Check if WebSocket mode is requested
        if "--websocket" in sys.argv or settings.mcp_websocket_port:
            # Run WebSocket server
            ws_server = WebSocketMCPServer(server_instance)
            host = settings.mcp_server_host or "0.0.0.0"
            port = settings.mcp_websocket_port or 8001

            logger.info(f"Starting WebSocket server on ws://{host}:{port}")
            await ws_server.run(host=host, port=port)

        else:
            # Run stdio server (default)
            logger.info("Starting stdio MCP server...")
            await server_instance.run()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")

    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
