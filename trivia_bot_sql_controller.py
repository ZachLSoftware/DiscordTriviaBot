import sqlite3
import os
from sql_query_commands import *

class SQLiteController():
    
    def __init__(self, db="test.sqlite"):
        if os.path.isfile(db):
            try:
                self.conn = sqlite3.connect(db)
                self.cursor = self.conn.cursor()
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

    def get_object(self, id):
        command = '''SELECT * FROM user WHERE id = ?'''
        parameters = (id)

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
        if (id is None or not self.check_if_exists(table, id)):
            column_names = ', '.join(columns)
            placeholders = ', '.join(['?' for _ in values])

            command = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
            self.cursor.execute(command, values)
            self.conn.commit()
            last_inserted_id = self.cursor.lastrowid
            return last_inserted_id

    def check_if_exists(self, table, id):
        if isinstance(id,tuple):
            self.cursor.execute(f'SELECT 1 FROM {table} WHERE guild_id = ? AND user_id = ?', id)
        else:
            self.cursor.execute(f'SELECT 1 FROM {table} WHERE id = ?', (id,))
        return self.cursor.fetchone() is not None
    
    def fetch_open_questions(self):
        query = '''
            SELECT
                m.id AS message_id,
                q.content AS question_content,
                q.answer AS question_answer,
                q.category AS question_category,
                q.difficulty AS question_difficulty,
                w.label AS wrong_answer_label,
                ua.user_id AS user_id,
                ua.answered AS user_answered,
                ua.correct AS user_correct,
                m.channel_id AS channel_id
            FROM
                message m
                INNER JOIN question q ON m.id = q.message_id
                LEFT JOIN wrong_answers w ON q.id = w.question_id
                LEFT JOIN user_answers ua ON q.id = ua.question_id
        '''
        self.cursor.execute(query)
        result = self.cursor.fetchall()

        messages_data = {}
        for row in result:
            message_id = row[0]  # accessing tuple element by index
            if message_id not in messages_data:
                messages_data[message_id] = {
                    'question': {
                        'content': row[1],
                        'answer': row[2],
                        'category': row[3],
                        'difficulty': row[4]
                    },
                    'wrong_answers': [],
                    'user_answers': {}
                }

            if row[5] is not None:  # Check for NULL value
                messages_data[message_id]['wrong_answers'].append(row[5])

            if row[6] is not None:  # Check for NULL value
                messages_data[message_id]['user_answers'][row[6]] = {
                    'answered': row[7],
                    'correct': row[8]
                }

        return messages_data

#sql=SQLiteController()
