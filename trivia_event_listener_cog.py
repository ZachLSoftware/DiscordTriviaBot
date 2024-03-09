import discord
from discord.ext import commands
from trivia_bot_sql_controller import SQLiteController
import asyncio

class EventManagementCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
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
        await self.bot.add_cog(self)


    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.bot.insert_guild_data([guild])
        self.controller.user_remove_check()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        try:
            self.controller.open_connection()
            self.controller.delete_object("guild", guild.id)
            await asyncio.sleep(1)
            self.controller.user_remove_check()
        except Exception as e:
            print(e)
        finally:
            self.controller.close_connection()

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.TextChannel):
        self.controller.open_connection()
        self.controller.insert_object("channel", ["id", "channel_name", "guild_id"], (channel.id, channel.name, channel.guild.id), (channel.id, channel.guild.id))
        for member in channel.members:
            if not member.bot:
                self.controller.insert_object("scorecard", ["user_id", "channel_id","guild_id"], [member.id, channel.id, channel.guild.id], (member.id, channel.id))
        self.controller.close_connection()

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.TextChannel):
        self.controller.open_connection()
        self.controller.delete_object("channel", (channel.id, channel.guild.id), ["id", "guild_id"])
        for member in channel.members:
            self.controller.user_remove_check()
        self.controller.close_connection()

    
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.TextChannel, after: discord.TextChannel):
        if before.name == "general":
            return
        perm_before = await self.bot.is_bot_allowed(before)
        perm_after = await self.bot.is_bot_allowed(after)
        self.controller.open_connection()
        try:
            if not perm_before and perm_after:
                channel = after
                
                self.controller.insert_object("channel", ["id", "channel_name", "guild_id"], (channel.id, channel.name, channel.guild.id), (channel.id, channel.guild.id))
                for member in channel.members:
                    if not member.bot:
                        self.controller.insert_object("scorecard", ["user_id", "channel_id","guild_id"], [member.id, channel.id, channel.guild.id], (member.id, channel.id))
                
            elif perm_before and not perm_after:
                self.controller.delete_object("channel", (after.id, after.guild.id), ["id", "guild_id"])

            if perm_before and perm_after and (before.name != after.name):
                self.controller.update_object("channel", (after.id, after.guild.id), ["channel_name"], [after.name], ("id","guild_id"))
            
            if before.members!=after.members:
                for member in list(set(before.members) | set(after.members)):
                    if not member.bot:
                        await self.check_permission_change(after, member)
        except Exception as e:
            print(e)
        finally:
            self.controller.close_connection()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            self.controller.open_connection()
            self.controller.insert_object("user", ["id", "username"],[member.id, member.name], member.id)
            for channel in member.guild.channels:
                if member in channel.members:
                    self.controller.insert_object("scorecard", ["user_id", "channel_id","guild_id"], [member.id, channel.id, channel.guild.id], (member.id, channel.id))
         
        except Exception as e:
            print(e)
        finally:
            self.controller.close_connection()

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        try:
            self.controller.open_connection()
            self.controller.delete_object("user", member.id)
        except Exception as e:
            print(e)
        finally:
            self.controller.close_connection()

    async def check_permission_change(self, channel: discord.Member, member: discord.TextChannel):
        try:
            # Fetch channel IDs where the member currently has permissions
            #allowed_channel_ids = [channel.id for channel in after.guild.channels if await self.bot.is_user_allowed(channel, after.id)]
            allowed = await self.bot.is_user_allowed(channel, member.id)
            # Fetch channel IDs associated with the member from the scorecard table
            query = "SELECT channel_id FROM scorecard WHERE user_id = ? AND guild_id = ? AND channel_id = ?"
            self.controller.cursor.execute(query, (member.id, member.guild.id, channel.id))
            scorecard = self.controller.cursor.fetchone()

            # Delete records for channels where the member no longer has permissions
            if scorecard is not None and not allowed:
                self.controller.delete_object("scorecard", (member.id, channel.id, member.guild.id), ["user_id", "channel_id", "guild_id"])

            # Insert records for new channels where the member now has permissions
            if scorecard is None and allowed:
                self.controller.insert_object("scorecard", ["user_id", "channel_id", "guild_id"], [member.id, channel.id, member.guild.id])

        except Exception as e:
            print(e)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        try:
            self.controller.open_connection()
            self.controller.delete_object("message", (message.id, message.channel.id), ["id", "channel_id"])
        except Exception as e:
            print(e)
        finally:
            self.controller.close_connection()