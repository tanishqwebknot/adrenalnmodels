from mongoengine import Document, StringField, ListField, IntField, BooleanField
from pydantic import BaseModel as MongoBaseModel


class PostView(Document):
    user_id = StringField()
    posts = ListField()


class UserTimeline(Document):
    user_id = StringField()
    post_sequence = ListField()
    index = IntField()


class UserIntermediate(Document):
    user_id = StringField()
    post_sequence = ListField()
    is_dumped = BooleanField(default=False)


class CityList(Document):
    iso2 = StringField()
    iso3 = StringField()
    country = StringField()
    cities = StringField()
