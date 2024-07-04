import datetime
import json
from operator import or_, and_, itemgetter

from flask import jsonify, request
from sqlalchemy import func
from sqlalchemy.testing.pickleable import User

from api.Group.models import Group, GroupMembers
from api.Post.models import Post, MasterActivity, UserBettings, BettingPost, PostCustomVisibility, PostReact, \
    MasterBettingItems
from api.Users.models import Users
from api.contact.models import Contact
from api.profile.models import MasterSports, Sport_level
from app import db
from common.connection import add_item, update_item, _query_execution, delete_item
from common.response import success, failure


def get_friend_suggestion(current_user, data):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    offset = per_page * (page - 1)
    contacts = []
    blocklist = []
    pending_req = []
    my_pending_req = []
    friends_friend = []
    my_blocklist = Contact.query.filter_by(user_id=current_user.id, friend_status='blocked', deleted_at=None).all()
    if my_blocklist:
        for blocked_user in my_blocklist:
            blocklist.append(str(blocked_user.contact_id))

    my_friends = Contact.query.filter_by(user_id=current_user.id, is_following=True, deleted_at=None).all()
    pending_requests = Contact.query.filter_by(user_id=current_user.id, friend_status='pending', deleted_at=None).all()
    if pending_requests:
        for req in pending_requests:
            pending_req.append(str(req.contact_id))
    my_pending_requests = Contact.query.filter_by(contact_id=current_user.id, friend_status='pending',
                                                  deleted_at=None).all()
    if my_pending_requests:
        for data in my_pending_requests:
            pending_req.append(str(data.user_id))

    if my_friends:
        for my_friend in my_friends:
            contacts.append(str(my_friend.contact_id))
        all_friends = db.session.query(Contact).filter(Contact.user_id.in_(contacts),
                                                       Contact.friend_status == 'friends',
                                                       Contact.contact_id != current_user.id,
                                                       Contact.deleted_at == None).all()

        friends = db.session.query(Contact).filter(Contact.user_id.in_(contacts),
                                                   Contact.friend_status == 'friends',
                                                   Contact.contact_id != current_user.id, Contact.deleted_at == None,
                                                   Contact.contact_id.notin_(blocklist),
                                                   Contact.contact_id.notin_(pending_req)).order_by(func.random()).paginate(
            page=page,
            per_page=per_page,
            error_out=False)

        friends = friends.items
        total_record = len(all_friends)
        # total_pages = total_record // per_page + 1
        if friends:
            result = []
            for friend in friends:
                if str(friend.contact_id) not in friends_friend:
                    friends_friend.append(str(friend.contact_id))
                # friends_friend = friend.contact_id
            for data in friends_friend:
                if str(data) not in contacts:
                    user = Users.query.filter_by(id=data,user_deleted_at=None,deleted_at=None).first()
                    friend_suggestions = {}
                    friend_suggestions['id'] = data
                    friend_suggestions['name'] = user.first_name
                    friend_suggestions['profile_image'] = user.profile_image
                    friend_suggestions['can_follows'] = user.can_follows
                #     # if friends_friend in contacts:
                    is_contact = Contact.query.filter_by(user_id=current_user.id, contact_id=data,
                                                             deleted_at=None).first()
                    if is_contact:
                        friend_suggestions['is_following'] = is_contact.is_following
                    else:
                        friend_suggestions['is_following'] = False
                    result.append(friend_suggestions)
            return success("SUCCESS", result, meta={"message": "Friend Suggestion List 1",
                                                        'page_info': {'current_page': page,
                                                                      'limit': per_page}})
        else:
            users = db.session.query(Users).filter(
                or_(Users.work_place == current_user.work_place, Users.city == current_user.city),
                Users.id.notin_(blocklist), Users.id.notin_(pending_req),
                Users.id.notin_(my_pending_req),Users.id.notin_(contacts)).order_by(func.random()).paginate(
                page=page,
                per_page=per_page,
                error_out=False)
            users = users.items
            total_record = len(users)
            total_pages = total_record // per_page + 1
            if users:
                result = []
                for user in users:
                    if user.id == current_user.id:
                        continue
                    friend_suggestions = {}
                    friend_suggestions['id'] = user.id
                    friend_suggestions['name'] = user.first_name
                    friend_suggestions['profile_image'] = user.profile_image
                    friend_suggestions['can_follows'] = user.can_follows
                    friend_suggestions['is_following'] = False
                    result.append(friend_suggestions)
                return success("SUCCESS", result, meta={"message": "Friend Suggestion List 2"})
            else:
                users = db.session.query(Users).filter(Users.id.notin_(blocklist), Users.id.notin_(pending_req),
                                                       Users.id.notin_(my_pending_req),Users.id.notin_(contacts)).order_by(func.random()).paginate(
                    page=page,
                    per_page=per_page,
                    error_out=False)
                users = users.items
                if users:
                    result = []
                    for user in users:
                        if user.id == current_user.id:
                            continue
                        friend_suggestions = {}
                        friend_suggestions['id'] = user.id
                        friend_suggestions['name'] = user.first_name
                        friend_suggestions['profile_image'] = user.profile_image
                        friend_suggestions['can_follows'] = user.can_follows
                        friend_suggestions['is_following'] = False
                        result.append(friend_suggestions)
                # total_record = len(users)
                # total_pages = total_record // per_page + 1
                return success("SUCCESS", meta={"message": "Friend Suggestion List",
                                                'page_info': {'current_page': page, 'limit': per_page}})
    else:
        users = Users.query.filter(
            or_(Users.work_place == current_user.work_place, Users.city == current_user.city),
            Users.id.notin_(pending_req), Users.id.notin_(blocklist),
            Users.id.notin_(my_pending_req),Users.user_deleted_at==None,Users.deleted_at==None).order_by(func.random()).paginate(
            page=page,
            per_page=per_page,
            error_out=False)

        users = users.items
        total_record = len(users)
        total_pages = total_record // per_page + 1
        if users:
            result = []
            for user in users:
                if user.id == current_user.id:
                    continue
                friend_suggestions = {}
                friend_suggestions['id'] = user.id
                friend_suggestions['name'] = user.first_name
                friend_suggestions['profile_image'] = user.profile_image
                friend_suggestions['can_follows'] = user.can_follows
                friend_suggestions['is_following'] = False
                result.append(friend_suggestions)
            return success("SUCCESS", result,
                           meta={"message": "Friend Suggestion List 3", 'page_info': {'current_page': page,
                                                                                      'limit': per_page}})
        else:
            users = db.session.query(Users).filter(Users.id.notin_(blocklist), Users.id.notin_(pending_req),
                                                   Users.id.notin_(my_pending_req),Users.id.notin_(contacts)).order_by(func.random()).paginate(
                page=page,
                per_page=per_page,
                error_out=False)
            users = users.items
            if users:
                result = []
                for user in users:
                    if user.id == current_user.id:
                        continue
                    friend_suggestions = {}
                    friend_suggestions['id'] = user.id
                    friend_suggestions['name'] = user.first_name
                    friend_suggestions['profile_image'] = user.profile_image
                    friend_suggestions['can_follows'] = user.can_follows
                    friend_suggestions['is_following'] = False
                    result.append(friend_suggestions)
            # total_record = len(users)
            # total_pages = total_record // per_page + 1
            return success("SUCCESS", meta={"message": "Friend Suggestion List",
                                            'page_info': {'current_page': page, 'limit': per_page}})


def get_friend_suggestion_v2(current_user, data):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)

    contacts = []
    blocklist = []

    pending_req = []
    my_following = []
    same_sports = []

    user_sports = Sport_level.query.filter_by(user_id=current_user.id, primary_deleted_at=None,
                                              secondary_deleted_at=None).all()
    if user_sports:
        for item in user_sports:
            users_same_sports = Sport_level.query.filter_by(sport_id=item.sport_id, deleted_at=None).all()
            if users_same_sports:
                for same in users_same_sports:
                    same_sports.append(same.user_id)

    my_follow_list = Contact.query.filter_by(user_id=current_user.id, is_following=True, deleted_at=None).all()
    if my_follow_list:
        for follow in my_follow_list:
            my_following.append(str(follow.contact_id))
    my_blocklist = Contact.query.filter_by(user_id=current_user.id, friend_status='blocked', deleted_at=None).all()
    if my_blocklist:
        for blocked_user in my_blocklist:
            blocklist.append(str(blocked_user.contact_id))

    my_friends = Contact.query.filter_by(user_id=current_user.id, friend_status='friends',
                                         deleted_at=None).all()
    pending_requests = Contact.query.filter_by(user_id=current_user.id, friend_status='pending', deleted_at=None).all()
    if pending_requests:
        for req in pending_requests:
            pending_req.append(str(req.contact_id))

    if my_friends:
        for my_friend in my_friends:
            contacts.append(str(my_friend.contact_id))
        friend_friends = db.session.query(Contact).filter(Contact.user_id.in_(contacts),
                                                          Contact.friend_status == 'friends',
                                                          Contact.contact_id.notin_(contacts),
                                                          Contact.contact_id != current_user.id,
                                                          Contact.deleted_at == None).all()

        list = []
        result = []
        if friend_friends:
            for data in friend_friends:
                list.append(data.contact_id)
            id_count = len(list)

            if id_count <= 10:
                influencer_data = db.session.query(Users).filter(Users.id.notin_(list),
                                                                 or_(Users.business_account == True,
                                                                     Users.can_follows == True),
                                                                 Users.id.notin_(pending_req),
                                                                 Users.id.notin_(contacts), Users.id.notin_(blocklist),
                                                                 Users.id.notin_(my_following),
                                                                 Users.id != current_user.id, Users.deleted_at == None,
                                                                 Users.user_deleted_at == None,
                                                                 or_(Users.city == current_user.city,
                                                                     Users.id.in_(same_sports)),
                                                                 Users.id.notin_(pending_req)).all()
                if influencer_data:
                    for data in influencer_data:
                        list.append(data.id)

            if list:
                total_record = len(list)
                total_pages = total_record // per_page + 1

                if total_record != 0:
                    if page > total_pages:
                        return success("SUCCESS",
                                       meta={"message": "No data", 'page_info': {'current_page': page,
                                                                                 'limit': per_page,
                                                                                 'total_record': total_record,
                                                                                 'total_pages': total_pages}})
                final_data = Users.query.filter(
                    Users.id.in_(list)).order_by(func.random()).paginate(
                    page=page,
                    per_page=per_page,
                    error_out=False)
                final_data = final_data.items
                if final_data:
                    for user in final_data:
                        friend_suggestions = {}
                        friend_suggestions['id'] = user.id
                        friend_suggestions['name'] = user.first_name
                        friend_suggestions['profile_image'] = user.profile_image
                        friend_suggestions['can_follows'] = user.can_follows
                        is_contact = Contact.query.filter_by(user_id=current_user.id, contact_id=data.id,
                                                             deleted_at=None).first()
                        if is_contact:
                            friend_suggestions['is_following'] = is_contact.is_following
                        else:
                            friend_suggestions['is_following'] = False
                        result.append(friend_suggestions)
                    newlist = sorted(result, key=lambda x: x['name'].lower())
                    return success("SUCCESS", newlist,
                                   meta={"message": "Friend Suggestion", 'page_info': {'current_page': page,
                                                                                       'limit': per_page,
                                                                                       'total_record': total_record,
                                                                                       'total_pages': total_pages}})
        else:
            newlist, total_pages, total_record = city_or_sports_based_users(current_user, page, per_page, blocklist,
                                                                            pending_req, my_following,contacts,same_sports)
            if newlist:
                return success("SUCCESS", newlist,
                               meta={"message": "Friend Suggestion", 'page_info': {'current_page': page,
                                                                                   'limit': per_page,
                                                                                   'total_record': total_record,
                                                                                   'total_pages': total_pages}})

            else:
                newlist, total_pages, total_record = influencers_list(current_user, page, per_page, blocklist,
                                                                      pending_req, my_following,same_sports)
                if newlist:
                    return success("SUCCESS", newlist, meta={"message": "Friend Suggestion",
                                                             'page_info': {'current_page': page, 'limit': per_page,
                                                                           'total_record': total_record,
                                                                           'total_pages': total_pages}})
                else:
                    return success("SUCCESS", meta={"message": "No Suggestion",
                                                    'page_info': {'current_page': page, 'limit': per_page,
                                                                  'total_record': total_record,
                                                                  'total_pages': total_pages}})
    elif not my_friends:
        newlist, total_pages, total_record = city_or_sports_based_users(current_user, page, per_page, blocklist,
                                                                        pending_req, my_following,contacts,same_sports)
        if newlist:
            return success("SUCCESS", newlist,
                           meta={"message": "Friend Suggestion", 'page_info': {'current_page': page,
                                                                               'limit': per_page,
                                                                               'total_record': total_record,
                                                                               'total_pages': total_pages}})
        else:
            newlist, total_pages, total_record = influencers_list(current_user, page, per_page, blocklist, pending_req,
                                                                  my_following,same_sports)
            if newlist:
                return success("SUCCESS", newlist, meta={"message": "Friend Suggestion List",
                                                         'page_info': {'current_page': page, 'limit': per_page,
                                                                       'total_record': total_record,
                                                                       'total_pages': total_pages}})
            else:
                return success("SUCCESS", meta={"message": "No Suggestion",
                                                'page_info': {'current_page': page, 'limit': per_page,
                                                              'total_record': total_record,
                                                              'total_pages': total_pages}})
    else:
        newlist, total_pages, total_record = influencers_list(current_user, page, per_page, blocklist, pending_req,
                                                              my_following,same_sports)
        if newlist:
            return success("SUCCESS", newlist, meta={"message": "Friend suggenstion",
                                                     'page_info': {'current_page': page, 'limit': per_page,
                                                                   'total_record': total_record,
                                                                   'total_pages': total_pages}})
        else:
            return success("SUCCESS", meta={"message": "No Suggestion",
                                            'page_info': {'current_page': page, 'limit': per_page,
                                                          'total_record': total_record,
                                                          'total_pages': total_pages}})

def city_or_sports_based_users(current_user, page, per_page, blocklist, pending_req, my_following,contacts,same_sports):
    users_count = Users.query.filter(
        Users.city == current_user.city,
        Users.id.notin_(pending_req), Users.id.notin_(blocklist),
        Users.id.notin_(my_following), Users.id != current_user.id, Users.id.notin_(contacts)).all()
    list = []
    if users_count:
        for data in users_count:
            list.append(data.id)
    id_count = len(list)

    total_record = len(users_count)
    total_pages = total_record // per_page + 1
    if total_record != 0:
        if page > total_pages:
            return success("SUCCESS",
                           meta={"message": "No data", 'page_info': {'current_page': page,
                                                                     'limit': per_page,
                                                                     'total_record': total_record,
                                                                     'total_pages': total_pages}})

    if id_count < 10:
        influencer_data = db.session.query(Users).filter(Users.id.notin_(list),
                                                         or_(Users.business_account == True,
                                                             Users.can_follows == True),
                                                         Users.id.notin_(pending_req),
                                                         Users.id.notin_(contacts), Users.id.notin_(blocklist),
                                                         Users.id.notin_(my_following),
                                                         Users.id != current_user.id, Users.deleted_at == None,
                                                         Users.user_deleted_at == None,
                                                         or_(Users.city == current_user.city,
                                                             Users.id.in_(same_sports)),
                                                         Users.id.notin_(pending_req)).all()

        if influencer_data:
            for data in influencer_data:
                list.append(data.id)

    users = Users.query.filter(Users.id.in_(list)).order_by(func.random()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    users = users.items
    result = []

    if users:
        for user in users:
            friend_suggestions = {}
            friend_suggestions['id'] = user.id
            friend_suggestions['name'] = user.first_name
            friend_suggestions['profile_image'] = user.profile_image
            friend_suggestions['can_follows'] = user.can_follows
            friend_suggestions['is_following'] = False
            result.append(friend_suggestions)
    if result:
        newlist = sorted(result, key=lambda x: x['name'].lower())
        return newlist, total_pages, total_record
    else:
        return None, None, None


def influencers_list(current_user, page, per_page, blocklist, pending_req, my_following,same_sports):

    all_users = db.session.query(Users).filter(
        or_(Users.business_account == True, Users.can_follows == True), Users.user_deleted_at == None,
                                                                        Users.deleted_at == None,
        Users.id.notin_(my_following),
        Users.id.notin_(blocklist), Users.id != current_user.id, Users.id.notin_(pending_req),
        or_(Users.city == current_user.city, Users.id.in_(same_sports)),
        Users.id.notin_(pending_req)).all()
    users = db.session.query(Users).filter(
        or_(Users.business_account == True, Users.can_follows == True), Users.user_deleted_at == None,
                                                                        Users.id != current_user.id,
                                                                        Users.deleted_at == None,
        Users.id.notin_(my_following),
        Users.id.notin_(blocklist), Users.id.notin_(pending_req),
        or_(Users.city == current_user.city, Users.id.in_(same_sports)),
        Users.id.notin_(pending_req)).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    users = users.items
    result = []
    total_record = len(all_users)
    total_pages = total_record // per_page + 1
    if total_record != 0:
        if page > total_pages:
            return success("SUCCESS",
                           meta={"message": "No data", 'page_info': {'current_page': page,
                                                                     'limit': per_page,
                                                                     'total_record': total_record,
                                                                     'total_pages': total_pages}})
    if users:
        for user in users:
            if user.id == current_user:
                continue
            friend_suggestions = {}
            friend_suggestions['id'] = user.id
            friend_suggestions['name'] = user.first_name
            friend_suggestions['profile_image'] = user.profile_image
            friend_suggestions['can_follows'] = user.can_follows
            friend_suggestions['is_following'] = False
            result.append(friend_suggestions)

        # return result
    if result:
        newlist = sorted(result, key=lambda x: x['name'].lower())
        return newlist, total_pages, total_record
    else:
        return None, None, None



def get_group_suggestion(current_user, data):
    if data:
        page, per_page = data.get('page'), data.get('limit')
    else:
        page = 1
        per_page = 10
    contacts = []
    my_group_id = []
    my_friends = Contact.query.filter_by(user_id=current_user.id, friend_status='friends',deleted_at=None).all()
    for my_friend in my_friends:
        contacts.append(my_friend.contact_id)
    mygroup_ids = GroupMembers.query.filter_by(user_id=current_user.id, deleted_at=None,status='active').all()
    for data in mygroup_ids:
        my_group_id.append(data.group_id)
    if contacts:
        my_groups = db.session.query(GroupMembers).filter(GroupMembers.user_id.in_(contacts),
                                                          GroupMembers.type == 'admin',
                                                          GroupMembers.group_id.notin_(my_group_id),
                                                          GroupMembers.user_id != current_user.id,
                                                          GroupMembers.deleted_at == None).distinct(GroupMembers.group_id).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        groups = my_groups.items
        if groups:
            result = []
            for data in groups:
                group_name = {}
                visibility=''
                user_data = Users.query.filter_by(id=data.user_id,deleted_at=None,user_deleted_at=None).first()
                members = GroupMembers.query.filter_by(group_id=data.group_id,status='active',deleted_at=None).count()
                group_details = Group.query.filter_by(id=data.group_id,deleted_at=None).first()
                if group_details.visibility=='group_members':
                    visibility = 'closed'
                if group_details.visibility == 'all':
                    visibility = 'open'
                group_name['group_name'] = group_details.group_name
                group_name['group_id'] = data.group_id
                group_name['description'] = group_details.description
                group_name['sport'] = group_details.sport_type
                group_name['image'] = group_details.image
                group_name['city'] = group_details.city
                group_name['owner_name'] = user_data.first_name
                group_name['members_count'] = members
                group_name['visibility'] = visibility
                result.append(group_name)
            return success("SUCCESS", result, meta={"message": "Group Suggestion List",
                                                    'page_info': {'current_page': page, 'limit': per_page}})
        else:
            my_groups = db.session.query(GroupMembers).filter(GroupMembers.type == 'admin',
                                                              GroupMembers.group_id.notin_(my_group_id),
                                                              GroupMembers.user_id != current_user.id,
                                                              GroupMembers.deleted_at == None).distinct(GroupMembers.group_id).paginate(
                page=page,
                per_page=per_page,
                error_out=False)
            groups = my_groups.items
            if groups:
                result = []
                for data in groups:
                    group_name = {}
                    visibility=''
                    user_data = Users.query.filter_by(id=data.user_id,deleted_at=None,user_deleted_at=None).first()
                    members = GroupMembers.query.filter_by(group_id=data.group_id,deleted_at=None).count()
                    group_details = Group.query.filter_by(id=data.group_id,deleted_at=None).first()
                    if group_details.visibility == 'group_members':
                        visibility = 'closed'
                    if group_details.visibility == 'all':
                        visibility = 'open'
                    group_name['group_name'] = group_details.group_name
                    group_name['group_id'] = data.group_id
                    group_name['description'] = group_details.description
                    group_name['sport'] = group_details.sport_type
                    group_name['image'] = group_details.image
                    group_name['city'] = group_details.city
                    group_name['owner_name'] = user_data.first_name
                    group_name['members_count'] = members
                    group_name['visibility'] = visibility
                    result.append(group_name)
                return success("SUCCESS", result, meta={"message": "Group Suggestion List",
                                                        'page_info': {'current_page': page,
                                                                      'limit': per_page}})
            else:
                return success("SUCCESS", meta={"message": "No Group Suggestions"})
    else:
        my_groups = db.session.query(GroupMembers).filter(GroupMembers.type == 'admin',
                                                          GroupMembers.group_id.notin_(my_group_id),
                                                          GroupMembers.user_id != current_user.id,
                                                          GroupMembers.deleted_at == None).distinct(GroupMembers.group_id).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        groups = my_groups.items
        if groups:
            result = []
            for data in groups:
                group_name = {}
                user_data = Users.query.filter_by(id=data.user_id,deleted_at=None,user_deleted_at=None).first()
                members = GroupMembers.query.filter_by(group_id=data.group_id,deleted_at=None).count()
                group_details = Group.query.filter_by(id=data.group_id,deleted_at=None).first()
                group_name['group_name'] = group_details.group_name
                group_name['group_id'] = data.group_id
                group_name['description'] = group_details.description
                group_name['sport'] = group_details.sport_type
                group_name['image'] = group_details.image
                group_name['city'] = group_details.city
                group_name['owner_name'] = user_data.first_name
                group_name['members_count'] = members
                group_name['visibility'] = group_details.visibility
                result.append(group_name)
            return success("SUCCESS", result, meta={"message": "Group Suggestion List",
                                                    'page_info': {'current_page': page, 'limit': per_page}})
        else:
            return success("SUCCESS", meta={"message": "No Group Suggestions"})


def get_group_suggestion_v2(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    final_group_suggestion = []
    contacts = []
    my_group_id = []

    # getting current user groups
    mygroup_ids = GroupMembers.query.filter_by(user_id=current_user.id, deleted_at=None, status='active').all()
    if mygroup_ids:
        for data in mygroup_ids:
            my_group_id.append(data.group_id)

    # friends' groups
    my_friends = Contact.query.filter_by(user_id=current_user.id, friend_status='friends', deleted_at=None).all()
    if my_friends:
        for my_friend in my_friends:
            contacts.append(my_friend.contact_id)
    if contacts:
        my_groups = db.session.query(GroupMembers).filter(GroupMembers.user_id.in_(contacts),
                                                          GroupMembers.group_id.notin_(my_group_id),
                                                          GroupMembers.user_id != current_user.id,
                                                          GroupMembers.deleted_at == None).distinct(
            GroupMembers.group_id).all()
        if my_groups:
            for group in my_groups:
                final_group_suggestion.append(group.group_id)
    # city based groups
    city_group = db.session.query(Group).filter(Group.id.notin_(my_group_id),
                                                Group.id.notin_(final_group_suggestion),
                                                Group.city == current_user.city,
                                                Group.deleted_at == None).all()
    if city_group:
        for city in city_group:
            final_group_suggestion.append(city.id)

    # sport based group
    sports_types = []
    my_sports = Sport_level.query.filter_by(user_id=current_user.id, primary_deleted_at=None,
                                            secondary_deleted_at=None).all()
    # ===> getting group types
    if my_sports:
        for sports in my_sports:
            sport = MasterSports.query.filter_by(id=sports.sport_id, deleted_at=None).first()
            if sport:
                sports_types.append(sport.name)
    if sports_types:
        sport_group = db.session.query(Group).filter(Group.id.notin_(my_group_id),
                                                     Group.id.notin_(final_group_suggestion),
                                                     Group.sport_type.in_(sports_types),
                                                     Group.deleted_at == None).all()
        if sport_group:
            for sport_data in sport_group:
                final_group_suggestion.append(sport_data.id)

    # public groups
    public_groups = db.session.query(Group).filter(Group.id.notin_(my_group_id),
                                                   Group.id.notin_(final_group_suggestion),
                                                   Group.visibility == 'all',
                                                   Group.deleted_at == None).all()
    if public_groups:
        for public in public_groups:
            final_group_suggestion.append(str(public.id))

    if final_group_suggestion:
        total_records = len(final_group_suggestion)
        total_pages = total_records // per_page + 1

        group_suggestion = db.session.query(Group).filter(Group.id.in_(final_group_suggestion)).order_by(
            func.random()).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        group_suggestion = group_suggestion.items
        if group_suggestion:
            result = []
            for data in group_suggestion:
                group_name = {}
                visibility = ''
                # group_details = Group.query.filter_by(id=data.id, deleted_at=None).first()
                # if group_details:
                user_data = Users.query.filter_by(id=data.user_id, deleted_at=None,
                                                  user_deleted_at=None).first()
                members = GroupMembers.query.filter_by(group_id=data.id, status='active',
                                                       deleted_at=None).count()
                if user_data and members:
                    if data.visibility == 'group_members':
                        visibility = 'closed'
                    if data.visibility == 'all':
                        visibility = 'open'
                    group_name['group_name'] = data.group_name
                    group_name['group_id'] = data.id
                    group_name['description'] = data.description
                    group_name['sport'] = data.sport_type
                    group_name['image'] = data.image
                    group_name['owner_name'] = user_data.first_name
                    group_name['members_count'] = members
                    group_name['visibility'] = visibility
                    result.append(group_name)
            # SORTING RANDOMLY PICKED DATA
            result = sorted(result, key=lambda x: x['group_name'].lower())
            return success("SUCCESS", result, meta={"message": "Group Suggestion List",
                                                    'page_info': {'current_page': page, 'limit': per_page,
                                                                  'total_records': total_records,
                                                                  'total_pages': total_pages
                                                                  }})
    else:
        return success("SUCCESS", meta={"message": "No Group Suggestion",
                                        'page_info': {'current_page': page, 'limit': per_page}})
