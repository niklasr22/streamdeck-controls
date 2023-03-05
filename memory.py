import glob
import random

from PIL import Image, ImageDraw

from sdsystem import SDUserApp


class Memory(SDUserApp):

    PLAYER_COLORS = ["#FF0000", "#0000FF"]

    def __init__(self, memory_pics_dir: str, icon_path: str, backside_path: str) -> None:
        super().__init__("Memory")
        self._icon = Image.open(icon_path)

        self._backside = Image.open(backside_path)
        self._memory_cards: list[Image.Image] = []
        for file in glob.glob(memory_pics_dir):
            self._memory_cards.append(Image.open(file).resize((72, 72)))

        self._shuffle_memory()

    def _shuffle_memory(self):
        self._random_distribution = list(range(len(self._memory_cards))) * 2
        random.shuffle(self._random_distribution)

    def get_icon(self) -> Image:
        return self._icon

    def init(self) -> None:
        print("Started Memory")
        self._uncovered_keys = []
        self._players = [[], []]
        self._current_player = 0
        for key in self.get_usable_keys():
            self.set_key(key, self._backside)
        self._shuffle_memory()

    def _get_memory_card_for_key(self, key: int) -> Image:
        return self._memory_cards[self._random_distribution[key - 1]]

    def _check_uncovered_pair(self):
        if (
            len(self._uncovered_keys) == 2
            and self._random_distribution[self._uncovered_keys[0] - 1]
            == self._random_distribution[self._uncovered_keys[1] - 1]
        ):
            self._players[self._current_player].append(self._random_distribution[self._uncovered_keys[0] - 1])
            self._add_frame_to_valid_pair()
            self._uncovered_keys.clear()

    def _add_frame_to_valid_pair(self):
        for k in self._uncovered_keys:
            framed = self._get_memory_card_for_key(k).copy()
            draw = ImageDraw.Draw(framed)
            draw.rectangle(
                (0, 0, 72, 72), outline=self.PLAYER_COLORS[self._current_player], fill="#00000000", width=3, radius=7
            )
            self.set_key(k, framed)

    def _cover_uncovered_pair(self):
        if len(self._uncovered_keys) == 2:
            self.set_key(self._uncovered_keys.pop(), self._backside)
            self.set_key(self._uncovered_keys.pop(), self._backside)
            self._current_player = (self._current_player + 1) % 2

    def update(self, keys_before: list[bool], keys: list[bool]) -> None:
        for key, (pressed_before, pressed) in enumerate(zip(keys_before[1:], keys[1:])):
            key += 1
            if pressed and not pressed_before:
                if (
                    self._random_distribution[key - 1] not in self._players[0] + self._players[1]
                    and key not in self._uncovered_keys
                ):
                    self._cover_uncovered_pair()
                    self.set_key(key, self._get_memory_card_for_key(key))
                    self._uncovered_keys.append(key)
                    self._check_uncovered_pair()
                elif len(self._players[0]) + len(self._players[1]) == len(self._memory_cards):
                    # Game finished
                    if len(self._players[0]) > len(self._players[1]):
                        print(f"Player 1 won ({len(self._players[0])})")
                    elif len(self._players[0]) < len(self._players[1]):
                        print(f"Player 2 won ({len(self._players[1])})")
                    else:
                        print("Draw")
                    self.init()
