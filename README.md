# Streamdeck controls

## Prerequisites:

- [hidapi](https://github.com/libusb/hidapi)

## Supported Streamdecks:

- Streamdeck Mk.2

## Linux udev rules

Create a `/etc/udev/rules.d/50-elgato.rules` file with the following content:

```
SUBSYSTEM=="input", GROUP="input", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0fd9", ATTRS{idProduct}=="0080", MODE:="666", GROUP="plugdev"
KERNEL=="hidraw*", ATTRS{idVendor}=="0fd9", ATTRS{idProduct}=="0080", MODE:="666", GROUP="plugdev"
```