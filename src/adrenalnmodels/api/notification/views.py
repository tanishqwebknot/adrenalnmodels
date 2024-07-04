import datetime
import json

from api.Post.mongo_services import ViewPostRepository, UserTimeLineRepository
from api.Post.services import create_post, fetch_post, add_master_activity, get_activity, betting_react, \
    get_wall_content, update_post, result_update, result_confirmation, fetch_post_own, add_post_react, \
    update_post_visibility, get_master_betting_items, get_promo_feeds, get_betting_members, remove_betting_members, \
    check_if_admin_post, add_admin_post, post_saved_posts, get_save_later, prepare_post_display_fileds, betting_details, \
    betting_conforamtion, check_expiry
from api.Users.models import Users, Membership
from api.Users.services import get_user_profile_details
from api.comment.models import Comment
from api.notification.services import update_notification, get_notification, unseen_notification_list, make_all_read
from flask import request, session, jsonify, Blueprint
from api.Post.models import Post, MasterActivity, BettingPost, Post_comments, PostReact, MasterBettingItems
from common.connection import add_item, update_item, raw_select, delete_item, get_item
from common.response import success, failure
from middleware.auth import token_required, validate_token

notification_api = Blueprint('notification', __name__, url_prefix='/notification')


# send notification
@notification_api.route('', methods=['POST'])
@validate_token(action='send_notification')
def send_notification(current_user):
    return success("SUCCESS")


@notification_api.route('', methods=['GET'])
@validate_token(action='get_notification')
def get_notifications(current_user):
    return get_notification(current_user)


@notification_api.route('/<notification_id>' , methods=['PUT'])
@validate_token(action='update_notification')
def update_notifications(current_user,notification_id):
    data = request.get_json()
    return update_notification(current_user, notification_id, data)


@notification_api.route('/notification_count' , methods=['GET'])
@validate_token(action='unseen_notification')
def notification_count(current_user):
    return unseen_notification_list(current_user)


@notification_api.route('/mark_all_read', methods=['POST'])
@validate_token(action='mark_all_read')
def notification_all_read(current_user):
    return make_all_read(current_user)
