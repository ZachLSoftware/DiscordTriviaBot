import sqlite3

def initialize(connection: sqlite3.Connection):
    init_statements = [
        '''CREATE TABLE IF NOT EXISTS guild
        ( 
            id INTEGER PRIMARY KEY NOT NULL,
            guild_name TEXT NOT NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS channel
        (
            id INTEGER NOT NULL,
            channel_name TEXT NOT NULL,
            guild_id INTEGER NOT NULL,
            PRIMARY KEY (id, guild_id),
            FOREIGN KEY(guild_id) REFERENCES guild(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS user
        (
            id INTEGER PRIMARY KEY NOT NULL,
            username TEXT NOT NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS scorecard
        (
            user_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            score INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, channel_id),
            FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE,
            FOREIGN KEY(channel_id, guild_id) REFERENCES channel(id, guild_id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS message
        (
            id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            PRIMARY KEY (id, channel_id),
            FOREIGN KEY(channel_id, guild_id) REFERENCES channel(id, guild_id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS question_data
        (
            id INTEGER PRIMARY KEY,
            question TEXT,
            correct_answer TEXT,
            category TEXT,
            difficulty TEXT,
            message_id INTEGER,
            channel_id INTEGER,
            FOREIGN KEY(message_id, channel_id) REFERENCES message(id, channel_id) ON UPDATE CASCADE ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS incorrect_answers
        (
            id INTEGER PRIMARY KEY,
            label CHAR(100),
            question_id INTEGER,
            FOREIGN KEY(question_id) REFERENCES question_data(id) ON DELETE CASCADE
        )''',
        '''CREATE TABLE IF NOT EXISTS user_answers
        (
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answered BOOLEAN default FALSE,
            correct BOOLEAN default FALSE,
            PRIMARY KEY (user_id, question_id),
            FOREIGN KEY(user_id) REFERENCES user(id),
            FOREIGN KEY(question_id) REFERENCES question_data(id) ON DELETE CASCADE
        );''',
        '''CREATE TABLE IF NOT EXISTS opentdb_tokens
        (
            guild_id INTEGER,
            channel_id INTEGER,
            token TEXT,
            last_refreshed TEXT,
            refresh_count INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, channel_id),
            FOREIGN KEY (channel_id, guild_id) REFERENCES channel(id, guild_id) ON DELETE CASCADE
        );'''
        ]

    for statement in init_statements:
        connection.execute(statement)