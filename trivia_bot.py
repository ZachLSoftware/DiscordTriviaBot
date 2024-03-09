#! /usr/bin/env python3
import discord
import requests
import discord.ext
from discord.ext import commands
from dotenv import load_dotenv
from trivia_cog import TriviaCog
import os
from trivia_file_helper import TriviaFileHelper
from trivia_bot_sql_controller import SQLiteController
from trivia_event_listener_cog import EventManagementCog


class TriviaBot(commands.Bot):
    """
    :When bot connects, create sqlite connection
    :Setup the trivia commands
    :Insert data from each guild (Checks in place to not try to re-insert data)
    """
    async def on_ready(self):
        self.controller = SQLiteController("test.sqlite")
        await self.set_commands()
        print(f'{self.user} has connected to Discord!')
        await self.insert_guild_data(self.guilds)


    """
    :Interates through each guild and tries to insert the following
    -Guild into guild table
    -User into user table
    -Create a scorecard for each user
    -Insert into channels
    :The SQL controller will check if the object exists before trying to insert
    """
    async def insert_guild_data(self, guilds):
        #Insert data into database if it doesn't exist
        #Iterate through guilds
        connection = await self.controller.start_sync_inserts()
        try:
            for guild in guilds:

                #Insert Guild
                await self.controller.insert_object_async("guild", ["id", "guild_name"], [guild.id, guild.name], connection, guild.id)

                #Iterate through guild members ignoring bots
                for member in guild.members:
                    if member == self.user or member.bot:
                        continue

                    #Insert user and create scorecard
                    await self.controller.insert_object_async("user", ["id", "username"], [member.id, member.name], connection, member.id)
                    
                
                #Interate through allowed channels
                for channel in guild.channels:
                    if channel.type == discord.ChannelType.text:
                        is_allowed = await self.is_bot_allowed(channel)
                        if is_allowed and channel.name!="general":
                            await self.controller.insert_object_async("channel", ["id", "channel_name", "guild_id"], [channel.id, channel.name, channel.guild.id], connection, channel.id)
                for channel in guild.channels:
                    if channel.type == discord.ChannelType.text:
                        is_allowed = await self.is_bot_allowed(channel)
                        if is_allowed and channel.name!="general":
                            for member in channel.members:
                                if member.bot:
                                    continue
                                await self.controller.insert_object_async("scorecard", ["user_id", "channel_id","guild_id"], [member.id, channel.id, guild.id], connection, (member.id, channel.id))

        except Exception as e:
            print(e)
        finally:
            await self.controller.close_async(connection)


    """
    :Checks if the bot is allowed to post messages to the channel
    """
    async def is_bot_allowed(self, channel):
        bot_member = channel.guild.get_member(self.user.id)
        if bot_member:
            permissions = channel.permissions_for(bot_member)
            return permissions.send_messages
        return False
    
    async def is_user_allowed(self, channel: discord.TextChannel, user_id: int):
        member = channel.guild.get_member(user_id)
        if member:
            permissions = channel.permissions_for(member)
            return permissions.send_messages
        return False
    """
    :Calls the cogs setup function
    """
    async def set_commands(self):
        await EventManagementCog(self).setup()
        await TriviaCog(self).setup()
    
    """
    :Get score for the guild and match them with members
    """
    def get_scores(self, channel: discord.TextChannel):
        try:
            self.controller.open_connection()
            #string builder
            score_str = ""

            #Guild Scores
            scores = self.controller.get_channel_scores(channel.id)

            #Add scores to string
            for member in channel.members:
                if member == self.user or member.bot:
                    continue
                score_str += member.name + ":   "
                score_str += str(scores[member.id]['score']) +"\n"
            
            return score_str
        except Exception as e:
            print(e)
            return None
        finally:
            self.controller.close_connection()


    """
    :Sync Discord Command Tree
    """
    async def sync_tree(self):
        print("Syncing...")
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} commands")
        except Exception as e:
            print(e)
        

load_dotenv()
TOKEN = os.getenv("TEST_TOKEN")
intents = discord.Intents.default()
intents.message_content=True
intents.guilds = True
intents.members = True
client = TriviaBot(command_prefix='/', intents=intents)
client.run(TOKEN)