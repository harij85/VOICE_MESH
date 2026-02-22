"""
WebSocket client for sending commands to the brain server.
"""
import asyncio
import json
from typing import Optional, Callable, Any, Dict
import websockets
from websockets.client import WebSocketClientProtocol


class VoiceWebSocketClient:
    """WebSocket client for voice commands."""

    def __init__(self, uri: str = "ws://localhost:8765"):
        self.uri = uri
        self.ws: Optional[WebSocketClientProtocol] = None
        self.running = False

    async def connect(self) -> None:
        """Connect to WebSocket server."""
        print(f"[ws] Connecting to {self.uri}")
        try:
            self.ws = await websockets.connect(self.uri)
            print("[ws] Connected successfully")

            # Send hello message
            await self.ws.send(
                json.dumps({"type": "hello", "role": "voice_client", "version": "0.1.0"})
            )

            # Receive initial scene state
            response = await self.ws.recv()
            msg = json.loads(response)
            print(f"[ws] Received initial scene: {msg.get('type')}")

        except Exception as e:
            print(f"[ws] Connection failed: {e}")
            raise

    async def ensure_connected(self) -> None:
        """Ensure WebSocket is connected, reconnect if needed."""
        if not self.ws:
            print("[ws] Reconnecting...")
            await self.connect()
            return

        # Check if connection is still alive
        try:
            # Try to ping to verify connection
            pong = await self.ws.ping()
            await asyncio.wait_for(pong, timeout=1.0)
        except Exception:
            print("[ws] Connection lost, reconnecting...")
            await self.connect()

    async def send_command_patch(self, patch: Dict[str, Any]) -> None:
        """
        Send a command patch directly to server.

        Args:
            patch: Scene patch dict (from LLM parser)
        """
        await self.ensure_connected()

        # The brain expects commands in this format, but we're sending
        # the patch directly since we've already parsed it
        # We'll modify the brain to accept direct patches too
        message = {"type": "patch", "patch": patch}

        await self.ws.send(json.dumps(message))
        print(f"[ws] Sent patch: {patch}")

    async def send_text_command(self, text: str) -> None:
        """
        Send a text command to server (will be parsed by brain's NLU).

        Args:
            text: Natural language command text
        """
        await self.ensure_connected()

        message = {"type": "command", "text": text, "source": "voice_client"}

        await self.ws.send(json.dumps(message))
        print(f"[ws] Sent text command: '{text}'")

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        if self.ws:
            await self.ws.close()
            print("[ws] Disconnected")
            self.ws = None


async def test_websocket_client():
    """Test function: Connect and send a test command."""
    print("\n=== Step 4: WebSocket Client Test ===")
    print("This will connect to the brain server and send a test command.\n")
    print("Make sure the brain server is running:")
    print("  Terminal 1: brain\n")

    client = VoiceWebSocketClient()

    try:
        # Connect
        await client.connect()

        # Wait a moment
        await asyncio.sleep(0.5)

        # Send test command
        print("\nSending test command: 'make it red'")
        await client.send_text_command("make it red")

        # Wait for processing
        await asyncio.sleep(1)

        print("\n✓ Test passed! Command sent successfully.")
        print("\nCheck the renderer to see if the object turned red.")
        print("If it worked, the WebSocket communication is functioning.")

    except ConnectionRefusedError:
        print("\n✗ Test failed! Could not connect to brain server.")
        print("  Make sure brain is running: brain")
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
    finally:
        await client.disconnect()

    print("\nNext step: python -m brain.voice_client")


def main():
    """Run the test."""
    asyncio.run(test_websocket_client())


if __name__ == "__main__":
    main()
