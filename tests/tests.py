#! python3
# tests.py

import discord

import re
import unittest

class TestGameLobbyControl(unittest.TestCase):

    def test_embeds(self, embed, fields):
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        for i, field in enumerate(fields):
            self.assertEqual(embed.fields[i].name, field)
            self.assertEqual(embed.fields[i].value, fields[field])

    def test_regular_expression(self):
        regex = re.compile(r"_Claimed: (Lobby [0-9])_")
        for i in range(10):
            role_name = f"_Claimed: Lobby {i}_"
            self.assertTrue(regex.search(role_name))

    def test_claim_panel_embed(self):
        embed = discord.Embed(title="Game Lobby Control", color=0x00ff00)
        fields = {
            "Claim": "Use the reactions below to claim a lobby",
            "Cancel": "React with :x: to cancel"}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        self.test_embeds(embed, fields)

    def test_retrieve_lobby_by_emoji_name(self):
        reactions = {}
        for num in range(10):
            emoji = str(num).encode()+b'\xef\xb8\x8f\xe2\x83\xa3'
            reactions.setdefault(emoji, num)
        for emoji in reactions:
            self.assertEqual(int(emoji.decode()[0]), reactions[emoji])

    def test_voice_control_panel_embed(self):
        embed = discord.Embed(title="Game Lobby Control", color=0x00ff00)
        fields = {
            "Claimed": "You have successfully claimed Lobby {num}",
            "Voice Control": '\n'.join([
                "You can control the voices of the members of Lobby {num}",
                "Mute with :mute:",
                "Unmute with :speaker:"
                ]),
            "Yield": '\n'.join([
                "Yield your claim on the game lobby when you are finished",
                "Yield with :flag_white:"
                ])}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        self.test_embeds(embed, fields)

if __name__ == '__main__':
    unittest.main()
