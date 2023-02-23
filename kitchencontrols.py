import json
import time
from threading import Thread

import requests
from PIL import Image, ImageDraw, ImageFont

import hue
from sdsystem import SDUserApp

KITCHENPICO_ENDPOINT = "http://kitchenpico"


class KitchenControlsApp(SDUserApp):
    HUE_LIGHTS = [5, 6, 7]
    HUE_GROUP = 2

    def __init__(self) -> None:
        super().__init__("Kitchen Controls")
        self._icon = Image.open("./kitchencontrols/lamp_on.jpeg")
        self._icon_ignore_hot_stove = Image.open("./kitchencontrols/alarm_off.jpeg")
        self._icon_reset_stove_ignore_state = Image.open(
            "./kitchencontrols/alarm_reset.jpeg"
        )
        self._icon_lamp_on = Image.open("./kitchencontrols/lamp_on.jpeg")
        self._icon_lamp_off = Image.open("./kitchencontrols/lamp_off.jpeg")
        self._clear_img = Image.open("./clear.jpeg")

        self._lights_on = False

    def get_icon(self) -> Image:
        return self._icon

    def init(self) -> None:
        print("Started Kitchen Controls")
        self.set_key(self.get_usable_keys()[0], self._icon_ignore_hot_stove)
        self.set_key(self.get_usable_keys()[1], self._icon_reset_stove_ignore_state)
        self.set_key(self.get_usable_keys()[2], self._icon_lamp_on)

        self._data_thread = Thread(target=self._fetch_data)
        self._data_thread.start()

    def update(self, keys_before: list[bool], keys: list[bool]) -> None:
        if keys[1] and not keys_before[1]:
            # turn alarm off
            self._turn_alarm_off()
        if keys[2] and not keys_before[2]:
            # reset alarm ignore state
            self._turn_alarm_ignore_state()
        if keys[3] and not keys_before[3]:
            self._lights_on = not self._lights_on
            # reset alarm ignore state
            self._set_hue_lights_state(self._lights_on)
            self._update_light_key()

    def _turn_alarm_off(self) -> None:
        requests.get(f"{KITCHENPICO_ENDPOINT}/ignore")

    def _turn_alarm_ignore_state(self) -> None:
        requests.get(f"{KITCHENPICO_ENDPOINT}/reset")

    def _set_hue_lights_state(self, active) -> None:
        for light in KitchenControlsApp.HUE_LIGHTS:
            hue.set_light(light, active)

    def _fetch_data(self) -> None:

        while self._running:
            # fetch temperature
            self._show_temp()
            self._check_light_state()
            time.sleep(10)

    def _show_temp(self) -> None:
        temp_data = requests.get(f"{KITCHENPICO_ENDPOINT}").json()
        temp = round(temp_data["ambient_temperature"], 1)

        temp_img = self._clear_img.copy()
        draw = ImageDraw.Draw(temp_img)
        font = ImageFont.truetype("./kitchencontrols/roboto.ttf", 24)
        draw.text(
            (36, 36),
            f"{temp}\n°C",
            (255, 255, 255),
            font=font,
            anchor="mm",
            align="center",
        )
        self.set_key(4, temp_img)

    def _check_light_state(self):
        data = hue.get_group(self.HUE_GROUP)
        self._lights_on = data["action"]["on"]
        self._update_light_key()

    def _update_light_key(self):
        if self._lights_on:
            self.set_key(3, self._icon_lamp_off)
        else:
            self.set_key(3, self._icon_lamp_on)
