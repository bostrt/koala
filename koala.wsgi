#!/usr/bin/python
import sys
from koala import app as application

sys.path.insert(0, '/var/www/koala')

activate_this = '/var/www/koala/venv/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
