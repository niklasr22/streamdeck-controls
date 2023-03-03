import traceback
from abc import ABC, abstractmethod
from enum import Enum
from threading import Lock, Thread
from typing import Iterator

from PIL import Image

from device import find_streamdecks
from streamdeck import StreamDeck


class NoStreamDeckFoundExcpetion(Exception):
    pass


class Orientation(Enum):
    DEFAULT = 1
    FLIPPED_180 = 2


class SDSystem:
    def __init__(self, orientation=Orientation.DEFAULT) -> None:
        self._apps: list[SDUserApp] = []
        self._app_thread: Thread = None
        self._deck: StreamDeck = None
        self._deck_thread: Thread = None
        self._running_app: _SDApp = None
        self._back_btn_img = Image.open("back_btn.jpeg")
        self._clear_key = Image.open("clear.jpeg")
        self._key_lock = Lock()
        self._orientation = orientation
        self._key_map = []
        self._connect()

    def _connect(self):
        decks = find_streamdecks()
        if len(decks) == 0:
            raise NoStreamDeckFoundExcpetion("There is no streamdeck available")
        self._deck: StreamDeck = decks[0]
        print("Selected", self._deck)
        self._create_key_map()
        self._deck.add_event_listener(self._system_key_listener)

    def start(self) -> None:
        self._deck.set_standby_timeout(0)
        self._deck_thread = Thread(target=self._deck.run)
        self._deck_thread.start()
        try:
            print("Started StreamDeck System")
            self._close_app()
            self._deck_thread.join()
        except KeyboardInterrupt:
            self.close()
            print("Stream Deck System shutdown")

    def register_app(self, app: "_SDApp") -> None:
        self._apps.append(app)

    def get_apps(self) -> list["SDUserApp"]:
        return self._apps

    def clear_deck(self) -> None:
        for key in range(self.get_key_count()):
            self._deck.set_key_image(key, self._clear_key)
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
        self._app_thread = Thread(target=self._running_app.start, args=[self])
        self._app_thread.start()

    def _close_app(self, shutdown=False):
        if self._running_app:
            self._running_app.stop()
            if self._app_thread and self._app_thread.is_alive():
                self._app_thread.join(2.0)
            self._running_app.closed()

        if not shutdown:
            self._start_app(_LaunchPad())

    def _is_user_app_running(self) -> bool:
        return (
            self._app_thread
            and self._app_thread.is_alive()
            and self._running_app
            and issubclass(type(self._running_app), SDUserApp)
        )

    def set_back_btn(self):
        self.set_key(0, self._back_btn_img)

    def set_key(self, key: int, image: Image) -> bool:
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

    def _system_key_listener(
        self, deck: StreamDeck, keys_before: list[bool], keys: list[bool]
    ):
        if keys[self._key_map[0]] and self._is_user_app_running():
            self._close_app()

    def _stop_deck(self):
        if self._deck:
            self._deck.stop()
            if self._deck_thread and self._deck_thread.is_alive():
                self._deck_thread.join(2.0)

    def close(self) -> None:
        self._deck.set_standby_timeout(1)
        self._close_app(shutdown=True)
        self.clear_deck()
        self._stop_deck()

    def __del__(self):
        self.close()


class _SDApp(ABC):
    def __init__(self) -> None:
        self._running = False
        self._system: SDSystem = None

    def set_key(self, key: int, image: Image):
        if 0 < key < self._system.get_key_count():
            return self._system.set_key(key, image)
        return False

    def clear_deck(self) -> None:
        self._system.clear_deck()

    def start(self, system: SDSystem) -> None:
        self._running = True
        self._system = system
        self.init()

        keys_init = list(self._system.get_keys())
        keys_before = [False] * self._system.get_key_count()
        while self._running:
            keys_new = list(self._system.get_keys())

            keys = [kn and not ki for ki, kn in zip(keys_init, keys_new)]
            try:
                self.update(keys_before, keys.copy())
            except Exception:
                print(traceback.format_exc())

            keys_init = [
                False if not ki else not (ki and not kn)
                for ki, kn in zip(keys_init, keys_new)
            ]
            keys_before = keys

    def stop(self) -> None:
        self._running = False
        self.close()

    def closed(self) -> None:
        self._system = None

    @abstractmethod
    def init(self) -> None:
        ...

    @abstractmethod
    def update(self, keys_before: list[bool], keys: list[bool]) -> None:
        ...

    def close(self) -> None:
        ...


class SDUserApp(_SDApp, ABC):
    def __init__(self, name: str) -> None:
        super().__init__()
        self._name = name

    def get_usable_keys(self) -> range:
        return range(1, self._system.get_key_count())

    def get_name(self) -> str:
        return self._name

    @abstractmethod
    def get_icon(self) -> Image:
        ...


class _SDSystemApp(_SDApp, ABC):
    def set_key(self, key: int, image: Image):
        return self._system.set_key(key, image)


class _LaunchPad(_SDSystemApp):
    def __init__(self) -> None:
        super().__init__()
        self.apps: dict[int, SDUserApp] = {}

    def init(self) -> None:
        print("Started Launchpad")
        self.apps.clear()
        for key, app in enumerate(
            self._system.get_apps()[: self._system.get_key_count()]
        ):
            self.set_key(key, app.get_icon())
            self.apps[key] = app

    def update(self, keys_before: list[bool], keys: list[bool]) -> None:
        for key, (before, after) in enumerate(zip(keys_before, keys)):
            if before and not after and key < len(self.apps):
                self._system._start_app(self.apps[key])
                self.stop()
                break
