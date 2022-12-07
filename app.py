from typing import Iterator
from sdsystem import SDSystem, SDUserApp
from PIL import Image


class Memory(SDUserApp):
    def __init__(self) -> None:
        super().__init__("Memory")
        self._icon = Image.open("goat.jpeg")

    def get_icon(self) -> Image:
        return self._icon

    def init(self) -> None:
        print("Started Memory")
        for i in self.get_usable_keys():
            self.set_key(i, self._icon)

    def update(self, keys_before: list[bool], keys: list[bool]) -> None:
        ...


system = SDSystem()
system.register_app(Memory())
system.start()
