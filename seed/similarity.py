'''Reddit Sub recommendation based on Jaccard's similarity coefficent'''
from collections import OrderedDict
import json
import multiprocessing
import logging

import numpy as np
import psycopg2
import pandas.io.sql as pd_psql
from requests import HTTPError
import praw
logging.basicConfig(level=logging.DEBUG)

NUMBER_THREADS = 20 #This will depend on your machine
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

    def insert_dict(self, table_name, entry_dict):
        if self.cursor is None:
            raise Exception("Invalid connection to database.")
        columns = ', '.join(['"'+key+'"' for key in entry_dict.keys()])
        values = ', '.join([str(value) for value in entry_dict.values()])
        query = 'insert into {} ({}) values ({});'.format(table_name, columns, values)
        self.execute_sql(query)

    def execute_sql(self, sql_query):
        if self.cursor is None:
            raise Exception("Invalid connection to database.")
        self.cursor.execute(sql_query)
        self.connection.commit()

    def retrieve_sql(self, sql_query):
        if self.cursor is None:
            raise Exception("Invalid connection to database.")
        self.cursor.execute(sql_query)
        query_result = self.cursor.fetchall()
        query_result = np.array(query_result)
        query_result = query_result.flatten()
        return list(query_result)

    def create_table(self, table_name, col_dict):
        if self.cursor is None:
            raise Exception("Invalid connection to database.")
        string = ''
        for item in col_dict.items():
            string = string + '"'+item[0]+'"' + ' ' + item[1] + ', '
        string = string[:-2]
        sql_query = 'CREATE TABLE {0} ({1});'.format(table_name, string)
        self.cursor.execute(sql_query)
        self.connection.commit()

def get_redditor_subs(redditor):

    redditor_subs = OrderedDict()
    redditor_parser = REDDIT.get_redditor(redditor, fetch=True)
    comments = redditor_parser.get_comments(limit=500)
    posts = redditor_parser.get_submitted(limit=500)

    while 1:
        try:
            sub = comments.next().subreddit.url.split('/')[2]
            print sub
        except:
            logging.exception('')
            break

        if sub in redditor_subs or sub not in SUBS:
            continue
        else:
            redditor_subs[sub] = 1

    while 1:
        try:
            sub = posts.next().subreddit.url.split('/')[2]
            print sub
        except:
            logging.exception('')
            break
        if sub in redditor_subs or sub not in SUBS:
            continue
        else:
            redditor_subs[sub] = 1

        if len(redditor_subs):
            if not check_redditor_in_db(redditor):
                redditor_subs['redditor'] = "'"+redditor+"'"
                SAVER.insert_dict('redditors', redditor_subs)
            else:
                print 'Already in the database'
                update_redditor(redditor, redditor_subs)
        return list(redditor_subs.keys())

def check_redditor_exists(redditor):
    '''Checks if a redditor exists in Reddit'''
    try:
        REDDIT.get_redditor(redditor, fetch=True)
    except HTTPError:
        print 'Redditor doesnt exist in Reddit'
        return False
    return True

def check_redditor_in_db(redditor):
    return bool(SAVER.retrieve_sql("SELECT EXISTS(select redditor from\
        redditors where redditor = '{}');".format(redditor)))

class Recommender(object):
    """Main Recommender"""
    def __init__(self, db_session, subs):
        self.db_session = db_session
        self.subs = subs

    def dispatch_jobs(self, data, job_number, function):

        def chunks(l, n):
            return [l[i:i+n] for i in range(0, len(l), n)]

        total = len(data)
        chunk_size = total / job_number
        slice = chunks(data, chunk_size)
        jobs = []

        for i, s in enumerate(slice):
            j = multiprocessing.Process(target=function, args=(i, s))
            jobs.append(j)
        for j in jobs:
            j.start()

    def populate_similarity(self):

        def create_similarity_table():
            '''We only need to create the similaroty table if it doesnt exist'''

            exists = self.db_session.retrieve_sql("select exists(select * from information_schema.tables where table_name = 'similarity');")[0]
            exists = bool(exists)

            if not exists:
                logging.info("CREATING SIMILARITY TABLE")
                sub_name_len = max([len(i) for i in self.subs])
                sim_dict = OrderedDict()
                sim_dict['sub1'] = 'varchar(%d)' % sub_name_len
                sim_dict['sub2'] = 'varchar(%d)' %  sub_name_len
                sim_dict['similarity'] = 'float'
                self.db_session.create_table('similarity', sim_dict)
            else:
                logging.info("SIMILARITY TABLE ALREADY EXISTS")

        def worker_populate_similarity(job_id, sub_list):

            worker_saver = Save_to_db(dbname='DB_NAME', user_name='DB_USER',
                    host='DB_HOST', password='DB_PWD')

            for sub1 in sub_list:
                exists = worker_saver.retrieve_sql("select exists(select sub2 from similarity where sub1 = '{0}');".format(sub1))
                exists = bool(exists)
                missing_entries = self.subs
                if exists:
                    existing_entries = worker_saver.retrieve_sql("SELECT\
                            distinct(sub2) from similarity where sub1 = '{0}';".format(sub1))
                    missing_entries = [i for i in self.subs if i not in
                            existing_entries]

                for sub2 in missing_entries:
                    if sub1 != sub2:
                        users_intersect = worker_saver.retrieve_sql('SELECT COUNT(redditor) FROM redditors WHERE "{0}" = 1 and "{1}" = 1;'.format(sub1, sub2))
                        users_union = worker_saver.retrieve_sql('SELECT COUNT(redditor) FROM redditors WHERE "{0}" = 1 OR "{1}" = 1;'.format(sub1, sub2))
                        users_intersect = int(users_intersect[0])
                        users_union = int(users_union[0])
                        if users_intersect:
                            sim = users_intersect * 1.0 / users_union
                        else:
                            sim = 0.0
                        logging.info('{} & {} = Union: {} Intersection: {};\
                                SIM: {}'. format(sub1, sub2, users_union,
                                    users_intersect, sim))
                        worker_saver.insert('similarity', [str(sub1), str(sub2), sim])

        create_similarity_table()
        n_workers = NUMBER_THREADS
        self.dispatch_jobs(self.subs, n_workers, worker_populate_similarity)

    def load_redditor_subs(self, redditor, force_update=False):
        redditor_subs = pd_psql.frame_query("SELECT * FROM redditors WHERE redditor = '{0}'".format(redditor), self.db_session.connection)
        redditor_subs = redditor_subs.dropna(axis=1)
        del redditor_subs['redditor']
        if redditor_subs.empty or force_update:
            print '\nRedditor not in the database. Acquiring.\n'
            if check_redditor_exists(redditor):
                return get_redditor_subs(redditor)
            return []
        return list(redditor_subs.columns)

if __name__ == '__main__':
    SAVER = Save_to_db(dbname='DB_NAME', user_name='DB_USER', host='DB_HOST',
    password='DB_PWD')
    REDDIT = praw.Reddit(user_agent='PUT A IDENTIFIER HERE') #be nice
    with open('subs.json') as file:
        SUBS = json.load(file)
        SUBS.sort(reverse=True)
    recommender = Recommender(SAVER, SUBS)
    recommender.populate_similarity()
