import datetime
from operator import or_

import firebase_admin
from firebase_admin import messaging,credentials
from flask import jsonify, request

from api.Group.models import Group, GroupMembers
from api.Post.models import Post, PostReact
from api.Users.models import Users, Membership
from api.Users.services import get_user_profile_details
from api.comment.models import Comment
from api.contact.models import Contact, UserTopics
from api.notification.models import Notification
from api.notification.services import send_queue_message
from app import db
from common.connection import add_item, update_item, delete_item, _query_execution
from common.response import failure, success
from config import PUSH_NOTIFICATION_URL


def sendrequest(data, current_user):
    request_to = data.get('user_id')
    if request_to == current_user.id:
        return success('SUCCESS',meta={'message':'Invalid User'})
    def send_notification():
        # send notification
        user_membership = Membership.query.filter_by(user_id=request_to, deleted_at=None).first()
        message = current_user.first_name + " has sent you a friend request"
        queue_url = PUSH_NOTIFICATION_URL
        fcm_token = []
        fcm_token.append(user_membership.fcm_token)
        payload = {}
        payload['id'] = None
        payload['current_user'] = str(current_user.id)
        payload['message'] = message
        payload['title'] = "Friend Request"
        payload['fcm_token'] = fcm_token
        payload['screen_type'] = 'ALL_FRIENDS'
        payload['responder_id'] = None
        send_queue_message(queue_url, payload)

        # post in-app notification
        screen_info = {}
        data = {}
        screen_info['screen_type'] = 'ALL_FRIENDS'
        screen_info['id'] = None
        data['meta_data'] = screen_info
        add_notification = Notification(user_id=request_to, type='friend', title=payload['title'],
                                        description=message, read_status=False,meta_data=data['meta_data'],c_user=current_user.id)
        add_item(add_notification)

    existing_users = Users.query.filter_by(id=current_user.id,deleted_at=None,user_deleted_at=None).first()
    users = Users.query.filter_by(id=request_to,deleted_at=None,user_deleted_at=None).first()
    if users:
        if users.can_follows == True:
            type = 'Influencer'
        else:
            type = 'Individual'
    if users and existing_users:
        status = Contact.query.filter_by(user_id=current_user.id, contact_id=request_to, deleted_at=None).first()
        is_request = Contact.query.filter_by(user_id=request_to, contact_id=current_user.id, deleted_at=None).first()
        if status:
            if status and status.friend_status == 'blocked':
                return success("SUCCESS",meta={"message":"Cannot send request to this user"})
            elif status and status.contact_id == current_user.id:
                return success("SUCCESS",meta={"message":"Cannot send request 1"})
            elif is_request and is_request.friend_status == 'blocked':
                return success("SUCCESS",meta={"message":"This user is in your blocklist ,Cannot send request"})
            elif status and status.friend_status == 'pending':
                return success("SUCCESS",meta={"message":"Request already Sent"})
            elif status and status.friend_status == 'friends':
                return success("SUCCESS", meta={"message": "You are already friend with this account"})
            else:
                status.friend_status = 'pending'
                update_item(status)
                send_notification()
                return success("SUCCESS", meta={"message": "Friend Request Sent"})
        elif is_request:
            if is_request.friend_status == 'blocked':
                return success("SUCCESS",meta={"message":"Cannot send request to this user"})
            elif is_request.contact_id == current_user.id:
                return success("SUCCESS",meta={"message":"Cannot send request 2"})
            elif is_request.friend_status == 'pending':
                return success('SUCCESS', meta={'message': 'Friend Request In Pending'})
            elif status.friend_status == 'friends':
                return success("SUCCESS", meta={"message": "You are already friend with this account"})
            else:
                return success('SUCCESS', meta={'message': 'Cannot Send Request 3'})
        else:
            send_request = Contact(user_id=current_user.id, contact_id=request_to, friend_status='pending', type=type)
            add_item(send_request)
            send_notification()
            return success("SUCCESS", meta={"message": "Friend Request Sent"})


def unsend_friend_request(current_user, data):
    users_id = data.get('user_id')
    existing_users = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    users = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_users and users:
        status = Contact.query.filter_by(user_id=current_user.id, contact_id=users_id, friend_status='pending',
                                         deleted_at=None).first()
        if status:
            status.friend_status = 'request_removed'
            update_item(status)
            return success('SUCCESS', meta={'message': 'Unsend Friend Request '})
        else:
            return success('SUCCESS', meta={'message': 'No Pending Requests'})


def request_sent(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    existing_users = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_users:
        all_sent_requests = Contact.query.filter_by(user_id=current_user.id, friend_status='pending',
                                                    deleted_at=None).all()
        sent_request = Contact.query.filter_by(user_id=current_user.id, friend_status='pending',
                                               deleted_at=None).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        sent_request = sent_request.items
        total_record = len(all_sent_requests)
        total_pages = total_record // per_page + 1
        result = []
        if sent_request:
            for user in sent_request:
                user_data = {}
                existing_user = Users.query.filter_by(id=user.contact_id,user_deleted_at=None,deleted_at=None).first()
                user_data['contact_id'] = user.contact_id
                user_data['created_on'] = user.following_on
                user_data['name'] = existing_user.first_name
                user_data['profile_image'] = existing_user.profile_image
                result.append(user_data)
            return success("SUCCESS", result, meta={'message': 'Friend Request Sent',
                                                    'page_info': {'total_record': total_record,
                                                                  'total_pages': total_pages,
                                                                  'limit': per_page}})
        else:
            return success("SUCCESS", result, meta={'message': 'No Requests Sent'})
    else:
        return success("SUCCESS", meta={'message': 'User Not Found'})


def request_list(current_user, data):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    existing_users = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_users:
        all_pending_requests = Contact.query.filter_by(user_id=current_user.id, friend_status='pending',
                                                       deleted_at=None).all()
        pending_request = Contact.query.filter_by(contact_id=current_user.id, friend_status='pending',
                                                  deleted_at=None).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        pending_request = pending_request.items
        total_record = len(all_pending_requests)
        total_pages = total_record // per_page + 1
        result = []
        if pending_request:
            for user in pending_request:
                user_data = {}
                existing_user = Users.query.filter_by(id=user.user_id,user_deleted_at=None,deleted_at=None).first()
                user_data['contact_id'] = user.user_id
                user_data['created_at'] = user.created_at
                user_data['name'] = existing_user.first_name
                user_data['profile_inage'] = existing_user.profile_image
                result.append(user_data)
            return success('SUCCESS', result, meta={'message': 'Friend Request List',
                                                    'page_info': {'total_record': total_record,
                                                                  'total_pages': total_pages,
                                                                  'limit': per_page}})
        else:
            return success('SUCCESS', result, meta={'message': 'No Friend Requests'})
    else:
        return success("SUCCESS", meta={'message': 'User Not Found'})


def friend_list(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    existing_users = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_users:
        all_contact = Contact.query.filter_by(user_id=current_user.id, friend_status='friends',
                                              deleted_at=None).all()
        is_contact = Contact.query.filter_by(user_id=current_user.id, friend_status='friends',
                                             deleted_at=None).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        is_contact = is_contact.items
        total_record = len(all_contact)
        total_pages = total_record // per_page + 1
        if is_contact:
            result = []
            for user in is_contact:
                user_data = {}
                existing_user = Users.query.filter_by(id=user.contact_id,user_deleted_at=None,deleted_at=None).first()
                if existing_user:
                    user_data['contact_id'] = user.contact_id
                    user_data['created_on'] = user.following_on
                    user_data['is_following'] = user.is_following
                    user_data['friend_status'] = user.friend_status
                    user_data['can_follows'] = existing_user.can_follows
                    user_data['name'] = existing_user.first_name
                    user_data['profile_image'] = existing_user.profile_image
                    result.append(user_data)
            return success('SUCCESS', result, meta={'message': 'Friend List',
                                                    'page_info': {'current_page': page, 'total_record': total_record,
                                                                  'total_pages': total_pages,
                                                                  'limit': per_page}})
        else:
            return success("SUCCESS", meta={'message': 'No Friends'})


def reqConfirm(current_user, data):
    user_id = data.get('user_id')
    def send_notification():
        # send notification
        user_membership = Membership.query.filter_by(user_id=user_id, deleted_at=None).first()
        message = current_user.first_name + " accepted your friend request"
        queue_url = PUSH_NOTIFICATION_URL
        fcm_token = []
        fcm_token.append(user_membership.fcm_token)
        payload = {}
        payload['id'] = None
        payload['current_user'] = str(current_user.id)
        payload['message'] = message
        payload['title'] = "Friend Request"
        payload['fcm_token'] = fcm_token
        payload['screen_type'] = 'ALL_FRIENDS'
        payload['responder_id'] = None
        send_queue_message(queue_url, payload)

        # post in-app notification
        screen_info = {}
        data = {}
        screen_info['screen_type'] = 'ALL_FRIENDS'
        screen_info['id'] = None
        data['meta_data'] = screen_info
        add_notification = Notification(user_id=user_id, type='friend', title=payload['title'],
                                        description=message, read_status=False, meta_data=data['meta_data'],c_user=current_user.id)
        add_item(add_notification)

    users = Users.query.filter_by(id=data.get('user_id'),user_deleted_at=None,deleted_at=None).first()
    existing_users = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if users.can_follows == True:
        type = 'Influencer'
    else:
        type = 'Individual'
    if existing_users and users:
        is_request = Contact.query.filter_by(contact_id=current_user.id, user_id=data.get('user_id'),
                                             friend_status='pending', deleted_at=None).first()
        if is_request and is_request.is_following == True:
            is_request.friend_status = 'friends'
            is_request.friend_since = datetime.datetime.now()
            update_item(is_request)
            send_notification()
            is_contact = Contact.query.filter_by(user_id=current_user.id, contact_id=data.get('user_id'),
                                                 deleted_at=None).first()
            if is_contact and is_contact.is_following == True:
                is_contact.friend_status = 'friends'
                is_contact.friend_since = datetime.datetime.now()
                update_item(is_contact)
                return success('SUCCESS', meta={'message': 'Friend Request Accepted'})
            elif is_contact and is_contact.is_following == False:
                is_contact.friend_status = 'friends'
                is_contact.friend_since = datetime.datetime.now()
                update_item(is_contact)
                return success('SUCCESS', meta={'message': 'Friend Request Accepted'})
            else:
                add_contact = Contact(user_id=current_user.id, contact_id=data.get('user_id'), type=type,
                                      friend_status='friends',
                                      friend_since=datetime.datetime.now()
                                     )

                add_item(add_contact)
            return success('SUCCESS', meta={'message': 'Friend Request Accepted'})
        elif is_request and is_request.is_following == False:
            is_request.friend_status = 'friends'
            is_request.friend_since = datetime.datetime.now()
            update_item(is_request)
            send_notification()
            is_contact = Contact.query.filter_by(user_id=current_user.id, contact_id=data.get('user_id'),
                                                 deleted_at=None).first()
            if is_contact and is_contact.is_following == True:
                is_contact.friend_status = 'friends'
                is_contact.friend_since = datetime.datetime.now()
                update_item(is_contact)
                return success('SUCCESS', meta={'message': 'Friend Request Accepted'})
            elif is_contact and is_contact.is_following == False:
                is_contact.friend_status = 'friends'
                is_contact.friend_since = datetime.datetime.now()
                update_item(is_contact)
                return success('SUCCESS', meta={'message': 'Friend Request Accepted'})
            else:
                add_contact = Contact(user_id=current_user.id, contact_id=data.get('user_id'), type=type,
                                      friend_status='friends',
                                      friend_since=datetime.datetime.now(),
                                     )

                add_item(add_contact)
                return success('SUCCESS', meta={'message': 'Friend Request Accepted'})
        else:
            return success('SUCCESS', meta={'message': 'No Friend Request Pending'})
    else:
        return success('SUCCESS', meta={'message': 'User Not Found'})


def reqRejected(current_user, data):
    existing_users = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_users:
        is_contact = Contact.query.filter_by(contact_id=current_user.id, user_id=data.get('user_id'),
                                             friend_status='pending', deleted_at=None).first()
        if is_contact:
            is_contact.friend_status = 'rejected'
            update_item(is_contact)
            return success('SUCCESS', meta={'message': 'Friend Request Deleted'})
        else:
            return success('SUCCESS', meta={'message': 'No Friend Request'})


def unfriend(current_user, data):
    user_id = data.get('user_id')
    is_friend = Contact.query.filter_by(contact_id=data.get('user_id'), user_id=current_user.id,
                                        friend_status='friends', deleted_at=None).first()
    is_contact = Contact.query.filter_by(contact_id=current_user.id, user_id=data.get('user_id'),
                                         friend_status='friends', deleted_at=None).first()
    if is_friend and is_contact:
        is_friend.is_following = False
        is_friend.friend_status = 'unfriend'
        is_friend.following_status = 'unfollowed'
        is_friend.unfollowed_on = datetime.datetime.now()
        is_contact.unfollowed_on = datetime.datetime.now()
        is_contact.is_following = False
        is_contact.friend_status = 'unfriend'
        is_contact.following_status = 'unfollowed'
        update_item(is_friend)
        update_item(is_contact)
        return success('SUCCESS', meta={'message': "Removed from friend list"})
    else:
        return success('SUCCESS', meta={'message': "User not in your friend list"})


def follow(current_user, data):
    user_id = data.get('user_id')
    if user_id== current_user.id:
        return success('SUCCESS',meta={'message':'Invalid User'})

    def send_notification():
        # send notification
        user_membership = Membership.query.filter_by(user_id=user_id, deleted_at=None,membership_status='active').first()
        message = current_user.first_name + " started Following you"
        queue_url = PUSH_NOTIFICATION_URL
        fcm_token = []
        fcm_token.append(user_membership.fcm_token)
        payload = {}
        payload['id'] = None
        payload['current_user'] = str(current_user.id)
        payload['message'] = message
        payload['title'] = "Following"
        payload['fcm_token'] = fcm_token
        payload['screen_type'] = 'ALL_FOLLOWING'
        payload['responder_id'] = None
        send_queue_message(queue_url, payload)

        # post in-app notification
        screen_info = {}
        data = {}
        screen_info['screen_type'] = 'ALL_FOLLOWING'
        screen_info['id'] = None
        data['meta_data'] = screen_info
        add_notification = Notification(user_id=user_id, type='friend', title=payload['title'],
                                        description=message, read_status=False,meta_data=data['meta_data'],c_user=current_user.id)
        add_item(add_notification)

    existing_user = Users.query.filter_by(id=current_user.id,deleted_at=None,user_deleted_at=None).first()
    users = Users.query.filter_by(id=user_id,deleted_at=None,user_deleted_at=None).first()
    if users:
        if users.can_follows == True:
            type = 'Influencer'
        else:
            type = 'Individual'
    if existing_user:
        if users.can_follows == True:
            is_following = Contact.query.filter_by(user_id=current_user.id, contact_id=user_id, deleted_at=None).first()
            if not is_following:
                follow = Contact(user_id=current_user.id, contact_id=user_id,
                                 following_status='following',
                                 is_following=True, following_on=data.get('following_on', None))
                add_item(follow)
                send_notification()
                return success('SUCCESS', meta={'message': 'Started Following'})
            elif is_following and is_following.friend_status == 'blocked':
                return success('SUCCESS', meta={'message': 'You cannot follow this user'})
            elif is_following and is_following.is_following == True:
                return success('SUCCESS', meta={'message': 'You already follow this user'})
            else:
                is_following.following_status = 'following'
                is_following.is_following = True
                is_following.following_on = datetime.datetime.now()
                update_item(is_following)
                send_notification()
                return success('SUCCESS', meta={'message': 'Started Following'})
        else:
            return success('SUCCESS', meta={'message': 'This account is not an influencer account'})
    else:
        return success('SUCCESS', meta={'message': 'User Not Found'})


def unfollow(current_user, data):
    user_id = data.get('user_id')
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    users = Users.query.filter_by(id=user_id,user_deleted_at=None,deleted_at=None).first()
    if existing_user:
        is_following = Contact.query.filter_by(contact_id=data.get('user_id'), user_id=current_user.id,
                                               deleted_at=None).first()
        if is_following and is_following.is_following == True:
            is_following.following_status = 'unfollowed'
            is_following.is_following = False
            is_following.unfollowed_on = datetime.datetime.now()
            update_item(is_following)
            return success("SUCCESS", meta={'message': 'unfollowed successfully'})
        else:
            return success("SUCCESS", meta={'message': 'You are not following this user'})
    else:
        return success('SUCCESS', meta={'message': 'User Not Found'})


def follwing_list(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_user:
        all_following_list = Contact.query.filter_by(user_id=current_user.id, is_following=True,
                                                     following_status='following', deleted_at=None).all()
        following_list = Contact.query.filter_by(user_id=current_user.id, is_following=True,
                                                 following_status='following', deleted_at=None).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        following_list = following_list.items
        total_record = len(all_following_list)
        total_pages = total_record // per_page + 1
        result = []
        if following_list:
            for user in following_list:
                user_data = {}
                existing_user = Users.query.filter_by(id=user.contact_id,user_deleted_at=None,deleted_at=None).first()
                if existing_user:
                    # user_data['contact_id'] = user.contact_id
                    # user_data['created_on'] = user.following_on
                    user_data['contact_id'] = existing_user.id
                    user_data['name'] = existing_user.first_name
                    user_data['profile_image'] = existing_user.profile_image
                    result.append(user_data)
                else:
                    pass
            return success("SUCCESS", result,
                           meta={"message": 'Following List',
                                 'page_info': {'current_page': page, 'total_record': total_record,
                                               'total_pages': total_pages,
                                               'limit': per_page}})

        else:
            return success("SUCCESS", meta={'message': 'No data found'})
    else:
        return success("SUCCESS", meta={'message': 'User not found'})


def followers_list(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_user:
        all_follower_list = Contact.query.filter_by(contact_id=current_user.id, is_following=True,
                                                    following_status='following', deleted_at=None).all()
        follower_list = Contact.query.filter_by(contact_id=current_user.id, is_following=True,
                                                following_status='following', deleted_at=None).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        my_followers = follower_list.items
        total_record = len(all_follower_list)
        total_pages = total_record // per_page + 1
        result = []
        for user in my_followers:
            user_data = {}
            existing_user = Users.query.filter_by(id=user.user_id,deleted_at=None,user_deleted_at=None).first()
            is_following =  Contact.query.filter_by(user_id=current_user.id,contact_id=user.user_id,deleted_at=None).first()
            if existing_user:
                user_data['contact_id'] = existing_user.id
                user_data['name'] = existing_user.first_name
                user_data['profile_image'] = existing_user.profile_image
                if is_following and is_following.friend_status=='friends':
                    user_data['friend_status'] = True
                else:
                    user_data['friend_status'] = False

                if is_following and is_following.is_following ==True:
                    user_data['is_following'] = True
                else:
                    user_data['is_following'] = False
                user_data['user_info'] = get_user_profile_details(existing_user.id)
                result.append(user_data)
        return success("SUCCESS", result,
                       meta={"message": 'Followers List',
                             'page_info': {'current_page': page, 'total_record': total_record,
                                           'total_pages': total_pages,
                                           'limit': per_page}})


def block_friend(current_user, data):
    request_to = data.get('user_id')
    if request_to == current_user.id:
        return success('SUCCESS', meta={'message': 'Invalid User'})
    users = Users.query.filter_by(id=request_to,deleted_at=None,user_deleted_at=None).first()
    if users:
        if users.can_follows == True:
            type = 'Influencer'
        else:
            type = 'Individual'
    existing_user = Users.query.filter_by(id=current_user.id,deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        is_blocked = Contact.query.filter_by(contact_id=data.get('user_id'), user_id=current_user.id,
                                             deleted_at=None).first()
        if is_blocked:
            if is_blocked.friend_status == 'blocked':
                return success('SUCCESS', meta={'message': 'User already blocked'})
            elif is_blocked.friend_status != 'blocked' and is_blocked.friend_status != 'friends' and is_blocked.is_following == True:
                is_blocked.friend_status = 'blocked'
                is_blocked.following_status = 'unfollowed'
                is_blocked.is_following = False
                is_blocked.unfollowed_on = datetime.datetime.now()
                is_blocked.block_on = datetime.datetime.now()
                update_item(is_blocked)
                return success("SUCCESS", meta={'message': 'blocked successfully'})
            elif is_blocked.friend_status == 'friends':
                is_blocked.friend_status = 'blocked'
                is_blocked.following_status = 'unfollowed'
                is_blocked.is_following = False
                is_blocked.unfollowed_on = datetime.datetime.now()
                is_blocked.block_on = datetime.datetime.now()
                update_item(is_blocked)
                my_contact = Contact.query.filter_by(user_id=data.get('user_id'), contact_id=current_user.id,
                                                     deleted_at=None).first()
                if my_contact:
                    my_contact.friend_status = 'unfriend'
                    my_contact.unfollowed_on = datetime.datetime.now()
                    my_contact.is_following = False
                    my_contact.following_status = 'unfollowed'
                    update_item(my_contact)
                return success("SUCCESS", meta={'message': 'blocked successfully'})
            else:
                is_blocked.friend_status = 'blocked'
                is_blocked.block_on = datetime.datetime.now()
                update_item(is_blocked)
                return success("SUCCESS", meta={'message': 'blocked successfully'})
        else:
            block = Contact(contact_id=data.get('user_id'), user_id=current_user.id, type=type,
                            friend_status='blocked', block_on=datetime.datetime.now())
            add_item(block)
            return success("SUCCESS", meta={'message': 'blocked successfully'})


def unblock_friend(current_user, data):
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_user:
        is_blocked = Contact.query.filter_by(contact_id=data.get('user_id'), user_id=current_user.id, deleted_at=None,
                                             friend_status='blocked').first()
        if is_blocked:
            is_blocked.friend_status = 'unblocked'
            is_blocked.unblock_on = datetime.datetime.now()
            update_item(is_blocked)
            return success('SUCCESS', meta={'message': 'unblocked successfully'})
        else:
            return success('SUCCESS', meta={'message': 'User Not in block list'})


def block_list(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_user:
        all_block_list = Contact.query.filter_by(user_id=current_user.id,
                                                 friend_status='blocked', deleted_at=None).all()
        block_list = Contact.query.filter_by(user_id=current_user.id,
                                             friend_status='blocked', deleted_at=None).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        my_block_list = block_list.items
        total_record = len(all_block_list)
        total_pages = total_record // per_page + 1
        result = []
        for user in my_block_list:
            user_data = {}
            existing_user = Users.query.filter_by(id=user.contact_id,user_deleted_at=None,deleted_at=None).first()
            user_data['contact_id'] = existing_user.id
            user_data['name'] = existing_user.first_name
            user_data['profile_image'] = existing_user.profile_image
            result.append(user_data)
        return success("SUCCESS", result,
                       meta={"message": 'Block List',
                             'page_info': {'current_page': page, 'total_record': total_record,
                                           'total_pages': total_pages,
                                           'limit': per_page}})


def search_friends_list(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    offset = per_page * (page - 1)
    keyword = request.args.get('keyword')
    type = request.args.get('type')
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_user:
        blocklist = []
        contactlist = []
        my_blocklist = Contact.query.filter_by(user_id=current_user.id, friend_status='blocked', deleted_at=None).all()
        my_contact = Contact.query.filter_by(user_id=current_user.id, friend_status='friends', deleted_at=None).all()
        if my_blocklist:
            for blocked_user in my_blocklist:
                blocklist.append(blocked_user.contact_id)
        if my_contact:
            for contact in my_contact:
                contactlist.append(contact.contact_id)
        if keyword and type == 'people':
            search_string = '%{}%'.format(keyword)
            search_friends_list = Users.query.join(Contact, Users.id == Contact.user_id, isouter=True).filter(
                or_((Users.first_name.ilike(search_string)), (Users.nickname.ilike(search_string))),
                Users.id.notin_(blocklist),Users.user_deleted_at==None,Users.deleted_at==None).paginate(
                page=page,
                per_page=per_page,
                error_out=False)

            users = search_friends_list.items
            total_record = len(users)
            total_pages = total_record // per_page + 1
            result = []
            if users:
                for user in users:
                    if user.id != current_user.id:
                        user_data = {}
                        contacts = Contact.query.filter_by(user_id=current_user.id, contact_id=user.id,deleted_at=None).all()
                        if contacts:
                            for contact in contacts:
                                user_data['is_following'] = contact.is_following
                                user_data['friend_status'] = contact.friend_status
                        else:
                            user_data['is_following'] = False
                            user_data['friend_status'] = False
                        user_data['id'] = user.id
                        user_data['name'] = user.first_name
                        user_data['profile_image'] = user.profile_image
                        user_data['can_follows'] = user.can_follows
                        result.append(user_data)
                return success("SUCCESS", result, meta={"message": "Friend Search",
                                                        'page_info': {'current_page': page, 'limit': per_page}})
            else:
                return success("SUCCESS", meta={"message": "No Data Found"})
        elif keyword and type == 'post':
            search_string = '%{}%'.format(keyword)
            friends_list = Contact.query.filter(or_(Contact.friend_status == 'friends', Contact.is_following == True),
                                                Contact.user_id == current_user.id, Contact.deleted_at == None).all()
            friends = []
            all_friends = ''
            if friends_list:
                for data in friends_list:
                    friends.append("'" + str(data.contact_id) + "'")
            # all_friends=tuple(friends)
            if friends:
                all_friends = ','.join(friends)
            query = """SELECT p.* FROM post p LEFT JOIN contact c ON p.user_id = c.user_id WHERE (p.deleted_at IS  NULL AND p.description like '{search_string}' AND p.group_id is NULL AND (
                            p.expire_on is null or p.expire_on > NOW())) AND (p.visibility ='all' OR p.user_id='{user_id}' OR  (p.user_id in ({all_friends}) AND p.visibility='friends')) GROUP BY (p.id)
                            ORDER BY p.created_at DESC LIMIT {per_page} OFFSET {offset}
                            """.format(user_id=current_user.id, all_friends=all_friends, search_string=search_string,
                                       per_page=per_page, offset=offset)
            posts = _query_execution(query)
            result = []
            if posts:
                for post in posts:
                    post_data = {}

                    like_count = PostReact.query.filter(PostReact.post_id == post['id'], PostReact.type == 'like',
                                                        PostReact.is_liked == True).count()
                    comment_count = Comment.query.filter(Comment.post_id == post['id'],
                                                         Comment.deleted_at == None).count()
                    is_reacted = PostReact.query.filter(PostReact.user_id == current_user.id,
                                                        PostReact.post_id == post['id'],
                                                        PostReact.deleted_at == None).first()
                    user_data = Users.query.filter_by(id=post['user_id'], deleted_at=None,user_deleted_at=None).first()
                    if user_data:
                        post_data['user_info'] = get_user_profile_details(user_data.id)
                        post_data['id'] = post['id']
                        post_data['location'] = post['location']
                        post_data['title'] = post['title']
                        post_data['description'] = post['description']
                        post_data['created_at'] = post['created_at']
                        post_data['visibility'] = post['visibility']
                        post_data['type'] = post['type']
                        post_data['meta_data'] = post['meta_data']
                        if like_count >= 0:
                            post_data['likes'] = like_count
                        if comment_count >= 0:
                            post_data['comments'] = comment_count
                        if is_reacted is not None:
                            post_data['is_liked'] = is_reacted.is_liked
                        else:
                            post_data['is_liked'] = False

                        result.append(post_data)
                return success("SUCCESS", result, meta={"message": "Post Search",
                                                        'page_info': {'current_page': page, 'limit': per_page}})
            else:
                return success("SUCCESS", meta={"message": "No Data Found"})
        elif keyword and type == 'group':
            search_string = '%{}%'.format(keyword)
            # search_friends_list = Users.query.filter(func.lower((Users.nickname).like(search_string))).all()
            search_group_list = Group.query.join(Users, Group.user_id == Users.id, isouter=True).filter(or_(
                Group.group_name.ilike(search_string),
                Group.description.ilike(search_string)
            ), Group.deleted_at == None).paginate(
                page=page,
                per_page=per_page,
                error_out=False)
            groups = search_group_list.items
            # total_record = len(groups)
            # total_pages = total_record // per_page + 1
            if groups:
                result = []
                for group in groups:
                    member_count = GroupMembers.query.filter_by(group_id=group.id, status='active',
                                                                deleted_at=None).count()
                    membership_status = GroupMembers.query.filter_by(group_id=group.id, user_id=current_user.id,
                                                                     deleted_at=None).first()
                    admin = GroupMembers.query.filter_by(group_id=group.id, status='active', type='admin',
                                                         deleted_at=None).first()
                    admin_info = ''
                    if admin:
                        admin_info = Users.query.filter_by(id=admin.user_id, deleted_at=None,user_deleted_at=None).first()
                    group_data = {}
                    visibility = ''
                    if group.visibility == 'group_members':
                        visibility = 'closed'
                    if group.visibility == 'all':
                        visibility = 'open'
                    group_data['group_id'] = group.id
                    group_data['group_name'] = group.group_name
                    group_data['description'] = group.description
                    group_data['image'] = group.image
                    group_data['city'] = group.city
                    group_data['visibility'] = visibility
                    group_data['members_count'] = member_count
                    # group_data['owner_id'] = admin_info.id
                    if admin_info:
                        group_data['owner_name'] = admin_info.first_name
                    group_data['sport'] = group.sport_type
                    if membership_status and membership_status.status == 'active':
                        group_data['status'] = 'active'
                    elif membership_status and membership_status.status == 'inactive':
                        group_data['status'] = 'pending'
                    else:
                        group_data['status'] = "inactive"
                    if membership_status and membership_status.type == 'admin':
                        group_data['type'] = 'Admin'
                    result.append(group_data)
                return success("SUCCESS", result,
                               meta={"message": "Group Search", 'page_info': {'current_page': page, 'limit': per_page}})

            else:
                return success("SUCCESS", meta={"message": "No Data Found"})

        else:
            return success("SUCCESS", meta={"message": "keyword is invalid"})



def user_friend_list(current_user, user_id):
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        exist_user = Users.query.filter_by(id=user_id, deleted_at=None,user_deleted_at=None).first()
        if exist_user:
            friend_status = Contact.query.filter_by(contact_id=current_user.id, friend_status='friends',
                                                    user_id=user_id, deleted_at=None).first()
            if friend_status:
                status = friend_list(exist_user)
                return status
                # return success('SUCCESS', meta={'message':'friends list'})
            else:
                return success('SUCCESS', meta={'message': 'not friends'})
        else:
            return success('SUCCESS', meta={'message': 'user not found'})
    else:
        return success('SUCCESS', meta={'message': 'invalid user'})



