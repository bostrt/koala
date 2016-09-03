from peewee import *
from datetime import datetime
from config import config

db = SqliteDatabase(config.get_database_path())

class KoalaModel(Model):
    added = DateTimeField(default=datetime.now())

    class Meta:
        database = db

class User(KoalaModel):
    username = CharField(index=True, unique=True)
    password = CharField()

class ApiKey(KoalaModel):
    key = CharField(index=True)
    owner = ForeignKeyField(User, related_name='apikeys')

class Article(KoalaModel):
    title = CharField(null=True)
    url = CharField()
    added = DateTimeField(default=datetime.now())
    read = BooleanField(default=False)
    favorite = BooleanField(default=False)
    owner = ForeignKeyField(User, related_name='articles')
