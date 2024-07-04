import datetime

from sqlalchemy import or_

from api.Group.models import Group, GroupMembers
from api.Post.models import PostReact
from api.Users.models import Users, Membership
from api.Users.services import get_user_profile_details
from api.comment.models import Comment
from api.contact.models import Contact
from api.notification.models import Notification
from api.notification.services import send_queue_message
from app import db
from common.connection import update_item, add_item, delete_item, _query_execution
from common.response import failure, success
from flask import request

from config import PUSH_NOTIFICATION_URL


def group_create(current_user,data):
    group_name = data['group_name']
    sport_type = data['sport']
    city = data['city']
    description = data['description']
    visibility = data['visibility']
    members = data.get('members', None)
    admin_list = data.get('admin', None)
    existing_group = Group.query.filter_by(group_name=group_name,deleted_at=None).first()
    if existing_group:
        return failure("group with this name already exists")
    group_details = Group(user_id=current_user.id, group_name=group_name, sport_type=sport_type, city=city,
                          description=description, visibility=visibility)
    group = add_item(group_details)
    group_id = group.id
    group_member = GroupMembers(user_id=current_user.id, group_id=group_id, type='admin', status='active')
    add_item(group_member)
    fcm_token = []
    if members:
        for member in members:
            user_membership = Membership.query.filter_by(user_id=member, deleted_at=None).first()
            fcm_token.append(user_membership.fcm_token)
            # send notification
            def send_notification():
                # send notification
                user_membership = Membership.query.filter_by(user_id=member, deleted_at=None).first()
                message = current_user.first_name + " has sent you a group invite"
                queue_url = PUSH_NOTIFICATION_URL
                fcm_token = []
                fcm_token.append(user_membership.fcm_token)
                payload = {}
                payload['id'] = str(group_id)
                payload['current_user'] = str(current_user.id)
                payload['message'] = message
                payload['title'] = "Group Invite"
                payload['fcm_token'] = fcm_token
                payload['screen_type'] = 'GROUP_DETAIL'
                payload['responder_id'] = None
                send_queue_message(queue_url, payload)
                # post in-app notification
                screen_info = {}
                data = {}
                screen_info['screen_type'] = 'GROUP_DETAIL'
                screen_info['id'] = str(group_id)
                data['meta_data'] = screen_info
                add_notification = Notification(user_id=member, type='group', title=payload['title'],
                                                description=message, read_status=False, meta_data=data['meta_data'],c_user=current_user.id)
                add_item(add_notification)

            if admin_list and member in admin_list:
                add_admin = GroupMembers(user_id=member, group_id=group_id, type='admin', status='invited')
                add_item(add_admin)
                send_notification()
            if member not in admin_list:
                add_members = GroupMembers(user_id=member, group_id=group_id, type='user', status='invited')
                add_item(add_members)
                send_notification()

    if group_details:
        if 'image' in data:
            image_data = data['image']
            media_data = {}
            media_data['type'] = image_data['type']
            media_data['path'] = image_data['path']
            media_data['media_id'] = image_data['media_id']
            group_details.image = media_data
            update_item(group_details)
            return success('SUCCESS', meta={"message": "Group Created Successfully"})
        else:
            return success('SUCCESS', meta={"message": "Group Created Successfully"})
    else:
        return failure("Group Created Successfully")


def join_group(current_user, group_id):
    existing_group = Group.query.filter_by(id=group_id, deleted_at=None).first()
    if existing_group:
        if existing_group.visibility == 'all':
            if existing_group.user_id == current_user.id:
                return success('SUCCESS', meta={'message': 'Cannot send request,You are the admin of this group'})
            user = GroupMembers.query.filter_by(user_id=current_user.id, group_id=group_id, deleted_at=None).first()
            if not user:
                group_member = GroupMembers(user_id=current_user.id, group_id=group_id, type='user', status='active')
                add_item(group_member)

                def send_notification():
                    group_admins = GroupMembers.query.filter_by(group_id=existing_group.id,type='admin',status='active').all()
                    fcm_token = []
                    if group_admins:
                        for admin in group_admins:
                            user_membership = Membership.query.filter_by(user_id=admin.user_id,
                                                                     membership_status='active',
                                                                     deleted_at=None).first()
                            if user_membership:
                                if user_membership.fcm_token != None:
                                    fcm_token.append(user_membership.fcm_token)

                    if fcm_token != None:
                        message = current_user.first_name + " has joined " + existing_group.group_name
                        queue_url = PUSH_NOTIFICATION_URL
                        payload = {}
                        payload['id'] = str(group_id)
                        payload['current_user'] = str(current_user.id)
                        payload['message'] = message
                        payload['title'] = "Group Join "
                        payload['fcm_token'] = fcm_token
                        payload['screen_type'] = 'GROUP_DETAIL'
                        payload['responder_id'] = None
                        send_queue_message(queue_url, payload)
                        # post in-app notification
                        screen_info = {}
                        data = {}
                        screen_info['screen_type'] = 'GROUP_DETAIL'
                        screen_info['id'] = str(group_id)
                        data['meta_data'] = screen_info
                        if group_admins:
                            for item in group_admins:
                                add_notification = Notification(user_id=item.user_id, type='group',
                                                                title=payload['title'],
                                                                description=message, read_status=False,
                                                                meta_data=data['meta_data'], c_user=current_user.id)
                                add_item(add_notification)

                send_notification()

                return success('SUCCESS', meta={'message': 'Group Member Added'})
            else:
                return success('SUCCESS', meta={'message': 'Already a Group Member'})
        else:
            if existing_group.user_id == current_user.id:
                return success('SUCCESS', meta={'message': 'Cannot send request,You are the admin of this group'})
            user = GroupMembers.query.filter_by(user_id=current_user.id, group_id=group_id, deleted_at=None).first()
            if not user:
                group_member = GroupMembers(user_id=current_user.id, group_id=group_id, type='user', status='inactive')
                add_item(group_member)

                def send_notification():
                    user_membership = Membership.query.filter_by(user_id=existing_group.user_id,
                                                                 membership_status='active',
                                                                 deleted_at=None).first()
                    if user_membership.fcm_token != None:
                        message = current_user.first_name + " sent request to join group " + existing_group.group_name
                        queue_url = PUSH_NOTIFICATION_URL
                        fcm_token = []
                        fcm_token.append(user_membership.fcm_token)
                        payload = {}
                        payload['id'] = str(group_id)
                        payload['current_user'] = str(current_user.id)
                        payload['message'] = message
                        payload['title'] = "Group Join Request"
                        payload['fcm_token'] = fcm_token
                        payload['screen_type'] = 'RAISED_REQUEST'
                        payload['responder_id'] = None
                        send_queue_message(queue_url, payload)
                        # post in-app notification
                        screen_info = {}
                        data = {}
                        screen_info['screen_type'] = 'RAISED_REQUEST'
                        screen_info['id'] = str(group_id)
                        data['meta_data'] = screen_info
                        add_notification = Notification(user_id=existing_group.user_id, type='group',
                                                        title=payload['title'],
                                                        description=message, read_status=False,
                                                        meta_data=data['meta_data'], c_user=current_user.id)
                        add_item(add_notification)

                send_notification()

                return success('SUCCESS', meta={'message': 'Request sent'})
            else:
                return success('SUCCESS', meta={'message': 'Already a Group Member'})
    else:
        return success('SUCCESS', meta={'message': 'Group does not exists'})


def update_group_details(current_user,data, group_id):
    city=data.get('city')
    existing_group_admin = GroupMembers.query.filter_by(group_id=group_id, type='admin',
                                                        user_id=current_user.id,deleted_at=None).first()
    if existing_group_admin is not None:
        existing_group = Group.query.filter_by(id=group_id,deleted_at=None).first()
        if existing_group:
            if data.get('group_name', None):
                existing_group.group_name = data.get('group_name', None)
            if data.get('description', None):
                existing_group.description = data.get('description', None)
            if data.get('sport', None):
                existing_group.sport_type = data.get('sport', None)
            if data.get('city', None):
                existing_group.city = city
            if data.get('image', None):
                existing_group.image = data.get('image', None)
            if data.get('visibility', None):
                existing_group.visibility = data.get('visibility', None)
            update_item(existing_group)
            return success('SUCCESS',meta={'message':'Group Details Updated SUccessfully'})
        else:
            return success('SUCCESS',meta={'message':'Group doesnot exists'})
    else:
        return success('SUCCESS',meta={'message':'Only Admin can update group details'})


def pending_requests(current_user,group_id):
    is_admin = GroupMembers.query.filter_by(user_id=current_user.id, type='admin', group_id=group_id,status='active',deleted_at=None).first()
    if is_admin:
        join_request = GroupMembers.query.filter_by(group_id=group_id, status='inactive', type='user',deleted_at=None).all()
        result = []
        if join_request:
            for request in join_request:
                group_join_request = {}
                existing_user = Users.query.filter_by(id=request.user_id,deleted_at=None,user_deleted_at=None).first()
                group_join_request['id'] = request.user_id
                group_join_request['name'] = existing_user.first_name
                group_join_request['created_at'] = request.created_at
                group_join_request['profile_image'] = existing_user.profile_image
                result.append(group_join_request)
            return success('SUCCESS', result, meta={'message': 'Pending Requests'})
        else:
            return success('SUCCESS', result, meta={'message': 'No Requests'})
    else:
        return success('SUCCESS',meta={'message': "not an admin"})


def accept_join_request(current_user,group_id,data):
    is_admin = GroupMembers.query.filter_by(user_id=current_user.id, type='admin', group_id=group_id,deleted_at=None).first()
    if is_admin:
        user_id = data['user_id']
        group_member = GroupMembers.query.filter_by(user_id=user_id, group_id=group_id, status='inactive',deleted_at=None).first()
        if group_member:
            group_member.status = 'active'
            update_item(group_member)

            def send_notification():
                user_membership = Membership.query.filter_by(user_id=user_id,
                                                             membership_status='active',
                                                             deleted_at=None).first()
                group_data = Group.query.filter_by(id=group_id, deleted_at=None).first()
                if user_membership.fcm_token != None and group_data:
                    message = current_user.first_name + " accepted your join request for group " + group_data.group_name
                    queue_url = PUSH_NOTIFICATION_URL
                    fcm_token = []
                    fcm_token.append(user_membership.fcm_token)
                    payload = {}
                    payload['id'] = str(group_id)
                    payload['current_user'] = str(current_user.id)
                    payload['message'] = message
                    payload['title'] = "Group Join Request Accepted"
                    payload['fcm_token'] = fcm_token
                    payload['screen_type'] = 'RAISED_REQUEST'
                    payload['responder_id'] = None
                    send_queue_message(queue_url, payload)
                    # post in-app notification
                    screen_info = {}
                    data = {}
                    screen_info['screen_type'] = 'RAISED_REQUEST'
                    screen_info['id'] = str(group_id)
                    data['meta_data'] = screen_info
                    add_notification = Notification(user_id=user_id, type='group',
                                                    title=payload['title'],
                                                    description=message, read_status=False,
                                                    meta_data=data['meta_data'], c_user=current_user.id)
                    add_item(add_notification)

            send_notification()
            return success('join request accepted')
        else:
            return failure("Invalid request")
    else:
        return failure("check group user id")


def make_new_admin(current_user,data,group_id):
    is_admin = GroupMembers.query.filter_by(user_id=current_user.id, type='admin', group_id=group_id,deleted_at=None).first()
    if is_admin:
        user_id = data['user_id']
        group_member = GroupMembers.query.filter_by(user_id=user_id, group_id=group_id,type='user',status='active',deleted_at=None).first()
        if group_member:
            group_member.type = 'admin'
            update_item(group_member)
            # send notification
            user_membership = Membership.query.filter_by(user_id=user_id,membership_status='active', deleted_at=None).first()
            message = current_user.first_name + " made you an admin"
            queue_url = PUSH_NOTIFICATION_URL
            fcm_token = []
            fcm_token.append(user_membership.fcm_token)
            payload = {}
            payload['id'] = str(group_id)
            payload['current_user'] = str(current_user.id)
            payload['message'] = message
            payload['title'] = "Group Admin"
            payload['fcm_token'] = fcm_token
            payload['screen_type'] = 'GROUP_DETAIL'
            payload['responder_id'] = None
            send_queue_message(queue_url, payload)

            # post in-app notification
            screen_info = {}
            data = {}
            screen_info['screen_type'] = 'GROUP_DETAIL'
            screen_info['id'] = None
            data['meta_data'] = screen_info
            add_notification = Notification(user_id=user_id, type='group', title=payload['title'],
                                            description=message, read_status=False, meta_data=data['meta_data'],c_user=current_user.id)
            add_item(add_notification)

            return success('Added this member as an admin')
        else:
            return failure("Member doesnot exist")
    else:
        return failure("You are not an Admin")


def remove_group_member(current_user, data, group_id):
    is_admin = GroupMembers.query.filter_by(user_id=current_user.id, type='admin', group_id=group_id,
                                            status='active', deleted_at=None).first()
    if is_admin:
        members = data.get('members', None)
        if members:
            for member in members:
                group_member = GroupMembers.query.filter_by(user_id=member, group_id=group_id, status='active',
                                                            deleted_at=None, type='user').first()
                if group_member:
                    group_member.deleted_at = datetime.datetime.now()
                    db.session.commit()
                else:

                    is_group_admin = GroupMembers.query.filter_by(user_id=member, group_id=group_id, status='active',
                                                                  deleted_at=None, type='admin').first()
                    if is_group_admin:
                        check_admin_id = Group.query.filter_by(id=group_id, user_id=member, deleted_at=None).first()
                        if check_admin_id:
                            check_existing_admin = GroupMembers.query.filter(GroupMembers.group_id == group_id,
                                                                             GroupMembers.type == 'admin',
                                                                             GroupMembers.user_id != current_user.id,
                                                                             GroupMembers.user_id != member,
                                                                             GroupMembers.deleted_at == None).first()
                            # if no other admin exist
                            if check_existing_admin is None:
                                make_admin = Group.query.filter_by(id=group_id, user_id=member,
                                                                   deleted_at=None).first()
                                if make_admin:
                                    make_admin.user_id = current_user.id
                                    db.session.commit()
                            else:
                                # if there is another admin
                                sorted_list = GroupMembers.query.filter(GroupMembers.group_id == group_id,
                                                                        GroupMembers.type == 'admin',
                                                                        GroupMembers.user_id != member,
                                                                        GroupMembers.deleted_at == None) \
                                    .order_by(GroupMembers.created_at)
                                if list(sorted_list):
                                    member_data = list(sorted_list)[0]
                                    check_admin_id.user_id = member_data.user_id
                                    db.session.commit()
                        delete_group_member = GroupMembers.query.filter(GroupMembers.group_id == group_id,
                                                                        GroupMembers.user_id == member,
                                                                        GroupMembers.deleted_at == None).first()
                        delete_group_member.deleted_at = datetime.datetime.now()
                        db.session.commit()
            return success('SUCCESS', meta={'message': 'removed successfully'})
        else:
            return success('SUCCESS', meta={'message': 'invalid input'})
    else:
        return success('SUCCESS', meta={'message': 'not an admin'})


def group_detail(current_user,group_id):
    group_detail = Group.query.filter_by(id=group_id,deleted_at=None).first()
    result = []
    if group_detail:
        members_count = GroupMembers.query.filter(GroupMembers.group_id == group_id,
                                                  GroupMembers.status == 'active',GroupMembers.deleted_at==None).count()
        member = GroupMembers.query.filter(GroupMembers.group_id == group_id,
                                           GroupMembers.user_id == current_user.id,GroupMembers.deleted_at==None).first()
        status = ''
        is_admin = False
        if member:
            if member.status == 'active':
                status = 'active'
            elif member.status == 'inactive':
                status = 'pending'
            elif member.status == 'invited':
                status = 'invited'
            else:
                status ='inactive'
            if member.type == 'admin':
                is_admin = True
        owner = ""
        visibility = ""
        owner_detail = Users.query.filter_by(id=group_detail.user_id,deleted_at=None,user_deleted_at=None).first()
        if owner_detail:
            owner = owner_detail.first_name
        if group_detail.visibility == 'group_members':
            visibility = 'closed'
        if group_detail.visibility == 'all':
            visibility = 'open'
        result = {}
        result['group_id'] = group_detail.id
        result['group_name'] = group_detail.group_name
        result['city'] = group_detail.city
        result['description'] = group_detail.description
        result['owner_name'] = owner
        result['owner_id'] = owner_detail.id
        result['sport'] = group_detail.sport_type
        result['image'] = group_detail.image
        result['visibility'] = visibility
        result['created_on'] = group_detail.created_at
        result['status'] = status
        result['is_owner'] = is_admin
        result['members_count'] = members_count
        return success('SUCCESS', result)
    return failure('Group Doesnot exists')


def group_exit(current_user, group_id):
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None)
    if existing_user:
        group_exist = Group.query.filter_by(id=group_id, deleted_at=None).first()
        if group_exist:
            existing_admin = GroupMembers.query.filter(GroupMembers.group_id == group_id,
                                                       GroupMembers.type == 'admin',
                                                       GroupMembers.user_id != current_user.id,
                                                       GroupMembers.deleted_at == None,
                                                       GroupMembers.status == 'active').first()
            # if no other admin exist
            if existing_admin is None:
                sorted_list = GroupMembers.query.filter(GroupMembers.group_id == group_id,
                                                        GroupMembers.user_id != current_user.id,
                                                        GroupMembers.deleted_at == None,
                                                        GroupMembers.status=='active') \
                    .order_by(GroupMembers.created_at)

                if list(sorted_list):
                    member = list(sorted_list)[0]
                    second_member = GroupMembers.query.filter_by(id=member.id, deleted_at=None).first()
                    if second_member:
                        if second_member.status == 'active':
                            second_member.type = 'admin'
                            update_item(second_member)
                            group_exist.user_id = member.user_id
                            update_item(group_exist)
                else:
                    # No member exist
                    delete_invitation = GroupMembers.query.filter(GroupMembers.group_id == group_id,
                                                       GroupMembers.deleted_at == None,
                                                       GroupMembers.status != 'active').all()
                    for item in delete_invitation:
                        invitation = GroupMembers.query.filter_by(id=item.id,deleted_at=None).first()
                        invitation.deleted_at = datetime.datetime.now()
                        update_item(invitation)
                    delete_group_also = Group.query.filter_by(id=group_id, deleted_at=None).first()
                    delete_group_also.deleted_at = datetime.datetime.now()
                    update_item(delete_group_also)
            else:
                # if there is another admin
                sorted_list = GroupMembers.query.filter(GroupMembers.group_id == group_id,
                                                        GroupMembers.type == 'admin',
                                                        GroupMembers.user_id != current_user.id,
                                                        GroupMembers.deleted_at == None,
                                                        GroupMembers.status == 'active') \
                    .order_by(GroupMembers.created_at)
                if list(sorted_list):
                    member = list(sorted_list)[0]
                    group_exist.user_id = member.user_id
                    update_item(group_exist)

            delete_group_member = GroupMembers.query.filter(GroupMembers.group_id == group_id,
                                                            GroupMembers.user_id == current_user.id,
                                                            GroupMembers.deleted_at == None,
                                                            GroupMembers.status == 'active').first()
            delete_group_member.deleted_at = datetime.datetime.now()
            update_item(delete_group_member)
            return success('SUCCESS', meta={'message': 'exit successfully!'})
        else:
            return success('SUCCESS', meta={'message': 'group does not exist'})
    else:
        return success('SUCCESS', meta={'message': 'user is not exist'})


def my_group_list(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    all_groups = GroupMembers.query.filter_by(user_id=current_user.id, status='active', deleted_at=None).all()
    my_groups = GroupMembers.query.filter_by(user_id=current_user.id, status='active', deleted_at=None).order_by(GroupMembers.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    my_groups=my_groups.items
    total_record = len(all_groups)
    total_pages = total_record // per_page + 1
    result = []
    if my_groups:
        for group in my_groups:
            member_count = GroupMembers.query.filter_by(group_id=group.group_id, deleted_at=None,status='active').count()
            status = ''
            is_admin = False
            if group.status == 'active':
                status = 'active'
            elif group.status == 'inactive':
                status = 'pending'
            else:
                status = 'inactive'
            if group.type == 'admin':
                is_admin = True
            owner = ""
            visibility = ''
            admin = Group.query.filter_by(id=group.group_id, deleted_at=None).first()
            owner_detail = Users.query.filter_by(id=admin.user_id,user_deleted_at=None,deleted_at=None).first()
            if owner_detail:
                owner = owner_detail.first_name
                group_data = {}
                if admin.visibility == 'group_members':
                    visibility = 'closed'
                if admin.visibility == 'all':
                    visibility = 'open'
                group_data['group_id'] = admin.id
                group_data['group_name'] = admin.group_name
                group_data['city'] = admin.city
                group_data['description'] = admin.description
                group_data['owner_name'] = owner
                group_data['sport'] = admin.sport_type
                group_data['visibility'] = visibility
                group_data['created_on'] = admin.created_at
                group_data['image'] = admin.image
                group_data['status'] = status
                group_data['is_owner'] = is_admin
                group_data['owner_id'] = owner_detail.id
                group_data['members_count'] = member_count
                result.append(group_data)
        return success("SUCCESS", result, meta={"message": "My Group List",
                                                'page_info': {'current_page': page, 'total_record': total_record,
                                       'total_pages': total_pages,
                                       'limit': per_page}})

    else:
        return success("SUCCESS", result, meta={"message": "No Groups Found"})


def search_group_members(current_user,group_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    keyword = request.args.get('keyword')
    if keyword:
        search_string = '%{}%'.format(keyword)
        existing_group = Group.query.filter_by(id=group_id,deleted_at=None,user_id=current_user.id).first()
        if existing_group:
            group_members = GroupMembers.query.join(Users, GroupMembers.user_id == Users.id, isouter=True).filter(GroupMembers.group_id == group_id,Users.first_name.ilike(search_string),GroupMembers.deleted_at==None).paginate(
                page=page,
                per_page=per_page,
                error_out=False)
            group_members = group_members.items
            if group_members:
                result = []
                for member in group_members:
                    existing_user = Users.query.filter_by(id=member.user_id,user_deleted_at=None,deleted_at=None).first()
                    if existing_user:
                        user_data = {}
                        user_data['user_id'] = member.user_id
                        user_data['name'] = existing_user.first_name
                        user_data['profile_image'] = existing_user.profile_image
                        result.append(user_data)
                    else:
                        return success('SUCCESS',meta={'message':'User not Found'})
                return success("SUCCESS", result, meta={"message": "Group Member Search",
                                                        'page_info': {'current_page': page, 'limit': per_page}})
            else:
                return success('SUCCESS',meta={'message':'No Members Found'})
        else:
            return success('SUCCESS', meta={'message': 'Group Not Found'})

    else:
        return success('SUCCESS', meta={'message': 'No Members Found'})


def group_member_list(current_user,group_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    existing_group = Group.query.filter_by(id=group_id, deleted_at=None).first()
    if existing_group:
        group_members = GroupMembers.query.filter_by(group_id=group_id,status='active',deleted_at=None).paginate(
                page=page,
                per_page=per_page,
                error_out=False)
        all_group_members = GroupMembers.query.filter_by(group_id=group_id, status='active', deleted_at=None).all()
        group_members = group_members.items
        total_record = len(all_group_members)
        total_pages = total_record // per_page + 1
        if group_members:
            result = []
            for member in group_members:
                existing_user = Users.query.filter_by(id=member.user_id,user_deleted_at=None,deleted_at=None).first()
                if existing_user:
                    user_data = {}
                    user_data['user_id'] = member.user_id
                    user_data['name'] = existing_user.first_name
                    user_data['profile_image'] = existing_user.profile_image
                    user_data['type'] = member.type
                    result.append(user_data)
                else:
                    return success('SUCCESS', meta={'message': 'User not Found'})
            return success("SUCCESS", result, meta={"message": "Group Member List",
                                                    'page_info': {'current_page': page, 'total_record': total_record,
                                       'total_pages': total_pages,
                                       'limit': per_page}})
        else:
            return success('SUCCESS', meta={'message': 'No Members Found'})
    else:
        return success('SUCCESS', meta={'message': 'Group Not Found'})


def search_friend_list(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    keyword = request.args.get('keyword')
    if keyword:
        search_string = '%{}%'.format(keyword)
        blocklist = []
        contactlist = []
        my_blocklist = Contact.query.filter_by(user_id=current_user.id, friend_status='blocked',
                                               deleted_at=None).all()
        for blocked_user in my_blocklist:
            blocklist.append(blocked_user.contact_id)
        my_contact = Contact.query.filter_by(user_id=current_user.id, friend_status='friends',
                                             deleted_at=None).all()
        for contact in my_contact:
            contactlist.append(contact.contact_id)
        search_friends_list = Users.query.join(Contact, Users.id == Contact.user_id, isouter=True).filter(
            or_((Users.first_name.ilike(search_string)), (Users.nickname.ilike(search_string))),
            Users.id.notin_(blocklist),Users.id.in_(contactlist),Users.user_deleted_at==None,Users.deleted_at==None).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        friend_list = search_friends_list.items
        total_record = len(friend_list)
        if friend_list:
            result = []
            for friend in friend_list:
                existing_user = Users.query.filter_by(id=friend.id,user_deleted_at=None,deleted_at=None).first()
                if existing_user:
                    user_data = {}
                    user_data['user_id'] = friend.id
                    user_data['name'] = existing_user.first_name
                    user_data['profile_image'] = existing_user.profile_image
                    result.append(user_data)
                else:
                    return success('SUCCESS', meta={'message': 'User not Found'})
            return success("SUCCESS", result, meta={"message": "Friend Search",
                                                    'page_info': {'current_page': page, 'limit': per_page}})
        else:
            return success('SUCCESS', meta={'message': 'No Members Found'})
    else:
        is_contact = Contact.query.filter_by(user_id=current_user.id, friend_status='friends',
                                             deleted_at=None).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        friend_list = is_contact.items
        if friend_list:
            result = []
            for friend in friend_list:
                existing_user = Users.query.filter_by(id=friend.contact_id,user_deleted_at=None,deleted_at=None).first()
                if existing_user:
                    user_data = {}
                    user_data['user_id'] = friend.contact_id
                    user_data['name'] = existing_user.first_name
                    user_data['profile_image'] = existing_user.profile_image
                    result.append(user_data)
                else:
                    return success('SUCCESS', meta={'message': 'User not Found'})
            return success("SUCCESS", result, meta={"message": "Friend Search"})
        else:
            return success('SUCCESS', meta={'message': 'No Friends'})


def get_group_content(current_user,group_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    offset = per_page * (page - 1)
    is_group = Group.query.filter_by(id=group_id,deleted_at=None).first()
    is_member = GroupMembers.query.filter_by(group_id=group_id,user_id=current_user.id,status='active',deleted_at=None).first()
    if is_group and is_member:
        query = """SELECT p.* FROM post p WHERE (p.deleted_at IS  NULL AND p.group_id='{group_id}' AND (
                       p.expire_on is null or p.expire_on > NOW()))
                       ORDER BY p.created_at DESC LIMIT {per_page} OFFSET {offset}
                       """.format(group_id=group_id, per_page=per_page, offset=offset)

        group_feed = _query_execution(query)
        result = []
        for post in group_feed:
            like_count = PostReact.query.filter(PostReact.post_id == post['id'], PostReact.type == 'like',
                                                PostReact.is_liked == True, PostReact.deleted_at == None).count()
            comment_count = Comment.query.filter(Comment.post_id == post['id'], Comment.deleted_at == None).count()
            is_reacted = PostReact.query.filter(PostReact.user_id == current_user.id, PostReact.post_id == post['id'],
                                                PostReact.deleted_at == None).first()

            if like_count >= 0:
                post['like'] = like_count
            if comment_count >= 0:
                post['comment'] = comment_count
            if is_reacted is not None:
                post['is_like'] = is_reacted.is_liked
            else:
                post['is_like'] = False
            post['group'] = post['group_id']
            result.append(prepare_post_display_fileds(post))

        return success('SUCCESS', result,
                       meta={'message': 'Group Feed', 'page_info': {'current_page': page, 'limit': per_page}})

    else:
        return failure(meta={'message':'User/Group Not Found'})


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
    post_data['meta_data'] = post['meta_data']
    post_data['type'] = post['type']
    post_data['group_id'] = post['group']

    return post_data


def add_member(current_user,data,group_id):
    members = data.get('members', None)
    is_admin = GroupMembers.query.filter_by(user_id=current_user.id, group_id=group_id, status='active',type='admin',
                                             deleted_at=None).first()
    if is_admin:
        if members:
            for member in members:
                is_member = GroupMembers.query.filter_by(user_id=member, group_id=group_id,deleted_at=None).first()
                if not is_member:
                    add_members = GroupMembers(user_id=member, group_id=group_id, type='user', status='invited')
                    add_item(add_members)

                    # send notification
                    def send_notification():
                        # send notification
                        user_membership = Membership.query.filter_by(user_id=member, deleted_at=None).first()
                        message = current_user.first_name + " has sent you a group invite"
                        queue_url = PUSH_NOTIFICATION_URL
                        fcm_token = []
                        fcm_token.append(user_membership.fcm_token)
                        payload = {}
                        payload['id'] = str(group_id)
                        payload['current_user'] = str(current_user.id)
                        payload['message'] = message
                        payload['title'] = "Group Invite"
                        payload['fcm_token'] = fcm_token
                        payload['screen_type'] = 'GROUP_DETAIL'
                        payload['responder_id'] = None
                        send_queue_message(queue_url, payload)
                        # post in-app notification
                        screen_info = {}
                        data = {}
                        screen_info['screen_type'] = 'GROUP_DETAIL'
                        screen_info['id'] = str(group_id)
                        data['meta_data'] = screen_info
                        add_notification = Notification(user_id=member, type='group', title=payload['title'],
                                                        description=message, read_status=False,
                                                        meta_data=data['meta_data'],c_user=current_user.id)
                        add_item(add_notification)

                    send_notification()
                else:
                    pass
            return success('SUCCESS',meta={'message':'Member added successfully'})
        else:
            return success('SUCCESS', meta={'message': 'Invalid Data'})
    else:
        return success('SUCCESS', meta={'message': 'You are not an admin'})


def make_admin_to_user(current_user,data,group_id):
    is_admin = GroupMembers.query.filter_by(user_id=current_user.id, type='admin', group_id=group_id,
                                            deleted_at=None,status='active').first()
    if is_admin:
        user_id = data['user_id']
        group_member = GroupMembers.query.filter_by(user_id=user_id, group_id=group_id, type='admin', status='active',
                                                    deleted_at=None).first()
        if group_member:
            group_member.type = 'user'
            update_item(group_member)
            return success('SUCCESS', meta={'message':'removed admin'})
        else:
            return success('SUCCESS', meta={'message':"this member is not an admin"})
    else:
        return success('SUCCESS', meta={'message':"You are not an Admin"})


def reject_join_request(current_user, group_id, data):
    is_admin = GroupMembers.query.filter_by(user_id=current_user.id, type='admin', group_id=group_id, deleted_at=None,
                                            status='active').first()
    if is_admin:
        user_id = data['user_id']
        group_member = GroupMembers.query.filter_by(user_id=user_id, group_id=group_id, status='inactive',
                                                    deleted_at=None).first()
        if group_member:
            is_raised_request = GroupMembers.query.filter_by(user_id=user_id, group_id=group_id, status='inactive',
                                         deleted_at=None).first()
            delete_item(is_raised_request)
            return success('join request rejected')
        else:
            return success('SUCCESS', meta={'message': 'Invalid request'})
    else:
        return success('SUCCESS', meta={'message': 'check group user id'})


def accept_group_invitation(current_user, data):
    group_id = data.get('group_id', None)
    status = data.get('status', None)
    if group_id is not None and status is not None:
        group_exist = Group.query.filter_by(id=group_id, deleted_at=None).first()
        if group_exist:
            group_member_exist = GroupMembers.query.filter_by(user_id=current_user.id, group_id=group_id,
                                                              status='invited', deleted_at=None).first()
            if group_member_exist:
                if status in ['accept', 'reject']:
                    if status == 'accept':
                        group_member_exist.status = 'active'
                        update_item(group_member_exist)

                        #send notification
                        def send_notification():
                            user_membership = Membership.query.filter_by(user_id=group_exist.user_id,
                                                                         membership_status='active',
                                                                         deleted_at=None).first()
                            message = current_user.first_name + " accepted your group invite"
                            queue_url = PUSH_NOTIFICATION_URL
                            fcm_token = []
                            fcm_token.append(user_membership.fcm_token)
                            payload = {}
                            payload['id'] = str(group_id)
                            payload['current_user'] = str(current_user.id)
                            payload['message'] = message
                            payload['title'] = "Group Invite Accepted"
                            payload['fcm_token'] = fcm_token
                            payload['screen_type'] = 'GROUP_DETAIL'
                            payload['responder_id'] = None
                            send_queue_message(queue_url, payload)
                            # post in-app notification
                            screen_info = {}
                            data = {}
                            screen_info['screen_type'] = 'GROUP_DETAIL'
                            screen_info['id'] = str(group_id)
                            data['meta_data'] = screen_info
                            add_notification = Notification(user_id=group_exist.user_id, type='group',
                                                            title=payload['title'],
                                                            description=message, read_status=False,
                                                            meta_data=data['meta_data'],c_user=current_user.id)
                            add_item(add_notification)

                        send_notification()

                        return success('SUCCESS', meta={"message": "group invitation accepted successfully"})
                    else:
                        GroupMembers.query.filter_by(user_id=current_user.id, group_id=group_id,
                                                     status='invited', deleted_at=None).delete()
                        db.session.commit()
                        return success('SUCCESS', meta={"message": "group invitation rejected successfully"})
                else:
                    return success('SUCCESS', meta={"message": "invalid status"})
            else:
                return success('SUCCESS', meta={"message": "invalid group member data"})
        else:
            return success('SUCCESS', meta={'message': 'invalid group'})
    else:
        return success('SUCCESS', meta={"message": "incomplete input"})


def get_group_list(current_user, user_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    group_list= GroupMembers.query.filter_by(user_id=user_id, status='active', deleted_at=None).all()
    my_groups_list = GroupMembers.query.filter_by(user_id=user_id, status='active', deleted_at=None).order_by(
        GroupMembers.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    my_groups_list = my_groups_list.items
    total_record = len(group_list)
    total_pages = total_record // per_page + 1
    result = []
    if my_groups_list:
        for group in my_groups_list:
            member_count = GroupMembers.query.filter_by(group_id=group.group_id, deleted_at=None,
                                                        status='active').count()

            is_admin = False
            if group.status == 'active':
                status = 'active'
            elif group.status == 'inactive':
                status = 'pending'
            else:
                status = 'inactive'
            if group.type == 'admin':
                is_admin = True
            owner = ""
            visibility = ''
            admin = Group.query.filter_by(id=group.group_id, deleted_at=None).first()
            owner_detail = Users.query.filter_by(id=admin.user_id,user_deleted_at=None,deleted_at=None).first()
            if owner_detail:
                owner = owner_detail.first_name
                group_data = {}
                if admin.visibility == 'group_members':
                    visibility = 'closed'
                if admin.visibility == 'all':
                    visibility = 'open'
                group_data['group_id'] = admin.id
                group_data['group_name'] = admin.group_name
                group_data['city'] = admin.city
                group_data['description'] = admin.description
                group_data['owner_name'] = owner
                group_data['sport'] = admin.sport_type
                group_data['visibility'] = visibility
                group_data['created_on'] = admin.created_at
                group_data['image'] = admin.image
                group_data['status'] = status
                group_data['is_owner'] = is_admin
                group_data['owner_id'] = owner_detail.id
                group_data['members_count'] = member_count
                result.append(group_data)
        return success("SUCCESS", result, meta={"message": "Group List",
                                                'page_info': {'current_page': page, 'total_record': total_record,
                                                              'total_pages': total_pages,
                                                              'limit': per_page}})

    else:
        return success("SUCCESS", result, meta={"message": "No Groups Found"})




