import os
import datetime
import time

from requests_oauthlib import OAuth1Session

from api.garmin_users.models import GarminUsers
from api.watch.models import Activity
from common.connection import add_item
from dotenv import load_dotenv

load_dotenv()

oauth_consumer_key = os.environ.get('OAUTH_CONSUMER_KEY')
oauth_consumer_secret = os.environ.get('OAUTH_CONSUMER_SECRET')

curr_date = datetime.datetime.now()
days = datetime.timedelta(days=90)
past_date = curr_date - days
summaryStartTimeInSeconds = str(int(time.mktime(past_date.timetuple())))
summaryEndTimeInSeconds = str(int(time.mktime(curr_date.timetuple())))


day = datetime.timedelta(days=1)
old_date = curr_date - day
updateStartTimeInSeconds = str(int(time.mktime(old_date.timetuple())))
updateEndTimeInSeconds = str(int(time.mktime(curr_date.timetuple())))


def add_request_token(request_token, request_token_secret, user_id):
    request_token_creds = GarminUsers(request_token=request_token, request_token_secret=request_token_secret,
                                      user_id=user_id)
    return request_token_creds


def add_access_token(access_token, access_token_secret, verifier):
    request_token_creds = GarminUsers(access_token=access_token, access_token_secret=access_token_secret,
                                      verifier=verifier)
    return request_token_creds


def add_activity_details(data,user_id,source='garmin'):

    activity_data = Activity(summaryid=data.get('summaryId', None), activityid=data.get('activityId', None),
        activityname=data.get('activityName', None), summary=data.get('summary', None),
        activitytype=data.get('activityType', None), location_data=data.get('samples', None),
        laps=data.get('laps', None),source=source,description='None',user_id=user_id)
    return activity_data


def add_activity(data,user_id,source='garmin'):
    # user_id = data['user_id']
    # garmin_id = data['userId']
    activity_data = Activity(summaryid=data.get('summaryId', None), activityid=data.get('activityId', None),
        activityname=data.get('activityName', None), summary=data.get('summary', None),
        activitytype=data.get('activityType', None), location_data=data.get('samples', None),
        laps=data.get('laps', None),source=source,description='None',user_id=user_id)
    return activity_data


def add_location(data):
    location_data = Activity(location_data=data)
    return location_data


#to call backfill api
def getBackfilData(user_id):
    user_creds = GarminUsers.query.filter_by(user_id=user_id,deleted_at=None).first()
    if user_creds and (user_creds.access_token is not None and user_creds.access_token_secret is not None):
        get_activity_path = 'https://apis.garmin.com/wellness-api/rest/backfill/activities?summaryStartTimeInSeconds=' + summaryStartTimeInSeconds + '&summaryEndTimeInSeconds=' + summaryEndTimeInSeconds
        garmin_OAuth = OAuth1Session(oauth_consumer_key, client_secret=oauth_consumer_secret,
                                     signature_method='HMAC-SHA1',
                                     resource_owner_key=user_creds.access_token,
                                     resource_owner_secret=user_creds.access_token_secret)
        response = garmin_OAuth.get(get_activity_path)
    return "Backfill Triggered"


#to call activity detail api
def activity_details(current_user):
    user_creds = GarminUsers.query.filter_by(user_id=current_user,deleted_at=None,deregister_at=None).first()
    if user_creds and (user_creds.access_token is not None and user_creds.access_token_secret is not None):
        get_activity_path = 'https://apis.garmin.com/wellness-api/rest/activityDetails?uploadStartTimeInSeconds' + updateStartTimeInSeconds + '&uploadEndTimeInSeconds=' + updateEndTimeInSeconds
        garmin_OAuth = OAuth1Session(oauth_consumer_key, client_secret=oauth_consumer_secret,
                                     signature_method='HMAC-SHA1',
                                     resource_owner_key=user_creds.access_token,
                                     resource_owner_secret=user_creds.access_token_secret)
        response = garmin_OAuth.get(get_activity_path)
        print(response.text)
    return "Activity Details Api Called"
