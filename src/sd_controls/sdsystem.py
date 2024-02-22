import asyncio
import inspect
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import Enum
from functools import cache
from pathlib import Path
from threading import Lock, Thread
from typing import Callable, Iterator

import hid
from PIL import Image, ImageDraw, ImageFont

from sd_controls.sprites import Sprites
from sd_controls.streamdeck import StreamDeck, StreamDeckMk2

_LIB_PATH = Path(__file__).parent
_FONT_PATH = _LIB_PATH / "fonts"


_DEVICE_VID_ELGATO = 0x0FD9


class NoStreamDeckFoundExcpetion(Exception):
    pass


class Orientation(Enum):
    DEFAULT = 1
    FLIPPED_180 = 2


class SDSystem:
    def __init__(self, orientation=Orientation.DEFAULT, timeout: int = 0, deck: StreamDeck = None) -> None:
        self._apps: list[SDUserApp] = []
        self._deck: StreamDeck = deck
        self._deck_thread: Thread = None
        self._running_app: _SDApp = None
        self._key_lock = Lock()
        self._orientation = orientation
        self._default_timeout = timeout
        self._key_map = []
        self._connect()

    def _connect(self):
        if not self._deck:
            decks = SDSystem.find_streamdecks()
            if len(decks) == 0:
                raise NoStreamDeckFoundExcpetion("There is no streamdeck available")
            self._deck: StreamDeck = decks[0]
            print("Selected", self._deck)
        self._create_key_map()
        self._deck.add_event_listener(self._system_key_listener)

    def start(self) -> None:
        self._deck.set_standby_timeout(self._default_timeout)
        # self._deck_thread = Thread(target=self._deck.run)
        # self._deck_thread.start()
        try:
            print("Started StreamDeck System")
            # starts launchpad
            self.close_app()
            asyncio.run(self._deck.run())
            # self._deck_thread.join()
        except KeyboardInterrupt:
            self.close()
            print("Stream Deck System shutdown")

    def register_app(self, app: "_SDApp") -> None:
        self._apps.append(app)

    def get_apps(self) -> list["SDUserApp"]:
        return self._apps

    def clear_deck(self) -> None:
        for key in range(self.get_key_count()):
            self._deck.set_key_image(key, Sprites.CLEAR)
        if self._is_user_app_running():
            self.set_back_btn()

    def _create_key_map(self):
        key_indices = range(0, self.get_key_count())
        match self._orientation:
            case Orientation.FLIPPED_180:
                self._key_map = list(reversed(key_indices))
            case _:
                self._key_map = list(key_indices)

    def _start_app(self, app: "_SDApp"):
        self._running_app: _SDApp = app
        self.clear_deck()
        self._running_app.start(self)

    def close_app(self, shutdown=False):
        if self._running_app:
            self._running_app.stop()
            self._running_app.closed()
            self._running_app = None

        if not shutdown:
            self._start_app(_LaunchPad())

    def _is_user_app_running(self) -> bool:
        return self._running_app and issubclass(type(self._running_app), SDUserApp)

    def set_back_btn(self):
        self.set_key(0, Sprites.BACK_BTN)

    def set_key(self, key: int, image: Image.Image) -> bool:
        self._key_lock.acquire()
        if self._orientation == Orientation.DEFAULT:
            image = image.rotate(180)
        result = self._deck.set_key_image(self._key_map[key], image)
        self._key_lock.release()
        return result

    def get_keys(self) -> Iterator[bool]:
        match self._orientation:
            case Orientation.FLIPPED_180:
                return reversed(self._deck.get_keys())
            case _:
                return self._deck.get_keys().__iter__()

    def get_key_count(self) -> int:
        return self._deck.get_key_count()

    def _system_key_listener(self, deck: StreamDeck, keys_before: list[bool], keys: list[bool]):
        if keys_before[self._key_map[0]] and not keys[self._key_map[0]] and self._is_user_app_running():
            self.close_app()
            return
        if self._running_app:
            self._running_app.key_event(keys_before, keys)

    def set_brightness(self, brightness: int) -> None:
        self._deck.set_brightness(brightness)

    def get_brightness(self) -> int:
        self._deck.get_brightness()

    def _stop_deck(self) -> None:
        if self._deck:
            self._deck.stop()
            # if self._deck_thread and self._deck_thread.is_alive():
            #     self._deck_thread.join(2.0)

    def close(self) -> None:
        self._deck.set_standby_timeout(1)
        self.close_app(shutdown=True)
        self.clear_deck()
        self._stop_deck()

    def __del__(self):
        self.close()

    @staticmethod
    def find_streamdecks() -> list[StreamDeck]:
        streamdeck_map = {StreamDeckMk2._PID: StreamDeckMk2}

        decks = []

        usb_devices = hid.enumerate()
        for device in usb_devices:
            if device["vendor_id"] == _DEVICE_VID_ELGATO and device["product_id"] in streamdeck_map:
                decks.append((streamdeck_map[device["product_id"]])(hid.Device(path=device["path"])))
        return decks


class _SDApp(ABC):
    def __init__(self) -> None:
        self._running = False
        self._system: SDSystem = None
        self._key_up_callbacks: dict[int, list[Callable[[], None]]] = defaultdict(list)
        self._key_down_callbacks: dict[int, list[Callable[[], None]]] = defaultdict(list)

    def set_key(self, key: int, image: Image.Image):
        if not self._check_system():
            return False

        if 0 < key < self._system.get_key_count():
            return self._system.set_key(key, image)
        return False

    def setup_key(self, key: int, *, down: Callable[[], None] = None, up: Callable[[], None] = None) -> bool:
        if not self._check_system():
            return False
        if up:
            self._key_up_callbacks[key].append(up)
        if down:
            self._key_down_callbacks[key].append(down)
        return True

    def clear_key_event(self, key: int) -> bool:
        if not self._check_system():
            return False
        self._key_up_callbacks[key].clear()
        self._key_down_callbacks[key].clear()
        return True

    def clear_deck(self) -> None:
        if not self._check_system():
            return False

        self._system.clear_deck()

    def start(self, system: SDSystem) -> None:
        self._running = True
        self._system = system
        self.init()

    def key_event(self, keys_before: list[bool], keys: list[bool]):
        self.keys_update(keys_before, keys)
        loop = asyncio.get_event_loop()
        for key, (before, after) in enumerate(zip(keys_before, keys)):
            if before and not after:
                for callback in self._key_up_callbacks[key]:
                    if inspect.iscoroutinefunction(callback):
                        loop.create_task(callback())
                    else:
                        callback()
            elif not before and after:
                for callback in self._key_down_callbacks[key]:
                    if inspect.iscoroutinefunction(callback):
                        t = loop.create_task(callback())
                    else:
                        callback()

    def close_app(self):
        self._system.close_app()

    def _check_system(self) -> bool:
        if not self._system:
            self._running = False
            return False
        return True

    def stop(self) -> None:
        self._running = False
        self.on_close()

    def closed(self) -> None:
        self._system = None

    @abstractmethod
    def init(self) -> None: ...

    def keys_update(self, keys_before: list[bool], keys: list[bool]) -> None: ...

    def on_close(self) -> None: ...


class SDUserApp(_SDApp, ABC):
    def __init__(self, name: str) -> None:
        super().__init__()
        self._name = name

    def get_usable_keys(self) -> range:
        return range(1, self._system.get_key_count())

    def get_name(self) -> str:
        return self._name

    @abstractmethod
    def get_icon(self) -> Image: ...

    @staticmethod
    @cache
    def font(size: int):
        return ImageFont.truetype(str(_FONT_PATH / "Roboto" / "Roboto-Regular.ttf"), size)

    @staticmethod
    def generate_labeled_img(
        base: Image,
        label: str,
        position: tuple[int, int] = (36, 52),
        color: tuple[int, int, int] = (255, 255, 255),
        font_size: int = 14,
        background: str | None = "#00000080",
    ) -> Image:
        labeled_img = base.copy()
        draw = ImageDraw.Draw(labeled_img)
        text_pos = position
        if background is not None:
            bbox = draw.textbbox(
                text_pos,
                label,
                font=SDUserApp.font(font_size),
                anchor="mm",
                align="center",
            )
            draw.rectangle(bbox, fill=background)
        draw.text(
            text_pos,
            label,
            color,
            font=SDUserApp.font(font_size),
            anchor="mm",
            align="center",
        )

        return labeled_img


class _SDSystemApp(_SDApp, ABC):
    def set_key(self, key: int, image: Image.Image):
        return self._system.set_key(key, image)


class _LaunchPad(_SDSystemApp):
    def __init__(self) -> None:
        super().__init__()
        self.apps: dict[int, SDUserApp] = {}

    def init(self) -> None:
        self.apps.clear()
        for key, app in enumerate(self._system.get_apps()[: self._system.get_key_count()]):
            self.set_key(key, app.get_icon())
            self.apps[key] = app

    def keys_update(self, keys_before: list[bool], keys: list[bool]) -> None:
        for key, (before, after) in enumerate(zip(keys_before, keys)):
            if before and not after and key < len(self.apps):
                self._system._start_app(self.apps[key])
                self.stop()
                break
