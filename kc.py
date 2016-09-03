#!/usr/bin/python
import argparse
from xdg import BaseDirectory
import requests
import json

KOALA_LOGIN_FILE='login'
KOALA_SERVER="http://localhost:5000/"
KOALA_API_PATH=""
X_KOALA_USERNAME='x-koala-username'
X_KOALA_KEY='x-koala-key'

parser = argparse.ArgumentParser()
subparser = parser.add_subparsers()

loginparser = subparser.add_parser('login')
registerparser = subparser.add_parser('register')
addparser = subparser.add_parser('add')
rmparser = subparser.add_parser('rm')
listparser = subparser.add_parser('list')
genkeyparser = subparser.add_parser('genkey')

registerparser.add_argument('-u', '--username', required=True)
registerparser.add_argument('-p', '--password', required=True)
registerparser.set_defaults(which='register')

loginparser.add_argument('-u', '--username')
loginparser.add_argument('-k', '--key')
loginparser.set_defaults(which='login')

addparser.add_argument('-u', '--url', required=True)
addparser.add_argument('-t', '--title')
addparser.set_defaults(which='add')

rmparser.add_argument('-a', '--article', required=True)
rmparser.set_defaults(which='rm')

listparser.add_argument('-l', '--limit')
listparser.add_argument('-v', '--verbose', action='store_true')
listparser.set_defaults(which='list')

genkeyparser.add_argument('-u', '--username')
genkeyparser.add_argument('-p', '--password')
genkeyparser.set_defaults(which='genkey')

def write_login_file(username, key):
    # Save username and password to user home.
    path = BaseDirectory.save_config_path('koala')
    loginfile = open(path + '/' + KOALA_LOGIN_FILE, 'w+')
    loginfile.writelines(username + ':' + key)
    loginfile.close()

def read_login_file():
    path = BaseDirectory.save_config_path('koala')
    loginfile = open(path + '/' + KOALA_LOGIN_FILE)
    line = loginfile.readline()
    loginfile.close()
    return tuple(line.split(':'))

def register(args):
    headers = {'Content-Type': 'application/json'}
    payload = {'username': args.username, 'password': args.password}
    r = requests.post(KOALA_SERVER + KOALA_API_PATH + 'users', data=json.dumps(payload), headers=headers, verify=False)
    if r.status_code != 201:
        print r.text
    else:
        apikey = r.json()['apikey']
        write_login_file(args.username, apikey)
        print 'registered'

def login(args):
    # Attempt a request.
    headers = {
        'Content-Type': 'application/json',
        X_KOALA_USERNAME: args.username,
        X_KOALA_KEY: args.key
    }
    r = requests.get(KOALA_SERVER + KOALA_API_PATH + 'articles', headers=headers, verify=False)

    if r.status_code != 200:
        print 'Invalid usernamd or API key'
    else:
        print 'Logged in as', args.username
        write_login_file(args.username, args.key)

def listing(args):
    user, key = read_login_file()
    headers = {
        'Content-Type': 'application/json',
        X_KOALA_USERNAME: user,
        X_KOALA_KEY: key
    }
    r = requests.get(KOALA_SERVER + KOALA_API_PATH + 'articles', headers=headers, verify=False)
    respjson = r.json()
    if r.status_code != 200 or not respjson.has_key('articles'):
        print r.text
    else:
        for article in respjson['articles']:
            if article['title']:
                print article['title']
            print article['url']

            if args.verbose:
                print 'Added on', article['added']
                print ('Read' if article['read'] else 'Not Read')
                if article['favorite']:
                    print 'Favorite'
                print '======================='

def add(args):
    user, key = read_login_file()
    headers = {
        'Content-Type': 'application/json',
        X_KOALA_USERNAME: user,
        X_KOALA_KEY: key
    }
    payload = {'url': args.url, 'title': args.title}
    r = requests.post(KOALA_SERVER + KOALA_API_PATH + 'articles', data=json.dumps(payload), headers=headers, verify=False)
    if r.status_code != 201:
        print r.text
    else:
        print 'Added %s' % (args.title or args.url)

def rm(args):
    user, key = read_login_file()
    headers = {
        X_KOALA_USERNAME: user,
        X_KOALA_KEY: key
    }
    r = requests.delete(KOALA_SERVER + KOALA_API_PATH + 'articles/' + args.article, headers=headers, verify=False)
    if r.status_code != 204:
        print r.text
    else:
        print 'Removed article',args.article

def genkey(args):
    headers = {'Content-Type': 'application/json'}
    payload = {'username': args.username, 'password': args.password}
    r = requests.post(KOALA_SERVER + KOALA_API_PATH + 'key', data=json.dumps(payload), headers=headers, verify=False)
    if r.status_code != 201:
        print r.text
    else:
        apikey = r.json()['apikey']
        write_login_file(args.username, apikey)
        print 'New API Key generated and saved'

args = parser.parse_args()

if args.which == 'register':
    register(args)
elif args.which == 'list':
    listing(args)
elif args.which == 'add':
    add(args)
elif args.which == 'genkey':
    genkey(args)
elif args.which == 'login':
    login(args)
elif args.which == 'rm':
    rm(args)
