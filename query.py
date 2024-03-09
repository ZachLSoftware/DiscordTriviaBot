import sqlite3

conn = sqlite3.connect("test.sqlite")
curs = conn.cursor()
query = '''UPDATE question_data
    SET message_id = 1215435928592580659
    where
    id = 1'''

curs.execute(query)