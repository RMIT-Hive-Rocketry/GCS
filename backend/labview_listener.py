import socket
import time
import csv
from datetime import datetime
import contextlib
from config.config import get_config
import os


cfg = get_config()
server_ip = cfg["tcp"]["labjack_ip"]
server_port = int(cfg["tcp"]["labjack_port"])
log_dir_path = cfg["tcp"]["labjack_log_path"].strip()
log_filename = f"labview_{time.strftime('%Y%m%d_%H%M%S')}.csv"
log_file_path = os.path.join(log_dir_path, log_filename)


class LabViewRow:
    def __init__(self, cluster_id, cluster_timestamp, data: dict):
        self.id: int = cluster_id
        self.timestamp: float = float(cluster_timestamp)
        # self.num_elts = data["NumElts"]
        # self.unknown = data[""]
        self.vent_temp: float = float(data["Vent Temp"])
        self.bottle_pressure: float = float(data["Bottle Pressure"])
        self.n2o_temp: float = float(data["N2O Temp"])
        self.tank_pressure: float = float(data["Tank Pressure"])
        self.rtd_bottom: float = float(data["RTD Bottom"])
        self.rtd_middle: float = float(data["RTD Middle"])
        self.rtd_top: float = float(data["RTD Top"])
        self.rocket_weight: float = float(data["Rocket Weight"])
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
                        format(self.o2_pressure, ".2f"),
                        format(self.rtd_bottom, ".2f"),
                        format(self.rtd_middle, ".2f"),
                        format(self.rtd_top, ".2f"),
                        format(self.rocket_weight, ".2f"),
                    ]
                )
        except Exception as e:
            print(f"[!] Logging error: {e}")


def create_log() -> None:
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
                        "o2_pressure",
                        "rtd_bottom",
                        "rtd_middle",
                        "rtd_top",
                        "rocket_weight",
                    ]
                )
    except Exception as e:
        print(f"[!] Error initializing CSV: {e}")
        return


def start_labview_listener() -> None:
    """
    Connects to LabVIEW server, prints data to screen, and logs to CSV with timestamps.
    """
    # Create log file
    create_log()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    cluster_id = 0
    cluster_data = None
    cluster_timestamp = None

    while True:
        try:
            print(
                f"[*] Connecting to LabVIEW server at {server_ip}:{server_port} ..."
            )
            client_socket.connect((server_ip, server_port))
            print("[+] Connected. Waiting for data...")

            buffer = ""
            while True:
                # Limit program to running 50 times per second
                time.sleep(1 / 50)

                # Load data chunk
                chunk = client_socket.recv(4096)
                if not chunk:
                    print("[-] LabVIEW server disconnected.")
                    break

                buffer += chunk.decode("utf-8", errors="replace")

                if "\n" in buffer:
                    # Save previous data
                    if cluster_data is not None:
                        row = LabViewRow(
                            str(cluster_id),
                            str(cluster_timestamp),
                            cluster_data,
                        )
                        row.save_to_log()

                    # Periodically log
                    if cluster_id % 500 == 0:
                        print(
                            f"{format(cluster_timestamp, '.3f')} LabVIEW connection active"
                        )

                    # Capture exact timestamp
                    cluster_timestamp = float(time.time())
                    # datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

                    # Increment ID
                    cluster_id += 1

                    # Get new dict
                    cluster_data = {}

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
                            cluster_data[name] = line[5:-6]

        except ConnectionRefusedError:
            print("[!] Connection refused. Retrying in 1s...")
            time.sleep(1)
        except (ConnectionResetError, BrokenPipeError):
            print("[!] Connection dropped. Reconnecting in 1s...")
            time.sleep(1)
        finally:
            with contextlib.suppress(Exception):
                client_socket.close()

            # Create a fresh socket before reconnecting.
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)


if __name__ == "__main__":
    start_labview_listener()
