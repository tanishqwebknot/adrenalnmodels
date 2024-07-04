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
from api.gfit.models import GfitUsers
from api.watch.models import Activity
from app import db
import time
from flask import Flask, render_template, url_for, redirect, request, jsonify, Blueprint
from requests import Session
from requests_oauthlib import OAuth1Session
from sqlalchemy.orm import session

from api.watch.models import User_activity_mapping
from common.connection import add_item, update_item, delete_item
from common.response import failure, success
from middleware.auth import get_request_token
import datetime
from middleware import auth
from middleware.auth import token_required, get_jwt
from flask import request, g


watch = Blueprint('watch', __name__, url_prefix='/watch')


# api to get user permission
@watch.route('/user_status', methods=['GET'])
@token_required
def user_status(current_user):
    today_date = datetime.date.today()
    result=[]
    status={}
    gfit_user = GfitUsers.query.filter_by(user_id=current_user,deleted_at=None).first()
    garmin_user = GarminUsers.query.filter_by(user_id=current_user,deleted_at=None,deregister_at=None).first()
    if gfit_user:
        status['is_google_fit_connected']=True
        if gfit_user.refresh_token_exp >= today_date:
            print("inside 2nd if")
            status['is_google_fit_token_alive'] = True
        else:
            print("else")
            status['is_google_fit_token_alive'] = False

    else:
        status['is_google_fit_connected'] = False
        status['is_google_fit_token_alive'] = False
    if garmin_user and garmin_user.verifier != None:
        status['is_garmin_connected'] = True
    else:
        status['is_garmin_connected'] = False
    result.append(status)
    return success("SUCCESS",result)


#To fetch user activity from DB
@watch.route('/activity', methods=['GET'])
@token_required
def getActivities(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    all_user_activities=Activity.query.filter_by(user_id= current_user,deleted_at=None).all()
    user_activities=Activity.query.filter_by(user_id=current_user,deleted_at=None).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    user_activities = user_activities.items
    total_record = len(all_user_activities)
    total_pages = total_record // per_page + 1
    if user_activities is not None:
        result = []
        for activity in user_activities:
            userActivityData = {}
            userActivityData['id'] = activity.id
            userActivityData['summaryid'] = activity.summaryid
            userActivityData['activityid']=activity.activityid
            userActivityData['activityname'] = activity.activityname
            userActivityData['activitytype'] = activity.activitytype
            userActivityData['summary'] = activity.summary
            userActivityData['location_data'] = activity.location_data
            userActivityData['laps'] = activity.laps
            userActivityData['source'] = activity.source
            userActivityData['description'] = activity.description

            result.append(userActivityData)
        return success('SUCCESS', result, meta={'message': 'Activity List',
                                                'page_info': {'current_page': page, 'total_record': total_record,
                                                              'total_pages': total_pages,
                                                              'limit': per_page}})

    else:
        return failure("User Not Registered!")


# to fetch user activity by activityid
@watch.route('/activityDetails/<activity_id>', methods=['GET'])
@token_required
def activityDetails(current_user, activity_id):
    activity = Activity.query.filter_by(activityid=activity_id).first()
    userActivityData = {}
    if activity is not None:
        # for activity in user_activities:
        userActivityData['id'] = activity.id
        userActivityData['summaryid'] = activity.summaryid
        userActivityData['activityid'] = activity.activityid
        userActivityData['activityname'] = activity.activityname
        userActivityData['summary'] = activity.summary
        userActivityData['location_data'] = activity.location_data
        userActivityData['laps'] = activity.laps
        userActivityData['source'] = activity.source
        userActivityData['description'] = activity.description

        if activity.location_data:
            locationData = activity.location_data
        else:
            locationData = None
        userActivityData['locationData'] = locationData

    return success("SUCCESS",userActivityData,meta={'message':'Activity Details'})