import hid

from PIL import Image
from streamdeck import StreamDeck, StreamDeckMk2

DEVICE_VID_ELGATO = 0x0FD9


def find_streamdecks() -> list[StreamDeck]:
    streamdeck_map = {StreamDeckMk2._PID: StreamDeckMk2}

    decks = []

    usb_devices = hid.enumerate()
    for device in usb_devices:
        if (
            device["vendor_id"] == DEVICE_VID_ELGATO
            and device["product_id"] in streamdeck_map
        ):
            decks.append(
                (streamdeck_map[device["product_id"]])(hid.Device(path=device["path"]))
            )
    return decks


if __name__ == "__main__":
    streamdecks = find_streamdecks()
    if len(streamdecks) == 0:
        print("No streamdecks discovered")
        exit()

    deck = streamdecks[0]
    print(deck)

    def update(
        streamdeck: StreamDeck, keys_before: list[bool], keys: list[bool]
    ) -> None:
        if keys[0]:
            streamdeck.set_brightness(10)
        elif keys[1]:
            streamdeck.set_brightness(90)
        elif keys[2]:
            streamdeck.set_standby_timeout(10)
        elif keys[3]:
            streamdeck.set_standby_timeout(0)
        elif keys[4]:
            with Image.open("back_btn.jpeg", mode="r") as img:
                img = img.rotate(180)
                streamdeck.set_key_image(4, image=img)
        elif keys[5]:
            with Image.open("goat.jpeg", mode="r") as img:
                img = img.rotate(180)
                streamdeck.set_key_image(4, image=img)

    deck.add_event_listener(update)
    deck.run()
