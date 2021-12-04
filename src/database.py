import sqlite3
from sqlite3 import Error

class FplDatabase:
    def __init__(self):
        sql_to_create_account_table = '''CREATE TABLE IF NOT EXISTS fplIDS (
            discord_id integer PRIMARY KEY,
            fpl_id integer NOT NULL
            )
            '''
        try:
            # create connection
            self.conn = sqlite3.connect('database.db')

            c = self.conn.cursor()
            c.execute(sql_to_create_account_table)

        except Error as e:
            print(e)

    def set_fpl_id(self, discord_id, fpl_id):

        cur = self.conn.cursor()

        # This SQL will delete a record and replace it if it is present
        sql_to_set_fpl_id = '''REPLACE INTO fplIDS(discord_id, fpl_id)
                                           VALUES(?,?)
                '''
        cur.execute(sql_to_set_fpl_id, (discord_id, fpl_id))
        self.conn.commit()

    def find_fpl_id(self, discord_id):
        sql_to_find_fpl_id = 'SELECT * FROM fplIDS WHERE discord_id = ?'

        cur = self.conn.cursor()

        cur.execute(sql_to_find_fpl_id, (discord_id,))
        try:
            fpl_id = cur.fetchall()[0]
        except:
            fpl_id = None
        return fpl_id