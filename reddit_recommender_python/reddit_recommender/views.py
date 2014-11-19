import logging
logging.basicConfig(level=logging.DEBUG)

import praw
from flask import (render_template, g, request, jsonify, redirect)

from reddit_recommender import app
from reddit_recommender.similarity_engine import Recommender
from reddit_recommender.models import db_connect

r = praw.Reddit('OAuth Webserver example by u/catmoon ver 0.1.')
r.set_oauth_app_info(app.config['REDDIT_CLIENT_ID'],
        app.config['REDDIT_CLIENT_SECRET'], app.config['REDDIT_REDIRECT_URI'])

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'connection'):
        g.connection = db_connect()
    return g.connection

def get_recommender():
    '''Instantiate a recommender'''
    if not hasattr(g, 'recommender'):
        g.recommender = Recommender()
    return g.recommender

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'recommender'):
        g.recommender.db_session.close()

@app.route('/')
def index():
    logging.info('\nNEW VISIT\n')
    return render_template('index.html')

@app.route('/langl')
def langl():
    logging.info('\nNEW VISIT\n')
    return render_template('langl/index.html')

@app.route('/oauth')
def get_user_auth():
     link = r.get_authorize_url('DifferentUniqueKey',{'identity','mysubreddits'})
     return redirect(link)

@app.route('/authorize_callback')
def authorized():
    logging.info('\nauthorized!\n')
    code = request.args.get('code', '')
    redditor, subs = get_subs(code)
    recommender = get_recommender()
    subs = recommender.get_sub_recommendations(redditor, subs)
    return render_template('index2.html', data=subs)

def get_subs(code):
    r.get_access_information(code)
    redditor = r.get_me().name
    subs = r.get_my_subreddits()
    sublist = []
    sublist.extend(subs)
    subs =  [sub.display_name for sub in sublist]
    return redditor, subs

@app.route('/query', methods = ['GET', 'POST'])
def query():
    recommender = get_recommender()
    query = request.form.get('text')
    data = recommender.get_sub_recommendations(query)
    assert len(data)
    data = jsonify(subs=data)
    return data
