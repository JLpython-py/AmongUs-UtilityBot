#! python3
# bots.py

import asyncio
import csv
import logging
import re

import discord
from discord.ext import commands

logging.basicConfig(level=logging.INFO, format=' %(asctime)s - %(levelname)s - %(message)s')
class UtilBot(commands.Bot):
    def __init__(self, *, command_prefix, name):
        commands.Bot.__init__(
            self, command_prefix=command_prefix, self_bot=False)
        self.channels = {}
        with open(r'.\docs\channels.csv') as channels:
            channel_ids = list(csv.reader(channels, delimiter='\t'))
            for i, item in enumerate(channel_ids):
                channel_ids[i] = [int(item[0]), item[1]]
            self.channels = dict(channel_ids)
        self.name = name
        self.execute_commands()

    async def on_ready(self):
        print(f"Utils is running")

    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.name == 'introductions':
            command_regex = re.compile(r'^(\*introduction)\s\w+')
            results = command_regex.findall(message.content)
            logging.info(results)
            if not results:
                await message.delete()
            await self.process_commands(message)
        elif message.channel.name == 'members':
            await message.delete()
        elif message.channel.name == 'game-codes':
            code_regex = re.compile(r'^[A-Za-z]{6}$')
            results = code_regex.findall(message.content)
            logging.info(results)
            if not results:
                await message.delete()

    def execute_commands(self):
        @self.command(name="introduction", pass_context=True)
        async def introduction(ctx):
            ''' Allows user to introduce themselves
                Message is parsed by a regex to find a valid name
                Bot will direct message user on the status of their entry
                Example: *introduction Among Us
'''
            if ctx.message.channel.name != 'dev-build':
                return
            direct_message = await ctx.message.author.create_dm()
            name_regex = re.compile(r'[A-Z][a-z]+ [A-Z][a-z]+')
            results = name_regex.search(ctx.message.content)
            if results is None:
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
                await ctx.message.delete()
                return
            else:
                name = results.group()
                member = ctx.message.author
                role = discord.utils.get(member.guild.roles, name="Member")
                await member.add_roles(role)
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
            return
            channel = discord.utils.get(ctx.guild.channels, name="members")
            announcement = discord.Embed(
                title="Member Information Card", color = 0xffff00)
            announcement.add_field(name="Nickname", value=member)
            announcement.add_field(name="Name", value=name)
            with open(r'.\docs\members.csv') as csvfile:
                data = dict(list(csv.reader(csvfile, delimiter='\t')))
                data[member] = name
            with open(r'.\docx\members.csv', 'w') as csvfile:
                csvwriter = csv.writer(csvfile, delimiter='\t')
                for (member, name) in list(data.items()):
                    csvwriter.writerow([member, name])
            await channel.send(embed=announcement)

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
        self.map = discord.File(self.files['Map'], filename="map.png")

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
            self.data[category].setdefault(name, info)

    async def on_ready(self):
        ''' Notification that the bot is ready
'''
        print(f"Bot is ready: {self.name}")

    def execute_commands(self):
        ''' Bot commands for server members to use
'''
        @self.command(name="map", pass_context=True)
        async def map(ctx):
            ''' Return an image of the map
'''
            embed = discord.Embed(title="Map", color=0x0000ff)
            embed.set_image(
                url="attachment://map.png")
            await ctx.send(file=self.map, embed=embed)

        @self.command(name="tasks", pass_context=True)
        async def all_tasks(ctx):
            ''' Return a list of all the tasks on the map
'''
            embed = discord.Embed(title="Tasks", color=0x0000ff)
            for i, task in enumerate(self.data['Tasks'], 1):
                embed.add_field(name=i, value=task)
            await ctx.send(embed=embed)

        @self.command(name="task", pass_context=True)
        async def task(ctx, *name):
            ''' Return information about a specific task
                - Name of task
                - Type of task
                - Rooms in which the task can be completed
                - Number of steps to complete the task
'''
            data = None
            for task in self.data['Tasks']:
                if ''.join(name).lower() == ''.join(task.split()).lower():
                    data = self.data['Tasks'][task]
                    break
            if data is None:
                await ctx.send(f"{name} cannot be found")
                return
            data = self.data['Tasks'][task]
            embed = discord.Embed(title=f"Task: {task}", color=0x0000ff)
            for aspect in data:
                embed.add_field(name=aspect, value=data[aspect])
            embed.set_footer(text="* denotes a required room")
            await ctx.send(embed=embed)

        @self.command(name="rooms", pass_context=True)
        async def rooms(ctx):
            ''' Returns a list of all the rooms on the map
'''
            embed = discord.Embed(title="Rooms", color = 0x0000ff)
            for i, room in enumerate(self.data["Rooms"], 1):
                embed.add_field(name=i, value=room)
            await ctx.send(embed=embed)

        @self.command(name="room", pass_context=True)
        async def room(ctx, *name):
            ''' Return information about a specific room
                - Name of room
                - Direct connections to other rooms
                - Vent connections to other rooms
                - Tasks which can be completed in the room
                - Actions which can be done in the room
'''
            data = None
            for room in self.data['Rooms']:
                if ''.join(name).lower() == ''.join(room.split()).lower():
                    data = self.data['Rooms'][room]
                    break
            if data is None:
                await ctx.send(f"{name} cannot be found")
                return
            embed = discord.Embed(title=f"Room: {room}", color = 0x0000ff)
            for aspect in data:
                embed.add_field(name=aspect, value=data[aspect])
            await ctx.send(embed=embed)

        @self.command(name="vents", pass_context=True)
        async def vents(ctx):
            ''' Returns a list of all the vents on the map
'''
            embed = discord.Embed(title="Vents", color=0x0000ff)
            for i, vent in enumerate(self.data["Vents"], 1):
                embed.add_field(name=i, value=vent)
            await ctx.send(embed=embed)

        @self.command(name="vent", pass_context=True)
        async def vent(ctx, *name):
            ''' Return information about a specific vent
'''
            data = None
            for vent in self.data['Vents']:
                if ''.join(name).lower() == ''.join(vent.split()).lower():
                    data = self.data['Vents'][vent]
                    break
            if data is None:
                await ctx.send(f"{name} cannot be found")
                return
            embed = discord.Embed(title=f"Vent: {vent}", color = 0x0000ff)
            for aspect in data:
                embed.add_field(name=aspect, value=data[aspect])
            await ctx.send(embed=embed)

class Main:
    def __init__(self):
        self.map_bots = ('The Skeld', 'Mira HQ', 'Polus')#, 'Airship')
        self.util_bot = 'Utils'
        with open(r'.\docs\tokens.csv') as tokenfile:
            self.tokens = dict(list(csv.reader(tokenfile, delimiter='\t')))
        self.loop = asyncio.get_event_loop()

        self.start_map_bots()
        self.start_util_bot()

        self.loop.run_forever()

    def start_map_bots(self):
        for bot in self.map_bots:
            discord_bot = MapBot(
                command_prefix=f"{''.join(bot.split())}.",
                name=bot,
                directory=''.join(bot.split()))
            self.loop.create_task(
                discord_bot.start(self.tokens[bot]))

    def start_util_bot(self):
        discord_bot = UtilBot(
            command_prefix="*",
            name=self.util_bot)
        self.loop.create_task(
            discord_bot.start(
                self.tokens[self.util_bot]))

if __name__ == '__main__':
    Main()
