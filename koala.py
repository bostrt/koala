#!/usr/bin/env python

import logging
from flask import Flask, jsonify, abort, request
from config import config
from model import User, ApiKey, Article, db
from functools import wraps
from datetime import datetime
from peewee import IntegrityError
import validators
from validators import ValidationFailure
import hashlib

app = Flask(__name__)
SALT = config.get_database_salt()

#logging.basicConfig(filename=config.get_log_path(),level=logging.__getattribute__(config.get_log_level()))
logging.basicConfig(level=logging.__getattribute__(config.get_log_level()))

def locate_user(username, apikey):
    '''
    Select user from database using Username + API Key.
    Returns None upon failure.
    '''
    if not username or not apikey:
        logging.info('Trying to locate user but Username/APIKey empty.')
        return None

    results = User.select().join(ApiKey).where((User.username==username) & (ApiKey.key==apikey))

    if results.count() != 1:
        logging.info("Unable to locate user.")
        return None

    return results[0]

def check_api_key(func):
    '''
    Validate user based on Username and API Key.
    Aborts with 403 upon failure.
    '''
    @wraps(func)
    def decorated_func(*args, **kwargs):
        username = request.headers.get('x-koala-username')
        apikey = request.headers.get('x-koala-key')
        user = locate_user(username, apikey)

        if user is None:
            abort(403)

        return func(*args, **kwargs)
    return decorated_func

@app.route('/articles', methods=['GET'])
@check_api_key
def get_articles():
    '''
    Get list of articles for particular user.
    TODO: Needs paging.
    '''
    username = request.headers.get('x-koala-username')
    apikey = request.headers.get('x-koala-key')
    user = locate_user(username, apikey)

    userarticles = Article.select().join(User).where((User.id==user.id)).dicts()

    return jsonify({'articles': list(userarticles)})

@app.route('/articles/<int:id>', methods=['GET'])
@check_api_key
def get_article(id):
    '''
    Get specific article based on its ID.
    '''
    username = request.headers.get('x-koala-username')
    apikey = request.headers.get('x-koala-key')
    user = locate_user(username, apikey)

    article = Article.select().join(User).where((Article.id==id) & (User.id == user.id)).dicts()
    if article.count() != 1:
        abort(404)

    return jsonify({'article': article[0]})

@app.route('/articles/<int:id>', methods=['DELETE'])
@check_api_key
def remove_article(id):
    '''
    Remote a specific article based on its ID.
    '''
    username = request.headers.get('x-koala-username')
    apikey = request.headers.get('x-koala-key')
    user = locate_user(username, apikey)

    delete = Article.delete().where(Article.id == id)
    result = delete.execute()
    if result == 0:
        abort(404)
    else:
        return '', 200

@app.route('/articles/<int:id>', methods=['PUT'])
@check_api_key
def update_article(id):
    username = request.headers.get('x-koala-username')
    apikey = request.headers.get('x-koala-key')
    user = locate_user(username, apikey)

    reqjson = request.get_json()

    article = Article.select().join(User).where((Article.id==id) & (User.id == user.id)).get()
    if not article:
        abort(404)
    elif not reqjson:
        abort(400)
    else:
        if reqjson.has_key('read'):
            article.read = reqjson['read'] != False
        if reqjson.has_key('favorite'):
            article.favorite = reqjson['favorite'] != False
        article.save()
        return '', 204


@app.route('/articles', methods=['POST'])
@check_api_key
def put_article():
    '''
    Add new article for a user.
    '''
    username = request.headers.get('x-koala-username')
    apikey = request.headers.get('x-koala-key')
    user = locate_user(username, apikey)

    reqjson = request.get_json()

    result = validators.url(reqjson['url'])
    if not result:
        # try again but with http://
        result = validators.url('http://' + reqjson['url'])
        if not result:
            logging.info("Bad URL: %s" % reqjson['url'])
            abort(400)
        else:
            reqjson['url'] = 'http://' + reqjson['url']

    title = reqjson.get('title', reqjson['url'])
    url = reqjson['url']
    date = str(datetime.now())
    read = False
    favorite = False
    owner = user.id

    article = Article.create(title=title, url=url, date=date, read=read, favorite=favorite, owner=owner)

    return jsonify({'id': article.id}), 201

@app.route('/users', methods=['POST'])
def register():
    '''
    Register a new user and generate then an API Key.
    Returns JSON-encoded username and API Key.
    '''
    reqjson = request.get_json()
    username = reqjson.get('username', '')
    password = reqjson.get('password', '')

    if not username or not password:
        logging.debug('Denying access for username of %s' % username)
        abort(400)

    try:
        user = User.create(username=username, password=password)
    except IntegrityError as e:
        logging.error('unable to register user with username %s' % username, e)
        abort(409)

    key = hashlib.sha1(username + password + str(datetime.now().microsecond) + SALT)

    apikey = ApiKey.create(owner=user.id, key=key.hexdigest())

    logging.warn('registered user with username %s' % username)
    return jsonify({'username': user.username, 'apikey': apikey.key}), 201

@app.route('/key', methods=['POST'])
def generate_key():
    '''
    Generate a new key for user.
    Returns JSON-encoded username and API Key.
    '''
    reqjson = request.get_json()
    username = reqjson.get('username', '')
    password = reqjson.get('password', '')

    try:
        user = User.get(User.username == username)
    except User.DoesNotExist:
        logging.debug('User does not exist with username of %s' % username)
        abort(403)

    if user.password == password:
        key = hashlib.sha1(username + password + str(datetime.now().microsecond) + SALT)
        apikey = ApiKey.create(owner=user.id, key=key.hexdigest())
        return jsonify({'username': user.username, 'apikey': apikey.key}), 201
    else:
        logging.debug('Unable to authenticate user to generate API Key for username %s' % username)
        abort(403)

@app.before_request
def db_connect():
    '''
    Create a database connection before each request.
    '''
    logging.debug("Connecting to database.")
    db.connect()
    logging.debug("Connected to database.")

@app.after_request
def db_close(response):
    '''
    Close the database connection after each request.
    '''
    logging.debug("Closing database connection.")
    if not db.is_closed():
        db.close()
    else:
        logging.debug("Database connection already closed.")
    logging.debug("Closed database connection.")
    return response

@app.before_first_request
def db_init():
    db.create_tables([User, ApiKey, Article], safe=True)

if __name__=="__main__":
    app.run(debug=True)
