import datetime
import os
import uuid

import boto3
from flask import request, jsonify, Blueprint
from werkzeug.utils import secure_filename

from api.media.models import Media
from api.media.services import add_media_detail, get_media_access
from common.connection import add_item, update_item, delete_item
from common.response import success, failure
from config import AWS_REGION_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME
from middleware.auth import token_required,validate_token
# from flasgger import swag_from

media_api = Blueprint('media_api', __name__, url_prefix='/media')


def create_temp_file(size, file_name, file_content):
    random_file_name = ''.join([str(uuid.uuid4().hex[:6]), file_name])
    with open(random_file_name, 'w') as f:
        f.write(str(file_content) * size)
    return random_file_name


@media_api.route('/media', methods=['POST'])
@validate_token(action='upload_media')
def s3_media(current_user, bucket_name=AWS_BUCKET_NAME):
    # try:
    s3_resource = boto3.resource(service_name='s3',
                                 region_name=AWS_REGION_NAME,
                                 aws_access_key_id=AWS_ACCESS_KEY_ID,
                                 aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                                 )

    first_file_name = request.files['file']
    local_file_path = 'uploads/' + secure_filename(first_file_name.filename)
    first_file_name.save(local_file_path)
    ext = local_file_path.split('.')[-1]
    file_type = ext
    file_size = os.path.getsize(local_file_path)
    s3_path = 'media/' + str(current_user.id) + '/' + str(uuid.uuid4()) + '.' + ext
    first_bucket = s3_resource.Bucket(name=bucket_name)
    first_object = s3_resource.Object(bucket_name=first_bucket, key=s3_path)
    s3_resource.Object(bucket_name, s3_path).upload_file(Filename=local_file_path)
    file_path = s3_path
    add_media = add_media_detail(current_user, file_type, file_path, file_size, source_type='gallery')
    media = add_item(add_media)
    media_id = media.id
    path = media.path

    media_type = media.type
    result = {"media_id": media_id, "media_type": media_type, "path": path}

    return success("image is upload succussfully", result)
    #
    # except Exception as e:
    #     return failure("Something went wrong.")


@media_api.route('/gallery', methods=['GET'])
@validate_token(action="get_media_file")
def get_media(current_user):
    media_data = Media.query.filter_by(user_id=current_user.id, source_type='gallery').order_by(
Media.created_at.desc()).all()
    if media_data is not None:
        result = []
        for media in media_data:
            media_value = {}
            media_value['type'] = media.type
            media_value['path'] = media.path
            media_value['media_id'] = media.id
            result.append(media_value)
        return jsonify(result)


@media_api.route('/access', methods=['POST'])
def media_access():
    data = request.json
    status, media = get_media_access(data)
    if status:
        return success("SUCCESS", media)
    else:
        return failure("unauthorized user")


@media_api.route('/delete/<media_id>', methods=['DELETE'])
@validate_token(action="delete_media_file")
@token_required
def delete_media(current_user, media_id):
    delete_my_media = Media.query.filter_by(id=media_id, user_id=current_user.id).first()
    delete_item(delete_my_media)
    client = boto3.client(service_name='s3',
                          region_name=AWS_REGION_NAME,
                          aws_access_key_id=AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                          )
    client.delete_object(Bucket=AWS_BUCKET_NAME, Key=delete_my_media.path)
    return success("media file is deleted successfully")


@media_api.route('/', methods=['POST'])
@token_required
def se_bucket(bucket_name, path, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY):
    try:
        s3 = boto3.client(
            service_name='s3',
            region_name=AWS_REGION_NAME,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        s3.delete_object(Bucket=bucket_name, Key=path)
        return True
    except Exception as ex:
        print(str(ex))
        return False


@media_api.route('/limit/<user_id>', methods=['GET'])
@token_required
def limit_s3_bucket(current_user):
    try:
        s3_resource = boto3.resource(service_name='s3',
                                     region_name=AWS_REGION_NAME,
                                     aws_access_key_id=AWS_ACCESS_KEY_ID,
                                     aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                                     )
        total_size = 0
        for object in s3_resource.objects.all():
            total_size += object.size

    except Exception as ex:
        print(str(ex))
        return False

@media_api.route('/upload_media', methods=['POST'])
@validate_token(action='upload_media')
def upload_media(current_user, bucket_name=AWS_BUCKET_NAME):
    # try:

    responce=[]
    first_file_name = request.files.get('file1')
    first_file_name1 = request.files.get('file2')
    first_file_name2 = request.files.get('file3')
    first_file_name3 = request.files.get('file4')
    first_file_name4 = request.files.get('file5')
    if first_file_name:
        result = {}
        s3_path, file_type, file_size = upload_aws_bucket(first_file_name, bucket_name, current_user)
        file_path = s3_path
        add_media = add_media_detail(current_user, file_type, file_path, file_size, source_type='gallery')
        media = add_item(add_media)
        media_id = media.id
        path = media.path
        media_type = media.type
        result = {"media_id": media_id, "media_type": media_type, "path": path}
        responce.append(result)
    if first_file_name1:
        result = {}
        s3_path, file_type, file_size = upload_aws_bucket(first_file_name1, bucket_name, current_user)
        file_path = s3_path
        add_media = add_media_detail(current_user, file_type, file_path, file_size, source_type='gallery')
        media = add_item(add_media)
        media_id = media.id
        path = media.path
        media_type = media.type
        result = {"media_id": media_id, "media_type": media_type, "path": path}
        responce.append(result)
    if first_file_name2:
        s3_path, file_type, file_size = upload_aws_bucket(first_file_name2, bucket_name, current_user)
        file_path = s3_path
        add_media = add_media_detail(current_user, file_type, file_path, file_size, source_type='gallery')
        media = add_item(add_media)
        media_id = media.id
        path = media.path
        media_type = media.type
        result = {"media_id": media_id, "media_type": media_type, "path": path}
        responce.append(result)
    if first_file_name3:
        s3_path, file_type, file_size = upload_aws_bucket(first_file_name3, bucket_name, current_user)
        file_path = s3_path
        add_media = add_media_detail(current_user, file_type, file_path, file_size, source_type='gallery')
        media = add_item(add_media)
        media_id = media.id
        path = media.path
        media_type = media.type
        result = {"media_id": media_id, "media_type": media_type, "path": path}
        responce.append(result)
    if first_file_name4:
        s3_path, file_type, file_size = upload_aws_bucket(first_file_name4, bucket_name, current_user)
        file_path = s3_path
        add_media = add_media_detail(current_user, file_type, file_path, file_size, source_type='gallery')
        media = add_item(add_media)
        media_id = media.id
        path = media.path
        media_type = media.type
        result = {"media_id": media_id, "media_type": media_type, "path": path}
        responce.append(result)
    return success('SUCCESS',responce,meta={"message":"image is upload succussfully"})

    # except Exception as e:
    #     return failure("Something went wrong.")


def upload_aws_bucket(first_file_name, bucket_name, current_user):
    s3 = boto3.resource('s3', region_name=AWS_REGION_NAME,
                        aws_access_key_id=AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

    obj = s3.Object(bucket_name, first_file_name.filename)
    obj.put(Body=first_file_name, ACL='public-read', ContentType=first_file_name.content_type)

    s3_path = f"https://{bucket_name}.s3.amazonaws.com/{first_file_name.filename}"

    file_size=first_file_name.tell()
    attachment_type = first_file_name.content_type
    file_type = attachment_type.split('/')[0]
    return s3_path,file_type, file_size


def upload_aws(first_file_name, bucket_name, current_user):
    s3_resource = boto3.resource(service_name='s3',
                                 region_name=AWS_REGION_NAME,
                                 aws_access_key_id=AWS_ACCESS_KEY_ID,
                                 aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                                 )
    local_file_path = 'uploads/' + secure_filename(first_file_name.filename)
    first_file_name.save(local_file_path)
    ext = local_file_path.split('.')[-1]
    file_type = ext
    file_size = os.path.getsize(local_file_path)
    s3_path = 'media/' + str(current_user.id) + '/' + str(uuid.uuid4()) + '.' + ext
    first_bucket = s3_resource.Bucket(name=bucket_name)
    first_object = s3_resource.Object(bucket_name=first_bucket, key=s3_path)
    s3_resource.Object(bucket_name, s3_path).upload_file(Filename=local_file_path)
    return s3_path,file_type, file_size


@media_api.route('/delete', methods=['POST'])
@validate_token(action="delete_multiple_media_file")
def delete_multiple_files(current_user):
    data = request.get_json()
    media_id = data.get('media_id')
    if media_id:
        for id in media_id:
            my_media = Media.query.filter_by(id=id,user_id=current_user.id).first()
            delete_item(my_media)
            client = boto3.client(service_name='s3',
                                  region_name=AWS_REGION_NAME,
                                  aws_access_key_id=AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                                  )
            client.delete_object(Bucket=AWS_BUCKET_NAME, Key=my_media.path)
        return success("media file is deleted successfully")
    else:
        return failure("unauthorized user")
