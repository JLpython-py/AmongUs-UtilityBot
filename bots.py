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

    async def on_raw_reaction_add(self, payload):
        reaction, user = payload.emoji, payload.member
        channel = self.get_channel(payload.channel_id)
        guild = self.get_guild(payload.guild_id)
        message = await channel.fetch_message(payload.message_id)
        if user.bot:
            return
        if channel.name == 'dev-build':
            if reaction.name in ["Shhh", "Emergency_Meeting", "Report"]:
                await self.voice_control(payload)
            elif reaction.name in ["Kill"]:
                await self.yield_claim(payload)
            elif reaction.name in [
                u"\u0030\ufe0f\u20e3", u"\u0031\ufe0f\u20e3",
                u"\u0030\ufe2f\u20e3", u"\u0033\ufe0f\u20e3",
                u"\u0030\ufe4f\u20e3"]:
                await self.claim_lobby(payload)
            else:
                await message.remove_reaction(reaction, user)            

    async def voice_control(self, payload):
        reaction, user = payload.emoji, payload.member
        channel = self.get_channel(payload.channel_id)
        guild = self.get_guild(payload.guild_id)
        message = await channel.fetch_message(payload.message_id)
        voice = {"Shhh": True, "Emergency_Meeting": False, "Report": False}
        role, regex = None, re.compile(r"_Claimed: (Lobby [0-9])_")
        for r in user.roles:
            if regex.search(r.name):
                role = regex.search(r.name).group()
                lobby = regex.search(r.name).group(1)
                break
        if role is None:
            await channel.send("You have not claimed any of the game lobbies")
            await message.remove_reaction(reaction, user)
            return
        embed = message.embeds[0].to_dict()
        if lobby != embed['footer']['text']:
            claim = embed['footer']['text']
            await channel.send(f"You do not have a claim on {claim}")
            await message.remove_reaction(reaction, user)
            return
        lobby = discord.utils.get(guild.channels, name=lobby)
        if not lobby.members:
            await channel.send(f"There are no members in {lobby}")
        else:
            for member in lobby.members:
                await member.edit(mute=voice[reaction.name])
        await message.remove_reaction(reaction, user)

    async def yield_claim(self, payload):
        reaction, user = payload.emoji, payload.member
        channel = self.get_channel(payload.channel_id)
        guild = self.get_guild(payload.guild_id)
        message = await channel.fetch_message(payload.message_id)
        role, regex = None, re.compile(r"_Claimed: (Lobby [0-9])_")
        for r in user.roles:
            if regex.search(r.name):
                role = regex.search(r.name).group()
                lobby = regex.search(r.name).group(1)
                break
        if role is None:
            await channel.send("You have not claimed any of the game lobbies")
            await message.remove_reaction(reaction, user)
            return
        embed = message.embeds[0].to_dict()
        if lobby != embed['footer']['text']:
            claim = embed['footer']['text']
            await channel.send(f"You do not have a claim on {claim}")
            await message.remove_reaction(reaction, user)
            return
        claim_role = discord.utils.get(guild.roles, name=role)
        await claim_role.delete()
        embed = message.embeds[0]
        embed.title = "Game Lobby Yielded"
        fields = {"Yielded": f"You have successfully yielded {lobby}"}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await message.edit(embed=embed)
        for r in message.reactions:
            await message.clear_reaction(r)

    async def claim_lobby(self, payload):
        reaction, user = payload.emoji, payload.member
        channel = self.get_channel(payload.channel_id)
        guild = self.get_guild(payload.guild_id)
        message = await channel.fetch_message(payload.message_id)
        embed = message.embeds[0].to_dict()
        if user.name != embed['footer']['text']:
            await channel.send("You did not request this claim panel")
            await message.remove_reaction(reaction, user)
            return
        lobbies = {
            u"\u0030\ufe0f\u20e3": "Lobby 0",
            u"\u0031\ufe0f\u20e3": "Lobby 1",
            u"\u0030\ufe2f\u20e3": "Lobby 2",
            u"\u0033\ufe0f\u20e3": "Lobby 3",
            u"\u0030\ufe4f\u20e3": "Lobby 4"}
        lobby = lobbies[reaction.name]
        claim_rname = f"_Claimed: {lobby}_"
        await guild.create_role(name=claim_rname)
        claim_role = discord.utils.get(guild.roles, name=claim_rname)
        await user.add_roles(claim_role)
        embed = discord.Embed(title="Game Lobby Claimed", color=0x00ff00)
        fields = {
            "Claimed": f"You have successfully claimed {lobby}",
            "Voice Control": '\n'.join([
                f"You now have control of the voices in {lobby}",
                "Mute: <:Shhh:777210413929463808>",
                "Unmute: <:Emergency_Meeting:777211033655574549>"
                "\t or <:Report:777211184881467462>"]),
            "Yield": '\n'.join([
                "Please yield your claim when you are finished",
                "Yield: <:Kill:777210412269043773>"])}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        embed.set_footer(text=lobby)
        message = await channel.send(embed=embed)
        reactions = [
            "<:Shhh:777210413929463808>",
            "<:Emergency_Meeting:777211033655574549>",
            "<:Report:777211184881467462>",
            "<:Kill:777210412269043773>"]
        for reaction in reactions:
            await message.add_reaction(reaction)

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
            if ctx.message.channel.name != 'introductions':
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
        async def claim(ctx):
            ''' Claim control of a voice channel in Game Lobbies
'''
            #Ignore messages outside #utility-bots
            #if ctx.message.channel.name != 'utility-bots':
            #    return
            #Use a RegEx to check if user has already claimed a game lobby
            regex = re.compile(r"_Claimed: (Lobby [0-9])_")
            for role in ctx.author.roles:
                if regex.search(role.name) is None:
                    continue
                await ctx.send("You cannot claim multiple game lobbies")
                return
            embed = discord.Embed(
                title="Game Lobby Claim Panel", color=0x00ff00)
            fields = {"Claim": "Use the reactions below to claim a lobby"}
            for field in fields:
                embed.add_field(name=field, value=fields[field])
            embed.set_footer(text=ctx.author.name)
            message = await ctx.send(embed=embed)
            reactions = {
                "Lobby 0": u"\u0030\ufe0f\u20e3",
                "Lobby 1": u"\u0031\ufe0f\u20e3",
                "Lobby 2": u"\u0032\ufe0f\u20e3",
                "Lobby 3": u"\u0033\ufe0f\u20e3",
                "Lobby 4": u"\u0034\ufe0f\u20e3"}
            for lobby in reactions:
                role = f"_Claimed: {lobby}_"
                if discord.utils.get(ctx.guild.roles, name=role) is None:
                    await message.add_reaction(reactions[lobby])

class Main:
    def __init__(self):
        ''' Create and run a UtilityBot-class bot
'''
        self.bots = {
            'Utils': os.environ.get('UTILS', None)}
        if None in self.bots.values():
            with open(os.path.join('data', 'tokens.csv')) as file:
                self.bots = dict(list(csv.reader(file, delimiter='\t')))
        self.loop = asyncio.get_event_loop()
        for bot in self.bots:
            token = self.bots[bot]
            discord_bot = UtilityBot(command_prefix="*", name=bot)
            self.loop.create_task(discord_bot.start(token))
        self.loop.run_forever()

if __name__ == '__main__':
    Main()
