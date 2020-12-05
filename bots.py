#! python3
# bots.py

import asyncio
import csv
import json
import logging
import os
import re

import discord
from discord.ext import commands

logging.basicConfig(level=logging.INFO, format=' %(asctime)s - %(levelname)s - %(message)s')

class UtilityBot(commands.Bot):
    def __init__(self, *, command_prefix, name):
        '''
'''
        intents = discord.Intents.default()
        intents.members = True
        commands.Bot.__init__(
            self, command_prefix=command_prefix, intents=intents,
            self_bot=False)
        self.name = name
        with open(os.path.join('data', 'regex.csv')) as file:
            self.regexes = dict(list(csv.reader(file, delimiter='\t')))
        with open(os.path.join('data', 'tiers.csv')) as file:
            self.tiers = dict(list(csv.reader(file, delimiter='\t')))
            self.tiers = {v:int(k) for k, v in self.tiers.items()}
        self.execute_commands()

    async def on_ready(self):
        ''' Notify developer that a UtilBot-class bot is active
'''
        print(f"Bot is ready: {self.name}")

    async def on_message(self, message):
        ''' Messages from certain channels are run through a regex
            Messages that do not comply to the regex are deleted
'''
        logging.info((message.author.name, message.channel, message.content))
        #Ignore all bot messages
        if message.author.bot:
            return
        if 'Direct Message' in str(message.channel):
            embed = discord.Embed(
                title="Direct Messaging is not supported", color=0xff000)
            ctx.send(embed=embed)
            return
        for channel in self.regexes:
            if channel in message.channel.name:
                break
        regex = re.compile(self.regexes[channel])
        results = regex.search(message.content)
        if results is not None or 'help' in message.content:
            await self.process_commands(message)
        else:
            await message.delete()
            return

    async def on_voice_state_update(self, member, before, after):
        regex, claimed = re.compile(r"_Claimed: (Lobby [0-9])_"), False
        for role in member.roles:
            if regex.search(role.name):
                voice_channel = regex.search(role.name).group(1)
                claimed = True
                break
        if not claimed or not (before.channel and after.channel is None):
            return
        direct_message = await member.create_dm()
        embed = discord.Embed(
            title="Surrender Game Lobby Claim", color=0x00ff00)
        fields = {
            "Details": '\n'.join([
                f"You recently disconnected from {voice_channel}.",
                "If you are still using this lobby, ignore this message.",
                "If not, please surrender your claim on this lobby."]),
            "Surrender Claim": "Use command 'surrender' in #utility-bots"}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await direct_message.send(embed=embed)

    def execute_commands(self):
        ''' Bot commands which can be used by users with the 'Member' role
'''
        @self.command(name="introduction", pass_context=True)
        async def introduction(ctx, name):
            ''' Returned embed values:
                - Member nickname
                - Member name
                Other return values:
                - User is granted Member role
                Restricted to: #introductions
'''
            #Ignore commands outside #introductions
            if ctx.message.channel.name != 'introduction':
                return
            #Parse 'name' argument for a valid name
            regex = re.compile(r'^[A-Z][A-Za-z]+ [A-Z][A-Za-z]+$')
            results = regex.search(name)
            #Create a direct message to notify member of message status
            direct_message = await ctx.message.author.create_dm()
            if results is None:
                #Create an embed containing status information
                embed = discord.Embed(
                    title="Invalid Introduction", color=0x00ff00)
                fields = {
                    "Error": "Name not detected in entry",
                    "Note": "Include quotes around you name",
                    "Acceptable Format": "^[A-Z][A-Za-z]+ [A-Z][A-Za-z]+$",
                    "Example": "Among Us",
                    "Not": "AmongUs, among us, amongus"}
                #Delete invalid command
                await ctx.message.delete()
            else:
                name = results.group()
                #Add 'Member' role to member
                member = ctx.message.author
                role = discord.utils.get(member.guild.roles, name="Member")
                await member.add_roles(role)
                #Create and send new member information embed to #members channel
                embed = discord.Embed(
                    title="Member Information Card", color=0xffff00)
                information = {"Nickname": member.name, "Name": name}
                for info in information:
                    embed.add_field(name=info, value=information[info])
                channel = discord.utils.get(
                    ctx.guild.channels, name="members")
                await channel.send(embed=embed)
                #Create an embed containing status information
                embed = discord.Embed(
                    title="Confirm Introduction", color=0x00ff00)
                fields = {
                    "Name set to": name,
                    "Role": "You have now been granted the 'Member' role",
                    "Status": "You can now view the rest of the server",
                    "Typo?": "Run this command to override previous entries"}
            #Direct message the status embed
            for field in fields:
                embed.add_field(name=field, value=fields[field])
            await direct_message.send(embed=embed)

        @self.command(name="member", pass_context=True)
        async def member(ctx, search_method, search):
            ''' Search for a member of the guild by their name or nickname
                Returned embed values:
                - Member nickname
                - Member name
'''
            #Assert that the search is either by Name or Nickname
            search_method = search_method.title()
            if search_method not in ('Name', 'Nickname'):
                await ctx.send(f"{search_method} is not a valid search method")
                return
            #Parse 'member' argument for a valid name/nickname
            regex = re.compile(r'^[A-Z][A-Za-z]+ [A-Z][A-Za-z]+$|.*{1,32}')
            results = regex.search(member)
            channel = discord.utils.get(
                ctx.guild.channels, name="introductions")
            #Parse through the last 200 messages from newest to oldest
            messages = await channel.history(limit=200).flatten()
            found = False
            for message in messages[::-1]:
                #Use a RegEx to find the name in the introduction
                name_re = re.compile(r'"?([A-Z][A-Za-z]+\s[A-Z][A-Za-z]+)"?')
                nickname = message.author.name
                name = name_re.search(message.content).group(1)
                if search in message.content:
                    if search_method == 'Name':
                        name = search
                    elif search_method == 'Nickname':
                        nickname = search
                    found = True
                    break
            if not found:
                await ctx.send(
                    f"Could not find {member} [Searched by {search_method}]")
                return
            #Create and send member information embed
            embed = discord.Embed(
                title="Member Information Card", color=0xffff00)
            embed.add_field(name="Nickname", value=nickname)
            embed.add_field(name="Name", value=name)
            await ctx.send(embed=embed)

        @self.command(name="suggestion", pass_context=True)
        async def suggestion(ctx):
            ''' Suggest a feature for the guild or for the bots
                Return values:
                - :Victory: and :Defeat: reactions for members to vote with
'''
            #Ignore command if outside #suggestions-and-bugs
            if ctx.message.channel.name != 'suggestions-and-bugs':
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
            #Ignore command if outside #suggestions-and-bugs
            if ctx.message.channel.name != 'suggestions-and-bugs':
                return
            #React to message with emojis to allow members to report
            reactions = ["<:Report:777211184881467462"]
            for emoji in reactions:
                await ctx.message.add_reaction(emoji)

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
            for role in ctx.author.roles:
                if '_Contributions' in role.name:
                    points = int(role.name.strip('_').split()[-1])
                    break
            #Parse through dictionary to get tier information from points
            current_tier, next_tier = 'None', 'Bronze Contributor'
            for t in list(self.tiers):
                if t <= points:
                    current_tier = self.tiers[t]
                elif t > points:
                    next_tier, until = self.tiers[t], t-points
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

        @self.command(name="give_points", pass_context=True)
        async def give_points(ctx, plus, nickname):
            ''' Give guild points to a user
'''
            #Restrict point-giving privelage to 'Moderator'
            if "Moderator" not in [r.name for r in ctx.author.roles]:
                await ctx.message.delete()
                await ctx.send("You are not authorized to use this command")
                return
            #Find the member in all guild members by nickname
            found = False
            for member in ctx.guild.members:
                if nickname.lower() == member.name.lower():
                    found = True
                    break
            if not found:
                await ctx.message.delete()
                await ctx.send(f"Could not find {nickname}")
                return
            #Use a RegEx to find the number of points from the role
            role_regex = re.compile('_Contributions: ([0-9]+)_')
            #Parse through member roles to get points
            points = 0
            for role in member.roles:
                if role_regex.search(role.name):
                    points = role_regex.search(role.name).group(1)
            new_points, points = int(points)+int(plus), int(points)
            #Generate roles for the new and old number of points
            old = f"_Contributions: {points}_"
            new = f"_Contributions: {new_points}_"
            old_role = discord.utils.get(ctx.guild.roles, name=old)
            new_role = discord.utils.get(ctx.guild.roles, name=new)
            #Create new role if does not already exist
            if new_role is None:
                await ctx.guild.create_role(name=new)
                new_role = discord.utils.get(ctx.guild.roles, name=new)
            #Add new role and remove old role to member, if possible
            await member.add_roles(new_role)
            if old_role is not None:
                await member.remove_roles(old_role)
            #Delete old role if it exists and no one else owns it
            all_points = [r.name for r in ctx.guild.roles\
                          if role_regex.search(r.name) is not None]
            if old_role and old_role not in all_points:
                await old_role.delete()
            #Check if the member has reached a new tier
            for i in range(int(points)+1, new_points+1):
                if i in self.tiers:
                    #Get tier which the member just reached
                    new_tier = self.tiers[i]
                    tier_role = discord.utils.get(
                        ctx.guild.roles, name=new_tier)
                    #Create and send an embed congratulating them
                    embed = discord.Embed(
                        title="New Role Achieved!", color=tier_role.color)
                    embed.add_field(name="New Role", value=new_tier)
                    embed.add_field(name="Granted to", value=member.name)
                    await member.add_roles(tier_role)
                    await ctx.send(embed=embed)

        @self.command(name="claim", pass_context=True)
        async def claim(ctx, lobby):
            ''' Claim control of a voice channel in Game Lobbies
'''
            #Ignore messages outside #utility-bots
            if ctx.message.channel.name != 'utility-bots':
                return
            #Get channel and assert that it exists in the guild
            channel = discord.utils.get(
                ctx.guild.channels, name=lobby)
            if channel is None or channel.category.name != "Game Lobbies":
                await ctx.send("You cannot claim that voice channel")
                return
            #Use a RegEx to check if user has already claimed a game lobby
            regex = re.compile(r"_Claimed: (Lobby [0-9])_")
            for role in ctx.author.roles:
                if regex.search(role.name) is None:
                    continue
                if regex.search(role.name).group(1) == lobby:
                    await ctx.send(f"You have already claimed {voice_channel}")
                    return
                await ctx.send("You cannot claim multiple game lobbies")
                return
            #Generate a role identifying the game lobby which was claimed
            claim_rname = f"_Claimed: {channel}_"
            if claim_rname in [r.name for r in ctx.guild.roles]:
                await ctx.send("This channel has already been claimed")
                return
            #Create the role and award it to the user
            await ctx.guild.create_role(name=claim_rname)
            claim_role = discord.utils.get(
                ctx.guild.roles, name=claim_rname)
            await ctx.message.author.add_roles(claim_role)
            #Notify user that the game lobby has been claimed
            direct_message = await ctx.message.author.create_dm()
            embed = discord.Embed(title="Game Lobby claimed", color=0x00ff00)
            fields = {
                "Claimed": f"You have successfully claimed {lobby}",
                "Mute/Unmute": '\n'.join([
                    f"You can now control the voices of others in {lobby}",
                    "Use 'manage_mute' or 'mm' in #utility-bots"]),
                "Role": '\n'.join([
                    f"You now have the '\{claim_rname}' role",
                    f"This identifies your claim on {lobby}"]),
                "Surrender": '\n'.join([
                    "Please surrender your claim when you are finished",
                    "Use 'surrender' in #utility-bots"])}
            for field in fields:
                embed.add_field(name=field, value=fields[field])
            await direct_message.send(embed=embed)

        @self.command(name="surrender", pass_context=True)
        async def surrender(ctx):
            ''' Surrender control of a voice channel in Game Lobbies
'''
            #Ignore messages outside #utility-bots
            if ctx.message.channel.name != 'utility-bots':
                return
            #Assert that the user has claimed a lobby
            regex, claimed = re.compile(r"_Claimed: (Lobby [0-9])_"), False
            for role in ctx.message.author.roles:
                if regex.search(role.name):
                    lobby = regex.search(role.name).group(1)
                    claimed = True
                    break
            if not claimed:
                await ctx.send("You have not claimed any of the game lobbies")
                return
            #Get the role of the claimed game lobby and delete the role
            claim_rname = regex.search(role.name).group()
            claim_role = discord.utils.get(ctx.guild.roles, name=claim_rname)
            await claim_role.delete()
            #Notify user that the game lobby has been surrendered
            direct_message = await ctx.message.author.create_dm()
            embed = discord.Embed(
                title="Game Lobby surrendered", color=0x00ff00)
            fields = {
                "Surrendered": f"You have successfully surrendered {lobby}"}
            for field in fields:
                embed.add_field(name=field, value=fields[field])
            await direct_message.send(embed=embed)

        @self.command(name="claimed", pass_context=True)
        async def claimed(ctx):
            ''' Check which voice channels in Game Lobbies have been claimed
'''
            #Ignore messages outside #utility-bots
            if ctx.message.channel.name != 'utility-bots':
                return
            #Parse through all the channels in Game Lobbies
            category = discord.utils.get(
                ctx.guild.categories, name="Game Lobbies")
            claimed = []
            for channel in category.channels:
                #Check if the claimed game lobby role exists
                claim_rname = f"_Claimed: {channel.name}_"
                if claim_rname in [r.name for r in ctx.guild.roles]:
                    claimed.append(channel.name)
            #Report any claimed game lobbies
            if not claimed:
                await ctx.send("No game lobbies are currently claimed")
            else:
                await ctx.send(f"Claimed game lobbies: {claimed}")

        @self.command(name="manage_mute", pass_context=True, aliases=['mm'])
        async def manage_mute(ctx):
            ''' Mute all the users in a voice channel in Game Lobbies
'''
            #Ignore messages outside #utility-bots
            if ctx.message.channel.name != 'utility-bots':
                return
            #Use a RegEx to assert that the user has claimed a lobby
            regex, claimed = re.compile(r"_Claimed: (Lobby [0-9])_"), False
            for role in ctx.message.author.roles:
                if regex.search(role.name):
                    claimed = True
                    break
            if not claimed:
                await ctx.send("You have not claimed any of the game lobbies")
                return
            #Get the claimed voice channel and mute/unmute all users in it
            lobby = discord.utils.get(
                ctx.guild.channels, name=regex.search(role.name).group(1))
            if not lobby.members:
                await ctx.send(f"There are no members to mute/unmute")
                return
            for member in lobby.members:
                await member.edit(mute=not member.voice.mute)
            status = "muted" if member.voice.mute else "unmuted"
            await ctx.send(f"The members in {lobby} have been {status}")

class Main:
    def __init__(self):
        ''' Create and run a UtilityBot-class bot
'''
        self.bots = {
            'Utils': os.environ.get('UTILS', None)}
        self.loop = asyncio.get_event_loop()
        for bot in self.bots:
            token = self.bots[bot]
            discord_bot = UtilityBot(command_prefix="*", name=bot)
            self.loop.create_task(discord_bot.start(token))
        self.loop.run_forever()

if __name__ == '__main__':
    Main()
