import json
import os
# import numpy
# from astropy.io import fits
# import fitdecode
import fitdecode
import fitparse
from fitparse import FitFile
import requests
from google.protobuf.text_format import Merge

from api.garmin_users.models import GarminUsers
from api.garmin_users.service import add_request_token, add_access_token, add_activity, getBackfilData, add_location, \
    activity_details, add_activity_details
from app import db
import time
from flask import Flask, render_template, url_for, redirect, request, jsonify, Blueprint
from requests import Session
from requests_oauthlib import OAuth1Session
from sqlalchemy.orm import session

from api.watch.models import Activity, User_activity_mapping
from common.connection import add_item, update_item, delete_item
from common.response import failure, success
from middleware.auth import get_request_token
import datetime
from middleware import auth
from middleware.auth import token_required, get_jwt
from flask import request, g
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

garmin_api = Blueprint('garmin_api', __name__, url_prefix='/garmin')

# user login api
@garmin_api.route('/login', methods=['GET', 'POST'])
@token_required
def login(current_user):
    user_creds = GarminUsers.query.filter_by(user_id=current_user,deleted_at=None).first()

    if user_creds and user_creds.garmin_id is not None:

        return success("SUCCESS",meta={'message':'User already Registered!'})

    else:
        # data = request.get_json()
        credentials = get_request_token()
        request_token = credentials[0]
        request_token_secret = credentials[1]
        if user_creds and user_creds.request_token and user_creds.request_token_secret is not None:
            user_creds.request_token = request_token
            user_creds.request_token_secret = request_token_secret
            update_item(user_creds)
        else:
            request_token_creds = add_request_token(request_token, request_token_secret, current_user)
            add_item(request_token_creds)

        call_back_url = os.environ.get('CALL_BACK_URL') + current_user
        auth_url = "https://connect.garmin.com/oauthConfirm?" + "oauth_token=" + request_token
        if call_back_url:
            call_back_url = "&oauth_callback=" + call_back_url + "#?action=step3"
            auth_url = auth_url + call_back_url
            return success("SUCCESS", auth_url,meta={'message':'Authorization URL'})


# callback url to get user permission
@garmin_api.route('/getActivity/<current_user>', methods=['GET', 'POST'])
def get_user_activity(current_user):

    user_creds = GarminUsers.query.filter_by(user_id=current_user,deleted_at=None).first()
    if user_creds is not None:

        oauth_verifier = request.args.get('oauth_verifier')

        if oauth_verifier is not None:
            garmin_OAuth = OAuth1Session(os.environ.get('OAUTH_CONSUMER_KEY'),
                                         client_secret=os.environ.get('OAUTH_CONSUMER_SECRET'),
                                         signature_method='HMAC-SHA1',
                                         verifier=oauth_verifier, resource_owner_key=user_creds.request_token,
                                         resource_owner_secret=user_creds.request_token_secret)
            access_token_path = 'https://connectapi.garmin.com/oauth-service/oauth/access_token'
            response = garmin_OAuth.get(access_token_path)
            response = response.text

            credentials = response.split("&")

            # access_token
            access_token = credentials[0]
            access_token = access_token.split('=')
            access_token = access_token[1]
            # secret_tokens
            access_token_secret = credentials[1]
            access_token_secret = access_token_secret.split('=')
            access_token_secret = access_token_secret[1]

            # getting garmin_user_id

            def getGarminUserId():
                get_userid_path = 'https://apis.garmin.com/wellness-api/rest/user/id'
                garmin_OAuth = OAuth1Session(oauth_consumer_key, client_secret=oauth_consumer_secret,
                                             signature_method='HMAC-SHA1',
                                             resource_owner_key=access_token,
                                             resource_owner_secret=access_token_secret)
                response = garmin_OAuth.get(get_userid_path)
                data = response.json()
                garmin_id = data['userId']
                return garmin_id

            garmin_id = getGarminUserId()

            is_garmin_account=GarminUsers.query.filter_by(garmin_id=garmin_id,deregister_at=None,deleted_at=None).first()
            if is_garmin_account:
                deleted_account =GarminUsers.query.filter_by(user_id=current_user,deleted_at=None,deregister_at=None).first()
                delete_item(deleted_account)
                return redirect(url_for('garmin_api.url_redirect',garmain_connected='false',error_message='This Garmin Account is linked with another account'))

            # updating access token values in DB
            user_creds.garmin_id = garmin_id
            user_creds.access_token = access_token
            user_creds.access_token_secret = access_token_secret
            user_creds.verifier = oauth_verifier
            update_item(user_creds)


            #getting backfill data
            res = getBackfilData(user_creds.user_id)
            # getting user data
            garmin_OAuth = OAuth1Session(os.environ.get('OAUTH_CONSUMER_KEY'),
                                         client_secret=os.environ.get('OAUTH_CONSUMER_SECRET'), signature_method='HMAC-SHA1',
                                         resource_owner_key=access_token, resource_owner_secret=access_token_secret)

            get_activity_path = 'https://apis.garmin.com/wellness-api/rest/activities?uploadStartTimeInSeconds='+updateStartTimeInSeconds+'&uploadEndTimeInSeconds='+summaryEndTimeInSeconds
            response = garmin_OAuth.get(get_activity_path)
            res=activity_details(current_user)
            return success("SUCCESS",meta={'message':'User Verified!'})
        else:
            return failure('Permission Denied!')

    else:
        return failure("User Not Registered!")


@garmin_api.route('?garmin_connected=<garmain_connected>&error_message=<error_message>', methods=['GET'])
def url_redirect(garmain_connected,error_message):
    # result=[]
    data={}
    data['error_message'] = "This Garmin Account is linked with another account"
    data['garmain_connected'] = 'false'
    return success("SUCCESS",data,meta={'message': 'This Garmin Account is linked with another account'})


#webhook to get activity
@garmin_api.route('/webhook/getActivity', methods=['POST'])
def webhook():
    # try:
    data = request.get_json()
    activities = data["activities"]
    garmin_id = data["activities"][0]['userId']
    activityId = data["activities"][0]['activityId']

    if activities:
        for activity in activities:
            garmin_id = str(activity['userId'])
            garmin_user = GarminUsers.query.filter_by(garmin_id=garmin_id, deleted_at=None, deregister_at=None).first()
            existing_data = Activity.query.filter_by(activityid=str(activity['activityId']),user_id=garmin_user.user_id).first()
            if not existing_data:
                user_activity = add_activity(activity,garmin_user.user_id,source='garmin')
                add_item(user_activity)

                # updating summary data
                activity_data = Activity.query.filter_by(activityid=str(activity['activityId'])).first()
                if activity_data:
                    rem_list = ['activityId', 'activityName', 'activityType', 'userId', 'userAccessToken', 'summaryId']
                    [activity.pop(key) for key in rem_list]
                     # summary = activity
                    activity_data.summary=activity
                    update_item(activity_data)

            #updating mapping table
            # garmin_user = GarminUsers.query.filter_by(garmin_id=garmin_id,deleted_at=None).all()
            # if garmin_user:
            #     for user in garmin_user:
            #         activity_data = Activity.query.filter_by(activityid=str(activityId)).first()
            #         mapping_data=User_activity_mapping(user_id=user.user_id,activity_table_id=activity_data.id)
            #         add_item(mapping_data)

        return success("SUCCESS", meta={'message':'WEBHOOK TO GET ACTIVITY'})

    # except Exception as e:
    #     return failure("No Data Found!")


 # Webhook for activity details api
@garmin_api.route('/webhook/getActivityDetail', methods=['POST'])
def detailwebhook():
    # try:
    data = request.get_json()
    activities = data["activityDetails"]

    if activities:
        for activity in activities:
            garmin_user = GarminUsers.query.filter_by(garmin_id= str(activity['userId']), deleted_at=None, deregister_at=None).first()
            existing_data = Activity.query.filter_by(activityid=str(activity['activityId']),user_id=garmin_user.user_id).first()
            if not existing_data:
                garmin_id = str(activity['userId'])
                activityId = activity['activityId']
                activityType = activity['summary']['activityType']
                activityName = activity['summary']['activityName']

                activity["activityType"] = activityType
                activity["activityName"] = activityName
                user_activity = add_activity_details(activity,garmin_user.user_id,source='garmin')
                add_item(user_activity)

            else:
                activityType = activity['summary']['activityType']
                activityName = activity['summary']['activityName']
                summaryId = activity['summaryId']
                activity["activityType"] = activityType
                activity["activityName"] = activityName
                existing_data.activityid = activity.get('activityId')
                existing_data.summaryid = summaryId
                existing_data.activityname = activityName
                existing_data.activitytype =activityType
                existing_data.summary = activity.get('summary')
                existing_data.laps = activity.get('laps')
                existing_data.location_data = activity.get('samples')
                existing_data.user_id = garmin_user.user_id
                update_item(existing_data)

    return success("SUCCESS",meta={'message':'WEBHOOK FOR ACTIVITY!'})


# to get Garmin User id
@garmin_api.route('/getid', methods=['GET', 'POST'])
def getGarminUserId():
    get_userid_path = 'https://apis.garmin.com/wellness-api/rest/user/id'
    garmin_OAuth = OAuth1Session(oauth_consumer_key, client_secret=oauth_consumer_secret,
                                 signature_method='HMAC-SHA1', resource_owner_key='access key',
                                 resource_owner_secret='secret key')
    response = garmin_OAuth.get(get_userid_path)
    data = response.json()
    garmin_id = data['userId']
    return garmin_id


# to get list of permission given by garmin users
@garmin_api.route('/userPermission/<user_id>', methods=['GET','POST'])
def user_permission(user_id):
    user_creds = GarminUsers.query.filter_by(user_id=user_id,deleted_at=None).first()
    user_permission_url = 'https://apis.garmin.com/userPermissions/'
    garmin_OAuth = OAuth1Session(oauth_consumer_key, client_secret=oauth_consumer_secret,
                                 signature_method='HMAC-SHA1', resource_owner_key=user_creds.access_token,
                                 resource_owner_secret=user_creds.access_token_secret)
    response = garmin_OAuth.get(user_permission_url)
    return success("SUCCESS",meta={'message':'User Permissions!'})


# user Deregistration from garmin
@garmin_api.route('/userDeregistration', methods=['GET'])
@token_required
def userDeregistration(user_id):
    user_creds = GarminUsers.query.filter_by(user_id=user_id,deleted_at=None).first()
    if user_creds:
        user_deregistration_url = 'https://apis.garmin.com/wellness-api/rest/user/registration'
        garmin_OAuth = OAuth1Session(oauth_consumer_key, client_secret=oauth_consumer_secret,
                                     signature_method='HMAC-SHA1', resource_owner_key=user_creds.access_token)
        response = garmin_OAuth.get(user_deregistration_url)
        user_creds.deleted_at = datetime.datetime.now()
        user_creds.deregister_at = datetime.date.today()
        update_item(user_creds)
        return success("SUCCESS",meta={'message':'User Deegistered!'})
    else:
        return success("SUCCESS",meta={'message':'User Not Registered!'})


# to get FIT files from garmin
@garmin_api.route('/activityfiles', methods=['GET', 'POST'])
def activityfiles():

    data = request.get_json()
    activityfiles = data["activityFiles"]

    for item in activityfiles:
        garmin_user_id = item["userId"]
        access_token = item["userAccessToken"]
        activityFile_url = item["callbackURL"]
        activity_id = str(item["activityId"])
        manual = item["manual"]

        garmin_user = GarminUsers.query.filter_by(access_token=access_token,deleted_at=None).first()

        garmin_OAuth = OAuth1Session(oauth_consumer_key, client_secret=oauth_consumer_secret,
                                     signature_method='HMAC-SHA1', resource_owner_key=garmin_user.access_token,
                                     resource_owner_secret=garmin_user.access_token_secret)
        response = garmin_OAuth.get(activityFile_url)

        open("garminActivity/" + activity_id + '.fit', "wb").write(response.content)

        #decodin fit file
        with fitdecode.FitReader('garminActivity/8430426122.fit') as fit_file:
            result = []
            for frame in fit_file:

                if isinstance(frame, fitdecode.records.FitDataMessage):
                    if frame.name == 'record':
                        location_json= {}
                        if frame.has_field('position_lat') and frame.has_field('position_long'):
                            location_json['latitude'] = frame.get_value('position_lat')
                            location_json['longitude'] = frame.get_value('position_long')
                            location_json['timestamp'] = frame.get_value('timestamp').strftime("%d-%b-%Y %H:%M:%S.%f")
                            location_json['enhanced_speed'] = frame.get_value('enhanced_speed')
                            location_json['enhanced_altitude'] = frame.get_value('enhanced_altitude')
                            location_json['distance'] = frame.get_value('distance')
                            result.append(location_json)

                    else:
                        continue

        activity_data = Activity.query.filter_by(garmin_id=garmin_user_id, activityid=activity_id).first()

        if activity_data is not None:
            activity_data.location_data = json.dumps(result)
            update_item(activity_data)
        else:
            location = add_location(json.dumps(result))
            add_item(location)


# test api to get fit files
@garmin_api.route('/test', methods=['GET','POST'])
def test():
    data = request.get_json()
    activityfiles = data["activityFiles"]
    for item in activityfiles:
        garmin_user_id = item["userId"]
        access_token = item["userAccessToken"]
        activityFile_url = item["callbackURL"]
        activity_id = str(item["activityId"])
        manual = item["manual"]

        garmin_user = GarminUsers.query.filter_by(access_token=access_token,deleted_at=None).first()

        garmin_OAuth = OAuth1Session(oauth_consumer_key, client_secret=oauth_consumer_secret,
                                     signature_method='HMAC-SHA1', resource_owner_key=garmin_user.access_token,
                                     resource_owner_secret=garmin_user.access_token_secret)
        response = garmin_OAuth.get(activityFile_url)

        open("garminActivity/"+activity_id+'.fit', "wb").write(response.content)

        fitfile = fitparse.FitFile('garminActivity/'+activity_id+'.fit', check_crc=False, data_processor=None)

        if fitfile.get_messages('record'):

            location_json, result = {}, []

            # Get all data messages that are of type record
            for record in fitfile.get_messages('record'):

             # Go through all the data entries in this record
                for location_data in record:
                    if location_data.name == 'timestamp':
                        location_json[location_data.name] = location_data.value.strftime("%d-%b-%Y %H:%M:%S.%f")
                    else:
                        location_json[location_data.name] = location_data.value

                    result.append(location_json)

            if result:
                activity_data = Activity.query.filter_by(garmin_id=garmin_user_id,activityid=activity_id).first()

                if activity_data is not None:
                    activity_data.location_data = json.dumps(result)
                    update_item(activity_data)
                else:
                    location = add_location(json.dumps(result))
                    add_item(location)

        else:
            continue

    return success("SUCCESS",meta={'message':'Location Data retrived!'})





