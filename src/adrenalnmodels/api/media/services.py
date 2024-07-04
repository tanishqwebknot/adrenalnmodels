from api.media.models import Media
from config import AWS_REGION_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME
import boto3


def add_media_detail(current_user, file_type, file_path, file_size, source_type):
    media_data = Media(user_id=current_user.id, type=file_type, path=file_path, file_size=file_size,
                       source_type='gallery')
    return media_data


def get_media_access(data, is_object=False):
    try:
        expiry = 3600
        response = []
        client = boto3.client(service_name='s3',
                              region_name=AWS_REGION_NAME,
                              aws_access_key_id=AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                              )
        if is_object:
            data = [data]
        for imedia in data:
            path = imedia['path']
            actual_path = client.generate_presigned_url('get_object',
                                                        Params={'Bucket': AWS_BUCKET_NAME, 'Key': path},
                                                        ExpiresIn=expiry)


            imedia['path'] = actual_path
            response.append(imedia)
        if is_object:
            return True, response[0]
        else:
            return True, response
    except Exception as e:
        return False, None
