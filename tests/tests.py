#! python3
# tests.py

import json
import os
import re
import unittest

import discord

class TestMain(unittest.TestCase):

    def test_token(self):
        environ_token = os.environ.get("token", None)
        with open(os.path.join('data', 'token.txt')) as file:
            file_token = file.read()
        self.assertTrue(environ_token or file_token)

class TestUtils(unittest.TestCase):

    def test_cog_files_exist(self):
        filenames = [
            'messages.txt', 'tiers.txt', 'pings.txt', 'commands.txt',
            'spam.txt', 'censor.txt']
        for file in filenames:
            self.assertTrue(
                os.path.exists(os.path.join('data', file)))

class TestWelcomeMessage(unittest.TestCase):

    def open_file(self):
        path = os.path.join('data', 'welcome.txt')
        with open(path) as file:
            data = json.load(file)
        return data

    def test_file_format(self):
        data = self.open_file()
        self.assertEqual(list(data), ['private', 'public', 'fields'])
        self.assertTrue(isinstance(data['private'], bool))
        self.assertTrue(isinstance(data['public'], bool))
        self.assertTrue(isinstance(data['fields'], dict))

class TestReactionRolesCog(unittest.TestCase):

    def open_messages_file(self):
        path = os.path.join('data', 'messages.txt')
        with open(path) as file:
            data = {int(k):v for k, v in json.load(file).items()}
        return data

    def test_messages_file_format(self):
        data = self.open_messages_file()
        for msgid in data:
            self.assertTrue(isinstance(msgid, int))
            for emoji in data[msgid]:
                self.assertTrue(isinstance(data[msgid][emoji], list))
                for roleid in data[msgid][emoji]:
                    self.assertTrue(isinstance(roleid, int))

class TestGuildPointsCog(unittest.TestCase):

    def open_file(self):
        path = os.path.join('data', 'tiers.txt')
        with open(path) as file:
            data = {int(k):int(v) for k, v in json.load(file).items()}
        return data

    def test_file_format(self):
        data = self.open_file()
        for pts in data:
            self.assertTrue(isinstance(pts, int))
            self.assertTrue(isinstance(data[pts], int))

    def test_reaction_unicodes(self):
        reactions = {
            u"\u0031\ufe0f\u20e3": '1️⃣', u"\u0032\ufe0f\u20e3": '2️⃣',
            u"\u0033\ufe0f\u20e3": '3️⃣', u"\u0034\ufe0f\u20e3": '4️⃣',
            u"\u0035\ufe0f\u20e3": '5️⃣', u"\u0036\ufe0f\u20e3": '6️⃣',
            u"\u0037\ufe0f\u20e3": '7️⃣', u"\u0038\ufe0f\u20e3": '8️⃣',
            u"\u0039\ufe0f\u20e3": '9️⃣'}
        for uni in reactions:
            self.assertEqual(uni, reactions[uni])

    def test_exponential_function(self):
        upper = 10
        nums = [(1/2)**n for n in range(1, upper)]
        self.assertEqual(nums[0], 1/2)
        self.assertEqual(nums[-1], 1/512)
        for step in range(upper-2):
            self.assertEqual(nums[step]*1/2, nums[step+1])

class TestGhostPingCog(unittest.TestCase):

    def open_file(self):
        path = os.path.join('data', 'pings.txt')
        with open(path) as file:
            data = json.load(file)
        return data

    def test_file_format(self):
        data = self.open_file()
        self.assertEqual(list(data), ["everyone", "roles", "members"])
        for group in data:
            self.assertTrue(isinstance(data[group], bool))

class TestModerationCog(unittest.TestCase):

    def open_commands_file(self):
        path = os.path.join('data', 'commands.txt')
        with open(path) as file:
            data = json.load(file)
        return data

    def open_spam_file(self):
        path = os.path.join('data', 'spam.txt')
        with open(path) as file:
            data = json.load(file)
        return data

    def open_censor_file(self):
        path = os.path.join('data', 'censor.txt')
        with open(path) as file:
            data = json.load(file)
        return data

    def test_commands_file_format(self):
        data = self.open_commands_file()
        for cmd in data:
            self.assertTrue(isinstance(data[cmd], dict))
            self.assertEqual(list(data[cmd]), ["channels", "roles"])
            for key in data[cmd]:
                self.assertTrue(isinstance(data[cmd][key], list))
                for item in data[cmd][key]:
                    self.assertTrue(isinstance(item, int))

    def test_spam_file_format(self):
        data = self.open_spam_file()
        self.assertEqual(list(data), ["limit", "interval"])
        for param in data:
            self.assertTrue(isinstance(data[param], int))

    def test_censor_file_format(self):
        data = self.open_censor_file()
        self.assertEqual(list(data), ["blacklist", "separators", "excluded"])
        self.assertTrue(isinstance(data["blacklist"], list))
        self.assertTrue(isinstance(data["separators"], str))
        self.assertTrue(isinstance(data["excluded"], str))

    def test_censor_regular_expression(self):
        data = self.open_censor_file()
        separators, excluded = data["separators"], data["excluded"]
        word = "badword"
        regex_match_true = re.compile(
            fr"[{separators}]*".join(list(word)), re.IGNORECASE)
        regex_match_none = re.compile(
            fr"([{excluded}]+{word})|({word}[{excluded}]+)", re.IGNORECASE)
        cases = {
            "badword": True, "BADWORD": True, "a-badword": True,
            "notbadword": False, "badwordfake": False,
            "~b@a$d^w*o)r+d}": True, "B1A3D5W7O9R-D": True}
        for case in cases:
            match_true = regex_match_true.search(case)
            match_none = regex_match_none.search(case)
            profane = match_true and match_none is None
            self.assertEqual(cases[case], profane)

class TestVoiceChannelControlCog(unittest.TestCase):

    def test_reaction_unicodes(self):
        reactions = {
            u'\u274c': '❌', "\U0001f507": '🔇', "\U0001f508": '🔈', 
            "\U0001f3f3": '🏳'}
        for uni in reactions:
            self.assertEqual(uni, reactions[uni])

if __name__ == '__main__':
    unittest.main()
