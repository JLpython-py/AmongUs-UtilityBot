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
        commands.Bot.__init__(
            self, command_prefix=command_prefix, self_bot=False)
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
        ##introductions - Only allow *introduction, *help commands
        if message.channel.name == 'introductions':
            regex = re.compile(r'^\*(introduction|help$)')
            results = regex.findall(message.content)
            if not results:
                await message.delete()
            await self.process_commands(message)
        ##members - Only allow *member_name, *member_nickname
        elif message.channel.name == 'members':
            regex = re.compile(r'^\*(member_name|member_nickname)')
            results = regex.findall(message.content)
            if not results:
                await message.delete()
            await self.process_commands(message)
        ##game-codes - Only allow working Among Us game codes
        elif message.channel.name == 'game-codes':
            regex = re.compile(r'^\w{6}$')
            results = regex.findall(message.content)
            if not results:
                await message.delete()
        ##bot-commands - Only allow messages with valid map bot prefixes
        elif message.channel.name == 'mapbot-commands':
            regex = re.compile(r'^(MiraHQ|Polus|TheSkeld)\.')
            results = regex.findall(message.content)
            if not results:
                await message.delete()
        ##dev-build - Allow all messages and commands
        elif message.channel.name == 'dev-build':
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
            if ctx.message.channel.name != 'introductions':
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
                name = results.group()
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
                    embed.add_field(name=field, values=fields[field])
                await direct_message.send(embed=embed)
                #Add 'Member' role to member
                await member.add_roles(role)
            #Write information to members.csv to be referenced
            with open(os.path.join('data', 'members.txt'), 'w+') as jsonfile:
                data = json.load(jsonfile)
                data[member.name] = name
                json.dump(data, jsonfile)
            #Create and send new member information embed to #members channel
            embed = discord.Embed(
                title="Member Information Card", color=0xffff00)
            fields = {
                "Nickname": member.name,
                "Name": name}
            for field in fields:
                embed.add_field(name=field, value=fields[field])
            channel = discord.utils.get(ctx.guild.channels, name="members")
            await channel.send(embed=embed)

        @self.command(name="member_name", pass_context=True)
        async def member_name(ctx, nickname):
            ''' Command: *member_name nickname
                Return Embed Values:
                - Member nickname
                - Member name
                Restridctions: #members
'''
            #Ignore commands outside #members
            if ctx.message.channel.name != 'members':
                return
            #Convert data to nickname:name dictionary
            with open(os.path.join('data', 'members.txt')) as jsonfile:
                data = json.load(jsonfile)
            #Assert that nickname is on file
            if nickname not in data:
                await ctx.message.delete()
                await ctx.send(f"{nickname} could not be found")
                return
            #Create and send member information embed
            embed = discord.Embed(
                title="Member Information Card", color=0xffff00)
            embed.add_field(name="Nickname", value=nickname)
            embed.add_field(name="Name", value=data.get(nickname))
            await ctx.send(embed=embed)

        @self.command(name="member_nickname", pass_context=True)
        async def member_nickname(ctx, *name):
            ''' Command: *member_nickname name
                Return Embed Values:
                - Member nickname
                - Member name
                Restrictions: #members
'''
            #Ignore commands outside #members
            if ctx.message.channel.name != 'members':
                return
            name = ' '.join(name).title()
            #Convert data to name:nickname dictionary
            with open(os.path.join('data', 'members.txt')) as jsonfile:
                data = {v:k for k, v in json.load(jsonfile).items()}
            #Assert that name is on file
            if name not in data:
                await ctx.message.delete()
                await ctx.send(f"{name} could not be found")
                return
            #Create and send member informatio embed
            embed = discord.Embed(
                title="Member Information Card", color=0xffff00)
            embed.add_field(name="Nickname", value=data.get(name))
            embed.add_field(name="Name", value=name)
            await ctx.message.delete()
            await ctx.send(embed=embed)
            

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
                os.path.join('data', self.directory, "map.jpg"),
                "map.jpg")
            embed.set_image(url="attachment://map.jpg")
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
                os.path.join('data', self.directory, 'location', filename),
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
