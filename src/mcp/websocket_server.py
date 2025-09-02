"""WebSocket server implementation for MCP."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class WebSocketMCPServer:
    """WebSocket-based MCP server."""

    def __init__(self, mcp_server):
        """Initialize WebSocket server.

        Args:
            mcp_server: The main MCP server instance
        """
        self.mcp_server = mcp_server
        self.clients: set[WebSocketServerProtocol] = set()
        self.client_info: dict[str, dict] = {}

    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle WebSocket client connection.

        Args:
            websocket: WebSocket connection
            path: Connection path
        """
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"

        try:
            # Register client
            self.clients.add(websocket)
            self.client_info[client_id] = {
                "connected_at": datetime.utcnow(),
                "path": path,
                "address": websocket.remote_address
            }

            logger.info(f"Client connected: {client_id}")

            # Send welcome message
            await websocket.send(json.dumps({
                "type": "welcome",
                "server": "itglue-mcp",
                "version": "0.1.0",
                "timestamp": datetime.utcnow().isoformat()
            }))

            # Handle messages
            async for message in websocket:
                await self.handle_message(websocket, message, client_id)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")

        except Exception as e:
            logger.error(f"WebSocket error for client {client_id}: {e}", exc_info=True)

        finally:
            # Clean up
            self.clients.discard(websocket)
            if client_id in self.client_info:
                del self.client_info[client_id]

    async def handle_message(
        self,
        websocket: WebSocketServerProtocol,
        message: str,
        client_id: str
    ):
        """Handle incoming WebSocket message.

        Args:
            websocket: WebSocket connection
            message: JSON-RPC message
            client_id: Client identifier
        """
        try:
            # Parse JSON-RPC message
            data = json.loads(message)

            if "jsonrpc" not in data or data["jsonrpc"] != "2.0":
                await self.send_error(
                    websocket,
                    -32600,
                    "Invalid Request",
                    data.get("id")
                )
                return

            method = data.get("method")
            params = data.get("params", {})
            msg_id = data.get("id")

            logger.debug(f"Client {client_id} called method: {method}")

            # Route to appropriate handler
            if method == "initialize":
                await self.handle_initialize(websocket, params, msg_id)

            elif method == "query":
                await self.handle_query(websocket, params, msg_id)

            elif method == "search":
                await self.handle_search(websocket, params, msg_id)

            elif method == "sync":
                await self.handle_sync(websocket, params, msg_id)

            elif method == "health":
                await self.handle_health(websocket, msg_id)

            elif method == "list_companies":
                await self.handle_list_companies(websocket, msg_id)

            else:
                await self.send_error(
                    websocket,
                    -32601,
                    f"Method not found: {method}",
                    msg_id
                )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from client {client_id}: {e}")
            await self.send_error(websocket, -32700, "Parse error", None)

        except Exception as e:
            logger.error(f"Message handling error: {e}", exc_info=True)
            await self.send_error(
                websocket,
                -32603,
                f"Internal error: {str(e)}",
                data.get("id") if "data" in locals() else None
            )

    async def handle_initialize(
        self,
        websocket: WebSocketServerProtocol,
        params: dict,
        msg_id: Any
    ):
        """Handle initialization request.

        Args:
            websocket: WebSocket connection
            params: Initialization parameters
            msg_id: Message ID
        """
        response = {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "0.1.0",
                "serverInfo": {
                    "name": "itglue-mcp",
                    "version": "0.1.0"
                },
                "capabilities": {
                    "tools": {
                        "query": {
                            "description": "Natural language query for IT Glue"
                        },
                        "search": {
                            "description": "Cross-company search"
                        },
                        "sync": {
                            "description": "Manage data synchronization"
                        }
                    }
                }
            },
            "id": msg_id
        }

        await websocket.send(json.dumps(response))

    async def handle_query(
        self,
        websocket: WebSocketServerProtocol,
        params: dict,
        msg_id: Any
    ):
        """Handle query request.

        Args:
            websocket: WebSocket connection
            params: Query parameters
            msg_id: Message ID
        """
        # Get the query tool
        query_tool = self.mcp_server.tools.get("query")

        if not query_tool:
            await self.send_error(websocket, -32603, "Query tool not available", msg_id)
            return

        # Execute query
        result = await query_tool.execute(**params)

        # Send response
        response = {
            "jsonrpc": "2.0",
            "result": result,
            "id": msg_id
        }

        await websocket.send(json.dumps(response))

    async def handle_search(
        self,
        websocket: WebSocketServerProtocol,
        params: dict,
        msg_id: Any
    ):
        """Handle search request.

        Args:
            websocket: WebSocket connection
            params: Search parameters
            msg_id: Message ID
        """
        search_tool = self.mcp_server.tools.get("search")

        if not search_tool:
            await self.send_error(websocket, -32603, "Search tool not available", msg_id)
            return

        result = await search_tool.execute(**params)

        response = {
            "jsonrpc": "2.0",
            "result": result,
            "id": msg_id
        }

        await websocket.send(json.dumps(response))

    async def handle_sync(
        self,
        websocket: WebSocketServerProtocol,
        params: dict,
        msg_id: Any
    ):
        """Handle sync request.

        Args:
            websocket: WebSocket connection
            params: Sync parameters
            msg_id: Message ID
        """
        sync_tool = self.mcp_server.tools.get("sync")

        if not sync_tool:
            await self.send_error(websocket, -32603, "Sync tool not available", msg_id)
            return

        result = await sync_tool.execute(**params)

        response = {
            "jsonrpc": "2.0",
            "result": result,
            "id": msg_id
        }

        await websocket.send(json.dumps(response))

    async def handle_health(
        self,
        websocket: WebSocketServerProtocol,
        msg_id: Any
    ):
        """Handle health check request.

        Args:
            websocket: WebSocket connection
            msg_id: Message ID
        """
        health_tool = self.mcp_server.tools.get("health")

        if health_tool:
            result = await health_tool.execute()
        else:
            result = {
                "status": "healthy",
                "server": "itglue-mcp",
                "clients": len(self.clients)
            }

        response = {
            "jsonrpc": "2.0",
            "result": result,
            "id": msg_id
        }

        await websocket.send(json.dumps(response))

    async def handle_list_companies(
        self,
        websocket: WebSocketServerProtocol,
        msg_id: Any
    ):
        """Handle list companies request.

        Args:
            websocket: WebSocket connection
            msg_id: Message ID
        """
        companies_tool = self.mcp_server.tools.get("list_companies")

        if companies_tool:
            result = await companies_tool.execute()
        else:
            result = {
                "companies": [],
                "count": 0
            }

        response = {
            "jsonrpc": "2.0",
            "result": result,
            "id": msg_id
        }

        await websocket.send(json.dumps(response))

    async def send_error(
        self,
        websocket: WebSocketServerProtocol,
        code: int,
        message: str,
        msg_id: Any
    ):
        """Send JSON-RPC error response.

        Args:
            websocket: WebSocket connection
            code: Error code
            message: Error message
            msg_id: Message ID
        """
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            },
            "id": msg_id
        }

        await websocket.send(json.dumps(error_response))

    async def broadcast(self, message: dict[str, Any]):
        """Broadcast message to all connected clients.

        Args:
            message: Message to broadcast
        """
        if self.clients:
            message_str = json.dumps(message)
            await asyncio.gather(
                *[client.send(message_str) for client in self.clients],
                return_exceptions=True
            )

    async def run(self, host: str = "0.0.0.0", port: int = 8001):
        """Run WebSocket server.

        Args:
            host: Server host
            port: Server port
        """
        logger.info(f"Starting WebSocket MCP server on {host}:{port}")

        async with websockets.serve(self.handle_client, host, port):
            logger.info(f"WebSocket server listening on ws://{host}:{port}")
            await asyncio.Future()  # Run forever
