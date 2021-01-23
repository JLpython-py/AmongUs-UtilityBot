#! python3
# bot.py

'''

'''

import asyncio
import datetime
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
        self.name = name
        #Manage intents to allow bot to view all members
        intents = discord.Intents.default()
        intents.members = True
        intents.guilds = True
        commands.Bot.__init__(
            self, command_prefix=prefix, intents=intents,
            self_bot=False)
        #Call feature classes
        self.add_cog(GhostPing(self))
        self.add_cog(GuildPoints(self))
        self.add_cog(Moderation(self))
        self.add_cog(ReactionRoles(self))
        self.add_cog(VoiceChannelControl(self))
        self.add_cog(WelcomeMessage(self))

    async def on_ready(self):
        '''
'''
        logging.info("Ready: %s", self.name)

    async def on_member_join(self, member):
        '''
'''
        logging.info("Member Join: %s", member)

    async def on_message(self, message):
        '''
'''
        logging.info("Message: %s", message)
        if message.author.bot:
            return
        if await self.check_message(message):
            await message.delete()
            return
        await self.process_commands(message)

    async def check_message(self, message):
        ''' Run message through spam and censor moderation functions
            Determine if message should be flagged
'''
        moderation = self.get_cog("Moderation")
        flags = []
        if moderation is not None:
            if moderation.data["actives"]["spam"]:
                flags.append(await moderation.spam(message))
            if moderation.data["actives"]["commands"]:
                flags.append(await moderation.censor(message))
            return any(flags)
        return False
        
    async def check_commands(self, ctx):
        ''' Run command through command moderation function
            Determine if message should be flagged
'''
        moderation = self.get_cog("Moderation")
        if moderation is not None:
            if moderation.data["actives"]["commands"]:
                return await moderation.commands(ctx)
        return False

class GhostPing(commands.Cog):
    ''' Detect if a memeber ghost pings a role, member, or everyone
'''
    def __init__(self, bot):
        self.bot = bot
        with open(os.path.join('data', 'ghost_ping.txt')) as file:
            self.data = json.load(file)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        logging.info("Message Delete: %s", message)
        await self.parse(message)

    async def parse(self, message):
        ''' Check all disallowed categories if the message mentions it
'''
        pinged = []
        fields = {
            "User": message.author.name, "Channel": message.channel.name,
            "Message": message.content}
        if self.data["everyone"]:
            if message.mention_everyone:
                fields["Message @everyone"] = "Yes"
            pinged.append(bool(message.mention_everyone))
        if self.data["roles"]:
            if message.raw_role_mentions:
                fields["Role Mentions"] = ', '.join([
                    discord.utils.get(message.guild.roles, id=i).name\
                    for i in message.raw_role_mentions])
            pinged.append(bool(message.raw_role_mentions))
        if self.data["members"]:
            if message.raw_mentions:
                fields["Member Mentions"] = ', '.join(
                    [discord.utils.get(message.guild.members, id=i).name\
                     for i in message.raw_mentions])
            pinged.append(bool(message.raw_mentions))
        if not any(pinged):
            return False
        embed = discord.Embed(
            title="Ghost Ping Detected :no_entry_sign::ghost:",
            color=0xff0000)
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        embed.set_footer(
            text=f"Detected At: {datetime.datetime.now().strftime('%D %T')}")
        await message.channel.send(embed=embed)
        return True

class GuildPoints(commands.Cog):
    ''' Manage Guild Points and Bounty Tickets which can be awarded to members
'''
    def __init__(self, bot, *, channel="general"):
        self.bot = bot
        with open(os.path.join('data', 'guild_points.txt')) as file:
            self.data = json.load(file)
        self.data['tiers'] = {
            int(k):int(v) for k, v in self.data['tiers'].items()}
        self.point_regex = re.compile(r'_Guild Points: ([0-9]+)_')
        self.ticket_regex = re.compile(r'_Bounty Tickets: ([0-9]+)_')
        self.channel = channel
        self.bounty_reactions = [
            u"\u0031\ufe0f\u20e3", u"\u0032\ufe0f\u20e3",
            u"\u0033\ufe0f\u20e3", u"\u0034\ufe0f\u20e3",
            u"\u0035\ufe0f\u20e3", u"\u0036\ufe0f\u20e3",
            u"\u0037\ufe0f\u20e3", u"\u0038\ufe0f\u20e3",
            u"\u0039\ufe0f\u20e3"]
        self.bounty_entries = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        members = [m for m in message.guild.members if not m.bot]
        if random.randint(1, 25) == random.randint(1, 25):
            await self.award_tickets(message)
            if random.choice(message.guild.members).id == message.author.id:
                await self.create_bounty(message)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot:
            return
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        embed = message.embeds[0]
        if embed.footer.text != "GuildPoints":
            return
        if payload.emoji.name == u"\u274c":
            await self.withdraw_entry(payload)
        elif payload.emoji.name in self.bounty_reactions:
            await self.enter_bounty(payload)

    @commands.command(name="points", pass_context=True, aliases=["p"])
    async def points(self, ctx):
        ''' Get number of Guild Points a member has
'''
        if await self.bot.check_commands(ctx):
            return
        #Parse through members roles to get current points
        points = 0
        for role in ctx.message.author.roles:
            if self.point_regex.search(role.name) is not None:
                points = int(self.point_regex.search(role.name).group(1))
                break
        #Get tier information from points
        tiers = ["---", "---"]
        for pts in self.data["tiers"]:
            if pts <= points:
                tiers[0] = discord.utils.get(
                    ctx.guild.roles, id=self.data["tiers"][pts]).name
            elif pts > points:
                tiers[1] = discord.utils.get(
                    ctx.guild.roles, id=self.data["tiers"][pts]).name
                diff = pts-points
                break
        if points >= 100:
            tiers[1] = '---'
            diff = '---'
        #Send point and tier information
        role = discord.utils.get(ctx.guild.roles, name=tiers[0])
        color = 0x00ff00 if role is None else role.color
        fields = {
            "Points": points, "Current Tier": tiers[0],
            "Next Tier": tiers[1], "Points until next tier": diff}
        embed = discord.Embed(
            title=f"{ctx.author.name}'s Guild points",
            color=color)
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        embed.set_footer(
            text="Gain new roles by accumulating Guild points")
        await ctx.send(embed=embed)

    @commands.command(name="tickets", pass_context=True, aliases=["t"])
    async def tickets(self, ctx):
        ''' Get number of Bounty Tickets a member has
'''
        if await self.bot.check_commands(ctx):
            return
        #Parse through member roles to get current tickets
        tickets = 0
        for role in ctx.author.roles:
            if self.ticket_regex.search(role.name) is not None:
                tickets = int(self.ticket_regex.search(role.name).group(1))
                break
        #Send ticket information
        fields = {
            "Tickets": tickets}
        embed = discord.Embed(
            title=f"{ctx.author.name}'s Bounty Tickets",
            color=0x00ff00)
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await ctx.send(embed=embed)

    @commands.command(name="give", pass_context=True, aliases=["g"])
    async def give(self, ctx, unit, member, quantity):
        ''' Give Guild Points or Bounty Tickets to a member
'''
        if await self.bot.check_commands(ctx):
            return
        unit = unit.lower()[0]
        if unit == 'p':
            regex = self.point_regex
        elif unit == 't':
            regex = self.ticket_regex
        else:
            await ctx.send("You can only give points or tickets")
            await ctx.message.delete()
            return
        if not ctx.message.raw_mentions:
            await ctx.send("You have to mention someone")
            await ctx.message.delete()
            return
        member = discord.utils.get(
            ctx.guild.members, id=ctx.message.raw_mentions[0])
        units, quantity = 0, int(float(quantity))
        for role in member.roles:
            if regex.search(role.name):
                units = int(regex.search(role.name).group(1))
                break
        new_units = units + quantity
        currency = "Guild Points" if unit == 'p' else "Bounty Tickets"
        names = [f"_{currency}: {units}_",
                 f"_{currency}: {new_units}_"]
        await self.guild_currency(member, names)
        if unit == 'p':
            await self.parse_tiers(member, [units, new_units])

    async def award_tickets(self, message):
        ''' Award a random number of tickets to a member
'''
        #Parse through member roles to get the number of tickets
        tickets = 0
        for role in message.author.roles:
            if self.ticket_regex.search(role.name):
                tickets = int(self.ticket_regex.search(role.name).group(1))
                break
        #Award a random number of tickets
        plus = random.choices(
            list(range(1, 10)),
            [(1/2)**n for n in range(1, 10)])[0]
        new_tickets = tickets + plus
        names = [f"_Bounty Tickets: {tickets}_",
                 f"_Bounty Tickets: {new_tickets}_"]
        await self.guild_currency(message.author, names)
        #Notify member
        direct_message = await message.author.create_dm()
        embed = discord.Embed(
            title=f"Awarded {plus} Bounty Tickets", color=0x00ff00)
        embed.add_field(name="Total Tickets", value=new_tickets)
        await direct_message.send(embed=embed)

    async def enter_bounty(self, payload):
        ''' Enter a Guild Point Bounty with a number of tickets
'''
        #Get information from payload
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        direct_message = await payload.member.create_dm()
        #Verify member has not already entered bounty
        if payload.member.id in self.bounty_entries:
            embed = discord.Embed(
                title="You have already entered that bounty!", color=0x00ff00)
            embed.add_field(
                name="Withdraw Entry",
                value="React with :x: to get tickets refunded")
            await direct_message.send(embed=embed)
            await message.remove_reaction(payload.emoji, payload.member)
            return
        #Get the current number of tickets member has
        tickets = 0
        for role in payload.member.roles:
            if self.ticket_regex.search(role.name):
                tickets = int(self.ticket_regex.search(role.name).group(1))
                break
        #Verify member has enough tickets to enter
        entries = self.bounty_reactions.index(payload.emoji.name)+1
        if entries > tickets:
            embed = discord.Embed(
                title="You don't have enough tickets!",
                color=0xff0000)
            embed.add_field(name="Tickets", value=tickets)
            await direct_message.send(embed=embed)
            await message.remove_reaction(payload.emoji, payload.member)
            return
        new_tickets = tickets - entries
        names = [f"_Bounty Tickets: {tickets}_",
                 f"_Bounty Tickets: {new_tickets}_"]
        await self.guild_currency(payload.member, names)
        #Enter member in bounty and notify member
        self.bounty_entries.setdefault(payload.member.id, entries)
        embed = discord.Embed(
            title="Bounty Entry Successful", color=0x00ff00)
        embed.add_field(name="Entries", value=entries)
        embed.add_field(
            name="Widthdraw Entry",
            value="React with :x: to get tickets refunded")
        embed.add_field(name="Tickets", value=new_tickets)
        await direct_message.send(embed=embed)

    async def withdraw_entry(self, payload):
        ''' Withdraw all entries in a Guild Points Bounty and refund tickets
'''
        #Get information from payload
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        direct_message = await payload.member.create_dm()
        #Get tickets used by member
        entries = self.bounty_entries.get(payload.member.id)
        if entries is None:
            return
        await message.remove_reaction(
            self.bounty_reactions[entries-1], payload.member)
        await message.remove_reaction(
            payload.emoji, payload.member)
        del self.bounty_entries[payload.member.id]
        #Get number of tickets member has
        tickets = 0
        for role in payload.member.roles:
            if self.ticket_regex.search(role.name):
                tickets = int(self.ticket_regex.search(role.name).group(1))
                break
        #Refund tickets to member
        new_tickets = tickets + entries
        names = [f"_Bounty Tickets: {tickets}_",
                 f"_Bounty Tickets: {new_tickets}_"]
        await self.guild_currency(payload.member, names)
        #Notify member
        embed = discord.Embed(
            title="Bounty Withdrawl Successful", color=0x00ff00)
        embed.add_field(name="Tickets", value=new_tickets)
        await direct_message.send(embed=embed)

    async def create_bounty(self, message):
        ''' Create a Guild Point Bounty for members to enter in
'''
        start = datetime.datetime.now()
        end = start+datetime.timedelta(minutes=1)
        embed = discord.Embed(title="New Bounty!", color=0x00ff00)
        fields = {
            "Enter this Bounty": "React to enter in this bounty",
            "Message": message.content, "Author": message.author.name,
            "Bounty Start": start.strftime("%D %T"),
            "Bounty End": end.strftime("%D %T")}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        embed.set_footer(text="GuildPoints")
        channel = discord.utils.get(message.guild.channels, name=self.channel)
        bounty = await channel.send(embed=embed)
        #Add reactions for members to enter
        for emoji in self.bounty_reactions:
            await bounty.add_reaction(emoji)
        await bounty.add_reaction(u"\u274c")
        #Wait until the bounty has ended
        time_left = (end-datetime.datetime.now()).total_seconds()
        while time_left > 0:
            time_left = (end-datetime.datetime.now()).total_seconds()
            await asyncio.sleep(1)
        await self.award_bounty(bounty)

    async def award_bounty(self, message):
        ''' Award a random number of Guild Points to a random member
'''
        channel = discord.utils.get(
            message.guild.channels, id=self.data["bounty"])
        message = await channel.fetch_message(message.id)
        #Randomly select a winner and the number of points won
        await message.clear_reactions()
        embed = discord.Embed(title="Bounty Awarded", color=0x00ff00)
        if sum(list(self.bounties.values())) < 15:
            embed.add_field(
                name="No Winner", value="Not Enough Bounty Entries")
            await message.edit(embed=embed)
            return
        bounty = {
            "Winner": discord.utils.get(
                message.guild.members,
                id=random.choices(
                    list(self.bounty_entries),
                    list(self.bounty_entries.values()))[0]),
            "Points": random.choices(
                list(range(1, 11)),
                [(1/2)**n for n in range(1, 11)])[0]}
        embed.add_field(name="Winner", value=bounty["Winner"].name)
        embed.add_field(name="Points", value=bounty["Points"])
        await message.edit(embed=embed)
        #Add points to member
        points = 0
        for role in bounty["Winner"].roles:
            if self.point_regex.search(role.name):
                points = int(self.point_regex.search(role.name).group(1))
                break
        new_points = points + bounty["Points"]
        names = [f"_Guild Points: {points}_",
                 f"_Guild Points: {new_points}_"]
        await self.guild_currency(bounty["Winner"], names)
        await self.parse_tiers(bounty["Winner"], [points, new_points])

    async def guild_currency(self, member, names):
        ''' Manage the number of Guild Points or Bounty Tickets a member has
'''
        #Get new and old roles
        old = discord.utils.get(member.guild.roles, name=names[0])
        new = discord.utils.get(member.guild.roles, name=names[1])
        #Create new role if does not already exist
        if new is None:
            await member.guild.create_role(name=names[1])
            new = discord.utils.get(member.guild.roles, name=names[1])
        #Add new role and remove old role from member roles
        await member.add_roles(new)
        if old is not None:
            await member.remove_roles(old)
        #Delete old role if no other member has it
        delete = True
        for mem in member.guild.members:
            if old in mem.roles:
                delete = False
                break
        if old and delete:
            await old.delete()

    async def parse_tiers(self, member, ptrange):
        ''' Check if a member achieved a new Guild Point tier
'''
        for pts in self.data["tiers"]:
            if ptrange[0] < pts <= ptrange[1]:
                new_tier = self.data["tiers"][pts]
                role = discord.utils.get(member.guild.roles, id=new_tier)
                divider = discord.utils.get(
                    member.guild.roles, name='__________ Tiers __________')
                if divider is None:
                    await member.guild.create_role(
                        name='__________ Tiers __________')
                    divider = discord.utils.get(
                    member.guild.roles, name='__________ Tiers __________')
                await member.add_roles(divider)
                color = 0x00ff00 if role is None else role.color
                direct_message = await member.create_dm()
                embed = discord.Embed(
                    title="New Tier Reached!", color=color)
                embed.add_field(name="New Role", value=role.name)
                await member.add_roles(role)
                await direct_message.send(embed=embed)

class Moderation(commands.Cog):
    ''' Parse messages with various features to moderate a text channel
'''
    def __init__(self, bot):
        self.bot = bot
        with open(os.path.join('data', 'moderation.txt')) as file:
            self.data = json.load(file)

    async def commands(self, ctx):
        ''' Flag command used by members inproperly
            - Commands used outside of allowed channel(s)
            - Commands used without necessary roles
'''
        #Get information
        parameters = self.data["commands"].get(ctx.command.name)
        if parameters is None:
            return False
        restricted = False
        #Verify command used in correct channel
        channels = parameters['channels']
        if channels and ctx.channel.id not in channels:
            restricted = True
        #Verify member using command has necessary roles
        roles = parameters['roles']
        if roles and not any(r.id in roles for r in ctx.author.roles):
            restricted = True
        if not restricted:
            return False
        channel_names = [
            discord.utils.get(ctx.guild.channels, id=c).name\
            for c in channels]
        role_names = [
            discord.utils.get(ctx.guild.roles, id=r).name\
            for r in roles]
        embed = discord.Embed(
            title="Command Used Improperly", color=0x00ff00)
        fields = {
            "Command Name": f"`{ctx.command.name}`",
            "Allowed Channels": ', '.join(channel_names),
            "Required Roles": ', '.join(role_names)}
        for field in fields:
            if not fields[field]:
                break
            embed.add_field(name=field, value=fields[field])
        await ctx.send(embed=embed)
        return True

    async def spam(self, message):
        ''' Flag member if they send too many messages too quickly
'''
        #Get parameters and initial conditions
        max_num, max_int = self.data["spam"]
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
            if interval > max_int:
                break
            #Flag as spam if tracked messages exceeds specification
            if len(tracked_messages) >= max_num:
                spam = True
            tracked_messages.append(msg)
        if not spam:
            return False
        await message.channel.delete_messages(tracked_messages)
        #Flag member for spam
        embed = discord.Embed(
            title="Member Marked for Spam", color=0x00ff00)
        fields = {
            "Marked as Spam": f"{message.author.mention} messaged too quickly",
            "Message Limit": max_num,
            "Maximum Time Interval": max_int,
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
        blacklist = self.data["blacklist"]
        included, excluded = self.data["characters"]
        #Check if any blacklisted word in message
        profane = False
        for word in blacklist:
            #Word separates by non-alphabetic characters
            regex_match_true = re.compile(
                fr"[{included}]*".join(list(word)), re.IGNORECASE)
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

class ReactionRoles(commands.Cog):
    ''' Grant member role when they react to message
'''
    def __init__(self, bot):
        self.bot = bot
        with open(os.path.join('data', 'reaction_roles.txt')) as file:
            self.messages = {int(k):v for k, v in json.load(file).items()}

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot:
            return
        if payload.message_id not in self.messages:
            return
        await self.manage_rroles(payload, mode='+')

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id not in self.messages:
            return
        await self.manage_rroles(payload, mode='-')

    async def manage_rroles(self, payload, *, mode):
        ''' Add/Remove role(s) if the member added/removed a reaction
'''
        #Get informatino from paylaod
        guild = self.bot.get_guild(payload.guild_id)
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        member = guild.get_member(payload.user_id)
        data = self.messages.get(payload.message_id)
        #Manage all roles according to the emoji used
        for roleid in data[payload.emoji.name]:
            #Get role from emoji
            role = discord.utils.get(
                guild.roles, id=int(roleid))
            if mode == '+':
                await member.add_roles(role)
                #Remove all other reactions used by member
                for rxn in message.reactions:
                    if rxn.emoji.name == payload.emoji.name:
                        continue
                    await message.remove_reaction(
                        rxn, member)
            elif mode == '-':
                await member.remove_roles(role)

class VoiceChannelControl(commands.Cog):
    ''' Allow guild member to be able to claim control of a voice channel
        Members can control member voices in a voice channel they claimed
'''

    def __init__(self, bot):
        self.bot = bot
        with open(os.path.join('data', 'voice_channel_control.txt')) as file:
            self.data = json.load(file)
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
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        embed = message.embeds[0]
        if embed.footer.text != "VoiceChannelControl":
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
        if await self.bot.check_commands(ctx):
            return
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
            ctx.guild.categories, id=self.data['category']).channels
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
        embed.set_footer(text="VoiceChannelControl")
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
        embed.set_footer(text="VoiceChannelControl")
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

class WelcomeMessage(commands.Cog):
    ''' Send a private and/or public welcome message when member joins
'''
    def __init__(self, bot):
        self.bot = bot
        with open(os.path.join('data', 'welcome_message.txt')) as file:
            self.data = json.load(file)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return
        await self.private_message(member)
        await self.public_message(member)

    async def private_message(self, member):
        ''' Send private message embed in direct message channel
'''
        if not self.data["private"]["active"]:
            return
        direct_message = await member.create_dm()
        embed = discord.Embed(
            title=self.data["private"]["title"],
            color=0xff0000)
        fields = self.data["private"]["fields"]
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await direct_message.send(embed=embed)

    async def public_message(self, member):
        ''' Send public message embed in determined channel
'''
        if not self.data["public"]["active"]:
            return
        channel = discord.utils.get(
            member.guild.channels, id=self.data["public"]["channel"])
        embed = discord.Embed(
            title=self.data["public"]["title"],
            color=0xff0000)
        fields = self.data["public"]["fields"]
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await channel.send(embed=embed)
        
def main():
    token = os.environ.get("token", None)
    if token is None:
        with open('token.txt') as file:
            token = file.read()
    assert token is not None
    loop = asyncio.get_event_loop()
    discord_bot = Utils(
        prefix="*", name="Util5")
    loop.create_task(discord_bot.start(token))
    loop.run_forever()

if __name__ == '__main__':
    main()
