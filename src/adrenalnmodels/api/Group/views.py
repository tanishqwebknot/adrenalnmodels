import datetime

import requests
from flask import request, jsonify, json, g, Blueprint
from sqlalchemy import func, or_
from api.Group.models import GroupMembers
from api.Group.services import Group, update_group_details, group_create, join_group, pending_requests, \
    accept_join_request, make_new_admin, remove_group_member, group_detail, my_group_list, search_group_members, \
    group_member_list, search_friend_list, group_exit, get_group_content, add_member, make_admin_to_user, \
    reject_join_request, accept_group_invitation, get_group_list
from api.Post.models import Post
from api.Users.models import Users
from api.Users.services import get_user_profile_details
from app import db
from common.connection import add_item, update_item, delete_item
from common.response import success, failure
from middleware.auth import token_required, validate_token
# from flasgger import swag_from

group_api = Blueprint('group_api', __name__, url_prefix='/group')


# create Group
@group_api.route('', methods=['POST'])
@validate_token(action='group_create')
def create_group(current_user):
    data = request.json
    return group_create(current_user,data)


# group wall
@group_api.route('/feeds/<group_id>', methods=['GET'])
@token_required
def group_wall(current_user,group_id):
    data = request.json
    return get_group_content(current_user,group_id)


# Send request to Join Group
@group_api.route('/join/<group_id>', methods=['POST'])
@validate_token(action='group_join')
def join_group_request(current_user, group_id):
    return join_group(current_user,group_id)


# Pending requests for Group
@group_api.route('/requests/<group_id>', methods=['GET'])
@validate_token(action='get_requests_list')
def join_request_pending(current_user, group_id):
    return pending_requests(current_user,group_id)


# accept Join request for group
@group_api.route('/requests/accept/<group_id>', methods=['POST'])
@validate_token(action='group_requests_accept')
def accept_req(current_user, group_id):
    data = request.get_json()
    return accept_join_request(current_user,group_id,data)


# Exit group
@group_api.route('/exit/<group_id>', methods=['POST'])
@validate_token(action='group_exit')
def exit_group(current_user, group_id):
    return group_exit(current_user,group_id)


# edit group
@group_api.route('/<group_id>', methods=['PUT'])
@validate_token(action='group_update')
def update_group(current_user, group_id):
    try:
        data = request.get_json()
        return update_group_details(current_user,data, group_id)
    except Exception as e:
        return failure("Something went wrong.")


# member as a admin
@group_api.route('/admin/<group_id>', methods=['POST'])
@validate_token(action='group_admin_add')
def member_as_admin(current_user, group_id):
    data = request.get_json()
    return make_new_admin(current_user,data,group_id)


# remove members from group only by admin
@group_api.route('/members/remove/<group_id>', methods=['POST'])
@validate_token(action='group_member_remove')
def remove_members(current_user, group_id):
    data = request.get_json()
    return remove_group_member(current_user,data,group_id)


# delete group
@group_api.route('/<group_id>', methods=['DELETE'])
@validate_token(action='group_delete')
def delete_group(current_user, group_id):
    existing_user_group = Group.query.filter_by(user_id=current_user.id, id=group_id).first()
    if existing_user_group:
        delete_my_group = GroupMembers.query.filter(GroupMembers.group_id == group_id).all()
        for item in delete_my_group:
            delete_members = GroupMembers.query.filter_by(group_id=item.group_id).first()
            delete_item(delete_members)
        delete_item(existing_user_group)
    return success("group deleted successfully!")


# Group Detail
@group_api.route('/<group_id>', methods=['GET'])
@validate_token(action='group_detail')
def group_details(current_user, group_id):
    return group_detail(current_user,group_id)


# show list of my groups
@group_api.route('/', methods=['GET'])
@validate_token(action='group_list')
def show_group(current_user):
    # groups = Group.query.filter_by(user_id=current_user.id, status='active').all()
    return my_group_list(current_user)


# search group members
@group_api.route('/members/search/<group_id>', methods=['GET'])
@validate_token(action='search_group_member')
def search_members(current_user, group_id):
    return search_group_members(current_user,group_id)


# Group Member List
@group_api.route('/members/<group_id>', methods=['GET'])
@validate_token(action='search_group')
def members_list(current_user,group_id):
    return group_member_list(current_user,group_id)


# search group members
@group_api.route('/friend/search', methods=['GET'])
@validate_token(action='search_group_member')
def search_friend(current_user):
    return search_friend_list(current_user)


# search Groups
@group_api.route('/search', methods=['GET'])
@validate_token(action='search_group')
def search_group(current_user):
    keyword = request.args.get('keyword')
    keyword = keyword.lower()
    if keyword:
        search_string = '%{}%'.format(keyword)
        group_detail_search = Group.query.filter(func.lower(Group.group_name).like(search_string)).all()
        groups = Group.query.filter_by(user_id=current_user.id).all()

        result = []
        if group_detail_search:
            members_count = GroupMembers.query.filter().count()
            member = GroupMembers.query.filter(GroupMembers.user_id == current_user.id).first()
            is_member = False
            is_admin = False
            if member:
                if member.status == 'active':
                    is_member = True
                if member.type == 'admin':
                    is_admin = True
            owner = ""
            owner_detail = Users.query.filter_by(id=groups.user_id,user_deleted_at=None,deleted_at=None).first()
            if owner_detail:
                owner = owner_detail.nickname
            group_data = {}
            group_data['group_id'] = group_detail_search.id
            group_data['group_name'] = group_detail_search.group_name
            group_data['description'] = group_detail_search.description
            group_data['owner_name'] = owner
            group_data['sport'] = group_detail_search.sport_type
            group_data['visibility'] = group_detail_search.visibility
            group_data['created_on'] = group_detail_search.created_at
            group_data['is_member'] = is_member
            group_data['is_admin'] = is_admin
            group_data['members_count'] = members_count
            return success('SUCCESS', result)
        return failure()


# member as a admin
@group_api.route('/add_admin/<group_id>', methods=['POST'])
@validate_token(action='group_admin_add')
def make_admin(current_user, group_id):
    data = request.get_json()
    return make_new_admin(current_user,data,group_id)


# add member
@group_api.route('/add_members/<group_id>', methods=['POST'])
@validate_token(action='group_admin_add')
def add_members(current_user, group_id):
    data = request.get_json()
    return add_member(current_user,data,group_id)


# admin as a member
@group_api.route('/remove_admin/<group_id>', methods=['POST'])
@validate_token(action='change_admin_as_member')
def change_to_member(current_user, group_id):
    data = request.get_json()
    return make_admin_to_user(current_user,data,group_id)


# reject join request gor group
@group_api.route('/requests/reject/<group_id>', methods=['DELETE'])
@validate_token(action='group_requests_reject')
def reject_req(current_user, group_id):
    data = request.get_json()
    return reject_join_request(current_user,group_id,data)


# accept group invitation
@group_api.route('/group_invitation', methods=['POST'])
@validate_token(action='accept_group_invitation')
def group_invitation(current_user):
    data = request.get_json()
    return accept_group_invitation(current_user,data)


# others users group list
@group_api.route('/groups_list/<user_id>' , methods=['GET'])
@validate_token(action='get_my_group_list')
def list_of_groups(current_user,user_id):
    return get_group_list(current_user,user_id)


