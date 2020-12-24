#! python3
# tests.py

import re
import unittest

class TestGameLobbyControl(unittest.TestCase):

    def test_regular_expression(self):
        regex = re.compile(r"_Claimed: (Lobby [0-9])_")
        for i in range(10):
            role_name = f"_Claimed: Lobby {i}_"
            self.assertTrue(regex.search(role_name))

    def test_reactions_to_add(self):
        reactions = {}
        for i in range(10):
            channel_name = f"Lobby {i}"
            emoji = str(i).encode() +  b'\xef\xb8\x8f\xe2\x83\xa3'
            reactions.setdefault(channel_name, emoji)
            
if __name__ == '__main__':
    unittest.main()
