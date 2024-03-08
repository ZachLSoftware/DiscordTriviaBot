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


class TriviaBot(commands.Bot):
    channel = ""
    scores_file = "scores.json"
    open_questions_file = "questions.json"

    async def on_ready(self):
        self.controller = SQLiteController("trivia_bot_db.sqlite")
        await self.set_commands()
        print(f'{self.user} has connected to Discord!')
        await self.insert_guild_data()


        
        # self.members = channel.members
        # self.members.remove(self.user)
        # for member in self.members:
        #     self.scores[str(member.id)]=0
        # if os.path.isfile(self.scores_file):
        #     load = TriviaFileHelper().load_file(self.scores_file)
        #     if load != {}:
        #         for k,v in load.items():
        #             self.scores[k]=v
        #     else:
        #         TriviaFileHelper().save_file(self.scores_file, self.scores)

        
        #await self.sync_tree()



    async def insert_guild_data(self):
        #Insert data into database if it doesn't exist
        for guild in self.guilds:
            self.controller.insert_object("guild", ["id", "guild_name"], [guild.id, guild.name], guild.id)
            for member in guild.members:
                if member == self.user or member.bot:
                    continue
                self.controller.insert_object("user", ["id", "username"], [member.id, member.name], member.id)
                self.controller.insert_object("scorecard", ["guild_id", "user_id"], [guild.id, member.id], (guild.id, member.id))
            for channel in guild.channels:
                if channel.type == discord.ChannelType.text:
                    is_allowed = await self.is_bot_allowed(channel)
                    if is_allowed and channel.name!="general":
                        self.controller.insert_object("channel", ["id", "channel_name", "guild_id"], [channel.id, channel.name, channel.guild.id], channel.id)


    async def is_bot_allowed(self, channel):
        bot_member = channel.guild.get_member(self.user.id)
        if bot_member:
            permissions = channel.permissions_for(bot_member)
            return permissions.send_messages
        return False
    async def set_commands(self):
        await TriviaCog(self).setup()
    
    def get_scores(self, guild: discord.Guild):
        score_str = ""
        for member in guild.members:
            if member == self.user or member.bot:
                continue
            score_str += member.name + ":   "
            score_str += str(self.controller.get_score(guild.id, member.id)['score']) +"\n"
        
        # for member in self.members:
        #     score_str += member.name
        #     score_str += ": " + str(self.scores[str(member.id)]) + "\n"
        return score_str

    async def sync_tree(self):
        print("Syncing...")
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} commands")
        except Exception as e:
            print(e)
    
    def get_trivia_channel(self):
        return self.channel
    
        

load_dotenv()
TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content=True
intents.guilds = True
intents.members = True
client = TriviaBot(command_prefix='/', intents=intents)
client.run(TOKEN)