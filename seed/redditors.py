from collections import OrderedDict
import json
import psycopg2
from datetime import datetime
import multiprocessing
from random import shuffle
import numpy as np

import praw
from praw.handlers import MultiprocessHandler

class Save_to_db():
    connection = None
    cursor = None

    def __init__(self, host, dbname, user_name, password):
        # Connect to an existing database
        self.connection = psycopg2.connect(dbname=dbname, user=user_name,
                host=host, password=password)
        self.cursor = self.connection.cursor()

    def insert(self, table_name, entry_list):
        if self.cursor is None:
            raise Exception("Invalid connection to database.")
        # Fill in the new values
        subquery=( ", ".join( repr(point) for point in entry_list))
        query = 'INSERT INTO %s VALUES (%s);' % (table_name, subquery)
        self.cursor.execute(query, subquery)
        # Write the new info to db
        self.connection.commit() 

    def execute_sql(self, sql_query):
        if self.cursor is None:
            raise Exception("Invalid connection to database.")
        self.cursor.execute(sql_query)
        self.connection.commit() 

    def retrieve_sql(self, sql_query):
        if self.cursor is None:
            raise Exception("Invalid connection to database.")
        self.cursor.execute(sql_query)
        return self.cursor.fetchall()

    def create_table(self, table_name, col_dict):
        if self.cursor is None:
            raise Exception("Invalid connection to database.")
        string = ''
        for item in col_dict.items():
            string = string + '"'+item[0]+'"' + ' ' + item[1] + ', '
        string = string[:-2]
        sql_query = 'CREATE TABLE IF NOT EXISTS {0} ({1});'.format(table_name, string)
        print sql_query
        self.cursor.execute(sql_query)
        self.connection.commit()


#create the table (just once)
with open('subs.json') as file:
    subs = json.load(file)
col_dict = OrderedDict()
col_dict['redditor'] = 'varchar(20)'
for sub in subs:
  col_dict[sub] = 'smallint'

saver = Save_to_db(dbname='reddit', user_name='reddit', host='localhost',
password='reddit')

saver.create_table('redditors', col_dict)


def store_redditor(sub, redditor, saver):
    query = '''
    DO
    $BODY$
    BEGIN
    IF EXISTS (SELECT "{sub}" from redditors where redditor = '{redditor}' ) THEN
        UPDATE redditors SET "{sub}" = 1 WHERE redditor = "{redditor}";
    ELSE
        INSERT INTO redditors (redditor, "{sub}") VALUES ('{redditor}',1);
    END IF;
    END;
    $BODY$
    '''.format(redditor=redditor, sub=sub)
    saver.execute_sql(query)


def sub_in_db(sub, saver):
    sub_col = np.array(saver.retrieve_sql('SELECT "{}" from\
        redditors'.format(sub)))
    print sub_col
    if 1 in sub_col:
        print 'Sub {0} in Database'.format(sub)
        return True
    else:
        print 'Sub {0} NOT in Database'.format(sub)
        return False

def get_redditors(sub, r):
    sub_redditors = []
    sub_info = r.get_subreddit(sub)
    comments = sub_info.get_new(limit=None)
    while 1:
        c = comments.next()
        time_old = (datetime.now() - datetime.fromtimestamp(c.created))
        if time_old.total_seconds()/(3600*24) < 180:
            redditor = c.author.name
            if redditor not in sub_redditors:
                store_redditor(sub, redditor, saver)
                print sub,redditor
                sub_redditors.append(redditor)
            else:
                pass
        else:
            break

with open('subs_db.json') as file:
    subs = json.load(file)

handler = MultiprocessHandler()
def praw_process(handler):
    saver = Save_to_db(dbname='reddit', user_name='reddit', host='localhost',
    password='reddit')
    r = praw.Reddit(user_agent='PUT AN IDENTIFIER HERE', handler=handler)
    #shuffle(subs)
    for sub in subs:
        if not sub_in_db(sub, saver):
            get_redditors(sub, r, saver)

if __name__ == '__main__':
    saver = Save_to_db(dbname='DB_NAME', user_name='DB_USER', host='DB_HOST',
    password='DB_PWD')
    jobs = []
    for i in range(10):
        p = multiprocessing.Process(target=praw_process, args=(handler,))
        jobs.append(p)
        p.start()
    #praw_process(handler)
