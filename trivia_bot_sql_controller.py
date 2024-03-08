import sqlite3
import aiosqlite
import os
from sql_query_commands import *

class SQLiteController():
    
    def __init__(self, db="trivia_bot_db.sqlite"):
        if os.path.isfile(db):
            try:
                self.db = db
                self.pragma = 'PRAGMA foreign_keys = ON'
                self.conn = sqlite3.connect(self.db)
                self.cursor = self.conn.cursor()
                self.conn.execute('PRAGMA foreign_keys = ON')
                self.initialize_db()
                self.conn.close()
                print("done")
            except Exception as e:
                print(e)


    """Initialize database"""   
    def initialize_db(self):
        initialize(self.conn)

    """
    :Handle opening database and setting foreign-keys
    """
    def open_connection(self):
        self.conn = sqlite3.connect(self.db)
        self.conn.execute('PRAGMA foreign_keys = ON')
        self.cursor = self.conn.cursor()
    
    """
    :Commit and close the database
    """
    def close_connection(self):
        self.conn.commit()
        self.conn.close()


    """
    :Get the score of a user
    """
    def get_score(self, guild_id, user_id):
        command = '''SELECT * FROM scorecard WHERE guild_id = ? and user_id = ?'''
        parameters = (guild_id, user_id)

        try:
            self.cursor.execute(command, parameters)
            row = self.cursor.fetchone()
            if row is None:
                return None
            columns = [desc[0] for desc in self.cursor.description]
            return dict(zip(columns, row))

        
        except Exception as e:
            print(e)
            return None
        
    """
    :Get the guild scores
    """
    def get_guild_scores(self, guild_id):
        try:
            command="""SELECT * FROM scorecard WHERE guild_id = ?"""
            self.cursor.execute(command, (guild_id,))
            scores = {}
            rows = self.cursor.fetchall()
            for row in rows:
                if row is None:
                    return None
                columns = [desc[0] for desc in self.cursor.description]
                temp = dict(zip(columns, row))
                scores[temp["user_id"]]=temp
            return scores
        
        except Exception as e:
            print(e)
            return None
    
    """
    :Update a user score
    """
    def update_score(self, guild_id, user_id, score_change):
        score = self.get_score(guild_id, user_id)
        if score is not None:
            curr = score['score']+score_change

            command = '''UPDATE scorecard
                        SET score = ?
                        WHERE guild_id = ? AND user_id = ?'''
            
            parameters = (curr, guild_id, user_id)
            self.cursor.execute(command, parameters)


    """
    :Update row
    :Needs a table name, ID, columns to update, values for columns, and if composite key, id_columns
    """
    def update_object(self, table, id, columns: list, values: list, id_columns: tuple = None):
            set_str=", ".join([f"{column} = ?" for column in columns])
            
            
            if isinstance(id, tuple):
                where_str = " AND ".join([f"{id_column} = ?" for id_column in id_columns])
                values.extend(id)
            else:
                where_str = "id = ?"
                values.append(id)

            query = f'''UPDATE {table}
                        SET {set_str}
                        WHERE {where_str}'''
            self.cursor.execute(query, values)

    def get_question_id(self, guild_id, channel_id, messaged_id):
        command = '''SELECT q.id
                    FROM question_data q
                    JOIN message m ON q.message_id = m.id
                    JOIN channel c ON m.channel_id = c.id
                    WHERE m.id = ? AND m.channel_id = ? AND c.guild_id = ?;
                     '''
        row = self.cursor.execute(command, (messaged_id, channel_id, guild_id)).fetchone()
        return row[0]


    """
    :Get object from ID
    """
    def get_object(self, table, id, id_columns: tuple = None):
        if isinstance(id, tuple):
            where_str = " AND ".join([f"{id_column} = ?" for id_column in id_columns])
            parameters = id
        else:
            where_str = "id = ?"
        command = f'''SELECT * FROM {table} WHERE {where_str}'''
        parameters = (id,)

        try:
            self.cursor.execute(command, parameters)
            row = self.cursor.fetchone()
            if row is None:
                return None
            columns = [desc[0] for desc in self.cursor.description]
            return dict(zip(columns, row))
        
        except Exception as e:
            print(e)
            return None
    
    """
    :Insert new object
    :Tests if object already exists
    """
    def insert_object(self, table: str, columns: list, values: list, id=None):
        try:
            if (id is None or not self.check_if_exists(table, id)):
                column_names = ', '.join(columns)
                placeholders = ', '.join(['?' for _ in values])

                command = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
                self.cursor.execute(command, values)
                last_inserted_id = self.cursor.lastrowid
                return last_inserted_id
        except Exception as e:
            print(e)

    """
    :Create async connection
    """
    async def start_sync_inserts(self):
        connection = await aiosqlite.connect(self.db)
        await connection.execute(self.pragma)
        return connection
    
    """
    :Close async connection
    """
    async def close_async(self, connection: aiosqlite.Connection):
        await connection.commit()
        await connection.close()


    """
    :Insert objects async
    """
    async def insert_object_async(self, table: str, columns: list, values: list, connection: aiosqlite.Connection, id=None):
        try:           
            exists = await self.check_if_exists_async(table, id, connection)
            if (id is None or not exists):
                column_names = ', '.join(columns)
                placeholders = ', '.join(['?' for _ in values])

                command = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
                cursor = await connection.execute(command, values)
                last_inserted_id = cursor.lastrowid
                return last_inserted_id
        except Exception as e:
            print(e)


    """
    :Check if object exists (Async version)
    """
    async def check_if_exists_async(self, table, id, connection: aiosqlite.Connection):
        try:
            if isinstance(id,tuple):
                match table:
                    case "channel":
                        key1 = "id"
                        key2 = "guild_id"
                    case "message":
                        key1="id"
                        key2="channel_id"
                    case "scorecard":
                        key1="guild_id"
                        key2="user_id"
                    case "user_answers":
                        key1="user_id"
                        key2="question_id"
                    case _:
                        pass
                
                result = await connection.execute(f'SELECT 1 FROM {table} WHERE {key1} = ? AND {key2} = ?', id)
            else:
                result = await connection.execute(f'SELECT 1 FROM {table} WHERE id = ?', (id,))
            return (await result.fetchone()) is not None
        except Exception as e:
            print(e)
            return False
        

    """
    :Standard check
    """
    def check_if_exists(self, table, id):

        if isinstance(id,tuple):
            match table:
                case "channel":
                    key1 = "id"
                    key2 = "guild_id"
                case "message":
                    key1="id"
                    key2="channel_id"
                case "scorecard":
                    key1="guild_id"
                    key2="user_id"
                case "user_answers":
                    key1="user_id"
                    key2="question_id"
                case _:
                    pass
            self.cursor.execute(f'SELECT 1 FROM {table} WHERE {key1} = ? AND {key2} = ?', id)
        else:
            self.cursor.execute(f'SELECT 1 FROM {table} WHERE id = ?', (id,))
        return self.cursor.fetchone() is not None
    

    """
    :Deletes a message/question from the database
    """
    def delete_question(self, message_id):
        command = '''DELETE FROM message WHERE id = ?'''
        self.cursor.execute(command, (message_id,))
    

    """
    :Fetch all open questions
    """
    def fetch_open_questions(self):
        query = '''
            SELECT
                g.id AS guild_id,
                c.id AS channel_id,
                m.id AS message_id,
                q.id AS question_data_id,
                q.question AS question_data_question,
                q.correct_answer AS question_data_answer,
                q.category AS question_data_category,
                q.difficulty AS question_data_difficulty
                
            FROM
                message m
                INNER JOIN channel c ON m.channel_id = c.id
                INNER JOIN guild g ON c.guild_id = g.id
                INNER JOIN question_data q ON m.id = q.message_id
        '''

        self.cursor.execute(query)
        result = self.cursor.fetchall()

        guilds_data = {}
        for row in result:
            guild_id = row[0]
            channel_id = row[1]
            message_id = row[2]
            question_id = row[3]

            if guild_id not in guilds_data:
                guilds_data[guild_id] = {}

            if channel_id not in guilds_data[guild_id]:
                guilds_data[guild_id][channel_id] = {}

            if message_id not in guilds_data[guild_id][channel_id]:
                guilds_data[guild_id][channel_id][message_id] = {
                    'question_data': {
                        'id': row[3],
                        'question': row[4],
                        'correct_answer': row[5],
                        'category': row[6],
                        'difficulty': row[7],
                        'incorrect_answers': []
                    },
                    'user_answers': {}
                }

            incorrect_answers = self.cursor.execute("select label from incorrect_answers where question_id = ?", (question_id,)).fetchall()
            for answer in incorrect_answers:
                guilds_data[guild_id][channel_id][message_id]['question_data']['incorrect_answers'].append(answer[0])
            
            user_answers = self.cursor.execute("select user_id, answered, correct from user_answers where question_id = ?", (question_id,)).fetchall()
            for ua in user_answers:
                guilds_data[guild_id][channel_id][message_id]['user_answers'][ua[0]] = {"answered": bool(ua[1]), "correct": bool(ua[2])}

        return guilds_data

#sql=SQLiteController()
