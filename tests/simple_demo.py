from sd_controls.sdsystem import SDSystem, Sprites
from sd_controls.streamdeck import StreamDeck

if __name__ == "__main__":
    streamdecks = SDSystem.find_streamdecks()
    if len(streamdecks) == 0:
        print("No streamdecks discovered")
        exit()

    deck = streamdecks[0]
    print(deck)

    def update(streamdeck: StreamDeck, keys_before: list[bool], keys: list[bool]) -> None:
        if keys[0]:
            streamdeck.set_brightness(10)
        elif keys[1]:
            streamdeck.set_brightness(90)
        elif keys[2]:
            streamdeck.set_standby_timeout(10)
        elif keys[3]:
            streamdeck.set_standby_timeout(0)
        elif keys[4]:
            streamdeck.set_key_image(4, Sprites.BACK_BTN)
        elif keys[5]:
            streamdeck.set_key_image(4, Sprites.GOAT)

    deck.add_event_listener(update)
    deck.run()
