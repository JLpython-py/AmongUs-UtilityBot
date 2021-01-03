#! python3
# tests.py

import csv
import json
import os
import re
import string
import unittest

import discord

class TestMain(unittest.TestCase):

    def test_token(self):
        environment_token = os.environ.get("UTILS", None)
        with open(os.path.join('data', 'tokens.csv')) as file:
            tokens = dict(list(csv.reader(file, delimiter='\t')))
            file_token = tokens.get("UTILS", None)
        self.assertTrue(environment_token or file_token)

class TestModeration(unittest.TestCase):

    def open_command_restrictions(self):
        path = os.path.join('data', 'command_restrictions.txt')
        with open(path) as file:
            restrictions = json.load(file)
        return restrictions

    def test_open_command_restrictions_file(self):
        restrictions = self.open_command_restrictions()
        for command in restrictions:
            self.assertIn('channels', restrictions[command])
            self.assertIn('roles', restrictions[command])
            for category in restrictions[command]:
                self.assertTrue(isinstance(restrictions[command][category], list))
                for item in restrictions[command][category]:
                    self.assertTrue(isinstance(item, int))

    def test_command_regular_expression(self):
        messages = [
            "*suggestion Suggestion goes here", "*bug Bug goes here",
            "*comment Comment goes here", "*give_points 10", "*get_points", "*get_tickets",
            "*claim"]
        regex = re.compile(fr"^\*(.*)")
        for msg in messages:
            command = regex.search(msg)
            self.assertTrue(command is not None)

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

class TestVoiceChannelControl(unittest.TestCase):

    def test_retrieve_number_by_emoji(self):
        reactions = {}
        for num in range(10):
            emoji = str(num).encode()+b'\xef\xb8\x8f\xe2\x83\xa3'
            reactions.setdefault(emoji, num)
        for emoji in reactions:
            self.assertEqual(int(emoji.decode()[0]), reactions[emoji])

if __name__ == '__main__':
    unittest.main()
