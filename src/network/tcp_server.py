"""
Async TCP Server Module (Task 3)

This module implements the asynchronous TCP server for KV-Cache.

Students must implement:
- handle_client(): Handle a single client connection
- start(): Start the server and accept connections

Key asyncio concepts needed:
- asyncio.start_server(): Create a TCP server
- StreamReader.readline(): Read a line from client
- StreamWriter.write() / drain(): Send data to client
- Proper connection cleanup with writer.close() / wait_closed()
"""

import asyncio
from csv import writer
import logging
from asyncio import StreamReader, StreamWriter
from typing import Optional

from ..cache.store import KVStore
from ..config.settings import settings
from ..protocol.commands import CommandType, Response
from ..protocol.parser import ProtocolParser
import os


from ..cluster.config import (
    NODES,
    get_shard_id,
    get_primary_node,
    get_replica_node,
)


# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KVServer:
    """
    Asynchronous TCP server for the KV-Cache service.

    This server handles multiple concurrent clients using asyncio.
    Each client connection is handled in a separate coroutine,
    allowing for high concurrency without threading.

    Features:
    - Non-blocking I/O with asyncio
    - Persistent connections (multiple commands per connection)
    - Graceful error handling and connection cleanup
    - Shared KVStore across all connections

    Usage:
        server = KVServer(host='0.0.0.0', port=7171)
        await server.start()  # Runs forever

    Attributes:
        host: Server bind address (e.g., '0.0.0.0')
        port: Server port number (e.g., 7171)
        store: The KVStore instance shared by all connections
        parser: The ProtocolParser for parsing commands
    """

    def __init__(
            self,
            host: str = None,
            port: int = None,
            store: KVStore = None,
            node_id: int = None,
    ):
        """
        Initialize the server.

        Args:
            host: Bind address (default from settings)
            port: Port number (default from settings)
            store: KVStore instance (creates new one if not provided)
        """
        self.host = host if host is not None else settings.HOST
        self.port = port if port is not None else settings.PORT
        self.store = store if store is not None else KVStore()
        self.parser = ProtocolParser()

        self.node_id = node_id if node_id is not None else int(os.getenv("NODE_ID", "1")) 
        # Server state
        self._server: Optional[asyncio.Server] = None
        self._running = False
        self._connection_count = 0
        self._total_requests = 0

    async def handle_client(
            self,
            reader: StreamReader,
            writer: StreamWriter
    ) -> None:
        """
        Handle a single client connection.

        This coroutine is called for each new client connection.
        It reads commands from the client, processes them, and sends
        responses until the client disconnects or sends QUIT.

        Args:
            reader: StreamReader for reading from the client
            writer: StreamWriter for writing to the client

        Protocol flow:
            1. Read a line (command) from the client
            2. Parse the command using ProtocolParser
            3. Execute the command on the KVStore
            4. Format and send the response
            5. Repeat until QUIT or client disconnects

        Implementation requirements:
        - Get client address for logging (writer.get_extra_info('peername'))
        - Loop reading lines until empty data (disconnect) or QUIT
        - Handle decode errors gracefully
        - Always close the writer in a finally block
        - Handle ConnectionResetError and other exceptions
        """
        # === TODO START: Implement handle_client ===
        peer = writer.get_extra_info("peername")
        self._connection_count += 1
        logger.debug(f"Client connected: {peer}")

        try:
            while True:
                data = await reader.readline()
                if not data:
                    logger.debug(f"Client disconnected: {peer}")
                    break

                try:
                    text = data.decode().strip()
                except UnicodeDecodeError:
                    response = Response.error("invalid encoding")
                    writer.write(self.parser.format_response(response).encode())
                    await writer.drain()
                    continue

                command = self.parser.parse_request(text)
                self._total_requests += 1

                if command.type == CommandType.QUIT:
                    logger.debug(f"Client sent QUIT: {peer}")
                    break
                
                if not command.is_valid:
                    response = Response.error("invalid command")
                    writer.write(self.parser.format_response(response).encode())
                    await writer.drain()
                    continue
               

                shard = get_shard_id(command.key)
                primary = get_primary_node(shard)

                if primary != self.node_id:
                    response = await self._forward(command, primary)
                else:
                    response = await self._execute_primary(command)

                writer.write(self.parser.format_response(response).encode())
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
            logger.debug(f"Connection closed: {peer}")            

        # === TODO END ===

    def _execute_command(self, command) -> Response:
        """
        Execute a parsed command on the store.

        This is a helper method that routes commands to the appropriate
        KVStore method and returns the formatted response.

        Args:
            command: The Command object to execute

        Returns:
            Response object with the result
        """
        # === TODO START: Implement _execute_command ===
        if command.type == CommandType.PUT:
            self.store.put(command.key, command.value, command.ttl)
            return Response.stored()
        
        elif command.type == CommandType.GET:
            value = self.store.get(command.key)
            if value is not None:
                return Response.value_response(value)
            else:
                return Response.key_not_found()
            
        elif command.type == CommandType.DELETE:
            deleted = self.store.delete(command.key)
            if deleted:
                return Response.deleted()
            else:
                return Response.key_not_found()

        elif command.type == CommandType.EXISTS:
            return Response.exists_response(self.store.exists(command.key))

        return Response.error("unknown command")        
        # === TODO END ===
    async def _execute_primary(self, command) -> Response:
        """Execute on primary & replicate if needed"""

        # PUT
        if command.type == CommandType.PUT:
            self.store.put(command.key, command.value, command.ttl)

            # === REPLICATION ===
            shard = get_shard_id(command.key)
            replica = get_replica_node(shard)
            if replica != self.node_id:
                await self._forward(command, replica)

            return Response.stored()

        # DELETE
        if command.type == CommandType.DELETE:
            ok = self.store.delete(command.key)

            shard = get_shard_id(command.key)
            replica = get_replica_node(shard)
            if replica != self.node_id:
                await self._forward(command, replica)

            return Response.deleted() if ok else Response.key_not_found()

        # READS (Primary only)
        if command.type == CommandType.GET:
            val = self.store.get(command.key)
            return Response.value_response(val) if val else Response.key_not_found()

        if command.type == CommandType.EXISTS:
            return Response.exists_response(self.store.exists(command.key))

        return Response.error("invalid command")

    async def _forward(self, command, node_id: int) -> Response:
        """Forward command to another node"""
        node = NODES[node_id]

        reader, writer = await asyncio.open_connection(
            node["host"], node["port"]
        )

        writer.write((command.raw + "\n").encode())
        await writer.drain()

        data = await reader.readline()
        writer.close()
        await writer.wait_closed()
        text = data.decode().strip()

        if text.startswith("OK"):
            if text == "OK":
                return Response.ok()
            return Response.ok(text[3:])
        else:
            return Response.error(text[6:])
    
         
    async def start(self) -> None:
        """
        Start the server and begin accepting connections.

        This method creates the asyncio server and runs forever
        (or until cancelled). It should be called from asyncio.run()
        or within an existing event loop.

        Implementation:
        - Use asyncio.start_server() with self.handle_client as callback
        - Log the server address when started
        - Use server.serve_forever() to run indefinitely

        Example:
            server = KVServer(port=7171)
            asyncio.run(server.start())
        """
        # === TODO START: Implement start ===
        self._server = await asyncio.start_server(
            self.handle_client,
            host=self.host,
            port=self.port
        )

        self._running = True
        logger.info(f"Server started on {self.host}:{self.port}")

        async with self._server:
            await self._server.serve_forever()
        # === TODO END ===

    async def stop(self) -> None:
        """
        Stop the server gracefully.

        Closes the server and waits for it to fully shut down.
        """
        # === TODO START: Implement stop ===
        if self._server :
            self._server.close()
            await self._server.wait_closed()
            self._running = False
            logger.info("Server stopped")
        # === TODO END ===

    def is_running(self) -> bool:
        """Check if the server is currently running."""
        return self._running

    def get_stats(self) -> dict:
        """
        Get server statistics.

        Returns:
            Dictionary with server stats including connection counts,
            request counts, and store statistics.
        """
        return {
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "total_connections": self._connection_count,
            "total_requests": self._total_requests,
            "store_stats": self.store.get_stats(),
        }


async def run_server(host: str = None, port: int = None) -> None:
    """
    Convenience function to create and run the server.

    Args:
        host: Bind address (default from settings)
        port: Port number (default from settings)

    Usage:
        asyncio.run(run_server(port=7171))
    """
    server = KVServer(host=host, port=port)

    try:
        await server.start()
    except asyncio.CancelledError:
        logger.info("Server shutdown requested")
    finally:
        await server.stop()
