import asyncio
from typing import Never
import websockets
import json
from config import config

# only read these packets
PACKETS_TO_DEBUG = [50]
DEBUG_ALL_PACKETS = False


async def pretty_print_json(uri: str) -> Never:
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print(f"Connected to {uri}")
                while True:
                    message = await websocket.recv()
                    try:
                        json_data = json.loads(message)

                        if isinstance(json_data, dict):
                            packet_id = json_data.get("id")
                            if (
                                packet_id in PACKETS_TO_DEBUG
                                or DEBUG_ALL_PACKETS
                            ):
                                print(json.dumps(json_data, indent=4))
                    except json.JSONDecodeError:
                        print("Non-JSON message received:")
                        print(message)
        except (websockets.ConnectionClosed, ConnectionRefusedError, OSError):
            print("WebSocket connection lost. Reconnecting in 1s...")
            await asyncio.sleep(1)


if __name__ == "__main__":
    frontend_config = config.get_config()["frontend"]
    ws_host = frontend_config.get("ws_host")
    ws_port = frontend_config.get("ws_port")
    uri = f"ws://{ws_host}:{ws_port}"
    asyncio.run(pretty_print_json(uri))
