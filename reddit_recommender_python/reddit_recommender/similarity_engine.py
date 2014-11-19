'''Reddit Sub recommendation based on Jaccard's similarity coefficent'''
import json
import re
import logging

import pandas.io.sql as pd_psql
import praw

from reddit_recommender.models import db_connect


logging.basicConfig(level=logging.INFO)
ESCAPE_REGEX = re.compile(r"[\0\n\r\032\'\"\\]")
ESCAPE_MAP = {'\0': '\\0', '\n': '\\n', '\r': '\\r', '\032': '\\Z',
              '\'': '\\\'', '"': '\\"', '\\': '\\\\'}

#We remove default subs. People haven't asked to subscribe to them and forget
#to unsubscribe.
DEFAULT_SUBS = [
 'mildlyinteresting',
 'trees',
 'Games',
 'LifeProTips',
 'todayilearned',
 'funny',
 'politics',
 'sports',
 'Music',
 'EarthPorn',
 'gaming',
 'aww',
 'IAmA',
 'AdviceAnimals',
 'science',
 'worldnews',
 'explainlikeimfive',
 'television',
 'bestof',
 'askscience',
 'Futurology',
 'pics',
 'movies',
 'news',
 'gifs',
 'videos',
 'TodayILearned',
 'AskReddit',
 'books',
 'technology',
 'funny',
 'fffffffuuuuuuuuuuuu',
 ]

def escape_string(value):
    return ("%s" % (ESCAPE_REGEX.sub(
            lambda match: ESCAPE_MAP.get(match.group(0)), value),))

with open('reddit_recommender/static/subs.json') as file:
    SUBS = json.load(file)
    SUBS.sort(reverse=True)

REDDIT = praw.Reddit(user_agent='Manueslapera Reddit recommender')

class Recommender(object):
    """Main Recommender"""
    def __init__(self, dev_session=None):
        if dev_session:
            self.db_session = dev_session
        else:
            self.db_session = db_connect()
        self.subs = SUBS

    def __del__(self):
        self.db_session.close()

    def check_redditor_exists(self, redditor):
        '''Checks if a redditor exists in Reddit'''
        try:
            REDDIT.get_redditor(redditor, fetch=True)
        except:
            print 'Redditor doesnt exist in Reddit'
            return False
        return True

    def get_similarity_from_sub(self, sub):
        """Given a sub, return all other subs with similarity"""
        sub_scores = pd_psql.frame_query("SELECT sub2, similarity FROM\
            similarity WHERE sub1 = '{0} ORDER BY sum DESC';".format(sub), self.db_session.connection)
        sub_scores.similarity = sub_scores.similarity.astype(float)
        sub_scores = sub_scores[sub_scores['similarity']>0]
        sub_scores.set_index('sub2',inplace=True)
        return sub_scores

    def get_sub_recommendations(self, redditor, subs=None):
        """Given a redditor, return recommended subs with scores"""
        redditor_subs = self.load_redditor_subs(redditor,subs=subs)
        if not isinstance(redditor_subs, list) or not len(redditor_subs):
            redditor_subs = DEFAULT_SUBS

        #Filter for similarity
        redditor_subs = [sub for sub in redditor_subs if sub in SUBS]
        base_query = "select sub2, sum(similarity) as similarity from similarity where sub1 in ({})\
                group by sub2 ORDER BY similarity DESC;"
        query = base_query.format(', '.join(["'" + i + "'" for i in redditor_subs]))
        all_sub_scores = pd_psql.frame_query(query, self.db_session.connection)
        all_sub_scores = all_sub_scores[-all_sub_scores.sub2.isin(redditor_subs)]
        all_sub_scores.fillna(0,inplace=True)
        all_sub_scores.sort(columns=['similarity'], ascending=False, inplace=True)
        recommendations = list(all_sub_scores.sub2[(-all_sub_scores.sub2.isin(DEFAULT_SUBS))][:10])
        logging.info('\n\nRECOMMENDATIONS FOR REDDITOR {}:\n'.format(redditor))
        logging.info(recommendations)
        if not len(recommendations):
            recommendations = DEFAULT_SUBS
        return recommendations

    def load_redditor_subs(self, redditor, subs=None):
        if not subs:
            redditor = redditor.replace(';','').replace("'",'').replace('/','').replace('\\','').strip()
            base_query = "SELECT sub FROM redditors2 WHERE redditor = '{0}'"
            query = base_query.format(redditor)
            redditor_subs = pd_psql.read_sql(query, self.db_session.connection)
            if redditor_subs.empty:
                if self.check_redditor_exists(redditor):
                    return self.get_redditor_subs(redditor)
                else:
                    return DEFAULT_SUBS
            redditor_subs = redditor_subs['sub'].tolist()
        else:
            redditor_subs = self.get_redditor_subs(redditor, subs)

        logging.info(redditor_subs)
        return redditor_subs
