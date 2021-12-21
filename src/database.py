import sqlite3
from sqlite3 import Error

class FplDatabase:
    def __init__(self):
        sql_to_create_account_table = '''CREATE TABLE IF NOT EXISTS fplIDS (
            discord_id integer PRIMARY KEY,
            fpl_id integer NOT NULL
            )
            '''
        sql_to_create_gambling_accounts_table = '''CREATE TABLE IF NOT EXISTS gamblingAccounts (
            discord_id integer PRIMARY KEY,
            fpl_coins integer NOT NULL
        )
        '''
        sql_to_create_betting_records_table = '''CREATE TABLE IF NOT EXISTS bets(
            bet_id INTEGER PRIMARY KEY,
            discord_id INTEGER NOT NULL,
            coins_bet INTEGER NOT NULL,
            potential_coins INTEGER NOT NULL,
            selected_bet_condition TEXT NOT NULL,
            selected_bet_type TEXT NOT NULL,
            has_ended INTEGER NOT NULL,
            was_correct INTEGER
        )
    
        '''
        try:
            # create connection
            self.conn = sqlite3.connect('database.db')

            c = self.conn.cursor()
            c.execute(sql_to_create_account_table)
            c.execute(sql_to_create_gambling_accounts_table)
            c.execute(sql_to_create_betting_records_table)

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
            fpl_id = cur.fetchall()[0][1]
        except:
            fpl_id = None
        return fpl_id

    def create_gambling_account(self, discord_id, starting_cash:int = 100):
        sql_to_create_gambling_account = '''INSERT INTO gamblingAccounts VALUES (?,?)'''
        new_account = (discord_id, starting_cash)

        cur = self.conn.cursor()

        cur.execute(sql_to_create_gambling_account, new_account)
        self.conn.commit()

    def find_account_money(self, discord_id) -> int:
        sql_to_find_account = 'SELECT * FROM gamblingAccounts WHERE discord_id = ?'

        cur = self.conn.cursor()

        cur.execute(sql_to_find_account, (discord_id,))
        try:
            account = cur.fetchall()
            account_money = account[0][1]
        except:
            self.create_gambling_account(discord_id)
            account_money = 100
        return account_money

    def add_account_money(self, discord_id: int, amount: int) -> int:
        """
        Add an amount of money to a certain account
        :param discord_id: Discord id of account
        :param amount: Amount to change money amount by
        :return: New money amount
        """
        money = self.find_account_money(discord_id)
        new_money = money + amount
        if new_money < 0:
            new_money = 0

        sql_to_update = '''UPDATE gamblingAccounts
                                       SET fpl_coins = ?
                                       WHERE discord_id = ?
                    '''

        cur = self.conn.cursor()
        cur.execute(sql_to_update, (new_money, discord_id))

        self.conn.commit()

        return new_money

    def create_bet(self,
                   discord_id: int,
                   coins_bet: int,
                   potential_coins: int,
                   selected_bet_condition: str,
                   selected_bet_type: str):
        bet=(discord_id,
             coins_bet,
             potential_coins,
             selected_bet_condition,
             selected_bet_type,
             0)

        sql_to_update = '''INSERT INTO bets(discord_id,
        coins_bet,potential_coins,
        selected_bet_condition,
        selected_bet_type,has_ended)
        VALUES (?,?,?,?,?,?)'''

        cur = self.conn.cursor()
        cur.execute(sql_to_update, bet)
        self.conn.commit()

        self.add_account_money(discord_id, -coins_bet)

    def mark_bet_finished(self, bet_id, was_correct):
        was_correct = int(was_correct)
        sql_to_update = '''UPDATE bets
        SET has_ended=1, was_correct=?
        WHERE bet_id = ?
        '''

        cur = self.conn.cursor()
        cur.execute(sql_to_update, (was_correct, bet_id))
        self.conn.commit()


    def find_all_unfinished_bets(self):
        sql_to_search='''
        SELECT * FROM bets WHERE has_ended=0
        '''
        cur = self.conn.cursor()
        cur.execute(sql_to_search)
        bets=cur.fetchall()
        return bets

    def find_all_finished_bets(self, bet_type: str):
        sql_to_search='''
        SELECT * FROM bets WHERE has_ended=1 AND selected_bet_type = ?
        '''
        cur = self.conn.cursor()
        cur.execute(sql_to_search, (bet_type,))
        bets=cur.fetchall()
        return bets