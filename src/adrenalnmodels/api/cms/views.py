import json
import os
from werkzeug.utils import redirect
from api.Users.models import Users, Verification, Device, UserDevice, Membership, Roles, Actions, RoleActions
from api.Users.services import create_user, update_user_basic_details, update_existiong_user, create_otp, verify_otp, \
    addDevice, generate_session_code, verify_password, update_user_info, update_user_details, get_basic_details
from api.cms.services import user_role_list, action_list, role_action_list, create_new_admin, get_user_list, \
    disable_user, create_post, get_user_list_fields, create_admin_post, inactive_users_list, \
    active_users_list, post_user_list, user_details, search_users_list, user_enable, user_post_details, admin_post_list, \
    approved_post_list, publisher_views_discarded_posts, search_post_by_date, \
    publisher_bucket_filter, publisher_approve_post, approve_posts, get_master_bucket_list, get_promotion_posts, \
    final_post_list, discard_final_post, get_membership_list, get_admin_post_list, update_sequence, unpublish_post, \
    inactive_post_list, reported_posts_list, approved_promotion_posts, discarded_promotion_posts, \
    feature_program_verification, get_all_program_list, search_reviewer_feed, search_discarded_post, search_final_post, \
    search_approved_post, user_friend_list_info, add_profile_terms_conditions, remove_profile_terms_conditions, \
    section_list, search_promotion_posts, search_approved_promotion_posts, search_discarded_promotion_posts, \
    friend_req_count, health_records_count, users_count, list_of_bucket, users_summary, reported_post_list, \
    approved_post_list_v2, publisher_views_discarded_posts_v2, final_post_list_v2, get_admin_post_list_v2, \
    approved_promotion_posts_v2, discarded_promotion_posts_v2, cms_user_details_update, search_admin_post, \
    create_admin_post_v2, mis_list_count,cms_user_enable,disable_cms_user

from api.exceptions.exceptions import Exception, Error
from common.connection import add_item, update_item, delete_item
from common.helper import update_session
from common.response import success, failure
from app import db, bcrypt
from middleware import auth
from middleware.auth import get_jwt, validate_token, token_required
from flask import request, g, url_for, session, Blueprint
# from flasgger import swag_from

cms_api = Blueprint('cms_api', __name__, url_prefix='/admin')


# create admin role
@cms_api.route('/role', methods=['POST'])
def create_role_action():
    data = request.json
    name = data['name']
    key = data['key']
    actions = data['actions']
    role = Roles.query.filter_by(key=key).first()
    if key and actions:
        role_action = RoleActions.query.filter_by(role_key=key, deleted_at=None).first()
        if not role:
            user_roles = Roles(name=name, key=key, membership_type='general')
            add_item(user_roles)
            if role_action:
                deleted = RoleActions(role_key=key, deleted_at=None).all()
                if deleted:
                    for data in deleted:
                        delete_item(data)
                for action in actions:
                    role_actions = RoleActions(role_key=key, action_key=action, status='active')
                    add_item(role_actions)
                return success('SUCCESS', {'message': 'Admin Role created'})
            else:
                for action in actions:
                    role_actions = RoleActions(role_key=key, action_key=action, status='active')
                    add_item(role_actions)
                return success('SUCCESS', {'message': 'Admin Role created'})
        else:
            if role_action:
                deleted = RoleActions.query.filter_by(role_key=key, deleted_at=None).all()
                if deleted:
                    for data in deleted:
                        delete_item(data)
                for action in actions:
                    role_actions = RoleActions(role_key=key, action_key=action, status='active')
                    add_item(role_actions)
                return success('SUCCESS', {'message': 'Admin Role Updated'})
            return success('SUCCESS', {'message': 'Admin Role already created'})
    else:
        return success('SUCCESS', {'message': 'Invalid Data'})


# get admin roles
@cms_api.route('/role', methods=['GET'])
def get_roles():
    try:
        return user_role_list()
    except Exception as e:
        return failure("Something went wrong.")


# update admin role
@cms_api.route('/role', methods=['PUT'])
def update_role_action():
    data = request.json
    name = data['name']
    key = data['key']
    actions = data['actions']
    role = Roles.query.filter_by(key=key).first()
    if role:
        for action in actions:
            role_action = RoleActions.query.filter_by(role_key=key, action_key=action).first()
            if not role_action:
                role_actions = RoleActions(role_key=key, action_key=action, status='active')
                add_item(role_actions)
            else:
                continue
        return success('SUCCESS', {'message': 'Admin Role updated'})


# add actions
@cms_api.route('/action', methods=['POST'])
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


# get action
@cms_api.route('/action', methods=['GET'])
def get_action():
    try:
        action_lst = action_list()
        return action_lst

    except Exception as e:
        return failure("Something went wrong.")


# get role_action
@cms_api.route('/role_action', methods=['POST'])
def get_role_action():
    try:
        data = request.get_json()
        action_lst = role_action_list(data)
        return action_lst

    except Exception as e:
        return failure("Something went wrong.")


# create ADMIN
@cms_api.route('/create_admin', methods=['POST'])
def create_admin():
    data = request.json
    return create_new_admin(data)


@cms_api.route('/user_list', methods=['GET'])
# @validate_token(action='user_list')
def user_list():
    data = request.args
    return get_user_list(data)


@cms_api.route('/user_list/fields', methods=['GET'])
def user_list_fields():
    return get_user_list_fields()


@cms_api.route('/disable_user/<user_id>', methods=['POST'])
@validate_token(action='disable_user')
def user_disable(current_user,user_id):
    data = request.json
    return disable_user(data, user_id)


@cms_api.route('/active_users', methods=['GET'])
@validate_token(action='active_user_list')
def active_users(current_user):
    data = request.json
    return active_users_list()


@cms_api.route('/inactive_users', methods=['GET'])
@validate_token(action='inactive_user_list')
def inactive_users(current_user):
    data = request.json
    return inactive_users_list()


@cms_api.route('/create_post', methods=['POST'])
@validate_token(action='create_post')
def add_post(current_user):
    data = request.form.get('data')
    data = json.loads(data)
    return create_admin_post_v2(data, current_user)




@cms_api.route('/user/detail/<user_id>', methods=['GET'])
def get_user_details(user_id):
    return user_details(user_id)


@cms_api.route('/search_user', methods=['GET'])
# @validate_token(action='search_user')
def search_user():
    try:
        return search_users_list()

    except Exception as e:
        return failure("Something went wrong.")


# post detail api
@cms_api.route('/post_detail/<post_id>', methods=['GET'])
@validate_token(action='post_detail')
def get_user_post_details(current_user,post_id):
    return user_post_details(current_user,post_id)


@cms_api.route('/post/user_list/', methods=['GET'])
def post_users_list():
    data = request.args
    return post_user_list(data)


# reviewer feed section
@cms_api.route('/reviewer/feed', methods=['GET'])
@validate_token(action='post_list')
def post_admin_list(current_user):
    data = request.args
    return admin_post_list(data,current_user)


@cms_api.route('/user/enable/<user_id>', methods=['POST'])
@validate_token(action='enable_user')
def user_enable_account(current_user, user_id):
    return user_enable(current_user, user_id)


@cms_api.route('/reviewer/approve_post', methods=['POST'])
@validate_token(action='approve_post')
def admin_post_approval(current_user):
    data = request.json
    return approve_posts(current_user,data)


# publisher approve/discard post
@cms_api.route('/publisher/approve_post', methods=['POST'])
@validate_token(action='publisher_approve_post')
def publisher_post_approval(current_user):
    data = request.json
    return publisher_approve_post(current_user,data)


# publisher feed api
@cms_api.route('/publisher/feed', methods=['GET'])
@validate_token(action='approved_post_list')
def publisher_feed(current_user):
    type = request.args.get('type')
    if type and type == 'discarded':
        return publisher_views_discarded_posts_v2(current_user)
    if type and type == 'approved':
        return approved_post_list_v2(current_user)
    if type and type == 'promotion_approved':
        return approved_promotion_posts_v2(current_user)
    if type and type == 'promotion_discarded':
        return discarded_promotion_posts_v2(current_user)


@cms_api.route('/publisher/bucket_feed', methods=['GET'])
@validate_token(action='bucket_post_list')
def publisher_bucket_feed(current_user):
    key = request.args.get('bucket_key')
    return publisher_bucket_filter(key,current_user)


@cms_api.route('/search_by_date', methods=['POST'])
@validate_token(action='search_post_by_date')
def search_user_post_by_date(current_user):
    try:
        data = request.json
        return search_post_by_date(current_user,data)

    except Exception as e:
        return failure("Something went wrong.")


@cms_api.route('/master_bucket', methods=['GET'])
def master_bucket():
    return get_master_bucket_list()


@cms_api.route('/promotion_post', methods=['GET'])
@validate_token(action="promotion_post_list")
def promotion_list(current_user):
    return get_promotion_posts(current_user)


@cms_api.route('/publisher/posts', methods=['GET'])
@validate_token(action='final_posts')
def final_posts(current_user):
    return final_post_list_v2(current_user)


@cms_api.route('/publisher/delete_post', methods=['POST'])
@validate_token(action='discard_final_post')
def publisher_discard_final_post(current_user):
    data = request.json
    return discard_final_post(current_user, data)


@cms_api.route('/cms_users', methods=['GET'])
def user_list_fis():
    return get_membership_list()


@cms_api.route('/admin_content', methods=['GET'])
def admin_list():
    return get_admin_post_list_v2()


@cms_api.route('/publisher/update_priority', methods=['PUT'])
@validate_token(action='update_post')
def update_post_publisher(current_user):
    data = request.json
    return update_sequence(current_user,data)


@cms_api.route('/post/unpublish', methods=['POST'])
@validate_token(action='unpublish_post')
def admin_unpublish_post(current_user):
    data = request.json
    return unpublish_post(current_user, data)


@cms_api.route('/inactive_post/<user_id>', methods=['GET'])
@validate_token(action='inactive_status')
def inactive_list(current_user,user_id):
    return inactive_post_list(current_user,user_id)


@cms_api.route('/get_reported_posts/<post_id>', methods=['GET'])
@validate_token(action='get_reported_post_list')
def get_report(current_user,post_id):
    return reported_posts_list(current_user,post_id)


@cms_api.route('/feature_programme', methods=['POST'])
@validate_token(action="feature_programme")
def program_verifcation(current_user):
    data = request.get_json()
    return feature_program_verification(current_user,data)


@cms_api.route('/programme_list', methods=['GET'])
@validate_token(action="list_program_details")
def all_program_list(current_user):
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()

    is_admin = Membership.query.filter_by(user_id=current_user.id, membership_status='active', membership_type='admin',
                                          deleted_at=None).first()
    if existing_user:
        if is_admin:
            return get_all_program_list()
        else:
            return failure('User is not admin')
    else:
        return success('SUCCESS', meta={'message': 'Invalid User'})


@cms_api.route('/search_approved_posts', methods=['GET'])
@validate_token(action='search_approved_posts')
def approved_post(current_user):
    return search_approved_post(current_user)


@cms_api.route('/search_final_post', methods=['GET'])
@validate_token(action='search_final_post')
def search_final(current_user):
    return search_final_post(current_user)


@cms_api.route('/search_discarded_post', methods=['GET'])
@validate_token(action='search_discarded_post')
def search_discarded(current_user):
    return search_discarded_post(current_user)


@cms_api.route('/search_reviewer_feed', methods=['GET'])
@validate_token(action='search_reviewer_feed')
def search_reviewer_feed_list(current_user):
    return search_reviewer_feed(current_user)


@cms_api.route('/followers_count/<user_id>',methods=['GET'])
@validate_token(action='all_frd_rqs')
def friend_count(current_user,user_id):
    return user_friend_list_info(current_user,user_id)


@cms_api.route('/terms_conditions', methods=['POST'])
@validate_token(action="add_terms_conditions")
def add_terms_and_conditions(current_user):
    data = request.get_json()
    return add_profile_terms_conditions(current_user, data)


@cms_api.route('/remove_terms_conditions/<section_id>', methods=['DELETE'])
@validate_token(action="remove_terms_conditions")
def delete_terms_and_conditions(current_user,section_id):
    return remove_profile_terms_conditions(current_user, section_id)


@cms_api.route('/section_list', methods=['GET'])
@validate_token(action="section_list")
def get_section_list(current_user):
    return section_list(current_user)


@cms_api.route('/search_promotion_post', methods=['GET'])
@validate_token(action="search_promotion_post")
def search_promotion(current_user):
    return search_promotion_posts(current_user)


@cms_api.route('/search_approved_promotion_posts', methods=['GET'])
@validate_token(action="search_approved_promotion_posts")
def search_approved_promotion(current_user):
    return search_approved_promotion_posts(current_user)


@cms_api.route('/search_discarded_promotion_posts', methods=['GET'])
@validate_token(action="search_discarded_promotion_posts")
def search_discarded_promotion(current_user):
    return search_discarded_promotion_posts(current_user)


@cms_api.route('/cms_users_count', methods=['GET'])
@validate_token(action="users_count")
def get_users_count(current_user):
    return users_count(current_user)


@cms_api.route('/friend_requests',methods=['POST'])
@validate_token(action='number_of_req_list')
def friend_rqs(current_user):
    data = request.json
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    is_admin = Membership.query.filter_by(user_id=current_user.id, membership_status='active', membership_type='admin',
                                          deleted_at=None).first()
    if existing_user:
        if is_admin:
            return friend_req_count(current_user,data)
        else:
            return success('SUCCESS',meta={'message':'access denied'})
    else:
        return success('SUCCESS', meta={'message': 'user does not exist'})


@cms_api.route('/health_record',methods=['POST'])
@validate_token(action='health_records_count')
def records_count(current_user):
    data = request.json
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    is_admin = Membership.query.filter_by(user_id=current_user.id, membership_status='active', membership_type='admin',
                                          deleted_at=None).first()
    if existing_user:
        if is_admin:
            return health_records_count(current_user,data)
        else:
            return success('SUCCESS',meta={'message':'access denied'})
    else:
        return success('SUCCESS', meta={'message': 'user does not exist'})


@cms_api.route('/bucket_list',methods=['POST'])
@validate_token(action='mis_bucket_count')
def backet_list_count(current_user):
    data = request.json
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    is_admin = Membership.query.filter_by(user_id=current_user.id, membership_status='active', membership_type='admin',
                                          deleted_at=None).first()

    if existing_user:
        if is_admin:
            return list_of_bucket(current_user,data)
        else:
            return success('SUCCESS',meta={'message':'access denied'})
    else:
        return success('SUCCESS', meta={'message': 'user does not exist'})


@cms_api.route('/users_summary',methods=['POST'])
@validate_token(action='mis_bucket_count')
def users_summarys(current_user):
    data = request.json
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    is_admin = Membership.query.filter_by(user_id=current_user.id, membership_status='active', membership_type='admin',
                                          deleted_at=None).first()

    if existing_user:
        if is_admin:
            return users_summary()
        else:
            return success('SUCCESS',meta={'message':'access denied'})
    else:
        return success('SUCCESS', meta={'message': 'user does not exist'})


@cms_api.route('/report_posts',methods=['GET'])
@validate_token(action='mis_bucket_count')
def list_of_reported_posts(current_user):
    data = request.json
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    is_admin = Membership.query.filter_by(user_id=current_user.id, membership_status='active', membership_type='admin',
                                          deleted_at=None).first()

    if existing_user:
        if is_admin:
            return reported_post_list(current_user)
        else:
            return success('SUCCESS',meta={'message':'access denied'})
    else:
        return success('SUCCESS', meta={'message': 'Reported Post List '})


@cms_api.route('/update_cms_user_details/<user_id>', methods=['PUT'])
@validate_token(action='update_cms_user_detaials')
def update_cms_details(current_user,user_id):
    try:
        data = request.json
        existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
        is_admin = Membership.query.filter_by(user_id=current_user.id, membership_status='active', membership_type='admin',role='super_admin',
                                              deleted_at=None).first()
        if existing_user:
            if is_admin:
                return cms_user_details_update(current_user,user_id,data)
            else:
                return success('SUCCESS', meta={'message': 'access denied'})
        else:
            return success('SUCCESS', meta={'message': 'user does not exist'})
    except Exception as e:
        return failure("Something went wrong.")


@cms_api.route('/search_admin_post', methods=['GET'])
@validate_token(action='search_admin_post_lists')
def search_admin_post_list(current_user):
    return search_admin_post(current_user)


@cms_api.route('/profile_mis', methods=['POST'])
@validate_token(action='profile_mis_count')
def as_of_data(current_user):
    data = request.json
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    is_admin = Membership.query.filter_by(user_id=current_user.id, membership_status='active', membership_type='admin',
                                          deleted_at=None).first()

    if existing_user:
        if is_admin:
            return mis_list_count(current_user, data)
        else:
            return success('SUCCESS', meta={'message': 'access denied'})
    else:
        return success('SUCCESS', meta={'message': 'user does not exist'})


@cms_api.route('/disable_cms_user/<user_id>', methods=['POST'])
@validate_token(action='disable_cms_user')
def user_cms_disable(current_user, user_id):
    return disable_cms_user(current_user, user_id)


@cms_api.route('/cms_user/enable/<user_id>', methods=['POST'])
@validate_token(action='enable_cms_user')
def cms_user_enable_account(current_user, user_id):
    return cms_user_enable(current_user, user_id)
