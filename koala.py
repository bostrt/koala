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

logging.basicConfig(filename=config.get_log_path(),level=logging.__getattribute__(config.get_log_level()))

def locate_user(username, apikey):
    '''
    Select user from database using Username + API Key.
    Returns None upon failure.
    '''
    if not username or not apikey:
        logging.debug('Trying to locate user but Username/APIKey empty.')
        return None

    results = User.select().join(ApiKey).where((User.username==username) & (ApiKey.key==apikey))

    if results.count() != 1:
        logging.debug("Unable to locate user.")
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
    username = request.headers.get('x-koala-username')
    apikey = request.headers.get('x-koala-key')
    user = locate_user(username, apikey)

    userarticles = Article.select().join(User).where((User.id==user.id)).dicts()

    return jsonify({'articles': list(userarticles)})

@app.route('/api/articles/<int:id>', methods=['GET'])
@check_api_key
def get_article(id):
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
    username = request.headers.get('x-koala-username')
    apikey = request.headers.get('x-koala-key')
    user = locate_user(username, apikey)

    delete = Article.delete().where(Article.id == id)
    result = delete.execute()
    if result == 0:
        abort(404)
    else:
        return '', 200

@app.route('/articles', methods=['POST'])
@check_api_key
def put_article():
    username = request.headers.get('x-koala-username')
    apikey = request.headers.get('x-koala-key')
    user = locate_user(username, apikey)

    reqjson = request.get_json()

    result = validators.url(reqjson['url'])
    if not result:
        logging.debug("Bad URL: %s" % reqjson['url'])
        abort(400)

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

    logging.debug('registered user with username %s' % username)
    return jsonify({'username': user.username, 'apikey': apikey.key}), 201

@app.route('/key', methods=['POST'])
def generate_key():
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

def init(f):
    @wraps(f)
    def wrapped(*args, **kwards):
        try:
            db.connect()
            db.create_tables([User, ApiKey, Article], safe=True)
            #app.run(debug=True)
            f()
        finally:
            db.close()
    return wrapped

if __name__=="__main__":
    @init
    def run():
        app.run(debug=True)
    run()
