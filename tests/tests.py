#! python3
# tests.py

import discord

import json
import os
import re
import string
import unittest

class TestSpamDetection(unittest.TestCase):

    def open_parameters(self):
        path = os.path.join('data', 'spam_parameters.txt')
        with open(path) as file:
            parameters = json.load(file)
        return parameters

    def test_open_spam_parameters_file(self):
        parameters = self.open_parameters()
        self.assertIn('Limit', parameters)
        self.assertIn('Interval', parameters)
        self.assertTrue(isinstance(parameters['Limit'], int))
        self.assertTrue(isinstance(parameters['Interval'], int))

class TestCensor(unittest.TestCase):

    def test_open_blacklist_file(self):
        path = os.path.join('data', 'blacklisted_words.txt')
        with open(path) as file:
            blacklist = file.read().split('\n')
        self.assertTrue(isinstance(blacklist, list))

    def test_regular_expression(self):
        test_cases = ['word', 'w o r d', '!w#o%r&d(', '0w2o4r6d8']
        word = 'word'
        separators = string.punctuation+string.digits+string.whitespace
        regex = re.compile(fr'[{separators}]*'.join(list(word)))
        for case in test_cases:
            self.assertTrue(regex.search(case))

class TestGameLobbyControl(unittest.TestCase):

    def test_regular_expression(self):
        regex = re.compile(r"_Claimed: (Lobby [0-9])_")
        for i in range(10):
            role_name = f"_Claimed: Lobby {i}_"
            self.assertTrue(regex.search(role_name))

    def test_retrieve_lobby_by_emoji_name(self):
        reactions = {}
        for num in range(10):
            emoji = str(num).encode()+b'\xef\xb8\x8f\xe2\x83\xa3'
            reactions.setdefault(emoji, num)
        for emoji in reactions:
            self.assertEqual(int(emoji.decode()[0]), reactions[emoji])

if __name__ == '__main__':
    unittest.main()
