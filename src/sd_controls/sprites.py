from pathlib import Path

from PIL import Image

_LIB_PATH = Path(__file__).parent
_IMG_PATH = _LIB_PATH / "imgs"


class Sprites:
    CLEAR = Image.open(_IMG_PATH / "clear.jpeg")
    BACK_BTN = Image.open(_IMG_PATH / "back_btn.jpeg")
    GOAT = Image.open(_IMG_PATH / "goat.jpeg")
