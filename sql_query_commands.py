import sqlite3

def initialize(connection: sqlite3.Connection):
    init_statements = [
        '''CREATE TABLE IF NOT EXISTS guild
        ( 
            id INT PRIMARY KEY NOT NULL,
            guild_name TEXT NOT NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS channel
        (
            id INT PRIMARY KEY NOT NULL,
            channel_name TEXT NOT NULL,
            guild_id INT,
            FOREIGN KEY(guild_id) REFERENCES guild(id)
        )''',
        '''CREATE TABLE IF NOT EXISTS user
        (
            id INT PRIMARY KEY NOT NULL,
            username TEXT NOT NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS scorecard
        (
            guild_id INT NOT NULL,
            user_id INT NOT NULL,
            score INT DEFAULT 0,
            PRIMARY KEY (guild_id, user_id),
            FOREIGN KEY(guild_id) REFERENCES guild(id),
            FOREIGN KEY(user_id) REFERENCES user(id)
        )''',
        '''CREATE TABLE IF NOT EXISTS message
        (
            id INT PRIMARY KEY NOT NULL,
            channel_id INT,
            FOREIGN KEY(channel_id) REFERENCES channel(id)
        )''',
        '''CREATE TABLE IF NOT EXISTS question
        (
            id INT PRIMARY KEY,
            content TEXT,
            answer TEXT,
            category TEXT,
            difficulty TEXT,
            message_id INT,
            FOREIGN KEY(message_id) REFERENCES message(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS wrong_answers
        (
            id INT PRIMARY KEY,
            label CHAR(100),
            question_id INT,
            FOREIGN KEY(question_id) REFERENCES question(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS user_answers
        (
            id INT PRIMARY KEY,
            user_id INT NOT NULL,
            question_id INT NOT NULL,
            answered BOOLEAN default FALSE,
            correct BOOLEAN default FALSE,
            FOREIGN KEY(user_id) REFERENCES user(id),
            FOREIGN KEY(question_id) REFERENCES question(id) ON DELETE CASCADE
        );'''
        ]

    for statement in init_statements:
        connection.execute(statement)