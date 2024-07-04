import datetime
import json
import urllib
import boto3
import firebase_admin
import requests
from firebase_admin import messaging, credentials
from flask import jsonify, request, send_from_directory, url_for
from sqlalchemy import not_

from api.Group.models import Group, GroupMembers
from api.notification.models import Notification
from config import UPDATE_TIMELINE_URL, PUSH_NOTIFICATION_URL, FIREBASE_DYNAMIC_LINK_URL, DEEP_LINK_PREFIX, \
    DEEP_LINK_URL, ANDROID_PACKAGE_NAME, IOS_BUNDLE_ID
from api.Post.models import Post, MasterActivity, UserBettings, BettingPost, PostCustomVisibility, PostReact, \
    MasterBettingItems, UserBucket, AdminPostViews, AdminPost, ReportedPost
from api.Post.mongo_services import UserIntermediateRepository, UserTimeLineRepository, ViewPostRepository
from api.Users.models import Users, Membership
from api.Users.services import get_user_profile_details
from api.comment.models import Comment
from api.contact.models import Contact, UserTopics
from api.media.services import get_media_access
from api.notification.services import send_queue_message
from app import db
from common.connection import add_item, update_item, _query_execution, delete_item
from common.response import success, failure
from geopy.geocoders import Nominatim


def prepare_activity(activities):
    activity_id = activities["activity_id"]
    keys = activities.keys()
    incoming_activity_keys = list(keys)
    final_activities = {"activity_id": activity_id}
    master_activity = MasterActivity.query.filter_by(id=activity_id).first()
    if master_activity:
        activity_fields = master_activity.fields
        master_activity_fields = []
        for fields in activity_fields:
            fields = fields['key']
            if fields in incoming_activity_keys:
                final_activities[fields] = activities[fields]
            else:
                final_activities[fields] = None
    return final_activities



def prepare_activity_v2(activities):
    activity_id = activities.get("activity_id",None)
    more_info = activities.get("more_info",None)
    parameters = activities.get('parameters',None)
    final_activities = {"activity_id": activity_id, "more_info": more_info}
    master_activity = MasterActivity.query.filter_by(id=activity_id).first()
    if master_activity:
        activity_fields = master_activity.fields
        master_activity_fields = []
        if activity_fields:
            for fields in activity_fields:
                field = fields['key']
                for item in parameters:
                    if field == item['key']:
                        master_activity_fields.append(item)
            final_activities['parameters'] = master_activity_fields
    return final_activities


def fetch_post_own(current_user, data):
    if data:
        page, per_page = data.get('page'), data.get('limit')
    else:
        page = 1
        per_page = 10
    posts = Post.query.filter(Post.user_id == current_user.id).paginate(page=page,
                                                                        per_page=per_page,
                                                                        error_out=False)
    posts = posts.items
    result = []
    for post in posts:
        post_data = {}
        post_data['user_id'] = post.user_id
        post_data['id'] = post.id
        post_data['location'] = post.location
        post_data['title'] = post.title
        post_data['description'] = post.description
        post_data['created_at'] = post.created_at
        post_data['visibility'] = post.visibility
        post_data['type'] = post.type
        post_data['meta_data'] = post.meta_data

        result.append(post_data)

    return success('SUCCESS', result)


def fetch_post(current_user, user_id, data):
    if data:
        page, per_page = data.get('page'), data.get('limit')
    else:
        page = 1
        per_page = 10
    offset = per_page * (page - 1)
    filter_visibility = "'all'"
    user_contact = Contact.query.filter_by(user_id=current_user.id, contact_id=user_id).first()
    if user_contact:
        if user_contact.is_following:
            filter_visibility = filter_visibility + ", 'followers'"
        if user_contact.friend_status == 'friends':
            filter_visibility = filter_visibility + ", 'friends'"

    query = "SELECT p.* " \
            "FROM post p " \
            "LEFT JOIN post_custom_visibility v ON p.id = v.post_id " \
            "WHERE p.user_id = '" + user_id + "' " \
                                              "AND p.visibility IN(" + filter_visibility + ") AND (v.id is null OR " \
                                                                                           "(v.user_id = '" + str(
        current_user.id) + "') " \
                           ") ORDER BY p.created_at DESC LIMIT " + str(per_page) + " OFFSET " + str(offset)
    posts = _query_execution(query)


    result = []
    for post in posts:
        post_data = {}
        post_data['user_id'] = post['user_id']
        post_data['id'] = post['id']
        post_data['location'] = post['location']
        post_data['title'] = post['title']
        post_data['description'] = post['description']
        post_data['created_at'] = post['created_at']
        post_data['visibility'] = post['visibility']
        post_data['type'] = post['type']
        post_data['meta_data'] = post['meta_data']

        result.append(post_data)

    return success('SUCCESS', result)


def add_master_activity(data):
    master_activity = MasterActivity(name=data.get('name', None), fields=data.get('fields', None))
    add_item(master_activity)
    return success('Activity added', {})


def get_activity():
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    all_activities = MasterActivity.query.all()
    activities = MasterActivity.query.order_by(MasterActivity.name.asc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    total_records = len(all_activities)
    activities = activities.items
    total_pages = total_records // per_page + 1
    result = []
    for activity in activities:
        activity_data = {}
        activity_data['id'] = activity.id
        activity_data['name'] = activity.name
        activity_data['image_url'] = activity.logo
        activity_data['fields'] = activity.fields

        result.append(activity_data)

    return success('SUCCESS', result, meta={'message': 'Master Activities',
                                            'page_info': {'current_page': page, 'limit': per_page,
                                                          'total_record': total_records, 'total_pages': total_pages}})


def post_details(data):
    new_post = Post.query.get()
    type = data['type']
    title = data['title']
    source = data['source']
    sorting_position = data['sorting_position']
    path = data['path']
    thumbnail = data['thumbnail']
    metadata = data['metadata']
    visibility = data['visibility']
    group_id = data['group_id']

    new_post.type = type
    new_post.title = title
    new_post.source = source
    new_post.sorting_postion = sorting_position
    new_post.path = path
    new_post.thumbnail = thumbnail
    new_post.metadata = metadata
    new_post.visibility = visibility
    new_post.group_id = group_id
    return new_post


def create_post(data, current_user):
    fcm_token = []
    # membership_type = current_user.membership_type
    expire_on = data.get('expire_on', None)
    save_later = data.get('save_later', None)
    type = data.get('type', None)
    post_visibility = data.get('visibility', None)
    meta_data = data.get('meta_data', None)
    input_location = data.get('location', None)
    if type not in ['regular', 'activity', 'betting','result','watch_activity','record_activity']:
        return success('SUCCESS',meta={'message':'Invalid post type'})

    if type == "betting" and "betting" in meta_data:
        betting_fields = meta_data['betting']
        members = betting_fields.get("members", [])
        # if int(betting_fields["oods"]) != len(members):
        #     return failure('FAILURE', {'message': "Selected members are not matching"})

    location = {"city": None, "state": None}
    if input_location:
        location["city"] = input_location.get('city', None)
        location["state"] = input_location.get('state', None)
    post = Post(title=data.get('title', None), description=data.get('description', None),
                visibility=data.get('visibility', None), type=type,
                user_id=current_user.id, location=location, group_id=data.get('group_id', None))
    post = add_item(post)

    # add share_link
    share_link = share_dynamic_link(post.id)
    post.share_link = share_link
    update_item(post)

    timeline = UserTimeLineRepository.get_one_by_user_id(str(current_user.id))
    if timeline is not None:
        timeline_data = timeline.post_sequence
        UserTimeLineRepository.update(timeline, [str(post.id)] + timeline_data)
    else:
        UserTimeLineRepository.create({'user_id': str(current_user.id), 'post_sequence': [str(post.id)]})

    if expire_on:
        post.expire_on = expire_on
        update_item(post)

    if type == 'activity' and meta_data and 'activity' in meta_data:
        activity_meta_data = prepare_activity(activities=meta_data['activity'])
        meta_data['activity'] = activity_meta_data

    if type == 'watch_activity' and meta_data and 'activity' in meta_data:
        meta_data = meta_data

    if type == 'record_activity' and meta_data and 'activity' in meta_data:
        record_meta_data = prepare_record(post=post, record_fields=meta_data['activity'])
        meta_data['activity'] = record_meta_data

    elif type == 'betting':
        # meta_data['betting']['expire_on'] = data.get('expire_on', None)
        betting_meta_data = prepare_betting(post=post, betting_fields=meta_data['betting'])
        meta_data['betting'] = betting_meta_data
        # primary_team = meta_data['betting']['primary_team']
        betting_post = BettingPost(user_id=current_user.id, primary_team=meta_data['betting']['primary_team'],
                                   secondary_team=meta_data['betting']['secondary_team'], post_id=post.id,
                                   betting_for=meta_data['betting']['betting_for'], oods=meta_data['betting']['oods'],
                                   favour_of=meta_data['betting']['favour_of'],expire_on=expire_on,
                                   description=meta_data['betting']['item_description'])
        add_item(betting_post)

        betting_fields = meta_data['betting']
        members = betting_fields.get("members", [])
        for member in members:
            user_betting = UserBettings(user_id=member, post_id=post.id, betting_status='invited',
                                        result_status='')
            add_item(user_betting)
            user_membership = Membership.query.filter_by(user_id=member, deleted_at=None).first()
            fcm_token.append(user_membership.fcm_token)

        # send notification
        user_data = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
        message = "Betting invite from " + user_data.first_name
        queue_url = PUSH_NOTIFICATION_URL
        payload = {}
        payload['id'] = str(post.id)
        payload['current_user'] = str(current_user.id)
        payload['message'] = message
        payload['title'] = "Betting Invite"
        payload['fcm_token'] = fcm_token
        payload['screen_type'] = 'BETTING_DETAIL'
        payload['responder_id'] = None
        send_queue_message(queue_url, payload)
        # post in-app notification
        screen_info = {}
        data = {}
        screen_info['screen_type'] = 'BETTING_DETAIL'
        screen_info['id'] = str(post.id)
        data['meta_data'] = screen_info
        for user in members:
            add_notification = Notification(user_id=user, type='post', title=payload['title'],
                                            description=message, read_status=False,meta_data=data['meta_data'],c_user=current_user.id)
            add_item(add_notification)

    if post_visibility == "custom":
        betting_data = meta_data['betting']
        visible_to_users = betting_data.get("members", [])
        if visible_to_users:
            for user in visible_to_users:
                custom_visibility = PostCustomVisibility(post_id=post.id, user_id=user, tag=True)
                add_item(custom_visibility)
        else:
            return success('SUCCESS',meta={"please add members"})

    if post and meta_data:
        post.meta_data = meta_data
        if type == 'activity':
            post.save_later = save_later
        update_item(post)

    from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
    sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                                aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
    response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL ,MessageBody=json.dumps({'post_id': str(post.id)})
        )

    return success('SUCCESS', meta={'message': 'Post created succesfully'})


def prepare_betting(post, betting_fields):
    final_betting_fields = {}
    final_betting_fields["primary_team"] = betting_fields.get("primary_team")
    final_betting_fields["prediction_description"] = betting_fields.get("prediction_description")
    final_betting_fields["secondary_team"] = betting_fields.get("secondary_team")
    final_betting_fields["betting_for"] = betting_fields.get("betting_for")
    final_betting_fields["oods"] = betting_fields.get("oods")
    final_betting_fields["favour_of"] = betting_fields.get("favour_of")
    final_betting_fields["item_description"] = betting_fields.get("item_description")
    final_betting_fields["result"] = None
    members = betting_fields.get("members", [])
    final_betting_fields["members"] = members
    return final_betting_fields


def prepare_record(post, record_fields):
    final_record_fields = {}
    final_record_fields["activity_id"] = record_fields.get("activity_id")
    final_record_fields["parameters"] = record_fields.get("parameters")
    final_record_fields["felt"] = record_fields.get("felt")
    return final_record_fields


def prepare_record_v2(post, record_fields):
    final_record_fields = {}
    final_record_fields["activity_id"] = record_fields.get("activity_id")
    final_record_fields["activityName"] = record_fields.get("activityName")
    final_record_fields["average_speed"] = record_fields.get("average_speed")
    final_record_fields["ditance"] = record_fields.get("ditance")
    final_record_fields["duration"] = record_fields.get("duration")
    final_record_fields["felt"] = record_fields.get("felt")
    return final_record_fields


def betting_react(current_user, data):
    post_id = data.get('post_id', None)
    betting_status = data.get('betting_status', None)
    if post_id and betting_status:
        user_bettings = UserBettings.query.filter_by(user_id=current_user.id, post_id=post_id).first()
        if user_bettings:
            if betting_status in ["accepted", "reject"] and user_bettings.betting_status == 'invited':
                user_bettings.betting_status = betting_status
                update_item(user_bettings)
                if betting_status =='accepted':
                    #send notification
                    message = current_user.first_name + " accepted your betting invite"
                    queue_url = PUSH_NOTIFICATION_URL
                    fcm_token = []
                    post_data = Post.query.filter_by(id=post_id, deleted_at=None,status='active').first()
                    post_owner = Users.query.filter_by(id=post_data.user_id, deleted_at=None,user_deleted_at=None).first()
                    user_membership = Membership.query.filter_by(user_id=post_owner.id, deleted_at=None).first()
                    fcm_token.append(user_membership.fcm_token)
                    payload = {}
                    payload['id'] = str(post_data.id)
                    payload['current_user'] = str(current_user.id)
                    payload['message'] = message
                    payload['title'] = "Betting Request"
                    payload['fcm_token'] = fcm_token
                    payload['screen_type'] = 'BETTING_DETAIL'
                    payload['responder_id'] = str(current_user.id)
                    send_queue_message(queue_url, payload)

                    # post in-app notification
                    screen_info = {}
                    data = {}
                    screen_info['screen_type'] = 'BETTING_DETAIL'
                    screen_info['id'] = str(post_data.id)
                    screen_info['responder_id'] = str(current_user.id)
                    data['meta_data'] = screen_info
                    add_notification = Notification(user_id=post_owner.id, type='post', title=payload['title'],
                                                    description=message, read_status=False,meta_data=data['meta_data'],c_user=current_user.id)
                    add_item(add_notification)

            else:
                return success('SUCCESS',meta={'message':'invalid_betting_react_status'})
        else:
            return success('SUCCESS', meta={'message':'Betting request not found'})
    else:
        return success('SUCCESS',meta={'message':'invalid data'})


def result_update(current_user, data):
    post_id = data.get('post_id')
    results = data.get('result')
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        valid_post = Post.query.filter_by(id=post_id, user_id=current_user.id, deleted_at=None,status='active').first()
        if valid_post:
            my_betting_post = BettingPost.query.filter_by(user_id=current_user.id, post_id=post_id,
                                                          deleted_at=None, results=None).first()
            if my_betting_post:
                my_betting_post.results = results
                update_item(my_betting_post)
                create_result_post(post_id, results)
                # create result post

                return success("SUCCESS", meta={"message": "Betting Result updated"})
            else:
                return success('SUCCESS', meta={'message': 'data not found'})
        else:
            return success('SUCCESS', meta={'message': 'invalid post'})
    else:
        return success('SUCCESS', meta={'message': 'invalid user'})


def betting_conforamtion(current_user, data):
    user_id = data.get('user_id',None)
    post_id = data.get('post_id',None)
    betting_status = data.get('betting_status' ,None)
    post = Post.query.filter_by(id=post_id, user_id=current_user.id ,deleted_at=None,status='active').first()
    if post:
        user_betting =UserBettings.query.filter_by(post_id=post.id,user_id=user_id ,betting_status='accepted' , deleted_at=None).first()
        if user_betting:
            if betting_status in ["confirmed" ,"rejected"]:
                user_betting.betting_status = betting_status
                update_item(user_betting)
                #send notification
                if betting_status == 'confirmed':
                    fcm_token = []
                    user_membership = Membership.query.filter_by(user_id=user_id, deleted_at=None).first()
                    fcm_token.append(user_membership.fcm_token)
                    message = "BETTING is ON!"
                    queue_url = PUSH_NOTIFICATION_URL
                    payload = {}
                    payload['id'] = str(post_id)
                    payload['current_user'] = str(current_user.id)
                    payload['message'] = message
                    payload['title'] = "Betting Confirmation"
                    payload['fcm_token'] = fcm_token
                    payload['screen_type'] = 'BETTING_DETAIL'
                    payload['responder_id'] = None
                    send_queue_message(queue_url, payload)

                    # post in-app notification
                    screen_info = {}
                    data = {}
                    screen_info['screen_type'] = 'BETTING_DETAIL'
                    screen_info['id'] =str(post_id)
                    data['meta_data'] = screen_info
                    add_notification = Notification(user_id=user_id, type='post', title=payload['title'],
                                                    description=message, read_status=False,meta_data=data['meta_data'],c_user=current_user.id)
                    add_item(add_notification)

                return success("SUCCESS", meta={"message": "Betting Confirmation"})
            else:
                return success("SUCCESS", meta={"message": "Invalid Status"})
        else:
            return success('SUCCESS',meta={"message": 'No Betting Requests!'})
    else:
        return success('SUCCESS',meta={"message": 'post not found'})


def result_confirmation(current_user, data):
    post_id = data.get('post_id')
    status = data.get('result_status')
    users_betting = UserBettings.query.filter_by(user_id=current_user.id, post_id=post_id,
                                                 betting_status='accepted').first()
    if users_betting:
        users_betting.result_status = status
        update_item(users_betting)
        return "betting users result confirmation updated"


def create_result_post(post_id, results):
    post_details = Post.query.filter_by(id=post_id, deleted_at=None,status='active').first()
    betting_details = BettingPost.query.filter_by(post_id=post_id, deleted_at=None).first()
    exist_betting_item = post_details.meta_data['betting']['betting_for']
    item_description = post_details.meta_data['betting']['item_description']

    betting_item = MasterBettingItems.query.filter_by(id=betting_details.betting_for, deleted_at=None).first()
    if betting_details.primary_team == results:
        description = ''
        user_id = post_details.user_id
        if exist_betting_item:
            description = description + "I won on " + betting_details.primary_team + " for " + betting_details.oods + " " + \
                          betting_item.name + " X 1:" + betting_details.oods + " oods"
        else:
            description = description + "I won on " + betting_details.primary_team + " for " + betting_details.oods + " " + \
                          item_description + " X 1:" + betting_details.oods + " oods"

        post_result = Post(type='betting_result', visibility='friends', user_id=user_id,
                           location=post_details.location, description=description, meta_data=post_details.meta_data,
                           expire_on=betting_details.expire_on)
        res_post = add_item(post_result)
        ###
        timeline = UserTimeLineRepository.get_one_by_user_id(str(user_id))
        if timeline is not None:
            timeline_data = timeline.post_sequence
            UserTimeLineRepository.update(timeline, [str(res_post.id)] + timeline_data)
        else:
            UserTimeLineRepository.create({'user_id': str(user_id), 'post_sequence': [str(res_post.id)]})

        from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
        sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                           aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
        response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL, MessageBody=json.dumps({'post_id': str(res_post.id)})
                                    )
        return success('SUCCESS', meta={'message': 'result post created'})
    elif betting_details.secondary_team == results:
        description = ''
        betting_members = UserBettings.query.filter_by(post_id=post_id, deleted_at=None,
                                                       betting_status='confirmed').all()
        for members in betting_members:
            if exist_betting_item:
                description = description + "I won on " + betting_details.primary_team + " for " + betting_details.oods + " " + \
                              betting_item.name + " X 1:" + betting_details.oods + " oods"
            else:
                description = description + "I won on " + betting_details.primary_team + " for " + betting_details.oods + " " + \
                              item_description + " X 1:" + betting_details.oods + " oods"
            post_result = Post(type='betting_result', visibility='friends', user_id=members.user_id,
                               location=post_details.location, description=description, meta_data=post_details.meta_data,
                               expire_on=betting_details.expire_on)
            res_post = add_item(post_result)
            #####
            timeline = UserTimeLineRepository.get_one_by_user_id(str(members.user_id))
            if timeline is not None:
                timeline_data = timeline.post_sequence
                UserTimeLineRepository.update(timeline, [str(res_post.id)] + timeline_data)
            else:
                UserTimeLineRepository.create({'user_id': str(members.user_id), 'post_sequence': [str(res_post.id)]})

            from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
            sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                               aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
            response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL, MessageBody=json.dumps({'post_id': str(res_post.id)})
                                        )
        return success('SUCCESS', meta={'message': 'result post created'})
    else:
        return success('SUCCESS', meta={'message': 'invalid result'})


def update_post(data, post_id, current_user):
    my_post = Post.query.filter_by(user_id=current_user.id, id=post_id, deleted_at=None,status='active').first()
    type = data.get('type', None)
    promotion = data.get('promotion', None)
    meta_data = data.get('meta_data', None)
    input_location = data.get('location', None)
    if type not in ['regular', 'activity', 'betting']:
        return False
    location = {"city": None, "state": None}
    if input_location:
        location["city"] = input_location.get('city', None)
        location["state"] = input_location.get('state', None)
    my_post.title = data.get('title', None)
    my_post.description = data.get('description', None)
    my_post.visibility = data.get('visibility', None)
    my_post.type = type
    my_post.location = location
    if data.get('expire_on', None):
        my_post.expire_on = data.get('expire_on', None)
    post = update_item(my_post)

    if type == 'activity' and meta_data and 'activity' in meta_data:
        activity_meta_data = prepare_activity_v2(activities=meta_data['activity'])
        meta_data['activity'] = activity_meta_data
    elif type == 'betting':
        meta_data['betting']['expire_on'] = data.get('expire_on', None)
        betting_field = meta_data['betting']
        members = betting_field.get("members", [])
        if int(betting_field["oods"]) != len(members):
            return success('SUCCESS', meta={'message': "Ood numbers are not matching"})
        else:
            if data.get('visibility') == "custom":
                visible_to_users = data.get('visible_to')
                if not visible_to_users == members:
                    return success('SUCCESS', meta={'message': "Make visible to the members"})
                else:
                    betting_meta_data = prepare_betting(post=post, betting_fields=meta_data['betting'])
                    meta_data['betting'] = betting_meta_data

                    update_post = BettingPost.query.filter_by(post_id=post_id).first()
                    update_post.oods = len(members)
                    update_post.expire_on = data.get('expire_on', None)
                    update_item(update_post)
            else:
                betting_meta_data = prepare_betting(post=post, betting_fields=meta_data['betting'])
                meta_data['betting'] = betting_meta_data

                update_post = BettingPost.query.filter_by(post_id=post_id).first()
                update_post.oods = len(members)
                update_post.expire_on = data.get('expire_on', None)
                update_item(update_post)
    if post and meta_data:
        post.meta_data = meta_data
        update_item(post)

    # update promotion
    if promotion and  promotion == True:
        post.promotion = True
        update_item(post)
    else:
        post.promotion = False
        update_item(post)
    return success('SUCCESS',meta={"messgae":"Post Updated Successfully"})


def get_wall_content(current_user, data):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    offset = per_page * (page - 1)

    following_contacts = Contact.query.filter(Contact.user_id == current_user.id,
                                              Contact.is_following == True).all()
    only_following = []
    all_friends = ''
    for following_contact in following_contacts:
        only_following.append("'" + str(following_contact.contact_id) + "'")
    if only_following:
        all_friends = ','.join(only_following)

    if all_friends:
        filter_visibility = ('all', 'followers')
        query = """SELECT  p.* FROM post p 
               LEFT JOIN post_custom_visibility v ON p.id = v.post_id
               LEFT JOIN contact c ON (p.user_id = c.user_id AND c.friend_status = 'friends')
               WHERE (p.deleted_at IS NULL AND p.group_id is NULL AND p.save_later is null) AND (p.user_id = '{user_id}' OR v.user_id ='{user_id}' OR p.visibility='all' OR (
               p.user_id IN({all_friends}) AND
               (p.visibility IN {filter_visibility} OR (p.visibility = 'friends' 
               AND (c.friend_status = 'friends' AND (c.contact_id = '{user_id}'))))
               ))GROUP BY (p.id) ORDER BY p.created_at DESC LIMIT {per_page} OFFSET {offset}
               """.format(all_friends=all_friends, filter_visibility=filter_visibility,
                          user_id=current_user.id, per_page=per_page, offset=offset)

    else:
        query = """SELECT p.* FROM post p LEFT JOIN post_custom_visibility v ON p.id = v.post_id WHERE (p.deleted_at IS  NULL AND p.group_id is NULL AND p.save_later is null ) AND (p.visibility ='all' OR v.user_id='{user_id}' OR  p.user_id = '{user_id}')
                ORDER BY p.created_at DESC LIMIT {per_page} OFFSET {offset}
                """.format(user_id=current_user.id, per_page=per_page, offset=offset)
    posts = _query_execution(query)
    total_record = len(posts)
    total_pages = total_record // per_page + 1

    result = []
    for post in posts:
        like_count = PostReact.query.filter(PostReact.post_id == post['id'], PostReact.type == 'like',
                                            PostReact.is_liked == True).count()
        comment_count = Comment.query.filter(Comment.post_id == post['id'], Comment.deleted_at == None).count()
        is_reacted = PostReact.query.filter(PostReact.user_id == current_user.id, PostReact.post_id == post['id'],
                                            PostReact.deleted_at == None).first()
        is_accepted = UserBettings.query.filter(UserBettings.user_id == current_user.id, UserBettings.post_id == post['id'],
                                            UserBettings.deleted_at == None,UserBettings.betting_status=='accepted').first()

        if like_count >= 0:
            post['like'] = like_count
        if comment_count >= 0:
            post['comment'] = comment_count
        if is_reacted is not None:
            post['is_like'] = is_reacted.is_liked
        else:
            post['is_like'] = False
        if is_accepted is not None:
            post['is_accepted'] = True
        else:
            post['is_accepted'] = False
        result.append(prepare_post_display_fileds(post))

    return success('SUCCESS', result,
                   meta={'message': 'Post Feed', 'page_info': {'current_page': page, 'limit': per_page}})


def get_promo_feeds(current_user):
    required_posts = 3
    primary_bucket_result_count = 0
    secondary_bucket_result_count = 0
    general_bucket_result_count = 0
    user_bucket = ['general']
    primary_bucket = []
    secondary_bucket = []
    user_buckets = UserBucket.query.filter_by(user_id=current_user.id).all()
    if user_buckets:
        for data in user_buckets:
            if data.is_primary:
                primary_bucket.append(data.bucket_key)
            else:
                secondary_bucket.append(data.bucket_key)
    user_bucket = user_bucket + primary_bucket
    user_bucket = user_bucket + secondary_bucket
    posts = []
    priority_post = get_admin_posts(current_user.id, user_bucket, True)
    if priority_post:
        posts = posts + priority_post
    priority_post_length = len(posts)
    required_posts = required_posts - priority_post_length
    if required_posts and primary_bucket:
        if secondary_bucket:
            if required_posts > 1:
                primary_bucket_result_count = 1
                secondary_bucket_result_count = 1
                required_posts = required_posts - 2
            else:
                primary_bucket_result_count = 1
                required_posts = required_posts - 1
        else:
            if required_posts > 1:
                primary_bucket_result_count = 2
                required_posts = required_posts - 2
            else:
                primary_bucket_result_count = 1
                required_posts = required_posts - 1

    if required_posts and (secondary_bucket and secondary_bucket_result_count == 0):
        if not primary_bucket and required_posts > 1:
            secondary_bucket_result_count = 2
            required_posts = required_posts - 2
        else:
            secondary_bucket_result_count = 1
            required_posts = required_posts - 1

    general_bucket_result_count = required_posts

    if primary_bucket_result_count > 0:
        admin_posts = get_admin_posts(current_user.id, primary_bucket, False, primary_bucket_result_count)
        if admin_posts:
            posts = posts + admin_posts

    if secondary_bucket_result_count > 0:
        admin_posts = get_admin_posts(current_user.id, secondary_bucket, False, secondary_bucket_result_count)
        if admin_posts:
            posts = posts + admin_posts

    if general_bucket_result_count > 0:
        admin_posts = get_admin_posts(current_user.id, ['general'], False, general_bucket_result_count)
        if admin_posts:
            posts = posts + admin_posts

    result = []
    for post in posts:
        admin_post_view = AdminPostViews.query.filter_by(user_id=current_user.id,
                                                         admin_post_id=post['admin_post_id']).first()
        if not admin_post_view:
            view_admin_post = AdminPostViews(user_id=current_user.id, admin_post_id=post['admin_post_id'])
            add_item(view_admin_post)
        result.append(prepare_post_display_fileds(post))

    if not result:
        return success('EMPTY', result)
    return success('SUCCESS', result)


def prepare_post_display_fileds(post):
    post_data = {}
    post_data['user_info'] = get_user_profile_details(post['user_id'])
    post_data['id'] = post['id']
    post_data['location'] = post['location']
    post_data['title'] = post['title']
    post_data['description'] = post['description']
    post_data['created_at'] = post['created_at']
    post_data['visibility'] = post['visibility']
    post_data['type'] = post['type']
    post_data['likes'] = post['like']
    post_data['comments'] = post['comment']
    post_data['is_liked'] = post['is_like']
    post_data['is_accepted'] = post['is_accepted']
    post_data['meta_data'] = post['meta_data']
    return post_data


def get_admin_posts(user_id, buckets, is_priority=False, record_count=0):
    filter_bucket = []
    for bucket in buckets:
        filter_bucket.append("'" + bucket + "'")
    user_bucket = ','.join(filter_bucket)
    query = """SELECT p.*, ap.id as admin_post_id FROM admin_post ap
                LEFT JOIN post p ON p.id = ap.post_id
                LEFT JOIN admin_post_views apv ON p.user_id = apv.user_id
                WHERE p.deleted_at IS  NULL AND (p.visibility = 'all' 
                AND (apv.id is null OR ((apv.created_at BETWEEN NOW() - INTERVAL '24 HOURS' AND NOW()) 
                AND (ap.is_priority = {is_priority} AND (ap.bucket IN ({user_bucket}) 
                AND (ap.is_approved = true AND (p.expire_on is null or p.expire_on > NOW())))))))
                """.format(user_bucket=user_bucket, user_id=user_id, is_priority=is_priority)
    query = query + " ORDER BY p.created_at DESC"
    if record_count:
        query = query + " LIMIT " + str(record_count)
    return _query_execution(query)


# send like notification
def add_post_react(data, current_user):
    post_id = data['post_id']
    type = data['type']
    post_data = Post.query.filter_by(id=post_id, deleted_at=None,status='active').first()
    post_owner = Users.query.filter_by(id=post_data.user_id, deleted_at=None,user_deleted_at=None).first()

    def like_notification():
        user_membership = Membership.query.filter_by(user_id=post_owner.id, deleted_at=None).first()
        message = current_user.first_name + " liked your post"
        queue_url = PUSH_NOTIFICATION_URL
        fcm_token = []
        fcm_token.append(user_membership.fcm_token)
        payload = {}
        screen_type = ''
        if post_data.type == 'regular':
            screen_type = 'REGULAR_POST'
        if post_data.type == 'activity':
            screen_type = 'ACTIVITY_POST'
        if post_data.type == 'betting':
            screen_type = 'BETTING_POST'
        if post_data.type == 'watch_activity':
            screen_type = 'WATCH_ACTIVITY_POST'
        if post_data.type =='betting_result':
            screen_type = 'BETTING_RESULT'
        if post_data.type == 'record_activity':
            screen_type = 'RECORD_ACTIVITY_POST'

        payload['id'] = str(post_data.id)
        payload['current_user'] = str(current_user.id)
        payload['message'] = message
        payload['title'] = "Like"
        payload['fcm_token'] = fcm_token
        payload['screen_type'] = screen_type
        payload['responder_id'] = None
        send_queue_message(queue_url, payload)

        # post in-app notification
        screen_info = {}
        data = {}
        screen_info['screen_type'] = screen_type
        screen_info['id'] = str(post_data.id)
        data['meta_data'] = screen_info
        add_notification = Notification(user_id=post_owner.id, type='post', title=payload['title'],
                                        description=message, read_status=False,meta_data=data['meta_data'],c_user=current_user.id)
        add_item(add_notification)

    post_react = PostReact.query.filter_by(post_id=post_id, user_id=current_user.id).order_by(
        PostReact.created_at.desc()).first()
    if post_react:
        if post_react.is_liked == True:
            # post_react.deleted_at = datetime.datetime.now()
            post_react.is_liked = False
            update_item(post_react)
            return success('SUCCESS', meta={'message': 'You unliked this post'})
        else:
            post_react.is_liked = True
            update_item(post_react)
            if post_owner.id != current_user.id:
                like_notification()
            return success('SUCCESS', meta={'message': 'You liked this post'})
    else:
        add_post_react = PostReact(post_id=post_id, type=type, user_id=current_user.id, is_liked=True)
        add_item(add_post_react)
        if post_owner.id != current_user.id:
            like_notification()
        return success('SUCCESS', meta={'message': 'You liked this post'})


def update_post_visibility(data, current_user):
    post_id = data.get('post_id')
    visibility = data.get('visibility')
    my_post = Post.query.filter_by(user_id=current_user.id, id=post_id,status='active').first()

    if my_post:
        if visibility in ["all", "friends", "private", "custom", "group", "followers"]:
            my_post.visibility = visibility
            update_item(my_post)
            visible_to = PostCustomVisibility.query.filter_by(post_id=post_id).all()
            for user in visible_to:
                delete_item(user)
            return success('SUCCESS', meta={'message': 'Post Visibility Updated'})
        else:
            my_post.visibility = data.get('visibility', None)
            update_item(my_post)
            return success('SUCCESS', meta={'message': 'Post Visibility Updated'})
    else:
        return success('SUCCESS', meta={'message': 'Post does not exists'})


def get_master_betting_items():
    all_items = MasterBettingItems.query.all()
    result = []
    for item in all_items:
        betting_items = {}
        betting_items['id'] = item.id
        betting_items['name'] = item.name
        betting_items['image'] = item.image
        result.append(betting_items)
    return success("SUCCESS", result)


def get_betting_members(post_id):
    members = UserBettings.query.filter_by(post_id=post_id, deleted_at=None).all()
    result = []
    if members:
        for member in members:
            member_details = Users.query.filter_by(id=member.user_id,user_deleted_at=None,deleted_at=None).first()
            if member_details:
                details = {}
                details["first_name"] = member_details.first_name
                details["last_name"] = member_details.last_name
                details["profile_image"] = member_details.profile_image
                details["betting_status"] = member.betting_status
                result.append(details)
        return success("SUCCESS", result)


def remove_betting_members(post_id, user_id):
    user_betting = UserBettings.query.filter_by(user_id=user_id, post_id=post_id, deleted_at=None).first()
    if user_betting:
        if user_betting.betting_status == 'pending':
            user_betting.betting_status = 'deleted'
            update_item(user_betting)
            return success("Removed successfully", {})
        else:
            return success("Bet is already accepted or deleted", {})
    else:
        return success("No bet found", {})



def check_if_admin_post(post_id):
    try:
        query = AdminPost.query.filter_by(post_id=post_id, publisher_status=True).first()
        if query is not None:
            return True
        return False
    except Exception as err:
        print(str(err))
        return False


def add_broadcast_post(user_id, viewed_post_list):
    try:
        post_list = []
        query = """SELECT p.id, ap.id as admin_post_id FROM admin_post ap
                    LEFT JOIN post p ON p.id = ap.post_id
                    LEFT JOIN post_bucket_mapping pbm ON p.id = pbm.post_id
                    WHERE p.deleted_at IS NULL AND ap.deleted_at is NULL 
                    AND ap.publisher_status IS true AND pbm.type = 'broadcast'"""
        if len(viewed_post_list) > 0:
            viewed_post_list = tuple(viewed_post_list)
            query = query + """ AND
                        ap.post_id NOT IN {viewed_post}""".format(viewed_post=viewed_post_list)
        data = _query_execution(query)
        for each in data:
            post_list.append(str(each['id']))
        time_line = UserTimeLineRepository.get_one_by_user_id(user_id)
        if time_line is not None:
            time_line_post = time_line.post_sequence
            post_list = post_list + time_line_post
            UserTimeLineRepository.update(time_line, post_list)
        else:
            UserTimeLineRepository.create({'user_id': user_id, 'post_sequence': post_list})
        return True
    except Exception as err:
        return False


def add_admin_post(user_id):
    # try:
    membership = Membership.query.filter_by(user_id=user_id,membership_status='active',membership_type='general').first()
    if membership is not None:
        intermediate_timeline = UserIntermediateRepository.get_one_by_user_id(user_id)
        if intermediate_timeline is not None:
            if intermediate_timeline.is_dumped or membership.last_feed_viewed.strftime("%Y-%m-%d") == datetime.date.today():
                # Intermediate queue dumped already for the day.
                pass
            else:
                timeline = UserTimeLineRepository.get_one_by_user_id(user_id)
                if timeline is not None and timeline.index >= 3:
                    UserTimeLineRepository.update(timeline, timeline.post_sequence[0:3] + intermediate_timeline.post_sequence + timeline.post_sequence[3:],0)
                elif timeline is not None and timeline.index > 0 and timeline.index < 3:
                    UserTimeLineRepository.update(timeline, timeline.post_sequence[0:1]
                                                             + intermediate_timeline.post_sequence + timeline.post_sequence[
                                                                                              1:],0)
                elif timeline is not None and timeline.index == 0:
                    UserTimeLineRepository.update(timeline, timeline.post_sequence
                                                             + intermediate_timeline.post_sequence,0)
                else:
                    UserTimeLineRepository.create({'user_id': user_id, 'post_sequence': intermediate_timeline.post_sequence,'index':0})
                viewed_post = ViewPostRepository.get_one_by_user_id(user_id)
                if viewed_post is None:
                    ViewPostRepository.create_post_view({'user_id': user_id, 'posts': intermediate_timeline.post_sequence})
                else:
                    post_list = viewed_post.posts
                    for each in intermediate_timeline.post_sequence:
                        if each in post_list:
                            pass
                        else:
                            post_list.append(each)
                    ViewPostRepository.update(viewed_post, post_list)
                UserIntermediateRepository.update(intermediate_timeline, {'is_dumped': True})
                membership.last_feed_viewed = datetime.datetime.now()
                update_item(membership)
        else:
            # Intermediate queue not found for the particular user
            pass
        return success('Success')
    return failure('Membership not found')
    # except Exception as err:
    #     return failure(str(err))


def post_saved_posts(current_user, post_id):
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        post_exist = Post.query.filter_by(id=post_id, deleted_at=None, user_id=current_user.id,status='active').first()
        if post_exist:
            post_exist.save_later = None
            update_item(post_exist)
            return success('SUCCESS', meta={'message': 'posted successfully'})
        else:
            return success('SUCCESS', meta={'message': 'invalid post'})
    else:
        return success('SUCCESS', meta={'message': 'invalid user'})


def get_save_later(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        all_post = Post.query.filter_by(user_id=current_user.id, save_later=True, deleted_at=None,status='active').all()
        post = Post.query.filter_by(user_id=current_user.id, save_later=True, deleted_at=None,status='active').paginate(
            page=page,
            per_page=per_page,
            error_out=False)

        total_records = len(all_post)
        posts = post.items
        total_pages = total_records // per_page + 1
        result = []
        if post:
            for item in posts:
                user_info = get_user_profile_details(item.user_id)
                post_data = {}
                post_data['post_id'] = item.id
                post_data['title'] = item.title
                post_data['type'] = item.type
                post_data['visibility'] = item.visibility
                post_data['user_info'] = user_info
                post_data['group_id'] = item.group_id
                post_data['meta_data'] = item.meta_data
                post_data['location'] = item.location
                post_data['description'] = item.description
                post_data['expire_on'] = item.expire_on
                post_data['save_later'] = item.save_later
                result.append(post_data)
            return success('SUCCESS', result, meta={'message': 'save later posts',
                                                    'page_info': {'current_page': page, 'limit': per_page,
                                                                  'total_record': total_records,
                                                                  'total_pages': total_pages}})
        else:
            return success('SUCCESS', meta={'message': 'no data found'})
    else:
        return success('SUCCESS', meta={'message': 'invalid user'})


def betting_details(current_user, post_id):
    existing_user = Users.query.filter_by(id=current_user.id, user_deleted_at=None,deleted_at=None).first()
    if existing_user:
        exist_post = Post.query.filter_by(id=post_id, deleted_at=None,status='active').first()
        if exist_post:
            betting_data = BettingPost.query.filter_by(post_id=post_id, deleted_at=None).first()
            if betting_data:
                comments = Comment.query.filter_by(post_id=post_id, deleted_at=None).count()
                likes = PostReact.query.filter_by(post_id=post_id, deleted_at=None).count()
                details = {}
                details['id'] = exist_post.id
                details['type'] = exist_post.type
                details['created_at'] = exist_post.created_at
                details['description'] = exist_post.description
                details['title'] = exist_post.title
                details['visibility'] = exist_post.visibility
                details['expire_on'] = exist_post.expire_on
                details['share_url'] = exist_post.share_link
                details['comments'] = comments
                details['likes'] = likes
                is_liked = PostReact.query.filter_by(user_id=current_user.id, post_id=post_id, is_liked=True,
                                                     deleted_at=None).first()
                if is_liked:
                    details['is_liked'] = True
                else:
                    details['is_liked'] = False

                if betting_data.results:
                    details['result'] = betting_data.results
                else:
                    details['result'] = None

                users = UserBettings.query.filter_by(post_id=post_id, deleted_at=None).all()
                if users:
                    members = []
                    for user in users:
                        user_data = Users.query.filter_by(id=user.user_id, deleted_at=None,user_deleted_at=None).first()
                        betting_status = UserBettings.query.filter_by(post_id=post_id, user_id=user.user_id,
                                                                      deleted_at=None).first()
                        if user_data:
                            users_list = {}
                            users_list['id'] = user_data.id
                            users_list['name'] = user_data.first_name
                            users_list['email'] = user_data.email
                            users_list['profile_image'] = user_data.profile_image
                            users_list['betting_status'] = betting_status.betting_status
                            members.append(users_list)
                        else:
                            # return success('SUCCESS', meta={'message': 'user not found'})
                            pass
                    details['members'] = members
                else:
                    return success('SUCCESS', meta={'message': 'data not found'})
                # details['expire_on'] = exist_post.expire_on.strftime("%Y-%m-%d %H:%M")
                details['location'] = exist_post.location
                details['meta_data'] = exist_post.meta_data
                post_owner = Users.query.filter_by(id=exist_post.user_id, deleted_at=None,user_deleted_at=None).first()
                user_info = {}
                user_info['id'] = post_owner.id
                user_info['name'] = post_owner.first_name
                user_info['email'] = post_owner.email
                user_info['phone'] = post_owner.phone
                user_info['can_follows'] = post_owner.can_follows
                user_info['business_account'] = post_owner.business_account
                user_info['profile_image'] = post_owner.profile_image
                details['user_info'] = user_info

                return success('SUCCESS', details, meta={'message': 'betting details'})
            else:
                return success('SUCCESS', meta={'message': 'invalid betting post'})
        else:
            return success('SUCCESS', meta={'message': 'invalid post'})
    else:
        return success('SUCCESS', meta={'message': 'invalid user'})


def check_expiry(current_user, post_id):
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        exist_post = Post.query.filter_by(id=post_id, deleted_at=None,status='active').first()
        if exist_post:
            post_data = BettingPost.query.filter_by(post_id=post_id, deleted_at=None).first()
            if post_data:
                expire_date = post_data.expire_on
                if expire_date:
                    current_date = datetime.date.today()
                    if expire_date <= current_date:
                        return success('SUCCESS', meta={'message': 'please update the betting result'})
                    else:
                        return success('SUCCESS', meta={'message': 'valid expire date'})
                else:
                    return success('SUCCESS', meta={'message': 'no expire date'})
            else:
                return success('SUCCESS', meta={'message': 'invalid betting post'})
        else:
            return success('SUCCESS', meta={'message': 'invalid post'})
    else:
        return success('SUCCESS', meta={'message': 'invalid user'})



def post_list(current_user, user_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    existing_user = Users.query.filter_by(id=user_id, deleted_at=None, user_deleted_at=None).first()
    result = []
    if existing_user.id == current_user.id:
        post_list = Post.query.filter_by(user_id=existing_user.id, status='active', deleted_at=None,
                                         group_id=None).order_by(
            Post.created_at.desc()).all()
        get_list = Post.query.filter_by(user_id=existing_user.id, status='active', deleted_at=None,
                                        group_id=None).order_by(Post.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False)

        total_records = len(post_list)
        get_list = get_list.items
        total_pages = total_records // per_page + 1
        for data in get_list:
            user_info = get_user_profile_details(data.user_id)
            get_post_list = {}
            get_post_list['id'] = data.id
            get_post_list['location'] = data.location
            get_post_list['title'] = data.title
            get_post_list['description'] = data.description
            get_post_list['created_at'] = data.created_at
            get_post_list['visibility'] = data.visibility
            get_post_list['type'] = data.type

            if data.type == 'record_activity':
                get_post_list['meta_data'] = data.meta_data
            if data.type == 'watch_activity':
                get_post_list['meta_data'] = data.meta_data
            if data.type == 'regular':
                get_post_list['meta_data'] = data.meta_data
            if data.type == 'activity':
                activity_id = data.meta_data['activity']['activity_id']
                activity_data = MasterActivity.query.filter_by(id=activity_id, deleted_at=None).first()
                if activity_data:
                    activity_meta_data = data.meta_data
                    activity_meta_data['activity']['activity_name'] = activity_data.name
                    activity_meta_data['activity']['activity_logo'] = activity_data.logo
                    get_post_list['meta_data'] = activity_meta_data
            if data.type == 'betting':
                activity_meta_data = data.meta_data
                if activity_meta_data:
                    get_post_list['meta_data'] = activity_meta_data
                is_accepted = UserBettings.query.filter(UserBettings.user_id == user_id,
                                                        UserBettings.post_id == data.id,
                                                        UserBettings.deleted_at == None,
                                                        UserBettings.betting_status == 'confirmed').first()
                if is_accepted:
                    get_post_list['is_accepted'] = True
                else:
                    get_post_list['is_accepted'] = False
                if data.expire_on:
                    get_post_list['expire_on'] = data.expire_on
                member = UserBettings.query.filter_by(post_id=data.id, user_id=user_id, deleted_at=None).first()
                if member:
                    get_post_list['betting_status'] = member.betting_status

            # get_post_list['meta_data'] = data.meta_data
            get_post_list['expire_on'] = data.expire_on
            get_post_list['share_url'] = data.share_link
            get_post_list['user_info'] = user_info

            like_count = PostReact.query.filter(PostReact.post_id == data.id, PostReact.type == 'like',
                                                PostReact.is_liked == True).count()
            comment_count = Comment.query.filter(Comment.post_id == data.id, Comment.deleted_at == None).count()
            is_reacted = PostReact.query.filter(PostReact.user_id == current_user.id, PostReact.post_id == data.id,
                                                PostReact.deleted_at == None).first()

            if like_count >= 0:
                get_post_list['likes'] = like_count
            if comment_count >= 0:
                get_post_list['comments'] = comment_count
            if is_reacted is not None:
                get_post_list['is_liked'] = is_reacted.is_liked
            else:
                get_post_list['is_liked'] = False

            result.append(get_post_list)
        return success('SUCCESS', result, meta={'message': 'Get Post List',
                                                'page_info': {'current_page': page, 'limit': per_page,
                                                              'total_record': total_records,
                                                              'total_pages': total_pages}})
    else:
        filter_visibility = {'friends', 'all'}
        if existing_user:
            my_friend = Contact.query.filter_by(user_id=current_user.id, contact_id=user_id, friend_status='friends',
                                                deleted_at=None).all()
            if my_friend:

                post_list = db.session.query(Post).filter(Post.user_id == user_id, Post.status == 'active',
                                                          Post.visibility.in_(filter_visibility),
                                                          Post.deleted_at == None, Post.group_id == None).order_by(
                    Post.created_at.desc()).all()
                get_list = db.session.query(Post).filter(Post.user_id == user_id, Post.status == 'active',
                                                         Post.visibility.in_(filter_visibility)
                                                         , Post.deleted_at == None, Post.group_id == None).order_by(
                    Post.created_at.desc()).paginate(
                    page=page,
                    per_page=per_page,
                    error_out=False)

                total_records = len(post_list)
                get_list = get_list.items
                total_pages = total_records // per_page + 1
                for data in get_list:
                    like_count = PostReact.query.filter(PostReact.post_id == data.id, PostReact.type == 'like',
                                                        PostReact.is_liked == True).count()
                    comment_count = Comment.query.filter(Comment.post_id == data.id, Comment.deleted_at == None).count()
                    is_reacted = PostReact.query.filter(PostReact.user_id == user_id,
                                                        PostReact.post_id == data.id,
                                                        PostReact.deleted_at == None).first()

                    user_data = Users.query.filter_by(id=data.user_id, deleted_at=None, user_deleted_at=None).first()
                    if user_data:
                        user_info = get_user_profile_details(data.user_id)
                        get_post_list = {}
                        get_post_list['id'] = data.id
                        get_post_list['location'] = data.location
                        get_post_list['title'] = data.title
                        get_post_list['description'] = data.description
                        get_post_list['created_at'] = data.created_at
                        get_post_list['visibility'] = data.visibility
                        get_post_list['type'] = data.type

                        if data.type == 'record_activity':
                            get_post_list['meta_data'] = data.meta_data
                        if data.type == 'watch_activity':
                            get_post_list['meta_data'] = data.meta_data
                        if data.type == 'regular':
                            get_post_list['meta_data'] = data.meta_data
                        if data.type == 'activity':
                            activity_id = data.meta_data['activity']['activity_id']
                            activity_data = MasterActivity.query.filter_by(id=activity_id, deleted_at=None).first()
                            if activity_data:
                                activity_meta_data = data.meta_data
                                activity_meta_data['activity']['activity_name'] = activity_data.name
                                activity_meta_data['activity']['activity_logo'] = activity_data.logo
                                get_post_list['meta_data'] = activity_meta_data
                        if data.type == 'betting':
                            activity_meta_data = data.meta_data
                            if activity_meta_data:
                                get_post_list['meta_data'] = activity_meta_data
                            is_accepted = UserBettings.query.filter(UserBettings.user_id == user_id,
                                                                    UserBettings.post_id == data.id,
                                                                    UserBettings.deleted_at == None,
                                                                    UserBettings.betting_status == 'confirmed').first()
                            if is_accepted:
                                get_post_list['is_accepted'] = True
                            else:
                                get_post_list['is_accepted'] = False
                            if data.expire_on:
                                get_post_list['expire_on'] = data.expire_on

                            member = UserBettings.query.filter_by(post_id=data.id, user_id=user_id,
                                                                  deleted_at=None).first()
                            if member:
                                get_post_list['betting_status'] = member.betting_status

                        get_post_list['meta_data'] = data.meta_data
                        get_post_list['expire_on'] = data.expire_on
                        get_post_list['share_url'] = data.share_link
                        get_post_list['user_info'] = user_info
                        if like_count >= 0:
                            get_post_list['likes'] = like_count
                        if comment_count >= 0:
                            get_post_list['comments'] = comment_count
                        if is_reacted is not None:
                            get_post_list['is_liked'] = is_reacted.is_liked
                        else:
                            get_post_list['is_liked'] = False
                        result.append(get_post_list)
                return success('SUCCESS', result, meta={'message': 'Get Post List',
                                                        'page_info': {'current_page': page, 'limit': per_page,
                                                                      'total_record': total_records,
                                                                      'total_pages': total_pages}})

            else:
                post_list = db.session.query(Post).filter(Post.user_id == user_id, Post.status == 'active',
                                                          Post.visibility == 'all', Post.deleted_at == None,
                                                          Post.group_id == None).order_by(Post.created_at.desc()).all()
                get_list = db.session.query(Post).filter(Post.user_id == user_id, Post.status == 'active',
                                                         Post.visibility == 'all'
                                                         , Post.deleted_at == None, Post.group_id == None).order_by(
                    Post.created_at.desc()).paginate(
                    page=page,
                    per_page=per_page,
                    error_out=False)

                total_records = len(post_list)
                get_list = get_list.items
                total_pages = total_records // per_page + 1
                for data in get_list:
                    like_count = PostReact.query.filter(PostReact.post_id == data.id, PostReact.type == 'like',
                                                        PostReact.is_liked == True).count()
                    comment_count = Comment.query.filter(Comment.post_id == data.id, Comment.deleted_at == None).count()
                    is_reacted = PostReact.query.filter(PostReact.user_id == user_id,
                                                        PostReact.post_id == data.id,
                                                        PostReact.deleted_at == None).first()
                    user_data = Users.query.filter_by(id=data.user_id, deleted_at=None, user_deleted_at=None).first()
                    if user_data:
                        user_info = get_user_profile_details(data.user_id)
                        get_post_list = {}
                        get_post_list['id'] = data.id
                        get_post_list['location'] = data.location
                        get_post_list['title'] = data.title
                        get_post_list['description'] = data.description
                        get_post_list['created_at'] = data.created_at
                        get_post_list['visibility'] = data.visibility
                        get_post_list['type'] = data.type

                        if data.type == 'record_activity':
                            get_post_list['meta_data'] = data.meta_data
                        if data.type == 'watch_activity':
                            get_post_list['meta_data'] = data.meta_data
                        if data.type == 'regular':
                            get_post_list['meta_data'] = data.meta_data
                        if data.type == 'activity':
                            activity_id = data.meta_data['activity']['activity_id']
                            activity_data = MasterActivity.query.filter_by(id=activity_id, deleted_at=None).first()
                            if activity_data:
                                activity_meta_data = data.meta_data
                                activity_meta_data['activity']['activity_name'] = activity_data.name
                                activity_meta_data['activity']['activity_logo'] = activity_data.logo
                                get_post_list['meta_data'] = activity_meta_data
                        if data.type == 'betting':
                            activity_meta_data = data.meta_data
                            if activity_meta_data:
                                get_post_list['meta_data'] = activity_meta_data
                            is_accepted = UserBettings.query.filter(UserBettings.user_id == user_id,
                                                                    UserBettings.post_id == data.id,
                                                                    UserBettings.deleted_at == None,
                                                                    UserBettings.betting_status == 'confirmed').first()
                            if is_accepted:
                                get_post_list['is_accepted'] = True
                            else:
                                get_post_list['is_accepted'] = False
                            if data.expire_on:
                                get_post_list['expire_on'] = data.expire_on

                            member = UserBettings.query.filter_by(post_id=data.id, user_id=user_id,
                                                                  deleted_at=None).first()
                            if member:
                                get_post_list['betting_status'] = member.betting_status

                        get_post_list['meta_data'] = data.meta_data
                        get_post_list['expire_on'] = data.expire_on
                        get_post_list['share_url'] = data.share_link
                        get_post_list['user_info'] = user_info
                        if like_count >= 0:
                            get_post_list['likes'] = like_count
                        if comment_count >= 0:
                            get_post_list['comments'] = comment_count
                        if is_reacted is not None:
                            get_post_list['is_liked'] = is_reacted.is_liked
                        else:
                            get_post_list['is_liked'] = False
                        result.append(get_post_list)
                return success('SUCCESS', result, meta={'message': 'Get Post List',
                                                        'page_info': {'current_page': page, 'limit': per_page,
                                                                      'total_record': total_records,
                                                                      'total_pages': total_pages}})

        else:
            return success('SUCCESS', meta={'message': 'user id is not found'})


def set_default_visibility(current_user, data):
    post_visibility= data.get('post_visibility', None)
    existing_user=Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        member_ship=Membership.query.filter_by(user_id=existing_user.id, deleted_at=None).first()
        if member_ship:
            if post_visibility in ["all","friends", "private", "custom", "group", "followers"]:
                member_ship.post_visibility = post_visibility
                update_item(member_ship)
                return success('SUCCESS', meta={'message' : 'visibility status is updated'})
            else:
                return success('SUCCESS', meta={'message': 'Invalid Data'})
        else:
            return success('SUCCESS', meta={'message':'User Not Registered!'})
    else:
        return success('SUCCESS',meta={'message' : 'User Not Found!'})


def post_detail_list(current_user, post_id):
    existing_post = Post.query.filter_by(id=post_id,status='active',deleted_at=None).all()
    if existing_post:
        result=[]
        for data in existing_post:
            user_data = Users.query.filter_by(id=data.user_id, deleted_at=None,user_deleted_at=None).first()
            if user_data:
                user_info = get_user_profile_details(data.user_id)
                like_count = PostReact.query.filter(PostReact.post_id == post_id, PostReact.type == 'like',
                                                    PostReact.is_liked == True).count()
                comment_count = Comment.query.filter(Comment.post_id == post_id,
                                                     Comment.deleted_at == None).count()
                is_reacted = PostReact.query.filter( PostReact.post_id == post_id,
                                                    PostReact.deleted_at == None).first()
                get_post_list = {}
                get_post_list['id'] = data.id
                get_post_list['location'] = data.location
                get_post_list['title'] = data.title
                get_post_list['description'] = data.description
                get_post_list['created_at'] = data.created_at
                get_post_list['visibility'] = data.visibility
                get_post_list['type'] = data.type
                get_post_list['meta_data'] = data.meta_data
                get_post_list['expire_on'] = data.expire_on
                get_post_list['share_url'] = data.share_link
                get_post_list['user_info'] = user_info
                if like_count >= 0:
                    get_post_list['likes'] = like_count
                if comment_count >= 0:
                    get_post_list['comments'] = comment_count
                if is_reacted is not None:
                    get_post_list['is_liked'] = is_reacted.is_liked
                else:
                    get_post_list['is_liked'] = False
                result.append(get_post_list)
        return success('SUCCESS', result, meta={'message':'Post Details'})
    else:
        return success('SUCCESS', meta={'message':'post id does not exit'})


def share_dynamic_link(post_id):
    post_details = Post.query.filter_by(id=post_id, deleted_at=None,status='active').first()
    screen_type = ''
    if post_details:
        if post_details.type == 'betting':
            screen_type = 'BETTING_POST'
        if post_details.type == 'regular':
            screen_type = 'REGULAR_POST'
        if post_details.type == 'activity':
            screen_type = 'ACTIVITY_POST'
        if post_details.type == 'watch_activity':
            screen_type = 'WATCH_ACTIVITY_POST'
        if post_details.type == 'record_activity':
            screen_type = 'RECORD_ACTIVITY_POST'
        url = FIREBASE_DYNAMIC_LINK_URL
        encoded_string = urllib.parse.quote_plus(DEEP_LINK_URL + '?post_id=' + str(post_id) + '&screen_type=' + screen_type)

        # encoded_string = unquote(DEEP_LINK_PREFIX + '/?link=' + DEEP_LINK_URL + '?post_id=' + str(post_id) + '&screen_type=' + screen_type)
        # encoded_string = urllib.request.pathname2url(DEEP_LINK_URL + '?post_id=' + str(post_id) + '&screen_type=' + screen_type)

        payload = {}
        payload['longDynamicLink'] = DEEP_LINK_PREFIX + '/?link=' + encoded_string + '&apn=' + ANDROID_PACKAGE_NAME + '&ibi=' + IOS_BUNDLE_ID
        payload['suffix'] = {"option": "SHORT"}
        payload = json.dumps(payload)

        headers = {'Content-Type': 'application/json'}

        response = requests.request("POST", url, headers=headers, data=payload)

        return response.json()['shortLink']
    else:
        return success("SUCCESS", meta={'message': 'invalid post'})

# to add intermediate post
def add_intermediate_post(user_id, viewed_post_list, count=3):
    try:
        user_data = Users.query.filter_by(id=user_id,deleted_at=None,user_deleted_at=None).first()
        post_list = []
        if user_data is not None:
            if user_data.phone_code == 91:
                user_bucket = ['india_adrenln', 'india_sport', 'india_general']
            else:
                user_bucket = ['international_adrenln', 'international_sport', 'international_general']
            if user_data.can_follows or user_data.business_account:
                user_bucket.append('bussiness_influencer')
            for bucket in user_bucket:
                query = """SELECT p.id, ap.id as admin_post_id FROM admin_post ap
                                LEFT JOIN post p ON p.id = ap.post_id
                                LEFT JOIN post_bucket_mapping pbm ON p.id = pbm.post_id
                                WHERE p.deleted_at IS NULL AND ap.deleted_at IS NULL AND p.status='active' AND pbm.type = 'bucket' AND p.visibility IN ('all', 'admin')"""
                if len(viewed_post_list) > 0:
                    viewed_post_tuple = tuple(viewed_post_list)
                    if len(viewed_post_list) == 1:
                        viewed_post_tuple = ''.join(map(str, viewed_post_tuple))
                        viewed_post_tuple=tuple(map(int,viewed_post_tuple.split(', ')))
                    query = query + """ AND
                                ap.post_id NOT IN {viewed_post}""".format(viewed_post=viewed_post_tuple)
                today = datetime.datetime.today().strftime('%Y-%m-%d')
                query = query + """ AND ap.publisher_status IS true AND pbm.key = '{user_bucket}' AND 
                                    (ap.expiry_date >= '{date}' OR ap.expiry_date IS NULL) order by 
                                    ap.expiry_date DESC NULLS LAST, ap.is_priority desc, ap.s_id ASC""".format(date=today, user_bucket=bucket)
                if bucket.endswith('_general'):
                    query = query + " LIMIT " + str(3 - len(post_list))
                else:
                    query = query + " LIMIT 1"
                data = _query_execution(query)
                for each in data:
                    post_list.append(str(each['id']))
            query = """SELECT p.id, ap.id as admin_post_id FROM admin_post ap
                                INNER JOIN post p ON p.id = ap.post_id
                                INNER JOIN post_bucket_mapping pbm ON p.id = pbm.post_id
                                WHERE p.deleted_at IS NULL AND pbm.type = 'email' AND p.visibility IN ('all', 'admin') 
                                AND ap.publisher_status IS true AND ap.deleted_at IS NULL  AND p.status='active' AND pbm.category_value = '{user_id}'""".format(user_id=user_id)
            if len(viewed_post_list) > 0:
                viewed_post_tuple = tuple(viewed_post_list)
                if len(viewed_post_list) == 1:
                    viewed_post_tuple = ''.join(map(str, viewed_post_tuple))
                    viewed_post_tuple = tuple(map(int, viewed_post_tuple.split(', ')))
                query = query + """ AND
                            ap.post_id NOT IN {viewed_post}""".format(viewed_post=viewed_post_tuple)
            query = query + """AND (ap.expiry_date >= '{date}' OR ap.expiry_date IS NULL) order by 
                                ap.expiry_date DESC NULLS LAST, ap.is_priority DESC, ap.s_id ASC limit 1""".format(date=today)
            data = _query_execution(query)
            for each in data:
                post_list.append(str(each['id']))
            # add state posts
            # query = """SELECT p.id, ap.id as admin_post_id FROM admin_post ap
            #                     INNER JOIN post p ON p.id = ap.post_id
            #                     INNER JOIN post_bucket_mapping pbm ON p.id = pbm.post_id
            #                     WHERE p.deleted_at IS NULL AND pbm.type = 'state' AND p.visibility IN ('all', 'admin')
            #                     AND ap.publisher_status IS true AND pbm.category_value = '{state}'""".format(state=user_data.state)
            # if len(viewed_post_list) > 0:
            #     viewed_post_tuple = tuple(viewed_post_list)
            #     query = query + """ AND
            #                 ap.post_id NOT IN {viewed_post}""".format(viewed_post=viewed_post_tuple)
            # query = query +  """AND (ap.expiry_date >= '{date}' OR ap.expiry_date IS NULL) order by
            #                     ap.expiry_date DESC NULLS LAST, ap.is_priority desc, p.created_at DESC limit 1""".format(date=today)
            # data = _query_execution(query)
            # for each in data:
            #     post_list.append(str(each['id']))
            time_line = UserIntermediateRepository.get_one_by_user_id(user_id)
            if time_line is not None:
                UserIntermediateRepository.update(time_line, {'post_sequence': post_list, 'is_dumped': False})
            else:
                UserIntermediateRepository.create({'user_id': user_id, 'post_sequence': post_list, 'is_dumped': False})
        return success('Success', post_list)
    except Exception as err:
        return failure(str(err))


def create_post_v2(data, current_user):
    fcm_token = []
    expire_on = data.get('expire_on', None)
    promotion = data.get('promotion',None)
    type = data.get('type', None)
    post_visibility = data.get('visibility', None)
    meta_data = data.get('meta_data', None)
    input_location = data.get('location', None)
    tagged_users = data.get('tagged_users', None)
    group_id = data.get('group_id', None)
    if type not in ['regular', 'activity', 'betting', 'result', 'watch_activity', 'record_activity']:
        return success('SUCCESS', meta={'message': 'Invalid post type'})

    if type == "betting" and "betting" in meta_data:
        betting_fields = meta_data['betting']
        members = betting_fields.get("members", [])
        # if int(betting_fields["oods"]) != len(members):
        #     return failure('FAILURE', {'message': "Selected members are not matching"})

    location = {"city": None, "state": None}
    if input_location:
        location["city"] = input_location.get('city', None)
        location["state"] = input_location.get('state', None)
    post = Post(title=data.get('title', None), description=data.get('description', None),
                visibility=data.get('visibility', None), type=type,
                user_id=current_user.id, location=location, group_id=data.get('group_id', None))
    post = add_item(post)

    if promotion == True:
        post.visibility = 'all'
        post.promotion = True
        update_item(post)

    # add share_link
    # share_link = share_dynamic_link(post.id)
    # post.share_link = share_link
    update_item(post)

    if type == 'betting' or type == 'result':
        post.is_tag = False
        update_item(post)

    timeline = UserTimeLineRepository.get_one_by_user_id(str(current_user.id))
    if timeline:
    # if timeline and timeline.index :
        index = timeline.index + 1
        timeline_data = timeline.post_sequence
        UserTimeLineRepository.update(timeline, [str(post.id)] + timeline_data, index)
    else:
        UserTimeLineRepository.create({'user_id': str(current_user.id), 'post_sequence': [str(post.id)],'index':1})

    if expire_on:
        post.expire_on = expire_on
        update_item(post)

    if type == 'activity' and meta_data and 'activity' in meta_data:
        activity_meta_data = prepare_activity_v2(activities=meta_data['activity'])
        meta_data['activity'] = activity_meta_data

    if type == 'watch_activity' and meta_data and 'activity' in meta_data:
        meta_data = meta_data

    if type == 'record_activity' and meta_data and 'activity' in meta_data:
        record_meta_data = prepare_record(post=post, record_fields=meta_data['activity'])
        meta_data['activity'] = record_meta_data

    elif type == 'betting':
        tagged_users = None
        # meta_data['betting']['expire_on'] = data.get('expire_on', None)
        betting_meta_data = prepare_betting_v2(post=post, betting_fields=meta_data['betting'])
        meta_data['betting'] = betting_meta_data
        # primary_team = meta_data['betting']['primary_team']
        betting_post = BettingPost(user_id=current_user.id, primary_team=meta_data['betting']['primary_team'],
                                   secondary_team=meta_data['betting']['secondary_team'], post_id=post.id,
                                   expire_on=expire_on)
        add_item(betting_post)

        betting_fields = meta_data['betting']
        members = betting_fields.get("members", [])
        for member in members:
            user_betting = UserBettings(user_id=member, post_id=post.id, betting_status='invited',
                                        result_status='')
            add_item(user_betting)
            user_membership = Membership.query.filter_by(user_id=member, deleted_at=None).first()
            fcm_token.append(user_membership.fcm_token)

        # send notification
        user_data = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
        message = "Betting invite from " + user_data.first_name
        queue_url = PUSH_NOTIFICATION_URL
        payload = {}
        payload['id'] = str(post.id)
        payload['current_user'] = str(current_user.id)
        payload['message'] = message
        payload['title'] = "Betting Invite"
        payload['fcm_token'] = fcm_token
        payload['screen_type'] = 'BETTING_DETAIL'
        payload['responder_id'] = None
        # send_queue_message(queue_url, payload)
        # post in-app notification
        screen_info = {}
        data = {}
        screen_info['screen_type'] = 'BETTING_DETAIL'
        screen_info['id'] = str(post.id)
        data['meta_data'] = screen_info
        for user in members:
            add_notification = Notification(user_id=user, type='post', title=payload['title'],
                                            description=message, read_status=False, meta_data=data['meta_data'],c_user=current_user.id)
            add_item(add_notification)

    # tagging users
    if type == 'regular' or type == 'activity' or type == 'watch_activity' or type == 'record_activity':
        if tagged_users:
            post.is_tag = True
            update_item(post)
            for user in tagged_users:
                custom_visibility = PostCustomVisibility(post_id=post.id, user_id=user, tag=True)
                add_item(custom_visibility)
        else:
            post.is_tag = False
            update_item(post)

    if post_visibility == "custom":
        betting_data = meta_data['betting']
        visible_to_users = betting_data.get("members", [])
        if visible_to_users:
            for user in visible_to_users:
                custom_visibility = PostCustomVisibility(post_id=post.id, user_id=user, tag=False)
                add_item(custom_visibility)
        else:
            return success('SUCCESS', meta={"please add members"})

    if post and meta_data:
        post.meta_data = meta_data
        update_item(post)
    if tagged_users:
        users_tagged = tagged_users
    else:
        users_tagged = None
    # from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
    # if group_id:
    #     sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
    #                        aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
    #     response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL,
    #                                 MessageBody=json.dumps({'group_id': str(group_id), 'post_id': str(post.id)})
    #                                 )
    # else:
    #     sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
    #                        aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
    #     response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL,
    #                                 MessageBody=json.dumps({'tagged_users': users_tagged, 'post_id': str(post.id)})
    #                                 )
    # queue_url = PUSH_NOTIFICATION_URL

    screen_type = ''
    if post.type == 'regular':
        screen_type = 'REGULAR_POST'
    if post.type == 'activity':
        screen_type = 'ACTIVITY_POST'
    if post.type == 'betting':
        screen_type = 'BETTING_POST'
    if post.type == 'watch_activity':
        screen_type = 'WATCH_ACTIVITY_POST'
    if post.type == 'betting_result':
        screen_type = 'BETTING_RESULT'
    if post.type == 'record_activity':
        screen_type = 'RECORD_ACTIVITY_POST'

    payload_data = {}
    if group_id:
        payload_data['group_id'] = str(group_id)
    payload_data['id'] = str(post.id)
    payload_data['current_user'] = str(current_user.id)
    payload_data['post_owner'] = str(current_user.first_name)
    payload_data['tagged_users'] = tagged_users
    payload_data['visibility'] = post_visibility
    payload_data['group_id'] = group_id
    payload_data['message'] = None
    payload_data['title'] = 'Post'
    payload_data['fcm_token'] = None
    payload_data['screen_type'] = screen_type
    payload_data['responder_id'] = None
    # send_queue_message(queue_url, payload_data)

    return success('SUCCESS', meta={'message': 'Post created successfully'})


def prepare_betting_v2(post, betting_fields):
    final_betting_fields = {}
    final_betting_fields["primary_team"] = betting_fields["primary_team"]
    final_betting_fields["secondary_team"] = betting_fields["secondary_team"]
    final_betting_fields["item_description"] = betting_fields.get("item_description")
    final_betting_fields["prediction_description"] = betting_fields.get("prediction_description")
    final_betting_fields["result"] = None
    members = betting_fields.get("members", [])
    final_betting_fields["members"] = members
    return final_betting_fields


def betting_react_v2(current_user, data):
    post_id = data.get('post_id', None)
    betting_status = data.get('betting_status', None)
    if post_id and betting_status:
        user_bettings = UserBettings.query.filter_by(user_id=current_user.id, post_id=post_id).first()
        if user_bettings:
            if betting_status in ["accepted", "reject"] and user_bettings.betting_status == 'invited':
                if betting_status == 'accepted':
                    user_bettings.betting_status = 'confirmed'
                else:
                    user_bettings.betting_status = 'rejected'
                update_item(user_bettings)
                if betting_status =='accepted':
                    #send notification
                    message = current_user.first_name + " accepted your betting invite"
                    queue_url = PUSH_NOTIFICATION_URL
                    fcm_token = []
                    post_data = Post.query.filter_by(id=post_id, deleted_at=None,status='active').first()
                    post_owner = Users.query.filter_by(id=post_data.user_id, deleted_at=None,user_deleted_at=None).first()
                    user_membership = Membership.query.filter_by(user_id=post_owner.id, deleted_at=None).first()
                    fcm_token.append(user_membership.fcm_token)
                    payload = {}
                    payload['id'] = str(post_data.id)
                    payload['current_user'] = str(current_user.id)
                    payload['message'] = message
                    payload['title'] = "Betting Request"
                    payload['fcm_token'] = fcm_token
                    payload['screen_type'] = 'BETTING_DETAIL'
                    # payload['responder_id'] = str(current_user.id)
                    payload['responder_id'] = None
                    send_queue_message(queue_url, payload)

                    # post in-app notification
                    screen_info = {}
                    data = {}
                    screen_info['screen_type'] = 'BETTING_DETAIL'
                    screen_info['id'] = str(post_data.id)
                    # screen_info['responder_id'] = str(current_user.id)
                    screen_info['responder_id'] = None
                    data['meta_data'] = screen_info
                    add_notification = Notification(user_id=post_owner.id, type='post', title=payload['title'],
                                                    description=message, read_status=False,c_user=current_user.id,meta_data=data['meta_data'])
                    add_item(add_notification)

            else:
                return success('SUCCESS',meta={'message':'invalid_betting_react_status'})
        else:
            return success('SUCCESS', meta={'message':'Betting request not found'})
    else:
        return success('SUCCESS',meta={'message':'invalid data'})


def result_update_v2(current_user, data):
    post_id = data.get('post_id')
    results = data.get('result')
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        valid_post = Post.query.filter_by(id=post_id, user_id=current_user.id, deleted_at=None,status='active').first()
        if valid_post:
            my_betting_post = BettingPost.query.filter_by(user_id=current_user.id, post_id=post_id,
                                                          deleted_at=None, results=None).first()
            if my_betting_post:
                my_betting_post.results = results
                update_item(my_betting_post)
                create_result_post_v2(post_id, results)
                # create result post

                return success("SUCCESS", meta={"message": "Betting Result updated"})
            else:
                return success('SUCCESS', meta={'message': 'data not found'})
        else:
            return success('SUCCESS', meta={'message': 'invalid post'})
    else:
        return success('SUCCESS', meta={'message': 'invalid user'})


def create_result_post_v2(post_id, results):
    post_details = Post.query.filter_by(id=post_id, deleted_at=None,status='active').first()
    betting_details = BettingPost.query.filter_by(post_id=post_id, deleted_at=None).first()
    description = 'I won the Prediction'

    def send_notification(user_id,post_id):
        # send notification
        user_membership = Membership.query.filter_by(user_id=user_id, deleted_at=None).first()
        message = "Congratulations, You won the Prediction"
        queue_url = PUSH_NOTIFICATION_URL
        fcm_token = []
        fcm_token.append(user_membership.fcm_token)
        payload = {}
        payload['id'] = str(post_id)
        payload['user_id'] = str(user_id)
        payload['message'] = message
        payload['title'] = "Won the Bet"
        payload['fcm_token'] = fcm_token
        payload['screen_type'] = 'BETTING_RESULT'
        payload['responder_id'] = None
        send_queue_message(queue_url, payload)

        # post in-app notification
        screen_info = {}
        data = {}
        screen_info['screen_type'] = 'BETTING_RESULT'
        screen_info['id'] = str(post_id)
        data['meta_data'] = screen_info
        add_notification = Notification(user_id=user_id, type='post', title=payload['title'],
                                        description=message, read_status=False, meta_data=data['meta_data'],c_user=user_id)
        add_item(add_notification)

    if betting_details.primary_team == results:
        user_id = post_details.user_id
        post_result = Post(type='betting_result', visibility='friends', user_id=user_id,
                           location=post_details.location, description=description, meta_data=post_details.meta_data,
                           expire_on=betting_details.expire_on)
        res_post = add_item(post_result)
        ###
        timeline = UserTimeLineRepository.get_one_by_user_id(str(user_id))
        if timeline is not None:
            timeline_data = timeline.post_sequence
            UserTimeLineRepository.update(timeline, [str(res_post.id)] + timeline_data)
        else:
            UserTimeLineRepository.create({'user_id': str(user_id), 'post_sequence': [str(res_post.id)]})

        from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
        sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                           aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
        response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL, MessageBody=json.dumps({'post_id': str(res_post.id)})
                                    )
        #send notification
        send_notification(user_id, post_result.id)
        return success('SUCCESS', meta={'message': 'result post created'})
    elif betting_details.secondary_team == results:
        betting_members = UserBettings.query.filter_by(post_id=post_id, deleted_at=None,
                                                       betting_status='confirmed').all()
        for members in betting_members:
            post_result = Post(type='betting_result', visibility='friends', user_id=members.user_id,
                               location=post_details.location, description=description,
                               meta_data=post_details.meta_data,
                               expire_on=betting_details.expire_on)
            res_post = add_item(post_result)
            #####
            timeline = UserTimeLineRepository.get_one_by_user_id(str(members.user_id))
            if timeline is not None:
                timeline_data = timeline.post_sequence
                UserTimeLineRepository.update(timeline, [str(res_post.id)] + timeline_data)
            else:
                UserTimeLineRepository.create({'user_id': str(members.user_id), 'post_sequence': [str(res_post.id)]})

            from config import AWS_SQS_ACCESS_KEY_ID, AWS_REGION_NAME, AWS_SQS_SECRET_ACCESS_KEY
            sqs = boto3.client('sqs', region_name=AWS_REGION_NAME, aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                               aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY)
            response = sqs.send_message(QueueUrl=UPDATE_TIMELINE_URL,
                                        MessageBody=json.dumps({'post_id': str(res_post.id)})
                                        )
            # send notification
            send_notification(members.user_id,post_result.id)
        return success('SUCCESS', meta={'message': 'result post created'})
    else:
        return success('SUCCESS', meta={'message': 'invalid result'})


def user_location(data,current_user):
    geolocator = Nominatim(user_agent='MyApp')
    lat = data.get('latitude', None)
    lon = data.get('longitude', None)
    if lat and lon:
        coordinates = lat, lon
        location = geolocator.reverse(coordinates)
        address = location.raw['address']

        city = address.get('city', '')
        state = address.get('state', '')
        country = address.get('country', '')
        if city and state and country:
            result = {}
            result['address'] = address
            result['city'] = city
            result['state'] = state
            result['country'] = country
            return success('SUCCESS', result, meta={'message': 'User Location'})
        else:
            return success('SUCCESS', meta={'message': 'No data found'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid inputs'})


def user_likes_list(current_user,post_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    post_react=PostReact.query.filter_by(post_id=post_id,is_liked=True,deleted_at=None).all()
    post_react_list=PostReact.query.filter_by(post_id=post_id,is_liked=True,deleted_at=None).order_by(PostReact.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    post_react_list = post_react_list.items
    total_records = len(post_react)
    total_pages = total_records // per_page + 1
    result=[]
    if post_react_list:
        for data in post_react_list:
            # post_data = Post.query.filter_by(id=data.post_id, deleted_at=None).first()
            user_data = Users.query.filter_by(id=data.user_id, deleted_at=None,user_deleted_at=None).first()
            following = Contact.query.filter_by(user_id=current_user.id,contact_id=data.user_id,deleted_at=None).first()
            if user_data:
                user_info = get_user_profile_details(user_data.id)
                list={}
                list['post_id']=data.post_id
                list['is_liked']=data.is_liked
                if following and following.is_following==True:
                    list['is_following'] = True
                else:
                    list['is_following'] = False
                if following and following.friend_status == 'friends':
                    list['friend_status'] = True
                else:
                    list['friend_status'] = False
                list['user_info']=user_info
                result.append(list)
        return success('SUCCESS',result, meta={'message': 'Get Post List',
                                                        'page_info': {'current_page': page, 'limit': per_page,
                                                                      'total_record': total_records,
                                                                      'total_pages': total_pages}})
    else:
        return success('SUCCESS',meta={'message':'invalid post'})


def reported_posts(current_user,data):
    post_id = data.get('post_id')
    existing_user=Users.query.filter_by(id=current_user.id,deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        posts=Post.query.filter_by(id=post_id,deleted_at=None).first()
        if posts:
            list_reported_post=ReportedPost(user_id=existing_user.id,post_id=post_id)
            add_item(list_reported_post)
            return success('SUCCESS', meta={'message':'Post is reported'})
        else:
            return success('SUCCESS',meta={'message':'Invalid Post_id'})
    else:
        return success('SUCCESS',meta={'message':'Invalid User'})


