from flask import jsonify

from api.Post.models import Post
from api.Users.models import Users, Membership
from api.Users.services import get_user_profile_details
from api.comment.models import Comment, CommentReact, CommentTagging
from api.notification.models import Notification
from api.notification.services import send_queue_message
from common.connection import add_item, update_item
from common.response import success
from config import PUSH_NOTIFICATION_URL


def add_comment(current_user, data):
    parent_id = data.get('parent_id', None)
    post_id = data.get('post_id', None)
    tagged_users = data.get('tagged_users', None)
    comment = Comment(post_id=data.get('post_id', None), parent_id=data.get('parent_id', None), user_id=current_user.id,
                      comment=data.get('comment', None))
    add_item(comment)
    if tagged_users is not None:
        for user in tagged_users:
            user_exist = Users.query.filter_by(id=user, deleted_at=None,user_deleted_at=None).first()
            post_exist = Post.query.filter_by(id=post_id, deleted_at=None).first()
            if user_exist and post_exist:
                tagging = CommentTagging(post_id=post_id, user_id=user)
                add_item(tagging)
    if not parent_id:
        post_owner = Post.query.filter_by(id=post_id, deleted_at=None).first()
        # if post owner is commenting on his post
        if post_owner.user_id == current_user.id:
            message = None
            queue_url = PUSH_NOTIFICATION_URL
            fcm_token=[]
            # fcm_token.append(user_membership.fcm_token)
            payload={}
            screen_type = ''
            if post_owner.type == 'regular':
                screen_type = 'REGULAR_POST'
            if post_owner.type == 'activity':
                screen_type = 'ACTIVITY_POST'
            if post_owner.type == 'betting':
                screen_type = 'BETTING_POST'
            if post_owner.type == 'watch_activity':
                screen_type = 'WATCH_ACTIVITY_POST'
            if post_owner.type == 'betting_result':
                screen_type = 'BETTING_RESULT'
            if post_owner.type == 'record_activity':
                screen_type = 'RECORD_ACTIVITY_POST'
            payload['id'] = str(post_id)
            payload['current_user'] = str(current_user.id)
            payload['message'] = message
            payload['title'] = "Comment"
            payload['comment_tagging'] = tagged_users
            payload['fcm_token'] = fcm_token
            payload['screen_type'] = screen_type
            payload['post_owner_id'] = str(post_owner.user_id)
            payload['responder_id'] = None
            send_queue_message(queue_url, payload)
            # post in-app notification
            # screen_info = {}
            # data = {}
            # screen_info['screen_type'] = screen_type
            # screen_info['id'] = str(post_id)
            # data['meta_data'] = screen_info
            # add_notification = Notification(user_id=post_owner.user_id, type='post', title=payload['title'],
            #                                 description=message, read_status=False,meta_data=data['meta_data'])
            # add_item(add_notification)

        else:
            user_membership = Membership.query.filter_by(user_id=post_owner.user_id,membership_status='active', deleted_at=None).first()

            if tagged_users and str(post_owner.user_id) in tagged_users:
                message = current_user.first_name + " tagged you in a comment"
            else:
                message = current_user.first_name + " commented on your post"
            queue_url = PUSH_NOTIFICATION_URL
            token=[]
            token.append(user_membership.fcm_token)
            payload = {}
            screen_type = ''
            if post_owner.type == 'regular':
                screen_type = 'REGULAR_POST'
            if post_owner.type == 'activity':
                screen_type = 'ACTIVITY_POST'
            if post_owner.type == 'betting':
                screen_type = 'BETTING_POST'
            if post_owner.type == 'watch_activity':
                screen_type = 'WATCH_ACTIVITY_POST'
            if post_owner.type == 'betting_result':
                screen_type = 'BETTING_RESULT'
            if post_owner.type == 'record_activity':
                screen_type = 'RECORD_ACTIVITY_POST'
            payload['id'] = str(post_id)
            payload['current_user'] = str(current_user.id)
            payload['message'] = message
            payload['title'] = "Comment"
            payload['fcm_token'] = token
            payload['comment_tagging'] = tagged_users
            payload['screen_type'] = screen_type
            payload['post_owner_id'] = str(post_owner.user_id)
            payload['responder_id'] = None
            send_queue_message(queue_url, payload)
            # post in-app notification
            screen_info = {}
            data = {}
            screen_info['screen_type'] = screen_type
            screen_info['id'] = str(post_id)
            data['meta_data'] = screen_info
            add_notification = Notification(user_id=post_owner.user_id, type='post', title=payload['title'],
                                            description=message, read_status=False,meta_data=data['meta_data'],c_user=current_user.id)
            add_item(add_notification)

    # reply to a comment
    else:
        post_owner = Post.query.filter_by(id=post_id, deleted_at=None).first()
        comment_data = Comment.query.filter_by(id=parent_id, deleted_at=None).first()
        if comment_data.user_id != current_user.id:
            user_membership = Membership.query.filter_by(user_id=comment_data.user_id, deleted_at=None).first()
            message = current_user.first_name + " replied to your comment"
            queue_url = PUSH_NOTIFICATION_URL
            fcm_token = []
            fcm_token.append(user_membership.fcm_token)
            payload = {}
            screen_type = ''
            if post_owner.type == 'regular':
                screen_type = 'REGULAR_POST'
            if post_owner.type == 'activity':
                screen_type = 'ACTIVITY_POST'
            if post_owner.type == 'betting':
                screen_type = 'BETTING_POST'
            if post_owner.type == 'watch_activity':
                screen_type = 'WATCH_ACTIVITY_POST'
            if post_owner.type == 'betting_result':
                screen_type = 'BETTING_RESULT'
            if post_owner.type == 'record_activity':
                screen_type = 'RECORD_ACTIVITY_POST'

            payload['id'] = str(post_id)
            payload['current_user'] = str(current_user.id)
            payload['message'] = message
            payload['title'] = "Comment"
            payload['fcm_token'] = fcm_token
            payload['comment_tagging'] = tagged_users
            payload['screen_type'] = screen_type
            payload['post_owner_id'] = str(post_owner.user_id)
            payload['responder_id'] = None
            send_queue_message(queue_url, payload)
            # post in-app notification
            screen_info = {}
            data = {}
            screen_info['screen_type'] = screen_type
            screen_info['id'] = str(post_id)
            data['meta_data'] = screen_info
            add_notification = Notification(user_id=comment_data.user_id, type='post', title=payload['title'],
                                            description=message, read_status=False,meta_data=data['meta_data'],c_user=current_user.id)
            add_item(add_notification)

    return success('SUCCESS',meta={'message':'Comment Posted'})


def fetch_comment(current_user,postId):
    existing_user = Users.query.filter_by(id=current_user.id,deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        # postId = data.get('post_id')
        comments = Comment.query.filter_by(post_id=postId, parent_id=None,deleted_at=None).all()
        result = []

        for comment in comments:
            comment_details = get_comment_detail(comment.id)
            if comment_details:
                result.append(comment_details)
        return success("SUCCESS", result, meta={"message": "Comment List"})


def get_comment_detail(comment_id):
    comments = Comment.query.filter_by(id=comment_id,deleted_at=None).one()
    if comments:
        comment_detail = {"comment": comments.comment, "id": comments.id, "user_info": get_user_profile_details(comments.user_id),
                          "created_at": comments.created_at, "update_at": comments.update_at, "reply": []}

        child_comments = Comment.query.filter_by(parent_id=comment_id,deleted_at=None).order_by(Comment.created_at.desc()).all()
        if child_comments:
            for child in child_comments:
                child_detail = get_comment_detail(child.id)
                if child_detail:
                    comment_detail["reply"].append(child_detail)

        return comment_detail

    else:
        return None


def update_parent_comment(data, comment_id, current_user):
    tagged_users = data.get('tagged_users', None)
    existing_user = Users.query.filter_by(id=current_user.id,deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        my_comment = Comment.query.filter_by(user_id=current_user.id, id=comment_id,deleted_at=None).first()
        if my_comment:
            my_comment.comment = data.get('comment', None)
            update_item(my_comment)
            if tagged_users is not None:
                for user in tagged_users:
                    user_exist = Users.query.filter_by(id=user, deleted_at=None,user_deleted_at=None).first()
                    tag_exist = CommentTagging.query.filter_by(post_id=my_comment.post_id, user_id=user,
                                                               deleted_at=None).first()
                    if user_exist and not tag_exist:
                        tagging = CommentTagging(post_id=my_comment.post_id, user_id=user)
                        add_item(tagging)

            return success('SUCCESS',meta={'message':'Comment Updated'})
        else:
            return success('SUCCESS', meta={'message': 'invalid comment'})
    else:
        return success('SUCCESS', meta={'message': 'User Not Found'})
# def update_comment(current_user, data, comment_id):
#     my_comment = Comment.query.filter_by(user_id=current_user.id, id=comment_id,parent_id="null").first()
#     my_comment.comment = data.get('comment', None)
#     update_item(my_comment)


def add_comment_react(current_user, data):
    comment_id = data['comment_id']
    type = data['type']
    valid_comment = Comment.query.filter_by(id=comment_id,deleted_at=None).first()
    if valid_comment:
        exist_comment_react = CommentReact.query.filter_by(comment_id=comment_id, user_id=current_user.id,
                                                           deleted_at=None).first()
        if exist_comment_react:
            if exist_comment_react.is_liked == True:
                exist_comment_react.is_liked = False
                update_item(exist_comment_react)
                return success('SUCCESS', meta={'message': 'You unliked this comment'})
            else:
                exist_comment_react.is_liked = True
                update_item(exist_comment_react)
                return success('SUCCESS', meta={'message': 'You liked this comment'})
        else:
            add_reaction = CommentReact(comment_id=comment_id, is_liked=True, type=type, user_id=current_user.id)
            add_item(add_reaction)
            return success('SUCCESS', meta={'message': 'You liked this comment'})
    else:
        return success('SUCCESS', meta={'message': 'invalid comment'})

