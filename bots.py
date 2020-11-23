#! python3
# bots.py

import asyncio
import csv
import os

import discord
from discord.ext import commands

class UtilBot(commands.Bot):
    def __init__(self, *, command_prefix, name):
        commands.Bot.__init__(
            self, command_prefix=command_prefix, self_bot=False)
        with open(r'.\docs\channels.csv') as channels:
            channel_ids = list(csv.reader(channels, delimiter='\t'))
            for i, item in enumerate(channel_ids):
                channel_ids[i] = [int(item[0]), item[1]]
            self.channels = dict(channel_ids)
        self.channel_commands = {
            '#introductions': self.introduction,
            '#dev-build': self.introduction}
        self.name = name
        self.execute_commands()

    async def on_ready(self):
        print(f"Utils is running")

    def execute_commands(self):
        @self.event
        async def on_message(self, message):
            await print(message)

        @self.command(name="introduction", pass_context=True)
        async def introduction(self, first, last):
            pass

class MapBot(commands.Bot):
    def __init__(self, *, command_prefix, name, directory):
        self.client = discord.Client()
        commands.Bot.__init__(
            self, command_prefix=command_prefix, self_bot=False)
        self.name = name
        self.files = {
            'Map': fr'.\docs\{directory}\map.jpg',
            'Rooms': fr'.\docs\{directory}\rooms.csv',
            #'Sabotages': fr'.\docx\{directory}\sabotages.csv',
            'Tasks': fr'.\docs\{directory}\tasks.csv',
            'Vents': fr'.\docs\{directory}\vents.csv'}
        self.data = {}
        self.read_map()
        self.read_map_data('Rooms')
        #self.read_map_data('Sabotages')
        self.read_map_data('Tasks')
        self.read_map_data('Vents')
        self.execute_commands()

    def read_map(self):
        ''' Load an image of the map
'''
        self.map = discord.File(self.files['Map'])

    def read_map_data(self, category):
        ''' Read map CSV info
'''
        with open(self.files[category]) as csvfile:
            csvreader = csv.reader(csvfile, delimiter='|')
            data = list(csvreader)
            headers = data.pop(0)
        self.data[category] = {}
        for row in data:
            info = dict(zip(headers, row))
            name = info['Name']
            self.data[category].setdefault(''.join(name.split()), info)

    async def on_ready(self):
        ''' Notification that the bot is ready
'''
        print(f"Bot is ready: {self.name}")

    def execute_commands(self):
        ''' Bot commands for server members to use
'''
        @self.command(name="options", pass_context=True)
        async def options(ctx):
            ''' Return a list available bot command options
'''
            print(f'{ctx}: Options')
            await ctx.send('\n'.join(OPTIONS))

        @self.command(name="map", pass_context=True)
        async def map(ctx):
            ''' Return an image of the map
'''
            print(f'{ctx}: Map')
            await ctx.send(file=self.map)

        @self.command(name="tasks", pass_context=True)
        async def tasks(ctx):
            ''' Return a list of all the tasks on the map
'''
            print(f'{ctx}: Tasks')
            await ctx.send('\n'.join(self.data['Tasks']))

        @self.command(name="task", pass_context=True)
        async def task(ctx, *task):
            ''' Return information about a specific task
                - Name of task
                - Type of task
                - Rooms in which the task can be completed
                - Number of steps to complete the task
'''
            task = ''.join(task)
            print(f'{ctx}: Task[{task}]')
            tasks = self.data['Tasks']
            data = None
            for t in tasks:
                if t.lower() == task.lower():
                    data = tasks[t]
            if data is None:
                await ctx.send('Nonexistent Task')
                return
            return_text = [
                f"*Name:*\n\t{data['Name']}",
                f"*Type:*\n\t{data['Type']}",
                f"*Rooms:*\n\t{data['Room']}",
                f"*Number of steps:*\n\t{data['Steps']}"]
            if '*' in data['Room']:
                return_text.append('* deontes a required room')
            await ctx.send('\n'.join(return_text))

        @self.command(name="rooms", pass_context=True)
        async def rooms(ctx):
            ''' Returns a list of all the rooms on the map
'''
            print(f'{ctx}: Rooms')
            await ctx.send('\n'.join(self.data['Rooms']))

        @self.command(name="room", pass_context=True)
        async def room(ctx, *room):
            ''' Return information about a specific room
                - Name of room
                - Direct connections to other rooms
                - Vent connections to other rooms
                - Tasks which can be completed in the room
                - Actions which can be done in the room
'''
            room = ''.join(room)
            print(f'{ctx}: Room[{room}]')
            rooms = self.data['Rooms']
            data = None
            for r in rooms:
                if r.lower() == room.lower():
                    data = rooms[r]
            if data is None:
                await ctx.send('Nonexistent Room')
                return
            return_text = [
                f"*Name:*\n\t{data['Name']}",
                f"*Connections:*\n\t{data['Connections']}",
                f"*Vent Connections:*\n\t{data['Vents']}",
                f"*Tasks:*\n\t{data['Tasks']}",
                f"*Actions:*\n\t{data['Actions']}"]
            await ctx.send('\n'.join(return_text))

        @self.command(name="vents", pass_context=True)
        async def vents(ctx):
            ''' Returns a list of all the vents on the map
'''
            print(f'{ctx}: Vents')
            await ctx.send('\n'.join(self.data['Vents']))

        @self.command(name="vent", pass_context=True)
        async def vent(ctx, *vent):
            ''' Return information about a specific vent
'''
            vent = ''.join(vent)
            print(f'{ctx}: Vent[{vent}]')
            vents = self.data['Vents']
            data = None
            for v in vents:
                if v.lower() == vent.lower():
                    data = vents[v]
            if data is None:
                await ctx.send('Nonexistent Vent')
                return
            return_text = [
                f"*Name:*\n\t{data['Name']}",
                f"*Connections:*\n\t{data['Connections']}"]
            await ctx.send('\n'.join(return_text))
