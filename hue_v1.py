import json
from pathlib import Path

import requests

with (Path(__file__).parent / "config.json").open() as config_file:
    config = json.load(config_file)

HUE_BRIDGE_URL = config["hue"]["api_endpoint"]
HUE_USERNAME = config["hue"]["username"]
HUE_ENDPOINT = f"{HUE_BRIDGE_URL}/{HUE_USERNAME}"


def get_groups(rooms_only=False) -> list:
    data = requests.get(f"{HUE_ENDPOINT}/groups").json()
    if rooms_only:
        return {g: d for g, d in data.items() if d["type"] == "Room"}
    return data


def set_light(light: int, active: bool) -> None:
    requests.put(
        f"{HUE_ENDPOINT}/lights/{light}/state",
        json.dumps(
            {"on": active},
        ),
    )


def set_light_config(light: int, config: dict) -> None:
    requests.put(
        f"{HUE_ENDPOINT}/lights/{light}/state",
        json.dumps(
            config,
        ),
    )


def set_group(group: int, active: bool) -> None:
    requests.put(
        f"{HUE_ENDPOINT}/groups/{group}/action",
        json.dumps(
            {"on": active},
        ),
    )


def get_group(group: int) -> dict:
    return requests.get(f"{HUE_ENDPOINT}/groups/{group}").json()


def get_scenes(room: int | None = None) -> dict:
    scenes = requests.get(f"{HUE_ENDPOINT}/scenes").json()
    if room is not None:
        return {
            s_id: scene
            for s_id, scene in scenes.items()
            if scene["type"] == "GroupScene" and scene["group"] == str(room)
        }
    return scenes


def get_scene(scene: str) -> dict:
    return requests.get(f"{HUE_ENDPOINT}/scenes/{scene}").json()


def set_scene_active(scene_id: str | None = None, scene_obj: dict | None = None):
    if scene_obj is None:
        scene_obj = get_scene(scene_id)
    for light, state in scene_obj["lightstates"].items():
        set_light_config(light, state)
