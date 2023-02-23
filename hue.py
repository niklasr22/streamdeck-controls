import json

import requests

with open("config.json") as config_file:
    config = json.load(config_file)

HUE_BRIDGE_URL = config["hue"]["api_endpoint"]
HUE_USERNAME = config["hue"]["username"]
HUE_ENDPOINT = f"{HUE_BRIDGE_URL}/{HUE_USERNAME}"


def get_rooms() -> list:
    data = requests.get(f"{HUE_ENDPOINT}/groups").json()
    return {g: d for g, d in data.items() if d["type"] == "Room"}


def get_scenes(group: int | None = None) -> list:
    data = requests.get(f"{HUE_ENDPOINT}/scenes").json()
    if group is not None:
        return {g: d for g, d in data.items() if d["type"] == "Room"}
    return data


def set_light(light, active) -> None:
    requests.put(
        f"{HUE_ENDPOINT}/lights/{light}/state",
        json.dumps(
            {"on": active},
        ),
    )


def set_group(group, active) -> None:
    requests.put(
        f"{HUE_ENDPOINT}/lights/{group}/action",
        json.dumps(
            {"on": active},
        ),
    )


def get_group(group) -> dict:
    return requests.get(f"{HUE_ENDPOINT}/groups/{group}").json()
