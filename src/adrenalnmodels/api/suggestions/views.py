import json

from flask import request, Blueprint
from api.Post.mongo_models import CityList
from api.Post.mongo_services import CityListRepository
from api.contact.services import sendrequest, request_sent, request_list, friend_list, reqConfirm, search_friends_list, \
    reqRejected, unfollow, follwing_list
from api.exceptions.exceptions import Exception
from api.suggestions.services import get_friend_suggestion, get_group_suggestion, get_group_suggestion_v2, \
    get_friend_suggestion_v2
from common.response import success, failure
from middleware.auth import token_required, validate_token

suggestion_api = Blueprint('suggestion_api', __name__, url_prefix='/suggestions')


@suggestion_api.route('/friends', methods=['GET'])
@validate_token(action='friend_suggestion')
def friend_suggestion(current_user):
    try:
        data = request.get_json()
        return get_friend_suggestion_v2(current_user,data)

    except Exception as e:
        return failure("Something went wrong.")


@suggestion_api.route('/groups', methods=['GET'])
@validate_token(action='group_suggestion')
def group_suggestion(current_user):
    try:
        result = get_group_suggestion_v2(current_user)
        print(result)
        return result
    except Exception as e:
        return failure("Something went wrong")



@suggestion_api.route('/search_city', methods=['GET'])
def search_by_keyword():
    keyword = request.args.get('keyword')
    if keyword:
        search_city = CityListRepository.get_city_list(keyword)
        return success('SUCCESS', search_city, meta={'message':'City Suggestions'})


