#! python3
# bots.py

'''

'''

import asyncio
import csv
import datetime
import functools
import json
import logging
import os
import random
import re
import string

import discord
from discord.ext import commands

logging.basicConfig(level=logging.INFO, format=' %(asctime)s - %(levelname)s - %(message)s')

class UtilityBot(commands.Bot):
    ''' 
'''
    def __init__(self, *, command_prefix, name, command_channels):
        '''
'''
        #Manage intents to allow bot to view all members
        intents = discord.Intents.default()
        intents.members = True
        commands.Bot.__init__(
            self, command_prefix=command_prefix, intents=intents,
            self_bot=False)
        #Load regular expression and tier data
        with open(os.path.join('data', 'regular_expressions.csv')) as file:
            self.regexes = dict(list(csv.reader(file)))
        with open(os.path.join('data', 'tiers.csv')) as file:
            self.tiers = dict(list(csv.reader(file)))
            self.tiers = {int(k):v for k, v in self.tiers.items()}
        self.name = name
        self.command_channels = command_channels
        self.censor = Censor()
        self.spam_detection = SpamDetection()
        self.lobby_claims = {}
        self.execute_commands()

    async def on_ready(self):
        ''' 
'''
        logging.info("Ready: %(self.name)s")

    async def on_member_join(self, member):
        '''
'''
        logging.info("Member Join: %(member)s")
        if member.bot:
            return
        direct_message = await member.create_dm()
        embed = discord.Embed(
            title=f"Welcome {member.name}, to the Among Us Discord server",
            color=0xff0000)
        fields = {
            "Gain Access": "\n".join([
                "To gain full access to the server, read the rules in #rules",
                "Then, react to the message to be granted the 'Member' role",
                "You will have general access to the server with that role"]),
            "Bots": "\n".join([
                "In this server, there are three different classes of bots",
                "They are Moderator Bots, Utility Bots, and Map Bots",
                "The corresponding bots for each class are listed below:",
                "- MEE6 (!)",
                "- Utils (*)",
                "- Mira HQ (MiraHQ.), Polus (Polus.), The Skeld (TheSkeld.)"]),
            "Questions?": "\n".join([
                "Channel information can be found in #channel-descriptions",
                "Bot help can be found using the 'help' command for each bot",
                "If you still have questions, try asking others in the server",
                "You can always ask someone with the 'Moderator' role too"])}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await direct_message.send(embed=embed)

    async def on_message(self, message):
        logging.info("Message: %(message)s")
        #Ignore all bot messages
        if message.author.bot:
            return
        #Reject any commands in direct message channels
        if message.content.startswith('*')\
           and "Direct Message" in str(message.channel):
            await message.channel.send(
                "Direct Message channels do not support commands")
            return
        #Parse message for any blacklisted words
        await self.censor.parse(message)
        #Check message and channel messaging history for instances of spam
        await self.spam_detection.check(message)
        #Award Bounty Tickets
        if message.channel.category and\
           message.channel.category.name in ['General', 'Among Us']:
            guild = message.guild
            rand_channel = random.choice(
                discord.utils.get(
                    guild.categories, name=message.channel.category.name
                    ).channels)
            rand_member = random.choice(guild.members)
            if rand_channel.name == message.channel.name:
                await self.bounty_tickets(message)
                if rand_member.name == message.author.name:
                    await self.new_bounty(message)
        #Get the regular expression for the channel
        regex = re.compile(r'.*')
        for channel in self.regexes:
            if channel == message.channel.name and channel in self.regexes:
                regex = re.compile(self.regexes[channel])
                break
        #Delete message if it does not fit the regular expressions
        help_regex = re.compile(r'^\*help')
        results = regex.search(message.content)
        help_results = help_regex.search(message.content)
        if results is not None or help_results is not None:
            await self.process_commands(message)
        else:
            await message.delete()
            return

    async def on_message_delete(self, message):
        logging.info("Message Delete: %(message)s")
        #Check deleted message for ghost ping
        await self.ghost_ping(message)

    async def on_voice_state_update(self, member, before, after):
        logging.info("Voice State Update: %((member, before, after))s")
        #If the user disconnected, check if the user had a game lobby claim
        if before.channel and after.channel is None:
            regex = re.compile(r"_Claimed: (Lobby [0-9])_")
            for role in member.roles:
                if regex.search(role.name):
                    lobby = regex.search(role.name).group(1)
                    await self.disconnect_with_claim(member, lobby)
        #Mute new user if other members are muted when new user joins
        elif before.channel is None and after.channel:
            claim_role = discord.utils.get(
                self.get_guild(member.guild.id).roles,
                name=f"_Claimed: {after.channel.name}_")
            if claim_role is None:
                return
            for user in after.channel.members:
                if user.voice.mute:
                    await member.edit(mute=True)

    async def on_raw_reaction_add(self, payload):
        logging.info("Raw Reaction Add: %(payload)s")
        #Ignore bot reactions
        if payload.member.bot:
            return
        #Check if the reaction was used as a command
        channel = self.get_channel(payload.channel_id)
        name = payload.emoji.name
        if channel.name == 'rules':
            if name in [u"\u2705"]:
                await self.rule_agreement(payload)
        elif channel.name == 'bounties':
            await self.bounty_entry(payload)
        elif channel.name == 'utility-bots':
            control = self.lobby_claims.get(payload.member.name)
            if name in [
                u"\u0030\ufe0f\u20e3", u"\u0031\ufe0f\u20e3",
                u"\u0030\ufe2f\u20e3", u"\u0033\ufe0f\u20e3",
                u"\u0030\ufe4f\u20e3"]:
                await control.claim_lobby(payload)
            elif name == u'\u274c':
                await control.cancel_claim()
                del self.lobby_claims[payload.member.name]
            elif name.encode() in [
                b'\xf0\x9f\x94\x87', b'\xf0\x9f\x94\x88']:
                await control.voice_control(payload)
            elif name.encode() == b'\xf0\x9f\x8f\xb3\xef\xb8\x8f':
                await control.yield_control()
                del self.lobby_claims[payload.member.name]

    async def rule_agreement(self, payload):
        '''
'''
        #Get information from payload
        user = payload.member
        guild = self.get_guild(payload.guild_id)
        #Grant user the 'Member' role
        role = discord.utils.get(guild.roles, name="Member")
        await user.add_roles(role)
        direct_message = await user.create_dm()
        embed = discord.Embed(title="Membership Granted", color=0x00ff00)
        fields = {
            "Member": "'Member' and general server acess have been granted"}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await direct_message.send(embed=embed)

    async def ghost_ping(self, message):
        ''' Flag message if a role was mentioned in a deleted message
'''
        if not message.raw_role_mentions:
            return
        roles = [discord.utils.get(message.guild.roles, id=i).name\
                 for i in message.raw_role_mentions]
        fields = {
            "User": message.author.name, "Channel": message.channel.name,
            "Message": message.content, "Role Mentions": ', '.join(roles)}
        embed = discord.Embed(title="Ghost Ping Detected", color=0xff0000)
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        embed.set_footer(
            text=f"Detected At: {datetime.datetime.now().strftime('%D %T')}")
        channel = discord.utils.get(message.guild.channels, name='dev-build')
        await channel.send(embed=embed)

    async def disconnect_with_claim(self, member, lobby):
        ''' Notifies user if they disconnected from their claimed game lobby
            Requests that they use the :Report: reaction to yield their claim
'''
        #Create and send embed notifying user with claim
        direct_message = await member.create_dm()
        embed = discord.Embed(
            title="Disconnected from Game Lobby with Claim", color=0x00ff00)
        fields = {
            "Details": '\n'.join([
                f"You recently disconnected from {lobby}, which you claimed.",
                "If you are still using this lobby, ignore this message.",
                "Othersiwse, yield your claim using the control panel"]),
            "Yield Claim": "React with :flag_white:"}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await direct_message.send(embed=embed)

    async def bounty_tickets(self, message):
        '''
'''
        guild = message.guild
        role_regex = re.compile(r'_Bounty Tickets: ([0-9]+)_')
        tickets = 0
        #Verify that the user has the 'Member' role
        if 'Member' not in [r.name for r in message.author.roles]:
            return
        #Parse through member roles to get the number of tickets
        for role in message.author.roles:
            if role_regex.search(role.name):
                tickets = int(role_regex.search(role.name).group(1))
                break
        #Award a random number of tickets weighted by an exponential sequence
        plus = random.choices(
            list(range(1, 10)), [(1/2)**n for n in range(1, 10)])[0]
        new_tickets = tickets + plus
        logging.info(new_tickets)
        #Generate roles for the new and old number of tickets
        names = {"Old": f"_Bounty Tickets: {tickets}_",
                 "New": f"_Bounty Tickets: {new_tickets}_"}
        await self.manage_guild_units(
            guild, message.author, role_regex, names)
        #Notify member
        direct_message = await message.author.create_dm()
        embed = discord.Embed(
            title=f"You Received {plus} Bounty Ticket(s)",
            color=0xff0000)
        fields = {
            "Tickets": "\n".join([
                "Use your tickets to enter in the guild point bounties",
                "A random user will be chosen and awarded guild points"]),
            "Total Tickets": new_tickets}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await direct_message.send(embed=embed)

    async def bounty_entry(self, payload):
        '''
'''
        #Get information from payload
        channel = self.get_channel(payload.channel_id)
        guild = self.get_guild(payload.guild_id)
        message = await channel.fetch_message(payload.message_id)
        direct_message = await payload.member.create_dm()
        #Get the current number of tickets a member holds
        entry_regex = re.compile(r'_Bounty Entries: ([0-9])_')
        role_regex, tickets = re.compile(r'_Bounty Tickets: ([0-9]+)_'), 0
        for role in payload.member.roles:
            if entry_regex.search(role.name):
                embed = discord.Embed(
                    title="You have already entered that bounty!",
                    color=0xff0000)
                await direct_message.send(embed=embed)
                await message.remove_reaction(payload.emoji, payload.member)
                return
            if role_regex.search(role.name):
                tickets = int(role_regex.search(role.name).group(1))
        #Verify that the member has enough tickets to enter
        entry_emojis = {
            u"\u0031\ufe0f\u20e3": 1, u"\u0032\ufe0f\u20e3": 2,
            u"\u0033\ufe0f\u20e3": 3, u"\u0034\ufe0f\u20e3": 4,
            u"\u0035\ufe0f\u20e3": 5, u"\u0036\ufe0f\u20e3": 6,
            u"\u0037\ufe0f\u20e3": 7, u"\u0038\ufe0f\u20e3": 8,
            u"\u0039\ufe0f\u20e3": 9}
        entries = entry_emojis[payload.emoji.name]
        if entries > tickets:
            embed = discord.Embed(
                title="You don't have enough tickets!",
                color=0xff0000)
            embed.set_footer(text=f"Tickets: {tickets}")
            await direct_message.send(embed=embed)
            await message.remove_reaction(payload.emoji, payload.member)
            return
        names = {"Old": f"_Bounty Tickets: {tickets}_",
                 "New": f"_Bounty Tickets: {tickets-entries}_"}
        await self.manage_guild_units(
            guild, payload.member, role_regex, names)
        #Generate role for the number of entries
        entry_role = discord.utils.get(
            guild.roles, name=f"_Bounty Entries: {entries}_")
        #Create new role if does not already exist
        if entry_role is None:
            await guild.create_role(name=f"_Bounty Entries: {entries}_")
            entry_role = discord.utils.get(
                guild.roles, name=f"_Bounty Entries: {entries}_")
        #Add new role to member and notify member
        await payload.member.add_roles(entry_role)
        embed = discord.Embed(
            title=f"You have entered the bounty with {entries} entries",
            color=0xff0000)
        embed.set_footer(text=f"Tickets: {tickets-entries}")
        await direct_message.send(embed=embed)

    async def new_bounty(self, message):
        '''
'''
        guild = message.guild
        #Create an embed announcing the new bounty
        start = datetime.datetime.now()
        end = start+datetime.timedelta(minutes=1)
        embed = discord.Embed(title="New Bounty!", color=0xff0000)
        fields = {
            "Win This Bounty": "\n".join([
                "React with the below emojis to enter in this bounty",
                "Up to 9 entries are allowed"]),
            "Message": message.content, "Author": message.author.name,
            "Bounty Start": start.strftime("%D %T"),
            "Bounty End": end.strftime("%D %T")}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        channel = discord.utils.get(guild.channels, name='bounties')
        message = await channel.send(embed=embed)
        #Add reactions for members to enter the bounty with
        reactions = [u"\u0031\ufe0f\u20e3", u"\u0032\ufe0f\u20e3",
                     u"\u0033\ufe0f\u20e3", u"\u0034\ufe0f\u20e3",
                     u"\u0035\ufe0f\u20e3", u"\u0036\ufe0f\u20e3",
                     u"\u0037\ufe0f\u20e3", u"\u0038\ufe0f\u20e3",
                     u"\u0039\ufe0f\u20e3"]
        for emoji in reactions:
            await message.add_reaction(emoji)
        #Update the countdown until the bounty has ended
        while True:
            diff = (end-datetime.datetime.now()).total_seconds()
            if diff <= 0:
                break
            embed.set_footer(
                text=f"Time Remaining: {round(diff/60, 1)}")
            await message.edit(embed=embed)
        embed.set_footer(text="Bounty Ended")
        await message.edit(embed=embed)
        await self.award_bounty(message)

    async def award_bounty(self, message):
        '''
'''
        #Get updated message
        channel = discord.utils.get(message.guild.channels, name='bounties')
        message = await channel.fetch_message(message.id)
        #Get the users and number of entries per user, then clear all entries
        role_regex = re.compile(r"_Bounty Entries: ([0-9])_")
        user_entries = [[], []]
        for member in message.guild.members:
            for role in member.roles:
                if role_regex.search(role.name) is None:
                    continue
                user_entries[0].append(member)
                user_entries[1].append(
                    int(role_regex.search(role.name).group(1)))
        await message.clear_reactions()
        #Randomly select the winner and the number of guild points won
        fib = lambda n: functools.reduce(
            lambda x, n: [x[1], x[0]+x[1]], range(n), [0, 1])[0]
        bounty = {
            "Winner": random.choices(user_entries[0], user_entries[1])[0],
            "Points": random.choices(
                list(range(1, 11)), [1/fib(n) for n in range(1, 11)])[0]}
        #Delete all 'Bounty Entries' roles
        for num in range(1, 10):
            entry_role = discord.utils.get(
                message.guild.roles, name=f"_Bounty Entries: {num}_")
            if entry_role is None:
                continue
            await entry_role.delete()
        #Close bounty message
        embed = discord.Embed(title="Bounty Awarded", color=0xff0000)
        embed.add_field(name="Winner", value=bounty["Winner"].name)
        embed.add_field(name="Guild Points Won", value=bounty["Points"])
        await message.edit(embed=embed)
        #Parse the member's roles for the number of guild points
        role_regex = re.compile(r"_Guild Points: ([0-9]+)_")
        points = 0
        for role in bounty["Winner"].roles:
            if role_regex.search(role.name):
                points = int(role_regex.search(role.name).group(1))
                break
        names = {"Old": f"_Guild Points: {points}_",
                 "New": f"_Guild Points: {points+bounty['Points']}_"}
        await self.manage_guild_units(
            message.guild, bounty["Winner"], role_regex, names)
        await self.check_new_tiers(
            message.guild, bounty["Winner"], points, points+bounty['Point'])

    async def manage_guild_units(self, guild, member, role_regex, names):
        '''
'''
        old_role = discord.utils.get(guild.roles, name=names['Old'])
        new_role = discord.utils.get(guild.roes, name=names['New'])
        #Create new role if does not already exist
        if new_role is None:
            await guild.create_role(name=names['New'])
            new_role = discord.utils.get(guild.roles, name=names['New'])
        #Add new role and remove old role to member
        await member.add_roles(new_role)
        if old_role is not None:
            await member.remove_roles(old_role)
        #Delete old role if not other member holds it
        relevant_roles = []
        for role in guild.roles:
            if role_regex.search(role.name) is None:
                continue
            if any([role in user.roles for user in guild.members]):
                relevant_roles.append(role)
            if old_role and old_role not in relevant_roles:
                await old_role.delete()

    async def check_new_tiers(self, guild, member, lower, upper):
        '''
'''
        for pts in self.tiers:
            if lower < pts <= upper:
                new_tier = self.tiers[pts]
                tier_role = discord.utils.get(guild.roles, name=new_tier)
                direct_message = await member.create_dm()
                embed = discord.Embed(
                    title="New Role Achieved!", color=tier_role.color)
                embed.add_field(name="New Role", value=new_tier)
                embed.add_field(name="Granted to", value=member.name)
                await member.add_roles(tier_role)
                await direct_message.send(embed=embed)

    def execute_commands(self):
        ''' Bot commands which can be used by users with the 'Member' role
'''
        @self.command(name="suggestion", pass_context=True)
        async def suggestion(ctx):
            ''' Suggest a feature for the guild or for the bots
                Return values:
                - :Victory: and :Defeat: reactions for members to vote with
'''
            #Ignore command if outside #bugs-and-suggestions
            if ctx.message.channel.name != 'bugs-and-suggestions':
                return
            #React to the message with emojis to allow members to vote
            reactions = ["<:Victory:779396489792847892>",
                         "<:Defeat:779396491667963904>"]
            for emoji in reactions:
                await ctx.message.add_reaction(emoji)

        @self.command(name="bug", pass_context=True)
        async def bug(ctx):
            ''' Report a bug in the bots
                Return values:
                - :Report: reaction for members to report the bug
'''
            #Ignore command if outside #bugs-and-suggestions
            if ctx.message.channel.name != 'bugs-and-suggestions':
                return
            #React to message with emojis to allow members to report
            reactions = ["<:Report:777211184881467462"]
            for emoji in reactions:
                await ctx.message.add_reaction(emoji)

        @self.command(name="comment", pass_context=True)
        async def comment(ctx):
            ''' Comment on a bug or suggestion of another use
'''
            if ctx.channel.name != 'bugs-and-suggestions':
                return
            #Verify that the user has the 'Moderator' role
            if "Moderator" not in [r.name for r in ctx.author.roles]:
                await ctx.message.delete()
                await ctx.send("You are not authorized to use this command")
                return

        @self.command(name="give_points", pass_context=True)
        async def give_points(ctx, plus):
            ''' Give guild points to a user
'''
            #Restrict point-giving privelage to 'Moderator'
            if "Moderator" not in [r.name for r in ctx.author.roles]:
                await ctx.message.delete()
                await ctx.send("You are not authorized to use this command")
                return
            member = ctx.message.raw_mentions[0]
            role_regex = re.compile(r"_Guild Points: ([0-9]+)_")
            points, plus = 0, int(plus)
            for role in member.roles:
                if role_regex.search(role.name):
                    points = int(role_regex.search(role.name).group(1))
                    break
            new_points = points + plus
            names = {"Old": f"_Guild Points: {points}_",
                     "New": f"_Guild Points: {new_points}_"}
            await self.manage_guild_units(
                ctx.guild, member, role_regex, names)
            await self.check_new_tiers(
                ctx.guild, member, points, new_points)

        @self.command(name="get_points", pass_context=True)
        async def get_points(ctx):
            ''' Get the number of guild points
                Returned embed values:
                - Number of points
                - Current tier name
                - Next tier name
                - Number of points until the next tier
'''
            #Parse through member roles to get points
            points = 0
            role_regex = re.compile(r'_Guild Points: ([0-9]+)_')
            for role in ctx.author.roles:
                if role_regex.search(role.name) is not None:
                    points = int(role_regex.search(role.name).group(1))
                    break
            #Parse through dictionary to get tier information from points
            current_tier, next_tier = 'None', 'Bronze Contributor'
            for pts in list(self.tiers):
                if pts <= points:
                    current_tier = self.tiers[pts]
                elif pts > points:
                    next_tier, until = self.tiers[pts], pts-points
                    break
            if points >= 100:
                next_tier, until = '---', '---'
            #Create and send an embed containing point and tier information
            role = discord.utils.get(ctx.guild.roles, name=current_tier)
            color = 0x000000 if role is None else role.color
            fields = {
                "Points": points, "Current Tier": current_tier,
                "Next Tier": next_tier, "Points until next tier": until}
            embed = discord.Embed(title=ctx.author.name, color=color)
            for field in fields:
                embed.add_field(name=field, value=fields[field])
            await ctx.send(embed=embed)

        @self.command(name="get_tickets", pass_context=True)
        async def get_tickets(ctx):
            #Parse through member roles to get tickets
            tickets = 0
            role_regex = re.compile(r'_Bounty Tickets: ([0-9]+)_')
            for role in ctx.author.roles:
                if role_regex.search(role.name) is not None:
                    tickets = int(role_regex.search(role.name).group(1))
                    break
            fields = {"Total Bounty Tickets": tickets}
            embed = discord.Embed(
                title=f"Bounty Tickets for {ctx.author.name}",
                color=0xff0000)
            for field in fields:
                embed.add_field(name=field, value=fields[field])
            await ctx.send(embed=embed)

        @self.command(name="claim", pass_context=True)
        async def claim(ctx):
            ''' Claim control of a voice channel in Game Lobbies
'''
            #Ignore messages outside #utility-bots
            if ctx.message.channel.name != self.command_channels['claim']:
                return
            #Verify that the member has not already claimed a game lobby
            regex = re.compile(r"_Claimed: (Lobby [0-9])_")
            for role in ctx.author.roles:
                if regex.search(role.name) is None:
                    continue
                await ctx.send("You cannot claim multiple game lobbies")
                return
            control = GameLobbyControl(
                ctx,
                category="Game Lobbies",
                channel=self.command_channels['claim']
                )
            self.lobby_claims.setdefault(ctx.author.name, control)
            await control.send_panel()
            await control.add_panel_reactions()
            await ctx.message.delete()

class SpamDetection:
    def __init__(self, *, filename='spam_parameters.txt'):
        self.file = os.path.join('data', filename)
        with open(self.file) as file:
            self.parameters = json.load(file)
        self.limit = self.parameters['Limit']
        self.interval = self.parameters['Interval']

    async def check(self, message):
        spam = None
        nmessages = 0
        tinitial = message.created_at
        content_initial = message.content
        async for msg in message.channel.history(limit=50):
            interval = (tinitial-msg.created_at).total_seconds()
            if interval <= 0:
                continue
            if interval > self.interval:
                spam = False
                break
            if msg.content in content_initial:
                nmessages += 1
            if nmessages > self.limit:
                spam = True
                break
        if not spam:
            return
        embed = discord.Embed(
            title=f"@{message.author.name} Has Been Marked for Spam", color=0xff0000)
        fields = {
            "Marked as Spam": f"{message.author.mention} messaged too quickly",
            "Message Limit": self.limit, "Messages Sent": nmessages,
            "Time Interval": self.interval}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await message.channel.send(embed=embed)
        
class Censor:
    def __init__(self):
        self.file = os.path.join('data', 'blacklisted_words.txt')
        with open(self.file) as file:
            self.blacklist = file.read().split('\n')
        self.separators = string.punctuation+string.digits+string.whitespace

    async def parse(self, message):
        profane = False
        for word in self.blacklist:
            regex = re.compile(fr'[{self.separators}]*'.join(list(word)))
            if regex.search(message.content) is not None:
                profane = True
                break
        if not profane:
            return
        embed = discord.Embed(
            title="Blacklisted Word Detected in Message :no_entry_sign:",
            color=0xff0000)
        embed.add_field(
            name="You aren't allowed to say that!",
            value=message.author.mention)
        notification = await message.channel.send(embed=embed)
        await message.delete()
        await asyncio.sleep(10)
        await notification.delete()
        
class VoiceChannelControl:
    def __init__(self, context, *, category, channel):
        self.context = context
        self.regex = re.compile(r"_Claimed: (Lobby [0-9])_")
        self.guild = self.context.guild
        self.category = discord.utils.get(
            self.guild.categories, name=category)
        self.lobbies = self.category.channels
        self.member = self.context.author
        self.channel = discord.utils.get(
            self.guild.channels, name=channel)

    async def send_panel(self):
        embed = discord.Embed(
            title="Game Lobby Claim", color=0x00ff00)
        fields = {
            "Claim": "Use the reactions below to claim a lobby",
            "Cancel": "React with :x: to cancel"
            }
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        embed.set_footer(text=self.member.name)
        self.panel = await self.context.channel.send(embed=embed)

    async def add_panel_reactions(self):
        for num, channel in enumerate(self.lobbies):
            emoji = str(num).encode()+b'\xef\xb8\x8f\xe2\x83\xa3'
            role = f"_Claimed: {channel}_"
            if discord.utils.get(self.guild.roles, name=role) is None:
                await self.panel.add_reaction(emoji.decode())
        await self.panel.add_reaction(u'\u274c')

    async def cancel_claim(self):
        await self.panel.clear_reactions()
        embed = discord.Embed(
            title="Voice Channel Claim Canceled", color=0x00ff00)
        await self.panel.edit(embed=embed)
        await asyncio.sleep(10)
        await self.panel.delete()

    async def claim_lobby(self, payload):
        #Grant member game lobby claim based on the emoji used
        num = payload.emoji.name[0]
        self.lobby = discord.utils.get(
            self.lobbies, name=f"Lobby {num}")
        await self.guild.create_role(name=f"_Claimed: {self.lobby.name}_")
        role = discord.utils.get(
            self.guild.roles, name=f"_Claimed: {self.lobby.name}_")
        await self.member.add_roles(role)
        #Edit panel for game lobby member voice control
        await self.panel.clear_reactions()
        embed = discord.Embed(
            title="Voice Channel Control Panel", color=0x00ff00)
        fields = {
            "Claimed": f"You have successfully claimed Lobby {num}",
            "Voice Control": '\n'.join([
                f"You can control the voices of the members of Lobby {num}",
                "Mute with :mute:",
                "Unmute with :speaker:"
                ]),
            "Yield": '\n'.join([
                "Yield your claim on the game lobby when you are finished",
                "Yield with :flag_white:"
                ])}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await self.panel.edit(embed=embed)
        #Add reactions to allow member to control member voices
        reactions = [
            b'\xf0\x9f\x94\x87',
            b'\xf0\x9f\x94\x88',
            b'\xf0\x9f\x8f\xb3\xef\xb8\x8f'
            ]
        for reaction in reactions:
            await self.panel.add_reaction(reaction.decode())

    async def voice_control(self, payload):
        #Manage the voices of the members based on the emoji used
        controls = {
            b'\xf0\x9f\x94\x87': True,
            b'\xf0\x9f\x94\x88': False
            }
        if not self.lobby.members:
            await self.channel.send(
                f"There are no members in {self.lobby.name}")
        else:
            for member in self.lobby.members:
                await member.edit(mute=controls[payload.emoji.name.encode()])
        await self.panel.remove_reaction(payload.emoji, self.member)

    async def yield_control(self):
        #Delete the claim role that was granted to the member
        role = discord.utils.get(
            self.guild.roles, name=f"_Claimed: {self.lobby.name}_")
        await role.delete()
        #Close control panel
        embed = discord.Embed(
            title="Voice Channel Control Panel Closed", color=0x00ff00)
        fields = {
            "Yielded": f"You have successfully yielded {self.lobby.name}"
            }
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await self.panel.edit(embed=embed)
        await self.panel.clear_reactions()
        await asyncio.sleep(10)
        await self.panel.delete()

def main():
    ''' Create and run UtilityBot instances
'''
    tokens = {
        "Utils": os.environ.get("UTILS", None)}
    if None in tokens.values():
        with open(os.path.join('data', 'tokens.csv')) as file:
            tokens = dict(list(csv.reader(file, delimiter='\t')))
    with open(os.path.join('data', 'command_channels.txt')) as file:
        command_channels = json.load(file)
    loop = asyncio.get_event_loop()
    for bot in tokens:
        discord_bot = UtilityBot(
            command_prefix="*",
            name=bot,
            command_channels=command_channels)
        loop.create_task(discord_bot.start(tokens[bot]))
    loop.run_forever()

if __name__ == '__main__':
    main()
