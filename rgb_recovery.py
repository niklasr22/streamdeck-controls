import subprocess

from PIL import Image

from sdsystem import SDUserApp


class RgbRecovery(SDUserApp):

    KEY_UPDATE = 1

    def __init__(self) -> None:
        super().__init__("Recovery")
        self._icon = Image.open("./imgs/recovery.jpeg")

    def get_icon(self) -> Image:
        return self._icon

    def init(self) -> None:
        print("Started Kitchen RGB Recovery")
        subprocess.call(["sh", "./scripts/restart_leds.sh"])
        self.close_app()
