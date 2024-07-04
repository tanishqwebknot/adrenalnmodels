from flask import request, Blueprint

from api.contact.services import sendrequest, request_sent, request_list, friend_list, reqConfirm, search_friends_list, \
    reqRejected, unfollow, block_friend, unfriend, unblock_friend, follwing_list, followers_list, follow, \
    unsend_friend_request, block_list, user_friend_list
from api.exceptions.exceptions import Exception
from common.response import success, failure
from middleware.auth import token_required, validate_token

contact_api = Blueprint('contact_api', __name__, url_prefix='/friends')


@contact_api.route('/request', methods=['POST'])
@validate_token(action='send_friend_request')
def friendRequest(current_user):
    try:
        data = request.get_json()
        return sendrequest(data, current_user)

    except Exception as e:
        return failure("Something went wrong.")


@contact_api.route('/unsend_request', methods=['POST'])
@validate_token(action='unsend_friend_request')
def unsend_request(current_user):
    try:
        data = request.get_json()
        return unsend_friend_request(current_user,data)
    except Exception as e:
        return failure("Something went wrong.")


@contact_api.route('/request_sent', methods=['GET'])
@validate_token(action='get_friend_request_sent')
def friend_request_sent(current_user):
    try:
        return request_sent(current_user)
    except Exception as e:
        return failure("Something went wrong.")


# to check pending friend requests
@contact_api.route('/request_list', methods=['GET'])
@validate_token(action='get_friend_request_list')
def get_request_list(current_user):
    try:
        data = request.get_json()
        return request_list(current_user, data)

    except Exception as e:
        return failure("Something went wrong.")


@contact_api.route('/friend_list', methods=['GET'])
@validate_token(action='get_friend_list')
def friends(current_user):
    try:
        return friend_list(current_user)
    except Exception as e:
        return failure("Something went wrong.")


@contact_api.route('/confirm_request', methods=['POST'])
@validate_token(action='accept_friend_request')
def confirmRequest(current_user):
    try:
        data = request.get_json()
        return reqConfirm(current_user, data)

    except Exception as e:
        return failure("Something went wrong.")


@contact_api.route('/delete_request', methods=['POST'])
@validate_token(action='reject_friend_request')
def rejectRequest(current_user):
    try:
        data = request.get_json()
        return reqRejected(current_user, data)

    except Exception as e:
        return failure("Something went wrong.")


@contact_api.route('/search', methods=['GET'])
@validate_token(action='search_people')
def search_friends(current_user):
    try:
        search_list = search_friends_list(current_user)
        return search_list

    except Exception as e:
        return failure("Something went wrong.")


# unfriend friend API
@contact_api.route('/unfriend', methods=['POST'])
@validate_token(action='unfriend')
def unfriend_friends(current_user):
    data = request.get_json()
    try:
        return unfriend(current_user, data)
    except Exception as e:
        return failure("Something went wrong.")


# unfolllow friend API
@contact_api.route('/unfollow', methods=['POST'])
@validate_token(action='unfollow')
def unfollow_friends(current_user):
    try:
        data = request.get_json()
        return unfollow(current_user, data)
    except Exception as e:
        return failure("Something went wrong.")


# folllow friend API
@contact_api.route('/follow', methods=['POST'])
@validate_token(action='follow')
def follow_friends(current_user):
    try:
        data = request.get_json()
        return follow(current_user, data)
    except Exception as e:
        return failure("Something went wrong.")


@contact_api.route('/block', methods=['POST'])
@validate_token(action='blocked')
def block_friends(current_user):
    data = request.get_json()
    try:
        return block_friend(current_user, data)
    except Exception as e:
        return failure("Something went wrong.")


@contact_api.route('/unblock', methods=['POST'])
@validate_token(action='unblocked')
def unblock_friends(current_user):
    data = request.get_json()
    try:
        return unblock_friend(current_user, data)

    except Exception as e:
        return failure("Something went wrong.")


# API for my following list
@contact_api.route('/block_list', methods=['GET'])
@validate_token(action='block_list')
def blocked_list(current_user):
    try:
        return block_list(current_user)

    except Exception as e:
        return failure("Something went wrong.")


# API for my following list
@contact_api.route('/follwing', methods=['GET'])
@validate_token(action='following_list')
def following(current_user):
    try:
        follwing = follwing_list(current_user)
        return follwing
    except Exception as e:
        return failure("Something went wrong.")


# API for my followers list
@contact_api.route('/followers', methods=['GET'])
@validate_token(action='followers_list')
def followers(current_user):
    try:
        followers = followers_list(current_user)
        return followers

    except Exception as e:
        return failure("Something went wrong.")


# to get other users friendlist
@contact_api.route('/friend_list/<user_id>', methods=['GET'])
@validate_token(action='get_users_friend_list')
def others_friend_list(current_user, user_id):
    try:
        return user_friend_list(current_user, user_id)
    except Exception as e:
        return failure("Something went wrong.")

