import asyncio
import websockets
from websockets.server import WebSocketServerProtocol

from .state import SceneState
from .nlu import parse_command
from .protocol import dumps, loads

CLIENTS: set[WebSocketServerProtocol] = set()

async def broadcast(state: SceneState) -> None:
    msg = dumps(state.to_message())
    dead = []
    for ws in CLIENTS:
        try:
            await ws.send(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        CLIENTS.discard(ws)

async def handler(ws: WebSocketServerProtocol) -> None:
    CLIENTS.add(ws)
    state = handler.state  # shared state across clients
    await ws.send(dumps(state.to_message()))

    try:
        async for raw in ws:
            msg = loads(raw)
            mtype = msg.get("type")

            if mtype == "hello":
                continue

            if mtype == "command":
                text = str(msg.get("text", ""))
                patch = parse_command(text)
                if patch:
                    state.apply_patch(patch)
                    await broadcast(state)
                continue

            if mtype == "patch":
                # Direct patch from voice client (already parsed by LLM)
                patch = msg.get("patch", {})
                if patch:
                    state.apply_patch(patch)
                    await broadcast(state)
                continue

            # ignore unknown messages
    finally:
        CLIENTS.discard(ws)

handler.state = SceneState.new()  # type: ignore[attr-defined]

async def run(host: str = "0.0.0.0", port: int = 8765) -> None:
    async with websockets.serve(
        handler,
        host,
        port,
        ping_interval=60,  # Send ping every 60 seconds
        ping_timeout=60,   # Wait 60 seconds for pong before closing
    ):
        print(f"[brain] ws://{host}:{port}")
        while True:
            await asyncio.sleep(3600)

def main() -> None:
    asyncio.run(run())