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

import discord
from discord.ext import commands

logging.basicConfig(
    level=logging.INFO,
    format=' %(asctime)s - %(levelname)s - %(message)s')

class Utils(commands.Bot):
    ''' 
'''
    def __init__(self, *, prefix, name):
        '''
'''
        self.name = name
        self.prefix = prefix
        #Manage intents to allow bot to view all members
        intents = discord.Intents.default()
        intents.members = True
        commands.Bot.__init__(
            self, command_prefix=self.prefix, intents=intents,
            self_bot=False)
        #Load regular expression and tier data
        with open(os.path.join('data', 'tiers.csv')) as file:
            self.tiers = dict(list(csv.reader(file)))
            self.tiers = {int(k):v for k, v in self.tiers.items()}
        with open(os.path.join('data', 'allowed_pings.txt')) as file:
            self.allowed_pings = json.load(file)
        allowed_moderations = {
            "command_restrictions": False, "spam_detection": True,
            "censor": True}
        #Call feature classes
        self.add_cog(VoiceChannelControl(
            self, category="Game Lobbies"))
        self.add_cog(Moderation(
            self, cmdrestrict="command_restrictions.txt",
            spamdetect="spam_parameters.txt", censor="blacklisted_words.txt"))
        self.add_cog(GhostPing(
            self, ping="allowed_pings.txt"))
        #Execute commands
        self.execute_commands()

    async def on_ready(self):
        ''' 
'''
        logging.info("Ready: %s", self.name)

    async def on_member_join(self, member):
        '''
'''
        logging.info("Member Join: %s", member)
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
        logging.info("Message: %s", message)
        #Ignore all bot messages
        if message.author.bot:
            return
        cog = self.get_cog("Moderation")
        if not await cog.check_all(message):
            await self.process_commands(message)

    async def on_raw_reaction_add(self, payload):
        logging.info("Raw Reaction Add: %s", payload)
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

class GuildPoints(commands.Cog):
    def __init__(self, bot, *, tiers,
                 names=("Guild Points", "Bounty Tickets")):
        self.bot = bot
        path = os.path.join('data', tiers)
        with open(path) as file:
            self.tiers = json.load(file)
        self.point_regex = fr'_{names[0]}: ([0-9]+)_'
        self.ticket_regex = fr'_{names[1]}: ([0-9]+)_'
        self.names = names

    
    @self.command(name="points", pass_context=True, aliases=["p"])
    async def points(self, ctx):
        #Pasre through members roles to get current points
        points = 0
        for role in ctx.author.roles:
            if self.point_regex.search(role.name) is not None:
                points = int(self.point_regex.search(role.name).group(1))
                break
        #Get tier information from points
        tiers = ["None", "Bronze"]
        for pts in self.tiers:
            if pts <= points:
                tiers[0] = self.tiers[pts]
            elif pts > points:
                tiers[1] = self.tiers[pts]
                diff = pts-points
                break
        if points >= 100:
            tiers[1] = '---'
            diff = '---'
        #Send point and tier information
        role = discord.utils.get(ctx.guild.roles, name=tiers[1])
        color = 0x000000 if role is None else role.color
        fields = {
            "Points": points, "Current Tier": tiers[0], "Next Tier": tiers[1],
            "Points until next tier": diff}
        embed = discord.Embed(
            title=f"{ctx.author.name}'s {self.names[0]}", color=color)
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await ctx.send(embed=embed)

class GhostPing(commands.Cog):
    def __init__(self, bot, *, ping):
        self.bot = bot
        path = os.path.join('data', ping)
        with open(path) as file:
            self.pings = json.load(file)
        self.fields = {}

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        logging.info(message)
        await self.check_all(message)

    async def check_all(self, message):
        pinged = []
        self.fields["User"] = message.author.name
        self.fields["Channel"] = message.channel.name
        self.fields["Message"] = message.content
        if not self.pings["everyone"]:
            pinged.append(self.everyone_pings(message))
        if not self.pings["roles"]:
            pinged.append(self.role_pings(message))
        if not self.pings["members"]:
            pinged.append(self.member_pings(message))
        if not any(pinged):
            self.fields = {}
            return False
        embed = discord.Embed(title="Ghost Ping Detected", color=0xff0000)
        for field in self.fields:
            embed.add_field(name=field, value=self.fields[field])
        embed.set_footer(
            text=f"Detected At: {datetime.datetime.now().strftime('%D %T')}")
        await message.channel.send(embed=embed)
        return True

    def everyone_pings(self, message):
        if not message.mention_everyone:
            return False
        self.fields["Mentions @everyone"] = "Yes"
        return True

    def role_pings(self, message):
        if not message.raw_role_mentions:
            return False
        roles = [discord.utils.get(message.guild.roles, id=i).name\
                 for i in message.raw_role_mentions]
        self.fields["Role Mentions"] = ', '.join(roles)
        return True

    def member_pings(self, message):
        if not message.raw_mentions:
            return False
        members = [discord.utils.get(message.guild.members, id=i).name\
                   for i in message.raw_mentions]
        self.fields["Member Mentions"] = ', '.join(members)
        return Ture

class Moderation(commands.Cog):
    ''' Parse messages with various features to moderate a text channel
'''
    def __init__(self, bot, *,
                 cmdrestrict=None, spamdetect=None, censor=None):
        self.bot = bot
        args = {
            "Command Restrictions": cmdrestrict,
            "Spam Detection": spamdetect,
            "Censor": censor}
        self.features = {
            'Command Restrictions': None,
            'Spam Detection': None,
            'Censor': None}
        for arg in args:
            if args[arg] is None:
                continue
            path = os.path.join('data', args[arg])
            with open(path) as file:
                self.features[arg] = json.load(file)

    async def check_all(self, message):
        ''' Parse message with all enabled features
'''
        #Delete messages which are flagged with any enabled feature
        flags = []
        if self.features["Command Restrictions"]:
            flags.append(await self.command_restrictions(message))
        if self.features["Spam Detection"]:
            flags.append(await self.spam_detection(message))
        if self.features["Censor"]:
            flags.append(await self.censor(message))
        if any(flags):
            await message.delete()
            return True
        return False
        
    async def command_restrictions(self, message):
        ''' Flag command used by members inproperly
            - Commands used outside of allowed channel(s)
            - Commands used without necessary roles
'''
        #Get parameters
        if not self.bot.prefix in message.content:
            return
        command = message.content.split()[0].strip(self.bot.prefix)
        parameters = self.features["Command Restrictions"][command]
        restricted = False
        #Verify command used in correct channel
        channels = parameters['channels']
        if channels and message.channel.id not in channels:
            restricted = True
        #Verify member using command has necessary roles
        roles = parameters['roles']
        if roles and not any(r.id in roles for r in message.author.roles):
            restricted = True
        if not restricted:
            return False
        channel_names = [
            discord.utils.get(message.guild.channels, id=c).name\
            for c in channels]
        role_names = [
            discord.utils.get(message.guild.roles, id=r).name\
            for r in roles]
        embed = discord.Embed(
            title=f"Command Used Improperly", color=0x00ff00)
        fields = {
            "Command Name": f"`{command}`",
            "Allowed Channels": '-\n'.join(channel_names),
            "Required Roles": '-\n'.join(role_names)}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await message.channel.send(embed=embed)
        return True

    async def spam_detection(self, message):
        ''' Flag member if they send too many messages too quickly
'''
        #Get parameters and initial conditions
        parameters = self.features["Spam Detection"]
        spam = False
        tracked_messages = []
        start_time = message.created_at
        #Check time interval and message quantity
        async for msg in message.channel.history(limit=50):
            interval = (start_time-msg.created_at).total_seconds()
            #Ignore messages sent after initial message
            if interval <= 0:
                continue
            #Stop message count once interval exceeds specification
            if interval > parameters['Interval']:
                break
            #Flag as spam if tracked messages exceeds specification
            if len(tracked_messages) >= parameters['Limit']:
                spam = True
            tracked_messages.append(msg)
        if not spam:
            return False
        await message.channel.delete_messages(tracked_messages)
        #Flag member for spam
        embed = discord.Embed(
            title=f"Member Marked for Spam", color=0x00ff00)
        fields = {
            "Marked as Spam": f"{message.author.mention} messaged too quickly",
            "Message Limit": limit, "Maximum Time Interval": interval,
            "Discovered Messages": len(tracked_messages)}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await message.channel.send(embed=embed)
        return True

    async def censor(self, message):
        ''' Flag message if it contains any of the blacklisted words
            Words will be flagged if non-alphabetic characters separate word
            Words will not be flagged if word stands alone in another word
'''
        #Get parameters
        parameters = self.features["Censor"]
        blacklist = parameters["Blacklist"]
        separators = parameters["Separators"]
        excluded = parameters["Excluded"]
        #Check if any blacklisted word in message
        profane = False
        for word in blacklist:
            #Word separates by non-alphabetic characters
            regex_match_true = re.compile(
                f"[{separators}]*".join(list(word)), re.IGNORECASE)
            #Word stands alone in another word
            regex_match_none = re.compile(
                fr"([{excluded}]+{word})|({word}[{excluded}]+)",re.IGNORECASE)
            if regex_match_true.search(message.content)\
               and regex_match_none.search(message.content) is None:
                profane = True
                break
        if not profane:
            return False
        #Flag message for profanity
        embed = discord.Embed(
            title="Blacklisted Word Detected in Message :no_entry_sign:",
            color=0xff0000)
        embed.add_field(
            name="You aren't allowed to say that!",
            value=message.author.mention)
        await message.channel.send(embed=embed)
        return True
        
class VoiceChannelControl(commands.Cog):
    ''' Allow guild member to be able to claim control of a voice channel
        Members can control member voices in a voice channel they claimed
'''

    def __init__(self, bot, *, category):
        self.bot = bot
        self.category = category
        self.emojis = [
            u'0\ufe0f\u20e3', u'1\ufe0f\u20e3', u'2\ufe0f\u20e3',
            u'3\ufe0f\u20e3', u'4\ufe0f\u20e3', u'5\ufe0f\u20e3',
            u'6\ufe0f\u20e3', u'7\ufe0f\u20e3', u'8\ufe0f\u20e3',
            u'9\ufe0f\u20e3']
        self.claims = {}
        self.claim_requests = {}
        self.voice_channels = {}

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        ''' Listen for member using emojis to control other members' voices
'''
        logging.info("Raw Reaction Add: %s", payload)
        if payload.member.bot:
            return
        if payload.emoji.name in self.emojis:
            await self.claim_control_panel(payload)
        elif payload.emoji.name == u'\u274c':
            await self.cancel_claim(payload)
        elif payload.emoji.name in ["\U0001f507", "\U0001f508"]:
            await self.voice_control(payload)
        elif payload.emoji.name == "\U0001f3f3":
            await self.yield_control(payload)

    @commands.command(name="claim", pass_context=True)
    async def claim(self, ctx):
        ''' Invoke a claim request panel
            Member cannot have an active claim request
            Member cannot have a claim on another voice channel
'''
        if ctx.author.id in self.claim_requests:
            await ctx.send("You already have an active claim request")
            return
        if ctx.author.id in self.claims:
            await ctx.send("You already have a voice channel claim")
            return
        await self.claim_request_panel(ctx)
        await ctx.message.delete()
        
    async def claim_request_panel(self, ctx):
        ''' Send an embed with reactions for member to claim a voice channel
'''
        #Get voice channels in category
        self.voice_channels = discord.utils.get(
            ctx.guild.categories, name=self.category).channels
        #Send claim request panel
        embed = discord.Embed(
            title="Voice Channel Claim", color=0x00ff00)
        fields = {
            "Channel Options": '\n'.join([
                f"{self.emojis[self.voice_channels.index(c)]} - {c}"\
                for c in self.voice_channels]),
            "Claim": "Use the reactions below to claim a lobby",
            "Cancel": "React with :x: to cancel"}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        panel = await ctx.channel.send(embed=embed)
        self.claim_requests.setdefault(ctx.message.author.id, panel.id)
        #Add reactions to claim request panel
        for channel in self.voice_channels:
            await panel.add_reaction(
                self.emojis[self.voice_channels.index(channel)])
        await panel.add_reaction(u'\u274c')

    async def cancel_claim(self, payload):
        ''' Cancel the request to claim a voice channel
'''
        #Get channel and message information from payload
        msg_id = self.claim_requests.get(payload.member.id)
        channel = discord.utils.get(
            payload.member.guild.channels, id=payload.channel_id)
        if msg_id is None:
            await channel.send(
                "You do not have an active voice channel claim")
            return
        panel = await channel.fetch_message(msg_id)
        #Deprecate voice channel claim panel
        await panel.clear_reactions()
        embed = discord.Embed(
            title="Voice Channel Claim Canceled", color=0x00ff00)
        await panel.edit(embed=embed)
        del self.claim_requests[payload.member.id]
        await asyncio.sleep(10)
        await panel.delete()

    async def claim_control_panel(self, payload):
        ''' Send an embed with reactions for member to manage members' voices
'''
        #Get voice channel and message from payload
        voice_channel = discord.utils.get(
            self.voice_channels,
            name=self.voice_channels[
                self.emojis.index(payload.emoji.name)
                ].name)
        channel = self.bot.get_channel(payload.channel_id)
        panel = await channel.fetch_message(
            self.claim_requests.get(payload.member.id))
        self.claims.setdefault(payload.member.id, voice_channel.id)
        #Edit panel for voice channel control
        embed = discord.Embed(
            title="Voice Channel Control Panel", color=0x00ff00)
        fields = {
            "Claimed": f"You have successfully claimed {voice_channel.name}",
            "Voice Channel Control": '\n'.join([
                "Mute all - :mute:", "Unmute all - :speaker:",
                "Yield - :flag_white:"])}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await panel.edit(embed=embed)
        #Add voice control reactions
        await panel.clear_reactions()
        reactions = ["\U0001f507", "\U0001f508", "\U0001f3f3"]
        for reaction in reactions:
            await panel.add_reaction(reaction)

    async def voice_control(self, payload):
        ''' Manage members' voices according to the reaction used
'''
        channel = self.bot.get_channel(payload.channel_id)
        panel = await channel.fetch_message(
            self.claim_requests.get(payload.member.id))
        #Manage the voices of the members based on the emoji used
        controls = {"\U0001f507": True, "\U0001f508": False}
        voice_channel = self.bot.get_channel(
            self.claims.get(payload.member.id))
        if not voice_channel.members:
            message = await channel.send(
                f"There are no members in {voice_channel.name}")
            await asyncio.sleep(5)
            await message.delete()
        else:
            for member in voice_channel.members:
                await member.edit(mute=controls[payload.emoji.name])
        await panel.remove_reaction(payload.emoji, payload.member)

    async def yield_control(self, payload):
        ''' Yield control of a claimed voice channel
'''
        channel = self.bot.get_channel(payload.channel_id)
        panel = await channel.fetch_message(
            self.claim_requests.get(payload.member.id))
        #Close control panel
        voice_channel = self.bot.get_channel(
            self.claims.get(payload.member.id))
        embed = discord.Embed(
            title="Voice Channel Control Panel Closed", color=0x00ff00)
        fields = {
            "Yielded": f"You have successfully yielded {voice_channel.name}"
            }
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await panel.edit(embed=embed)
        await panel.clear_reactions()
        del self.claim_requests[payload.member.id]
        del self.claims[payload.member.id]
        await asyncio.sleep(10)
        await panel.delete()

    async def disconnect_with_claim(self, member):
        ''' Send message to member if they disconnect while holding a claim
'''
        if member.id not in self.claims:
            return
        voice_channel = self.claims.get(member.id)
        #Notify member that they still have a claim and request that they yield it
        direct_message = await member.create_dm()
        embed = discord.Embed(
            title="Disconnected from Voice Channel with Claim", color=0x00ff00)
        fields = {
            "Details": '\n'.join([
                f"Disconnected from claimed voice channel, {voice_channel.name}",
                "Ignore this message if you are still using this voice channel.",
                "Otherwise, please yield the claim using the control panel"]),
            "Yield Claim": "React with :flag_white:"}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await direct_message.send(embed=embed)

    async def manage_new_voice_channel_join(self, new_member, channel):
        #Parse guild roles to check if the voice channel is claimed
        role = discord.utils.get(
            channel.guild.roles, name=f"_Claimed: {channel.name}_")
        if role is None:
            return
        #Edit new member voice
        for member in channel.members:
            if member.id in self.claim_requests:
                await new_member.edit(mute=member.voice.mute)

def main():
    token = os.environ.get("token", None)
    if token is None:
        with open(os.path.join('data', 'token.txt')) as file:
            token = file.read()
    assert token is not None
    loop = asyncio.get_event_loop()
    discord_bot = Utils(
        prefix="*", name="Util5")
    loop.create_task(discord_bot.start(token))
    loop.run_forever()

if __name__ == '__main__':
    main()
