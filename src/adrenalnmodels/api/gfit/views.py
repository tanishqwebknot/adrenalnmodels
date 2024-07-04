import os
import json

import flask
import google_auth_oauthlib
import google.oauth2.credentials
import google_auth_oauthlib.flow
import httplib2
import requests
from datetime import datetime
import time
import datetime
import json
from urllib.parse import urlparse, parse_qs
from datetime import timedelta
from googleapiclient.discovery import build
from dateutil.relativedelta import relativedelta
from flask import request, jsonify, url_for, Blueprint
from oauth2client.client import OAuth2WebServerFlow, flow_from_clientsecrets
from oauth2client.client import Credentials

from oauth2client.file import Storage
from werkzeug.utils import redirect

from api.garmin_users.models import GarminUsers
from api.gfit.models import GfitUsers
from api.gfit.services import oauth_creds, add_activity, exchange_token
from api.watch.models import Activity, User_activity_mapping
from common.connection import add_item, update_item
from common.response import failure, success
from middleware.auth import token_required
from dotenv import load_dotenv

load_dotenv()

DATA_SOURCE = "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
CREDENTIALS_FILE = "api/gfit/client_secret/"

gfit_api = Blueprint('gfit_api', __name__, url_prefix='/googleFit')


# api for user login
@gfit_api.route('/login', methods=['POST'])
@token_required
def auth_data(current_user):
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file('secret_key.json', scopes=[os.environ.get('OAUTH_SCOPE'),os.environ.get('OAUTH_SCOPE_2')])
    flow.redirect_uri = os.environ.get('REDIRECT_URI')
    authorization_url, state = flow.authorization_url(prompt='consent',access_type='offline')
    return success("SUCCESS", authorization_url,meta={'message':'Authorization URL'})


# api to get user permission
@gfit_api.route('/getcode', methods=['GET'])
def get_code():
    return success("SUCCESS",meta={'message':'User Verified'})


# api to get access token and refresh token
@gfit_api.route('/syncdata', methods=['GET', 'POST'])
@token_required
def user_permission(current_user):
    today_date = datetime.date.today()
    existing_user = GfitUsers.query.filter_by(user_id=current_user,deleted_at=None).first()
    if not existing_user or today_date > existing_user.refresh_token_exp:
        state = request.args.get('state')
        oauth_code = request.args.get('code')
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            'secret_key.json', scopes=[os.environ.get('OAUTH_SCOPE'),os.environ.get('OAUTH_SCOPE_2')], state=state)
        flow.redirect_uri = os.environ.get('REDIRECT_URI')

        authorization_response = flask.request.url
        authorization_response = os.environ.get('APP_BASE_URL') + flask.request.full_path
        flow.fetch_token(authorization_response=authorization_response)
        credentials = flow.credentials
        refresh_token = credentials.refresh_token
        access_token = credentials.token
        datetime.datetime.now()
        exp_date = datetime.date.today() + relativedelta(months=+5)
        user_creds = GfitUsers.query.filter_by(user_id=current_user,deleted_at=None).first()

        if user_creds is not None:
            user_creds.access_token = access_token
            # user_creds.token_uri = token_uri
            user_creds.refresh_token = refresh_token
            user_creds.auth_code = oauth_code
            user_creds.refresh_token_exp = exp_date
            update_item(user_creds)
        else:
            user_creds = oauth_creds(access_token,refresh_token,oauth_code,current_user,exp_date)
            add_item(user_creds)
        return success("SUCCESS",meta={'message':'Token Generated Successfully!'})
    else:
        return success("SUCCESS",meta={'message':'User already Registered!'})


# api to get activity from google fit
@gfit_api.route('/getdata', methods=['GET', 'POST'])
def getdata():
    user_creds = GfitUsers.query.filter_by(deleted_at=None,deregister_at=None).all()
    if user_creds:
        for user in user_creds:
            get_user_activity(user.user_id)
        return success("SUCCESS",meta={'message':'Google FIT Data'})


@gfit_api.route('/gfitdata', methods=['GET', 'POST'])
@token_required
def getgfitdata(current_user):
    user_creds = GfitUsers.query.filter_by(user_id=current_user,deleted_at=None,deregister_at=None).first()
    if user_creds:
        get_user_activity(user_creds.user_id)
        return success("SUCCESS",meta={'message':'Google FIT Data'})
    else:
        return success("SUCCESS", meta={'message': 'User Not Registered'})

# function to get activity from google fit
def get_user_activity(current_user):
    curr_date = datetime.datetime.now().isoformat("T", "milliseconds") + "Z"
    user_creds = GfitUsers.query.filter_by(user_id=current_user,deleted_at=None,deregister_at=None).first()

    if user_creds is not None:

        if user_creds.activity_last_synced is None:
            past_date = datetime.datetime.today() - timedelta(days=90)
            past_date = past_date.isoformat("T", "milliseconds") + "Z"

            #token exhange func
            res = exchange_token(current_user)
            url = 'https://www.googleapis.com/fitness/v1/users/me/sessions'
            # url = "https://www.googleapis.com/fitness/v1/users/me/sessions?startTime=" + past_date + "&endTime=" + curr_date
            # url = "https://www.googleapis.com/fitness/v1/users/me/sessions?startTime=" + past_date + "&endTime=" + curr_date
            # url = 'https://www.googleapis.com/fitness/v1/users/me/dataSources'
            user_data = requests.get(url, headers={"Authorization": "Bearer {}".format(user_creds.access_token)})
            resp = json.loads(user_data.text)
            sessions = resp['session']

            # updating last sync time
            user_creds.activity_last_synced = curr_date
            update_item(user_creds)
            if sessions:
                for session in sessions:
                    activityid = session["id"]
                    existing_data = Activity.query.filter_by(activityid=session["id"]).first()
                    if not existing_data:
                        summary = {"startTimeMillis": session["startTimeMillis"], "endTimeMillis": session["endTimeMillis"],
                                   "modifiedTimeMillis": session["modifiedTimeMillis"]}
                        session["summary"] = summary
                        session["summaryId"] = 'None'
                        session["samples"] = 'None'
                        session["laps"] = 'None'
                        user_activity = add_activity(session, source='google_fit')
                        add_item(user_activity)

                    gfit_user = GfitUsers.query.filter_by(user_id=current_user,deleted_at=None).all()
                    for user in gfit_user:
                        activity_data = Activity.query.filter_by(activityid=activityid).first()
                        mapping_data = User_activity_mapping(user_id=user.user_id, activity_table_id=activity_data.id)
                        add_item(mapping_data)

        else:
            past_date = user_creds.activity_last_synced
            past_date = past_date.isoformat("T", "milliseconds") + "Z"
            past_date = past_date.replace("+", " ")

            # token exhange func
            res = exchange_token(current_user)

            url = 'https://www.googleapis.com/fitness/v1/users/me/sessions'
            # url = "https://www.googleapis.com/fitness/v1/users/me/sessions?startTime=" + past_date + "&endTime=" + curr_date
            # url = 'https://www.googleapis.com/fitness/v1/users/me/dataSources'

            user_data = requests.get(url, headers={"Authorization": "Bearer {}".format(user_creds.access_token)})
            resp = json.loads(user_data.text)
            sessions = resp['session']

            #updating last sync time
            user_creds.activity_last_synced = curr_date
            update_item(user_creds)

            if sessions:
                for session in sessions:
                    activityid = session["id"]
                    existing_data = Activity.query.filter_by(activityid=activityid).first()
                    if not existing_data:
                        summary = {"startTimeMillis": session["startTimeMillis"], "endTimeMillis": session["endTimeMillis"],
                                   "modifiedTimeMillis": session["modifiedTimeMillis"]}
                        session["summary"] = summary
                        session["summaryId"] = 'None'
                        session["samples"] = 'None'
                        session["laps"] = 'None'
                        user_activity = add_activity(session, source='google_fit')
                        add_item(user_activity)

                    gfit_user = GfitUsers.query.filter_by(user_id=current_user,deleted_at=None).all()
                    for user in gfit_user:
                        activity_data = Activity.query.filter_by(activityid=activityid).first()
                        mapping_data = User_activity_mapping(user_id=user.user_id, activity_table_id=activity_data.id)
                        add_item(mapping_data)

    else:
        return failure("User Not Registered!")


# user Deregistration from gfit
@gfit_api.route('/userDeregistration', methods=['GET'])
@token_required
def userDeregistration(user_id):
    user_creds = GfitUsers.query.filter_by(user_id=user_id,deleted_at=None).first()
    if user_creds:
        user_creds.deleted_at = datetime.datetime.now()
        user_creds.deregister_at = datetime.date.today()
        update_item(user_creds)
        return success("SUCCESS",meta={'message':'User Deregistered!'})
    else:
        return success("SUCCESS",meta={'message':'User Not Registered!'})










