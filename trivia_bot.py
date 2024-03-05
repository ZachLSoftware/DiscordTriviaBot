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
    scores_file = "scores.json"
    open_questions_file = "questions.json"

    async def on_ready(self):
        await self.set_commands()
        print(f'{self.user} has connected to Discord!')
        for channel in self.get_all_channels():
            if channel.name=="trivia-showdown":
                self.channel = channel
        
        members = channel.members
        members.remove(self.user)

        scores = {}

        for member in members:
            scores[str(member.id)]=0
        if os.path.isfile(self.scores_file):
            load = TriviaFileHelper().load_file(self.scores_file)
            for k,v in load.items():
                scores[k]=v
        
        print(scores)
        
        #await self.sync_tree()

    async def set_commands(self):
        trivia_commands = TriviaCog(self)
        await trivia_commands.setup()

    async def sync_tree(self):
        print("Syncing...")
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} commands")
        except Exception as e:
            print(e)

load_dotenv()
TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content=True
intents.guilds = True
intents.members = True
client = TriviaBot(command_prefix='/', intents=intents)
client.run(TOKEN)