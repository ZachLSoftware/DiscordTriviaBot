import sqlite3
import os
from sql_query_commands import *

class SQLiteController():
    
    def __init__(self, db="test.sqlite"):
        if os.path.isfile(db):
            try:
                self.conn = sqlite3.connect(db)
                self.cursor = self.conn.cursor()
                self.conn.execute('PRAGMA foreign_keys = ON')
                self.initialize_db()
                print("done")
            except Exception as e:
                print(e)
        
    def initialize_db(self):
        initialize(self.conn)


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
        
    def update_score(self, guild_id, user_id, score_change):
        score = self.get_score(guild_id, user_id)
        if score is not None:
            curr = score['score']+score_change

            command = '''UPDATE scorecard
                        SET score = ?
                        WHERE guild_id = ? AND user_id = ?'''
            
            parameters = (curr, guild_id, user_id)
            self.cursor.execute(command, parameters)
            self.conn.commit()

    def update_object(self, table, id, columns: list, values: list):
            set_str=", ".join([f"{column} = ?" for column in columns])
            

            
            if isinstance(id, tuple):
                where_str = "user_id = ? AND question_id = ?"
                values.extend(id)
            else:
                where_str = "id = ?"
                values.append(id)

            query = f'''UPDATE {table}
                        SET {set_str}
                        WHERE {where_str}'''
            self.cursor.execute(query, values)
            self.conn.commit()

    def get_question_id(self, guild_id, channel_id, messaged_id):
        command = '''SELECT q.id
                    FROM question_data q
                    JOIN message m ON q.message_id = m.id
                    JOIN channel c ON m.channel_id = c.id
                    WHERE m.id = ? AND m.channel_id = ? AND c.guild_id = ?;
                     '''
        row = self.cursor.execute(command, (messaged_id, channel_id, guild_id)).fetchone()
        return row[0]

    def get_object(self, table, id):
        command = f'''SELECT * FROM {table} WHERE id = ?'''
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
        
    def insert_object(self, table: str, columns: list, values: list, id=None):
        try:
            if (id is None or not self.check_if_exists(table, id)):
                column_names = ', '.join(columns)
                placeholders = ', '.join(['?' for _ in values])

                command = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
                self.cursor.execute(command, values)
                self.conn.commit()
                last_inserted_id = self.cursor.lastrowid
                return last_inserted_id
        except Exception as e:
            print(e)

    def check_if_exists(self, table, id):
        if isinstance(id,tuple):
            self.cursor.execute(f'SELECT 1 FROM {table} WHERE guild_id = ? AND user_id = ?', id)
        else:
            self.cursor.execute(f'SELECT 1 FROM {table} WHERE id = ?', (id,))
        return self.cursor.fetchone() is not None
    
    def delete_question(self, message_id):
        command = '''DELETE FROM message WHERE id = ?'''
        self.cursor.execute(command, (message_id,))
        self.conn.commit()
    
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
