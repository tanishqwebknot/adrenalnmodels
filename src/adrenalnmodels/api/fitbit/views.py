from flask import Flask, redirect, request, session, url_for,jsonify,send_file
import requests
from requests_oauthlib import OAuth2Session
import os
from flask import Blueprint
from dotenv import load_dotenv
from api.fitbit.models import FitbitUsers
from common.connection import add_item, update_item, delete_item
from common.response import failure, success

load_dotenv()
# This information is obtained upon registration of a new Fitbit application
FITBIT_CLIENT_ID = os.environ.get('FITBIT_CLIENT_ID')
FITBIT_CLIENT_SECRET =  os.environ.get('FITBIT_CLIENT_SECRET')
FITBIT_REDIRECT_URI = os.environ.get('FITBIT_REDIRECT_URI') # Should match exactly with the registered callback URL

# Fitbit API endpoints
FITBIT_AUTHORIZATION_BASE_URL = os.environ.get('FITBIT_AUTHORIZATION_BASE_URL')
FITBIT_TOKEN_URL = os.environ.get('FITBIT_TOKEN_URL')
FITBIT_SCOPE = ['weight','respiratory_rate' ,'social' ,'location'  ,'activity' ,'heartrate' ,'sleep' ,'oxygen_saturation' ,'cardio_fitness' ,'nutrition' ,'temperature settings', 'electrocardiogram ']


fitbit_api = Blueprint('fitbit_api', __name__, url_prefix='/fitbit')
# Secret key for session management. Use a random value in production.
fitbit_api.secret_key = os.urandom(24)

@fitbit_api.route('/fitbit_auth',methods=['GET'])
def index():
    """Step 1: User Authorization.
    Redirect the user to Fitbit for authorization.
    """
    fitbit = OAuth2Session(FITBIT_CLIENT_ID, scope=FITBIT_SCOPE, redirect_uri=FITBIT_REDIRECT_URI)
    authorization_url, state = fitbit.authorization_url(FITBIT_AUTHORIZATION_BASE_URL)

    # State is used to prevent CSRF. Keep this for later.
    session['oauth_state'] = state
    return jsonify({
        'authorization_url': authorization_url,
        'state': state
    })

@fitbit_api.route('/callback',methods=['POST'])
def callback():
    """Step 2: Callback from Fitbit.
    Fitbit redirects the user here after authorization.
    """
    data = request.get_json()
    authorization_res = data.get('authorization_response')
    print(request.url)
    fitbit = OAuth2Session(FITBIT_CLIENT_ID, state=session['oauth_state'], redirect_uri=FITBIT_REDIRECT_URI)
    token = fitbit.fetch_token(FITBIT_TOKEN_URL, client_secret=FITBIT_CLIENT_SECRET,
                               authorization_response=
                               authorization_res)
    
    # Save the token for future use
    session['oauth_token'] = token
    
    
    
    fitbit_user = FitbitUsers(
        fitbit_id=token['user_id'],
        scope=token['scope'],
        access_token=token['access_token'],
        expires_in=token['expires_in'],
        refresh_token=token['refresh_token'],
        expires_at=token['expires_at']
    )
    add_item(fitbit_user)
    return jsonify({
        'Success':"Sucesss",
        'access_token':token['access_token'],
        'refresh_token':token['refresh_token'], 
        'scope':token['scope'], 
        'user_id':token['user_id']
    })
