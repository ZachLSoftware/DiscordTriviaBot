import discord
from discord import ui
from discord import app_commands
from discord.ext import commands
from trivia_file_helper import TriviaFileHelper
import html
import requests
import random

class TriviaCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="new-random-question", description="Challenge all to a new random question")
    async def new_random_question(self, interaction: discord.Interaction):
        members = [member for member in interaction.channel.members if member!=self.bot.user]
        question = requests.get("https://opentdb.com/api.php?amount=1&category=12")
        if question.json()['response_code']!=0:
            await interaction.response.send_message("Error Retrieving Question")
            return
        q = question.json()['results'][0]
        
        await interaction.response.send_message(content="# "+html.unescape(q['question']),view=question_view(q, members, self.question_completed), ephemeral=False)
        msg = await interaction.original_response()
        print(msg.id)

    @app_commands.command(name="clear-channel", description="Clear all messages in the Trivia Channel")
    async def clear_channel(self, interaction: discord.Interaction):
        channel=interaction.channel
        if interaction.channel.name!="trivia-showdown":
            return
        history = []
        async for msg in interaction.channel.history(limit=100):
            history.append(msg)
        await interaction.channel.delete_messages(history)
        await channel.send(f"Channel has been cleared by {interaction.user}")

    async def question_completed(self, interaction: discord.Interaction):
        print(interaction.message.id)

    async def setup(self) -> None:
        await self.bot.add_cog(self)


class question_view(discord.ui.View):
    def __init__(self, question, members, completed_callback):
        self.completed_callback=completed_callback
        self.callback=self.answer_callback
        self.members = members
        self.who_answered=[]
        self.question = question['question']
        self.answer = question['correct_answer']
        self.options = question['incorrect_answers']
        self.options.append(self.answer)
        random.shuffle(self.options)
        super().__init__(timeout=None)

        for option in self.options:
            button = answer_button(label=html.unescape(option), correct=(option==self.answer))
            #button.callback=self.check_answer
            self.add_item(button)

    async def answer_callback(self, interaction: discord.Interaction, correct: bool):
        if interaction.user in self.who_answered:
            await interaction.response.send_message("You have already answered this question", ephemeral=True)
            return
        if correct:
            await interaction.response.send_message(f"{interaction.message.content} \n{interaction.user}: Correct")
        else:
            await interaction.response.send_message(f"{interaction.message.content} \n{interaction.user}: Incorrect")
        self.who_answered.append(interaction.user)
        self.members.remove(interaction.user)
        if len(self.members)==0:
            await self.completed_callback(interaction)
            await interaction.message.edit(content=f"{interaction.message.content} \n **All users have answered**", view=None)
    

    #async def check_answer(self, interaction: discord.Interaction):
    #    print(interaction)


class answer_button(discord.ui.Button):
    def __init__(self, label, correct):
        self.correct = correct
        super().__init__(label=label, style=discord.ButtonStyle.primary)
    async def callback(self, interaction):
        if self.view.callback:
            await self.view.callback(interaction, self.correct)
