import discord
from discord import ui
from discord import app_commands
from discord.ext import commands
from trivia_file_helper import TriviaFileHelper
from categories_enum import TriviaCategories
import copy
import asyncio
import html
import requests
import random

class TriviaCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.questions_file = "open_questions.json"
        self.open_questions = TriviaFileHelper().load_file(self.questions_file)

    @app_commands.command(name="new-random-question", description="Challenge all to a new random question")
    async def new_random_question(self, interaction: discord.Interaction):
        
        q = await self.get_question("https://opentdb.com/api.php?amount=1")
        if q == False:
            await interaction.response.send_message("Error Retrieving Question")
            return

        await self.setup_question(interaction, q)

    # @app_commands.command(name="clear-channel", description="Clear all messages in the Trivia Channel")
    # async def clear_channel(self, interaction: discord.Interaction):
    #     channel=interaction.channel
    #     if interaction.channel.name!="trivia-showdown":
    #         return
    #     history = []
    #     async for msg in interaction.channel.history(limit=100):
    #         history.append(msg)
    #     await interaction.channel.delete_messages(history)
    #     await channel.send(f"Channel has been cleared by {interaction.user}")


    @app_commands.command(name="new-question", description="Challenge all to a new question of the category of your choice")
    @app_commands.describe(categories="Categories to choose from")
    async def new_question(self, interaction: discord.Interaction, categories: TriviaCategories):
        url = f"https://opentdb.com/api.php?amount=1&category={categories.value}"
        q = await self.get_question(url)
        if q == False:
            await interaction.response.send_message("Error Retrieving Question")
            return
        await self.setup_question(interaction, q)


    @app_commands.command(name="scoreboard", description="See the scoreboard")
    async def scoreboard(self, interaction: discord.Interaction):
        await interaction.response.send_message(content=self.bot.get_scores(interaction.guild), ephemeral=False)

    async def question_completed(self, interaction: discord.Interaction):
        # del self.open_questions[str(interaction.message.id)]
        # TriviaFileHelper().save_file(self.questions_file, self.open_questions)
        self.bot.controller.delete_question(interaction.message.id)
        await interaction.channel.send(content=self.bot.get_scores(interaction.guild))

    async def get_question(self, url):
        result =  requests.get(url)

        if result.json()['response_code']!=0:
            return False
        else:
            return result.json()['results'][0]
        
    async def setup_question(self, interaction: discord.Interaction, q):
        members = [member for member in interaction.channel.members if not member.bot]
        #members = [member for member in interaction.channel.members if member.id==405785308639133696]
        user_string = "***"
        for member in members:
            user_string += member.name + ": Not answered, "
        user_string=user_string[:-2] + "***\n"
        await interaction.response.send_message(content=f"@everyone **Category: {q['category']}**\n {user_string}# {html.unescape(q['question'])}",view=question_view(copy.deepcopy(q), members, self.question_completed, self.user_answered), ephemeral=False)
        msg = await interaction.original_response()
        self.bot.controller.insert_object("message", ["id", "channel_id"],[msg.id, msg.channel.id], msg.id)
        question_id=self.bot.controller.insert_object("question_data", ["question", "correct_answer", "category", "difficulty", "message_id"], [q['question'], q['correct_answer'], q['category'], q['difficulty'], msg.id])
        for incorrect in q['incorrect_answers']:
            self.bot.controller.insert_object("incorrect_answers", ["label", "question_id"], [incorrect, question_id])
        for member in members:
            self.bot.controller.insert_object("user_answers", ["user_id", "question_id"], [member.id, question_id])

    async def user_answered(self, interaction: discord.Interaction, correct: bool):
        if correct: 
            self.bot.controller.update_score(interaction.guild.id, interaction.user.id, 1)
            result_string = ": Correct"
            response_string = "You were correct! +1 to your score!"
            
        else:  
            result_string = ": Incorrect"
            q_id = self.bot.controller.get_question_id(interaction.guild.id, interaction.channel.id, interaction.message.id)
            answer= self.bot.controller.get_object("question_data",q_id)['correct_answer']
            response_string = f"You were incorrect! The correct answer was: {answer}\n Better luck next time!"
        q_id = self.bot.controller.get_question_id(interaction.guild.id, interaction.channel.id, interaction.message.id)    
        self.bot.controller.update_object("user_answers", (interaction.user.id, q_id), ["answered", "correct"], [True, correct])

        # question_dict = self.open_questions[str(interaction.message.id)]
        # question_dict["users"][str(interaction.user.id)][0]=True
        # question_dict["users"][str(interaction.user.id)][1]=correct


        # TriviaFileHelper().save_file(self.questions_file, self.open_questions)


        user_string = interaction.message.content.split("***\n")[0]
        user_string=user_string.replace(interaction.user.name + ": Not answered", interaction.user.name + result_string)
        content = user_string + "***\n" + interaction.message.content.split("***\n")[1]
        await interaction.message.edit(content=content)
        await interaction.response.send_message(response_string, ephemeral=True)
        

    async def setup(self) -> None:
        await self.reset_questions()
        await self.bot.add_cog(self)

    async def reset_questions(self):
        open_questions = self.bot.controller.fetch_open_questions()
        for gld, gq in open_questions.items():
            for chnl, messages in gq.items():
                for msg, question in messages.items():
                    channel = await self.bot.fetch_channel(chnl)
                    message = await channel.fetch_message(msg)
                    members = [member for member in channel.members if member!=self.bot.user and member.id in question['user_answers'] and not question['user_answers'][member.id]['answered']]
                    new_message = await channel.send(content=message.content, view=question_view(question['question_data'], members, self.question_completed, self.user_answered))
                    await message.delete()
                    self.bot.controller.update_object("message", msg, ["id"], [new_message.id])
                    #self.bot.controller.update_object("question_data", question['question_data']['id'], ["message_id"], [new_message.id])
        # for msg, data in self.open_questions.items():
        #     channel = await self.bot.fetch_channel(data["channel_id"])
        #     message = await channel.fetch_message(msg)
        #     members = [member for member in channel.members if member!=self.bot.user and (str(member.id) in data["users"] and not data["users"][str(member.id)][0])]
        #     new_message = await channel.send(content=message.content, view=question_view(data["question"], members, self.question_completed, self.user_answered))
        #     await message.delete()
        #     updated_questions[str(new_message.id)]=data
        # self.open_questions=updated_questions
        # TriviaFileHelper().save_file(self.questions_file, self.open_questions)


class question_view(discord.ui.View):
    def __init__(self, question, members, completed_callback, user_callback):
        self.completed_callback=completed_callback
        self.user_callback = user_callback
        self.callback=self.answer_callback
        self.members = members
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
        message=interaction.message
        if interaction.user not in self.members:
            await interaction.response.send_message("You have already answered this question", ephemeral=True)
            return
        if correct:
            await self.user_callback(interaction, True)
            result_string = ": Correct"
            
        else:
            await self.user_callback(interaction, False)
            result_string = ": Incorrect"
        self.members.remove(interaction.user)
        if len(self.members)==0:
            await self.completed_callback(interaction)
            user_string = interaction.message.content.split("***\n")[0]
            user_string=user_string.replace(interaction.user.name + ": Not answered", interaction.user.name + result_string)
            content = user_string + "***\n" + interaction.message.content.split("***\n")[1]
            await message.edit(content=f"{content} \n ## The correct answer was: {self.answer} \n **Question is now closed.**", view=None)
    

    #async def check_answer(self, interaction: discord.Interaction):
    #    print(interaction)


class answer_button(discord.ui.Button):
    def __init__(self, label, correct):
        self.correct = correct
        super().__init__(label=label, style=discord.ButtonStyle.primary)
    async def callback(self, interaction):
        if self.view.callback:
            await self.view.callback(interaction, self.correct)
