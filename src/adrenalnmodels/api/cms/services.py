import datetime
import json
import os
import pathlib
import uuid
import csv

import boto3
import pytz
from dateutil import parser
import xlsxwriter
from flask import jsonify, request
from sqlalchemy import or_, and_, exists, func
from werkzeug.utils import secure_filename
from api.Group.models import GroupMembers, Group
from api.Post.models import Post, BettingPost, PostCustomVisibility, AdminPost, AdminPostViews, UserBucket, \
    UserPostStatus, PostBucketMapping, MasterBucket, PostReact, ReportedPost, UserBettings
from api.Post.services import create_post, prepare_activity, prepare_betting, share_dynamic_link
from api.Users.models import Roles, Actions, RoleActions, Users, Membership
from api.Users.services import get_user_profile_details
from api.comment.models import Comment
from api.contact.models import Contact
from api.health_parameters.models import HealthProfile, HealthReport
from api.media.services import get_media_access
from api.notification.models import Notification
from api.notification.services import send_queue_message
from api.profile.models import Programme, MasterProgram, TermsConditions, Hall_of_fame, Sport_level, Fitness_level, \
    Experties_background, ContactMe, Master_course
from app import bcrypt, db
from common.connection import add_item, update_item, delete_item, _query_execution
from common.response import success, failure
from api.cms.grid_config import user_list as user_grid_fields
from api.cms.grid_config import cms_users_list as cms_user_grid_fields
from api.cms.grid_config import post_list as post_list_grid_fields
from config import UPDATE_TIMELINE_URL, AWS_REGION_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME, \
    PUSH_NOTIFICATION_URL


def user_role_list():
    roles = Roles.query.filter_by(membership_type='admin').all()
    result = []
    for role in roles:
        user_roles = {}
        user_roles['name'] = role.name
        user_roles['key'] = role.key
        user_roles['membership_type'] = role.membership_type
        result.append(user_roles)
    return success('SUCCESS', result, {"message": 'User Roels'})


def action_list():
    actions = Actions.query.all()
    result = []
    for action in actions:
        user_action = {}
        user_action['name'] = action.name
        user_action['key'] = action.key
        user_action['description'] = action.description
        user_action['group'] = action.group
        user_action['dependency'] = action.dependency
        user_action['group'] = action.group
        user_action['sorting_position'] = action.sorting_position
        result.append(user_action)
    return success('SUCCESS', result, {"message": 'User Action'})


def role_action_list(data):
    if data:
        page, per_page = data.get('page', 1), data.get('limit', 10)
    else:
        page = 1
        per_page = 10
    actions = RoleActions.query.filter_by(role_key=data.get('role_key')).paginate(
        page=page,
        per_page=per_page,
        error_out=False)

    actions = actions.items
    total_record = len(actions)
    total_pages = total_record // per_page + 1
    if actions:
        result = []
        for role in actions:
            # user_action = {}
            # user_action['action_key'] = role.action_key
            result.append(role.action_key)
        return success('SUCCESS', result, {"message": 'Admin Role',
                                           'page_info': {'total_record': total_record, 'total_pages': total_pages,
                                                         'limit': per_page}})
    else:
        return failure('FAILURE', {"message": 'No action for this role'})


def create_new_admin(data):
    role = data['role']
    name = data['name']
    email = data['email']
    password = data['password']
    password = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')
    existing_user = Users.query.filter_by(email=email,user_deleted_at=None,deleted_at=None).first()
    if existing_user:
        membership = Membership.query.filter_by(user_id=existing_user.id, membership_type='admin').first()
        if membership:
            return success('SUCCESS', {'message': 'Account Already Exists'})
        else:
            admin = Membership(user_id=existing_user.id, role=role, password=password, encrption_type='bcrypt',
                               membership_type='admin', membership_status='active')
            add_item(admin)
            return success('SUCCESS', {'message': 'Admin Account Created'})
    else:
        existing_user = Users(email=email, password=password, first_name=name, nickname=name)
        add_item(existing_user)
        admin = Membership(user_id=existing_user.id, role=role, password=password, encrption_type='bcrypt',
                           membership_type='admin', membership_status='active')
        add_item(admin)
        return success('SUCCESS', None, {'message': 'Admin Account created'})


def get_user_list_fields():
    result = user_grid_fields.MEMBERSHIP
    result = result + user_grid_fields.USER
    return success('SUCCESS', result)


def get_user_list(data):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    members = {}
    membership_model = db.session.query(Membership).filter(Membership.membership_type == 'general')
    if data.get('membership_status', None):
        membership_model.filter(Membership.membership_status == data.get('membership_status'))
    if data.get('role', None):
        membership_model.filter(Membership.role == data.get('role'))
    membership_pagination = membership_model.paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    total_record = membership_pagination.total
    total_pages = total_record // per_page + 1
    membership = membership_pagination.items
    result = []
    if membership:
        for member in membership:
            members[str(member.user_id)] = {}
            for required_field in user_grid_fields.MEMBERSHIP:
                my_code = "members[str(member.user_id)][required_field['key']] = member." + required_field['key']
                exec(my_code)

    if members:
        users = db.session.query(Users).filter(Users.id.in_(members.keys())).all()
        users_count = db.session.query(Membership).count()
        for user in users:
            user_data = {}
            final_user_data = {}
            for required_field in user_grid_fields.USER:
                my_code = "user_data['" + required_field["key"] + "'] = user." + required_field["key"]
                exec(my_code)
                user_data.update(members[str(user.id)])
            post_count = Post.query.filter_by(user_id=user_data['id'],deleted_at=None,status='active').count()
            final_user_data['column 1'] = user_data['id']
            final_user_data['column 2'] = user_data['profile_image']
            final_user_data['column 3'] = user_data['membership_status']
            final_user_data['column 4'] = user_data['membership_type']
            final_user_data['column 5'] = user_data['first_name']
            # final_user_data['column 6'] = user_data['last_name']
            final_user_data['column 7'] = user_data['gender']
            final_user_data['column 8'] = user_data['email']
            final_user_data['column 9'] = user_data['phone']
            final_user_data['column10'] = user_data['created_at']
            final_user_data['column11'] = post_count
            result.append(final_user_data)
        return success("SUCCESS", {"Count": users_count, "content": result, 'message': 'Retrieved successfully',
                                   'page_info': {'current_page': page, 'total_data': total_record,
                                                 'total_pages': total_pages,
                                                 'limit': per_page},
                                   'structure': cms_user_grid_fields.STRUCTURE[0],
                                   })


def disable_user(current_user, user_id):
    existing_user = Membership.query.filter_by(user_id=user_id, membership_type='general',
                                               membership_status='active').first()
    user_data = Users.query.filter_by(id=user_id, user_deleted_at=None, deleted_at=None).first()
    if existing_user and user_data:
        def send_notification():
            user_membership = Membership.query.filter_by(user_id=user_id,
                                                         membership_status='active',
                                                         membership_type='general',
                                                         deleted_at=None).first()
            if user_membership.fcm_token != None:
                queue_url = PUSH_NOTIFICATION_URL
                fcm_token = []
                fcm_token.append(user_membership.fcm_token)
                payload = {}
                payload['id'] = str(existing_user.id)
                payload['current_user'] = str(current_user.id)
                payload['message'] = 'Blocked your Adrenaln account'
                payload['title'] = 'Blocked Account'
                payload['fcm_token'] = fcm_token
                payload['screen_type'] = ''
                payload['responder_id'] = None
                send_queue_message(queue_url, payload)


        send_notification()
        existing_user.membership_status = 'inactive'
        update_item(existing_user)
        user_data.deleted_at = datetime.datetime.now()
        update_item(user_data)

        return success("SUCCESS", meta={'message': 'User Disabled'})
    else:
        return success('SUCCESS', meta={'message': 'invalid user'})




def create_admin_post(data, current_user):
    meta_data = data.get('meta_data', None)
    input_location = data.get('location', None)
    key = data.get('key', None)
    file_name = request.files.get('users_list', None)
    category_type = data.get('category_type', None)
    is_priority = data.get('is_priority', False)
    expire_on = data.get('expire_on', None)
    city_name = data.get('city_name', None)
    if category_type in ['broadcast', 'international_broadcast', 'india_broadcast', 'business_broadcast',
                         'email_broadcast', 'city_broadcast']:
        key = None
    location = {"city": None, "state": None}
    if input_location:
        location["city"] = input_location.get('city', None)
        location["state"] = input_location.get('state', None)
    post = Post(title=data.get('title', None), description=data.get('description', None),
                visibility='admin', type='regular',
                user_id=current_user.id, location=location, group_id=None)
    post = add_item(post)

    # add share_link
    share_link = share_dynamic_link(post.id)
    post.share_link = share_link
    update_item(post)
    if key and category_type not in ['broadcast', 'international_broadcast', 'india_broadcast', 'business_broadcast',
                                     'email_broadcast','city_broadcast']:
        max_data = db.session.query(func.max(AdminPost.s_id)).scalar()
        if max_data:
            s_id = int(max_data) + 1
        else:
            s_id = 1
        admin_post = AdminPost(is_priority=is_priority, reviewer_status=True, publisher_status=True, post_id=post.id,
                               publisher_id=current_user.id, s_id=s_id)
        add_item(admin_post)
        for data in key:
            post_bucket = PostBucketMapping(post_id=post.id, key=data, type=category_type)
            add_item(post_bucket)
        # user_bucket = UserBucket(user_id=current_user,bucket_key=bucket_key,is_primary=is_primary)
        # add_item(user_bucket)
    elif category_type == 'broadcast':
        admin_post = AdminPost(is_priority=is_priority, reviewer_status=True, publisher_status=True, post_id=post.id,
                               publisher_id=current_user.id)
        add_item(admin_post)
        post_bucket = PostBucketMapping(post_id=post.id, category_value='all', type=category_type)
        add_item(post_bucket)
        # add broadcast post to all users timeline
        from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
        sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                           aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
        response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL,
                                    MessageBody=json.dumps({'post_id': str(post.id), 'type': category_type}))
    elif category_type == 'international_broadcast':
        admin_post = AdminPost(is_priority=is_priority, reviewer_status=True, publisher_status=True, post_id=post.id,
                               publisher_id=current_user.id)
        add_item(admin_post)
        post_bucket = PostBucketMapping(post_id=post.id, category_value='international', type=category_type)
        add_item(post_bucket)
        # add broadcast post to all users timeline
        from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
        sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                           aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
        response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL,
                                    MessageBody=json.dumps({'post_id': str(post.id), 'type': category_type}))
    elif category_type == 'india_broadcast':
        admin_post = AdminPost(is_priority=is_priority, reviewer_status=True, publisher_status=True, post_id=post.id,
                               publisher_id=current_user.id)
        add_item(admin_post)
        post_bucket = PostBucketMapping(post_id=post.id, category_value='india', type=category_type)
        add_item(post_bucket)
        # add broadcast post to all users timeline
        from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
        sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                           aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
        response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL,
                                    MessageBody=json.dumps({'post_id': str(post.id), 'type': category_type}))
    elif category_type == 'business_broadcast':
        admin_post = AdminPost(is_priority=is_priority, reviewer_status=True, publisher_status=True, post_id=post.id,
                               publisher_id=current_user.id)
        add_item(admin_post)
        post_bucket = PostBucketMapping(post_id=post.id, category_value='business_user', type=category_type)
        add_item(post_bucket)
        # add broadcast post to all users timeline
        from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
        sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                           aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
        response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL,
                                    MessageBody=json.dumps({'post_id': str(post.id), 'type': category_type}))
    elif category_type == 'email_broadcast':
        if file_name:

            admin_post = AdminPost(is_priority=is_priority, reviewer_status=True, publisher_status=True, post_id=post.id,
                                   publisher_id=current_user.id)
            add_item(admin_post)

            result = read_csv_file(current_user.id, file_name)
            if result:
                for item in result:
                    post_bucket = PostBucketMapping(post_id=post.id, category_value=item, type=category_type)
                    add_item(post_bucket)
            else:
                return success('SUCCESS', meta={'message': 'Invalid Data'})
            # add broadcast post to all users timeline
            from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
            sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                               aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
            response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL,
                                        MessageBody=json.dumps({'post_id': str(post.id), 'type': category_type}))
        else:
            return success('SUCCESS', meta={'message': 'Filename not found'})
    elif category_type == 'city_broadcast':
        if city_name:
            admin_post = AdminPost(is_priority=is_priority, reviewer_status=True, publisher_status=True, post_id=post.id,
                                   publisher_id=current_user.id)
            add_item(admin_post)
            for city in city_name:
                post_bucket = PostBucketMapping(post_id=post.id, category_value=city, type=category_type)
                add_item(post_bucket)
                # add broadcast post to all users timeline
                from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
                sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                                   aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
                response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL,
                                            MessageBody=json.dumps({'post_id': str(post.id), 'type': category_type}))
        else:
            return success('SUCCESS', meta={'message': 'City name not found'})
    else:
        return success('SUCCESS', meta={"message": "Please select category"})
    # admin_post_view = AdminPostViews(admin_post_id=post.id, user_id=current_user)
    # add_item(admin_post_view)
    if expire_on:
        # post.expire_on = data.get('expire_on', None)
        # update_item(post)
        admin_post.expiry_date = expire_on
        update_item(admin_post)

    if post and meta_data:
        post.meta_data = meta_data
        add_item(post)
    admin_post.publisher_approved_at = datetime.datetime.now()
    update_item(admin_post)
    return success("Post added successfully", {})



def read_csv_file(current_user, file_name):
    exist_user = Membership.query.filter_by(user_id=current_user, membership_status='active',
                                            deleted_at=None).first()
    if exist_user:
        data = []

        # get the current path
        current_path = pathlib.Path(__file__).parent.resolve()

        # change path to csv folder
        folder_path = str(pathlib.Path(current_path).parents[1]) + '/csv/'

        # save file in th folder
        filename = secure_filename(file_name.filename)
        file_name.save(os.path.join(folder_path, filename))
        path = folder_path + file_name.filename

        with open(path) as file:
            csv_file = csv.DictReader(file)
            for row in csv_file:
                data.append(row['email'])
            file.close()
            os.remove(path)
            return data
    else:
        return success('SUCCESS', meta={'message': 'Invalid User'})


def create_admin_post_v2(data, current_user):
    meta_data = data.get('meta_data', None)
    input_location = data.get('location', None)
    key = data.get('key', None)
    file_name = request.files.get('users_list', None)
    category_type = data.get('category_type', None)
    is_priority = data.get('is_priority', False)
    expire_on = data.get('expire_on', None)
    city_name = data.get('city_name', None)
    if category_type in ['broadcast', 'international_broadcast', 'india_broadcast', 'business_broadcast',
                         'email_broadcast', 'city_broadcast']:
        key = None
    location = {"city": None, "state": None}
    if input_location:
        location["city"] = input_location.get('city', None)
        location["state"] = input_location.get('state', None)
    post = Post(title=data.get('title', None), description=data.get('description', None),
                visibility='admin', type='regular',
                user_id=current_user.id, location=location, group_id=None)
    post = add_item(post)

    # add share_link
    share_link = share_dynamic_link(post.id)
    post.share_link = share_link
    update_item(post)
    # is_primary = data.get('is_priority',False)
    if key and category_type not in ['broadcast', 'international_broadcast', 'india_broadcast', 'business_broadcast',
                                     'email_broadcast','city_broadcast']:
        max_data = db.session.query(func.max(AdminPost.s_id)).scalar()
        if max_data:
            s_id = float(max_data) + 1
        else:
            s_id = 1
        admin_post = AdminPost(is_priority=is_priority, reviewer_status=True, publisher_status=True, post_id=post.id,
                               publisher_id=current_user.id, s_id=s_id)
        add_item(admin_post)
        for data in key:
            post_bucket = PostBucketMapping(post_id=post.id, key=data, type=category_type)
            add_item(post_bucket)
        # user_bucket = UserBucket(user_id=current_user,bucket_key=bucket_key,is_primary=is_primary)
        # add_item(user_bucket)
    elif category_type == 'broadcast':
        admin_post = AdminPost(is_priority=is_priority, reviewer_status=True, publisher_status=True, post_id=post.id,
                               publisher_id=current_user.id)
        add_item(admin_post)
        post_bucket = PostBucketMapping(post_id=post.id, category_value='all', type=category_type)
        add_item(post_bucket)
        # add broadcast post to all users timeline
        from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
        sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                           aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
        response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL,
                                    MessageBody=json.dumps({'post_id': str(post.id), 'type': category_type}))
    elif category_type == 'international_broadcast':
        admin_post = AdminPost(is_priority=is_priority, reviewer_status=True, publisher_status=True, post_id=post.id,
                               publisher_id=current_user.id)
        add_item(admin_post)
        post_bucket = PostBucketMapping(post_id=post.id, category_value='international', type=category_type)
        add_item(post_bucket)
        # add broadcast post to all users timeline
        from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
        sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                           aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
        response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL,
                                    MessageBody=json.dumps({'post_id': str(post.id), 'type': category_type}))
    elif category_type == 'india_broadcast':
        admin_post = AdminPost(is_priority=is_priority, reviewer_status=True, publisher_status=True, post_id=post.id,
                               publisher_id=current_user.id)
        add_item(admin_post)
        post_bucket = PostBucketMapping(post_id=post.id, category_value='india', type=category_type)
        add_item(post_bucket)
        # add broadcast post to all users timeline
        from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
        sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                           aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
        response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL,
                                    MessageBody=json.dumps({'post_id': str(post.id), 'type': category_type}))
    elif category_type == 'business_broadcast':
        admin_post = AdminPost(is_priority=is_priority, reviewer_status=True, publisher_status=True, post_id=post.id,
                               publisher_id=current_user.id)
        add_item(admin_post)
        post_bucket = PostBucketMapping(post_id=post.id, category_value='business_user', type=category_type)
        add_item(post_bucket)
        # add broadcast post to all users timeline
        from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
        sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                           aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
        response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL,
                                    MessageBody=json.dumps({'post_id': str(post.id), 'type': category_type}))
    elif category_type == 'email_broadcast':
        if file_name:

            admin_post = AdminPost(is_priority=is_priority, reviewer_status=True, publisher_status=True, post_id=post.id,
                                   publisher_id=current_user.id)
            add_item(admin_post)

            result = read_csv_file(current_user.id, file_name)
            if result:
                for item in result:
                    post_bucket = PostBucketMapping(post_id=post.id, category_value=item, type=category_type)
                    add_item(post_bucket)
            else:
                return success('SUCCESS', meta={'message': 'Invalid Data'})
            # add broadcast post to all users timeline
            from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
            sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                               aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
            response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL,
                                        MessageBody=json.dumps({'post_id': str(post.id), 'type': category_type}))
        else:
            return success('SUCCESS', meta={'message': 'Filename not found'})
    elif category_type == 'city_broadcast':
        if city_name:
            for city in city_name:
                admin_post = AdminPost(is_priority=is_priority, reviewer_status=True, publisher_status=True, post_id=post.id,
                                       publisher_id=current_user.id)
                add_item(admin_post)
                post_bucket = PostBucketMapping(post_id=post.id, category_value=city, type=category_type)
                add_item(post_bucket)
                # add broadcast post to all users timeline
                from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
                sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                                   aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
                response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL,
                                            MessageBody=json.dumps({'post_id': str(post.id), 'type': category_type}))
        else:
            return success('SUCCESS', meta={'message': 'City name not found'})
    else:
        return success('SUCCESS', meta={"message": "Please select category"})
    # admin_post_view = AdminPostViews(admin_post_id=post.id, user_id=current_user)
    # add_item(admin_post_view)
    if expire_on:
        # post.expire_on = data.get('expire_on', None)
        # update_item(post)
        admin_post.expiry_date = expire_on
        update_item(admin_post)

    if post and meta_data:
        post.meta_data = meta_data
        add_item(post)
    admin_post.publisher_approved_at = datetime.datetime.now()
    update_item(admin_post)
    return success("Post added successfully", {})


def active_users_list():
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    active_users_count = Membership.query.filter_by(membership_status='active').count()
    all_active_users = Membership.query.filter_by(membership_status='active').all()
    active_users = Membership.query.filter_by(membership_status='active').paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    total_records = len(all_active_users)
    active_users = active_users.items
    total_pages = total_records // per_page + 1
    result = []
    for users in active_users:
        existing_user = Users.query.filter_by(id=users.user_id,deleted_at=None,user_deleted_at=None).first()
        active_users = {}
        user_data = {}
        user_data['id'] = users.user_id
        user_data['status'] = users.membership_status
        user_data['name'] = existing_user.first_name
        user_data['city'] = existing_user.city
        user_data['profile_image'] = existing_user.profile_image
        result.append(user_data)
    active_users['active_users'] = active_users_count
    result.append(active_users)
    return success('SUCCESS', result, meta={'message': 'Active Users',
                                            'page_info': {'current_page': page, 'limit': per_page,
                                                          'total_record': total_records, 'total_pages': total_pages}})


def inactive_users_list():
    inactive = ['inactive', 'pending']
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    inactive_users_count = db.session.query(Membership).filter(Membership.membership_status.in_(inactive)).count()
    all_inactive_users = db.session.query(Membership).filter(Membership.membership_status.in_(inactive)).all()
    active_users = db.session.query(Membership).filter(Membership.membership_status.in_(inactive)).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    total_records = len(all_inactive_users)
    active_users = active_users.items
    total_pages = total_records // per_page + 1
    result = []
    for users in active_users:
        existing_user = Users.query.filter_by(id=users.user_id,deleted_at=None,user_deleted_at=None).first()
        active_users = {}
        user_data = {}
        user_data['id'] = users.user_id
        user_data['status'] = users.membership_status
        user_data['name'] = existing_user.first_name
        user_data['city'] = existing_user.city
        user_data['profile_image'] = existing_user.profile_image
        result.append(user_data)
    active_users['inactive_users'] = inactive_users_count
    result.append(active_users)

    return success('SUCCESS', result, meta={'message': 'Inactive Users',
                                            'page_info': {'current_page': page, 'limit': per_page,
                                                          'total_record': total_records, 'total_pages': total_pages}})


def user_details(user_id):
    users = Users.query.filter_by(id=user_id,deleted_at=None,user_deleted_at=None).first()
    status = Membership.query.filter_by(user_id=user_id, deleted_at=None, membership_status='active').first()
    result = []
    if users and status:
        details = {}
        details['phone'] = users.phone
        details['status'] = status.membership_status
        details['user_info'] = get_user_profile_details(users.id)
        post_count = Post.query.filter_by(user_id=users.id,deleted_at=None,status='active').count()
        if post_count == 0:
            details['post_count'] = post_count
        else:
            details['post_count'] = post_count
        result.append(details)
        return success("SUCCESS",result, meta={"message":"User Details"})
    else:
        return success('SUCCESS',meta={"message":"No membership status"})



def post_user_list(data):
    if data:
        page, per_page = data.get('page'), data.get('limit')
    else:
        page = 1
        per_page = 10

    membership_model = db.session.query(Membership).filter(Membership.membership_type == 'general')
    if data.get('membership_status', None):
        membership_model.filter(Membership.membership_status == data.get('membership_status'))
    if data.get('role', None):
        membership_model.filter(Membership.role == data.get('role'))
    membership_pagination = membership_model.paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    total_record = membership_pagination.total
    total_pages = total_record // per_page + 1

    result = []
    users = db.session.query(Users).join(Post).filter(Post.user_id == Users.id).all()
    users_count = 0
    if users:
        for user in users:
            status = Membership.query.filter_by(user_id=user.id).first()
            if status:
                post_count = Post.query.filter_by(user_id=user.id,deleted_at=None,status='active').count()
                details = {}
                details['column 1'] = user.id
                details['column 2'] = user.profile_image
                details['column 3'] = status.membership_status
                details['column 4'] = status.membership_type
                details['column 5'] = user.first_name
                # details['column 6'] = user.last_name
                details['column 7'] = user.gender
                details['column 8'] = user.email
                details['column 9'] = user.phone
                details['column10'] = user.created_at
                details['column11'] = post_count
                result.append(details)
                users_count = users_count + 1
        return success("SUCCESS", {"Count": users_count, "content": result, 'message': 'Retrieved successfully',
                                   'page_info': {'current_page': page, 'total_data': total_record,
                                                 'total_pages': total_pages,
                                                 'limit': per_page},
                                   "structure": cms_user_grid_fields.STRUCTURE[0]
                                   })
    else:
        return failure("No users", {})


def search_users_list():
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    keyword = request.args.get('keyword')
    membership_status = request.args.get('membership_status')
    if membership_status not in ['general', 'admin']:
        return success('SUCCESS',meta={'message':'Invalid membership status'})
    result = []
    if keyword and membership_status:
        search_string = '%{}%'.format(keyword)
        search_users_list = Users.query.join(Membership).filter(or_(
            Users.nickname.ilike(search_string), Users.email.ilike(search_string),
            Users.first_name.ilike(search_string)), Membership.user_id == Users.id,Membership.membership_type==membership_status, Users.user_deleted_at == None,
                                                    Users.deleted_at == None). \
            with_entities(Users.id, Users.nickname,
                          Users.first_name, Users.profile_image,
                          Users.email, Users.created_at,
                          Users.last_name, Users.gender,
                          Users.email, Users.phone,
                          Membership.membership_status,
                          Membership.membership_type).distinct(Users.id).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        users = search_users_list.items
        users_count = db.session.query(Users).count()
        for user in users:
            post_count = Post.query.filter_by(user_id=user.id, status='active', deleted_at=None).count()
            details = {}
            details['column 1'] = user.id
            details['column 2'] = user.profile_image
            details['column 3'] = user.membership_status
            details['column 4'] = user.membership_type
            details['column 5'] = user.first_name
            details['column 6'] = user.last_name
            details['column 7'] = user.gender
            details['column 8'] = user.email
            details['column 9'] = user.phone
            details['column10'] = user.created_at
            details['column11'] = post_count
            result.append(details)
        return success("SUCCESS", {"Count": users_count, "content": result, 'message': 'Retrieved successfully',
                                   'page_info': {'current_page': page,
                                                 'limit': per_page},
                                   "structure": cms_user_grid_fields.STRUCTURE[0]
                                   })
    else:
        return success("SUCCESS", meta={"message": "keyword is invalid"})


def user_enable(current_user,user_id):
    disabled_user = Membership.query.filter_by(user_id=user_id, membership_type='general',
                                               membership_status='inactive').first()
    user_data = db.session.query(Users).filter(Users.id==user_id,Users.deleted_at != None).first()
    if disabled_user and user_data:
        def send_notification():
            user_membership = Membership.query.filter_by(user_id=user_id,
                                                         membership_status='inactive',
                                                         membership_type='general',
                                                         deleted_at=None).first()
            if user_membership.fcm_token != None:
                queue_url = PUSH_NOTIFICATION_URL
                fcm_token = []
                fcm_token.append(user_membership.fcm_token)
                payload = {}
                payload['id'] = str(user_id)
                payload['current_user'] = str(current_user.id)
                payload['message'] = 'Unblocked your Adrenaln account'
                payload['title'] = 'Unblocked Account'
                payload['fcm_token'] = fcm_token
                payload['screen_type'] = ''
                payload['responder_id'] = None
                send_queue_message(queue_url, payload)
        send_notification()
        disabled_user.membership_status = 'active'
        update_item(disabled_user)
        user_data.deleted_at = None
        update_item(user_data)

        return success("SUCCESS", None, {'message': 'User Enabled'})
    else:
        return success("SUCCESS", None, {'message': 'User is not inactive'})



def user_post_details(current_user,post_id):
    user_post = Post.query.filter_by(id=post_id,status='active',deleted_at=None).all()
    result = []
    for post in user_post:
        details = {}
        details['post_id'] = post.id
        details['type'] = post.type
        details['title'] = post.title
        details['description'] = post.description
        details['visibility'] = post.visibility
        details['meta_data'] = post.meta_data
        details['location'] = post.location
        result.append(details)
    return success('SUCCESS', result, meta={"message": "User post details"})


def admin_post_list(data, current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    statement = exists().where(AdminPost.post_id == Post.id)
    all_user_post = db.session.query(Post).filter(~statement, Post.visibility == 'all',Post.type =='regular',Post.promotion != True, Post.deleted_at == None,Post.status=='active',
                                                  Post.group_id == None).all()
    user_post = db.session.query(Post).filter(~statement, Post.visibility == 'all',Post.type =='regular',Post.promotion != True, Post.deleted_at == None,Post.status=='active',
                                              Post.group_id == None).order_by(
        Post.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)

    user_posts = user_post.items
    total_record = len(all_user_post)
    total_pages = total_record // per_page + 1
    result = []
    if user_posts:
        for post in user_posts:
            user_data = Users.query.filter_by(id=post.user_id, deleted_at=None,user_deleted_at=None).first()
            if user_data:
                user_info = get_user_profile_details(post.user_id)
                details = {}
                details['id'] = post.id
                details['location'] = post.location
                details['title'] = post.title
                details['description'] = post.description
                details['created_at'] = post.created_at
                details['visibility'] = post.visibility
                details['type'] = post.type
                details['meta_data'] = post.meta_data
                details['expire_on'] = post.expire_on
                details['user_info'] = user_info
                result.append(details)
        return success('SUCCESS', result, meta={'message': 'Reviewer Feed',
                                   'page_info': {'current_page': page,
                                                 'limit': per_page,
                                                 'total_records': total_record,
                                                 'total_pages': total_pages}})
    else:
        return success('SUCCESS', meta={"message": "No Posts Found"})



def approve_posts(current_user, data):
    post_id = data.get('post_id')
    is_priority = data.get('is_priority',False)
    is_approved = data.get('is_approved',False)
    key = data.get('key',None)
    expiry_date = data.get('expiry_date',None)
    category_type = data.get('category_type',None)
    no_priority_expiry=data.get('no_priority_expiry',None)

    user_role = Membership.query.filter_by(user_id=current_user.id,membership_status='active', deleted_at=None).filter(
        or_(Membership.role == 'post_reviewer', Membership.role == 'post_publisher',Membership.role == 'super_admin')).first()
    if post_id:
        if user_role.role == 'post_reviewer':
            if category_type == 'broadcast':
                return success("SUCCESS", meta={'message': 'Invalid Category Type'})
            for post_item in post_id:
                post_details = Post.query.filter_by(id=post_item, type='regular', visibility='all', deleted_at=None,status='active').first()
                if post_details:
                    admin_post_exist = AdminPost.query.filter_by(post_id=post_item,
                                                           deleted_at=None).first()
                    is_bucket_mapping = PostBucketMapping.query.filter_by(post_id=post_item,
                                                           deleted_at=None).all()
                    if not admin_post_exist and not is_bucket_mapping:
                        if is_approved == True and (not key or not category_type):
                            return success('SUCCESS',meta={'message':'Invalid data'})
                        # add post by reviewer logic
                        admin_post = AdminPost(post_id=post_item,
                                               reviewer_approved_at=datetime.datetime.now(),
                                               reviewer_id=current_user.id)
                        add_item(admin_post)
                        if post_details.promotion == True:
                            admin_post.promotion = 'promotion_post'
                            update_item(admin_post)

                        if is_priority:
                            if is_priority in [True,False]:
                                admin_post.is_priority = is_priority
                                update_item(admin_post)
                        else:
                            admin_post.is_priority = False
                            update_item(admin_post)

                        if expiry_date:
                            admin_post.expiry_date=expiry_date
                            admin_post.is_priority=False
                            update_item(admin_post)

                        if is_approved and is_approved == True:
                            admin_post.reviewer_status = True
                            update_item(admin_post)
                        else:
                            admin_post.reviewer_status = False
                            update_item(admin_post)
                            # return success('SUCCESS',meta={'message':'Details Updated Successfully'})

                        if category_type == 'state':
                            if key:
                                for value in key:
                                    pbm = PostBucketMapping(type=category_type, post_id=post_item,category_value=value)
                                    add_item(pbm)
                            else:
                                return success('SUCCESS',meta={'message':'Invalid Data'})
                        if category_type == 'email':
                            if key:
                                for value in key:
                                    pbm = PostBucketMapping(type=category_type, post_id=post_item,category_value=value)
                                    add_item(pbm)
                            else:
                                return success('SUCCESS',meta={'message':'Invalid Data'})
                        if category_type == 'bucket':
                            if key:
                                for value in key:
                                    pbm = PostBucketMapping(type=category_type, post_id=post_item,key=value)
                                    add_item(pbm)
                            else:
                                return success('SUCCESS',meta={'message':'Invalid Data'})
                    else:
                        if post_details.promotion == True:
                            admin_post_exist.promotion = 'promotion_post'
                            update_item(admin_post_exist)
                        # update post by reviewr logic
                        if is_approved == False:
                            admin_post_exist.reviewer_status=False
                            admin_post_exist.expiry_date = None
                            admin_post_exist.is_priority = False
                            update_item(admin_post_exist)
                            if is_bucket_mapping:
                                for data in is_bucket_mapping:
                                    delete_item(data)
                        else:
                            if category_type and category_type == 'broadcast':
                                return success("SUCCESS",meta={'message':'Invalid Category Type'})
                            if is_priority and is_priority == True:
                                admin_post_exist.is_priority = is_priority
                                admin_post_exist.expiry_date = None
                                update_item(admin_post_exist)
                            if expiry_date:
                                admin_post_exist.expiry_date = expiry_date
                                admin_post_exist.is_priority = False
                                update_item(admin_post_exist)

                            if no_priority_expiry and  no_priority_expiry == 'no_priority_expiry':
                                admin_post_exist.expiry_date = None
                                admin_post_exist.is_priority = False
                                update_item(admin_post_exist)

                            if category_type and category_type == 'state':
                                admin_post_exist.expiry_date = None
                                admin_post_exist.is_priority = False
                                update_item(admin_post_exist)
                                post_bucket_map = PostBucketMapping.query.filter_by(post_id=post_item).all()
                                if key:
                                    if post_bucket_map:
                                        for data in post_bucket_map:
                                            delete_item(data)
                                    for value in key:
                                        bucket_table= PostBucketMapping(post_id=post_item,type='state',category_value=value)
                                        add_item(bucket_table)
                            if category_type and category_type == 'email':
                                admin_post_exist.expiry_date = None
                                admin_post_exist.is_priority = False
                                update_item(admin_post_exist)
                                post_bucket_map = PostBucketMapping.query.filter_by(post_id=post_item).all()
                                if key:
                                    if post_bucket_map:
                                        for data in post_bucket_map:
                                            delete_item(data)
                                    for value in key:
                                        bucket_table= PostBucketMapping(post_id=post_item,type='email',category_value=value)
                                        add_item(bucket_table)
                            if category_type and category_type == 'bucket':
                                post_bucket_map = PostBucketMapping.query.filter_by(post_id=post_item).all()
                                if key:
                                    if post_bucket_map:
                                        for data in post_bucket_map:
                                            delete_item(data)
                                    for value in key:
                                        bucket_table= PostBucketMapping(post_id=post_item,type='bucket',key=value)
                                        add_item(bucket_table)

            return success('SUCCESS',meta={'message':'Details Updated Successfully'})

        elif user_role.role in ['post_publisher','super_admin']:
            # publisher logic
            for post_item in post_id:
                post_details = Post.query.filter_by(id=post_item, type='regular', visibility='all', deleted_at=None,status='active').first()
                if post_details:
                    admin_post_exist = AdminPost.query.filter_by(post_id=post_item,
                                                           deleted_at=None).first()
                    is_bucket_mapping = PostBucketMapping.query.filter_by(post_id=post_item,
                                                           deleted_at=None).all()

                    if is_approved == False:
                        admin_post_exist.publisher_status = False
                        admin_post_exist.publisher_id = current_user.id
                        update_item(admin_post_exist)
                        if is_bucket_mapping:
                            for data in is_bucket_mapping:
                                delete_item(data)
                    else:
                        if category_type and category_type == 'broadcast':
                            return success("SUCCESS",meta={'message':'Invalid Category Type'})
                        if not admin_post_exist.s_id:
                            max_data = db.session.query(func.max(AdminPost.s_id)).scalar()
                            if max_data:
                                admin_post_exist.s_id = int(max_data) + 1
                            else:
                                admin_post_exist.s_id = 1
                        admin_post_exist.publisher_approved_at = datetime.datetime.now()
                        admin_post_exist.publisher_status = True
                        admin_post_exist.publisher_id = current_user.id
                        update_item(admin_post_exist)

                        if is_priority and is_priority == True:
                            admin_post_exist.is_priority = is_priority
                            admin_post_exist.expiry_date = None
                            update_item(admin_post_exist)
                        if expiry_date:
                            admin_post_exist.expiry_date = expiry_date
                            admin_post_exist.is_priority = False
                            update_item(admin_post_exist)

                        if no_priority_expiry and no_priority_expiry == 'no_priority_expiry':
                            admin_post_exist.expiry_date = None
                            admin_post_exist.is_priority = False
                            update_item(admin_post_exist)

                        if category_type and category_type == 'state':
                            admin_post_exist.expiry_date = None
                            admin_post_exist.is_priority = False
                            update_item(admin_post_exist)
                            post_bucket_map = PostBucketMapping.query.filter_by(post_id=post_item).all()
                            if key:
                                if post_bucket_map:
                                    for data in post_bucket_map:
                                        delete_item(data)
                                for value in key:
                                    bucket_table = PostBucketMapping(post_id=post_item, type='state',
                                                                     category_value=value)
                                    add_item(bucket_table)
                        if category_type and category_type == 'email':
                            admin_post_exist.expiry_date = None
                            admin_post_exist.is_priority = False
                            update_item(admin_post_exist)
                            post_bucket_map = PostBucketMapping.query.filter_by(post_id=post_item).all()
                            if key:
                                if post_bucket_map:
                                    for data in post_bucket_map:
                                        delete_item(data)
                                for value in key:
                                    bucket_table = PostBucketMapping(post_id=post_item, type='email',
                                                                     category_value=value)
                                    add_item(bucket_table)
                        if category_type and category_type == 'bucket':
                            post_bucket_map = PostBucketMapping.query.filter_by(post_id=post_item).all()
                            if key:
                                if post_bucket_map:
                                    for data in post_bucket_map:
                                        delete_item(data)
                                for value in key:
                                    bucket_table = PostBucketMapping(post_id=post_item, type='bucket', key=value)
                                    add_item(bucket_table)

            return success('SUCCESS', meta={'message': 'Details Updated Successfully'})
    else:
        return success('SUCCESS',meta={'message':'Permission Denied'})



def approved_post_list(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    approved_posts_count = AdminPost.query.filter_by(promotion=None, reviewer_status=True, deleted_at=None,
                                                     publisher_status=None).all()
    approved_post = AdminPost.query.filter_by(promotion=None, reviewer_status=True, deleted_at=None,
                                              publisher_status=None).order_by(
        AdminPost.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    result = []
    approved_posts = approved_post.items
    if approved_posts:
        for post in approved_posts:
            details = Post.query.filter_by(id=post.post_id, deleted_at=None, status='active').all()
            for detail in details:
                user_data = Users.query.filter_by(id=detail.user_id, deleted_at=None,user_deleted_at=None).first()
                post_list = AdminPost.query.filter_by(post_id=detail.id, deleted_at=None).first()
                bucket_data = PostBucketMapping.query.filter_by(post_id=detail.id, deleted_at=None).all()
                if user_data and post_list and bucket_data:
                    user_info = get_user_profile_details(user_data.id)
                    details = {}
                    details['id'] = detail.id
                    details['location'] = detail.location
                    details['title'] = detail.title
                    details['description'] = detail.description
                    details['created_at'] = detail.created_at
                    details['visibility'] = detail.visibility
                    details['type'] = detail.type
                    details['meta_data'] = detail.meta_data
                    details['expire_on'] = detail.expire_on
                    details['user_info'] = user_info
                    details['expiry_date'] = post_list.expiry_date
                    details['is_priority'] = post_list.is_priority
                    buckets = []
                    for bucket in bucket_data:
                        buckets.append(bucket.key)
                    details['bucket_name'] = buckets
                    result.append(details)
        total_record = len(approved_posts_count)
        total_pages = total_record // per_page + 1
        return success('SUCCESS', result, meta={'message': 'approved posts',
                                                'page_info': {'current_page': page,
                                                              'limit': per_page,
                                                              'total_records': total_record,
                                                              'total_pages': total_pages}
                                                })
    else:
        return success('SUCCESS', meta={'message': 'No posts'})



def approved_promotion_posts(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    approved_posts_count = AdminPost.query.filter_by(promotion='promotion_post', reviewer_status=True, deleted_at=None,
                                                     publisher_status=None).all()
    approved_post = AdminPost.query.filter_by(promotion='promotion_post', reviewer_status=True, deleted_at=None,
                                              publisher_status=None).order_by(
        AdminPost.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    result = []
    approved_posts = approved_post.items
    if approved_posts:
        for post in approved_posts:
            details = Post.query.filter_by(id=post.post_id, deleted_at=None, status='active').all()
            for detail in details:
                user_data = Users.query.filter_by(id=detail.user_id, user_deleted_at=None, deleted_at=None).first()
                post_list = AdminPost.query.filter_by(post_id=detail.id, deleted_at=None).first()
                bucket_data = PostBucketMapping.query.filter_by(post_id=detail.id, deleted_at=None).all()
                if user_data and post_list and bucket_data:
                    user_info = get_user_profile_details(user_data.id)
                    details = {}
                    details['id'] = detail.id
                    details['location'] = detail.location
                    details['title'] = detail.title
                    details['description'] = detail.description
                    details['created_at'] = detail.created_at
                    details['visibility'] = detail.visibility
                    details['type'] = detail.type
                    details['meta_data'] = detail.meta_data
                    details['expire_on'] = detail.expire_on
                    details['user_info'] = user_info
                    details['expiry_date'] = post_list.expiry_date
                    details['is_priority'] = post_list.is_priority
                    buckets = []
                    for bucket in bucket_data:
                        buckets.append(bucket.key)
                    details['bucket_name'] = buckets
                    result.append(details)
        total_record = len(approved_posts_count)
        total_pages = total_record // per_page + 1
        return success('SUCCESS', result, meta={'message': 'approved posts',
                                                'page_info': {'current_page': page,
                                                              'limit': per_page,
                                                              'total_records': total_record,
                                                              'total_pages': total_pages}
                                                })
    else:
        return success('SUCCESS', meta={'message': 'No posts'})


def discarded_promotion_posts(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    approved_posts_count = AdminPost.query.filter_by(promotion='promotion_post',reviewer_status=True, deleted_at=None,
                                                     publisher_status=None).all()
    approved_post = AdminPost.query.filter_by(promotion='promotion_post',reviewer_status=False, deleted_at=None, publisher_status=None).order_by(
        AdminPost.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    result = []
    approved_posts = approved_post.items
    total_record = len(approved_posts_count)
    total_pages = total_record // per_page + 1
    if approved_posts:
        for post in approved_posts:
            details = Post.query.filter_by(id=post.post_id,deleted_at=None,status='active').all()
            for detail in details:
                user_data = Users.query.filter_by(id=detail.user_id, deleted_at=None,user_deleted_at=None).first()
                post_list = AdminPost.query.filter_by(post_id=detail.id, deleted_at=None).first()
                if user_data and post_list:
                    user_info = get_user_profile_details(user_data.id)
                    details = {}
                    details['id'] = detail.id
                    details['location'] = detail.location
                    details['title'] = detail.title
                    details['description'] = detail.description
                    details['created_at'] = detail.created_at
                    details['visibility'] = detail.visibility
                    details['type'] = detail.type
                    details['meta_data'] = detail.meta_data
                    details['expire_on'] = detail.expire_on
                    details['user_info'] = user_info
                    details['expiry_date'] = post_list.expiry_date
                    details['is_priority'] = post_list.is_priority

                    result.append(details)
        return success('SUCCESS', result, meta={'message': 'approved posts',
                                   'page_info': {'current_page': page,
                                                 'limit': per_page,
                                                 'total_records': total_record,
                                                 'total_pages': total_pages}
                                   })
    else:
        return success('SUCCESS', meta={'message': 'No posts'})


def publisher_views_discarded_posts(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    discarded_posts_count = AdminPost.query.filter_by(promotion=None,reviewer_status=False, deleted_at=None,
                                                      publisher_status=None).all()
    discarded_post = AdminPost.query.filter_by(promotion=None,reviewer_status=False, deleted_at=None, publisher_status=None).order_by(
        AdminPost.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    result = []
    discarded_posts = discarded_post.items
    total_record = len(discarded_posts_count)
    total_pages = total_record // per_page + 1
    if discarded_posts:
        for post in discarded_posts:
            post_exist = Post.query.filter_by(id=post.post_id, deleted_at=None, status='active').first()
            if post_exist:
                user_data = Users.query.filter_by(id=post_exist.user_id, deleted_at=None,user_deleted_at=None).first()
                post_list = AdminPost.query.filter_by(post_id=post_exist.id, deleted_at=None).first()
                if user_data and post_list:
                    user_info = get_user_profile_details(user_data.id)
                    details = {}
                    details['id'] = post_exist.id
                    details['location'] = post_exist.location
                    details['title'] = post_exist.title
                    details['description'] = post_exist.description
                    details['created_at'] = post_exist.created_at
                    details['visibility'] = post_exist.visibility
                    details['type'] = post_exist.type
                    details['meta_data'] = post_exist.meta_data
                    details['expire_on'] = post_exist.expire_on
                    details['expiry_date'] = post_list.expiry_date
                    details['is_priority'] = post_list.is_priority
                    details['user_info'] = user_info
                    result.append(details)
        return success('SUCCESS', result, meta={'message': 'discarded posts',
                                                        'page_info': {'current_page': page,
                                                                      'limit': per_page,
                                                                      'total_records': total_record,
                                                                      'total_pages': total_pages}
                                                        })
    else:
        return success('SUCCESS', meta={'message': 'No posts'})


def publisher_approve_post(current_user, data):
    post_id = data.get('post_id')
    is_approved = data.get('is_approved')
    bucket = data.get('bucket')
    post_details = AdminPost.query.filter_by(post_id=post_id,
                                             deleted_at=None).first()
    if post_details:
        if post_details.publisher_approved_at is None:
            post_details.publisher_status = is_approved
            post_details.publisher_approved_at = datetime.datetime.now()
            post_details.publisher_id = current_user.id
            update_item(post_details)
            exist_bucket = PostBucketMapping.query.filter_by(post_id=post_id, deleted_at=None).first()
            if exist_bucket:
                exist_bucket.key = bucket
                update_item(exist_bucket)
            return success('SUCCESS', meta={'message': 'post approved'})
        else:
            return success('FAILURE', meta={'message': 'already approved/ discarded'})
    else:
        return success('SUCCESS', meta={'message': 'invalid post'})


def search_post_by_date(current_user, data):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    type = request.args.get('type')
    if type == 'date':
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        if start_date and end_date:
            parsed_start_time = parser.parse(start_date)
            parsed_end_time = parser.parse(end_date)
            new_start_time = parsed_start_time.astimezone(datetime.timezone.utc)
            new_end_time = parsed_end_time.astimezone(datetime.timezone.utc)
            post = Post.query.filter(and_(Post.created_at >= new_start_time,
                                          Post.created_at <= new_end_time),
                                     Post.deleted_at == None,Post.status=='active', Post.visibility == 'all',
                                     Post.group_id == None, Post.save_later == None).paginate(
                page=page,
                per_page=per_page,
                error_out=False)
            post_result = Post.query.filter(and_(Post.created_at >= new_start_time,
                                                 Post.created_at <= new_end_time),
                                            Post.deleted_at == None,Post.status=='active',Post.visibility == 'all',
                                            Post.group_id == None, Post.save_later == None).all()
            result = []
            posts = post.items
            if posts:
                posts_count = len(posts)
                total_records = len(post_result)
                total_pages = total_records // per_page + 1
                for post in posts:
                    user_data = Users.query.filter_by(id=post.user_id, deleted_at=None,user_deleted_at=None).first()
                    if user_data:
                        user_info = get_user_profile_details(post.user_id)
                        details = {}
                        details['id'] = post.id
                        details['location'] = post.location
                        details['title'] = post.title
                        details['description'] = post.description
                        details['created_at'] = post.created_at
                        details['visibility'] = post.visibility
                        details['type'] = post.type
                        details['meta_data'] = post.meta_data
                        details['expire_on'] = post.expire_on
                        details['user_info'] = user_info
                        result.append(details)
                return success("SUCCESS", result, meta={'message': 'Retrieved successfully',
                                           'page_info': {'current_page': page,
                                                         'total_records': total_records,
                                                         'total_pages': total_pages,
                                                         'limit': per_page}})
            else:
                return success("SUCCESS", meta={"message": " No data found"})
        else:
            return success("SUCCESS", meta={"message": "Invalid start and end dates"})

    elif type == 'post':
        keyword = request.args.get('keyword')
        result = []
        if keyword:
            search_string = '%{}%'.format(keyword)
            search_users_post = Users.query.join(Post).filter(or_(
                Users.first_name.contains(search_string),
                Post.description.contains(search_string)),Users.user_deleted_at==None,Users.deleted_at==None, Post.visibility == 'all', Post.deleted_at == None,
                                                           Post.group_id == None, Post.save_later == None). \
                with_entities(Post.id, Post.type,
                              Post.title, Post.visibility,
                              Post.user_id, Post.meta_data,
                              Post.location, Post.description,
                              Post.expire_on, Post.created_at
                              ).paginate(
                page=page,
                per_page=per_page,
                error_out=False)
            post_result = Users.query.join(Post).filter(or_(
                Users.first_name.contains(search_string),
                Post.description.contains(search_string)),Users.user_deleted_at==None,Users.deleted_at==None, Post.visibility == 'all', Post.deleted_at == None,
                                                           Post.group_id == None, Post.save_later == None).all()
            posts = search_users_post.items
            if posts:
                posts_count = len(posts)
                total_records = len(post_result)
                total_pages = total_records // per_page + 1
                for post in posts:
                    user_info = get_user_profile_details(post.user_id)
                    details = {}
                    details['id'] = post.id
                    details['location'] = post.location
                    details['title'] = post.title
                    details['description'] = post.description
                    details['created_at'] = post.created_at
                    details['visibility'] = post.visibility
                    details['type'] = post.type
                    details['meta_data'] = post.meta_data
                    details['expire_on'] = post.expire_on
                    details['user_info'] = user_info
                    result.append(details)
                return success("SUCCESS" ,result, meta={'message': 'Retrieved successfully',
                                           'page_info': {'current_page': page,
                                                         'total-records': total_records,
                                                         'total_pages': total_pages,
                                                         'limit': per_page}
                                           })
            else:
                return success("SUCCESS", meta={"message": "No data found"})
        else:
            return success("SUCCESS", meta={"message": "keyword is invalid"})
    else:
        return success("SUCCESS", meta={"message": " Invalid type"})



def publisher_bucket_filter(key, current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    offset = per_page * (page - 1)
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        priority = request.args.get('priority', None)
        sequence_id = request.args.get('sequence_id')
        filter_key = request.args.get('filter_key')
        if priority and priority not in ['expiry', 'priority']:
            return success('SUCCESS', meta={'message': 'invalid priority'})
        if filter_key and filter_key not in ['final_post', 'approved', 'discarded',
                                             'promotion_approved', 'promotion_discarded']:
            return success('SUCCESS', meta={'message': 'invalid priority'})
        user_role = Membership.query.filter_by(user_id=current_user.id, membership_status='active',
                                               deleted_at=None).filter(
            or_(Membership.role == 'post_reviewer', Membership.role == 'post_publisher',Membership.role == 'super_admin')).first()
        if user_role:
            if user_role.role in['post_publisher','super_admin']:
                if sequence_id and sequence_id == 'true':
                    result, total_pages, total_record = sort_by_sequence(priority, key, filter_key)
                    if result:
                        return success('SUCCESS', result, meta={'message': 'Post List',
                                                                'page_info': {'current_page': page,
                                                                              'limit': per_page,
                                                                              'total_records': total_record,
                                                                              'total_pages': total_pages}})
                    else:
                        return success('SUCCESS', meta={'message': 'No data found'})
                if filter_key == 'approved':
                    exist_posts = filter_reviewer_approved(priority, key, per_page, offset)
                elif filter_key == 'discarded':
                    exist_posts = filter_reviewer_discarded(per_page, offset)
                elif filter_key == 'promotion_approved':
                    exist_posts = filter_reviewer_promotion_approved(priority, key, per_page, offset)
                elif filter_key == 'promotion_discarded':
                    exist_posts = filter_reviewer_promotion_discarded(per_page, offset)
                elif filter_key == 'final_post':
                    exist_posts = filter_publisher_final_posts(priority, key, per_page, offset)
                else:
                    return success('SUCCESS', meta={'message': 'Invalid filter key'})
            else:
                if filter_key == 'approved':
                    exist_posts = filter_reviewer_approved(priority, key, per_page, offset)
                elif filter_key == 'discarded':
                    exist_posts = filter_reviewer_discarded(per_page, offset)
                elif filter_key == 'promotion_approved':
                    exist_posts = filter_reviewer_promotion_approved(priority, key, per_page, offset)
                elif filter_key == 'promotion_discarded':
                    exist_posts = filter_reviewer_promotion_discarded(per_page, offset)
                else:
                    return success('SUCCESS', meta={'message': 'Invalid filter key'})
        else:
            return success('SUCCESS', meta={'message': 'Invalid user role'})
        result = []
        if exist_posts:

            for post in exist_posts:
                post_details = Post.query.filter_by(id=post['post_id']).first()
                if post_details:
                    user_data = Users.query.filter_by(id=post_details.user_id, deleted_at=None,user_deleted_at=None).first()
                    admin_post_data = AdminPost.query.filter_by(post_id=post['post_id'], deleted_at=None).first()
                    bucket_data = PostBucketMapping.query.filter_by(post_id=post['post_id'], deleted_at=None).all()
                    if user_data and admin_post_data:
                        user_info = get_user_profile_details(user_data.id)
                        if bucket_data:
                            post_list = {}
                            post_list['id'] = post['post_id']
                            post_list['s_id'] = post['s_id']
                            post_list['type'] = post_details.type
                            post_list['title'] = post_details.title
                            post_list['created_at'] = post_details.created_at
                            post_list['description'] = post_details.description
                            post_list['visibility'] = post_details.visibility
                            post_list['meta_data'] = post_details.meta_data
                            post_list['location'] = post_details.location
                            post_list['is_priority'] = admin_post_data.is_priority
                            post_list['expiry_date'] = admin_post_data.expiry_date
                            post_list['user_info'] = user_info
                            buckets = []
                            for bucket in bucket_data:
                                buckets.append(bucket.key)
                            post_list['bucket_name'] = buckets
                            result.append(post_list)
                        else:
                            post_list = {}
                            post_list['id'] = post['post_id']
                            # post_list['s_id'] = post['s_id']
                            post_list['type'] = post_details.type
                            post_list['title'] = post_details.title
                            post_list['created_at'] = post_details.created_at
                            post_list['description'] = post_details.description
                            post_list['visibility'] = post_details.visibility
                            post_list['meta_data'] = post_details.meta_data
                            post_list['location'] = post_details.location
                            post_list['is_priority'] = admin_post_data.is_priority
                            post_list['expiry_date'] = admin_post_data.expiry_date
                            # post_list['bucket_name'] = bucket.key
                            post_list['user_info'] = user_info
                            result.append(post_list)
            total_record = len(exist_posts)
            total_pages = total_record // per_page + 1
            return success('SUCCESS', result, meta={'message': 'Post List',
                                                    'page_info': {'current_page': page,
                                                                  'limit': per_page,
                                                                  'total_records': total_record,
                                                                  'total_pages': total_pages}})
        else:
            return success('SUCCESS', meta={'message': 'data not found'})
    else:
        return success('SUCCESS', meta={'message': 'invalid user'})


def filter_reviewer_promotion_approved(priority, key, per_page, offset):
    if priority:
        if priority == 'expiry':
            exist_posts = """select * from post_bucket_mapping inner join admin_post on 
            post_bucket_mapping.post_id=admin_post.post_id where admin_post.expiry_date is not null and ( 
            post_bucket_mapping.key='{key}' and post_bucket_mapping.deleted_at is null) and 
            admin_post.reviewer_status is true and admin_post.publisher_status is null and 
            admin_post.promotion='promotion_post' ORDER BY post_bucket_mapping.created_at DESC LIMIT {per_page} 
            OFFSET {offset}""".format(key=key,
                                      per_page=per_page,
                                      offset=offset)
            exist_posts = _query_execution(exist_posts)
        else:
            exist_posts = """select * from post_bucket_mapping inner join admin_post on 
            post_bucket_mapping.post_id=admin_post.post_id where admin_post.is_priority is true and ( 
            post_bucket_mapping.key='{key}' and post_bucket_mapping.deleted_at is null) and 
            admin_post.reviewer_status is true and admin_post.publisher_status is null and 
            admin_post.promotion='promotion_post' ORDER BY post_bucket_mapping.created_at DESC LIMIT {per_page} 
            OFFSET {offset}""".format(key=key,
                                      per_page=per_page,
                                      offset=offset)
            exist_posts = _query_execution(exist_posts)
    else:
        exist_posts = """select * from post_bucket_mapping inner join admin_post on 
        post_bucket_mapping.post_id=admin_post.post_id where (post_bucket_mapping.key='{key}' and 
        post_bucket_mapping.deleted_at is null) and admin_post.reviewer_status is true
            and admin_post.publisher_status is null and admin_post.promotion='promotion_post' ORDER BY 
        post_bucket_mapping.created_at DESC LIMIT {per_page} OFFSET {offset}""".format(key=key,
                                                                                       per_page=per_page,
                                                                                       offset=offset)
        exist_posts = _query_execution(exist_posts)
    return exist_posts


def filter_reviewer_promotion_discarded(per_page, offset):
    exist_posts = """select * from admin_post where admin_post.reviewer_status is false and 
        admin_post.publisher_status is null and admin_post.promotion is null ORDER BY admin_post.created_at 
        DESC LIMIT {per_page} OFFSET {offset}""".format(per_page=per_page,
                                                        offset=offset)
    exist_posts = _query_execution(exist_posts)
    return exist_posts


def filter_publisher_final_posts(priority, key, per_page, offset):
    if priority:
        if priority == 'expiry':
            exist_posts = """select * from post_bucket_mapping inner join admin_post on 
            post_bucket_mapping.post_id=admin_post.post_id where admin_post.expiry_date is not null and (
            post_bucket_mapping.key='{key}' and post_bucket_mapping.deleted_at is null) and 
            admin_post.publisher_status is true and (admin_post.promotion is null or admin_post.promotion ='promotion_post')
            ORDER BY post_bucket_mapping.created_at DESC LIMIT {per_page} OFFSET {offset}""".format(key=key,
                                                                                                    per_page=per_page,
                                                                                                    offset=offset)
            exist_posts = _query_execution(exist_posts)
        else:
            exist_posts = """select * from post_bucket_mapping inner join admin_post on 
            post_bucket_mapping.post_id=admin_post.post_id where admin_post.is_priority is true and ( 
            post_bucket_mapping.key='{key}' and post_bucket_mapping.deleted_at is null) and 
            admin_post.publisher_status is true and (admin_post.promotion is null or admin_post.promotion ='promotion_post') ORDER BY 
            post_bucket_mapping.created_at DESC LIMIT {per_page} OFFSET {offset}""".format(key=key,
                                                                                           per_page=per_page,
                                                                                           offset=offset)
            exist_posts = _query_execution(exist_posts)
    else:
        exist_posts = """select * from post_bucket_mapping inner join admin_post on 
        post_bucket_mapping.post_id=admin_post.post_id where (post_bucket_mapping.key='{key}' and 
        post_bucket_mapping.deleted_at is null) and 
        admin_post.publisher_status is true and (admin_post.promotion is null or admin_post.promotion ='promotion_post') ORDER BY 
        post_bucket_mapping.created_at DESC LIMIT {per_page} OFFSET {offset}""".format(key=key,
                                                                                       per_page=per_page,
                                                                                       offset=offset)
        exist_posts = _query_execution(exist_posts)
    return exist_posts


def filter_reviewer_approved(priority, key, per_page, offset):
    if priority:
        if priority == 'expiry':
            exist_posts = """select * from post_bucket_mapping inner join admin_post on 
            post_bucket_mapping.post_id=admin_post.post_id where admin_post.expiry_date is not null and 
            (post_bucket_mapping.key='{key}' and post_bucket_mapping.deleted_at is null) and 
            admin_post.reviewer_status is true and admin_post.publisher_status is null and admin_post.promotion is null
            ORDER BY post_bucket_mapping.created_at DESC LIMIT 
            {per_page} OFFSET {offset}""".format(key=key, per_page=per_page, offset=offset)
            exist_posts = _query_execution(exist_posts)
        else:
            exist_posts = """select * from post_bucket_mapping inner join admin_post on 
            post_bucket_mapping.post_id=admin_post.post_id where admin_post.is_priority is true and ( 
            post_bucket_mapping.key='{key}' and post_bucket_mapping.deleted_at is null) and
            admin_post.reviewer_status is true and admin_post.publisher_status is null and admin_post.promotion is null
            ORDER BY post_bucket_mapping.created_at DESC LIMIT 
            {per_page} OFFSET {offset}""".format(key=key, per_page=per_page, offset=offset)
            exist_posts = _query_execution(exist_posts)
    else:
        exist_posts = """select * from post_bucket_mapping inner join admin_post on 
        post_bucket_mapping.post_id=admin_post.post_id where (post_bucket_mapping.key='{key}' and 
        post_bucket_mapping.deleted_at is null) and admin_post.reviewer_status is true and 
        admin_post.publisher_status is null and admin_post.promotion is null ORDER BY post_bucket_mapping.created_at 
        DESC LIMIT {per_page} OFFSET {offset}""".format(key=key, per_page=per_page, offset=offset)
        exist_posts = _query_execution(exist_posts)
    return exist_posts


def filter_reviewer_discarded(per_page, offset):
    exist_posts = """select * from admin_post where admin_post.reviewer_status is false and 
    admin_post.publisher_status is null and admin_post.promotion is null ORDER BY admin_post.created_at 
    DESC LIMIT {per_page} OFFSET {offset}""".format(per_page=per_page,
                                                    offset=offset)

    exist_posts = _query_execution(exist_posts)
    return exist_posts


def sort_by_sequence(priority, key, filter_key):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    offset = per_page * (page - 1)
    if filter_key == 'final_post':
        if priority:
            if priority == 'expiry':
                exist_posts = """select * from post_bucket_mapping inner join admin_post on 
                post_bucket_mapping.post_id=admin_post.post_id where admin_post.expiry_date is not null and (
                post_bucket_mapping.key='{key}' and post_bucket_mapping.deleted_at is null) and 
                admin_post.publisher_status is true and (admin_post.promotion is null or admin_post.promotion ='promotion_post')
                ORDER BY admin_post.s_id LIMIT {per_page} OFFSET {offset}""".format(key=key,
                                                                                                        per_page=per_page,
                                                                                                        offset=offset)
                exist_posts = _query_execution(exist_posts)
            else:
                exist_posts = """select * from post_bucket_mapping inner join admin_post on 
                post_bucket_mapping.post_id=admin_post.post_id where admin_post.is_priority is true and ( 
                post_bucket_mapping.key='{key}' and post_bucket_mapping.deleted_at is null) and 
                admin_post.publisher_status is true and (admin_post.promotion is null or admin_post.promotion ='promotion_post') ORDER BY 
                admin_post.s_id LIMIT {per_page} OFFSET {offset}""".format(key=key,
                                                                                               per_page=per_page,
                                                                                               offset=offset)
                exist_posts = _query_execution(exist_posts)
        else:
            exist_posts = """select * from post_bucket_mapping inner join admin_post on 
            post_bucket_mapping.post_id=admin_post.post_id where (post_bucket_mapping.key='{key}' and 
            post_bucket_mapping.deleted_at is null) and 
            admin_post.publisher_status is true and (admin_post.promotion is null or admin_post.promotion ='promotion_post') ORDER BY 
            admin_post.s_id LIMIT {per_page} OFFSET {offset}""".format(key=key,
                                                                                           per_page=per_page,
                                                                                           offset=offset)
            exist_posts = _query_execution(exist_posts)

    else:
        return success('SUCCESS', meta={'message': 'Invalid filter key'})

    result = []

    if exist_posts:
        for post in exist_posts:
            post_details = Post.query.filter_by(id=post['post_id']).first()
            if post_details:
                user_data = Users.query.filter_by(id=post_details.user_id, deleted_at=None,user_deleted_at=None).first()
                admin_post_data = AdminPost.query.filter_by(post_id=post['post_id'], deleted_at=None).first()
                bucket_data = PostBucketMapping.query.filter_by(post_id=post['post_id'], deleted_at=None).all()
                if admin_post_data and user_data and bucket_data:
                    user_info = get_user_profile_details(user_data.id)
                    post_list = {}
                    post_list['id'] = post['post_id']
                    post_list['s_id'] = post['s_id']
                    post_list['type'] = post_details.type
                    post_list['title'] = post_details.title
                    post_list['created_at'] = post_details.created_at
                    post_list['description'] = post_details.description
                    post_list['visibility'] = post_details.visibility
                    post_list['meta_data'] = post_details.meta_data
                    post_list['location'] = post_details.location
                    post_list['user_info'] = user_info
                    post_list['is_priority'] = admin_post_data.is_priority
                    post_list['expiry_date'] = admin_post_data.expiry_date
                    buckets = []
                    for bucket in bucket_data:
                        buckets.append(bucket.key)
                    post_list['bucket_name'] = buckets
                    result.append(post_list)
        total_record = len(exist_posts)
        total_pages = total_record // per_page + 1
        return result, total_pages, total_record
    else:
        return None, None, None


def get_master_bucket_list():
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    master_bucket = MasterBucket.query.all()
    list_master_bucket_list = MasterBucket.query.paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    list_master_bucket_list = list_master_bucket_list.items
    total_records = len(master_bucket)
    total_pages = total_records // per_page + 1
    if list_master_bucket_list:
        result = []
        for data in list_master_bucket_list:
            bucket_list = {}
            bucket_list['bucket_id'] = data.id
            bucket_list['bucket_name'] = data.name
            bucket_list['bucket_key'] = data.key
            bucket_list['category_type'] = data.category_type
            result.append(bucket_list)
        return success('SUCCESS', result,meta={'message':'Master Bucket List',
                                   'page_info': {'current_page': page,
                                                 'limit': per_page,
                                                 'total_records': total_records,
                                                 'total_pages': total_pages}})
    else:
        return success('SUCCESS',meta={'message':'No data found'})


def get_promotion_posts(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    post_promotion_lis = Post.query.filter_by(promotion=True, deleted_at=None,status='active').order_by(Post.created_at.desc()).all()
    list_promtion = Post.query.filter_by(promotion=True, deleted_at=None,status='active').order_by(Post.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    list_promtion = list_promtion.items
    total_record = len(post_promotion_lis)
    total_pages = total_record // per_page + 1
    result = []
    comment = []
    if list_promtion:
        for data in list_promtion:
            is_post=AdminPost.query.filter_by(post_id=data.id,deleted_at=None).first()
            if is_post:
                pass
            else:
                user_data = Users.query.filter_by(id=data.user_id,deleted_at=None,user_deleted_at=None).first()
                if user_data:
                    user_info = get_user_profile_details(user_data.id)
                    comment_list = Comment.query.filter_by(post_id=data.id, deleted_at=None).all()
                    if comment_list:
                        for list in comment_list:
                            comment.append(list.comment)
                    get_data = {}
                    get_data['id'] = data.id
                    get_data['type'] = data.type
                    get_data['title'] = data.title
                    get_data['visibility'] = data.visibility
                    get_data['meta_data'] = data.meta_data
                    get_data['location'] = data.location
                    get_data['description'] = data.description
                    get_data['comment'] = comment
                    get_data['user_info'] = user_info
                    like_count = PostReact.query.filter_by(post_id=data.id, deleted_at=None, is_liked=True).count()
                    if like_count > 0:
                        get_data['like_count'] = like_count
                    else:
                        get_data['like_count'] = None

                    get_data['user_id'] = data.user_id
                    result.append(get_data)
        return success('SUCCESS', result, meta={'message': 'promotion List ',
                                   'page_info': {'current_page': page,
                                                 'limit': per_page,
                                                 'total_records': total_record,
                                                 'total_pages': total_pages}})


def final_post_list(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    exist_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if exist_user:
        final_post_count = AdminPost.query.filter_by(publisher_status=True, deleted_at=None).order_by(
            AdminPost.update_at.desc()).all()
        final_post = AdminPost.query.filter_by(publisher_status=True, deleted_at=None).order_by(
            AdminPost.update_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        result = []
        final_list = final_post.items
        total_record = len(final_post_count)
        total_pages = total_record // per_page + 1
        if final_list:
            for item in final_list:
                post_detail = Post.query.filter_by(id=item.post_id, deleted_at=None, status='active').first()
                if post_detail:
                    user_data = Users.query.filter_by(id=post_detail.user_id, user_deleted_at=None,
                                                      deleted_at=None).first()
                    post_list = AdminPost.query.filter_by(post_id=post_detail.id, deleted_at=None).first()
                    bucket_data = PostBucketMapping.query.filter_by(post_id=post_detail.id, deleted_at=None).all()
                    if user_data and post_list and bucket_data:
                        user_info = get_user_profile_details(user_data.id)
                        details = {}
                        details['id'] = post_detail.id
                        details['location'] = post_detail.location
                        details['title'] = post_detail.title
                        details['description'] = post_detail.description
                        details['created_at'] = post_detail.created_at
                        details['visibility'] = post_detail.visibility
                        details['type'] = post_detail.type
                        details['meta_data'] = post_detail.meta_data
                        details['expire_on'] = post_detail.expire_on
                        details['user_info'] = user_info
                        details['priority'] = item.s_id
                        details['expiry_date'] = post_list.expiry_date
                        details['is_priority'] = post_list.is_priority
                        buckets = []
                        for bucket in bucket_data:
                            buckets.append(bucket.key)
                        details['bucket_name'] = buckets
                        result.append(details)
            return success('SUCCESS', result, meta={"message": "post details", 'page_info': {'current_page': page,
                                                                                             'limit': per_page,
                                                                                             'total_records': total_record,
                                                                                             'total_pages': total_pages}})

        else:
            return success('SUCCESS', meta={'message': "No data found"})
    else:
        return success('SUCCESS', meta={'message': "invalid user"})


def discard_final_post(current_user, data):
    post_id = data.get("post_id",None)
    if post_id:
        for post in post_id:
            valid_post = AdminPost.query.filter_by(post_id=post, publisher_status=True, deleted_at=None).first()
            if valid_post:
                valid_post.deleted_at = datetime.datetime.now()
                update_item(valid_post)
            else:
                return success('SUCCESS', meta={'message': 'invalid post'})
        return success('SUCCESS', meta={'message': 'successfully discarded'})
    else:
        return success('SUCCESS', meta={'message': 'please select posts'})


def get_membership_list():
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    membership = """select * from membership where membership_status='active' and deleted_at is null and role not in 
                ('user','business') """
    membership = _query_execution(membership)
    offset = per_page * (page - 1)
    query = """select * from membership where membership_status='active' and deleted_at is null and role not in (
    'user','business') ORDER BY created_at DESC LIMIT {per_page} OFFSET {offset}""" .format(per_page=per_page,
                                                                                            offset=offset)
    user_list = _query_execution(query)

    total_record = len(membership)
    total_pages = total_record // per_page + 1
    result = []
    if user_list:
        for data in user_list:
            user_data = Users.query.filter_by(id=data['user_id'], deleted_at=None, user_deleted_at=None).first()
            post_count = Post.query.filter_by(user_id=data['id'], deleted_at=None).count()
            if user_data:
                list = {}
                list['column 1'] = user_data.id
                list['column 2'] = user_data.profile_image
                list['column 3'] = data['membership_status']
                list['column 4'] = data['membership_type']
                list['column 5'] = user_data.first_name
                list['column 6'] = user_data.last_name
                list['column 7'] = user_data.gender
                list['column 8'] = user_data.email
                list['column 9'] = user_data.phone
                list['column 10'] = user_data.created_at
                if post_count:
                    list['column 11'] = post_count
                else:
                    list['column 11'] = post_count
                result.append(list)
            else:
                return success('SUCCESS', meta={'message': 'invalid data'})
        return success("SUCCESS", {"content": result, 'message': 'User List',
                                   'page_info': {'current_page': page, 'total_data': total_record,
                                                 'total_pages': total_pages,
                                                 'limit': per_page},
                                   'structure': cms_user_grid_fields.STRUCTURE[0],
                                   })


def get_admin_post_list():
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    membership = Membership.query.filter_by(membership_status='active',membership_type='admin', deleted_at=None).all()
    result = []
    content_creator=[]
    if membership:
        for data in membership:
            content_creator.append(data.user_id)
    if content_creator:
        admin_post_list=Post.query.filter(Post.user_id.in_(content_creator) , Post.deleted_at==None).all()
        post_list=Post.query.filter(Post.user_id.in_(content_creator) , Post.deleted_at==None).order_by(Post.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
        post_list = post_list.items
        total_record = len(admin_post_list)
        total_pages = total_record // per_page + 1
        if post_list:
            for list in post_list:
                user_data = Users.query.filter_by(id=list.user_id, deleted_at=None,user_deleted_at=None).first()
                if user_data:
                    user_info = get_user_profile_details(list.user_id)
                    details={}
                    details['id'] = list.id
                    details['location'] = list.location
                    details['title'] = list.title
                    details['description'] = list.description
                    details['created_at'] = list.created_at
                    details['visibility'] = list.visibility
                    details['type'] = list.type
                    details['meta_data'] = list.meta_data
                    details['expire_on'] = list.expire_on
                    details['user_info'] = user_info
                    result.append(details)
            return success('SUCCESS', result, meta={'message': 'Admin Post List',
                                    'page_info': {'current_page': page,
                                                  'total_pages': total_pages,
                                                  'limit': per_page}})
        else:
            return success('SUCCESS', meta={'message': 'No Admin Content'})
    else:
        return success('SUCCESS',meta={'message':'No Admin Content'})


def update_sequence(current_user, data):
    post_id = data.get('post_id')
    s_id = data.get('s_id')
    if post_id:
        exit_post = AdminPost.query.filter_by(post_id=post_id, publisher_status=True, deleted_at=None).first()
        if exit_post and s_id:
            priority_exist = AdminPost.query.filter_by(s_id=s_id, publisher_status=True, deleted_at=None).first()
            if not priority_exist:
                exit_post.s_id = s_id
                update_item(exit_post)
                return success('SUCCESS', meta={'message': 'Priority updated successfully'})
            else:
                return success('SUCCESS', meta={'message': 'Post with this priority already exists'})
        else:
            return success('SUCCESS', meta={'message': 'Invalid post'})
    else:
        return success('SUCCESS', meta={'message': 'post not found'})


def unpublish_post(current_user, data):
    global send_notification
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        post_id = data.get('post_id', None)
        status = data.get('status', None)
        if post_id and status:
            for post in post_id:
                exist_post = Post.query.filter_by(id=post, deleted_at=None).first()
                if exist_post:
                    if status and status in ['inactive', 'active']:
                        exist_post.status = status
                        update_item(exist_post)

                        def send_notification(message_data, title):
                            user_membership = Membership.query.filter_by(user_id=exist_post.user_id,
                                                                         membership_status='active',
                                                                         deleted_at=None).first()
                            if user_membership.fcm_token != None:
                                message = message_data
                                queue_url = PUSH_NOTIFICATION_URL
                                fcm_token = []
                                fcm_token.append(user_membership.fcm_token)
                                payload = {}
                                payload['id'] = str(exist_post.id)
                                payload['current_user'] = str(current_user.id)
                                payload['message'] = message
                                payload['title'] = title
                                payload['fcm_token'] = fcm_token
                                payload['screen_type'] = ''
                                payload['responder_id'] = None
                                send_queue_message(queue_url, payload)
                                # post in-app notification
                                screen_info = {}
                                data = {}
                                screen_info['screen_type'] = ''
                                screen_info['id'] = str(exist_post.id)
                                data['meta_data'] = screen_info
                                add_notification = Notification(user_id=exist_post.user_id, type='post',
                                                                title=payload['title'],
                                                                description=message, read_status=False,
                                                                meta_data=data['meta_data'], c_user=current_user.id,
                                                                notification_status=None)
                                add_item(add_notification)

                        # send_notification()
                        if status == 'active':
                            message_data = 'Adrenaln published your post'
                            title = 'Published Your Post'
                            send_notification(message_data, title)
                        else:
                            message_data = 'Adrenaln unpublished your post'
                            title = 'Unpublished Your Post'
                            send_notification(message_data, title)

                    else:
                        return success('SUCCESS', meta={'message': 'Invalid Status'})
                else:
                    return success('SUCCESS', meta={'message': 'Invalid Post'})
            return success('SUCCESS', meta={'message': 'Post Unpublished Successfully'})
        else:
            return success('SUCCESS', meta={'message': 'Invalid Input'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid User'})



def inactive_post_list(current_user,user_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    status = Post.query.filter_by(user_id=user_id,status='inactive',deleted_at=None).all()
    inactive_list = Post.query.filter_by(user_id=user_id,status='inactive',deleted_at=None).order_by(Post.update_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    inactive_list = inactive_list.items
    total_record = len(status)
    total_pages = total_record // per_page + 1
    result = []
    if inactive_list:
        for data in inactive_list:
            user_data = Users.query.filter_by(id=data.user_id, deleted_at=None,user_deleted_at=None).first()
            if user_data:
                user_info = get_user_profile_details(data.user_id)
                list={}
                list['id'] = data.id
                list['type'] = data.type
                list['title'] = data.title
                list['visibility'] = data.visibility
                list['user_info'] = user_info
                list['group_id'] = data.group_id
                list['meta_data'] = data.meta_data
                list['location'] = data.location
                list['description'] = data.description
                list['created_at'] = data.created_at
                list['status'] = data.status
                result.append(list)
        return success('SUCCESS', result, meta={'message': 'inactive status',
                                                'page_info': {'current_page': page,
                                                              'total_pages': total_pages,
                                                              'limit': per_page}})

    else:
        return success('SUCCESS', meta={'message':'Empty'})


def reported_posts_list(current_user,post_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    result=[]
    reported_posts = ReportedPost.query.filter_by(post_id=post_id,deleted_at=None).all()
    reported_posts_list = ReportedPost.query.filter_by(post_id=post_id,deleted_at=None).distinct(ReportedPost.post_id).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    reported_posts_list = reported_posts_list.items
    total_record = len(reported_posts)
    total_pages = total_record // per_page + 1

    if reported_posts_list:
        reported_post_count = ReportedPost.query.filter_by(post_id=post_id, deleted_at=None).count()
        for data in reported_posts_list:
            post_data = Post.query.filter_by(id=data.post_id,deleted_at=None).first()
            user_data = Users.query.filter_by(id=post_data.user_id, deleted_at=None,user_deleted_at=None).first()
            user_info = get_user_profile_details(user_data.id)
            list={}
            list['id'] = data.id
            list['post_id'] = data.post_id
            list['type'] = post_data.type
            list['title'] = post_data.title
            list['visibility'] = post_data.visibility
            list['user_info'] = user_info
            list['group_id'] = post_data.group_id
            list['media'] = post_data.meta_data['media']
            list['location'] = post_data.location
            list['description'] = post_data.description
            list['created_at'] = post_data.created_at
            list['status'] = post_data.status
            list['count'] = reported_post_count
            result.append(list)

        return success("SUCCESS", result, meta={'message': 'Reported Post List',
                                                'page_info': {'current_page': page,
                                                              'total_pages': total_pages,
                                                              'total_record': total_record,
                                                              'limit': per_page}}
                       )
    else:
        return success('SUCCESS',meta={'message':'Empty Data'})



def feature_program_verification(current_user, data):
    is_featured = data.get("is_featured",None)
    program_id = data.get("program_id", None)
    if is_featured == None:
        return success('SUCCESS',meta={'message':'Please add is_feature key'})
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        user_role = Membership.query.filter_by(user_id=current_user.id, membership_status='active',role='admin',
                                               deleted_at=None).filter()
        if user_role:
            if program_id:
                for id in program_id:
                    feature_program = Programme.query.filter_by(id=id, deleted_at=None).first()
                    if feature_program:
                        feature_program.is_featured = is_featured
                        update_item(feature_program)
                    else:
                        return success('SUCCESS', meta={'message': 'invalid program id'})
                return success('SUCCESS', meta={'message': 'program status is updated'})
            else:
                return success('SUCCESS', meta={'message': 'invalid data'})
    else:
        return success('SUCCESS', meta={'message': 'User not found'})



def get_all_program_list():
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    all_progremme = db.session.query(Programme).filter(Programme.deleted_at==None,or_(Programme.is_featured==0,Programme.is_featured==1)).all()
    offset = per_page * (page - 1)
    get_progremme = """select * from programme where deleted_at is null and (is_featured=1 OR is_featured=0) ORDER BY greatest(created_at,
        update_at) DESC LIMIT {per_page} OFFSET {offset}""".format(per_page=per_page, offset=offset)
    get_progremme = _query_execution(get_progremme)
    # get_progremme = get_progremme.items
    total_records = len(all_progremme)
    total_pages = total_records // per_page + 1
    if get_progremme:
        result = []
        for data in get_progremme:
            user_programme = {}
            user_programme['id'] = data['id']
            user_programme['title'] = data['title']
            user_programme['description'] = data['description']
            user_programme['city'] = data['city']
            user_programme['media'] = data['media']
            user_programme['is_featured'] = data['is_featured']
            result.append(user_programme)
        return success('SUCCESS', result, meta={'message': 'Featured Programmes',
                                                'page_info': {'current_page': page, 'limit': per_page,
                                                              'total_record': total_records,
                                                              'total_pages': total_pages}})
    return success('SUCCESS', meta={'message': 'No Programme Found'})



def search_approved_post(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None, user_deleted_at=None).first()
    if existing_user:
        keyword = request.args.get('keyword')
        search_string = '%{}%'.format(keyword)
        approved_post = AdminPost.query.filter_by(reviewer_status=True, deleted_at=None,
                                                  publisher_status=None).all()
        post_list = []
        if approved_post:
            for item in approved_post:
                post_list.append(str(item.post_id))
        search_list = Post.query.join(Users, Users.id == Post.user_id).filter(
            or_((Users.first_name.ilike(search_string)), (Post.description.ilike(search_string))),
            Post.id.in_(post_list)).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        if search_list:
            posts = search_list.items
            total_record = len(posts)
            total_pages = total_record // per_page + 1
            if posts:
                result = []
                for data in posts:
                    user_data = Users.query.filter_by(id=data.user_id, deleted_at=None,
                                                      user_deleted_at=None).first()
                    post_data = AdminPost.query.filter_by(post_id=data.id, deleted_at=None).first()
                    bucket_data = PostBucketMapping.query.filter_by(post_id=data.id, deleted_at=None).first()
                    if user_data and post_data and bucket_data:
                        user_info = get_user_profile_details(user_data.id)
                        details = {}
                        details['id'] = data.id
                        details['location'] = data.location
                        details['title'] = data.title
                        details['description'] = data.description
                        details['created_at'] = data.created_at
                        details['visibility'] = data.visibility
                        details['type'] = data.type
                        details['meta_data'] = data.meta_data
                        details['expire_on'] = data.expire_on
                        details['user_info'] = user_info
                        details['expiry_date'] = post_data.expiry_date
                        details['is_priority'] = post_data.is_priority
                        details['bucket_name'] = bucket_data.key
                        result.append(details)
                return success('SUCCESS', result, meta={'message': 'post list',
                                                        'page_info': {'current_page': page, 'limit': per_page,
                                                                      'total_records': total_record,'total_pages':total_pages}})
            else:
                return success('SUCCESS', meta={'message': 'No post found'})
        else:
            return success('SUCCESS', meta={'message': 'No post'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid user'})


def search_final_post(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None, user_deleted_at=None).first()
    if existing_user:
        keyword = request.args.get('keyword')
        search_string = '%{}%'.format(keyword)
        final_post = AdminPost.query.filter_by(publisher_status=True, deleted_at=None).all()
        post_list = []
        if final_post:
            for item in final_post:
                post_list.append(str(item.post_id))
        search_list = Post.query.join(Users, Users.id == Post.user_id).filter(
            or_((Users.first_name.ilike(search_string)), (Post.description.ilike(search_string))),
            Post.id.in_(post_list), Post.status == 'active').paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        if search_list:
            posts = search_list.items
            total_record = len(posts)
            total_pages = total_record // per_page + 1
            if posts:
                result = []
                for data in posts:
                    user_data = Users.query.filter_by(id=data.user_id, deleted_at=None,
                                                      user_deleted_at=None).first()
                    post_data = AdminPost.query.filter_by(post_id=data.id, deleted_at=None).first()
                    bucket_data = PostBucketMapping.query.filter_by(post_id=data.id, deleted_at=None).first()
                    if user_data and post_data and bucket_data:
                        user_info = get_user_profile_details(user_data.id)
                        details = {}
                        details['id'] = data.id
                        details['location'] = data.location
                        details['title'] = data.title
                        details['description'] = data.description
                        details['created_at'] = data.created_at
                        details['visibility'] = data.visibility
                        details['type'] = data.type
                        details['meta_data'] = data.meta_data
                        details['expire_on'] = data.expire_on
                        details['priority'] = post_data.s_id
                        details['user_info'] = user_info
                        details['expiry_date'] = post_data.expiry_date
                        details['is_priority'] = post_data.is_priority
                        details['bucket_name'] = bucket_data.key
                        result.append(details)
                return success('SUCCESS', result, meta={'message': 'post list',
                                                        'page_info': {'current_page': page, 'limit': per_page,
                                                                      'total_records': total_record,'total_pages':total_pages}})
            else:
                return success('SUCCESS', meta={'message': 'No post found'})
        else:
            return success('SUCCESS', meta={'message': 'No post'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid user'})


def search_discarded_post(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None, user_deleted_at=None).first()
    if existing_user:
        keyword = request.args.get('keyword')
        search_string = '%{}%'.format(keyword)
        discarded_post = AdminPost.query.filter_by(reviewer_status=False, deleted_at=None, publisher_status=None).all()
        post_list = []
        if discarded_post:
            for item in discarded_post:
                post_list.append(str(item.post_id))
        # if keyword and type == 'name':
        search_list = Post.query.join(Users, Users.id == Post.user_id).filter(
            or_((Users.first_name.ilike(search_string)), (Post.description.ilike(search_string))),
            Post.id.in_(post_list), Post.status == 'active', ).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        if search_list:
            posts = search_list.items
            total_record = len(posts)
            total_pages = total_record // per_page + 1
            if posts:
                result = []
                for data in posts:
                    user_data = Users.query.filter_by(id=data.user_id, deleted_at=None,
                                                      user_deleted_at=None).first()
                    post_data = AdminPost.query.filter_by(post_id=data.id, deleted_at=None).first()
                    if user_data and post_data:
                        user_info = get_user_profile_details(user_data.id)
                        details = {}
                        details['id'] = data.id
                        details['location'] = data.location
                        details['title'] = data.title
                        details['description'] = data.description
                        details['created_at'] = data.created_at
                        details['visibility'] = data.visibility
                        details['type'] = data.type
                        details['meta_data'] = data.meta_data
                        details['expire_on'] = data.expire_on
                        details['user_info'] = user_info
                        details['expiry_date'] = post_data.expiry_date
                        details['is_priority'] = post_data.is_priority
                        result.append(details)
                return success('SUCCESS', result, meta={'message': 'post list',
                                                        'page_info': {'current_page': page, 'limit': per_page,
                                                                      'total_records': total_record,'total_pages': total_pages}})
            else:
                return success('SUCCESS', meta={'message': 'No post found'})
        else:
            return success('SUCCESS', meta={'message': 'No post'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid post'})


def search_reviewer_feed(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None, user_deleted_at=None).first()
    if existing_user:
        keyword = request.args.get('keyword')
        search_string = '%{}%'.format(keyword)
        statement = exists().where(AdminPost.post_id == Post.id)
        feed_post = db.session.query(Post).filter(~statement, Post.visibility == 'all', Post.type == 'regular',
                                                  Post.promotion != True, Post.deleted_at == None,
                                                  Post.status == 'active',
                                                  Post.group_id == None).all()
        post_list = []
        if feed_post:
            for item in feed_post:
                post_list.append(str(item.id))
        search_list = Post.query.join(Users, Users.id == Post.user_id).filter(
            or_((Users.first_name.ilike(search_string)), (Post.description.ilike(search_string))),
            Post.id.in_(post_list), Post.status == 'active').paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        if search_list:
            posts = search_list.items
            total_record = len(posts)
            total_pages = total_record // per_page + 1
            if posts:
                result = []
                for data in posts:
                    user_data = Users.query.filter_by(id=data.user_id, deleted_at=None,
                                                      user_deleted_at=None).first()
                    if user_data:
                        user_info = get_user_profile_details(user_data.id)
                        details = {}
                        details['id'] = data.id
                        details['location'] = data.location
                        details['title'] = data.title
                        details['description'] = data.description
                        details['created_at'] = data.created_at
                        details['visibility'] = data.visibility
                        details['type'] = data.type
                        details['meta_data'] = data.meta_data
                        details['expire_on'] = data.expire_on
                        details['user_info'] = user_info
                        result.append(details)
                return success('SUCCESS', result, meta={'message': 'post list',
                                                        'page_info': {'current_page': page, 'limit': per_page,
                                                                      'total_records': total_record,'total_pages': total_pages}})
            else:
                return success('SUCCESS', meta={'message': 'No post found'})
        else:
            return success('SUCCESS', meta={'message': 'No post'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid user'})


def user_friend_list_info(current_user,user_id):
    result=[]
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        exist_user = Users.query.filter_by(id=user_id, deleted_at=None,user_deleted_at=None).first()
        if exist_user:
            if exist_user:
                friend_list_count=Contact.query.filter_by(user_id=user_id,friend_status='friends',deleted_at=None).count()
                if friend_list_count:
                    followers = Contact.query.filter_by(contact_id=user_id, is_following=True,following_status='following',
                                                              deleted_at=None).count()
                    following = Contact.query.filter_by(user_id=user_id, following_status='following',is_following=True,
                                                              deleted_at=None).count()
                    group_count = db.session.query(GroupMembers).filter(GroupMembers.user_id==user_id,GroupMembers.status=='active',
                        GroupMembers.deleted_at ==None).count()

                    list={}
                    list['friend_list']=friend_list_count
                    list['following']=following
                    list['followers']=followers
                    list['groups']=group_count
                    result.append(list)
                return success('SUCCESS', result, meta={'message': 'friend list'})
    else:
        return success('SUCCESS', meta={'message':'Invalid User'})



def add_profile_terms_conditions(current_user, data):
    section = data.get('id', None)
    terms_and_conditions = data.get('terms_and_conditions', None)
    exist_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if exist_user:
        if section and terms_and_conditions:
            section_exist = TermsConditions.query.filter_by(id=section, deleted_at=None).first()
            if section_exist:
                section_exist.terms_condition = terms_and_conditions
                update_item(section_exist)
                return success('SUCCESS', meta={'message': 'Terms and Conditions updated'})
            else:
                # add_terms = TermsConditions(section=section, terms_condition=terms_and_conditions)
                # add_item(add_terms)
                return success('SUCCESS', meta={'message': 'Successfully added Terms and Conditions'})
        else:
            return success('SUCCESS', meta={'message': 'Invalid inputs'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid User'})


def remove_profile_terms_conditions(current_user, section_id):
    exist_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if exist_user:
        section_exist = TermsConditions.query.filter_by(id=section_id, deleted_at=None).first()
        if section_exist:
            section_exist.section = None
            update_item(section_exist)
            return success('SUCCESS', meta={'message': 'Removed Successfully'})
        else:
            return success('SUCCESS', meta={'message': 'Section not found'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid User'})


def section_list(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    exist_user = Users.query.filter_by(id=current_user.id, deleted_at=None, user_deleted_at=None).first()
    if exist_user:
        all_sections=TermsConditions.query.filter_by(deleted_at=None).order_by(TermsConditions.section.asc()).all()
        sections = TermsConditions.query.filter_by(deleted_at=None).order_by(TermsConditions.section.asc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False)

        section_data = sections.items
        total_records=len(all_sections)
        total_pages = total_records // per_page + 1
        if section_data:
            result = []
            for data in section_data:
                section_data={}
                section_data['id']=data.id
                section_data['section']=data.section
                section_data['terms_condition']= data.terms_condition
                result.append(section_data)
            return success("SUCCESS", result, meta={"message": "Section List",
                                                    'page_info': {'limit': per_page, 'current_page': page,
                                                                  'total_records':total_records,
                                                                  'total_pages':total_pages}})
        else:
            return success('SUCCESS', meta={'message': 'No data found'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid user'})


def search_promotion_posts(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    exist_user = Users.query.filter_by(id=current_user.id, deleted_at=None, user_deleted_at=None).first()
    if exist_user:
        keyword = request.args.get('keyword')
        search_string = '%{}%'.format(keyword)
        post_list = []
        post_promotion_list = Post.query.filter_by(promotion=True, deleted_at=None, status='active').all()
        if post_promotion_list:
            for post in post_promotion_list:
                post_list.append(post.id)
        post_promotion = Post.query.join(Users, Users.id == Post.user_id).filter(
            or_((Users.first_name.ilike(search_string)), (Post.description.ilike(search_string))),
            Post.id.in_(post_list), Post.status == 'active').paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        if post_promotion:
            posts = post_promotion.items
            total_record = len(posts)
            total_pages = total_record // per_page + 1
            if posts:
                result = []
                for data in posts:
                    user_data = Users.query.filter_by(id=data.user_id, deleted_at=None,
                                                      user_deleted_at=None).first()
                    post_data = AdminPost.query.filter_by(post_id=data.id, deleted_at=None).first()
                    bucket_data = PostBucketMapping.query.filter_by(post_id=data.id, deleted_at=None).first()
                    if user_data:
                        user_info = get_user_profile_details(user_data.id)
                        details = {}
                        details['id'] = data.id
                        details['location'] = data.location
                        details['title'] = data.title
                        details['description'] = data.description
                        details['created_at'] = data.created_at
                        details['visibility'] = data.visibility
                        details['type'] = data.type
                        details['meta_data'] = data.meta_data
                        details['expire_on'] = data.expire_on
                        details['user_info'] = user_info
                        if post_data:
                            details['expiry_date'] = post_data.expiry_date
                            details['is_priority'] = post_data.is_priority
                        else:
                            details['expiry_date'] = None
                            details['is_priority'] = None
                        if bucket_data:
                            details['bucket_name'] = bucket_data.key
                        else:
                            details['bucket_name'] = None
                        result.append(details)
                return success('SUCCESS', result, meta={'message': 'post list',
                                                        'page_info': {'current_page': page, 'limit': per_page,
                                                                      'total_records': total_record,'total_pages':total_pages}})
            else:
                return success('SUCCESS', meta={'message': 'No post found'})
        else:
            return success('SUCCESS', meta={'message': 'No post'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid user'})


def search_approved_promotion_posts(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    exist_user = Users.query.filter_by(id=current_user.id, deleted_at=None, user_deleted_at=None).first()
    if exist_user:
        keyword = request.args.get('keyword')
        search_string = '%{}%'.format(keyword)
        post_list = []
        approved_post = Post.query.join(AdminPost,Post.id == AdminPost.post_id).filter(Post.promotion==True,
                                                                                       Post.deleted_at==None,
                                                                                       Post.status == 'active',
                                                                                       AdminPost.reviewer_status==True,
                                                                                       AdminPost.deleted_at==None).all()
        if approved_post:
            for post in approved_post:
                post_list.append(post.id)
        post_promotion = Post.query.join(Users, Users.id == Post.user_id).filter(
            or_((Users.first_name.ilike(search_string)), (Post.description.ilike(search_string))),
            Post.id.in_(post_list), Post.status == 'active').paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        if post_promotion:
            posts = post_promotion.items
            total_record = len(posts)
            total_pages = total_record // per_page + 1
            if posts:
                result = []
                for data in posts:
                    user_data = Users.query.filter_by(id=data.user_id, deleted_at=None,
                                                      user_deleted_at=None).first()
                    post_data = AdminPost.query.filter_by(post_id=data.id, deleted_at=None).first()
                    bucket_data = PostBucketMapping.query.filter_by(post_id=data.id, deleted_at=None).first()
                    if user_data:
                        user_info = get_user_profile_details(user_data.id)
                        details = {}
                        details['id'] = data.id
                        details['location'] = data.location
                        details['title'] = data.title
                        details['description'] = data.description
                        details['created_at'] = data.created_at
                        details['visibility'] = data.visibility
                        details['type'] = data.type
                        details['meta_data'] = data.meta_data
                        details['expire_on'] = data.expire_on
                        details['user_info'] = user_info
                        if post_data:
                            details['expiry_date'] = post_data.expiry_date
                            details['is_priority'] = post_data.is_priority
                        else:
                            details['expiry_date'] = None
                            details['is_priority'] = None
                        if bucket_data:
                            details['bucket_name'] = bucket_data.key
                        else:
                            details['bucket_name'] = None
                        result.append(details)
                return success('SUCCESS', result, meta={'message': 'post list',
                                                        'page_info': {'current_page': page, 'limit': per_page,
                                                                      'total_records': total_record,'total_pages':total_pages}})
            else:
                return success('SUCCESS', meta={'message': 'No post found'})
        else:
            return success('SUCCESS', meta={'message': 'No post'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid user'})


def search_discarded_promotion_posts(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    exist_user = Users.query.filter_by(id=current_user.id, deleted_at=None, user_deleted_at=None).first()
    if exist_user:
        keyword = request.args.get('keyword')
        search_string = '%{}%'.format(keyword)
        post_list = []
        approved_post = Post.query.join(AdminPost, Post.id == AdminPost.post_id).filter(Post.promotion == True,
                                                                                        Post.deleted_at == None,
                                                                                        Post.status == 'active',
                                                                                        AdminPost.reviewer_status == False,
                                                                                        AdminPost.deleted_at == None).all()
        if approved_post:
            for post in approved_post:
                post_list.append(post.id)
        post_promotion = Post.query.join(Users, Users.id == Post.user_id).filter(
            or_((Users.first_name.ilike(search_string)), (Post.description.ilike(search_string))),
            Post.id.in_(post_list), Post.status == 'active').paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        if post_promotion:
            posts = post_promotion.items
            total_record = len(posts)
            total_pages = total_record // per_page + 1
            if posts:
                result = []
                for data in posts:
                    user_data = Users.query.filter_by(id=data.user_id, deleted_at=None,
                                                      user_deleted_at=None).first()
                    post_data = AdminPost.query.filter_by(post_id=data.id, deleted_at=None).first()
                    bucket_data = PostBucketMapping.query.filter_by(post_id=data.id, deleted_at=None).first()
                    if user_data:
                        user_info = get_user_profile_details(user_data.id)
                        details = {}
                        details['id'] = data.id
                        details['location'] = data.location
                        details['title'] = data.title
                        details['description'] = data.description
                        details['created_at'] = data.created_at
                        details['visibility'] = data.visibility
                        details['type'] = data.type
                        details['meta_data'] = data.meta_data
                        details['expire_on'] = data.expire_on
                        details['user_info'] = user_info
                        if post_data:
                            details['expiry_date'] = post_data.expiry_date
                            details['is_priority'] = post_data.is_priority
                        else:
                            details['expiry_date'] = None
                            details['is_priority'] = None
                        if bucket_data:
                            details['bucket_name'] = bucket_data.key
                        else:
                            details['bucket_name'] = None
                        result.append(details)
                return success('SUCCESS', result, meta={'message': 'post list',
                                                        'page_info': {'current_page': page, 'limit': per_page,
                                                                      'total_records': total_record,'total_pages':total_pages}})
            else:
                return success('SUCCESS', meta={'message': 'No post found'})
        else:
            return success('SUCCESS', meta={'message': 'No post'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid user'})


def friend_req_count(current_user,data):
    result = []
    from_date = data.get('from_date')
    to_date = data.get('to_date')
    existing_user = Users.query.filter_by(deleted_at=None, user_deleted_at=None).all()
    if from_date and to_date:
        if existing_user:
            for datass in existing_user:
                membere_ship=Membership.query.filter_by(user_id=datass.id,membership_type='general', membership_status='active',deleted_at=None).all()
                if membere_ship:
                    friends_count =   db.session.query(Contact).filter(and_(func.date(Contact.created_at) >= from_date),
                                                       func.date(Contact.created_at) <= to_date).filter(Contact.friend_status == 'friends',Contact.deleted_at==None).count()



                    pending_request_count =  db.session.query(Contact).filter(and_(func.date(Contact.created_at) >= from_date),
                                                       func.date(Contact.created_at) <= to_date).filter(Contact.friend_status == 'pending',Contact.deleted_at==None).count()


                    acivity_post_count = db.session.query(Post).filter(and_(func.date(Post.created_at) >= from_date),
                                                       func.date(Post.created_at) <= to_date).filter(Post.type == 'activity',Post.deleted_at==None).count()
                    regular_post_count = db.session.query(Post).filter(and_(func.date(Post.created_at) >= from_date),
                                                       func.date(Post.created_at) <= to_date).filter(Post.type == 'regular',Post.deleted_at==None).count()
                    watch_post_count = db.session.query(Post).filter(and_(func.date(Post.created_at) >= from_date),
                                                       func.date(Post.created_at) <= to_date).filter(Post.type == 'watch_activity',Post.deleted_at==None).count()
                    record_post_count = db.session.query(Post).filter(and_(func.date(Post.created_at) >= from_date),
                                                       func.date(Post.created_at) <= to_date).filter(Post.type == 'record_activity',Post.deleted_at==None).count()
                    betting_post_count = db.session.query(Post).filter(and_(func.date(Post.created_at) >= from_date),
                                                       func.date(Post.created_at) <= to_date).filter(Post.type == 'betting',Post.deleted_at==None).count()
                    group_accepted_count = db.session.query(GroupMembers).filter(and_(func.date(GroupMembers.created_at) >= from_date),
                                                       func.date(GroupMembers.created_at) <= to_date).filter(GroupMembers.status == 'active',GroupMembers.deleted_at==None).count()
                    users_count = db.session.query(Membership).filter(and_(func.date(Membership.created_at) >= from_date),
                                                       func.date(Membership.created_at) <= to_date).filter(Membership.deleted_at==None,Membership.last_feed_viewed>=from_date).count()
                    total_posts = acivity_post_count+regular_post_count+record_post_count+watch_post_count+betting_post_count
                    comments_count = db.session.query(Comment).filter(and_(func.date(Comment.created_at) >= from_date),
                                                       func.date(Comment.created_at) <= to_date).filter(Comment.deleted_at==None).count()
                    betting_accepted_count = db.session.query(UserBettings).filter(and_(func.date(UserBettings.created_at) >= from_date),
                                                       func.date(UserBettings.created_at) <= to_date).filter(UserBettings.betting_status == 'confirmed',UserBettings.deleted_at==None).count()
                    reported_post_count = db.session.query(ReportedPost).filter(and_(func.date(ReportedPost.created_at) >= from_date),
                                                       func.date(ReportedPost.created_at) <= to_date).filter(ReportedPost.deleted_at==None).count()
                    total_groups = db.session.query(Group).filter(
                        and_(func.date(Group.created_at) >= from_date),
                        func.date(Group.created_at) <= to_date).filter(Group.deleted_at == None).count()
                    total_likes= db.session.query(PostReact).filter(
                        and_(func.date(PostReact.created_at) >= from_date),
                        func.date(PostReact.created_at) <= to_date).filter(PostReact.is_liked=='true',PostReact.deleted_at == None).count()
                    india_users_bucket = db.session.query(Users).filter(
                        and_(func.date(Users.created_at) >= from_date),
                        func.date(Users.created_at) <= to_date).filter(Users.deleted_at==None,Users.user_deleted_at == None,Users.phone_code=='91',Users.business_account==None,Users.can_follows==None).count()
                    indian_business_users_bucket = db.session.query(Users).filter(
                        and_(func.date(Users.created_at) >= from_date),
                        func.date(Users.created_at) <= to_date).filter(Users.deleted_at==None,Users.user_deleted_at == None,Users.phone_code=='91',Users.business_account=='true',Users.can_follows=='true').count()
                    international_users_bucket = db.session.query(Users).filter(
                        and_(func.date(Users.created_at) >= from_date),
                        func.date(Users.created_at) <= to_date).filter(Users.deleted_at==None,Users.user_deleted_at == None,Users.phone_code!='91',Users.business_account=='true',Users.can_follows=='true').count()
                    new_users_count = db.session.query(Users).filter(
                        and_(func.date(Users.created_at) >= from_date),
                        func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                                   Users.user_deleted_at == None,).count()
                    health_records = db.session.query(HealthReport).filter(
                        and_(func.date(HealthReport.created_at) >= from_date),
                        func.date(HealthReport.created_at) <= to_date).filter(HealthReport.deleted_at == None).count()
                    feature_programs = db.session.query(Programme).filter(
                        and_(func.date(Programme.created_at) >= from_date),
                        func.date(Programme.created_at) <= to_date).filter(Programme.deleted_at == None).count()
                    contact_me_details = db.session.query(ContactMe).filter(
                        and_(func.date(ContactMe.created_at) >= from_date),
                        func.date(ContactMe.created_at) <= to_date).filter(ContactMe.deleted_at == None).count()
                    follower_list=db.session.query(Contact).filter(
                        and_(func.date(Contact.created_at) >= from_date),
                        func.date(Contact.created_at) <= to_date).filter(Contact.deleted_at == None,Contact.is_following==True,Contact.following_status=='following').count()
                    individual_user = db.session.query(Users).filter(
                        and_(func.date(Users.created_at) >=from_date),
                        func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                       Users.user_deleted_at == None,
                                                                       Users.business_account == False,
                                                                       Users.can_follows == False).count()
                    business_users = db.session.query(Users).filter(
                        and_(func.date(Users.created_at) >= from_date),
                        func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                       Users.user_deleted_at == None,
                                                                       Users.business_account == True).count()
                    follow_me_user = db.session.query(Users).filter(
                        and_(func.date(Users.created_at) >= from_date),
                        func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                       Users.user_deleted_at == None,
                                                                       Users.can_follows == True).count()


                    if acivity_post_count >= 0:
                        list = {}
                        list['name'] = 'Activity Post'
                        list['count'] = acivity_post_count
                        result.append(list)
                    if watch_post_count >= 0:
                        list1 = {}
                        list1['name'] = "Watch Post"
                        list1['count'] = watch_post_count
                        result.append(list1)
                    if regular_post_count >= 0:
                        list2 = {}
                        list2['name'] = "Regular Post"
                        list2['count'] = regular_post_count
                        result.append(list2)
                    if record_post_count >= 0:
                        list3 = {}
                        list3['name'] = "Record Post"
                        list3['count'] = record_post_count
                        result.append(list3)
                    if betting_post_count >= 0:
                        list4 = {}
                        list4['name'] = "Prediction Post"
                        list4['count'] = betting_post_count
                        result.append(list4)
                    if total_posts:
                        list14 = {}
                        list14['name'] = 'Total Posts'
                        list14['count'] = total_posts
                        result.append(list14)

                    if follower_list>=0:
                        follower_list1={}
                        follower_list1['name'] = "Follow me requests"
                        follower_list1['count'] = follower_list
                        result.append(follower_list1)

                    if pending_request_count >= 0:
                        list5 = {}
                        list5["name"] = "Friend Requests"
                        list5["count"] = pending_request_count
                        result.append(list5)
                    if friends_count >= 0:
                        list6 = {}
                        list6['name'] = "Accepted FR"
                        list6['count'] = friends_count
                        result.append(list6)
                    if total_groups >= 0:
                        list18 = {}
                        list18['name'] = "New Groups"
                        list18['count'] = total_groups
                        result.append(list18)
                    if group_accepted_count >= 0:
                        list7 = {}
                        list7['name'] = "Accepted GroupInvites"
                        list7['count'] = group_accepted_count
                        result.append(list7)

                    if new_users_count >= 0:
                        new_users = {}
                        new_users['name'] = "New Users"
                        new_users['count'] = new_users_count
                        result.append(new_users)
                    if individual_user >= 0:
                        list1 = {}
                        list1['name'] = 'Individual Users'
                        list1['count'] = individual_user
                        result.append(list1)
                    if business_users >= 0:
                        list2 = {}
                        list2['name'] = 'Business Users'
                        list2['count'] = business_users
                        result.append(list2)
                    if follow_me_user >= 0:
                        list3 = {}
                        list3['name'] = 'Follow Me Users'
                        list3['count'] = follow_me_user
                        result.append(list3)
                    if india_users_bucket >= 0:
                        lists1 = {}
                        lists1['name'] = "India Bucket"
                        lists1['count'] = india_users_bucket
                        result.append(lists1)
                    if international_users_bucket >= 0:
                        list111 = {}
                        list111['name'] = "International Bucket"
                        list111['count'] = international_users_bucket
                        result.append(list111)

                    if indian_business_users_bucket >= 0:
                        list33 = {}
                        list33['name'] = "Indian biz account"
                        list33['count'] = indian_business_users_bucket
                        result.append(list33)
                    if comments_count >= 0:
                        list9 = {}
                        list9['name'] = "Total Comments"
                        list9['count'] = comments_count
                        result.append(list9)
                    if total_likes >= 0:
                        list13 = {}
                        list13['name'] = 'Total Likes'
                        list13['count'] = total_likes
                        result.append(list13)
                    if betting_accepted_count >= 0:
                        list10 = {}
                        list10['name'] = "Prediction Accept"
                        list10['count'] = betting_accepted_count
                        result.append(list10)
                    if health_records >= 0:
                        hr_list = {}
                        hr_list['name'] = "HR added"
                        hr_list['count'] = health_records
                        result.append(hr_list)
                    if feature_programs >= 0:
                        feature_program_list = {}
                        feature_program_list['name'] = "Fprog added"
                        feature_program_list['count'] = feature_programs
                        result.append(feature_program_list)
                    if contact_me_details >= 0:
                        contact_me_list = {}
                        contact_me_list['name'] = 'Contact me emails'
                        contact_me_list['count'] = contact_me_details
                        result.append(contact_me_list)
                        # feature_programs
                    if reported_post_count >= 0:
                        list11 = {}
                        list11['name'] = "Reported Posts"
                        list11['count'] = reported_post_count
                        result.append(list11)

                    if data["xlsx_required"]:
                        results = []
                        status, file = generate_mis_list(result,from_date,to_date)
                        if status:
                            mis_list = {}
                            mis_list['file'] = file
                            results.append(mis_list)
                            return success('SUCCESS', results, meta={'message': 'file is downloaded'})
                return success('SUCCESS', result, meta={'message': 'user list'})
        else:
            return success('SUCCESS', meta={'No data found'})
    elif to_date and not from_date:
        if existing_user:
            for datass in existing_user:
                membere_ship = Membership.query.filter_by(user_id=datass.id, membership_type='general',
                                                          membership_status='active', deleted_at=None).all()
                if membere_ship:
                    friends_count = db.session.query(Contact).filter(and_(func.date(Contact.created_at) >='0001-01-01'),
                                                                     func.date(Contact.created_at) <= to_date).filter(
                        Contact.friend_status == 'friends', Contact.deleted_at == None).count()

                    pending_request_count = db.session.query(Contact).filter(
                        and_(func.date(Contact.created_at) >= '0001-01-01'),
                        func.date(Contact.created_at) <= to_date).filter(Contact.friend_status == 'pending',
                                                                         Contact.deleted_at == None).count()


                    acivity_post_count = db.session.query(Post).filter(and_(func.date(Post.created_at) >= '0001-01-01'),
                                                                       func.date(Post.created_at) <= to_date).filter(
                        Post.type == 'activity', Post.deleted_at == None).count()
                    regular_post_count = db.session.query(Post).filter(and_(func.date(Post.created_at) >= '0001-01-01'),
                                                                       func.date(Post.created_at) <= to_date).filter(
                        Post.type == 'regular', Post.deleted_at == None).count()
                    watch_post_count = db.session.query(Post).filter(and_(func.date(Post.created_at) >= '0001-01-01'),
                                                                     func.date(Post.created_at) <= to_date).filter(
                        Post.type == 'watch_activity', Post.deleted_at == None).count()
                    record_post_count = db.session.query(Post).filter(and_(func.date(Post.created_at) >= '0001-01-01'),
                                                                      func.date(Post.created_at) <= to_date).filter(
                        Post.type == 'record_activity', Post.deleted_at == None).count()
                    betting_post_count = db.session.query(Post).filter(and_(func.date(Post.created_at) >= '0001-01-01'),
                                                                       func.date(Post.created_at) <= to_date).filter(
                        Post.type == 'betting', Post.deleted_at == None).count()
                    group_accepted_count = db.session.query(GroupMembers).filter(
                        and_(func.date(GroupMembers.created_at) >= '0001-01-01'),
                        func.date(GroupMembers.created_at) <= to_date).filter(GroupMembers.status == 'active',
                                                                              GroupMembers.deleted_at == None).count()
                    users_count = db.session.query(Membership).filter(and_(func.date(Membership.created_at) >= '0001-01-01'),
                                                                      func.date(Membership.created_at) <= to_date).filter(
                        Membership.deleted_at == None, Membership.last_feed_viewed >= '0001-01-01').count()
                    total_posts = acivity_post_count + regular_post_count + record_post_count + watch_post_count + betting_post_count
                    comments_count = db.session.query(Comment).filter(and_(func.date(Comment.created_at) >= '0001-01-01'),
                                                                      func.date(Comment.created_at) <= to_date).filter(
                        Comment.deleted_at == None).count()
                    betting_accepted_count = db.session.query(UserBettings).filter(
                        and_(func.date(UserBettings.created_at) >= '0001-01-01'),
                        func.date(UserBettings.created_at) <= to_date).filter(UserBettings.betting_status == 'confirmed',
                                                                              UserBettings.deleted_at == None).count()
                    reported_post_count = db.session.query(ReportedPost).filter(
                        and_(func.date(ReportedPost.created_at) >= '0001-01-01'),
                        func.date(ReportedPost.created_at) <= to_date).filter(ReportedPost.deleted_at == None).count()
                    total_groups = db.session.query(Group).filter(
                        and_(func.date(Group.created_at) >= '0001-01-01'),
                        func.date(Group.created_at) <= to_date).filter(Group.deleted_at == None).count()
                    total_likes = db.session.query(PostReact).filter(
                        and_(func.date(PostReact.created_at) >= '0001-01-01'),
                        func.date(PostReact.created_at) <= to_date).filter(PostReact.is_liked == 'true',
                                                                           PostReact.deleted_at == None).count()
                    india_users_bucket = db.session.query(Users).filter(
                        and_(func.date(Users.created_at) >= '0001-01-01'),
                        func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                       Users.user_deleted_at == None,
                                                                       Users.phone_code == '91',
                                                                       Users.business_account == None,
                                                                       Users.can_follows == None).count()
                    indian_business_users_bucket = db.session.query(Users).filter(
                        and_(func.date(Users.created_at) >= '0001-01-01'),
                        func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                       Users.user_deleted_at == None,
                                                                       Users.phone_code == '91',
                                                                       Users.business_account == 'true',
                                                                       Users.can_follows == 'true').count()
                    international_users_bucket = db.session.query(Users).filter(
                        and_(func.date(Users.created_at) >= '0001-01-01'),
                        func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                       Users.user_deleted_at == None,
                                                                       Users.phone_code != '91',
                                                                       Users.business_account == 'true',
                                                                       Users.can_follows == 'true').count()
                    new_users_count = db.session.query(Users).filter(
                        and_(func.date(Users.created_at) >= '0001-01-01'),
                        func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                       Users.user_deleted_at == None, ).count()
                    health_records = db.session.query(HealthReport).filter(
                        and_(func.date(HealthReport.created_at) >= '0001-01-01'),
                        func.date(HealthReport.created_at) <= to_date).filter(HealthReport.deleted_at == None).count()
                    feature_programs = db.session.query(Programme).filter(
                        and_(func.date(Programme.created_at) >= '0001-01-01'),
                        func.date(Programme.created_at) <= to_date).filter(Programme.deleted_at == None).count()
                    contact_me_details = db.session.query(ContactMe).filter(
                        and_(func.date(ContactMe.created_at) >= '0001-01-01'),
                        func.date(ContactMe.created_at) <= to_date).filter(ContactMe.deleted_at == None).count()
                    follower_list = db.session.query(Contact).filter(
                        and_(func.date(Contact.created_at) >= '0001-01-01'),
                        func.date(Contact.created_at) <= to_date).filter(Contact.deleted_at == None,
                                                                         Contact.is_following == True,
                                                                         Contact.following_status == 'following').count()
                    individual_user = db.session.query(Users).filter(
                        and_(func.date(Users.created_at) >= '0001-01-01'),
                        func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                       Users.user_deleted_at == None,
                                                                       Users.business_account == False,
                                                                       Users.can_follows == False).count()
                    business_users = db.session.query(Users).filter(
                        and_(func.date(Users.created_at) >= '0001-01-01'),
                        func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                       Users.user_deleted_at == None,
                                                                       Users.business_account == True).count()
                    follow_me_user = db.session.query(Users).filter(
                        and_(func.date(Users.created_at) >= '0001-01-01'),
                        func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                       Users.user_deleted_at == None,
                                                                       Users.can_follows == True).count()

                    if acivity_post_count >= 0:
                        list = {}
                        list['name'] = 'Activity Post'
                        list['count'] = acivity_post_count
                        result.append(list)
                    if watch_post_count >= 0:
                        list1 = {}
                        list1['name'] = "Watch Post"
                        list1['count'] = watch_post_count
                        result.append(list1)
                    if regular_post_count >= 0:
                        list2 = {}
                        list2['name'] = "Regular Post"
                        list2['count'] = regular_post_count
                        result.append(list2)
                    if record_post_count >= 0:
                        list3 = {}
                        list3['name'] = "Record Post"
                        list3['count'] = record_post_count
                        result.append(list3)
                    if betting_post_count >= 0:
                        list4 = {}
                        list4['name'] = "Prediction Post"
                        list4['count'] = betting_post_count
                        result.append(list4)
                    if total_posts:
                        list14 = {}
                        list14['name'] = 'Total Posts'
                        list14['count'] = total_posts
                        result.append(list14)
                    # if users_count >= 0:
                    #     list8 = {}
                    #     list8['name'] = "Active Users"
                    #     list8['count'] = users_count
                    #     result.append(list8)

                    if follower_list >= 0:
                        follower_list1 = {}
                        follower_list1['name'] = "Follow me requests"
                        follower_list1['count'] = follower_list
                        result.append(follower_list1)

                    if pending_request_count >= 0:
                        list5 = {}
                        list5["name"] = "Friend Requests"
                        list5["count"] = pending_request_count
                        result.append(list5)
                    if friends_count >= 0:
                        list6 = {}
                        list6['name'] = "Accepted FR"
                        list6['count'] = friends_count
                        result.append(list6)
                    if total_groups >= 0:
                        list18 = {}
                        list18['name'] = "New Groups"
                        list18['count'] = total_groups
                        result.append(list18)
                    if group_accepted_count >= 0:
                        list7 = {}
                        list7['name'] = "Accepted GroupInvites"
                        list7['count'] = group_accepted_count
                        result.append(list7)

                    if new_users_count >= 0:
                        new_users = {}
                        new_users['name'] = "New Users"
                        new_users['count'] = new_users_count
                        result.append(new_users)
                    if individual_user >= 0:
                        list1 = {}
                        list1['name'] = 'Individual Users'
                        list1['count'] = individual_user
                        result.append(list1)
                    if business_users >= 0:
                        list2 = {}
                        list2['name'] = 'Business Users'
                        list2['count'] = business_users
                        result.append(list2)
                    if follow_me_user >= 0:
                        list3 = {}
                        list3['name'] = 'Follow Me Users'
                        list3['count'] = follow_me_user
                        result.append(list3)
                    if india_users_bucket >= 0:
                        lists1 = {}
                        lists1['name'] = "India Bucket"
                        lists1['count'] = india_users_bucket
                        result.append(lists1)
                    if international_users_bucket >= 0:
                        list111 = {}
                        list111['name'] = "International Bucket"
                        list111['count'] = international_users_bucket
                        result.append(list111)

                    if indian_business_users_bucket >= 0:
                        list33 = {}
                        list33['name'] = "Indian biz account"
                        list33['count'] = indian_business_users_bucket
                        result.append(list33)
                    if comments_count >= 0:
                        list9 = {}
                        list9['name'] = "Total Comments"
                        list9['count'] = comments_count
                        result.append(list9)
                    if total_likes >= 0:
                        list13 = {}
                        list13['name'] = 'Total Likes'
                        list13['count'] = total_likes
                        result.append(list13)
                    if betting_accepted_count >= 0:
                        list10 = {}
                        list10['name'] = "Prediction Accept"
                        list10['count'] = betting_accepted_count
                        result.append(list10)
                    if health_records >= 0:
                        hr_list = {}
                        hr_list['name'] = "HR added"
                        hr_list['count'] = health_records
                        result.append(hr_list)
                    if feature_programs >= 0:
                        feature_program_list = {}
                        feature_program_list['name'] = "Fprog added"
                        feature_program_list['count'] = feature_programs
                        result.append(feature_program_list)
                    if contact_me_details >= 0:
                        contact_me_list = {}
                        contact_me_list['name'] = 'Contact me emails'
                        contact_me_list['count'] = contact_me_details
                        result.append(contact_me_list)
                        # feature_programs
                    if reported_post_count >= 0:
                        list11 = {}
                        list11['name'] = "Reported Posts"
                        list11['count'] = reported_post_count
                        result.append(list11)

                    if data["xlsx_required"]:
                        results = []
                        status, file = generate_mis_list(result, from_date, to_date)
                        if status:
                            mis_list = {}
                            mis_list['file'] = file
                            results.append(mis_list)
                            return success('SUCCESS', results, meta={'message': 'file is downloaded'})
                return success('SUCCESS', result, meta={'message': 'user list'})
                    # else:
                #     return success('SUCCESS', meta={'message': 'No data found'})
        else:
            return success('SUCCESS', meta={'No data found'})
    else:
        return success('SUCCESS', meta={'message':'No data found'})



def health_records_count(current_user,data):
    result = []
    data = request.get_json()
    if data.get('date', None):
        from_date = parser.parse(data.get('date'))
        to_date = from_date + datetime.timedelta(hours=12)
        existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
        if existing_user:
            health_report_count = db.session.query(HealthProfile).filter(
                     from_date <= HealthProfile.created_at,
                    to_date > HealthProfile.created_at,HealthProfile.deleted_at==None).distinct(HealthProfile.user_id).count()
            health_records_counts = db.session.query(HealthReport).filter(
                from_date <= HealthReport.created_at,
                to_date > HealthReport.created_at,HealthReport.deleted_at==None).count()
            user_list = {}

            if health_report_count>=0:
                list={}
                list['name'] = "Health Report Users Count"
                list['count'] = health_report_count
                result.append(list)
            if health_records_counts >= 0:
                user_list['name'] = "health Records Count"
                user_list['count'] = health_records_counts
                result.append(user_list)
            return success('SUCCESS', result, meta={'message': 'health records'})



def users_count(current_user):
    exist_user = Users.query.filter_by(id=current_user.id,deleted_at=None,user_deleted_at=None).first()
    if exist_user:
        total_users = """select * from membership where deleted_at is null and role not in 
                        ('user','business')"""
        total_users = _query_execution(total_users)

        active_users = """select * from membership where membership_status='active' and deleted_at is null and role not in 
                            ('user','business')"""
        active_users = _query_execution(active_users)

        inactive_users = """select * from membership where membership_status='inactive' and deleted_at is null and role not in 
                                ('user','business')"""
        inactive_users = _query_execution(inactive_users)

        total_users_count = len(total_users)
        active_users_count = len(active_users)
        inactive_users_count = len(inactive_users)

        data = {}
        data['total_users']=total_users_count
        data['active_users']=active_users_count
        data['inactive_users']=inactive_users_count
        return success('SUCCESS',data, meta={'message': 'Count list'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid user'})


def generate_mis_list(data,from_date,to_date):
    name_uuid = uuid.uuid4()
    file_path = str(name_uuid) +'.xlsx'
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet('Transaction_mis')
    bold_formate=workbook.add_format({'bold':True})
    worksheet.write('C2', 'from_date', bold_formate)
    worksheet.write('C3', 'to_date', bold_formate)
    worksheet.write('D2', str(from_date))
    worksheet.write('D3', str(to_date))
    worksheet.write('A5', 'Activity Post',bold_formate)
    worksheet.write('B5', 'Watch Post',bold_formate)
    worksheet.write('C5', 'Regular Post',bold_formate)
    worksheet.write('D5', 'Record Post',bold_formate)
    worksheet.write('E5', 'Prediction Post',bold_formate)
    worksheet.write('F5', 'Total Posts',bold_formate)
    worksheet.write('G5', 'Follow me requests',bold_formate)
    worksheet.write('H5', 'Friend Requests',bold_formate)
    worksheet.write('I5', 'Accepted FR',bold_formate)
    worksheet.write('J5', 'New Groups',bold_formate)
    worksheet.write('K5', 'Accepted GroupInvites',bold_formate)
    worksheet.write('L5', 'New Users',bold_formate)
    worksheet.write('M5', 'Individual users', bold_formate)
    worksheet.write('N5', 'Business users', bold_formate)
    worksheet.write('O5', 'Follow me users', bold_formate)
    worksheet.write('P5', 'India Bucket',bold_formate)
    worksheet.write('Q5', 'International Bucket',bold_formate)
    worksheet.write('R5', 'Indian biz account',bold_formate)
    worksheet.write('S5', 'HR added',bold_formate)
    worksheet.write('T5', 'Total Comments',bold_formate)
    worksheet.write('U5', 'Total Likes',bold_formate)
    worksheet.write('V5', 'Prediction Accept',bold_formate)
    worksheet.write('W5', 'Fprog added',bold_formate)
    worksheet.write('X5', 'Contact me emails',bold_formate)
    worksheet.write('Y5', 'Reported Posts',bold_formate)
    row = 6
    column = 0
    for item in data:
        if item['name']=="Activity Post":
            worksheet.write(row, column, str(item['count']))
        if item['name'] == "Watch Post":
            worksheet.write(row, column + 1, str(item['count']))
        if item['name'] == "Regular Post":
            worksheet.write(row, column + 2, str(item['count']))
        if item['name'] == "Record Post":
            worksheet.write(row, column + 3, str(item['count']))
        if item['name'] == "Prediction Post":
            worksheet.write(row, column + 4, str(item['count']))
        if item['name'] == "Total Posts":
            worksheet.write(row, column + 5, str(item['count']))
        # if item['name'] == "Active Users":
        #     worksheet.write(row, column + 6, str(item['count']))
        if item['name'] == "Follow me requests":
            worksheet.write(row, column + 6, str(item['count']))
        if item['name'] == "Friend Requests":
            worksheet.write(row, column + 7, str(item['count']))
        if item['name'] == "Accepted FR":
            worksheet.write(row, column + 8, str(item['count']))
        if item['name'] == "New Groups":
            worksheet.write(row, column + 9, str(item['count']))
        if item['name'] == "Accepted GroupInvites":
            worksheet.write(row, column + 10, str(item['count']))
        if item['name'] == "New Users":
            worksheet.write(row, column + 11, str(item['count']))
        if item['name'] == "Individual Users":
            worksheet.write(row, column + 12, str(item['count']))
        if item['name'] == "Business Users":
            worksheet.write(row, column + 13, str(item['count']))
        if item['name'] == "Follow Me Users":
            worksheet.write(row, column + 14, str(item['count']))
        if item['name'] == "India Bucket":
            worksheet.write(row, column + 15, str(item['count']))
        if item['name'] == "International Bucket":
            worksheet.write(row, column + 16, str(item['count']))
        if item['name'] == "Indian biz account":
            worksheet.write(row, column + 17, str(item['count']))
        if item['name'] == "HR added":
            worksheet.write(row, column + 18, str(item['count']))
        if item['name'] == "Total Comments":
            worksheet.write(row, column + 19, str(item['count']))
        if item['name'] == "Total Likes":
            worksheet.write(row, column + 20, str(item['count']))
        if item['name'] == "Prediction Accept":
            worksheet.write(row, column + 21, str(item['count']))
        if item['name'] == "Fprog added":
            worksheet.write(row, column + 22, str(item['count']))
        if item['name'] == "Contact me emails":
            worksheet.write(row, column + 23, str(item['count']))
        if item['name'] == "Reported Posts":
            worksheet.write(row, column + 24, str(item['count']))

    row += 1
    workbook.close()
    # file = open(name)

    client = boto3.client('s3',
                          region_name=AWS_REGION_NAME,
                          aws_access_key_id=AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                          )
    client.upload_file(file_path, AWS_BUCKET_NAME, file_path, ExtraArgs={'ACL': 'public-read'})
    s3_path = f"https://{AWS_BUCKET_NAME}.s3.amazonaws.com/{file_path}"
    workbook.close()
    os.remove(file_path)
    return workbook, s3_path



def health_records_count(current_user,data):
    result = []
    data = request.get_json()
    if data.get('date', None):
        from_date = parser.parse(data.get('date'))
        to_date = from_date + datetime.timedelta(hours=12)
        existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
        if existing_user:
            health_report_count = db.session.query(HealthProfile).filter(
                     from_date <= HealthProfile.created_at,
                    to_date > HealthProfile.created_at,HealthProfile.deleted_at==None).count()
            health_records_counts = db.session.query(HealthReport).filter(
                from_date <= HealthReport.created_at,
                to_date > HealthReport.created_at,HealthReport.deleted_at==None).count()
            user_list = {}

            if health_report_count>=0:
                list={}
                list['name'] = "Number Of Users"
                list['count'] = health_report_count
                result.append(list)
            if health_records_counts >= 0:
                user_list['name'] = "Number Of Records"
                user_list['count'] = health_records_counts
                result.append(user_list)
            if data["xlsx_required"]:
                results = []
                status, file = generate_mis_health_records(result)
                if status:
                    mis_list = {}
                    mis_list['file'] = file
                    results.append(mis_list)
                    return success('SUCCESS',results ,meta={'message': 'file is downloaded'})
            return success('SUCCESS', result, meta={'message': 'health records'})


def generate_mis_health_records(data):
    name_uuid = uuid.uuid4()
    file_path = str(name_uuid) + '.xlsx'
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet('mis_list')
    bold_formate=workbook.add_format({'bold':True})
    worksheet.write('A1', 'Number Of Users',bold_formate)
    worksheet.write('B1', 'Number Of Records',bold_formate)
    row = 1
    column = 0
    for item in data:
        if item['name']=='Number Of Users':
            worksheet.write(row, column, str(item['count']))
        if item['name'] == 'Number Of Records':
            worksheet.write(row, column + 1, str(item['count']))
    row += 1
    workbook.close()
    client = boto3.client('s3',
                          region_name=AWS_REGION_NAME,
                          aws_access_key_id=AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                          )
    client.upload_file(file_path, AWS_BUCKET_NAME, file_path, ExtraArgs={'ACL': 'public-read'})
    s3_path = f"https://{AWS_BUCKET_NAME}.s3.amazonaws.com/{file_path}"
    workbook.close()
    os.remove(file_path)
    return workbook, s3_path


def list_of_bucket(current_user,data):
    india_users_bucket=Users.query.filter_by(phone_code='91',deleted_at=None,user_deleted_at=None).count()
    indian_business_users_bucket=Users.query.filter_by(phone_code=91,
                                               deleted_at=None,user_deleted_at=None).filter(
            or_(Users.business_account == True, Users.can_follows == True)).count()
    result=[]
    international_users_bucket = db.session.query(Users).filter(Users.deleted_at ==None,
                                                          Users.user_deleted_at==None,
                                                          Users.phone_code != 91,
                                                         ).count()
    international_business_bucket =db.session.query(Users).filter(Users.deleted_at ==None,
                                                          Users.user_deleted_at==None,
                                                          Users.phone_code != 91,
                                                         ).filter(
            or_(Users.business_account == True, Users.can_follows == True)).count()

    if india_users_bucket>=0:
        list={}
        list['name']="India Users Bucket"
        list['count']= india_users_bucket
        result.append(list)
    if international_users_bucket>=0:
        list1={}
        list1['name']="International Users Bucket"
        list1['count']= international_users_bucket
        result.append(list1)

    if indian_business_users_bucket >=0:
        list3 = {}
        list3['name'] = "Indian Business Users Bucket"
        list3['count'] = indian_business_users_bucket
        result.append(list3)
    if international_business_bucket >=0:
        list4 = {}
        list4['name'] = "International Business Bucket"
        list4['count'] = international_business_bucket
        result.append(list4)
        if data["xlsx_required"]:
            results = []
            status, file = generate_bucket_xlsx(result)
            if status:
                mis_list = {}
                mis_list['file'] = file
                results.append(mis_list)
            return success('SUCCESS', results,meta={'message': 'file is downloaded'})
    return success('SUCCESS',result,meta={'message':'Users bucket list'})


def generate_bucket_xlsx(data):
    name_uuid = uuid.uuid4()
    file_path = str(name_uuid) + '.xlsx'
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet('mis_bucket_list')
    bold_formate = workbook.add_format({'bold': True})
    worksheet.write('A1', 'India Users Bucket', bold_formate)
    worksheet.write('B1', 'International Users Bucket', bold_formate)
    worksheet.write('C1', 'Indian Business Users Bucket', bold_formate)
    worksheet.write('D1', 'International Business Bucket', bold_formate)
    row = 1
    column = 0
    for item in data:
        if item['name'] == 'India Users Bucket':
            worksheet.write(row, column, str(item['count']))
        if item['name'] == 'International Users Bucket':
            worksheet.write(row, column + 1, str(item['count']))
        if item['name'] == 'Indian Business Users Bucket':
            worksheet.write(row, column + 2, str(item['count']))
        if item['name'] == 'International Business Bucket':
            worksheet.write(row, column + 3, str(item['count']))
    row += 1
    workbook.close()
    client = boto3.client('s3',
                          region_name=AWS_REGION_NAME,
                          aws_access_key_id=AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                          )
    client.upload_file(file_path, AWS_BUCKET_NAME, file_path, ExtraArgs={'ACL': 'public-read'})
    s3_path = f"https://{AWS_BUCKET_NAME}.s3.amazonaws.com/{file_path}"
    workbook.close()
    os.remove(file_path)
    return workbook, s3_path


def get_fitness_level_list(user_id):
    f_level = Fitness_level.query.filter_by(user_id=user_id, deleted_at=None).all()
    if f_level:
        result = []
        for levels in f_level:
            course = Master_course.query.filter_by(id=levels.course_id).first()
            if course:
                fitness_level = course.level
                for level in fitness_level:
                    if int(levels.seconds) < level['lt'] and int(levels.seconds) > level['gt']:
                        fit_level = {}
                        fit_level['fitness_level'] = level['level']
                        result.append(fit_level)
        fitness_levels = []
        for res in result:
            if res['fitness_level'] not in fitness_levels:
                fitness_levels.append(res['fitness_level'])
        if 'supreme' in fitness_levels:
            return 'supreme'
        elif 'strong' in fitness_levels:
            return 'strong'
        else:
            return 'fit'

    else:
        return ""



def users_summary():
    result=[]
    data = request.get_json()
    from_date = data.get('from_date')
    to_date = data.get('to_date')
    if from_date and to_date:
        user_list =  db.session.query(Users).filter(and_(func.date(Users.created_at) >= from_date),
                                                       func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                        Users.user_deleted_at==None).order_by(Users.created_at.desc()).all()
        if user_list:
            for user_data in user_list:
                member_ship=Membership.query.filter_by(user_id=user_data.id,membership_type='general',membership_status='active',deleted_at=None).all()
                if member_ship:
                    for data in member_ship:
                        friends_count = Contact.query.filter_by(user_id=data.user_id,friend_status='friends',deleted_at=None).count()
                        hall_of_fame_list=Hall_of_fame.query.filter_by(user_id=data.user_id,deleted_at=None).count()
                        primary_sport_list=Sport_level.query.filter_by(user_id=data.user_id,is_primary=True,deleted_at=None,primary_deleted_at=None).count()
                        secondry_sport_list=Sport_level.query.filter_by(user_id=data.user_id,is_primary=False,deleted_at=None,secondary_deleted_at=None).count()
                        sport_level = Sport_level.query.filter_by(user_id=data.user_id,
                                                                          deleted_at=None,
                                                                          secondary_deleted_at=None,primary_deleted_at=None).first()

                        fitness_level_list=get_fitness_level_list(data.user_id)
                        experties_list=Experties_background.query.filter_by(user_id=data.user_id,deleted_at=None).count()
                        program_list=Programme.query.filter_by(user_id=data.id,deleted_at=None).count()
                        group_list=db.session.query(GroupMembers).filter(GroupMembers.user_id==data.user_id,GroupMembers.status=='active',
                                    GroupMembers.deleted_at ==None).filter(
                        or_(GroupMembers.type == 'user', GroupMembers.type == 'admin')).count()
                        followers =Contact.query.filter_by(contact_id=data.user_id, is_following=True,following_status='following',
                                                                          deleted_at=None).count()
                        following = Contact.query.filter_by(user_id=data.user_id, following_status='following',is_following=True,
                                                                          deleted_at=None).count()
                        regulur_posts=Post.query.filter_by(user_id=data.user_id,type = 'regular',deleted_at=None).count()
                        activity_posts=Post.query.filter_by(user_id=data.user_id,type = 'activity',deleted_at=None).count()
                        betting_posts=Post.query.filter_by(user_id=data.user_id,type = 'watch_activity',deleted_at=None).count()
                        watch_posts=Post.query.filter_by(user_id=data.user_id,type = 'betting',deleted_at=None).count()
                        record_activity_posts=Post.query.filter_by(user_id=data.user_id,type = 'record_activity',deleted_at=None).count()
                        user_data=Users.query.filter_by(id=data.user_id,deleted_at=None,user_deleted_at=None).first()

                        gifit_usesrs_list=  """SELECT * FROM gfitusers WHERE gfitusers.deleted_at IS  NULL AND gfitusers.user_id='{user_id}' 
                        """.format(user_id=data.user_id)

                        gifit_usesrs = _query_execution(gifit_usesrs_list)
                        # gifit_usesrs = GfitUsers.query.filter_by(user_id=data.user_id,deleted_at=None).all()
                        garmin_fit_list="""SELECT * FROM garminusers WHERE garminusers.deleted_at IS  NULL AND garminusers.user_id='{user_id}' 
                        """.format(user_id=str(data.user_id))
                        garmin_fit = _query_execution(garmin_fit_list)
                        # garmin_fit = GarminUsers.query.filter_by(user_id=str(data.user_id),deleted_at=None).all()
                        if user_data:
                            list = {}
                            list['Date of Account creation'] = user_data.created_at
                            list['User_id'] = user_data.id
                            list['Name'] = user_data.first_name
                            list['Email'] = user_data.email
                            list['Country Code'] = user_data.phone_code
                            list['Mobile Nos'] = user_data.phone
                            list['Year of birth'] = user_data.date_of_birth
                            list['Gender'] = user_data.gender
                            list['City'] = user_data.city
                            list['Martial status'] = user_data.marital_status
                            list['Highest qualification'] = user_data.education_qualification
                            list['College name'] = user_data.college_name
                            list['Work place'] = user_data.work_place
                            list['Business Account'] = user_data.business_account
                            if friends_count >= 0:
                                list['Friends'] = friends_count
                            if hall_of_fame_list >= 0:
                                list['Hall Of Fame'] = hall_of_fame_list
                            if primary_sport_list >= 0:
                                list['Primary Sport'] = primary_sport_list
                            if secondry_sport_list >= 0:
                                list['Secondry Sport'] = secondry_sport_list
                            if sport_level:
                                list['Sport Level'] = sport_level.playing_level
                            else:
                                list['Sport Level'] = "None"
                            if fitness_level_list:
                                list['Fitness Level'] = fitness_level_list
                            else:
                                list['Fitness Level'] = ""
                            if experties_list >= 0:
                                list['Experties Background'] = experties_list
                            if program_list >= 0:
                                list['Feature Programs'] = program_list
                            if group_list >= 0:
                                list['Groups'] = group_list
                            if followers >= 0:
                                list['Followers'] = followers
                            if regulur_posts >= 0:
                                list['Regular Post'] = regulur_posts
                            if activity_posts >= 0:
                                list['Activity Post'] = activity_posts
                            if betting_posts >= 0:
                                list['Prediction Post'] = betting_posts
                            if watch_posts >= 0:
                                list['Watch Post'] = watch_posts
                            if record_activity_posts >= 0:
                                list['Record Post'] = record_activity_posts
                            if following >= 0:
                                list['Following'] = following
                            if gifit_usesrs:
                                list['Watch Linked'] = "Google Fit"
                            elif garmin_fit:
                                list['Watch Linked'] = "Garmin fit"
                            elif gifit_usesrs and gifit_usesrs:
                                list['Watch Linked'] = "Google Fit/Garmin fit"
                            else:
                                list['Watch Linked'] = ""
                            result.append(list)
            status,file = generate_excel(result,from_date,to_date)
            lists=[]
            if status:
                user_list = {}
                user_list['file'] = file
                lists.append(user_list)
            return success('SUCCESS',lists,meta={'message':'file is downloaded'})
        else:
            return success('SUCCESS', meta={'message':'No data found'})
    elif to_date and not from_date:
        user_list = db.session.query(Users).filter(and_(func.date(Users.created_at) >= '0001-01-01'),
                                                   func.date(Users.created_at) <= to_date).filter(
            Users.deleted_at == None,
            Users.user_deleted_at == None).order_by(Users.created_at.desc()).all()
        if user_list:
            for user_data in user_list:
                member_ship = Membership.query.filter_by(user_id=user_data.id, membership_type='general',
                                                         membership_status='active', deleted_at=None).all()
                if member_ship:
                    for data in member_ship:
                        friends_count = Contact.query.filter_by(user_id=data.user_id, friend_status='friends',
                                                                deleted_at=None).count()
                        hall_of_fame_list = Hall_of_fame.query.filter_by(user_id=data.user_id,
                                                                         deleted_at=None).count()
                        primary_sport_list = Sport_level.query.filter_by(user_id=data.user_id, is_primary=True,
                                                                         deleted_at=None,
                                                                         primary_deleted_at=None).count()
                        secondry_sport_list = Sport_level.query.filter_by(user_id=data.user_id, is_primary=False,
                                                                          deleted_at=None,
                                                                          secondary_deleted_at=None).count()
                        sport_level = Sport_level.query.filter_by(user_id=data.user_id,
                                                                  deleted_at=None,
                                                                  secondary_deleted_at=None,
                                                                  primary_deleted_at=None).first()

                        fitness_level_list = get_fitness_level_list(data.user_id)
                        experties_list = Experties_background.query.filter_by(user_id=data.user_id,
                                                                              deleted_at=None).count()
                        program_list = Programme.query.filter_by(user_id=data.id, deleted_at=None).count()
                        group_list = db.session.query(GroupMembers).filter(GroupMembers.user_id == data.user_id,
                                                                           GroupMembers.status == 'active',
                                                                           GroupMembers.deleted_at == None).filter(
                            or_(GroupMembers.type == 'user', GroupMembers.type == 'admin')).count()
                        followers = Contact.query.filter_by(contact_id=data.user_id, is_following=True,
                                                            following_status='following',
                                                            deleted_at=None).count()
                        following = Contact.query.filter_by(user_id=data.user_id, following_status='following',
                                                            is_following=True,
                                                            deleted_at=None).count()
                        regulur_posts = Post.query.filter_by(user_id=data.user_id, type='regular',
                                                             deleted_at=None).count()
                        activity_posts = Post.query.filter_by(user_id=data.user_id, type='activity',
                                                              deleted_at=None).count()
                        betting_posts = Post.query.filter_by(user_id=data.user_id, type='watch_activity',
                                                             deleted_at=None).count()
                        watch_posts = Post.query.filter_by(user_id=data.user_id, type='betting',
                                                           deleted_at=None).count()
                        record_activity_posts = Post.query.filter_by(user_id=data.user_id, type='record_activity',
                                                                     deleted_at=None).count()
                        user_data = Users.query.filter_by(id=data.user_id, deleted_at=None,
                                                          user_deleted_at=None).first()

                        gifit_usesrs_list = """SELECT * FROM gfitusers WHERE gfitusers.deleted_at IS  NULL AND gfitusers.user_id='{user_id}' 
                        """.format(user_id=data.user_id)

                        gifit_usesrs = _query_execution(gifit_usesrs_list)
                        # gifit_usesrs = GfitUsers.query.filter_by(user_id=data.user_id,deleted_at=None).all()
                        garmin_fit_list = """SELECT * FROM garminusers WHERE garminusers.deleted_at IS  NULL AND garminusers.user_id='{user_id}' 
                        """.format(user_id=str(data.user_id))
                        garmin_fit = _query_execution(garmin_fit_list)
                        # garmin_fit = GarminUsers.query.filter_by(user_id=str(data.user_id),deleted_at=None).all()
                        if user_data:
                            list = {}
                            list['Date of Account creation'] = user_data.created_at
                            list['User_id'] = user_data.id
                            list['Name'] = user_data.first_name
                            list['Email'] = user_data.email
                            list['Country Code'] = user_data.phone_code
                            list['Mobile Nos'] = user_data.phone
                            list['Year of birth'] = user_data.date_of_birth
                            list['Gender'] = user_data.gender
                            list['City'] = user_data.city
                            list['Martial status'] = user_data.marital_status
                            list['Highest qualification'] = user_data.education_qualification
                            list['College name'] = user_data.college_name
                            list['Work place'] = user_data.work_place
                            list['Business Account'] = user_data.business_account
                            if friends_count >= 0:
                                list['Friends'] = friends_count
                            if hall_of_fame_list >= 0:
                                list['Hall Of Fame'] = hall_of_fame_list
                            if primary_sport_list >= 0:
                                list['Primary Sport'] = primary_sport_list
                            if secondry_sport_list >= 0:
                                list['Secondry Sport'] = secondry_sport_list
                            if sport_level:
                                list['Sport Level'] = sport_level.playing_level
                            else:
                                list['Sport Level'] = "None"
                            if fitness_level_list:
                                list['Fitness Level'] = fitness_level_list
                            else:
                                list['Fitness Level'] = ""
                            if experties_list >= 0:
                                list['Experties Background'] = experties_list
                            if program_list >= 0:
                                list['Feature Programs'] = program_list
                            if group_list >= 0:
                                list['Groups'] = group_list
                            if followers >= 0:
                                list['Followers'] = followers
                            if regulur_posts >= 0:
                                list['Regular Post'] = regulur_posts
                            if activity_posts >= 0:
                                list['Activity Post'] = activity_posts
                            if betting_posts >= 0:
                                list['Prediction Post'] = betting_posts
                            if watch_posts >= 0:
                                list['Watch Post'] = watch_posts
                            if record_activity_posts >= 0:
                                list['Record Post'] = record_activity_posts
                            if following >= 0:
                                list['Following'] = following
                            if gifit_usesrs:
                                list['Watch Linked'] = "Google Fit"
                            elif garmin_fit:
                                list['Watch Linked'] = "Garmin fit"
                            elif gifit_usesrs and gifit_usesrs:
                                list['Watch Linked'] = "Google Fit/Garmin fit"
                            else:
                                list['Watch Linked'] = ""
                            result.append(list)
            status, file = generate_excel(result, from_date, to_date)
            lists = []
            if status:
                user_list = {}
                user_list['file'] = file
                lists.append(user_list)
            return success('SUCCESS', lists, meta={'message': 'file is downloaded'})
        else:
            return success('SUCCESS', meta={'message':'No data found'})
    else:
        return success('SUCCESS', meta={'message':'No data found'})



def generate_excel(data,from_date,to_date):
    name_uuid = uuid.uuid4()
    file_path = str(name_uuid) + '.xlsx'
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet('users_profile_summary')
    bold_formate=workbook.add_format({'bold':True})

    worksheet.write('C2', 'from_date', bold_formate)
    worksheet.write('C3', 'to_date', bold_formate)
    worksheet.write('D2', str(from_date))
    worksheet.write('D3', str(to_date))
    worksheet.write('A6', 'User_id', bold_formate)
    worksheet.write('B6', 'Date of Account creation',bold_formate)
    # worksheet.write('C4', 'Accessed in last 3 months',bold_formate)
    worksheet.write('C6', 'Name', bold_formate)
    worksheet.write('D6', 'Email', bold_formate)
    worksheet.write('E6', 'Country Code',bold_formate)
    worksheet.write('F6', 'Mobile Nos',bold_formate)
    worksheet.write('G6', 'Friends',bold_formate)
    worksheet.write('H6', 'Hall Of Fame',bold_formate)
    worksheet.write('I6', 'Primary Sport',bold_formate)
    worksheet.write('J6', 'Secondry Sport',bold_formate)
    worksheet.write('K6', 'Sport Level',bold_formate)
    worksheet.write('L6', 'Fitness Level',bold_formate)
    worksheet.write('M6', 'Watch Linked',bold_formate)
    worksheet.write('N6', 'Experties Background',bold_formate)
    worksheet.write('O6', 'Feature Programs',bold_formate)
    worksheet.write('P6', 'Groups',bold_formate)
    worksheet.write('Q6', 'Followers',bold_formate)
    worksheet.write('R6', 'Following',bold_formate)
    worksheet.write('S6', 'Regular Post',bold_formate)
    worksheet.write('T6', 'Activity Posts',bold_formate)
    worksheet.write('U6', 'Prediction Post',bold_formate)
    worksheet.write('V6', 'Watch Post',bold_formate)
    worksheet.write('W6', 'Record Post',bold_formate)
    worksheet.write('X6', 'Business Account',bold_formate)
    worksheet.write('Y6', 'Year of birth',bold_formate)
    worksheet.write('Z6', 'Gender',bold_formate)
    worksheet.write('AA6', 'City',bold_formate)
    worksheet.write('AB6', 'Martial status',bold_formate)
    worksheet.write('AC6', 'Highest qualification',bold_formate)
    worksheet.write('AD6', 'College name',bold_formate)
    worksheet.write('AE6', 'Work place',bold_formate)
    row = 7
    column = 0
    for item in data:
        worksheet.write(row, column, str(item['User_id']))
        worksheet.write(row, column + 1, str(item['Date of Account creation']))
        # worksheet.write(row, column + 2, str(item['Accessed in last 3 months']))
        worksheet.write(row, column + 2, str(item['Name']))
        worksheet.write(row, column + 3, str(item['Email']))
        worksheet.write(row, column + 4, str(item['Country Code']))
        worksheet.write(row, column + 5, str(item['Mobile Nos']))
        worksheet.write(row, column + 6, str(item['Friends']))
        worksheet.write(row, column + 7, str(item['Hall Of Fame']))
        worksheet.write(row, column + 8, str(item['Primary Sport']))
        worksheet.write(row, column + 9, str(item['Secondry Sport']))
        worksheet.write(row, column + 10, str(item['Sport Level']))
        worksheet.write(row, column + 11, str(item['Fitness Level']))
        worksheet.write(row, column + 12, str(item['Watch Linked']))
        worksheet.write(row, column + 13, str(item['Experties Background']))
        worksheet.write(row, column + 14, str(item['Feature Programs']))
        worksheet.write(row, column + 15, str(item['Groups']))
        worksheet.write(row, column + 16, str(item['Followers']))
        worksheet.write(row, column + 17, str(item['Following']))
        worksheet.write(row, column + 18, str(item['Regular Post']))
        worksheet.write(row, column + 19, str(item['Activity Post']))
        worksheet.write(row, column + 20, str(item['Prediction Post']))
        worksheet.write(row, column + 21, str(item['Watch Post']))
        worksheet.write(row, column + 22, str(item['Record Post']))
        worksheet.write(row, column + 23, str(item['Business Account']))
        worksheet.write(row, column + 24, str(item['Year of birth']))
        # worksheet.write(row, column + 25, str(item['Business Account']))
        worksheet.write(row, column + 25, str(item['Gender']))
        worksheet.write(row, column + 26, str(item['City']))
        worksheet.write(row, column + 27, str(item['Martial status']))
        worksheet.write(row, column + 28, str(item['Highest qualification']))
        worksheet.write(row, column + 29, str(item['College name']))
        worksheet.write(row, column + 30, str(item['Work place']))
        row += 1
    workbook.close()
    client = boto3.client('s3',
                          region_name=AWS_REGION_NAME,
                          aws_access_key_id=AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                          )
    client.upload_file(file_path,AWS_BUCKET_NAME,file_path,ExtraArgs={'ACL': 'public-read'})
    s3_path = f"https://{AWS_BUCKET_NAME}.s3.amazonaws.com/{file_path}"
    workbook.close()
    os.remove(file_path)
    return workbook, s3_path



def reported_post_list(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    result=[]
    reported_posts = ReportedPost.query.filter_by(deleted_at=None).all()
    reported_posts_list = ReportedPost.query.filter_by(deleted_at=None).order_by(ReportedPost.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    reported_posts_list = reported_posts_list.items
    total_record = len(reported_posts)
    total_pages = total_record // per_page + 1

    if reported_posts_list:
        for data in reported_posts_list:
            reported_post_count = ReportedPost.query.filter_by(post_id=data.post_id, deleted_at=None).count()
            post_data = Post.query.filter_by(id=data.post_id,deleted_at=None,status='active').first()
            if post_data:
                user_data = Users.query.filter_by(id=post_data.user_id, deleted_at=None,user_deleted_at=None).first()
                user_info = get_user_profile_details(user_data.id)
                list={}
                list['id'] = data.post_id
                list['report_id'] = data.id
                list['type'] = post_data.type
                list['title'] = post_data.title
                list['visibility'] = post_data.visibility
                list['user_info'] = user_info
                list['group_id'] = post_data.group_id
                list['meta_data'] = post_data.meta_data
                list['location'] = post_data.location
                list['description'] = post_data.description
                list['created_at'] = post_data.created_at
                list['status'] = post_data.status
                if reported_post_count >=0:
                    list['count'] = reported_post_count
                result.append(list)

        return success("SUCCESS", result, meta={'message': 'Reported Post List',
                                                'page_info': {'current_page': page,
                                                              'total_pages': total_pages,
                                                              'total_record': total_record,
                                                              'limit': per_page}}
                       )
    else:
        return success('SUCCESS',meta={'message':'Empty Data'})


def approved_post_list_v2(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)

    count_data = """SELECT count(distinct admin_post.post_id) FROM admin_post JOIN Post ON admin_post.post_id = post.id JOIN 
    users ON post.user_id  = users.id JOIN post_bucket_mapping ON post.id  = post_bucket_mapping.post_id where 
    admin_post.deleted_at is null and admin_post.promotion is null and admin_post.reviewer_status is true and 
    admin_post.publisher_status is null and users.deleted_at is null and users.user_deleted_at is null and post.deleted_at is null and 
    post.status='active' and post.deleted_at is null and post_bucket_mapping.deleted_at is null; """

    count = _query_execution(count_data)

    approved_post = AdminPost.query.filter_by(promotion=None, reviewer_status=True, deleted_at=None,
                                              publisher_status=None).order_by(
        AdminPost.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    result = []
    approved_posts = approved_post.items

    if count:
        total_records = count[0]['count']
    else:
        total_records = 0
    total_pages = total_records // per_page + 1
    if approved_posts:
        for post in approved_posts:
            details = Post.query.filter_by(id=post.post_id, deleted_at=None, status='active').all()
            for detail in details:
                user_data = Users.query.filter_by(id=detail.user_id, deleted_at=None, user_deleted_at=None).first()
                post_list = AdminPost.query.filter_by(post_id=detail.id, deleted_at=None).first()
                bucket_data = PostBucketMapping.query.filter_by(post_id=detail.id, deleted_at=None).all()
                if user_data and post_list and bucket_data:
                    user_info = get_user_profile_details(user_data.id)
                    details = {}
                    details['id'] = detail.id
                    details['location'] = detail.location
                    details['title'] = detail.title
                    details['description'] = detail.description
                    details['created_at'] = detail.created_at
                    details['visibility'] = detail.visibility
                    details['type'] = detail.type
                    details['meta_data'] = detail.meta_data
                    details['expire_on'] = detail.expire_on
                    details['user_info'] = user_info
                    details['expiry_date'] = post_list.expiry_date
                    details['is_priority'] = post_list.is_priority
                    buckets = []
                    for bucket in bucket_data:
                        buckets.append(bucket.key)
                    details['bucket_name'] = buckets
                    result.append(details)
        return success('SUCCESS', result, meta={'message': 'approved posts',
                                                'page_info': {'current_page': page,
                                                              'limit': per_page,
                                                              'total_records': total_records,
                                                              'total_pages': total_pages}
                                                })
    else:
        return success('SUCCESS', meta={'message': 'No posts'})


def publisher_views_discarded_posts_v2(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)

    count_data = """SELECT count(distinct admin_post.post_id) FROM admin_post JOIN Post ON admin_post.post_id = post.id JOIN 
        users ON post.user_id  = users.id where 
        admin_post.deleted_at is null and admin_post.promotion is null and admin_post.reviewer_status is false and 
        admin_post.publisher_status is null and users.deleted_at is null and users.user_deleted_at is null and post.deleted_at is null and 
        post.status='active' and post.deleted_at is null ; """

    count = _query_execution(count_data)
    discarded_post = AdminPost.query.filter_by(promotion=None, reviewer_status=False, deleted_at=None,
                                               publisher_status=None).order_by(
        AdminPost.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    result = []
    discarded_posts = discarded_post.items
    if count:
        total_record = count[0]['count']
    else:
        total_record = 0
    total_pages = total_record // per_page + 1
    if discarded_posts:
        for post in discarded_posts:
            post_exist = Post.query.filter_by(id=post.post_id, deleted_at=None, status='active').first()
            if post_exist:
                user_data = Users.query.filter_by(id=post_exist.user_id, deleted_at=None, user_deleted_at=None).first()
                post_list = AdminPost.query.filter_by(post_id=post_exist.id, deleted_at=None).first()
                if user_data and post_list:
                    user_info = get_user_profile_details(user_data.id)
                    details = {}
                    details['id'] = post_exist.id
                    details['location'] = post_exist.location
                    details['title'] = post_exist.title
                    details['description'] = post_exist.description
                    details['created_at'] = post_exist.created_at
                    details['visibility'] = post_exist.visibility
                    details['type'] = post_exist.type
                    details['meta_data'] = post_exist.meta_data
                    details['expire_on'] = post_exist.expire_on
                    details['expiry_date'] = post_list.expiry_date
                    details['is_priority'] = post_list.is_priority
                    details['user_info'] = user_info
                    result.append(details)
        return success('SUCCESS', result, meta={'message': 'discarded posts',
                                                'page_info': {'current_page': page,
                                                              'limit': per_page,
                                                              'total_records': total_record,
                                                              'total_pages': total_pages}
                                                })
    else:
        return success('SUCCESS', meta={'message': 'No posts'})


def get_admin_post_list_v2():
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    membership = Membership.query.filter_by(membership_status='active', membership_type='admin', deleted_at=None).filter(
        or_(Membership.role == 'content_creator', Membership.role == 'super_admin')).all()
    result = []
    content_creator = []
    if membership:
        for data in membership:
            content_creator.append(data.user_id)
    if content_creator:
        count = Post.query.filter(Post.user_id.in_(content_creator), Post.deleted_at == None).count()
        post_list = Post.query.filter(Post.user_id.in_(content_creator), Post.deleted_at == None).order_by(
            Post.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        post_list = post_list.items
        if count:
            total_record = count
        else:
            total_record = 0
        total_pages = total_record // per_page + 1
        if post_list:
            for list in post_list:
                user_data = Users.query.filter_by(id=list.user_id, deleted_at=None, user_deleted_at=None).first()
                bucket_data = PostBucketMapping.query.filter_by(post_id=list.id, deleted_at=None).all()
                if user_data:
                    user_info = get_user_profile_details(list.user_id)
                    details = {}
                    details['id'] = list.id
                    details['location'] = list.location
                    details['title'] = list.title
                    details['description'] = list.description
                    details['created_at'] = list.created_at
                    details['visibility'] = list.visibility
                    details['type'] = list.type
                    details['meta_data'] = list.meta_data
                    details['expire_on'] = list.expire_on
                    details['user_info'] = user_info
                    # details['expiry_date'] = post_data.expiry_date
                    # details['is_priority'] = post_data.is_priority
                    if bucket_data:
                        buckets = []
                        for bucket in bucket_data:
                            if bucket.key:
                                buckets.append(bucket.key)
                            if buckets:
                                details['bucket_name'] = buckets
                    result.append(details)
            return success('SUCCESS', result, meta={'message': 'Admin Post List',
                                                    'page_info': {'current_page': page,
                                                                  'total_pages': total_pages,
                                                                  'total_records': total_record}})
        else:
            return success('SUCCESS', meta={'message': 'No Admin Content'})
    else:
        return success('SUCCESS', meta={'message': 'No Admin Content'})


def approved_promotion_posts_v2(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)

    count_data = """SELECT count(distinct admin_post.post_id) FROM admin_post JOIN Post ON admin_post.post_id = post.id JOIN 
        users ON post.user_id  = users.id JOIN post_bucket_mapping ON post.id  = post_bucket_mapping.post_id where 
        admin_post.deleted_at is null and admin_post.promotion='promotion_post' and admin_post.reviewer_status is true and 
        admin_post.publisher_status is null and users.deleted_at is null and users.user_deleted_at is null and post.deleted_at is null and 
        post.status='active' and post_bucket_mapping.deleted_at is null; """
    count = _query_execution(count_data)

    approved_post = AdminPost.query.filter_by(promotion='promotion_post', reviewer_status=True, deleted_at=None,
                                              publisher_status=None).order_by(
        AdminPost.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    result = []
    approved_posts = approved_post.items
    if count:
        total_record = count[0]['count']
    else:
        total_record = 0
    total_pages = total_record // per_page + 1
    if approved_posts:
        for post in approved_posts:
            details = Post.query.filter_by(id=post.post_id, deleted_at=None, status='active').all()
            for detail in details:
                user_data = Users.query.filter_by(id=detail.user_id, user_deleted_at=None, deleted_at=None).first()
                post_list = AdminPost.query.filter_by(post_id=detail.id, deleted_at=None).first()
                bucket_data = PostBucketMapping.query.filter_by(post_id=detail.id, deleted_at=None).all()
                if user_data and post_list and bucket_data:
                    user_info = get_user_profile_details(user_data.id)
                    details = {}
                    details['id'] = detail.id
                    details['location'] = detail.location
                    details['title'] = detail.title
                    details['description'] = detail.description
                    details['created_at'] = detail.created_at
                    details['visibility'] = detail.visibility
                    details['type'] = detail.type
                    details['meta_data'] = detail.meta_data
                    details['expire_on'] = detail.expire_on
                    details['user_info'] = user_info
                    details['expiry_date'] = post_list.expiry_date
                    details['is_priority'] = post_list.is_priority
                    buckets = []
                    for bucket in bucket_data:
                        buckets.append(bucket.key)
                    details['bucket_name'] = buckets
                    result.append(details)
        return success('SUCCESS', result, meta={'message': 'approved promotion posts',
                                                'page_info': {'current_page': page,
                                                              'limit': per_page,
                                                              'total_records': total_record,
                                                              'total_pages': total_pages}
                                                })
    else:
        return success('SUCCESS', meta={'message': 'No posts'})


def discarded_promotion_posts_v2(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    approved_posts_count = AdminPost.query.filter_by(promotion='promotion_post', reviewer_status=False, deleted_at=None,
                                                     publisher_status=None).all()

    count_data = """SELECT count(distinct admin_post.post_id) FROM admin_post JOIN Post ON admin_post.post_id = post.id JOIN 
            users ON post.user_id  = users.id where 
            admin_post.deleted_at is null and admin_post.promotion='promotion_post' and admin_post.reviewer_status is false and 
            admin_post.publisher_status is null and users.deleted_at is null and users.user_deleted_at is null and  
            post.status='active' and post.deleted_at is null ; """
    count = _query_execution(count_data)

    approved_post = AdminPost.query.filter_by(promotion='promotion_post', reviewer_status=False, deleted_at=None,
                                              publisher_status=None).order_by(
        AdminPost.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    result = []
    approved_posts = approved_post.items
    total_record = len(approved_posts_count)
    total_pages = total_record // per_page + 1
    if approved_posts:
        for post in approved_posts:
            details = Post.query.filter_by(id=post.post_id, deleted_at=None, status='active').all()
            for detail in details:
                user_data = Users.query.filter_by(id=detail.user_id, deleted_at=None,user_deleted_at=None).first()
                post_list = AdminPost.query.filter_by(post_id=detail.id, deleted_at=None).first()
                if user_data and post_list:
                    user_info = get_user_profile_details(user_data.id)
                    details = {}
                    details['id'] = detail.id
                    details['location'] = detail.location
                    details['title'] = detail.title
                    details['description'] = detail.description
                    details['created_at'] = detail.created_at
                    details['visibility'] = detail.visibility
                    details['type'] = detail.type
                    details['meta_data'] = detail.meta_data
                    details['expire_on'] = detail.expire_on
                    details['user_info'] = user_info
                    details['expiry_date'] = post_list.expiry_date
                    details['is_priority'] = post_list.is_priority

                    result.append(details)
        return success('SUCCESS', result, meta={'message': 'discarded promotion posts',
                                                'page_info': {'current_page': page,
                                                              'limit': per_page,
                                                              'total_records': total_record,
                                                              'total_pages': total_pages}
                                                })
    else:
        return success('SUCCESS', meta={'message': 'No posts'})


def cms_user_details_update(current_user, user_id,data):
    password = data.get('password', None)
    role = data.get('role', None)
    if password and role:
        users = Users.query.filter_by(id=user_id, deleted_at=None,
                                                     user_deleted_at=None).first()
        if users:
            memebership=Membership.query.filter_by(user_id=user_id,membership_type='admin',deleted_at=None).first()
            if memebership:
                password = bcrypt.generate_password_hash(password).decode('utf-8')
                users.password = password
                memebership.role = role
                memebership.password = password
                memebership.password_update_on = datetime.datetime.now()
                update_item(memebership)
                update_item(users)
                return success("SUCCESS", meta={'message': 'Details are updated successfully'})
            else:
                return success('SUCCESS', meta={'message': 'Invalid membership type'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid user details'})


def final_post_list_v2(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    exist_user = Users.query.filter_by(id=current_user.id, deleted_at=None, user_deleted_at=None).first()
    if exist_user:
        category = ['broadcast', 'international_broadcast', 'india_broadcast', 'business_broadcast',
                    'email_broadcast']
        count_data = """SELECT count(*) FROM admin_post JOIN Post ON admin_post.post_id = 
        post.id JOIN users ON post.user_id  = users.id JOIN post_bucket_mapping ON post.id  = 
        post_bucket_mapping.post_id where admin_post.deleted_at is null and admin_post.publisher_status is true and 
        post_bucket_mapping.deleted_at is null and post_bucket_mapping.type not in (
        'broadcast', 'international_broadcast', 'india_broadcast', 'business_broadcast', 'email_broadcast')"""
        count = _query_execution(count_data)

        final_post = AdminPost.query.join(PostBucketMapping, AdminPost.post_id == PostBucketMapping.post_id,
                                          ).filter(
            AdminPost.publisher_status == True,
            AdminPost.deleted_at == None,
            PostBucketMapping.type.notin_(category),
            # ).order_by(AdminPost.created_at.desc()).paginate(
            # ).order_by(nullslast(AdminPost.update_at.desc()),  AdminPost.created_at.desc()).paginate(
        # ).order_by(AdminPost.update_at.desc()).order_by(AdminPost.created_at.desc()).order_by(AdminPost.publisher_approved_at.desc()).paginate(
        ).order_by(AdminPost.publisher_approved_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False)

        result = []
        final_list = final_post.items
        if count:
            total_record = count[0]['count']
        else:
            total_record = 0
        total_pages = total_record // per_page + 1

        if final_list:
            for item in final_list:
                post_detail = Post.query.filter_by(id=item.post_id, deleted_at=None, status='active').first()
                if post_detail:
                    user_data = Users.query.filter_by(id=post_detail.user_id, user_deleted_at=None,
                                                      deleted_at=None).first()
                    post_list = AdminPost.query.filter_by(post_id=post_detail.id, deleted_at=None).first()
                    bucket_data = PostBucketMapping.query.filter_by(post_id=post_detail.id, deleted_at=None).all()
                    if user_data and post_list and bucket_data:
                        user_info = get_user_profile_details(user_data.id)
                        if user_info:
                            details = {}
                            details['id'] = post_detail.id
                            details['location'] = post_detail.location
                            details['title'] = post_detail.title
                            details['description'] = post_detail.description
                            details['created_at'] = post_detail.created_at
                            details['visibility'] = post_detail.visibility
                            details['type'] = post_detail.type
                            details['meta_data'] = post_detail.meta_data
                            details['expire_on'] = post_detail.expire_on
                            details['user_info'] = user_info
                            details['priority'] = item.s_id
                            details['expiry_date'] = post_list.expiry_date
                            details['is_priority'] = post_list.is_priority
                            buckets = []
                            for bucket in bucket_data:
                                buckets.append(bucket.key)
                            details['bucket_name'] = buckets
                            result.append(details)
            return success('SUCCESS', result, meta={"message": "final posts", 'page_info': {'current_page': page,
                                                                                            'limit': per_page,
                                                                                            'total_records': total_record,
                                                                                            'total_pages': total_pages}})

        else:
            return success('SUCCESS', meta={'message': "No data found"})
    else:
        return success('SUCCESS', meta={'message': "invalid user"})


def search_admin_post(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None, user_deleted_at=None).first()
    if existing_user:
        keyword = request.args.get('keyword')
        search_string = '%{}%'.format(keyword)
        discarded_post = AdminPost.query.filter_by(deleted_at=None, publisher_status=True).all()
        post_list = []
        if discarded_post:
            for item in discarded_post:
                post_list.append(str(item.post_id))
        # if keyword and type == 'name':
        search_list = Post.query.join(Users, Users.id == Post.user_id).filter(
            or_((Users.first_name.ilike(search_string)), (Post.description.ilike(search_string))),
            Post.id.in_(post_list), Post.status == 'active', Post.visibility=='admin' ).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        if search_list:
            posts = search_list.items
            total_record = len(posts)
            if posts:
                result = []
                for data in posts:
                    user_data = Users.query.filter_by(id=data.user_id, deleted_at=None,
                                                      user_deleted_at=None).first()
                    post_data = AdminPost.query.filter_by(post_id=data.id, deleted_at=None).first()
                    if user_data and post_data:
                        user_info = get_user_profile_details(user_data.id)
                        details = {}
                        details['id'] = data.id
                        details['location'] = data.location
                        details['title'] = data.title
                        details['description'] = data.description
                        details['created_at'] = data.created_at
                        details['visibility'] = data.visibility
                        details['type'] = data.type
                        details['meta_data'] = data.meta_data
                        details['expire_on'] = data.expire_on
                        details['user_info'] = user_info
                        details['expiry_date'] = post_data.expiry_date
                        details['is_priority'] = post_data.is_priority
                        result.append(details)
                return success('SUCCESS', result, meta={'message': 'post list',
                                                        'page_info': {'current_page': page, 'limit': per_page,
                                                                      'total_records': total_record}})
            else:
                return success('SUCCESS', meta={'message': 'No post found'})
        else:
            return success('SUCCESS', meta={'message': 'No post'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid post'})


def mis_list_count(current_user,data):
    data = request.get_json()
    # from_date = parser.parse(data.get('from_date'))
    to_date = parser.parse(data.get('to_date'))
    result = []
    user_list = db.session.query(Users).filter(and_(func.date(Users.created_at) >= '0001-01-01'),
                                               func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                                              Users.user_deleted_at == None).order_by(
        Users.created_at.desc()).all()

    if user_list:
        for user_data in user_list:
            member_ship = Membership.query.filter_by(user_id=user_data.id, membership_type='general',
                                                     membership_status='active', deleted_at=None).all()
            if member_ship:

                user_count = db.session.query(Users).filter(
                            and_(func.date(Users.created_at) >= '0001-01-01'),
                            func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None, Users.user_deleted_at == None).count()
                active_users = db.session.query(Membership).filter(
                    and_(func.date(Membership.created_at) >= '0001-01-01'),
                    func.date(Membership.created_at) <= to_date).filter(Membership.deleted_at == None,Membership.membership_status=='active'
                                                                 ).count()
                individual_user = db.session.query(Users).filter(
                    and_(func.date(Users.created_at) >= "0001-01-01"),
                    func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                   Users.user_deleted_at == None
                                                                   ).count()
                business_users = db.session.query(Users).filter(
                            and_(func.date(Users.created_at) >= '0001-01-01'),
                            func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                           Users.user_deleted_at == None,Users.business_account==True).count()
                follow_me_user = db.session.query(Users).filter(
                    and_(func.date(Users.created_at) >= '0001-01-01'),
                    func.date(Users.created_at) <= to_date).filter(Users.deleted_at == None,
                                                                   Users.user_deleted_at == None,
                                                                   Users.can_follows == True).count()
                friends_count = db.session.query(Contact).filter(and_(func.date(Contact.created_at) >= '0001-01-01'),
                                                                 func.date(Contact.created_at) <= to_date).filter(
                    Contact.friend_status == 'friends', Contact.deleted_at == None).count()
                total_groups = db.session.query(Group).filter(
                    and_(func.date(Group.created_at) >= '0001-01-01'),
                    func.date(Group.created_at) <= to_date).filter(Group.deleted_at == None).count()
                health_records = db.session.query(HealthReport).filter(
                    and_(func.date(HealthReport.created_at) >= '0001-01-01'),
                    func.date(HealthReport.created_at) <= to_date).filter(HealthReport.deleted_at == None).count()
                feature_programs = db.session.query(Programme).filter(
                    and_(func.date(Programme.created_at) >= '0001-01-01'),
                    func.date(Programme.created_at) <= to_date).filter(Programme.deleted_at == None).count()
                if user_count >= 0:
                    list = {}
                    list['name'] = 'Users'
                    list['count'] = user_count
                    result.append(list)
                if individual_user >= 0:
                    list1 = {}
                    list1['name'] = 'Individual users'
                    list1['count'] = individual_user
                    result.append(list1)

                if business_users >= 0:
                    list2 = {}
                    list2['name'] = 'Business users'
                    list2['count'] = business_users
                    result.append(list2)
                if follow_me_user >= 0:
                    list3 = {}
                    list3['name'] = 'Follow me users'
                    list3['count'] = follow_me_user
                    result.append(list3)
                if active_users >= 0:
                    active_users_list = {}
                    active_users_list['name'] = 'Active users'
                    active_users_list['count'] = active_users
                    result.append(active_users_list)
                if friends_count >= 0:
                    list31 = {}
                    list31['name'] = 'Friends'
                    list31['count'] = friends_count
                    result.append(list31)
                if total_groups >= 0:
                    group_count = {}
                    group_count['name'] = 'Groups'
                    group_count['count'] = total_groups
                    result.append(group_count)
                if health_records >= 0:
                    records_count = {}
                    records_count['name'] = 'HR added'
                    records_count['count'] = health_records
                    result.append(records_count)
                if feature_programs >= 0:
                    programs_count = {}
                    programs_count['name'] = 'Fprog added'
                    programs_count['count'] = feature_programs
                    result.append(programs_count)
                if data["xlsx_required"]:
                    results = []
                    status, file = profile_mis_xlsx(result,to_date)
                    if status:
                        mis_list = {}
                        mis_list['file'] = file
                        results.append(mis_list)
                    return success('SUCCESS', results, meta={'message': 'file is downloaded'})
            return success("SUCCESS", result, meta={'message': 'list'})
    else:
        return success('SUCCESS', meta={'message':'No data found'})


def profile_mis_xlsx(data,to_date):
    name_uuid = uuid.uuid4()
    file_path = str(name_uuid) + '.xlsx'
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet('Profile_mis')
    bold_formate = workbook.add_format({'bold': True})
    worksheet.write('C3', 'to_date', bold_formate)
    worksheet.write('D3', str(to_date))
    worksheet.write('A6', 'Users', bold_formate)
    worksheet.write('B6', 'Individual users', bold_formate)
    worksheet.write('C6', 'Business users', bold_formate)
    worksheet.write('D6', 'Follow me users', bold_formate)
    # worksheet.write('E1', 'Active users', bold_formate)
    worksheet.write('E6', 'Friends', bold_formate)
    worksheet.write('F6', 'Groups', bold_formate)
    worksheet.write('G6', 'HR added', bold_formate)
    worksheet.write('H6', 'Fprog added', bold_formate)
    row = 7
    column = 0
    for item in data:
        if item['name'] == 'Users':
            worksheet.write(row, column, str(item['count']))
        if item['name'] == 'Individual users':
            worksheet.write(row, column + 1, str(item['count']))
        if item['name'] == 'Business users':
            worksheet.write(row, column + 2, str(item['count']))
        if item['name'] == 'Follow me users':
            worksheet.write(row, column + 3, str(item['count']))
        # if item['name'] == 'Active users':
        #     worksheet.write(row, column + 4, str(item['count']))
        if item['name'] == 'Friends':
            worksheet.write(row, column + 4, str(item['count']))
        if item['name'] == 'Groups':
            worksheet.write(row, column + 5, str(item['count']))
        if item['name'] == 'HR added':
            worksheet.write(row, column + 6, str(item['count']))
        if item['name'] == 'Fprog added':
            worksheet.write(row, column + 7, str(item['count']))
    row += 1
    workbook.close()
    client = boto3.client('s3',
                          region_name=AWS_REGION_NAME,
                          aws_access_key_id=AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                          )
    client.upload_file(file_path, AWS_BUCKET_NAME, file_path, ExtraArgs={'ACL': 'public-read'})
    s3_path = f"https://{AWS_BUCKET_NAME}.s3.amazonaws.com/{file_path}"
    workbook.close()
    os.remove(file_path)
    return workbook, s3_path



def disable_cms_user(current_user, user_id):
    existing_user_role = Membership.query.filter_by(user_id=current_user.id, role='super_admin').first()
    if existing_user_role:
        existing_user = Membership.query.filter_by(user_id=user_id, membership_type='admin',
                                                   membership_status='active').first()
        user_data = Users.query.filter_by(id=user_id, user_deleted_at=None, deleted_at=None).first()
        if existing_user and user_data:

            existing_user.membership_status = 'inactive'
            update_item(existing_user)
            user_data.deleted_at = datetime.datetime.now()
            update_item(user_data)
            return success("SUCCESS", meta={'message': 'User Disabled'})
        else:
            return success('SUCCESS', meta={'message': 'invalid user'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid admin'})


def cms_user_enable(current_user, user_id):
    existing_user_role = Membership.query.filter_by(user_id=current_user.id, role='super_admin').first()
    if existing_user_role:
        disabled_user = Membership.query.filter_by(user_id=user_id, membership_type='admin',
                                                   membership_status='inactive').first()
        user_data = db.session.query(Users).filter(Users.id == user_id, Users.deleted_at != None).first()
        if disabled_user and user_data:
            disabled_user.membership_status = 'active'
            update_item(disabled_user)
            user_data.deleted_at = None
            update_item(user_data)

            return success("SUCCESS", meta={'message': 'User Enabled'})
        else:
            return success("SUCCESS", meta={'message': 'User is not inactive'})
    else:
        return success("SUCCESS", meta={'message': 'Invalid admin'})

