import json

from flask import request

from api.Users.models import Users
from api.Users.services import get_user_profile_details
from api.notification.models import Notification
from common.connection import update_item
from common.response import success
from config import AWS_REGION_NAME, AWS_SQS_ACCESS_KEY_ID, AWS_SQS_SECRET_ACCESS_KEY
import boto3


def send_queue_message(queue_url, payload):
    try:
        sqs_client = boto3.client('sqs',
                                  region_name=AWS_REGION_NAME,
                                  aws_access_key_id=AWS_SQS_ACCESS_KEY_ID,
                                  aws_secret_access_key=AWS_SQS_SECRET_ACCESS_KEY
                                  )
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=str(json.dumps(payload))
        )
    except Exception as e:
        print("sqs failed", e)


def get_notification(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    notification= Notification.query.filter_by(user_id=current_user.id, deleted_at=None).order_by(Notification.created_at.desc()).all()
    notification_list = Notification.query.filter_by(user_id=current_user.id , deleted_at=None).order_by(Notification.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
    total_records = len(notification)
    notification_list = notification_list.items
    total_pages = total_records // per_page + 1
    result = []
    if notification_list:
        for data in notification_list:
            user_exist = Users.query.filter_by(id=data.user_id, deleted_at=None,user_deleted_at=None).first()
            if user_exist:
                list = {}
                list['id'] = data.id
                list['user_id'] = data.user_id
                list['user_info'] = get_user_profile_details(data.c_user)
                list['type'] = data.type
                list['title'] = data.title
                list['description'] = data.description
                list['read_status'] = data.read_status
                list['meta_data'] = data.meta_data
                list['created_at'] = data.created_at
                result.append(list)
        return success('SUCCESS', result, meta={'message': 'Get Notification',
                                                'page_info': {'current_page': page, 'limit': per_page,
                                                              'total_record': total_records,
                                                              'total_pages': total_pages}})
    else:
        return success('SUCCESS',meta={'message':'No Notifications'})


def update_notification(current_user,notification_id,data):
    read_status = data.get('read_status', None)
    notification=Notification.query.filter_by(user_id=current_user.id,id=notification_id).first()
    if notification:
        notification.read_status = read_status
        update_item(notification)
        return success('SUCCESS', meta={'message': 'notification status updated'})
    else:
        return success('SUCCESS', meta={'message': 'No Notification found'})


def unseen_notification_list(current_user):
    notification_count=Notification.query.filter_by(user_id=current_user.id,read_status=False,deleted_at=None).count()
    result = []
    if notification_count:
        list={}
        list['notification_count']=notification_count
        result.append(list)
        return success('SUCCESS' ,result,meta={'message':'Notification Count'})
    else:
        return success('SUCCESS',meta={'message':'Empty'})


def make_all_read(current_user):
    exist_user = Users.query.filter_by(id=current_user.id, user_deleted_at=None, deleted_at=None).first()
    if exist_user:
        exist_notify = Notification.query.filter_by(user_id=current_user.id,deleted_at=None).all()
        if exist_notify:
            for item in exist_notify:
                item.read_status = True
                update_item(exist_notify)
            return success('SUCCESS', meta={'message': 'Marked as all read'})
        else:
            return success('SUCCESS', meta={'message', 'No notification found'})
    else:
        return success('SUCCESS', meta={'message', 'Invalid  user account'})
