#!./venv/bin/python
from flup.server.fcgi import WSGIServer
from koala import app, init
from models import User, ApiKey, Article, db

if __name__=='__main__':
   @init
   def run():
       WSGIServer(app).run()

   run()
