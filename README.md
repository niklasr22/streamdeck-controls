# Streamdeck controls

This project is a simple and small framework which simplifies developing and running custom apps for streamdeck devices.
It allows using streamdecks without the offical software so you can use it with any major OS.

## Currently supported Streamdecks

- Streamdeck Mk.2

## Installing

### Prerequisites

- [hidapi](https://github.com/libusb/hidapi)

Linux:

```bash
sudo apt install libhidapi-dev
````

MacOS:

```bash
brew install hidapi
```

### Installing sd-controls

```bash
pip install sd-controls
```

## Contributing

If you are interested in this project and have a streamdeck, please consider contributing to it.
Adding support for other Streamdecks is greatly appreciated but feel free to propose any other changes too!

## Using this software with Linux (Linux udev rules)

Create a `/etc/udev/rules.d/50-elgato.rules` file with the following content:

```rules
SUBSYSTEM=="input", GROUP="input", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0fd9", ATTRS{idProduct}=="0080", MODE:="666", GROUP="plugdev"
KERNEL=="hidraw*", ATTRS{idVendor}=="0fd9", ATTRS{idProduct}=="0080", MODE:="666", GROUP="plugdev"
```

## Example app

```python
from PIL import Image
from sd_controls.sdsystem import SDSystem, SDUserApp, Sprites


class HelloWorldApp(SDUserApp):
    _KEY_GREET = 1
    _KEY_ROTATE = 2

    def __init__(self) -> None:
        super().__init__("Settings")
        self._icon = SDUserApp.generate_labeled_img(Sprites.CLEAR, "Hello World")
        self._hello = SDUserApp.generate_labeled_img(Sprites.CLEAR, "Hello")
        self._world = SDUserApp.generate_labeled_img(Sprites.CLEAR, "World")
        self._rotate_key = Sprites.GOAT

    def get_icon(self) -> Image:
        return self._icon

    def init(self) -> None:
        self.set_key(self._KEY_GREET, self._hello)
        self.set_key(self._KEY_ROTATE, self._rotate_key)

    def keys_update(self, keys_before: list[bool], keys: list[bool]) -> None:
        if not keys[self._KEY_GREET] and keys_before[self._KEY_GREET]:
            self.set_key(self._KEY_GREET, self._world)
        if not keys[self._KEY_ROTATE] and keys_before[self._KEY_ROTATE]:
            self._rotate_key = self._rotate_key.rotate(90)
            self.set_key(self._KEY_ROTATE, self._rotate_key)
            

system = SDSystem()
system.register_app(HelloWorldApp())
system.start()
```
