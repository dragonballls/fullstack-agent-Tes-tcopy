import unittest

from quality_of_life.intents import parse_intent


class QoLIntentTests(unittest.TestCase):
    def test_location_intents(self):
        self.assertEqual(parse_intent("open Tokyo").kind, "place_search")
        self.assertEqual(parse_intent("show me Los Angeles").arguments["query"], "Los Angeles")
        self.assertEqual(parse_intent("where am I").kind, "locate_me")
        self.assertEqual(parse_intent("take me to the airport").kind, "route")

    def test_computer_and_chat_intents(self):
        move = parse_intent("move mouse to 100 200")
        self.assertEqual(move.kind, "computer_action")
        self.assertEqual(move.arguments, {"operation": "move", "x": 100, "y": 200})
        self.assertEqual(parse_intent("hello Jarvis").kind, "chat")

    def test_phone_device_intents(self):
        for text in ("list my phones", "show my devices"):
            self.assertEqual(parse_intent(text).kind, "device_list")
        for text in ("refresh my phones", "scan my devices"):
            self.assertEqual(parse_intent(text).kind, "device_refresh")
        selected = parse_intent("switch to my phone Main Phone")
        self.assertEqual(selected.kind, "device_select")
        self.assertEqual(selected.arguments["device"], "Main Phone")
        self.assertEqual(parse_intent("show my phone").kind, "device_screen")
        screen = parse_intent("view my device Main Phone")
        self.assertEqual(screen.kind, "device_screen")
        self.assertEqual(screen.arguments["device"], "Main Phone")
        hand = parse_intent("use hand control on my phone Main Phone")
        self.assertEqual(hand.kind, "device_hand_target")
        self.assertEqual(hand.arguments["device"], "Main Phone")

    def test_show_all_phone_screens_intent(self):
        for text in ("show all my phones", "show all phone screens", "mirror all my phones", "view all my devices"):
            self.assertEqual(parse_intent(text).kind, "device_screen_all")


if __name__ == "__main__":
    unittest.main()
