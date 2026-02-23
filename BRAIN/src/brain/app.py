import asyncio
import threading
import websockets
from websockets.server import WebSocketServerProtocol

from .state import SceneState
from .nlu import parse_command
from .protocol import dumps, loads
from .shape_gen import ShapeGenerator
from . import mesh_server

CLIENTS: set[WebSocketServerProtocol] = set()

_generator = ShapeGenerator()
_gen: dict = {"cancel": threading.Event(), "task": None}
_gen["cancel"].set()  # nothing active at startup


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


async def _generate_shape_task(
    state: SceneState, prompt: str, cancel: threading.Event, loop: asyncio.AbstractEventLoop
) -> None:
    """Runs shape generation off the event-loop thread, broadcasts result."""
    try:
        url = await loop.run_in_executor(None, _generator.generate, prompt, cancel)
    except Exception as exc:
        print(f"[shape_gen] ERROR generating '{prompt}': {exc}")
        import traceback; traceback.print_exc()
        if not cancel.is_set():
            state.apply_patch({"generating": False})
            await broadcast(state)
        return

    if url and not cancel.is_set():
        # Convert file:// → http://localhost:8766/<filename>
        filename = url.split("/")[-1]
        http_url = f"http://localhost:{mesh_server.PORT}/{filename}"
        print(f"[shape_gen] ready: {http_url}")
        state.apply_patch({"generating": False, "mesh_url": http_url})
        await broadcast(state)
    elif not cancel.is_set():
        # generate() returned None without cancellation — reset spinner
        state.apply_patch({"generating": False})
        await broadcast(state)


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

                    # Trigger Shap-E when an object was identified
                    if "object" in patch:
                        _gen["cancel"].set()  # signal old thread to stop
                        _gen["cancel"] = threading.Event()  # fresh event for new task
                        state.apply_patch({"generating": True, "mesh_url": None})
                        await broadcast(state)
                        prompt = patch["object"].get("name", "object")
                        loop = asyncio.get_running_loop()
                        _gen["task"] = asyncio.create_task(
                            _generate_shape_task(state, prompt, _gen["cancel"], loop)
                        )
                continue

            if mtype == "patch":
                # Direct patch from voice client (already parsed by LLM)
                patch = msg.get("patch", {})
                if patch:
                    state.apply_patch(patch)
                    await broadcast(state)

                    # Trigger Shap-E when an object was identified
                    if "object" in patch:
                        _gen["cancel"].set()
                        _gen["cancel"] = threading.Event()
                        state.apply_patch({"generating": True, "mesh_url": None})
                        await broadcast(state)
                        prompt = patch["object"].get("name", "object")
                        loop = asyncio.get_running_loop()
                        _gen["task"] = asyncio.create_task(
                            _generate_shape_task(state, prompt, _gen["cancel"], loop)
                        )
                continue

            # ignore unknown messages
    finally:
        CLIENTS.discard(ws)


handler.state = SceneState.new()  # type: ignore[attr-defined]


async def run(host: str = "0.0.0.0", port: int = 8765) -> None:
    mesh_server.start()  # start HTTP server for PLY files on port 8766
    async with websockets.serve(
        handler,
        host,
        port,
        ping_interval=None,  # Disable server-initiated pings — generation can take minutes
        ping_timeout=None,   # Don't timeout on client pings during long operations
    ):
        print(f"[brain] ws://{host}:{port}")
        print(f"[brain] mesh http://0.0.0.0:{mesh_server.PORT}")
        while True:
            await asyncio.sleep(3600)


def main() -> None:
    asyncio.run(run())
