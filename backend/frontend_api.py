from backend.includes_python.mach import Mach
import backend.includes_python.process_logging as slogger
import backend.proto.generated.GSE_TO_GCS_DATA_2_pb2 as GSE_TO_GCS_DATA_2_pb
import backend.proto.generated.GSE_TO_GCS_DATA_1_pb2 as GSE_TO_GCS_DATA_1_pb
import backend.proto.generated.AV_TO_GCS_DATA_3_pb2 as AV_TO_GCS_DATA_3_pb
import backend.proto.generated.AV_TO_GCS_DATA_2_pb2 as AV_TO_GCS_DATA_2_pb
import backend.proto.generated.AV_TO_GCS_DATA_1_pb2 as AV_TO_GCS_DATA_1_pb
import config.config as config
from google.protobuf.json_format import MessageToDict
import signal
import asyncio
import sys
import backend.device_emulator as device_emulator
import json
import websockets
import zmq
import zmq.asyncio
import os

# Global flag for shutdown control
shutdown_event = asyncio.Event()

# NOTE. if this starts getting big, consider just adding things from this into
# the backend server output through protobuf anyway


def append_data(data: dict, packet_id: int) -> dict:
    """Add data to the websocket structure that frontend uses

    Args:
        data (dict): protobuf data as a dict
        packet_id (int): packet ID from the protobuf message

    Returns:
        dict: updated output
    """
    match packet_id:
        case 3:
            data["mach_number"] = Mach.mach_from_alt_estimate(
                VELOCITY_M=data["velocity"], ALTITUDE_M=data["altitude"]
            )
    return data




# TODO Find why might a compile error cause the script to fail silently when i ran an incorrect argument it failed silently without notice or throwing an error
async def zmq_to_websocket(websocket, zmq_sub_socket) -> None:
    frontend_socket_path = os.path.abspath(
        os.path.join(os.path.sep, "tmp", "gcs_pendant_frontend_pub.sock")
    )

    frontend_socket_path_logging = os.path.abspath(
        os.path.join(os.path.sep, "tmp", "gcs_logging_frontend_pull.sock")
    )

    pendant_packet_id = 10
    slogger_packet_id = 40

    try:
        context = zmq.asyncio.Context()

        server_sub_socket = context.socket(zmq.SUB)
        server_sub_socket.connect(zmq_sub_socket)
        server_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        pendant_sub_socket = context.socket(zmq.SUB)
        pendant_sub_socket.setsockopt(
            zmq.CONFLATE, 1
        )  # only keep the most recent state
        pendant_sub_socket.connect(f"ipc://{frontend_socket_path}")
        pendant_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        logging_sub_socket = context.socket(zmq.SUB)
        logging_sub_socket.connect(f"ipc://{frontend_socket_path_logging}")
        logging_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        # https://learning-0mq-with-pyzmq.readthedocs.io/en/latest/pyzmq/multisocket/zmqpoller.html
        # ^ more about Poller
        poller = zmq.Poller()
        poller.register(server_sub_socket, zmq.POLLIN)
        poller.register(pendant_sub_socket, zmq.POLLIN)
        poller.register(logging_sub_socket, zmq.POLLIN)

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
                #print(events)
                if pendant_sub_socket in events:
                    pendant_state_dict = await pendant_sub_socket.recv_json()

                    packet = {
                        "id": pendant_packet_id,
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
                            slogger.debug("Websocket Client Disconnected")
                            break
                    else:
                        slogger.error(f"Unexpected packet ID: {packet_id}")

                if logging_sub_socket in events:
                    message = await logging_sub_socket.recv_json()

                    log_dicts = []
                    
                    # Go through buffer of logs sent through from handler
                    for entry in message:
                        # Check if correct amount of passed data
                        if(len(entry) == 3):
                            # Append passed logs in correct format to be sent to all web clients
                            log_dicts.append({"timestamp": entry[0], "level": entry[1], "message": entry[2]})
                        else:
                            slogger.warning("Frontend logging passthrough Received incorrect packet")

                    if log_dicts:
                        output = {
                            "id": slogger_packet_id,
                            "data": {"slogger": log_dicts},
                        }

                        try:
                            await websocket.send(json.dumps(output))
                        except websockets.ConnectionClosedOK:
                            slogger.debug("Websocket Client Disconnected")
                            break  # critical to break out of loop and not pass otherwise will get stuck trying to send to dead client

                    else:
                        slogger.warning("Malformed data sent upstream to front end")

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
        # Wait linger_time_ms before giving up on push request
        linger_time_ms = 300
        server_sub_socket.close(linger=linger_time_ms)
        pendant_sub_socket.close(linger=linger_time_ms)
        logging_sub_socket.close(linger=linger_time_ms)
        context.term()


async def consumer(websocket) -> None:
    context = zmq.asyncio.Context()
    try:
        push_socket = context.socket(zmq.PUSH)
        socket_path = os.path.abspath(
            os.path.join(os.path.sep, "tmp", "gcs_rocket_web_pull.sock")
        )
        linger_time_ms = 300
        push_socket.setsockopt(zmq.LINGER, linger_time_ms)
        push_socket.setsockopt(zmq.SNDHWM, 1)  # Limit send buffer to 1 message
        push_socket.setsockopt(zmq.CONFLATE, 1)  # Replace old messages
        push_socket.connect(f"ipc://{socket_path}")
        expected_ids = [0x09, 253]  # What ID should we relay to the server?
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
                    if message_json.get("id") not in expected_ids:
                        slogger.error(
                            f"Invalid packet ID for TX: {message_json.get('id')}. Expected in {expected_ids}"
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


def build_packet(websocket_data: dict) -> device_emulator.GCStoGSEManualControl:
    """An adaptor to convert internal websocket payload for manual actuation into lora packet GCS to GSE MANUAL CONTROL

    Args:
        websocket_data (dict): Data in the format of post translation packet 0x09

    Returns:
        device_emulator.GCStoGSEManualControl: Output packet to be written to lora
    """

    purge_high: bool = websocket_data.get("solenoid1High", False)
    n2o_high: bool = websocket_data.get("solenoid2High", False)
    o2_high: bool = websocket_data.get("solenoid3High", False)
    states = {
        "MANUAL_PURGE": purge_high,
        "O2_FILL_ACTIVATE": o2_high,
        "SELECTOR_SWITCH_NEUTRAL_POSITION": False,
        "N2O_FILL_ACTIVATE": n2o_high,
        "IGNITION_FIRE": False,
        "IGNITION_SELECTED": True,
        "GAS_FILL_SELECTED": True,
        "SYSTEM_ACTIVATE": True,
    }
    return device_emulator.GCStoGSEManualControl(**states)


async def handler(websocket) -> None:
    # start both producer and consumer
    producer_task = asyncio.create_task(
        zmq_to_websocket(websocket, IPC_ADDRESS)
    )
    consumer_task = asyncio.create_task(consumer(websocket))

    try:
        # wait until one side throws an exception or shutdown is requested
        _done, pending = await asyncio.wait(
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


async def amain() -> None:
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


def main() -> None:

    global WEBSOCKET_HOST, WEBSOCKET_PORT, IPC_ADDRESS

    # get_newest_messages()
    frontend_config = config.get_config()["frontend"]
    WEBSOCKET_HOST = frontend_config.get("ws_host")  # "0.0.0.0"
    WEBSOCKET_PORT = frontend_config.get("ws_port")  # 1887

    if "--socket-path" in sys.argv:
        socket_path = sys.argv[sys.argv.index("--socket-path") + 1]
        IPC_ADDRESS = f"ipc:///tmp/{socket_path}_pub.sock"
    else:
        slogger.error("Missing required --socket-path argument")
        sys.exit(1)

    device_emulator.MockPacket.initialize_settings(
        config.get_config()['emulation'])

    try:
        asyncio.run(amain())
    finally:
        slogger.info("Application exited")


if __name__ == "__main__":
    main()
