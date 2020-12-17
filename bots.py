#! python3
# bots.py

import asyncio
import csv
import datetime
import logging
import os
import random
import re

import discord
from discord.ext import commands

logging.basicConfig(level=logging.INFO, format=' %(asctime)s - %(levelname)s - %(message)s')

class UtilityBot(commands.Bot):
    def __init__(self, *, command_prefix, name):
        self.name = name
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
        self.execute_commands()

    async def on_ready(self):
        logging.info(f"Ready: {self.name}")

    async def on_member_join(self, member):
        logging.info(f"Member Join: {member}")
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
        logging.info(f"Message: {message}")
        #Ignore all bot messages
        if message.author.bot:
            return
        if message.content.startswith('*')\
           and "Direct Message" in str(message.channel):
            await ctx.send("Direct Message channels do not support commands")
            return
        #Check for Ghost Pings
        await self.ghost_ping(message)
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
        if message.channel.category in ['General', 'Among Us', None]:
            await self.bounty_tickets(message)
            await self.award_bounty(message)

    async def on_voice_state_update(self, member, before, after):
        logging.info(f"Voice State Update: {(member, before, after)}")
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
                if not member.voice.mute:
                    await member.edit(mute=True)

    async def on_raw_reaction_add(self, payload):
        logging.info(f"Raw Reaction Add: {payload}")
        #Ignore bot reactions
        if payload.member.bot:
            return
        #Check reaction properties for control panel usage
        channel = self.get_channel(payload.channel_id)
        if channel.name == 'rules':
            name = payload.emoji.name
            if name in [u"\u2705"]:
                await self.rule_agreement(payload)
        elif channel.name == 'utility-bots':
            name = payload.emoji.name
            if name in [
                u"\u0030\ufe0f\u20e3", u"\u0031\ufe0f\u20e3",
                u"\u0030\ufe2f\u20e3", u"\u0033\ufe0f\u20e3",
                u"\u0030\ufe4f\u20e3"]:
                await self.claim_lobby(payload)
            elif name in ["Shhh", "Emergency_Meeting", "Report"]:
                await self.voice_control(payload)
            elif name in ["Kill"]:
                await self.yield_claim(payload)
            else:
                message = await channel.fetch_message(payload.message_id)
                await message.remove_reaction(payload.emoji, payload.member)

    async def rule_agreement(self, payload):
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
            "Yield Claim": "React with <:Kill:777210412269043773>"}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        await direct_message.send(embed=embed)

    async def claim_lobby(self, payload):
        ''' Allows user to claim voice control over a game lobby
            Sends a voice control panel for the user to mute/unmute members
'''
        #Get information from payload
        reaction, user = payload.emoji, payload.member
        channel = self.get_channel(payload.channel_id)
        guild = self.get_guild(payload.guild_id)
        message = await channel.fetch_message(payload.message_id)
        #Verify that the user requested the claim panel
        claim_panel = message.embeds[0]
        claim_fields = claim_panel.to_dict()
        if user.name != claim_fields['footer']['text']:
            await channel.send("You did not request this claim panel")
            await message.remove_reaction(reaction, user)
            return
        #Indicate to all members that the claim panel is inactive
        claim_panel.title = f"{claim_panel.title} [CLOSED]"
        await message.edit(embed=claim_panel)
        for r in message.reactions:
            await message.clear_reaction(r)
        #Give game lobby claim to user based on the emoji used
        lobbies = {
            u"\u0030\ufe0f\u20e3": 0, u"\u0031\ufe0f\u20e3": 1,
            u"\u0030\ufe0f\u20e3": 2, u"\u0033\ufe0f\u20e3": 3,
            u"\u0030\ufe0f\u20e3": 4}
        lobby = f"Lobby {lobbies[reaction.name]}"
        claim_rname = f"_Claimed: {lobby}_"
        await guild.create_role(name=claim_rname)
        claim_role = discord.utils.get(guild.roles, name=claim_rname)
        await user.add_roles(claim_role)
        #Create and send game lobby control panel
        control_panel = discord.Embed(
            title="Game Lobby Control Panel", color=0x00ff00)
        fields = {
            "Claimed": f"You have successfully claimed {lobby}",
            "Voice Control": '\n'.join([
                f"You now have control of the voices in {lobby}",
                '\t'.join(["Mute:", "<:Shhh:777210413929463808>"]),
                '\t'.join(["Unmute:", "\t<:Report:777211184881467462>",
                           "\t<:Emergency_Meeting:777211033655574549>"])]),
            "Yield": '\n'.join([
                "Please yield your claim when you are finished",
                '\t'.join(["Yield:", "<:Kill:777210412269043773>"])])}
        for field in fields:
            control_panel.add_field(name=field, value=fields[field])
        control_panel.set_footer(text=lobby)
        message = await channel.send(embed=control_panel)
        reactions = [
            "<:Shhh:777210413929463808>", "<:Report:777211184881467462>",
            "<:Emergency_Meeting:777211033655574549>",
            "<:Kill:777210412269043773>"]
        for reaction in reactions:
            await message.add_reaction(reaction)

    async def ghost_ping(self, message):
        ''' Detects when a member @-mentions a role to prevent ghost pings
'''
        if '@' not in message.content:
            return
        #Verify that the author is not moderator or administrator
        mod_roles = (
            discord.utils.get(message.guild.roles, name="Moderator"),
            discord.utils.get(message.guild.roles, name="Administrator"))
        mod = any([r in message.author.roles for r in mod_roles])
        #Verify that the message @-mentions a role
        role = None
        for r in message.guild.roles:
            logging.info(r.id)
            if f"<@&{r.id}>" in message.content:
                role = discord.utils.get(message.guild.roles, name=r.name)
                logging.info(role)
                break
        logging.info(role)
        if role is None:
            return
        #Create and send ping notification embed to #dev-build
        embed = discord.Embed(
            title="Potential Ghost Ping Detected", color=0xff0000)
        fields = {"User": message.author.name, "Message": message.content}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        detection = datetime.datetime.now().strftime("%D %T")
        embed.set_footer(text=f"Detected At: {detection}")
        channel = discord.utils.get(message.guild.channels, name="dev-build")
        await channel.send(embed=embed)
        
    async def voice_control(self, payload):
        ''' Manages member voices in a game lobby if the user has a claim
'''
        #Get information from payload
        reaction, user = payload.emoji, payload.member
        channel = self.get_channel(payload.channel_id)
        guild = self.get_guild(payload.guild_id)
        message = await channel.fetch_message(payload.message_id)
        #Verify that the user has a claim on the game lobby
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
        #Verify that the user is using the correct control panel
        claim_panel = message.embeds[0]
        claim_fields = claim_panel.to_dict()
        if lobby != claim_fields['footer']['text']:
            claim = claim_fields['footer']['text']
            await channel.send(f"You do not have a claim on {claim}")
            await message.remove_reaction(reaction, user)
            return
        #Manage the voices based on the emoji used
        lobby = discord.utils.get(guild.channels, name=lobby)
        voice = {"Shhh": True, "Emergency_Meeting": False, "Report": False}
        if not lobby.members:
            await channel.send(f"There are no members in {lobby}")
        else:
            for member in lobby.members:
                await member.edit(mute=voice[reaction.name])
        await message.remove_reaction(reaction, user)

    async def yield_claim(self, payload):
        '''
'''
        #Get information from payload
        reaction, user = payload.emoji, payload.member
        channel = self.get_channel(payload.channel_id)
        guild = self.get_guild(payload.guild_id)
        message = await channel.fetch_message(payload.message_id)
        #Verify that the user has a claim on the game lobby
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
        #Verify that the user is using the correct control pannel
        control_panel = message.embeds[0]
        control_fields = control_panel.to_dict()
        if lobby != control_fields['footer']['text']:
            claim = control_fields['footer']['text']
            await channel.send(f"You do not have a claim on {claim}")
            await message.remove_reaction(reaction, user)
            return
        #Delete the role indicating the user's claim on the game lobby
        claim_role = discord.utils.get(guild.roles, name=role)
        await claim_role.delete()
        #Indicate to all members that the control panel is inactive
        control_panel.title = f"{control_panel.title} [CLOSED]"
        control_panel.clear_fields()
        fields = {"Yielded": f"You have successfully yielded {lobby}"}
        for field in fields:
            control_panel.add_field(name=field, value=fields[field])
        await message.edit(embed=control_panel)
        for r in message.reactions:
            await message.clear_reaction(r)

    async def bounty_tickets(self, message):
        guild = message.guild
        channel = random.choice(guild.channels)
        member = random.choice(guild.members)
        logging.info(channel)
        if message.channel != channel and message.author != member:
            return
        role_regex = re.compile(r'_Guild Tickets: ([0-9]+)_')
        tickets = 0
        for role in member.roles:
            if role_regex.search(role.name):
                tickets = int(role_regex.search(role.name).group(1))
                break
        new_tickets = tickets + 1
        old = f"_Guild Tickets: {tickets}_"
        new = f"_Guild Tickets: {new_tickets}_"
        old_role = discord.utils.get(guild.roles, name=old)
        new_role = discord.utils.get(guild.roles, name=new)
        if new_role is None:
            await guild.create_role(name=new)
            new_role = discord.utils.get(guild.roles, name=new)
        await member.add_roles(new_role)
        if old_role is not None:
            await member.remove_roles(old_role)
        all_tickets = [r.name for r in guild.roles\
                       if role_regex.search(r.name) is not None]
        if old_role and old_role not in all_tickets:
            await old_role.delete()
        embed = discord.Embed(
            title=f"{member} Received a Bounty Ticket", color=0xff0000)
        fields = {
            "Tickets": "\n".join([
                "Use your tickets to enter in the bounty",
                "A random user will be chosen and awarded guild points"]),
            "Total Tickets": new_tickets}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        message = await channel.send(embed=embed)
        reactions = [
            u"\u0030\ufe0f\u20e3", u"\u0031\ufe0f\u20e3",
            u"\u0032\ufe0f\u20e3", u"\u0033\ufe0f\u20e3",
            u"\u0034\ufe0f\u20e3", u"\u0035\ufe0f\u20e3",
            u"\u0036\ufe0f\u20e3", u"\u0037\ufe0f\u20e3",
            u"\u0038\ufe0f\u20e3", u"\u0039\ufe0f\u20e3"]
        for r in reactions:
            await message.add_reaction(r)
        
    async def award_bounty(self, message):
        guild = message.guild
        member = random.choice(guild.members)
        #if message.channel != 'general' and message.author != member:
        #    return
        start = datetime.datetime.now()
        end = start+datetime.timedelta(minutes=1)
        embed = discord.Embed(title="New Bounty!", color=0xff0000)
        fields = { 
            "Win This Bounty": "\n".join([
                "React with the below emojis to enter in this bounty",
                "- Up to 10 entries are allowed",
                "- At least 3 members must be entered"]),
            "Bounty Start": start, "Bounty End": end}
        for field in fields:
            embed.add_field(name=field, value=fields[field])
        channel = discord.utils.get(guild.channels, name='dev-build')
        message = await channel.send(embed=embed)
        reactions = [u"\u0031\ufe0f\u20e3", u"\u0032\ufe0f\u20e3",
                     u"\u0033\ufe0f\u20e3", u"\u0034\ufe0f\u20e3",
                     u"\u0035\ufe0f\u20e3", u"\u0036\ufe0f\u20e3",
                     u"\u0037\ufe0f\u20e3", u"\u0038\ufe0f\u20e3",
                     u"\u0039\ufe0f\u20e3"]
        for r in reactions:
            await message.add_reaction(r)
        while True:
            diff = (end-datetime.datetime.now()).total_seconds()
            if diff <= 0:
                break
            embed.set_footer(
                text=f"Time Reamining: ~ {round(diff/60, 1)} minutes")
            await message.edit(embed=embed)
        for r in message.reactions:
            await message.clear_reactions(r)
        
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
            role_regex = re.compile('_Guild Points: ([0-9]+)_')
            for role in ctx.author.roles:
                if role_regex.search(role.name) is not None:
                    points = int(role_regex.search(role.name).group(1))
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

        @self.command(name="comment", pass_context=True)
        async def comment(ctx):
            ''' Comment on a bug or suggestion of another use
'''
            if ctx.channel != 'bugs-and-suggestions':
                return
            logging.info(ctx.author.roles)
            if "Moderator" not in [r.name for r in ctx.author.roles]:
                await ctx.message.delete()
                await ctx.send("You are not authorized to use this command")
                return

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
            role_regex = re.compile('_Guild Points: ([0-9]+)_')
            #Parse through member roles to get points
            points, plus = 0, int(plus)
            for role in member.roles:
                if role_regex.search(role.name):
                    points = int(role_regex.search(role.name).group(1))
            new_points = points + plus
            #Generate roles for the new and old number of points
            old = f"_Guild Points: {points}_"
            new = f"_Guild Points: {new_points}_"
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
            if ctx.message.channel.name != 'utility-bots':
                return
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
