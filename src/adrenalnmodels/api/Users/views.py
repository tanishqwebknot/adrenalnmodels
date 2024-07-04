import datetime
import json
import os
import re
from random import randint

from werkzeug.utils import redirect

import config
from api.Post.services import add_intermediate_post
from api.Users.models import Users, Verification, Device, UserDevice, Membership, Roles, Actions, RoleActions
from api.Users.services import create_user, update_user_basic_details, update_existiong_user, create_otp, verify_otp, \
    addDevice, generate_session_code, verify_password, update_user_info, update_user_details, get_basic_details, \
    get_user_profile_details, user_profile_details, update_fcm_token, gmail_login

from api.exceptions.exceptions import Exception, Error
from api.media.models import Media
from api.media.services import get_media_access
from common.connection import add_item, update_item
from common.helper import update_session
from common.response import success, failure
from common.utils.validator import validate_name, validate_password
from app import db, bcrypt
from common.utils.validator import validate_email, validate_mobile_number
from middleware import auth
from middleware.auth import get_jwt, validate_token, token_required
from flask import request, g, url_for, session, Blueprint
# from flasgger import swag_from
# from application import oauth

users_api = Blueprint('user', __name__, url_prefix='/user')
verification_api = Blueprint('verification', __name__, url_prefix='/verification')


# register device
@users_api.route('/device/register', methods=['POST'])
def device_requests():
    try:
        data = request.get_json()
        fingerprint=data.get('fingerprint',None)
        existing_user = Device.query.filter_by(fingerprint=fingerprint,deleted_at=None).first()
        if existing_user is None:
            device_details = addDevice(data)
            device = add_item(device_details)
            device_verification_id = device.id
        else:
            device_verification_id = existing_user.id
        device_id = {"device_verification_id": device_verification_id}
        return success('SUCCESS', device_id)
    except Exception as e:
        return failure("Something went wrong.")


# otp verfication for login
@verification_api.route('/email_phone', methods=['POST'])
@validate_token(action='update_user_details')
def email_verification_request(current_user):
    return verification_request('email_phone_verification')



# otp verfication for signup
@verification_api.route('/signup', methods=['POST'])
def singup_verification_request():
    return verification_request('signup')


# otp verfication for login
@verification_api.route('/login', methods=['POST'])
def login_verification_request():
    return verification_request('login')


# otp verfication for reset_password
@verification_api.route('/reset_password', methods=['POST'])
def resetPassword_verification_request():
    return verification_request('reset_password')


def verification_request(verification_type):
    try:
        data = request.get_json()
        verification_detail = data.get('verification_detail', None)
        new_email = verification_detail.get('email', None)
        new_phone = verification_detail.get('phone', None)
        new_phonecode = verification_detail.get('phone_code', None)
        if verification_type == 'email_phone_verification':
            if new_email:
                is_user = Users.query.filter_by(email=new_email, deleted_at=None, user_deleted_at=None).first()
                if is_user:
                    return success('SUCCESS', meta={'message': 'This email is already registered!'})
            if new_phone and new_phonecode:
                is_user = Users.query.filter_by(phone=new_phone,phone_code=new_phonecode, deleted_at=None, user_deleted_at=None).first()
                if is_user:
                    return success('SUCCESS', meta={'message': 'This number is already registered!'})

        device_verification_id = data.get('device_verification_id')
        Device_check = Device.query.filter_by(id=device_verification_id).first()
        if Device_check:
            verification_detail = data.get('verification_detail', {})
            verification_data = {'device_verification_id': device_verification_id}
            email = verification_detail.get('email', None)
            phone = verification_detail.get('phone', None)
            existing_email_user = None
            existing_phone_user = None
            if email:
                verification_data['email'] = email
                existing_email_user = Users.query.filter_by(email=email, deleted_at=None, user_deleted_at=None).first()
            if phone:
                verification_data['phone'] = phone
                if verification_detail.get('phone_code', None):
                    verification_data['phone_code'] = verification_detail.get('phone_code', None)
                    existing_phone_user = Users.query.filter_by(phone=phone,phone_code=new_phonecode, deleted_at=None, user_deleted_at=None).first()
            if verification_type == 'signup' and existing_email_user:
                return failure("Email id already exists")
            if verification_type == 'signup' and existing_phone_user:
                return failure("Phone Number already exists")
            elif verification_type in ['reset_password',
                                       'login'] and not existing_phone_user and not existing_email_user:
                return failure("User not exists")
            else:
                verification_type = create_otp(verification_type, verification_data)
                verification = add_item(verification_type)
                verification_id = verification.id
                vid = {"verification_id": verification_id}
                return success('SUCCESS', vid, {"message": "User verification created"})
        else:
            return failure("device id not found")

    except Exception as e:
        return failure("Something went wrong.")


@users_api.route('/signup/verification', methods=['POST'])
def verify():
    try:
        if request.method == 'POST':
            data = request.get_json()
            fcm_token=data.get('fcm_token',None)
            status, payload = verify_otp('signup', data['verification_id'], data['verification_code'])
            device_verification_id = payload.get('device_verification_id',None)
            device = Device.query.filter_by(id=device_verification_id).first()
            if status and device:
                if fcm_token:
                    payload['fcm_token'] = data['fcm_token']
                existing_user = Users.query.filter_by(email=payload['email'], phone=payload['phone'],
                                                      phone_code=payload['phone_code'],user_deleted_at=None,deleted_at=None).first()
                if existing_user:
                    return failure("Account already exist")
                else:
                    new_user = create_user(payload)
                    user_id = new_user.id
                    session_code = generate_session_code()
                    device.session_code = session_code
                    update_item(device)
                    user_device = UserDevice(user_id=user_id, device_id=device.id, session_code=session_code,
                                             status='ACTIVE')
                    add_item(user_device)
                    token = get_jwt(user_id, 'general', session_code)
                    token['status'] = 'pending'
                    token['user_info'] = get_user_profile_details(user_id)
                    return success("SUCCESS", token, {"message": "user created"})
            else:
                return failure("Incorrect OTP!!")

    except Exception as e:
        return failure("Something went wrong")


# Function to register account and send OTP email to verify user
@users_api.route('/signup/profile', methods=['POST'])
@validate_token(action='complete_signup', session=False, membership_status=None)
def update_me(current_user):
    try:

        data = request.get_json()
        user_id = current_user.id
        user_device = UserDevice.query.filter_by(user_id=user_id).first()
        device = Device.query.filter_by(id=user_device.device_id).first()
        if device and user_device:
            update_user_basic_details(data, user_id)
            session_code = update_session(user_id=user_id, device_id=user_device.device_id)
            token = get_jwt(user_id, 'general', session_code)
            return success("SUCCESS", token, {"message": "Details added successfully !"})
        else:
            return failure("Device not found")
    except Exception as e:
        return failure("Something went wrong.")


# Function to register account and send OTP email to verify user

@users_api.route('/basic_details', methods=['POST'])
@validate_token(action='update_basic_profile')
def updated_user(i):
    try:
        if request.method == 'POST':
            data = request.get_json()
            user_id = g.user_id
            existing_user = Users.query.filter_by(user_deleted_at=None,deleted_at=None,id=user_id).first()
            if existing_user is not None:
                users = update_existiong_user(data, user_id)
                update_item(users)
                # call add_intermediate_post func here
                viewed_post_list = []
                add_intermediate_post(str(user_id), viewed_post_list)
                return success("user details updated successfully !", {})
            else:
                return success("check details!", {})
    except Exception as e:
        return failure("Something went wrong.")


# Function to register account and send OTP email to verify user
@users_api.route('/userInfo', methods=['POST'])
@validate_token(action='update_educational_info')
def updated_userInfo(current_user):
    try:
        if request.method == 'POST':
            data = request.get_json()
            existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
            if existing_user is not None:
                return update_user_info(data, current_user)
            else:
                return success("SUCCESS", {"message": "check details!"})
    except Exception as e:
        return failure("Something went wrong.")


# edit user details
@users_api.route('/basic_details', methods=['PUT'])
@validate_token(action='edit_user_basic_detail')
def edit_user_details(current_user):
    data = request.json
    update_user_details(current_user, data)
    # call add_intermediate_post func here
    viewed_post_list = []
    add_intermediate_post(str(current_user.id), viewed_post_list)
    return success("SUCCESS", {"message": "Details Updated Succcessfully"})


# GET user details
@users_api.route('/basic_details', methods=['GET'])
@validate_token(action='get_user_basic_detail')
def get_user_details(current_user):
    try:
        sent_request = get_basic_details(current_user)
        return sent_request

    except Exception as e:
        return failure("Something went wrong.")


@users_api.route('/email/login', methods=['POST'])
def email_login():
    return login('email')


@users_api.route('/phone/login', methods=['POST'])
def phone_login():
    return login('phone')


@users_api.route('/otp/login', methods=['POST'])
def otp_login():
    return login('otp')


def login(login_type):
    try:
        data = request.json
        device_verification_id = data.get('device_verification_id')
        device = Device.query.filter_by(id=device_verification_id).first()
        if device:
            login_details = data["login_details"]
            membership_type = data.get("membership_type", 'general')
            # notification
            fcm_token = None
            if 'fcm_token' in login_details:
                fcm_token = login_details["fcm_token"]
            email, phone ,phone_code = None, None, None
            if 'email' in login_details:
                email = login_details["email"]
            if 'phone' in login_details:
                phone = login_details["phone"]
                phone_code = login_details["phone_code"]
            if 'otp' in login_details:
                phone = login_details["otp"]
            logged_in_user, existing_user, password = None, None, None
            password_required = True
            if login_type == 'email':
                password = data["login_details"]["password"]
                existing_user = Users.query.filter_by(email=email, user_deleted_at=None, deleted_at=None).first()
            elif login_type == "phone":
                password = data["login_details"]["password"]
                existing_user = Users.query.filter_by(phone_code=phone_code,phone=phone, user_deleted_at=None, deleted_at=None).first()
            elif login_type == "otp":
                password_required = False
                verification_id = data["login_details"]['verification_id']
                verification_code = data["login_details"]['verification_code']
                status, payload = verify_otp('login', verification_id, verification_code)
                if status:
                    # auth
                    existing_user = None
                    if 'email' in payload:
                        existing_user = Users.query.filter_by(email=payload['email'], user_deleted_at=None,
                                                              deleted_at=None).first()
                    elif 'phone' in payload:
                        existing_user = Users.query.filter_by(phone_code=payload['phone_code'],phone=payload['phone'], user_deleted_at=None,
                                                              deleted_at=None).first()
                    if 'membership_type' in payload:
                        membership_type = payload['membership_type']
                else:
                    return failure("INVALID_ACCOUNT_CREDENTIALS")
            if existing_user:
                membership = verify_password(existing_user, password, membership_type, password_required)
                if not membership:
                    return failure("INVALID_ACCOUNT_CREDENTIALS")
                membership.fcm_token = fcm_token
            else:
                return failure("INVALID_ACCOUNT_CREDENTIALS")
            session_code = update_session(user_id=existing_user.id, device_id=device.id)
            token = get_jwt(existing_user.id, membership_type, session_code)
            token['status'] = membership.membership_status
            token['user_info'] = get_user_profile_details(existing_user.id)
            return success('SUCCESS', token, meta={"message": "user login successfully!"})

        else:
            return failure("device id not found")
    except Exception as e:
        return failure("Something went wrong.")


@users_api.route('/reset_password/verification', methods=['POST'])
def verify_reset_password():
    try:
        data = request.get_json()
        status, payload = verify_otp('reset_password', data['verification_id'], data['verification_code'])
        if status:
            email = payload.get('email', None)
            phone = payload.get('phone', None)
            phone_code = payload.get('phone_code', None)
            device_verification_id = payload.get('device_verification_id')
            if not device_verification_id:
                return failure("Device verification missing")
            else:
                device = Device.query.filter_by(id=device_verification_id).first()
                if not device:
                    return failure("Invalid Device verification")
            if email:
                existing_user = Users.query.filter_by(email=payload['email'],user_deleted_at=None,deleted_at=None).first()
            elif phone:
                existing_user = Users.query.filter_by(phone=payload['phone'],user_deleted_at=None,deleted_at=None).first()
            else:
                existing_user = None
            if existing_user:
                user_id = existing_user.id
                user_membership = Membership.query.filter_by(user_id=user_id).first()
                user_membership_type = user_membership.membership_type
                update_session(user_id=user_id, device_id=device_verification_id)
                token = get_jwt(user_id, user_membership_type)
                return success("SUCCESS", token, {"message": "user created"})
        else:
            return failure("Incorrect OTP!!")
    except Exception as e:
        return failure("Something went wrong")


@users_api.route('/reset_password', methods=['POST'])
@validate_token(action='reset_password', session=False)
def new_password(current_user):
    try:
        data = request.get_json()
        existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
        if existing_user is not None:
            password = data.get('password', None)
            if password:
                password = bcrypt.generate_password_hash(password).decode('utf-8')
                existing_user.password = password
                update_item(existing_user)
                membership = Membership.query.filter_by(user_id=current_user.id).first()
                membership.password = password
                membership.password_update_on = datetime.datetime.now()
                update_item(existing_user)
                return success('SUCCESS', meta={'message': 'Password has been reset successfully!'})
        else:
            return failure("User Not exists")
    except Exception as e:
        print(e)
        return failure("Something went wrong")


@users_api.route('/validate_user_id', methods=['POST'])
def validate_user_id():
    data = request.json
    id = data['id']
    users = Users.query.filter_by(id=id,user_deleted_at=None,deleted_at=None).first()
    if users:
        return success("user is valid")
    else:
        return failure("users is invalid")


# testing
@users_api.route("/logout", methods=['GET'])
@validate_token(action='log_out')
def logout(current_user):
    session_code = g.session_code
    new_session = randint(10000000, 99999999)
    user_device = UserDevice.query.filter_by(user_id=current_user.id, session_code=session_code).first()
    user_membership = Membership.query.filter_by(user_id=current_user.id,membership_status='active').first()
    if user_device:
        device = Device.query.filter_by(id=user_device.device_id, session_code=session_code).first()
        user_device.session_code = new_session
        user_device.save()
        if device:
            device.session_code=new_session
            update_item(device)
    if user_membership:
        user_membership.last_login_attempts=datetime.datetime.now()
        user_membership.fcm_token=None
        update_item(user_membership)
    return success("SUCCESS", meta={"message": "user logout successfully !!"})


@users_api.route('/update_role', methods=['POST'])
@validate_token(action='update_user_role')
def update_roles(current_user):
    data = request.json
    key = data['key']
    user_role = Roles.query.filter_by(key=key, membership_type='general').first()
    if user_role:
        membership = Membership.query.filter_by(user_id=current_user.id, membership_type='general').first()
        if membership:
            membership.role = user_role.key
            update_item(membership)
            return success("SUCCESS", {"message": "User Role Updated !!"})
        else:
            return ("User not found")
    else:
        return failure("Role not Found")


@users_api.route('/action', methods=['POST'])
def create_action():
    data = request.json
    name = data['name']
    key = data['key']
    description = data['description']
    dependency = data['dependency']
    group = data['group']
    sorting_position = data['sorting_position']
    user_roles = Actions(name=name, key=key, description=description, dependency=dependency, group=group,
                         sorting_position=sorting_position)
    add_item(user_roles)


@users_api.route('/role_action', methods=['POST'])
def create_role_action():
    data = request.json
    role_key = data['role_key']
    action_key = data['action_key']
    status = data['status']
    role_actions = RoleActions(role_key=role_key, action_key=action_key, status=status)
    add_item(role_actions)
    return 'success'


@users_api.route('/short_info', methods=['GET'])
@token_required
def profile_short_info(current_user):
    result = get_user_profile_details(current_user)
    return result


#others info
@users_api.route('/user_profile_info/<user_id>', methods=['GET'])
@token_required
def user_profile_information(current_user, user_id):
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        user_exist = Users.query.filter_by(id=user_id, deleted_at=None,user_deleted_at=None).first()
        if user_exist:
            data = user_profile_details(user_id)
            return success('SUCCESS', data, meta={'message': 'User profile information'})
        else:
            return success('SUCCESS', meta={'message': 'User is not exist'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid user'})


@users_api.route('/fcm_token_update', methods=['PUT'])
@validate_token(action='updated_fcm_token')
def update_token(current_user):
    data = request.json
    result = update_fcm_token(current_user, data)
    return result


@users_api.route('/new_email_verification' , methods=['POST'])
@validate_token(action='email_verification')
def new_email(current_user):
    data = request.get_json()
    status, payload = verify_otp('email_phone_verification', data['verification_id'], data['verification_code'])
    device_verification_id = payload.get('device_verification_id', None)
    device = Device.query.filter_by(id=device_verification_id).first()
    if status and device:
        existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
        if existing_user:
            if payload and 'email' in payload:
                existing_user.email=payload['email']
                update_item(existing_user)
            if payload and 'phone' in payload and 'phone_code' in payload:
                existing_user.phone = payload['phone']
                existing_user.phone_code = payload['phone_code']
            update_item(existing_user)
            return success('SUCCESS', meta={'message':' User details are updated'})
    else:
        return success('SUCCESS', meta={"message":"Incorrect OTP"})


@users_api.route('/social_login', methods=['POST'])
def user_gmail_login():
    data = request.json
    return gmail_login(data)


