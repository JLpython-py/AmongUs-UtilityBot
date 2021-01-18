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
        with open('token.txt') as file:
            file_token = file.read()
        self.assertTrue(environ_token or file_token)

class TestUtils(unittest.TestCase):

    def test_cog_files_exist(self):
        filenames = [
            'ghost_ping.txt', 'guild_points.txt', 'moderation.txt',
            'reaction_roles.txt', 'voice_channel_control.txt']
        for file in filenames:
            self.assertTrue(
                os.path.exists(os.path.join('data', file)))

<<<<<<< HEAD
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
=======
class TestGhostPingCog(unittest.TestCase):
>>>>>>> 88b755197e9664d65ac29dd74d5d63e30d187191

    def open_pings_file(self):
        with open(os.path.join('data', 'ghost_ping.txt')) as file:
            return json.load(file)

    def test_pings_file_format(self):
        data = self.open_pings_file()
        self.assertEqual(list(data), ["everyone", "roles", "members"])
        self.assertTrue(
            all([isinstance(data[i], bool) for i in data]))

class TestGuildPointsCog(unittest.TestCase):

<<<<<<< HEAD
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
=======
    def open_tiers_file(self):
        with open(os.path.join('data', 'guild_points.txt')) as file:
            return {int(k):int(v) for k, v in json.load(file).items()}

    def test_tiers_file_format(self):
        data = self.open_tiers_file()
        self.assertTrue(all([isinstance(i, int) for i in data]))
        self.assertTrue(all([isinstance(data[i], int) for i in data]))
>>>>>>> 88b755197e9664d65ac29dd74d5d63e30d187191

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

<<<<<<< HEAD
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

=======
>>>>>>> 88b755197e9664d65ac29dd74d5d63e30d187191
class TestModerationCog(unittest.TestCase):

    def open_file(self):
        with open(os.path.join('data', 'moderation.txt')) as file:
            return json.load(file)

    def test_file_format(self):
        data = self.open_file()
        self.assertEqual(
            list(data),
            ["actives", "blacklist", "characters", "spam", "commands"])

    def test_actives(self):
        data = self.open_file()["actives"]
        self.assertTrue(isinstance(data, dict))
        self.assertEqual(list(data), ["commands", "spam", "censor"])
        self.assertTrue(
            all([isinstance(i, bool) for i in data.values()]))

    def test_blacklist(self):
        data = self.open_file()["blacklist"]
        self.assertTrue(isinstance(data, list))
        self.assertTrue(
            all([isinstance(i, str) for i in data]))

    def test_characters(self):
        data = self.open_file()["characters"]
        self.assertTrue(isinstance(data, list))
        self.assertTrue(
            all([isinstance(i, str) for i in data]))

    def test_spam(self):
        data = self.open_file()["spam"]
        self.assertTrue(isinstance(data, list))
        self.assertTrue(
            all([isinstance(i, int) for i in data]))

    def test_commands(self):
        data = self.open_file()["commands"]
        self.assertTrue(isinstance(data, dict))
        self.assertTrue(
            all([isinstance(i, str) for i in data]))
        self.assertTrue(
            all([isinstance(data[i], dict) for i in data]))
        self.assertTrue(
            all([isinstance(j, str)
                 for i in data for j in data[i]]))
        self.assertTrue(
            all([isinstance(data[i][j], list)
                 for i in data for j in data[i]]))
        self.assertTrue(
            all([isinstance(k, int)
                 for i in data for j in data[i] for k in data[i][j]]))

    def test_censor_regular_expression(self):
        included, excluded = self.open_file()["characters"]
        word = "badword"
        regex_match_true = re.compile(
            fr"[{included}]*".join(list(word)), re.IGNORECASE)
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

class TestReactionRolesCog(unittest.TestCase):

    def open_messages_file(self):
        with open(os.path.join('data', 'reaction_roles.txt')) as file:
            return {int(k):v for k, v in json.load(file).items()}

    def test_file_format(self):
        data = self.open_messages_file()
        self.assertTrue(
            all([isinstance(i, int) for i in data]))
        self.assertTrue(
            all([isinstance(data[i][j], list)
                 for i in data for j in data[i]]))
        self.assertTrue(
            all([isinstance(k, int)
                 for i in data for j in data[i] for k in data[i][j]]))

class TestVoiceChannelControlCog(unittest.TestCase):

    def open_file(self):
        with open(os.path.join('data', 'voice_channel_control.txt')) as file:
            return json.load(file)

    def test_file_format(self):
        data = self.open_file()
        self.assertEqual(list(data), ['category'])
        self.assertTrue(isinstance(data['category'], int))
            
    def test_reaction_unicodes(self):
        reactions = {
            u'\u274c': '❌', "\U0001f507": '🔇', "\U0001f508": '🔈', 
            "\U0001f3f3": '🏳'}
        for uni in reactions:
            self.assertEqual(uni, reactions[uni])

if __name__ == '__main__':
    unittest.main()
