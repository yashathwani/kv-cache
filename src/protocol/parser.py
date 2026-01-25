"""
Protocol Parser Module (Task 2)

This module handles parsing of raw protocol commands and formatting of responses.

Students must implement:
- parse_request(): Parse a raw command string into a Command object
- format_response(): Format a Response object into a protocol string
"""

from .commands import Command, CommandType, Response , ResponseStatus
from ..config.settings import settings


class ProtocolParser:
    """
    Parser for the KV-Cache text protocol.

    Protocol Format:
        Request:  <COMMAND> [ARGS...]\n
        Response: <STATUS> [DATA]\n

    Commands:
        PUT <key> <value> [ttl]  -> OK stored
        GET <key>                -> OK <value> | ERROR key not found
        DELETE <key>             -> OK deleted | ERROR key not found
        EXISTS <key>             -> OK 1 | OK 0
        QUIT                     -> (connection closed)

    Constraints:
        - Keys: max 256 characters, no whitespace
        - Values: max 256 characters, no whitespace
        - TTL: non-negative integer (0 = no expiration)
    """

    def __init__(self):
        """Initialize the parser with constraints from settings."""
        self.max_key_length = settings.MAX_KEY_LENGTH
        self.max_value_length = settings.MAX_VALUE_LENGTH

    def parse_request(self, data: str) -> Command:
        """
        Parse a raw request string into a Command object.

        Args:
            data: Raw request string (may include trailing newline)

        Returns:
            Command object representing the parsed request.
            Returns Command with type=UNKNOWN for invalid/malformed requests.

        Examples:
            >>> parser = ProtocolParser()
            >>> cmd = parser.parse_request("PUT mykey myvalue 60")
            >>> cmd.type == CommandType.PUT
            True
            >>> cmd.key
            'mykey'
            >>> cmd.value
            'myvalue'
            >>> cmd.ttl
            60

        Implementation hints:
            - Strip whitespace and split the input
            - Identify the command type (case-insensitive)
            - Extract arguments based on command type
            - Validate key/value length constraints
            - Handle errors gracefully (return UNKNOWN command)
        """
        # === TODO START: Implement parse_request ===
        if not data:
            return Command(type=CommandType.UNKNOWN, raw=data)
    
        raw = data.strip()
        if not raw:
            return Command(type=CommandType.UNKNOWN, raw=data)
        
        parts = raw.split()
        cmd = parts[0].upper()


        
        if cmd == CommandType.PUT.name:
            return self._parse_put(parts, raw)
        elif cmd == CommandType.GET.name:
            return self._parse_get(parts, raw)
        elif cmd == CommandType.DELETE.name:
            return self._parse_delete(parts, raw)
        elif cmd == CommandType.EXISTS.name:
            return self._parse_exists(parts, raw)
        elif cmd == CommandType.QUIT.name:
            if len(parts) != 1:
                return Command(type=CommandType.UNKNOWN, raw=data)
            return Command(type=CommandType.QUIT, raw=data)
        else:
            return Command(type=CommandType.UNKNOWN, raw=data)
        
        # === TODO END ===

    def _parse_put(self, parts: list, raw: str) -> Command:
        """
        Parse a PUT command.

        Format: PUT <key> <value> [ttl]

        Args:
            parts: List of command parts (already split)
            raw: Original raw command string

        Returns:
            Command object for PUT, or UNKNOWN if invalid
        """
        # === TODO START: Implement _parse_put ===
        if len(parts) not in (3, 4):
            return Command(type=CommandType.UNKNOWN, raw=raw)
        
        _, key, value, *ttl_part = parts

        if len(key) > self.max_key_length or len(value) > self.max_value_length:
            return Command(type=CommandType.UNKNOWN, raw=raw)
        
        ttl = 0
        if ttl_part:
            try:
                ttl = int(ttl_part[0])
                if ttl < 0:
                    return Command(type=CommandType.UNKNOWN, raw=raw)
            except ValueError:
                return Command(type=CommandType.UNKNOWN, raw=raw)
            
        return Command(type=CommandType.PUT, key=key, value=value, ttl=ttl, raw=raw)
        # === TODO END ===

    def _parse_get(self, parts: list, raw: str) -> Command:
        """
        Parse a GET command.

        Format: GET <key>
        """
        # === TODO START: Implement _parse_get ===
        if len(parts) != 2:
            return Command(type=CommandType.UNKNOWN, raw=raw)
        
        _,key=parts

        if len(key) > self.max_key_length:
            return Command(type=CommandType.UNKNOWN, raw=raw)
        
        return Command(type=CommandType.GET, key=key, raw=raw)
        # === TODO END ===

    def _parse_delete(self, parts: list, raw: str) -> Command:
        """
        Parse a DELETE command.

        Format: DELETE <key>
        """
        # === TODO START: Implement _parse_delete ===
        if len(parts) != 2:
            return Command(type=CommandType.UNKNOWN, raw=raw)
        
        _,key=parts
        if len(key) > self.max_key_length:
            return Command(type=CommandType.UNKNOWN, raw=raw)
        
        return Command(type=CommandType.DELETE, key=key, raw=raw)
        # === TODO END ===

    def _parse_exists(self, parts: list, raw: str) -> Command:
        """
        Parse an EXISTS command.

        Format: EXISTS <key>
        """
        # === TODO START: Implement _parse_exists ===
        if len(parts) != 2:
            return Command(type=CommandType.UNKNOWN, raw=raw)
        
        _,key=parts
        if len(key) > self.max_key_length:
            return Command(type=CommandType.UNKNOWN, raw=raw)
        return Command(type=CommandType.EXISTS, key=key, raw=raw)
        # === TODO END ===

    def format_response(self, response: Response) -> str:
        """
        Format a Response object into a protocol string.

        Args:
            response: Response object to format

        Returns:
            Formatted response string WITH trailing newline.

        Examples:
            >>> parser = ProtocolParser()
            >>> parser.format_response(Response.stored())
            'OK stored\\n'
            >>> parser.format_response(Response.value_response("hello"))
            'OK hello\\n'
            >>> parser.format_response(Response.error("key not found"))
            'ERROR key not found\\n'

        Implementation hints:
            - Format based on response status (OK or ERROR)
            - For GET responses, include the value
            - For other responses, include the message
            - Always end with newline character
        """
        # === TODO START: Implement format_response ===
        if response.status == ResponseStatus.OK:
            if response.value is not None:
                return f"OK {response.value}\n"
            if response.message:
                return f"OK {response.message}\n"
            return "OK\n"
        else:
            return f"ERROR {response.message}\n"
        # === TODO END ===
