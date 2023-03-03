import json
import time
from threading import Thread

import requests
from PIL import Image, ImageDraw, ImageFont

import hue_v1
from sdsystem import SDUserApp

KITCHENPICO_ENDPOINT = "http://kitchenpico"


class KitchenControlsApp(SDUserApp):
    HUE_LIGHTS = [5, 6, 7]
    HUE_GROUP = 2  # room id

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

        self.font22 = ImageFont.truetype("./kitchencontrols/roboto.ttf", 22)
        self.font14 = ImageFont.truetype("./kitchencontrols/roboto.ttf", 14)

        self._lights_on = False

        self._scenes: dict[int, str] = {}

    def get_icon(self) -> Image:
        return self._icon

    def init(self) -> None:
        print("Started Kitchen Controls")
        self.set_key(self.get_usable_keys()[0], self._icon_ignore_hot_stove)
        self.set_key(self.get_usable_keys()[1], self._icon_reset_stove_ignore_state)
        self.set_key(self.get_usable_keys()[2], self._icon_lamp_on)

        self._data_thread = Thread(target=self._fetch_data)
        self._data_thread.start()

    def close(self) -> None:
        self._data_thread.join()

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
            hue_v1.set_group(self.HUE_GROUP, self._lights_on)
            self._update_light_key()

        scenes = self._scenes.copy()
        for scene_key, scene in scenes.items():
            if keys[scene_key] and not keys_before[scene_key]:
                hue_v1.set_scene_active(scene)
                self._lights_on = True
                self._update_light_key()

    def _turn_alarm_off(self) -> None:
        try:
            requests.get(f"{KITCHENPICO_ENDPOINT}/ignore")
        except requests.exceptions.ConnectionError:
            return

    def _turn_alarm_ignore_state(self) -> None:
        try:
            requests.get(f"{KITCHENPICO_ENDPOINT}/reset")
        except requests.exceptions.ConnectionError:
            return

    def _set_hue_lights_state(self, active) -> None:
        for light in KitchenControlsApp.HUE_LIGHTS:
            hue_v1.set_light(light, active)

    def _fetch_data(self) -> None:

        while self._running:
            # fetch temperature
            self._show_temp()
            # check light state
            self._check_light_state()

            # scenes
            self._update_scenes()

            time.sleep(10)

    def _generate_temp_img(self, temp: float, label: str):
        temp_img = self._clear_img.copy()
        draw = ImageDraw.Draw(temp_img)
        draw.text(
            (36, 36),
            f"{temp}\n°C\n{label}",
            (255, 255, 255),
            font=self.font22,
            anchor="mm",
            align="center",
        )
        return temp_img

    def _show_temp(self) -> None:
        try:
            temp_data = requests.get(f"{KITCHENPICO_ENDPOINT}").json()
        except requests.exceptions.ConnectionError:
            return
        temp_ambient = round(temp_data["ambient_temperature"], 1)
        temp_object = round(temp_data["object_temperature_1"], 1)

        self.set_key(4, self._generate_temp_img(temp_ambient, "Room"))
        self.set_key(9, self._generate_temp_img(temp_object, "Object"))

    def _check_light_state(self):
        try:
            data = hue_v1.get_group(self.HUE_GROUP)
        except requests.exceptions.ConnectionError:
            return
        self._lights_on = data["action"]["on"]
        self._update_light_key()

    def _generate_labeled_img(self, img: Image, label: str) -> Image:
        labeled_img = img.copy()
        draw = ImageDraw.Draw(labeled_img)
        text_pos = (36, 52)
        bbox = draw.textbbox(
            text_pos,
            label,
            font=self.font14,
            anchor="mm",
            align="center",
        )
        draw.rectangle(bbox, fill="#00000080")
        draw.text(
            text_pos,
            label,
            (255, 255, 255),
            font=self.font14,
            anchor="mm",
            align="center",
        )

        return labeled_img

    def _update_scenes(self):
        room_scenes = hue_v1.get_scenes(room=self.HUE_GROUP)

        self._scenes.clear()
        for i, scene_id in enumerate(list(room_scenes.keys())[:5]):
            scene = room_scenes[scene_id]
            key = 10 + i
            self.set_key(
                key, self._generate_labeled_img(self._icon_lamp_on, scene["name"])
            )
            self._scenes[key] = scene_id

    def _update_light_key(self):
        if self._lights_on:
            self.set_key(3, self._icon_lamp_off)
        else:
            self.set_key(3, self._icon_lamp_on)
