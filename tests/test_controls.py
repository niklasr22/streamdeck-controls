import asyncio
import io
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image

# Hardware behavior is tested through a fake HID device; no native library is needed.
with patch.dict(sys.modules, {"hid": SimpleNamespace(HIDException=OSError, Device=object)}):
    from sd_controls.sdsystem import Orientation, SDSystem, _SDApp
    from sd_controls.streamdeck import StreamDeck, StreamDeckMk2


class FakeDeck(StreamDeck):
    _KEY_COUNT = 15

    def set_key_image(self, key, image):
        return True

    def _get_data(self):
        self.stop()
        return None


class SystemTests(unittest.TestCase):
    def setUp(self):
        self.deck = FakeDeck()
        self.system = SDSystem(deck=self.deck)
        self.addCleanup(self.system.close)

    def test_brightness_returned(self):
        self.system.set_brightness(42)
        self.assertEqual(self.system.get_brightness(), 42)

    def test_lock_released_after_image_error(self):
        with patch.object(self.deck, "set_key_image", side_effect=ValueError):
            with self.assertRaises(ValueError):
                self.system.set_key(1, Image.new("RGB", (70, 70)))
        self.assertTrue(self.system._key_lock.acquire(blocking=False))
        self.system._key_lock.release()

    def test_invalid_keys_rejected(self):
        for key in (-1, 15):
            self.assertFalse(self.system.set_key(key, Image.new("RGB", (70, 70))))

    def test_flipped_events_match_logical_keys(self):
        self.system._orientation = Orientation.FLIPPED_180
        self.system._create_key_map()
        app = Mock(spec=_SDApp)
        self.system._running_app = app
        before, after = [False] * 15, [False] * 15
        after[13] = True
        self.system._system_key_listener(self.deck, before, after)
        expected = [False] * 15
        expected[1] = True
        app.key_event.assert_called_once_with(before, expected)

    def test_close_is_idempotent(self):
        with patch.object(self.deck, "stop") as stop:
            self.system.close()
            self.system.close()
            stop.assert_called_once()

    def test_start_closes_on_read_failure(self):
        with patch.object(self.deck, "_get_data", side_effect=OSError("disconnected")):
            with self.assertRaises(OSError):
                self.system.start()
        self.assertTrue(self.system._closed)
        self.assertFalse(self.deck._running)

    def test_shutdown_stops_deck_after_disconnect(self):
        with patch.object(self.deck, "set_standby_timeout", side_effect=OSError("disconnected")):
            with self.assertLogs(level="ERROR"):
                self.system.close()
        self.assertTrue(self.system._closed)
        self.assertFalse(self.deck._running)

    def test_sync_callback_without_event_loop(self):
        app = _SDApp()
        callback = Mock()
        app._key_down_callbacks[1].append(callback)
        app.key_event([False, False], [False, True])
        callback.assert_called_once()


class DeckTests(unittest.TestCase):
    def test_initial_timeout(self):
        self.assertEqual(FakeDeck().get_standby_timeout(), 0)

    def test_run_resets_running_after_error(self):
        deck = FakeDeck()
        with patch.object(deck, "_get_data", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                asyncio.run(deck.run())
        self.assertFalse(deck._running)

    def test_short_hid_report_ignored(self):
        device = Mock()
        device.read.return_value = b"\x00" * 5
        self.assertIsNone(StreamDeckMk2(device)._get_data())

    def test_rgba_image_encoded_and_packet_padded(self):
        device = Mock()
        deck = StreamDeckMk2(device)
        self.assertTrue(deck.set_key_image(0, Image.new("RGBA", (70, 70))))
        packets = [call.args[0] for call in device.write.call_args_list]
        self.assertTrue(all(len(packet) == 1024 for packet in packets))
        self.assertEqual(packets[-1][3], 1)
        payload = b"".join(packet[8 : 8 + int.from_bytes(packet[4:6], "little")] for packet in packets)
        with Image.open(io.BytesIO(payload)) as image:
            self.assertEqual(image.mode, "RGB")

    def test_invalid_hardware_key_does_not_write(self):
        device = Mock()
        deck = StreamDeckMk2(device)
        for key in (-1, 15):
            self.assertFalse(deck.set_key_image(key, Image.new("RGB", (70, 70))))
        device.write.assert_not_called()
