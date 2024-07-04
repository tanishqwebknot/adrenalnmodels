import datetime
import json
import os

from flask import jsonify, request
from api.Post.models import UserBucket
from api.Users.models import Users, UserProfile, Membership, UserDevice, Verification, Device
from api.contact.models import Contact
from api.media.models import Media
from api.media.services import get_media_access
from api.profile.models import Experties_background, Programme, CustomerTestimonials, FeaturedMedia, Hall_of_fame, \
    Sport_level, Fitness_level
from app import bcrypt
from common.connection import add_item, update_item
from common.response import success, failure
from common.utils.validator import is_valid_password
from google.oauth2 import id_token
from config import GOOGLE_CLIENT_ID, MOBILE_GOOGLE_CLIENT_ID, IOS_GOOGLE_CLIENT_ID
from middleware.auth import get_jwt


def create_user(data):
    date_today = datetime.datetime.now()
    days = datetime.timedelta(days=10)
    past_date = date_today - days
    fcm_token=data.get('fcm_token',None)
    new_user = Users(email=data['email'], phone=data['phone'],
                     phone_code=data['phone_code'])
    add_item(new_user)
    membership = Membership(user_id=new_user.id,
                            membership_type='general',
                            membership_status='pending',
                            phone_verified=True,
                            email_verified=True,last_feed_viewed=past_date,
                            role='user',fcm_token=fcm_token,post_visibility='all'
                            )
    add_item(membership)
    return new_user


def update_user_basic_details(data, user_id):
    new_user = Users.query.filter_by(id=user_id,user_deleted_at=None,deleted_at=None).first()
    first_name = data.get('name')
    nickname =  data.get('nickname')
    password = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')

    new_user.nickname = nickname.title()
    new_user.first_name = first_name.title()

    password_validation =data['password']
    if not password_validation:
        return failure("Invalid Password")

    new_user.password = password
    update_item(new_user)
    membership = Membership.query.filter_by(user_id=user_id, membership_type='general').first()
    membership.encrption_type = 'bcrypt'
    membership.password = password
    membership.membership_status = 'active'
    update_item(membership)
    return new_user


def verify_password(user, password, membership_type='general', password_required=True):
    membership = Membership.query.filter_by(user_id=user.id, membership_type=membership_type).first()
    if membership:
        if password_required and bcrypt.check_password_hash(str(membership.password), password):
            return membership
        elif membership and password_required == False:
            return membership
        else:
            return None
    else:
        return None


def user_list(data):
    new_user = Users(email=data['mobile_number'], phone=data['phone'], phone_code=data['phone_code'])
    return new_user


# Function to generate OTP
def generate_OTP():
    try:
        n = 4
        from random import randint
        random_number = ''.join(["%s" % randint(0, 9) for num in range(0, n)])
        return random_number
    except Exception as err:
        return None


def generate_session_code():
    try:
        n = 8
        from random import randint
        random_number = ''.join(["%s" % randint(0, 9) for num in range(0, n)])
        return random_number
    except Exception as err:
        return None


def membership():
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    membership_details = Membership(phone_verified='True', email_verified='false',
                                    registered_from='Adrenaline_account', password=Users.password,
                                    password_salt=Users.password,
                                    last_login='')
    return membership_details


def userprofile(data):
    update_user_profile = UserProfile(education_quelification=data['education_quelification'],
                                      college_name=data[' college_name'], work_place=data['college_name'],
                                      marital_status=data['marital_status'])
    return update_user_profile


def create_otp(verification_type, payload):
    otp = generate_OTP()
    verification = Verification(
        type=verification_type,
        payload=json.dumps(payload),
        code=otp,
        attempts=0
    )
    return verification


def create_login_otp(verification_type, phone):
    otp = generate_OTP()
    verification = Verification(
        payload=phone,
        type=verification_type,
        code=otp,
        attempts=0
    )
    return verification


def verify_otp(type, verification_id, code):
    debug = int(os.environ['DEBUG_MODE'])
    if debug:
        verification_data = Verification.query.filter_by(id=verification_id, type=type).first()
    else:
        verification_data = Verification.query.filter_by(id=verification_id, code=code, type=type).first()
    if verification_data:
        status = True
        payload = json.loads(verification_data.payload)

    else:
        status = False
        payload = {}
    return status, payload


def send_otp_login():
    otp = generate_OTP()
    verification = Verification(

        code=otp,
        attempts=0
    )
    return verification


def update_existiong_user(data, users_id):
    update_existiong_user = Users.query.filter_by(id=users_id,deleted_at=None,user_deleted_at=None).first()
    name = data['name']
    nickname = data['nickname']
    date_of_birth = data['date_of_birth']
    gender = data['gender']
    city = data['city']
    can_follows = data.get('can_follows', False)
    business_account = data.get('business_account', False)
    if not date_of_birth:
        return failure('Please Enter date_of_birth')
    if not gender:
        return failure('Please Enter gender')
    if not city:
        return failure('Please Enter city')

    update_existiong_user.first_name = name.title()
    update_existiong_user.nickname = nickname.title()
    update_existiong_user.date_of_birth = date_of_birth
    update_existiong_user.gender = gender
    update_existiong_user.city = city
    update_existiong_user.can_follows = can_follows
    update_existiong_user.business_account = business_account

    if data.get('profile_image', None):
        update_existiong_user.profile_image = data.get('profile_image')
        media_image = Media.query.filter_by(id=data.get('profile_image').get('media_id'), source_type='gallery').first()
        if media_image:
            media_image.source_type = 'profile_image'
            update_item(media_image)
    user_membership = Membership.query.filter_by(user_id=users_id).first()

    if business_account:
        user_membership.role = 'business'
        update_item(user_membership)
    else:
        user_membership.role = 'user'
        update_item(user_membership)
    return update_existiong_user


def update_user_info(data, current_user):
    update_existiong_user = Users.query.filter_by(current_user.id,user_deleted_at=None,deleted_at=None).first()
    if update_existiong_user:
        education_qualification = data.get('highest_qualification', None)
        college_name = data.get('college_name', None)
        work_place = data.get('work_place', None)
        marital_status = data.get('marital_status', None)

        update_existiong_user.education_qualification = education_qualification
        update_existiong_user.college_name = college_name
        update_existiong_user.work_place = work_place
        update_existiong_user.marital_status = marital_status
        update_item(update_existiong_user)

    return success("SUCCESS", {"message": "user details updated successfully !"})


def update_user_details(current_user, data):
    first_name = data.get('name')
    nickname = data.get('nickname')
    business_account = data.get('business_account')
    existiong_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    user_membership = Membership.query.filter_by(user_id=current_user.id).first()
    if existiong_user:
        existiong_user.education_qualification = data.get('highest_qualification')
        existiong_user.college_name = data.get('college_name')
        existiong_user.work_place = data.get('work_place')
        existiong_user.marital_status = data.get('marital_status')
        existiong_user.first_name = first_name.title()
        existiong_user.nickname = nickname.title()
        existiong_user.date_of_birth = data.get('date_of_birth')
        existiong_user.gender = data.get('gender')
        existiong_user.city = data.get('city')
        existiong_user.can_follows = data.get('can_follows')
        existiong_user.business_account = data.get('business_account')
        existiong_user.profile_image = data.get('profile_image')
        update_item(existiong_user)
        if business_account:
            user_membership.role = 'business'
            update_item(user_membership)
        else:
            user_membership.role = 'user'
            update_item(user_membership)


def get_basic_details(current_user):
    result=[]
    user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    followers = Contact.query.filter_by(contact_id=current_user.id,is_following=True,deleted_at=None,following_status='following').count()
    user_data = {}
    user_data['name'] = user.first_name
    user_data['email_id'] = user.email
    user_data['nickname'] = user.nickname
    user_data['phone'] = user.phone
    user_data['can_follows'] = user.can_follows
    user_data['business_account'] = user.business_account
    user_data['profile_image'] = user.profile_image
    user_data['date_of_birth'] = user.date_of_birth
    user_data['city'] = user.city
    user_data['highest_qualification'] = user.education_qualification
    user_data['gender'] = user.gender
    user_data['college_name'] = user.college_name
    user_data['work_place'] = user.work_place
    user_data['marital_status'] = user.marital_status
    user_data['profile_image'] = user.profile_image
    if followers:
        user_data['followers_count'] = followers
    result.append(user_data)
    return success('SUCCESS',result,meta={'message':'User Basic Details'})


def devices_ver(device_verification_id):
    device_verification_data = UserDevice.query.filter_by(id=device_verification_id).first()
    return device_verification_data


def addDevice(data):
    device = Device(fingerprint=data.get('fingerprint'), device_name=data.get('device_name', None),
                    device_type=data.get("device_type", None), os=data.get("os", None),
                    os_version=data.get("os_version", None),
                    browser=data.get("browser", None), browser_version=data.get("browser_version", None),
                    app_type=data.get("app_type", None), app_version=data.get("app_version", None),
                    device_ip=data.get("device_ip", None),
                    status='ACTIVE')
    add_item(device)
    return device


def get_user_profile_details(user_id):
    try:
        user = Users.query.filter_by(id=user_id, deleted_at=None,user_deleted_at=None).first()
        user_membership = Membership.query.filter_by(user_id=user_id, deleted_at=None).first()
        user_data = {}
        total_bar_count = 0
        if user:
            user_data['id'] = user.id
            user_data['name'] = user.first_name
            user_data['email_id'] = user.email
            user_data['phone_code'] = user.phone_code
            user_data['phone'] = user.phone
            user_data['nickname'] = user.nickname
            user_data['can_follows'] = user.can_follows
            user_data['business_account'] = user.business_account
            user_data['profile_image'] = user.profile_image
            user_data['role'] = user_membership.role
            user_data['default_visibility'] = user_membership.post_visibility

            user_hall_of_fame = Hall_of_fame.query.filter_by(user_id=user_id, deleted_at=None).first()
            user_sport_level = Sport_level.query.filter_by(user_id=user_id, deleted_at=None).first()
            user_fitness_level = Fitness_level.query.filter_by(user_id=user_id, deleted_at=None).first()
            user_primary_sport = Sport_level.query.filter_by(user_id=user_id, deleted_at=None, is_primary=True).first()
            user_secondaary_sport = Sport_level.query.filter_by(user_id=user_id, deleted_at=None,
                                                                is_primary=False).first()
            if user_hall_of_fame:
                total_bar_count = total_bar_count + 1
            if user_sport_level:
                total_bar_count = total_bar_count + 1
            if user_fitness_level:
                total_bar_count = total_bar_count + 1
            if user_primary_sport:
                total_bar_count = total_bar_count + 1
            if user_secondaary_sport:
                total_bar_count = total_bar_count + 1
            if user.business_account == False:
                user_data['bar_count'] = total_bar_count

            else:
                user_expertise = Experties_background.query.filter_by(user_id=user_id, deleted_at=None).first()
                user_media = FeaturedMedia.query.filter_by(user_id=user_id, deleted_at=None).first()
                user_programme = Programme.query.filter_by(user_id=user_id, deleted_at=None).first()
                user_testimonial = CustomerTestimonials.query.filter_by(name=user.first_name, deleted_at=None).first()
                if user_expertise:
                    total_bar_count = total_bar_count + 1
                if user_media:
                    total_bar_count = total_bar_count + 1
                if user_programme:
                    total_bar_count = total_bar_count + 1
                if user_testimonial:
                    total_bar_count = total_bar_count + 1
                user_data['bar_count'] = total_bar_count
            return user_data
        else:
            return success("SUCCESS",meta={'message':'User Not Registered'})
    except Exception as e:
        return failure("Something went wrong.")


def user_profile_details(user_id):
    user = Users.query.filter_by(id=user_id, deleted_at=None, user_deleted_at=None).first()
    user_membership = Membership.query.filter_by(user_id=user_id, deleted_at=None, membership_status='active').first()
    followers = Contact.query.filter_by(contact_id=user_id, is_following=True, deleted_at=None,
                                        following_status='following').count()
    user_data = {}
    total_bar_count = 0
    if user:
        user_data['id'] = user.id
        user_data['name'] = user.first_name
        user_data['nickname'] = user.nickname
        user_data['email_id'] = user.email
        user_data['phone'] = user.phone
        user_data['phone_code'] = user.phone_code
        user_data['can_follows'] = user.can_follows
        user_data['business_account'] = user.business_account
        user_data['role'] = user_membership.role
        user_data['highest_qualification'] = user.education_qualification
        user_data['work_place'] = user.work_place
        user_data['college_name'] = user.college_name
        user_data['gender'] = user.gender
        user_data['city'] = user.city
        user_data['marital_status'] = user.marital_status
        user_data['date_of_birth'] = user.date_of_birth
        user_data['profile_image'] = user.profile_image

        if followers:
            user_data['followers_count'] = followers

        user_hall_of_fame = Hall_of_fame.query.filter_by(user_id=user_id, deleted_at=None).first()
        user_sport_level = Sport_level.query.filter_by(user_id=user_id, deleted_at=None).first()
        user_fitness_level = Fitness_level.query.filter_by(user_id=user_id, deleted_at=None).first()
        user_primary_sport = Sport_level.query.filter_by(user_id=user_id, deleted_at=None, is_primary=True).first()
        user_secondaary_sport = Sport_level.query.filter_by(user_id=user_id, deleted_at=None,
                                                            is_primary=False).first()
        if user_hall_of_fame:
            total_bar_count = total_bar_count + 1
        if user_sport_level:
            total_bar_count = total_bar_count + 1
        if user_fitness_level:
            total_bar_count = total_bar_count + 1
        if user_primary_sport:
            total_bar_count = total_bar_count + 1
        if user_secondaary_sport:
            total_bar_count = total_bar_count + 1

        if user.business_account == False:
            user_data['bar_count'] = total_bar_count

        else:
            user_expertise = Experties_background.query.filter_by(user_id=user_id, deleted_at=None).first()
            user_media = FeaturedMedia.query.filter_by(user_id=user_id, deleted_at=None).first()
            user_programme = Programme.query.filter_by(user_id=user_id, deleted_at=None).first()
            user_testimonial = CustomerTestimonials.query.filter_by(name=user.first_name, deleted_at=None).first()
            if user_expertise:
                total_bar_count = total_bar_count + 1
            if user_media:
                total_bar_count = total_bar_count + 1
            if user_programme:
                total_bar_count = total_bar_count + 1
            if user_testimonial:
                total_bar_count = total_bar_count + 1
            user_data['bar_count'] = total_bar_count
        return user_data
    else:
        return success("SUCCESS", meta={'message': 'User Not Registered'})


def update_fcm_token(current_user,data):
    fcm_token = data.get('fcm_token', None)
    existing_user =Membership.query.filter_by(user_id=current_user.id,membership_type='general', deleted_at=None).first()
    if existing_user:
        existing_user.fcm_token = fcm_token
        update_item(existing_user)
        return success('SUCCESS' , meta={'message':'fcm_token is updated'})
    else:
        return success('SUCCESS', meta={'message':'user id is does not exit'})


def gmail_login(data):
    source = data.get('source', None)
    token_type = data.get('type', None)
    token = data.get('token', None)
    device_verification_id = data.get('device_verification_id', None)
    """
        This function is to validate the user credentials for google login
        @param type:
        @param data: Dict
        @return:
    """
    try:
        if source =='GMAIL':
            from google.auth.transport import requests
            if token_type == 'WEB':
                id_info = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
            elif token_type == 'MOBILE':
                id_info = id_token.verify_oauth2_token(token, requests.Request(), MOBILE_GOOGLE_CLIENT_ID)
            elif token_type == 'IOS':
                id_info = id_token.verify_oauth2_token(token, requests.Request(), IOS_GOOGLE_CLIENT_ID)

            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                return success('SUCCESS', meta={'message': 'Wrong issuer'})

            id_info['is_token_email'] = id_info.get('email', "")
            id_info['is_token_given_name'] = id_info.get('given_name', ""),
            id_info['is_token_family_name'] = id_info.get('family_name', "")

            # registration
            if id_info['is_token_email']:
                is_user = Users.query.filter_by(email=id_info['is_token_email'],deleted_at=None,user_deleted_at=None).first()
                device = Device.query.filter_by(id=device_verification_id).first()
                if is_user:
                    membership = Membership.query.filter_by(user_id=is_user.id,
                                                            deleted_at=None).first()
                    user_device = UserDevice.query.filter_by(user_id=is_user.id).first()
                    if user_device and device and membership.membership_status =='active':
                        data['is_new_user'] = False
                        session_code = update_session_code(user_id=is_user.id, device_id=user_device.device_id)
                        token = get_jwt(is_user.id, 'general', session_code)
                        data['user_info'] = get_user_profile_details(is_user.id)
                        data['status'] = membership.membership_status
                        data['token']=token
                        return success('SUCCESS',data,meta={'message':'User Already registerd'})

                    session_code = update_session_code(user_id=is_user.id, device_id=user_device.device_id)
                    token = get_jwt(is_user.id, 'general', session_code)
                    res={}
                    res['status'] = membership.membership_status
                    res['token'] = token
                    res['user_info'] = get_user_profile_details(is_user.id)
                    res['is_new_user'] = False
                    return success('SUCCESS',res,meta={'message':'User Already Registered'})
                else:
                    date_today = datetime.datetime.now()
                    days = datetime.timedelta(days=10)
                    past_date = date_today - days
                    if device:
                        new_user = Users(email=id_info['is_token_email'])
                        user_new = add_item(new_user)
                        membership = Membership(user_id=new_user.id,
                                                membership_type='general',
                                                membership_status='pending',
                                                phone_verified=True,
                                                email_verified=True,
                                                role='user', post_visibility='all',last_feed_viewed=past_date
                                                )
                        add_item(membership)
                        user_id = user_new.id
                        session_code = generate_session_code()
                        device.session_code = session_code
                        update_item(device)
                        user_device = UserDevice(user_id=user_id, device_id=device.id, session_code=session_code,
                                                 status='ACTIVE')
                        add_item(user_device)
                        token = get_jwt(user_id, 'general', session_code)
                        data['status'] = 'pending'
                        data['user_info'] = get_user_profile_details(user_id)
                        data['id_info'] = id_info
                        data['is_new_user'] = True
                        data['token'] = token
                        return success('SUCCESS', data, meta={'message': 'success'})

        if source == 'APPLE':
            return ("APPLE")

        if source == 'FACEBOOK':
            import requests
            response = requests.get(
                "https://graph.facebook.com/v2.5/me?fields=email,name,friends&access_token=" + token)
            user_data = response.json()
            # registration
            if user_data['email']:
                is_user = Users.query.filter_by(email=user_data['email'], deleted_at=None,user_deleted_at=None).first()
                device = Device.query.filter_by(id=device_verification_id).first()
                if is_user:
                    membership = Membership.query.filter_by(user_id=is_user.id,
                                                            deleted_at=None).first()
                    user_device = UserDevice.query.filter_by(user_id=is_user.id).first()
                    if user_device and device and membership.membership_status == 'active':
                        data['is_new_user'] = False
                        session_code = update_session_code(user_id=is_user.id, device_id=user_device.device_id)
                        token = get_jwt(is_user.id, 'general', session_code)
                        data['user_info'] = get_user_profile_details(is_user.id)
                        data['status'] = membership.membership_status
                        data['token'] = token
                        return success('SUCCESS', data, meta={'message': 'User Already registerd'})

                    session_code = update_session_code(user_id=is_user.id, device_id=user_device.device_id)
                    token = get_jwt(is_user.id, 'general', session_code)
                    res = {}
                    res['status'] = membership.membership_status
                    res['token'] = token
                    res['user_info'] = get_user_profile_details(is_user.id)
                    res['is_new_user'] = False
                    return success('SUCCESS', res, meta={'message': 'User Already Registered'})
                else:
                    date_today = datetime.datetime.now()
                    days = datetime.timedelta(days=10)
                    past_date = date_today - days
                    if device:
                        new_user = Users(email=user_data['email'])
                        user_new = add_item(new_user)
                        membership = Membership(user_id=new_user.id,
                                                membership_type='general',
                                                membership_status='pending',
                                                phone_verified=True,
                                                email_verified=True,
                                                role='user', post_visibility='all', last_feed_viewed=past_date
                                                )
                        add_item(membership)
                        user_id = user_new.id
                        session_code = generate_session_code()
                        device.session_code = session_code
                        update_item(device)
                        user_device = UserDevice(user_id=user_id, device_id=device.id, session_code=session_code,
                                                 status='ACTIVE')
                        add_item(user_device)
                        token = get_jwt(user_id, 'general', session_code)
                        data['status'] = 'pending'
                        data['user_info'] = get_user_profile_details(user_id)
                        data['id_info'] = user_data
                        data['is_new_user'] = True
                        data['token'] = token
                        return success('SUCCESS', data, meta={'message': 'success'})
            else:
                return success('SUCCESS', meta={'message': 'No email found'})
            return success('SUCCESS', meta={'message': 'success'})
    except Exception:
        return success('SUCCESS', meta={'message': 'Invalid token type or token'})


def update_session_code(user_id, device_id=None, update_device=True):
    session_code = generate_session_code()
    if device_id:
        user_devices = UserDevice.query.filter_by(user_id=user_id, device_id=device_id).all()
        if not user_devices:
            user_device = UserDevice(user_id=user_id, device_id=device_id, session_code=session_code, status='ACTIVE')
            add_item(user_device)
        if update_device:
            devices = Device.query.filter_by(id=device_id).first()
            devices.session_code = session_code
            update_item(devices)
    else:
        user_devices = UserDevice.query.filter_by(user_id=user_id).all()
    for user_device in user_devices:
        user_device.session_code = session_code
        update_item(user_device)
    return session_code