from backend.includes_python.mach import Mach
import backend.includes_python.process_logging as slogger
import backend.includes_python.network_pings as network_pings
import backend.proto.generated.GSE_TO_GCS_DATA_2_pb2 as GSE_TO_GCS_DATA_2_pb
import backend.proto.generated.GSE_TO_GCS_DATA_1_pb2 as GSE_TO_GCS_DATA_1_pb
import backend.proto.generated.AV_TO_GCS_DATA_3_pb2 as AV_TO_GCS_DATA_3_pb
import backend.proto.generated.AV_TO_GCS_DATA_2_pb2 as AV_TO_GCS_DATA_2_pb
import backend.proto.generated.AV_TO_GCS_DATA_1_pb2 as AV_TO_GCS_DATA_1_pb
import config.config as config
from google.protobuf.json_format import MessageToDict
import signal
import asyncio
import contextlib
import sys
import backend.device_emulator as device_emulator
from backend.includes_python.gsedaq_metrics import GseDaqMetrics
import json
import websockets
import zmq
import zmq.asyncio
import os

# Global flag for shutdown control
shutdown_event = asyncio.Event()

# NOTE. if this starts getting big, consider just adding things from this into
# the backend server output through protobuf anyway


def append_data(data: dict, PACKET_ID: int) -> dict:
    """Add data to the websocket structure that frontend uses

    Args:
        data (dict): protobuf data as a dict
        PACKET_ID (int): packet ID from the protobuf message

    Returns:
        dict: updated output
    """
    match PACKET_ID:
        case 3:
            data["mach_number"] = Mach.mach_from_alt_estimate(
                VELOCITY_M=data["velocity"], ALTITUDE_M=data["altitude"]
            )
    return data


# TODO Find why might a compile error cause the script to fail silently when i ran an incorrect argument it failed silently without notice or throwing an error
async def zmq_to_websocket(websocket, ZMQ_SUB_SOCKET):
    FRONTEND_SOCKET_PATH = os.path.abspath(
        os.path.join(os.path.sep, "tmp", "gcs_pendant_frontend_pub.sock")
    )

    FRONTEND_SOCKET_PATH_LOGGING = os.path.abspath(
        os.path.join(os.path.sep, "tmp", "gcs_logging_frontend_pull.sock")
    )

    PENDANT_PACKET_ID = 10
    SLOGGER_PACKET_ID = 40
    NETWORK_DIAGNOSTICS_PACKET_ID = 50
    GSE_LABVIEW_TCP_PACKET_ID = 55

    PING_GAP_TIME_S = 2
    next_ping_time = asyncio.get_running_loop().time()
    tcp_gse_task = None

    try:
        context = zmq.asyncio.Context()

        server_sub_socket = context.socket(zmq.SUB)
        server_sub_socket.connect(ZMQ_SUB_SOCKET)
        server_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        pendant_sub_socket = context.socket(zmq.SUB)
        pendant_sub_socket.setsockopt(
            zmq.CONFLATE, 1
        )  # only keep the most recent state
        pendant_sub_socket.connect(f"ipc://{FRONTEND_SOCKET_PATH}")
        pendant_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        logging_sub_socket = context.socket(zmq.PULL)

        logging_sub_socket.bind(f"ipc://{FRONTEND_SOCKET_PATH_LOGGING}")

        # https://learning-0mq-with-pyzmq.readthedocs.io/en/latest/pyzmq/multisocket/zmqpoller.html
        # ^ more about Poller
        poller = zmq.Poller()
        poller.register(server_sub_socket, zmq.POLLIN)
        poller.register(pendant_sub_socket, zmq.POLLIN)
        poller.register(logging_sub_socket, zmq.POLLIN)

        gse_tcp_queue: asyncio.Queue = asyncio.Queue(maxsize=1)

        async def _tcp_gse_labview_reader():
            """Pull data from LabVIEW or from LabVIEW emulator"""
            port = int(config.get_config()["emulation"]["tcp_server_port"])
            writer = None
            try:
                reader, writer = await asyncio.open_connection(
                    "127.0.0.1", port
                )
            except OSError as e:
                slogger.error("GSE LabVIEW TCP connect failed: %s", e)
                return
            try:
                while not shutdown_event.is_set():
                    line = await reader.readline()
                    if not line:
                        break
                    while True:
                        try:
                            gse_tcp_queue.put_nowait(line)
                            break
                        except asyncio.QueueFull:
                            try:
                                gse_tcp_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                pass
            except asyncio.CancelledError:
                raise
            except Exception as e:
                slogger.error("GSE LabVIEW TCP read error: %s", e)
            finally:
                if writer is not None:
                    writer.close()
                    with contextlib.suppress(Exception):
                        await writer.wait_closed()

        tcp_gse_task = asyncio.create_task(_tcp_gse_labview_reader())

        # Reserved 40 for sending logs ignoring Protobuf
        # reserved 10 for pendant
        packet_handlers = {
            3: AV_TO_GCS_DATA_1_pb.AV_TO_GCS_DATA_1,
            4: AV_TO_GCS_DATA_2_pb.AV_TO_GCS_DATA_2,
            5: AV_TO_GCS_DATA_3_pb.AV_TO_GCS_DATA_3,
            6: GSE_TO_GCS_DATA_1_pb.GSE_TO_GCS_DATA_1,
            7: GSE_TO_GCS_DATA_2_pb.GSE_TO_GCS_DATA_2,
        }

        while not shutdown_event.is_set():
            try:
                # poll pendant_daemon socket
                events = dict(poller.poll(timeout=100))
                # print(events)
                if pendant_sub_socket in events:
                    pendant_state_dict = await pendant_sub_socket.recv_json()

                    packet = {
                        "id": PENDANT_PACKET_ID,
                        "data": pendant_state_dict,
                    }
                    try:
                        await websocket.send(json.dumps(packet))
                    except websockets.ConnectionClosedOK:
                        break

                if server_sub_socket in events:
                    packet_id = int.from_bytes(
                        await server_sub_socket.recv(), "big"
                    )
                    message = await server_sub_socket.recv()

                    if len(message) == 1:
                        new_id = int.from_bytes(message, "big")
                        slogger.error(
                            f"Message mismatch: {packet_id} vs {new_id}"
                        )
                        continue

                    if packet_id in packet_handlers:
                        proto_object = packet_handlers[packet_id]()
                        proto_object.ParseFromString(message)
                        data = MessageToDict(proto_object)
                        data = append_data(data, packet_id)
                        output = {"id": packet_id, "data": data}
                        try:
                            await websocket.send(json.dumps(output))
                        except websockets.ConnectionClosedOK:
                            slogger.debug(f"Websocket Client Disconnected")
                            break
                    else:
                        slogger.error(f"Unexpected packet ID: {packet_id}")

                if asyncio.get_running_loop().time() > next_ping_time:
                    ping_results = await network_pings.ping_manifest()
                    packet = {
                        "id": NETWORK_DIAGNOSTICS_PACKET_ID,
                        "data": ping_results
                    }
                    try:
                        await websocket.send(json.dumps(packet))
                    except websockets.ConnectionClosedOK:
                        break
                    next_ping_time = asyncio.get_running_loop().time() + PING_GAP_TIME_S

                try:
                    # as mentioned in [labview_row_bytes_to_data_dict] this line
                    # is assumed to be a complete tag.
                    # otherwise the xml match will fail and throw valueerror
                    gse_line = gse_tcp_queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                else:
                    try:
                        gse_data = GseDaqMetrics.labview_row_bytes_to_data_dict(
                            gse_line
                        )
                        output = {
                            "id": GSE_LABVIEW_TCP_PACKET_ID,
                            "data": gse_data,
                        }
                        await websocket.send(json.dumps(output))
                    except (ValueError, SyntaxError, TypeError) as e:
                        slogger.warning("GSE LabVIEW row parse skip: %s", e)
                    except websockets.ConnectionClosedOK:
                        break

                if logging_sub_socket in events:
                    message = await logging_sub_socket.recv_json()

                    log_dicts = []

                    # Go through buffer of logs sent through from handler
                    for entry in message:
                        # Check if correct amount of passed data
                        if len(entry) == 3:
                            # Append passed logs in correct format to be sent to all web clients
                            log_dicts.append(
                                {
                                    "timestamp": entry[0],
                                    "level": entry[1],
                                    "message": entry[2],
                                }
                            )
                        else:
                            slogger.warning(
                                "Frontend logging passthrough Received incorrect packet"
                            )

                    if log_dicts:
                        output = {
                            "id": SLOGGER_PACKET_ID,
                            "data": {"slogger": log_dicts},
                        }

                        try:
                            await websocket.send(json.dumps(output))
                        except websockets.ConnectionClosedOK as ex:
                            slogger.debug(f"Websocket Client Disconnected")
                            break  # critical to break out of loop and not pass otherwise will get stuck trying to send to dead client

                    else:
                        slogger.warning(
                            "Malformed data sent upstream to front end"
                        )

                # Give event handler time to check shutdown event
                await asyncio.sleep(0.01)
            except websockets.ConnectionClosed:
                if not shutdown_event.is_set():
                    slogger.info(
                        "WebSocket connection closed from manager trigger"
                    )
                else:
                    slogger.info("WebSocket connection closed from ws client")
                break
            except Exception as e:
                slogger.error(f"Error forwarding data to websocket: {e}")
                if shutdown_event.is_set():
                    break
    except Exception as e:
        slogger.critical(f"error with frontend api: {e}")
    finally:
        if tcp_gse_task is not None:
            tcp_gse_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await tcp_gse_task
        # Wait LINGER_TIME_MS before giving up on push request
        LINGER_TIME_MS = 300
        server_sub_socket.close(linger=LINGER_TIME_MS)
        pendant_sub_socket.close(linger=LINGER_TIME_MS)
        logging_sub_socket.close(linger=LINGER_TIME_MS)
        context.term()


async def consumer(websocket):
    context = zmq.asyncio.Context()
    try:
        push_socket = context.socket(zmq.PUSH)
        SOCKET_PATH = os.path.abspath(
            os.path.join(os.path.sep, "tmp", "gcs_rocket_web_pull.sock")
        )
        LINGER_TIME_MS = 300
        push_socket.setsockopt(zmq.LINGER, LINGER_TIME_MS)
        push_socket.setsockopt(zmq.SNDHWM, 1)  # Limit send buffer to 1 message
        push_socket.setsockopt(zmq.CONFLATE, 1)  # Replace old messages
        push_socket.connect(f"ipc://{SOCKET_PATH}")
        EXPECTED_IDS = [0x09, 253]  # What ID should we relay to the server?
        slogger.debug("New websocket consumer started")
        try:
            async for message in websocket:
                if shutdown_event.is_set():
                    break
                try:
                    # TODO remove this after bundy testing
                    slogger.debug(f"Received ws message: {message}")
                    try:
                        message_json = json.loads(message)
                    except json.JSONDecodeError as e:
                        slogger.error(f"Invalid JSON received: {e}")
                        continue
                    if message_json.get("id") not in EXPECTED_IDS:
                        slogger.error(
                            f"Invalid packet ID for TX: {message_json.get('id')}. Expected in {EXPECTED_IDS}"
                        )
                        continue
                    data = message_json.get("data", None)
                    if data is None or len(data.keys()) == 0:
                        slogger.error("No data found in message")
                        continue
                    if message_json["id"] == 0x09:
                        packet = build_packet(data)
                        packet_bytes = packet.get_payload_bytes(EXTERNAL=True)
                        # Prepend the manual control bool as a byte to tell server
                        manual_control = data.get("manualEnabled", False)
                        if isinstance(manual_control, bool):
                            prefix = bytes([0xFF if manual_control else 0x00])
                        else:
                            slogger.error(
                                f"Manual control field contains non-bool {manual_control}"
                            )
                            continue
                        packet_bytes = bytes(prefix) + packet_bytes
                    elif message_json["id"] == 253:
                        # {"id":253,"data":{"cameraStatus":false}}
                        camera_status = message_json["data"].get(
                            "cameraStatus", True
                        )
                        if not isinstance(camera_status, bool):
                            camera_status = True
                        if camera_status:
                            packet_bytes = (123).to_bytes(1, byteorder="big")
                        else:
                            packet_bytes = (100).to_bytes(1, byteorder="big")
                    await push_socket.send(packet_bytes, flags=zmq.NOBLOCK)
                except json.JSONDecodeError as e:
                    slogger.error(f"Invalid JSON received: {e}")
                except KeyError as e:
                    slogger.error(f"Missing required key in message: {e}")
                except Exception as e:
                    slogger.error(
                        f"Error processing message: {e}. Socket may be full at HWM"
                    )
        except websockets.ConnectionClosedOK:
            if not shutdown_event.is_set():
                slogger.info(
                    "WebSocket connection closed in consumer from web side"
                )
            else:
                slogger.info(
                    "WebSocket connection closed in consumer from manager trigger"
                )
        except Exception as e:
            slogger.error(f"Consumer error: {e}")
    finally:
        slogger.debug("ZMQ socket closing")
        push_socket.close(linger=LINGER_TIME_MS)
        context.term()
        slogger.debug("Consumer ZMQ context terminated")


def build_packet(WEBSOCKET_DATA: dict) -> device_emulator.GCStoGSEManualControl:
    """An adaptor to convert internal websocket payload for manual actuation into lora packet GCS to GSE MANUAL CONTROL

    Args:
        WEBSOCKET_DATA (dict): Data in the format of post translation packet 0x09

    Returns:
        device_emulator.GCStoGSEManualControl: Output packet to be written to lora
    """

    PURGE_HIGH: bool = WEBSOCKET_DATA.get("solenoid1High", False)
    N2O_HIGH: bool = WEBSOCKET_DATA.get("solenoid2High", False)
    O2_HIGH: bool = WEBSOCKET_DATA.get("solenoid3High", False)
    states = {
        "MANUAL_PURGE": PURGE_HIGH,
        "O2_FILL_ACTIVATE": O2_HIGH,
        "SELECTOR_SWITCH_NEUTRAL_POSITION": False,
        "N2O_FILL_ACTIVATE": N2O_HIGH,
        "IGNITION_FIRE": False,
        "IGNITION_SELECTED": True,
        "GAS_FILL_SELECTED": True,
        "SYSTEM_ACTIVATE": True,
    }
    return device_emulator.GCStoGSEManualControl(**states)


async def handler(websocket):
    # start both producer and consumer
    producer_task = asyncio.create_task(
        zmq_to_websocket(websocket, IPC_ADDRESS)
    )
    consumer_task = asyncio.create_task(consumer(websocket))

    try:
        # wait until one side throws an exception or shutdown is requested
        done, pending = await asyncio.wait(
            [producer_task, consumer_task], return_when=asyncio.FIRST_EXCEPTION
        )

        if shutdown_event.is_set():
            await websocket.close(code=1001, reason="Server shutting down")
    except Exception as e:
        slogger.error(f"Handler error: {e}")
    finally:
        for task in pending:
            task.cancel()
        await websocket.close()


async def amain():
    # Set up signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: shutdown_event.set())

    server = await websockets.serve(handler, WEBSOCKET_HOST, WEBSOCKET_PORT)
    slogger.secret(
        f"WebSocket server started at ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}"
    )

    try:
        await shutdown_event.wait()
    finally:
        slogger.info("Shutting down server...")
        for ws in server.connections:
            await ws.close(code=1001, reason="Server shutdown")
        server.close()
        await server.wait_closed()
        slogger.info("Server shutdown complete")


def main():

    global WEBSOCKET_HOST, WEBSOCKET_PORT, IPC_ADDRESS

    # get_newest_messages()
    WEBSOCKET_HOST = "0.0.0.0"
    WEBSOCKET_PORT = 1887

    if "--socket-path" in sys.argv:
        SOCKET_PATH = sys.argv[sys.argv.index("--socket-path") + 1]
        IPC_ADDRESS = f"ipc:///tmp/{SOCKET_PATH}_pub.sock"
    else:
        slogger.error("Missing required --socket-path argument")
        sys.exit(1)

    device_emulator.MockPacket.initialize_settings(
        config.get_config()["emulation"]
    )

    try:
        asyncio.run(amain())
    finally:
        slogger.info("Application exited")


if __name__ == "__main__":
    main()
