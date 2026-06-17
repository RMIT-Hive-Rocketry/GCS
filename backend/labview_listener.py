import asyncio
import socket
import time
import csv
import contextlib
from config.config import get_config
import os
import backend.includes_python.process_logging as slogger
import zmq
from backend.includes_python import service_helper
from backend.includes_python.timers import RepeatingTimer


cfg = get_config()
server_ip = cfg["tcp"]["labview_server_ip"]
server_port = int(cfg["tcp"]["labview_server_port"])
log_dir_path = cfg["tcp"]["labview_log_path"].strip()
log_filename = f"labview_{time.strftime('%Y%m%d_%H%M%S')}.csv"
log_file_path = os.path.join(log_dir_path, log_filename)

LINGER_TIME_MS = 300

# path to the socket read by frontend api
LABVIEW_SOCKET_PATH = os.path.abspath(
    os.path.join(os.path.sep, "tmp", "labview_frontend_pub.sock")
)


class LabViewCluster:
    def __init__(self, cluster_id, cluster_timestamp, data: dict):
        self.id: int = cluster_id
        self.timestamp: float = float(cluster_timestamp)
        # self.num_elts = data["NumElts"]
        self.vent_temp: float = float(data["Vent Temp"])
        self.bottle_pressure: float = float(data["Bottle Pressure"])
        self.n2o_temp: float = float(data["N2O Temp"])
        self.tank_pressure: float = float(data["Tank Pressure"])
        self.diff_pressure: float = 0.0  # TODO
        self.rtd_bottom: float = float(data["RTD Bottom"])
        self.rtd_middle: float = float(data["RTD Middle"])
        self.rtd_top: float = float(data["RTD Top"])
        self.rocket_weight: float = float(data["Rocket Weight"]) * -1
        self.rocket_weight_tare: float = float(data["N2O Fill (kg)"]) * -1
        self.o2_pressure: float = float(data["O2 Pressure"])

    def save_to_log(self) -> None:
        # Log to CSV
        try:
            with open(log_file_path, mode="a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        self.id,
                        format(self.timestamp, ".3f"),
                        format(self.vent_temp, ".2f"),
                        format(self.n2o_temp, ".2f"),
                        format(self.bottle_pressure, ".2f"),
                        format(self.tank_pressure, ".2f"),
                        format(self.diff_pressure, ".2f"),
                        format(self.o2_pressure, ".2f"),
                        format(self.rtd_bottom, ".2f"),
                        format(self.rtd_middle, ".2f"),
                        format(self.rtd_top, ".2f"),
                        format(self.rocket_weight, ".2f"),
                        format(self.rocket_weight_tare, ".2f"),
                    ]
                )
        except Exception as e:
            slogger.error(f"Logging error: {e}")

    def get_values(self) -> dict[str, float]:
        return {
            "timestamp": self.timestamp,
            "vent_temp": self.vent_temp,
            "n2o_temp": self.n2o_temp,
            "bottle_pressure": self.bottle_pressure,
            "tank_pressure": self.tank_pressure,
            "diff_pressure": self.diff_pressure,
            "o2_pressure": self.o2_pressure,
            "rtd_bottom": self.rtd_bottom,
            "rtd_middle": self.rtd_middle,
            "rtd_top": self.rtd_top,
            "rocket_weight": self.rocket_weight,
            "rocket_weight_tare": self.rocket_weight_tare,
        }


def create_log_file() -> None:
    # Create the CSV file and write the header if it doesn't exist
    try:
        with open(log_file_path, mode="a", newline="") as f:
            writer = csv.writer(f)
            # Write header only if file is empty
            if f.tell() == 0:
                writer.writerow(
                    [
                        "id",
                        "timestamp",
                        "vent_temp",
                        "n2o_temp",
                        "bottle_pressure",
                        "tank_pressure",
                        "diff_pressure",
                        "o2_pressure",
                        "rtd_bottom",
                        "rtd_middle",
                        "rtd_top",
                        "rocket_weight",
                        "rocket_weight_tare",
                    ]
                )
    except Exception as e:
        slogger.error(f"Error initializing CSV: {e}")
        return


def parse_cluster(buffer, cluster_id) -> LabViewCluster:
    cluster_data = {}
    cluster_timestamp = float(time.time())

    if cluster_id % 500 == 1:
        slogger.info("LabVIEW connection active")

    # Process line-delimited payloads
    name = ""
    val = ""
    while "\n" in buffer:
        line, buffer = buffer.split("\n", 1)
        if line:
            line = line.strip()
            if "Name" in line:
                name = line[6:-7]
            elif "Val" in line and cluster_data is not None:
                # print(name, line[5:-6])
                cluster_data[name] = line[5:-6]

    # Save cluster data into row
    cluster = LabViewCluster(
        str(cluster_id),
        str(cluster_timestamp),
        cluster_data,
    )
    cluster.save_to_log()
    return cluster


def start_labview_listener() -> None:
    """
    Connects to LabVIEW server, prints data to screen, and logs to CSV with timestamps.
    """
    # Create log file
    create_log_file()

    # define sockets first to ensure they are not undefined
    context = zmq.Context()
    labview_complain_timer = RepeatingTimer(5)
    labview_pub_socket = context.socket(zmq.PUB)

    try:
        # Establish socket connection to frontend
        labview_pub_socket.setsockopt(zmq.LINGER, LINGER_TIME_MS)
        labview_pub_socket.setsockopt(
            zmq.SNDHWM, 1
        )  # Limit send buffer to 1 message
        labview_pub_socket.bind(f"ipc://{LABVIEW_SOCKET_PATH}")

        while not service_helper.time_to_stop():
            time.sleep(1)
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            cluster_id = 0

            try:
                # Establish connection to labview
                slogger.debug(
                    f"Connecting to LabVIEW server at {server_ip}:{server_port} ..."
                )
                client_socket.connect((server_ip, server_port))
                slogger.info("Connected. Waiting for data...")
                buffer = ""

                while not service_helper.time_to_stop():
                    # Limit program to running 50 times per second
                    time.sleep(1 / 50)

                    # Load data chunk
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        slogger.info("LabVIEW server disconnected.")
                        break

                    # Add chunk data to buffer and attempt to process it
                    buffer += chunk.decode("utf-8", errors="replace")
                    if "\n" in buffer:
                        cluster_id += 1
                        cluster = parse_cluster(buffer, cluster_id)

                        # send to frontend api
                        try:
                            labview_pub_socket.send_json(
                                cluster.get_values(),
                                flags=zmq.NOBLOCK,
                            )
                        except zmq.ZMQError as e:
                            # Queue is likely full
                            if labview_complain_timer.time_has_passed():
                                slogger.warning(
                                    f"labview ZMQ Push socket is likely full. error: {e}"
                                )

            except ConnectionRefusedError:
                slogger.debug("Connection refused. Retrying in 1s...")
                time.sleep(1)
            except (ConnectionResetError, BrokenPipeError):
                slogger.debug("Connection dropped. Reconnecting in 1s...")
                time.sleep(1)
            finally:
                with contextlib.suppress(Exception):
                    client_socket.close()

                # Create a fresh socket before reconnecting.
                client_socket = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM
                )
                client_socket.setsockopt(
                    socket.IPPROTO_TCP, socket.TCP_NODELAY, 1
                )
    finally:
        # If this code print every single second, we need to move the client_socket code into another nested loop thing
        slogger.debug("Labview sender closing socket")
        labview_pub_socket.close()
        slogger.debug("Labview sender closed socket")
        slogger.debug(f"Labview sender closing context (<{LINGER_TIME_MS}ms)")
        context.term()
        slogger.debug("Labview sender thread resources cleaned up")


if __name__ == "__main__":
    start_labview_listener()
