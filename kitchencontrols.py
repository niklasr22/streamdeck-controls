import json
import requests
from sdsystem import SDUserApp
from PIL import Image


with open("config.json") as config_file:
    config = json.load(config_file)

HUE_BRIDGE_URL = config["hue"]["api_endpoint"]
HUE_USERNAME = config["hue"]["username"]


class KitchenControlsApp(SDUserApp):
    HUE_LIGHTS = [5, 6, 7]

    def __init__(self) -> None:
        super().__init__("Kitchen Controls")
        self._icon = Image.open("./kitchencontrols/lamp_on.jpeg")
        self._icon_ignore_hot_stove = Image.open("./kitchencontrols/alarm_off.jpeg")
        self._icon_reset_stove_ignore_state = Image.open(
            "./kitchencontrols/alarm_reset.jpeg"
        )
        self._icon_lamp_on = Image.open("./kitchencontrols/lamp_on.jpeg")
        self._icon_lamp_off = Image.open("./kitchencontrols/lamp_off.jpeg")

        self._lights_on = False

    def get_icon(self) -> Image:
        return self._icon

    def init(self) -> None:
        print("Started Kitchen Controls")
        self.set_key(self.get_usable_keys()[0], self._icon_ignore_hot_stove)
        self.set_key(self.get_usable_keys()[1], self._icon_reset_stove_ignore_state)
        self.set_key(self.get_usable_keys()[2], self._icon_lamp_on)

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
            if self._lights_on:
                self.set_key(3, self._icon_lamp_off)
            else:
                self.set_key(3, self._icon_lamp_on)

    def _turn_alarm_off(self):
        requests.get("http://kitchenpico/ignore")

    def _turn_alarm_ignore_state(self):
        requests.get("http://kitchenpico/reset")

    def _set_hue_lights_state(self, active):
        for light in KitchenControlsApp.HUE_LIGHTS:
            self._set_hue_light_state(light, active)

    def _set_hue_light_state(self, light, active):
        requests.put(
            f"{HUE_BRIDGE_URL}/{HUE_USERNAME}/lights/{light}/state",
            json.dumps(
                {"on": active},
            ),
        )

    def _fetch_data(self):
        ...
