#! /usr/bin/env python3
import discord
import requests
import discord.ext
from discord.ext import commands
from dotenv import load_dotenv
from trivia_cog import TriviaCog
import os
from trivia_file_helper import TriviaFileHelper


class TriviaBot(commands.Bot):
    channel = ""
    members = []
    scores = {}
    scores_file = "scores.json"
    open_questions_file = "questions.json"

    async def on_ready(self):
        await self.set_commands()
        print(f'{self.user} has connected to Discord!')
        for channel in self.get_all_channels():
            if channel.name=="trivia-showdown":
                self.channel = channel
        
        self.members = channel.members
        self.members.remove(self.user)
        for member in self.members:
            self.scores[str(member.id)]=0
        if os.path.isfile(self.scores_file):
            load = TriviaFileHelper().load_file(self.scores_file)
            if load != {}:
                for k,v in load.items():
                    self.scores[k]=v
            else:
                TriviaFileHelper().save_file(self.scores_file, self.scores)

        
        #await self.sync_tree()

    async def set_commands(self):
        await TriviaCog(self).setup()
    
    def get_scores(self):
        score_str = ""
        for member in self.members:
            score_str += member.name
            score_str += ": " + str(self.scores[str(member.id)]) + "\n"
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
    
    def update_scores(self, user_id, score):
        self.scores[str(user_id)]+=score
        TriviaFileHelper().save_file(self.scores_file, self.scores)

load_dotenv()
TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content=True
intents.guilds = True
intents.members = True
client = TriviaBot(command_prefix='/', intents=intents)
client.run(TOKEN)