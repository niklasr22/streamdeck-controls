from abc import ABC, abstractmethod
from typing import Iterator
from device import find_streamdecks
from PIL import Image
from streamdeck import StreamDeck
from threading import Lock, Thread


class NoStreamDeckFoundExcpetion(Exception):
    pass


class SDSystem:
    def __init__(self) -> None:
        self._apps: list[SDUserApp] = []
        self._app_thread: Thread = None
        self._deck: StreamDeck = None
        self._deck_thread: Thread = None
        self._running_app: _SDApp = None
        self._back_btn_img = Image.open("testbild3.jpeg").rotate(270)
        self._clear_key = Image.open("clear.jpeg")
        self._key_lock = Lock()
        self._connect()

    def _connect(self):
        decks = find_streamdecks()
        if len(decks) == 0:
            raise NoStreamDeckFoundExcpetion("There is no streamdeck available")
        self._deck: StreamDeck = decks[0]
        print("Selected", self._deck)
        self._deck.add_event_listener(self._system_key_listener)

    def start(self) -> None:
        self._deck.set_standby_timeout(600)
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
        result = self._deck.set_key_image(key, image)
        self._key_lock.release()
        return result

    def get_keys(self) -> Iterator[bool]:
        return self._deck.get_keys()

    def get_key_count(self) -> int:
        return self._deck.get_key_count()

    def _system_key_listener(
        self, deck: StreamDeck, keys_before: list[bool], keys: list[bool]
    ):
        if keys[0] and self._is_user_app_running():
            self._close_app()

    def _stop_deck(self):
        if self._deck:
            self._deck.stop()
            if self._deck_thread and self._deck_thread.is_alive():
                self._deck_thread.join(2.0)

    def close(self) -> None:
        self._deck.set_standby_timeout(1)
        self.clear_deck()
        self._close_app(shutdown=True)
        self._stop_deck()

    def __del__(self):
        self.close()


class _SDApp(ABC):
    def __init__(self) -> None:
        self._running = False
        self._system: SDSystem = None

    def set_key(self, key: int, image: Image):
        if key != 0:
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
            self.update(keys_before, keys.copy())
            keys_init = [
                False if not ki else not (ki and not kn)
                for ki, kn in zip(keys_init, keys_new)
            ]
            keys_before = keys

    def stop(self) -> None:
        self._running = False

    def closed(self) -> None:
        self._system = None

    @abstractmethod
    def init(self) -> None:
        ...

    @abstractmethod
    def update(self, keys_before: list[bool], keys: list[bool]) -> None:
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