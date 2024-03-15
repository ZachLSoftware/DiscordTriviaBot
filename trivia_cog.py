import discord
from discord import app_commands
from discord.ext import commands
from categories_enum import TriviaCategories
from trivia_bot_sql_controller import SQLiteController
from datetime import datetime, timedelta
from log_to_file import *
import copy
import asyncio
import html
import requests
import random

class TriviaCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.questions_file = "open_questions.json"
        self.controller = bot.controller


    """
    :Create a pointer to the bot controller, ensuring it is the right type
    """
    @property
    def controller(self):
        if not hasattr(self, '_controller'):
            if isinstance(self.bot.controller, SQLiteController):
                self._controller = self.bot.controller
            else:
                raise AttributeError("Bot controller is not an instance of SQLiteController")
        return self._controller
    
    @controller.setter
    def controller(self, value):
        if not isinstance(value, SQLiteController):
            raise ValueError("Controller must be an instance of SQLiteController")
        self._controller = value


    """
    :Sets the commands to the bot and refreshes messages so they can be tracked again
    """
    async def setup(self) -> None:
        await self.reset_questions()
        await self.bot.add_cog(self)
        self.bot.loop.create_task(self.background_refresh())


    """
    :/new-random-question
    :Listens for the above command and returns a single random question
    """
    @app_commands.command(name="new-random-question", description="Challenge all to a new random question")
    async def new_random_question(self, interaction: discord.Interaction):
        
        try:
            await interaction.response.defer()
            #Get Question from opentdb
            q = await self.get_question({"amount": 1}, interaction)
            if q == False:
                await interaction.followup.send("Error Retrieving Question")
                return
            
            await self.setup_question(interaction, q)
        except Exception as e:
            await interaction.followup.send("Error Retrieving Question")
            log_error(e)


    """
    :/new-question category
    :Listens for the command and gets a new question from the category of choice
    """
    @app_commands.command(name="new-question", description="Challenge all to a new question of the category of your choice")
    @app_commands.describe(categories="Categories to choose from")
    async def new_question(self, interaction: discord.Interaction, categories: TriviaCategories):
        try:
            await interaction.response.defer()
            params = {
                "amount": 1,
                "category": categories.value
            }
            q = await self.get_question(params, interaction)
            if q == False:
                await interaction.followup.send("Error Retrieving Question")
                return
            await self.setup_question(interaction, q)
        except Exception as e:
            await interaction.followup.send("Error Retrieving Question")
            log_error(e)


    """
    :/scoreboard
    :Listens for the scoreboard command and returns guild scores
    """
    @app_commands.command(name="scoreboard", description="See the scoreboard")
    async def scoreboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(content=self.bot.get_scores(interaction.channel), ephemeral=False)

    async def question_completed(self, interaction: discord.Interaction, result_string, answer):
        try:
            self.controller.open_connection()
            self.controller.delete_question(interaction.message.id)
            self.controller.close_connection()
            content = self.edit_question_responses(interaction, result_string)
            await interaction.message.edit(content=f"{content} \n ## The correct answer was: {answer} \n **Question is now closed.**", view=None)
            #await interaction.followup.send(content=self.bot.get_scores(interaction.channel))
        except Exception as e:
            log_error(e)
            await interaction.channel.send("There was a problem closing the question")

    async def close_question(self, message: discord.Message):
        try:
            self.controller.open_connection()
            qid = self.controller.get_question_id(message.guild.id, message.channel.id, message.id)
            q = self.controller.get_object("question_data", qid)
            answer=q["correct_answer"]
            self.controller.delete_question(message.id)
            self.controller.close_connection()
            content = message.content
            await message.edit(content=f"{content} \n ## The correct answer was: {answer} \n **Question is now closed.**", view=None)
            #await interaction.followup.send(content=self.bot.get_scores(interaction.channel))
        except Exception as e:
            log_error(e)
            await message.channel.send("There was a problem closing the question")

    """Refresh open questions to the top."""
    @app_commands.command(name="refresh-questions", description="Refresh questions")
    async def refresh_questions(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("Refreshing....", ephemeral=True)
            self.bot.handle_delete = False
            await self.reset_questions(interaction.channel)
        except Exception as e:
            log_error(e)
            await interaction.followup.send("Cannot refresh questions", ephemeral=True)
        finally:
            self.bot.handle_delete = True

    async def background_refresh(self):
        while True:
            try:
                await self.refresh_tokens()
                await self.message_timeout()
            except Exception as e:
                log_error(e)
            finally:
                await asyncio.sleep(3600)

    async def message_timeout(self):
        self.controller.open_connection()
        try:
            messages = self.controller.fetch_all("message")
            for row, msg in messages.items():
                created = datetime.fromisoformat(msg["created"])
                dif = datetime.now()-created
                if dif > timedelta(hours=24):
                    channel = await self.bot.fetch_channel(msg["channel_id"])
                    message = await channel.fetch_message(msg["id"])
                    await self.close_question(message)
        except Exception as e:
            log_error(e)
        finally:
            self.controller.close_connection()

    async def refresh_tokens(self):
        try:
            self.controller.open_connection()
            tokens = self.controller.get_opentdb_tokens()
            now = datetime.now()
            for row, token in tokens.items():
                try:
                    guild = token["guild_id"]
                    channel = token["channel_id"]
                    current_token = token["token"]
                    lastr = datetime.fromisoformat(token["last_refreshed"])
                    rcount = token["refresh_count"]
                    timedif = now-lastr
                    if timedif > timedelta(hours=6):
                         await self.get_token(guild, channel, True)
                    elif timedif >= timedelta(hours=5):

                        #If token has been inactive for 48 hours, delete
                        if rcount >= 10:
                            await self.controller.delete_object("opentdb_tokens", (guild, channel), ("guild_id", "channel_id"))
                            continue

                        #Create loop to refresh the token, accounting for rate limiting.
                        retry = True
                        retry_count = 0
                        while retry:
                            result = requests.get(f"https://opentdb.com/api.php?amount=1&category=31&token={current_token}").json()
                            code = result["response_code"]
                            if code==0:
                                self.controller.update_object("opentdb_tokens", (guild, channel), ["last_refreshed", "refresh_count"], [now.isoformat(), rcount+1], ("guild_id", "channel_id"))
                                retry = False
                                break
                            elif code==3 or retry_count >= 2:
                                await self.get_token(guild, channel, True)
                                retry = False
                                break
                            elif code==5 and retry_count < 2:
                                retry_count+=1
                                await asyncio.sleep(5)
                                continue
                            else:
                                retry=False
                                break
                    else:
                        continue
                except Exception as e:
                    log_error(e)
        except Exception as e:
            log_error(e)
        finally:                
            self.controller.close_connection()


    async def get_token(self, guild_id, channel_id, force_new = False):
        try:
            self.controller.open_connection()
            if not force_new:
                token = self.controller.get_object("opentdb_tokens", (guild_id, channel_id), ("guild_id", "channel_id"))
            else:
                self.controller.delete_object("opentdb_tokens", (guild_id, channel_id), ("guild_id", "channel_id"))
                token = None
            if token is None:
                token_request = requests.get("https://opentdb.com/api_token.php?command=request")
                if token_request.json()['response_code']!=0:
                    raise Exception("Error getting token from API")
                else:
                    token = token_request.json()["token"]
                    timestamp = datetime.now().isoformat()
                    self.controller.insert_object("opentdb_tokens", ["guild_id", "channel_id", "token", "last_refreshed"], [guild_id, channel_id, token, timestamp])
                    return token
            else:
                timestamp = datetime.now().isoformat()
                self.controller.update_object("opentdb_tokens", (guild_id, channel_id), ["last_refreshed", "refresh_count"], [timestamp, 0], ("guild_id", "channel_id"))
                return token["token"]
        except Exception as e:
            log_error(e)
        finally:
            self.controller.close_connection()
    """
    :Actual get request for the questions
    """
    async def get_question(self, params, interaction: discord.Interaction):
        retry = True
        retry_count = 0
        url = "https://opentdb.com/api.php"
        token = await self.get_token(interaction.guild.id, interaction.channel_id)
        params["token"] = token
        try:
            await interaction.followup.send("Getting question....")
            msg = await interaction.original_response()
            self.controller.open_connection()
                #Insert Message data
            created = datetime.now().isoformat()
            self.controller.insert_object("message", ["id", "channel_id", "guild_id", "created"],[msg.id, msg.channel.id, msg.guild.id, created], (msg.id, msg.channel.id))
            


            while retry:
                if retry_count>=2:
                    return False
                response =  requests.get(url, params=params)
                result = response.json()
                self.controller.update_object("opentdb_tokens", (interaction.guild.id, interaction.channel.id), ["refresh_count"], [0], ("guild_id", "channel_id"))
                code = result['response_code']
                if code==0:
                    return result['results'][0]
                elif code == 1 or code == 2:
                    return False
                elif code == 3:
                    token = await self.get_token(interaction.guild.id, interaction.channel.id, True)
                elif code == 4:
                    await interaction.followup.send("You have had all the questions found in this category. Please choose another category or reset the session", ephemeral=True)
                elif code == 5:
                    await msg.edit(content="Waiting for question from server... Please wait...")
                    await asyncio.sleep(5)
                else:
                    return False
        except Exception as e:
            log_error(e)
        finally:
            self.controller.close_connection()
                
        
    """
    :Setup method for questions
    :Accepts the interaction and question
    :Creates database objects to track open questions
    :Sends the question to the channel
    """
    async def setup_question(self, interaction: discord.Interaction, q):
        try:
            #Get Non-Bot members of the channel
            members = [member for member in interaction.channel.members if not member.bot]

            #Create user string for tracking answers
            user_string = "***"
            for member in members:
                user_string += member.name + ": Not answered, "
            user_string=user_string[:-2] + "***\n"

            try:
                #Create new question view and send the question and retrieve the msg info from discord
                msg = await interaction.original_response()
                await msg.edit(content=f"@everyone \n **Category: {html.unescape(q['category'])} \n Difficulty: {q['difficulty']}**\n {user_string}# {html.unescape(q['question'])}",view=question_view(copy.deepcopy(q), members, self.question_completed, self.user_answered))
                
            except Exception as e:
                log_error(e)
                await interaction.followup.send("Error with question setup. Please try again later." + e, ephemeral=True)
                return
                
            try:
                self.controller.open_connection()
                #Insert Question Data
                question_id=self.controller.insert_object("question_data", ["question", "correct_answer", "category", "difficulty", "message_id", "channel_id"], [q['question'], q['correct_answer'], q['category'], q['difficulty'], msg.id, msg.channel.id])

                #Add list to incorrect_answers table
                for incorrect in q['incorrect_answers']:
                    self.controller.insert_object("incorrect_answers", ["label", "question_id"], [incorrect, question_id])

                #Add members to track answers
                for member in members:
                    self.controller.insert_object("user_answers", ["user_id", "question_id"], [member.id, question_id])

            except Exception as e:
                log_error(e)
                await interaction.followup.send("Error saving question data to database. Deleting question", ephemeral=True)
                await msg.delete()
                self.controller.conn.rollback()
            finally:
                self.controller.close_connection()
        except Exception as e:
            log_error(e)


    """
    :Callback to handle when a user answers a question (button press)
    """
    async def user_answered(self, interaction: discord.Interaction, btn, answer, all_answered):
        try:
            self.controller.open_connection()
            correct = btn.correct
            difficulty = btn.difficulty

            #If user answers correct, update the score
            if correct:
                result_string = ": Correct"
                response_string = f"You were correct! +1 to your score!"
                
            else:  
                result_string = ": Incorrect"
                response_string = f"You were incorrect! -1 to your score! The correct answer was: {answer}\n Better luck next time!"
            try:
                
                #Handle updating the open question and update score. If all answered, skip updating question as data will be deleted in a followup callback
                q_id = self.controller.get_question_id(interaction.guild.id, interaction.channel.id, interaction.message.id) 
                if not all_answered:
                    self.controller.update_object("user_answers", (interaction.user.id, q_id), ["answered", "correct"], [True, correct], ("user_id", "question_id"))
                self.controller.update_score(interaction.guild.id, interaction.user.id, 1 if correct else -1)
            except Exception as e:
                log_error(e)
                await interaction.followup.send("Error recording your answer.", ephemeral=True)

            #Edit the message to show status of users for question
            content = self.edit_question_responses(interaction, result_string)
            await interaction.message.edit(content=content)
            await interaction.response.send_message(response_string, ephemeral=True)
        except Exception as e:
            log_error(e)
        finally:
            self.controller.close_connection()
        
    def edit_question_responses(self, interaction: discord.Interaction, result_string):
        user_string = interaction.message.content.split("***\n")[0]
        user_string=user_string.replace(interaction.user.name + ": Not answered", interaction.user.name + result_string)
        content = user_string + "***\n" + interaction.message.content.split("***\n")[1]
        return content
        

    """
    :Handles recreating messages after bot restart. May need to evaluate if bot use grows as this will be an extensive task
    :Unsure of how else to help make this faster.
    """
    async def reset_questions_back(self, channel_refresh=None):
        try:
            #Open database and get a list of open questions across all guilds
            self.controller.open_connection()
            open_questions = self.controller.fetch_open_questions(channel_refresh)
            
            #Iterate through guilds
            for gld, gq in open_questions.items():

                #Iterate through channels
                for chnl, messages in gq.items():

                    #Iterate through each message
                    for msg, question in messages.items():

                        #Get actual channel and message from discord
                        channel = await self.bot.fetch_channel(chnl)
                        message = await channel.fetch_message(msg)

                        #Recreate members who have not answered the question yet
                        members = [member for member in channel.members if member!=self.bot.user and member.id in question['user_answers'] and not question['user_answers'][member.id]['answered']]

                        #Recreate view object and send message to channel
                        new_message = await channel.send(content=message.content, view=question_view(question['question_data'], members, self.question_completed, self.user_answered))

                        #Delete old message and update database to reflect the new message id
                        self.controller.update_object("message", (msg, channel.id), ["id"], [new_message.id], ("id", "channel_id"))
                        await message.delete()
        except Exception as e:
            log_error(e)
        finally:
            self.controller.close_connection()

    async def reset_questions(self, channel_refresh=None):
        try:
            self.controller.open_connection()

            # Fetch open questions across all guilds
            open_questions = self.controller.fetch_open_questions(channel_refresh)

            # Create tasks for recreating messages in parallel
            tasks = []
            for guild_id, guild_questions in open_questions.items():
                for channel_id, channel_messages in guild_questions.items():
                    for message_id, question_data in channel_messages.items():
                        tasks.append(self.recreate_message(guild_id, channel_id, message_id, question_data))

            # Execute tasks concurrently
            await asyncio.gather(*tasks)

        except Exception as e:
            log_error(e)
        finally:
            self.controller.close_connection()

    async def recreate_message(self, guild_id, channel_id, message_id, question_data):
        try:
            # Get actual channel and message from Discord
            try:
                channel = await self.bot.fetch_channel(channel_id)
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                # Message does not exist, delete it from the database
                self.controller.delete_object("message", (message_id, channel_id), ["id", "channel_id"])
                log_warning("Message was deleted from database")
                return

            # Recreate members who have not answered the question yet
            members = [member for member in channel.members if member != self.bot.user and member.id in question_data['user_answers'] and not question_data['user_answers'][member.id]['answered']]

            # Recreate view object and send message to channel
            if "@everyone" in message.content:
                content = message.content.split("@everyone \n ")[1]
            else:
                content = message.content
            new_message = await channel.send(content=content, view=question_view(question_data['question_data'], members, self.question_completed, self.user_answered))

            # Delete old message and update database to reflect the new message id
            self.controller.update_object("message", (message_id, channel_id), ["id"], [new_message.id], ("id", "channel_id"))
            await message.delete()
        except Exception as e:
            log_error(e)

"""
:Creates a discord view to handle the presentation of questions
"""
class question_view(discord.ui.View):
    def __init__(self, question, members, completed_callback, user_callback):

        #Set callbacks
        self.completed_callback=completed_callback
        self.user_callback = user_callback
        self.callback=self.answer_callback

        #set question data and shuffle answers
        self.members = members
        self.question = question['question']
        self.answer = question['correct_answer']
        self.options = question['incorrect_answers'].copy()
        self.options.append(self.answer)
        random.shuffle(self.options)
        super().__init__(timeout=None)

        #Create a button for each answer
        for option in self.options:
            button = answer_button(label=html.unescape(option), correct=(option==self.answer), difficulty=question['difficulty'])
            self.add_item(button)

    """
    Handles the initial callback
    """
    async def answer_callback(self, interaction: discord.Interaction, button):
        #If the member is not in the list, they have already answered
        if interaction.user not in self.members:
            await interaction.response.send_message("You have already answered this question", ephemeral=True)
            return
    
        #Run the main callback
        await self.user_callback(interaction, button, self.answer, all_answered=(self.members)==0)

        #Set result string
        if button.correct:          
            result_string = ": Correct"
        else:
            result_string = ": Incorrect"

        #Remove the user from unanswered list
        self.members.remove(interaction.user)

        #Handles if all users answered
        if len(self.members)==0:
            await self.completed_callback(interaction, result_string, self.answer)
            
    
"""
Handles button interaction and displaying of answers
"""
class answer_button(discord.ui.Button):
    def __init__(self, label, correct, difficulty):
        #Parse difficulty
        if difficulty == "easy":
            self.difficulty = 1
        elif difficulty == 'medium':
            self.difficulty = 2
        elif difficulty == 'hard':
            self.difficulty = 3
        else:
            self.difficulty = 1

        #Store if this answer is correct
        self.correct = correct
        
        super().__init__(label=label, style=discord.ButtonStyle.primary)
    async def callback(self, interaction):
        if self.view.callback:
            await self.view.callback(interaction, self)
