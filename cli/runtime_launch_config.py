import enum
import logging
import os
from dataclasses import dataclass
import config.config as config
from cli.start_middleware import (
    InterfaceType,
    MiddlewareConfig,
    get_interface_type,
)
from cli.start_socat import start_fake_serial_device


@dataclass(frozen=True)
class AuxServicePlan:
    service: str | None
    device_path: str | None
    interface_type: InterfaceType | None
    mission: str | None
    simulation: str | None


class RuntimeLaunchConfig:
    """Resolve launch-time interfaces, device paths, and middleware config."""
    
    _test_interfaces = {InterfaceType.TEST, InterfaceType.TEST_UART_E5}

    def __init__(
        self,
        command: enum.Enum,
        interface_av_arg: str | None,
        interface_gse_arg: str | None,
        gse_only: bool,
        logger: logging.Logger,
    ) -> None:
        self.command = command
        self.logger = logger
        self.is_release = self._is_release_mode(command)

        # get from config if not specified in CLI args
        if not interface_gse_arg:
            interface_gse_arg = config.get_config()["hardware"]["interface_dev_gse"].strip().upper()

        if not interface_av_arg:
            interface_av_arg = config.get_config()["hardware"]["interface_dev_av"].strip().upper()

        self.interface_gse_type = get_interface_type(interface_gse_arg)
        self.interface_av_type = get_interface_type(interface_av_arg)

        if gse_only:
            self.interface_av_type = InterfaceType.NONE

        self._validate_split_emulation_support()

        self.lora_config: dict[str, str] | None = None
        self.device_path_gse: str = ""
        self.device_path_av: str = ""
        self._aux_device_path: str | None = None

        self._resolve_paths_and_radio()

        self.optional_arg = "--GSE-ONLY" if gse_only else None
        self.middleware_config = MiddlewareConfig(
            release=self.is_release,
            interface_gse_type=self.interface_gse_type,
            device_path_gse=self.device_path_gse,
            interface_av_type=self.interface_av_type,
            device_path_av=self.device_path_av,
            pendant_socket_path="gcs_rocket",
            web_control_socket_path=os.path.abspath(
                os.path.join(os.path.sep, "tmp", "gcs_rocket_web_pull.sock")
            ),
            opt_arg=self.optional_arg,
            lora_config=(
                self.lora_config
                if self.interface_gse_type == InterfaceType.UART_E5
                or self.interface_av_type == InterfaceType.UART_E5
                else None
            ),
        )

    @staticmethod
    def _is_release_mode(command: enum.Enum) -> bool:
        return getattr(command, "name", "").upper() == "RUN"

    def _validate_split_emulation_support(self) -> None:
        if self.interface_gse_type == InterfaceType.NONE or self.interface_av_type == InterfaceType.NONE:
            # NONE should allow split emulation
            return

        any_interface_is_test = (
            self.interface_av_type in self._test_interfaces
            or self.interface_gse_type in self._test_interfaces
        )
        interfaces_differ = self.interface_gse_type != self.interface_av_type

        if (any_interface_is_test) and interfaces_differ:
            raise NotImplementedError(
                "Device emulator does not support split emulation interfaces yet"
            )

    def _resolve_paths_and_radio(self) -> None:
        either_is_test = self.interface_gse_type in self._test_interfaces or self.interface_av_type in self._test_interfaces
        either_is_none = self.interface_gse_type == InterfaceType.NONE or self.interface_av_type == InterfaceType.NONE

        if either_is_none and either_is_test:
            middleware_device, aux_device = self._run_pseudoterm_setup()
            self.device_path_gse = middleware_device
            self.device_path_av = middleware_device
            self._aux_device_path = aux_device
            return

        if either_is_test:
            raise NotImplementedError(
                "Mixed test/non-test interfaces are not supported yet"
                + self.interface_av_type.value
                + self.interface_gse_type.value
            )

        self.device_path_gse = self._resolve_non_test_device_path(
            self.interface_gse_type, link_name="GSE"
        )
        self.device_path_av = self._resolve_non_test_device_path(
            self.interface_av_type, link_name="AV"
        )

    def _resolve_non_test_device_path(
        self, interface_type: InterfaceType, link_name: str
    ) -> str:
        if interface_type == InterfaceType.UART_E5:
            lora_section = config.get_config()["lora"]
            serial_device = lora_section.get("serial_device")
            if serial_device is None or len(str(serial_device).strip()) == 0:
                raise RuntimeError(
                    "Please specify lora.serial_device in config/config.ini"
                )
            self.lora_config = {
                "frequency": str(lora_section.get("frequency")),
                "spread_factor": str(lora_section.get("spread_factor")),
                "bandwidth": str(lora_section.get("bandwidth")),
                "tx_preamble": str(lora_section.get("tx_preamble")),
                "rx_preamble": str(lora_section.get("rx_preamble")),
                "power": str(lora_section.get("power")),
                "crc": str(lora_section.get("crc")),
                "iq": str(lora_section.get("iq")),
                "net": str(lora_section.get("net")),
            }
            self._print_large_config(lora_section)
            self.logger.info(
                f"Starting UART E5 interface ({link_name}) on {serial_device}"
            )
            return str(serial_device)

        if interface_type == InterfaceType.TCP:
            self.logger.info(f"Starting TCP interface ({link_name})")
            tcp_section = config.get_config()["tcp"]
            tcp_ip = str(tcp_section.get("gse_ip"))
            tcp_port = int(tcp_section.get("gse_port"))
            self._print_large_config(tcp_section)
            if tcp_ip is None or tcp_port is None:
                raise RuntimeError(
                    "Please specify gse_ip and gse_port in config/config.ini"
                )
            if not (1 <= tcp_port <= 65535):
                raise RuntimeError("tcp-port must be between 1 and 65535")
            return f"{tcp_ip}:{tcp_port}"

        if interface_type == InterfaceType.NONE:
            self.logger.info(f"Starting NONE interface ({link_name})")
            return "NONE"

        raise ValueError("Invalid interface type")

    def _run_pseudoterm_setup(self) -> tuple[str, str]:
        """Starts a subprocess of socat to create linked pseudo-terminals and returns their paths."""
        if self.is_release:
            self.logger.warning("Test interface selected in production mode")
        self.logger.info("Starting pseudo-terminals for emulation")
        devices = start_fake_serial_device(self.logger)
        if devices == (None, None):
            raise RuntimeError("Failed to start fake serial device. Exiting")
        return devices[0], devices[1]

    def _print_large_config(self, params) -> None:
        self.logger.info("----------# RADIO PARAMETERS #----------")
        for key, value in params.items():
            self.logger.info(f"{key}:\t {value}")
        self.logger.info("----------# RADIO PARAMETERS #----------")

    def build_aux_service_plan(
        self,
        replay_mode: str | None,
        mission_arg: str | None,
        simulation_arg: str | None,
    ) -> AuxServicePlan:
        command_name = getattr(self.command, "name", "").upper()
        if command_name == "DEV" and (
            self.interface_av_type in self._test_interfaces
            or self.interface_gse_type in self._test_interfaces
        ):
            return AuxServicePlan(
                service="emulator",
                device_path=self._aux_device_path,
                interface_type=self.interface_av_type,
                mission=None,
                simulation=None,
            )
        if command_name == "SIMULATION":
            return AuxServicePlan(
                service="simulator",
                device_path=self._aux_device_path,
                interface_type=None,
                mission=None,
                simulation=None,
            )
        if command_name == "REPLAY":
            return AuxServicePlan(
                service="replay",
                device_path=self._aux_device_path,
                interface_type=None,
                mission=mission_arg if replay_mode == "mission" else None,
                simulation=None if replay_mode == "mission" else simulation_arg,
            )
        return AuxServicePlan(
            service=None,
            device_path=None,
            interface_type=None,
            mission=None,
            simulation=None,
        )
