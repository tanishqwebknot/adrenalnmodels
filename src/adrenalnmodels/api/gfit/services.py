import datetime
import json
import time

import requests

from api.watch.models import Activity
from api.gfit.models import GfitUsers
from common.connection import add_item, update_item
from common.response import success

curr_date = datetime.datetime.now()
days = datetime.timedelta(days=30)
past_date = curr_date - days
start_time = str(int(time.mktime(past_date.timetuple())))
end_time = str(int(time.mktime(curr_date.timetuple())))


#add fgit token details in DB

def oauth_creds(access_token,refresh_token,oauth_code,current_user,exp_date):
    user_creds = GfitUsers(access_token=access_token,refresh_token=refresh_token, auth_code=oauth_code,user_id=current_user,refresh_token_exp=exp_date)
    return user_creds


# function to get access token
def exchange_token(current_user):
    user_creds = GfitUsers.query.filter_by(user_id=current_user,deleted_at=None,deregister_at=None).first()
    if user_creds is not None:
        url = 'https://oauth2.googleapis.com/token?client_secret=client_secret&client_id=client_id&refresh_token='+user_creds.refresh_token+'&grant_type=refresh_token'
        response = requests.request("POST", url)
        resp = json.loads(response.text)
        access_token = resp['access_token']
        user_creds.access_token=access_token
        update_item(user_creds)
        return "success"


# function to add activity in DB
def add_activity(data,source='google_fit'):
    activity_data = Activity(activityid=data.get('id', None),activityname=data.get('name',None), summaryid=data.get('summaryId', None),summary=data.get('summary', None),activitytype=data.get('name', None), location_data=data.get('samples',None),
        laps=data.get('laps', None),source=source,description=data.get('description',None))
    return activity_data