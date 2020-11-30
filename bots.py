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

class UtilBot(commands.Bot):
    def __init__(self, *, command_prefix, name):
        '''
'''
        intents = discord.Intents.default()
        intents.members = True
        commands.Bot.__init__(
            self, command_prefix=command_prefix, intents=intents,
            self_bot=False)
        self.name = name
        self.execute_commands()

    async def on_ready(self):
        ''' Notify developer that a UtilBot-class bot is active
'''
        print(f"Bot is ready: {self.name}")

    async def on_message(self, message):
        ''' Messages from certain channels are run through a regex
            Messages that do not comply to the regex are considered spam
            Spam messages are deleted
'''
        logging.info((message.author.name, message.channel, message.content))
        #Ignore all bot messages
        if message.author.bot:
            return
        if 'Direct Message' in str(message.channel):
            await message.channel.send("Direct Messaging is not supported")
            return
        with open(os.path.join('data', 'regex.txt')) as file:
            regexes = dict([line.strip('\n').split('\t') for line in file])
        for channel in regexes:
            if channel in message.channel.name:
                break
        regex = re.compile(regexes[channel])
        results = regex.search(message.content)
        if results is None:
            await message.delete()
            return
        await self.process_commands(message)

    def execute_commands(self):
        ''' UtilBot-class bot commands which can be used by members
'''
        @self.command(name="introduction", pass_context=True)
        async def introduction(ctx):
            ''' Command: *introduction Firstname Lastname
                Return Embed Values:
                - Member nickname
                - Member name
                Other Return Values:
                - User is granted Member role
                - Information is stored for other Members to reference
                Restrictions: #introductions
'''
            #Ignore commands outside #introductions
            if 'introductions' in ctx.message.channel.name:
                return
            #Parse message for a valid name
            regex = re.compile(r'^\*introduction(\s[A-Z][a-z]+){2}$')
            results = regex.search(ctx.message.content)
            #Create a direct message to notify member of message status
            direct_message = await ctx.message.author.create_dm()
            if results is None:
                #Create and send an embed containing status information
                embed = discord.Embed(
                    title="Invalid Introduction", color=0x00ff00)
                fileds = {
                    "Error": "Name not detected in entry",
                    "Acceptable Format": "^\*introduction(\s[A-Z][a-z]+){2}$",
                    "Example": "Among Us",
                    "Not": "AMONG US, AmongUs, among us, amongus"}
                for field in fields:
                    embed.add_field(name=field, value=fields[field])
                await direct_message.send(embed=embed)
                #Delete invalid command
                await ctx.message.delete()
                return
            else:
                name = ' '.join(results.group().split()[-2:])
                member = ctx.message.author
                role = discord.utils.get(member.guild.roles, name="Member")
                #Create and send an embed containing status information
                embed = discord.Embed(
                    title="Confirm Introduction", color=0x00ff00)
                fields = {
                    "Name set to": name,
                    "Role": "You have now been granted the 'Member' role",
                    "Status": "You can now view the rest of the server",
                    "Typo?": "Run this command to override previous entries"}
                for field in fields:
                    embed.add_field(name=field, value=fields[field])
                await direct_message.send(embed=embed)
                #Add 'Member' role to member
                await member.add_roles(role)
            #Write information to members.txt to be referenced
            with open(os.path.join('data', 'members.txt'), 'r') as jsonfile:
                data = json.load(jsonfile)
                data[member.name] = name
            with open(os.path.join('data', 'members.txt'), 'w') as jsonfile:
                json.dump(data, jsonfile)
            #Create and send new member information embed to #members channel
            embed = discord.Embed(
                title="Member Information Card", color=0xffff00)
            fields = {
                "Nickname": member.name,
                "Name": name}
            for field in fields:
                embed.add_field(name=field, value=fields[field])
            channel = discord.utils.get(
                ctx.guild.channels, name="members")
            await channel.send(embed=embed)

        @self.command(name="member", pass_context=True)
        async def member(ctx, search_method, *member):
            '''
'''
            channel = self.get_channel(780599994360397825)
            messages = await channel.history(limit=200).flatten()
            if search_method == 'Name':
                search = ' '.join(member)
            elif search_method == 'Nickname':
                search = member[0]
            found = False
            for message in messages[::-1]:
                logging.info(message)
                nickname = message.author.name
                name = ' '.join(message.content.split()[-2:])
                if search in message.content:
                    if search_method == 'Name':
                        name = search
                    elif search_method == 'Nickname':
                        nickname = search
                    found = True
                    break
            if not found:
                await ctx.send(
                    f"Could not find {member} [Search by {search_method}]")
                return
            embed = discord.Embed(
                title="Member Information Card", color=0xffff00)
            embed.add_field(name="Nickname", value=nickname)
            embed.add_field(name="Name", value=name)
            await ctx.send(embed=embed)

        @self.command(name="suggestion", pass_context=True)
        async def suggestion(ctx, *suggestion):
            ''' Command: *suggestion Suggestion goes here
'''
            if ctx.message.channel.name != 'suggestions-and-bugs':
                return
            reactions = [
                "<:Victory:779396489792847892>",
                "<:Defeat:779396491667963904>"]
            for emoji in reactions:
                await ctx.message.add_reaction(emoji)

        @self.command(name="bug", pass_context=True)
        async def bug(ctx, *bug):
            ''' Command: *bug Bug goes here
'''
            if ctx.message.channel.name != 'suggestions-and-bugs':
                return
            reactions = [
                "<:Report:777211184881467462"]
            for emoji in reactions:
                await ctx.message.add_reaction(emoji)

        @self.command(name="get_points", pass_context=True)
        async def get_points(ctx):
            '''
'''
            for role in ctx.author.roles:
                points = role.name.strip('_').strip()[-1]
                if points.isdecimal():
                    break
            embed = discord.Embed(title=ctx.author.name, color=0xffff00)
            embed.add_field(name="Points", value=points)
            await ctx.send(embed=embed)

        @self.command(name="give_points", pass_context=True)
        async def give_points(ctx, nickname, plus):
            '''
'''
            if "Developer" not in [r.name for r in ctx.author.roles]:
                await ctx.message.delete()
                await ctx.send("You are not authorized to use this command")
                return
            found = False
            for member in ctx.guild.members:
                if member.name == nickname:
                    found = True
                    break
            logging.info(found)
            if not found:
                await ctx.message.delete()
                await ctx.send(f"Could not find {nickname}")
                return
            points = 0
            for role in member.roles:
                pts = role.name.strip('_').strip()[-1]
                if pts.isdecimal():
                    points = pts
            new_points = int(points)+int(plus)
            logging.info((points, new_points))
            all_points = [role for role in member.roles\
                          for member in ctx.message.guild.members\
                          if role.name.isdecimal()]
            if new_points not in all_points:
                await ctx.guild.create_role(
                    name=f"_Contributions: {new_points}_")
                new_role = discord.utils.get(
                    ctx.guild.roles, name=f"_Contributions: {new_points}_")
                await member.add_roles(new_role)
            if points:
                old_role = discord.utils.get(
                    ctx.guild.roles, name=f"_Contributions: {points}_")
                await member.remove_roles(old_role)
            all_points = [role for role in member.roles\
                          for member in ctx.message.guild.members\
                          if role.name.isdecimal()]
            if points and points not in all_points:
                role = discord.utils.get(
                    ctx.guild.roles, name=f"_Contributions: {points}_")
                await role.delete()

class MapBot(commands.Bot):
    def __init__(self, *, command_prefix, name, directory):
        '''
'''
        self.client = discord.Client()
        commands.Bot.__init__(
            self, command_prefix=command_prefix, self_bot=False)
        self.name = name
        self.directory = directory
        self.files = {
            'Actions': os.path.join('data', self.directory, 'actions.csv'),
            'Locations': os.path.join('data', self.directory, 'locations.csv'),
            'Tasks': os.path.join('data', self.directory, 'tasks.csv'),
            'Vents': os.path.join('data', self.directory, 'vents.csv')}
        self.data = {}
        self.read_files()
        self.execute_commands()

    def read_files(self):
        ''' Read CSV data for each map
'''
        for category in self.files:
            with open(self.files[category]) as csvfile:
                data = list(csv.reader(csvfile, delimiter='\t'))
                headings = data.pop(0)
            self.data[category] = {}
            for row in data:
                info = dict(zip(headings, row))
                self.data[category].setdefault(info['Name'], info)

    async def on_ready(self):
        ''' Notify developer that a MapBot-class bot is active
'''
        print(f"Bot is ready: {self.name}")

    def execute_commands(self):
        ''' MapBot-class commands which can be used by members
'''
        @self.command(name="map", pass_context=True)
        async def map(ctx):
            ''' Command: MapBot.map
                Return Embed Values:
                - High-detail image of corresponding map
'''
            embed = discord.Embed(title="Map", color=0x0000ff)
            file = discord.File(
                os.path.join('data', self.directory, "Map.jpg"),
                "Map.jpg")
            embed.set_image(url="attachment://Map.jpg")
            await ctx.send(file=file, embed=embed)

        async def sabotage_map(ctx):
            embed = discord.Embed(title="Sabotage Map", color=0x0000ff)
            file = discord.File(
                os.path.join('data', self.directory, "Sabotage Map.jpg"),
                "Sabotage Map.jpg")
            embed.set_image(url="attachment://Sabotage Map.jpg")
            await ctx.send(file=file, embed=embed)

        @self.command(name="tasks", pass_context=True)
        async def tasks(ctx):
            ''' Command: MapBot.tasks
                Return Embed Values:
                - List of all tasks which can be completed on the map
'''
            embed = discord.Embed(title="Tasks", color=0x0000ff)
            for i, task in enumerate(self.data['Tasks'], 1):
                embed.add_field(name=i, value=task)
            await ctx.send(embed=embed)

        @self.command(name="task_type", pass_context=True)
        async def task_type(ctx, type_name):
            ''' Command: MapBot.task_type Type
                Return Embed Values:
                - List of all tasks which are classified as such
'''
            tasks = []
            for task in self.data['Tasks']:
                if type_name.title() in self.data['Tasks'][task]['Type']:
                    tasks.append(task)
            if not tasks:
                await ctx.send(f"{type_name} cannot be found")
                await ctx.message.delete()
                return
            embed = discord.Embed(title=f"Task: {type_name}", color=0x0000ff)
            for i, task in enumerate(tasks, 1):
                embed.add_field(name=i, value=task)
            await ctx.send(embed=embed)

        @self.command(name="task", pass_context=True)
        async def task(ctx, *name):
            ''' Command: MapBot.task Task Name
                Return Embed Values:
                - Name of task
                - Type of task
                - Locations where the task can be completed
                - Number of steps required to complete the task
'''
            data = None
            for task in self.data['Tasks']:
                if ''.join(name).lower() == ''.join(task.split()).lower():
                    data = self.data['Tasks'][task]
                    break
            if data is None:
                await ctx.send(f"{name} cannot be found")
                await ctx.message.delete()
                return
            data = self.data['Tasks'][task]
            embed = discord.Embed(title=f"Task: {task}", color=0x0000ff)
            for aspect in data:
                embed.add_field(name=aspect, value=data[aspect])
            filename = f"{data['Name']}.png"
            file = discord.File(
                os.path.join('data', self.directory, 'tasks', filename),
                filename)
            embed.set_image(url=f"attachment://{filename}")
            await ctx.send(file=file, embed=embed)

        @self.command(name="locations", pass_context=True)
        async def locations(ctx):
            ''' Command: MapBot.locations
                Return Embed Values:
                - List of all locations on the map
'''
            embed = discord.Embed(title="Locations", color = 0x0000ff)
            for i, room in enumerate(self.data["Locations"], 1):
                embed.add_field(name=i, value=room)
            await ctx.send(embed=embed)

        @self.command(name="location", pass_context=True)
        async def location(ctx, *name):
            ''' Command: MapBot.location Location Name
                Return Embed Values:
                - Name of location
                - Directly connected locations
                - Locations connected by vents
                - Tasks which can be complete in the location
                - Actions which can be cone in the locations
                - Image of location
'''
            data = None
            for location in self.data['Locations']:
                if ''.join(name).lower() == ''.join(location.split()).lower():
                    data = self.data['Locations'][location]
                    break
            if data is None:
                await ctx.send(f"{name} cannot be found")
                await ctx.message.delete()
                return
            embed = discord.Embed(title=f"Location: {location}", color = 0x0000ff)
            for aspect in data:
                embed.add_field(name=aspect, value=data[aspect])
            filename = f"{data['Name']}.png"
            file = discord.File(
                os.path.join('data', self.directory, 'locations', filename),
                filename)
            embed.set_image(url=f"attachment://{filename}")
            await ctx.send(file=file, embed=embed)

        @self.command(name="vents", pass_context=True)
        async def vents(ctx):
            ''' Command: MapBot.vents
                Return Embed Values:
                - List of all vents on the map
'''
            embed = discord.Embed(title="Vents", color=0x0000ff)
            for i, vent in enumerate(self.data["Vents"], 1):
                embed.add_field(name=i, value=vent)
            await ctx.send(embed=embed)

        @self.command(name="vent", pass_context=True)
        async def vent(ctx, *name):
            ''' Command: MapBot.vent Location Name
                Return Embed Values:
                - Name of location
                - Locations connected by vents
'''
            data = None
            for vent in self.data['Vents']:
                if ''.join(name).lower() == ''.join(vent.split()).lower():
                    data = self.data['Vents'][vent]
                    break
            if data is None:
                await ctx.send(f"{name} cannot be found")
                await ctx.message.delete()
                return
            embed = discord.Embed(title=f"Vent: {vent}", color=0x0000ff)
            for aspect in data:
                embed.add_field(name=aspect, value=data[aspect])
            await ctx.send(embed=embed)

        @self.command(name="actions", pass_context=True)
        async def actions(ctx):
            ''' Command: MapBot.actions
                Return Embed Values:
                - List of all actions which can be done on the map
'''
            embed = discord.Embed(title="Actions", color=0x0000ff)
            for i, action in enumerate(self.data["Actions"], 1):
                embed.add_field(name=i, value=action)
            await ctx.send(embed=embed)

        @self.command(name="action", pass_contextroo=True)
        async def action(ctx, *name):
            ''' Command: MapBot.action Action Name
                Return Embed Values:
                - Name of action
                - Type of action
                - Locations where action can be done
                - Severity of action
'''
            data = None
            for action in self.data['Actions']:
                if ''.join(name).lower() == ''.join(action.split()).lower():
                    data = self.data['Actions'][action]
                    break
            if data is None:
                await ctx.send(f"{name} cannot be found")
                await ctx.message.delete()
                return
            embed = discord.Embed(title=f"Action: {action}", color=0x0000ff)
            for aspect in data:
                embed.add_field(name=aspect, value=data[aspect])
            await ctx.send(embed=embed)

class Main:
    def __init__(self):
        ''' Create and run bots for the Among Us Discord server
'''
        #Gather general data for each bot
        self.map_bots = ('The Skeld', 'Mira HQ', 'Polus')#, 'Airship')
        self.util_bots = ('Utils',)
        with open(os.path.join('data', 'tokens.txt')) as jsonfile:
            self.tokens = json.load(jsonfile)

        self.loop = asyncio.get_event_loop()
        #Create a MapBot-class bot for each Among Us map
        for bot in self.map_bots:
            pre = f"{''.join(bot.split())}."
            discord_bot = MapBot(
                command_prefix=pre, name=bot, directory=''.join(bot.split()))
            self.loop.create_task(discord_bot.start(self.tokens[bot]))
        #Create a UtilBot-class bot for the Among Us server
        for bot in self.util_bots:
            discord_bot = UtilBot(
                command_prefix="*", name=bot)
            self.loop.create_task(discord_bot.start(self.tokens[bot]))
        self.loop.run_forever()

if __name__ == '__main__':
    Main()
