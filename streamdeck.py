import ctypes
import io
from abc import ABC, abstractmethod
from typing import Callable, Iterator, Self

import hid
from PIL import Image


class StreamDeck(ABC):
    _PID: int = 0
    _ICON_SIZE: int = 0
    _KEY_COUNT: int = 0
    _KEY_DATA_OFFSET: int = 0
    _IMAGE_CMD_HEADER_LENGTH: int = 0
    _IMAGE_CMD_MAX_PAYLOAD_LENGTH: int = 0

    def __init__(self, device: hid.Device, read_interval: int = 100, buffer_size: int = 1024) -> None:
        self._device = device
        self._read_interval = read_interval
        self._buffer_size = buffer_size
        self._event_listeners: list[callable[[StreamDeck], None]] = []
        self._keys: list[bool] = [False] * self._KEY_COUNT
        self._running = False

    def __str__(self) -> str:
        return f"{self._device.product} ({self._device.manufacturer})"

    @abstractmethod
    def set_brightness(self, percentage: int) -> None:
        ...

    @abstractmethod
    def set_standby_timeout(self, timeout_secs: int) -> None:
        ...

    @abstractmethod
    def _get_send_image_command_header(
        self, key: int, is_last_package: bool, payload_length: int, package_index: int
    ) -> bytes:
        ...

    def get_key_count(self) -> int:
        return self._KEY_COUNT

    def get_keys(self) -> list[bool]:
        return self._keys

    def run(self) -> None:
        self._running = True
        try:
            while self._running:
                data = self._device.read(self._buffer_size, self._read_interval)
                if len(data) > 0:
                    keys_before = self._keys.copy()
                    self._keys = [
                        bool(k) for k in data[self._KEY_DATA_OFFSET : self._KEY_DATA_OFFSET + self._KEY_COUNT]
                    ]
                    for listener in self._event_listeners:
                        listener(self, keys_before, self._keys.copy())
        except (KeyboardInterrupt, hid.HIDException):
            self._running = False

    def stop(self) -> None:
        self._running = False

    def add_event_listener(self, callback: Callable[[Self, list[bool], list[bool]], None]) -> None:
        self._event_listeners.append(callback)

    def clear_event_listeners(self) -> None:
        self._event_listeners.clear()

    def __del__(self):
        print("Close device")
        self._device.close()

    def set_key_image(self, key: int, image: Image) -> bool:
        max_payload_length = self._IMAGE_CMD_MAX_PAYLOAD_LENGTH

        img_byte_buffer = io.BytesIO()
        image.save(img_byte_buffer, format="JPEG")
        img_bytes = img_byte_buffer.getvalue()

        package = 0
        offset = 0
        remaining_data = len(img_bytes)
        # print("Total length", remaining_data)
        try:
            while remaining_data > 0:
                payload_length = min(max_payload_length, remaining_data)
                remaining_data -= payload_length

                header = self._get_send_image_command_header(
                    key,
                    remaining_data == 0,
                    payload_length,
                    package,
                )
                data = (
                    header
                    + img_bytes[offset : offset + payload_length]
                    + bytes([0x0] * (max_payload_length - payload_length))
                )

                self._device.write(data)
                # print(
                #    "Wrote package", package, "Header:", header, "Data-Length:", len(data)
                # )

                offset += payload_length
                package += 1
        except hid.HIDException:
            return False
        return True


class StreamDeckMk2(StreamDeck):
    _PID: int = 0x0080
    _ICON_SIZE: int = 70
    _KEY_COUNT: int = 15
    _KEY_DATA_OFFSET: int = 4
    _IMAGE_CMD_HEADER_LENGTH: int = 8
    _IMAGE_CMD_MAX_PAYLOAD_LENGTH: int = 1016

    def __init__(self, device: hid.Device, read_interval: int = 60, buffer_size: int = 512) -> None:
        super().__init__(device, read_interval, buffer_size)

    def set_brightness(self, percentage: int) -> None:
        # command 0x03 0x08 (percentage as byte) ...
        command = bytes([0x03, 0x08, percentage] + [0x0] * 29)
        self._device.send_feature_report(command)

    def set_standby_timeout(self, timeout_secs: int) -> None:
        command = bytes(
            [
                0x03,
                0x0D,
                timeout_secs & 0xFF,
                timeout_secs >> 8,
            ]
        )
        self._device.send_feature_report(command)

    def _get_send_image_command_header(
        self, key: int, is_last_package: bool, payload_length: int, package_index: int
    ) -> bytes:
        return bytes(
            [
                0x02,
                0x07,
                key,
                is_last_package,
                payload_length & 0xFF,
                payload_length >> 8,
                package_index & 0xFF,
                package_index >> 8,
            ]
        )
