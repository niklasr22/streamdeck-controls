import tkinter as tk

from PIL import Image
from PIL import ImageTk as itk

from sd_controls.sprites import Sprites
from sd_controls.streamdeck import StreamDeck


class VirtualDeckMk2(StreamDeck):
    _ICON_SIZE: int = 70
    _KEY_COUNT: int = 15
    _KEY_DATA_OFFSET: int = 4

    def __init__(self) -> None:
        super().__init__()
        self._tkwindow = tk.Tk()
        self._key_btns = []
        self._key_images = []
        self._btn_presses = [False] * self._KEY_COUNT
        self._refresh_images = False

        self._setup_window()

    def _setup_window(self) -> None:
        self._tkwindow.title("VirtualDeck Mk.2 3x5")
        self._tkwindow.protocol("WM_DELETE_WINDOW", self.stop)

        # Create the key buttons. each button is a 70x70 square and contains an image
        self._button_frame = tk.Frame(self._tkwindow)
        self._button_frame.pack(side=tk.TOP)

        for i in range(self._KEY_COUNT):
            key_image = itk.PhotoImage(Sprites.CLEAR)
            key_btn = tk.Button(
                self._button_frame,
                image=key_image,
                command=self._key_press(i),
            )

            key_btn.grid(row=i // 5, column=i % 5)
            self._key_btns.append(key_btn)
            self._key_images.append(key_image)

        # Create centered title label
        title = tk.Label(self._tkwindow, text="VirtualDeck")
        title.pack(side=tk.BOTTOM)

    def __str__(self) -> str:
        return super().__str__()

    def _key_press(self, key: int) -> None:
        def pressed() -> None:
            self._btn_presses[key] = True

        return pressed

    def set_brightness(self, percentage: int) -> None:
        super().set_brightness(percentage)

    def set_standby_timeout(self, timeout_secs: int) -> None:
        super().set_standby_timeout(timeout_secs)

    def set_key_image(self, key: int, image: Image.Image) -> bool:
        if 0 <= key and key >= self._KEY_COUNT:
            return False

        if image:
            self._key_images[key] = image.rotate(180)
        else:
            self._key_images[key] = Sprites.CLEAR
        self._refresh_images = True
        return True

    def _get_data(self) -> list[bool] | None:
        if self._refresh_images:
            for key in range(self._KEY_COUNT):
                image = self._key_images[key]
                if type(image) != itk.PhotoImage:
                    self._key_images[key] = itk.PhotoImage(image)
                self._key_btns[key].config(image=self._key_images[key])
            self._refresh_images = False

        self._tkwindow.update()
        keys = self._btn_presses.copy()
        self._btn_presses = [False] * self._KEY_COUNT
        return keys

    def __del__(self):
        print("Close device")
