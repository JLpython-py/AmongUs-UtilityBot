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
            command_regex = re.compile(r'(^(\*introduction)\s\w+)|(\*help)')
            results = command_regex.findall(message.content)
            if not results:
                await message.delete()
            await self.process_commands(message)
        ##members - Only allow *member_name, *member_nickname
        elif message.channel.name == 'members':
            command_regex = re.compile(r'^(\*member_name)|(\*member_nickname)')
            results = command_regex.findall(message.content)
            if not results:
                await message.delete()
            await self.process_commands(message)
        ##game-codes - Only allow working Among Us game codes
        elif message.channel.name == 'game-codes':
            code_regex = re.compile(r'^[A-Za-z]{6}$')
            results = code_regex.findall(message.content)
            if not results:
                await message.delete()
        ##bot-commands - Only allow messages with valid map bot prefixes
        elif message.channel.name == 'map-bots':
            command_regex = re.compile(r'^(MiraHQ\.)|(Polus\.)|(TheSkeld\.)')
            results = command_regex.findall(message.content)
            if not results:
                await message.delete()
        ##dev-guild - Allow all messages and commands
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
            name_regex = re.compile(r'[A-Z][a-z]+ [A-Z][a-z]+')
            results = name_regex.search(ctx.message.content)
            #Create a direct message to notify member of message status
            direct_message = await ctx.message.author.create_dm()
            if results is None:
                #Create and send an embed containing status information
                embed = discord.Embed(
                    title="Invalid Introduction", color=0x00ff00)
                embed.add_field(
                    name="Error", value="Name not detected in entry")
                embed.add_field(
                    name="Acceptable Format", value="[A-Z][a-z]+ [A-Z][a-z]+")
                embed.add_field(name="Example", value="Among Us")
                embed.add_field(
                    name="Not", value="AmongUs, among us, amongus")
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
                embed.add_field(name="Name set to", value=name)
                embed.add_field(
                    name="Role",
                    value="You have now been granted the @Member role")
                embed.add_field(
                    name="Status",
                    value="You can now view the rest of the Among Us server")
                embed.add_field(
                    name="Typo?",
                    value="Run this command again to override the original")
                await direct_message.send(embed=embed)
                #Add 'Member' role to member
                await member.add_roles(role)
            #Write information to members.csv to be referenced
            with open('members.txt') as jsonfile:
                data = json.load(jsonfile)
                data[member.name] = name
            with open('members.txt', 'w') as outfile:
                json.dump(data, outfile)
            #Create and send new member information embed to #members channel
            embed = discord.Embed(
                title="Member Information Card", color=0xffff00)
            embed.add_field(name="Nickname", value=member.name)
            embed.add_field(name="Name", value=name)
            channel = discord.utils.get(ctx.guild.channels, name="members")
            await channel.send(embed=embed)

        @self.command(name="member_name", pass_context=True)
        async def member_name(ctx, *nickname):
            ''' Command: *member_name nickname
                Return Embed Values:
                - Member nickname
                - Member name
                Restridctions: #members
'''
            #Ignore commands outside #members
            if ctx.message.channel.name != 'members':
                return
            nickname = ' '.join(nickname)
            #Convert data to nickname:name dictionary
            with open('members.txt') as jsonfile:
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
            with open('members.txt') as jsonfile:
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
        self.files = {
            'Actions': fr'.\docs\{directory}\actions.csv',
            'Map': fr'.\docs\{directory}\map.jpg',
            'Rooms': fr'.\docs\{directory}\rooms.csv',
            'Tasks': fr'.\docs\{directory}\tasks.csv',
            'Vents': fr'.\docs\{directory}\vents.csv'}
        self.data = {}
        self.read_image('Map')
        self.read_csv('Actions')
        self.read_csv('Rooms')
        self.read_csv('Tasks')
        self.read_csv('Vents')
        self.execute_commands()

    def read_image(self, category):
        ''' Load an image of the map
'''
        file = self.files[category]
        filename = os.path.split(file)[-1]
        self.data[category] = discord.File(file, filename)

    def read_csv(self, category):
        ''' Read csv data for each map
'''
        with open(self.files[category]) as csvfile:
            csvreader = csv.reader(csvfile, delimiter='\t')
            data = list(csvreader)
            headers = data.pop(0)
        self.data[category] = {}
        for row in data:
            info = dict(zip(headers, row))
            name = info['Name']
            self.data[category].setdefault(name, info)

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
            embed.set_image(url="attachment://map.jpg")
            file = self.data['Map']
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
                - Rooms in which the task can be completed
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
            embed.set_footer(text="* denotes a required room")
            await ctx.send(embed=embed)

        @self.command(name="rooms", pass_context=True)
        async def rooms(ctx):
            ''' Command: MapBot.rooms
                Return Embed Values:
                - List of all rooms on the map
'''
            embed = discord.Embed(title="Rooms", color = 0x0000ff)
            for i, room in enumerate(self.data["Rooms"], 1):
                embed.add_field(name=i, value=room)
            await ctx.send(embed=embed)

        @self.command(name="room", pass_context=True)
        async def room(ctx, *name):
            ''' Command: MapBot.room Room Name
                Return Embed Values:
                - Name of room
                - Directly connected rooms
                - Rooms connected by vents
                - Tasks which can be complete in the room
                - Actions which can be cone in the rooms
'''
            data = None
            for room in self.data['Rooms']:
                if ''.join(name).lower() == ''.join(room.split()).lower():
                    data = self.data['Rooms'][room]
                    break
            if data is None:
                await ctx.send(f"{name} cannot be found")
                await ctx.message.delete()
                return
            embed = discord.Embed(title=f"Room: {room}", color = 0x0000ff)
            for aspect in data:
                embed.add_field(name=aspect, value=data[aspect])
            await ctx.send(embed=embed)

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
            ''' Command: MapBot.vent Room Name
                Return Embed Values:
                - Name of room
                - Rooms connected by vents
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

        @self.command(name="action", pass_context=True)
        async def action(ctx, *name):
            ''' Command: MapBot.action Action Name
                Return Embed Values:
                - Name of action
                - Type of action
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
        with open('tokens.txt') as jsonfile:
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
