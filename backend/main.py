import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from bot.config import Config
from bot.engine import BotEngine


class Hub:
    def __init__(self):
        self.loop = None
        self.subs = set()

    def publish_log(self, line):
        if self.loop is None:
            return
        self.loop.call_soon_threadsafe(self._fan, {"type": "log", "msg": line})

    def _fan(self, payload):
        for q in list(self.subs):
            q.put_nowait(payload)


hub = Hub()
config = Config()
engine = BotEngine(config, log=hub.publish_log)


def state_payload():
    return {
        "type": "state",
        "running": engine.running,
        "features": engine.features,
        "counters": engine.counters,
        "settings": {
            "max_runtime_minutes": config.max_runtime_minutes,
            "debug": config.debug,
            "allowed_grades": config.synthesis_allowed_grades,
            "calibrated": bool(config.synthesis_grid_rect and config.stash_grid_rect),
        },
    }


@asynccontextmanager
async def lifespan(app):
    hub.loop = asyncio.get_event_loop()
    yield
    engine.stop()


app = FastAPI(lifespan=lifespan, title="TBH AFK Bot")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/api/state")
def get_state():
    return state_payload()


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    q: asyncio.Queue = asyncio.Queue()
    hub.subs.add(q)
    await q.put(state_payload())

    async def reader():
        while True:
            data = await websocket.receive_json()
            cmd = data.get("cmd")
            if cmd == "start":
                engine.start()
            elif cmd == "stop":
                engine.stop()
            elif cmd == "toggle":
                engine.set_feature(data["feature"], data["enabled"])
            elif cmd == "set_max_runtime":
                config.max_runtime_minutes = int(data["value"])
            elif cmd == "set_debug":
                config.debug = bool(data["value"])
            await q.put(state_payload())

    async def writer():
        while True:
            await websocket.send_json(await q.get())

    try:
        await asyncio.gather(reader(), writer())
    except WebSocketDisconnect:
        pass
    finally:
        hub.subs.discard(q)
