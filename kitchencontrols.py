import time
from threading import Thread

import requests
from PIL import Image, ImageDraw

import hue_v1
from sdsystem import SDUserApp

KITCHENPICO_ENDPOINT = "http://kitchenpico"


class KitchenControlsApp(SDUserApp):
    HUE_KITCHEN_GROUP = "2"  # kitchen group id
    HUE_BATH_GROUP = "4"  # bath group id

    KEY_IGNORE_HOT_STOVE = 1
    KEY_RESET_IGNORE_HOT_STOVE = 2
    KEY_KITCHEN_LAMP = 3
    KEY_ROOM_TEMP = 4
    KEY_OBJECT_TEMP = 9
    KEY_BATH_LAMP = 5

    UPDATE_PERIOD = 5  # update waiting period

    def __init__(self) -> None:
        super().__init__("Kitchen Controls")
        self._icon = Image.open("./kitchencontrols/lamp_on.jpeg")
        self._icon_ignore_hot_stove = Image.open("./kitchencontrols/alarm_off.jpeg")
        self._icon_reset_stove_ignore_state = Image.open("./kitchencontrols/alarm_reset.jpeg")
        self._icon_lamp_on = Image.open("./kitchencontrols/lamp_on.jpeg")
        self._icon_lamp_off = Image.open("./kitchencontrols/lamp_off.jpeg")
        self._clear_img = Image.open("./imgs/clear.jpeg")

        # bath room
        self._icon_fan = SDUserApp.generate_labeled_img(Image.open("./kitchencontrols/fan.jpeg"), "WC")
        self._icon_bath_lamp = SDUserApp.generate_labeled_img(self._icon_lamp_on, "WC")

        self._kitchen_lights_on = False
        self._bath_lights_on = False

        self._scenes: dict[int, str] = {}

    def get_icon(self) -> Image:
        return self._icon

    def init(self) -> None:
        print("Started Kitchen Controls")

        # kitchen
        self.set_key(self.KEY_IGNORE_HOT_STOVE, self._icon_ignore_hot_stove)
        self.set_key(self.KEY_RESET_IGNORE_HOT_STOVE, self._icon_reset_stove_ignore_state)
        self.set_key(self.KEY_KITCHEN_LAMP, self._icon_lamp_on)

        # bath room
        self.set_key(self.KEY_BATH_LAMP, self._icon_fan)

        self._data_thread = Thread(target=self._fetch_data)
        self._data_thread.start()

    def close(self) -> None:
        self._data_thread.join()

    def update(self, keys_before: list[bool], keys: list[bool]) -> None:
        if keys[self.KEY_IGNORE_HOT_STOVE] and not keys_before[self.KEY_IGNORE_HOT_STOVE]:
            # turn alarm off
            self._turn_alarm_off()
        if keys[self.KEY_RESET_IGNORE_HOT_STOVE] and not keys_before[self.KEY_RESET_IGNORE_HOT_STOVE]:
            # reset alarm ignore state
            self._reset_alarm_ignore_state()
        if keys[self.KEY_KITCHEN_LAMP] and not keys_before[self.KEY_KITCHEN_LAMP]:
            self._kitchen_lights_on = not self._kitchen_lights_on
            hue_v1.set_group(self.HUE_KITCHEN_GROUP, self._kitchen_lights_on)
            self._update_kitchen_light_key()
        if keys[self.KEY_BATH_LAMP] and not keys_before[self.KEY_BATH_LAMP]:
            self._bath_lights_on = not self._bath_lights_on
            hue_v1.set_group(self.HUE_BATH_GROUP, self._bath_lights_on)
            self._update_bath_light_key()

        scenes = self._scenes.copy()
        for scene_key, scene in scenes.items():
            if keys[scene_key] and not keys_before[scene_key]:
                hue_v1.set_scene_active(scene)
                self._kitchen_lights_on = True
                self._update_kitchen_light_key()

    def _turn_alarm_off(self) -> None:
        try:
            requests.get(f"{KITCHENPICO_ENDPOINT}/ignore")
        except requests.exceptions.ConnectionError:
            return

    def _reset_alarm_ignore_state(self) -> None:
        try:
            requests.get(f"{KITCHENPICO_ENDPOINT}/reset")
        except requests.exceptions.ConnectionError:
            return

    def _fetch_data(self) -> None:

        while self._running:
            # fetch temperature
            self._show_temp()
            # check light states
            self._check_light_states()

            # scenes
            self._update_scenes()

            time.sleep(self.UPDATE_PERIOD)

    def _generate_temp_img(self, temp: float, label: str):
        temp_img = self._clear_img.copy()
        draw = ImageDraw.Draw(temp_img)
        draw.text(
            (36, 36),
            f"{temp}\n°C\n{label}",
            (255, 255, 255),
            font=SDUserApp.font(20),
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

        self.set_key(self.KEY_ROOM_TEMP, self._generate_temp_img(temp_ambient, "Room"))
        self.set_key(self.KEY_OBJECT_TEMP, self._generate_temp_img(temp_object, "Object"))

    def _check_light_states(self):
        try:
            groups = hue_v1.get_groups()
        except requests.exceptions.ConnectionError:
            return
        self._kitchen_lights_on = groups[self.HUE_KITCHEN_GROUP]["action"]["on"]
        self._bath_lights_on = groups[self.HUE_BATH_GROUP]["action"]["on"]
        self._update_kitchen_light_key()

    def _update_scenes(self):
        room_scenes = hue_v1.get_scenes(room=self.HUE_KITCHEN_GROUP)

        self._scenes.clear()
        for i, scene_id in enumerate(list(room_scenes.keys())[:5]):
            scene = room_scenes[scene_id]
            key = 10 + i
            self.set_key(key, SDUserApp.generate_labeled_img(self._icon_lamp_on, scene["name"]))
            self._scenes[key] = scene_id

    def _update_kitchen_light_key(self):
        if self._kitchen_lights_on:
            self.set_key(self.KEY_KITCHEN_LAMP, self._icon_lamp_off)
        else:
            self.set_key(self.KEY_KITCHEN_LAMP, self._icon_lamp_on)

    def _update_bath_light_key(self):
        if self._bath_lights_on:
            self.set_key(self.KEY_BATH_LAMP, self._icon_bath_lamp)
        else:
            self.set_key(self.KEY_BATH_LAMP, self._icon_fan)
