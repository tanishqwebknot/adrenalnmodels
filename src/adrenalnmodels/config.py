import os
from dotenv import load_dotenv
# print(os.environ)

load_dotenv()
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM')
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
JWT_TOKEN_TIME_OUT_IN_MINUTES = 600
ENABLE_AUTH = False
AWS_REGION_NAME= os.environ.get('AWS_REGION_NAME')
AWS_ACCESS_KEY_ID=os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY=os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_BUCKET_NAME=os.environ.get('AWS_BUCKET_NAME')
GOOGLE_CLIENT_ID=os.environ.get('GOOGLE_CLIENT_ID')
MOBILE_GOOGLE_CLIENT_ID= os.environ.get('MOBILE_GOOGLE_CLIENT_ID')
IOS_GOOGLE_CLIENT_ID = os.environ.get('IOS_GOOGLE_CLIENT_ID')
UPDATE_TIMELINE_URL=os.environ.get('UPDATE_TIMELINE_URL')
PUSH_NOTIFICATION_URL=os.environ.get('PUSH_NOTIFICATION_URL')   
FIREBASE_DYNAMIC_LINK_URL=os.environ.get('FIREBASE_DYNAMIC_LINK_URL')
DEEP_LINK_PREFIX=os.environ.get('DEEP_LINK_PREFIX')
DEEP_LINK_URL=os.environ.get('DEEP_LINK_URL')   
ANDROID_PACKAGE_NAME= os.environ.get('ANDROID_PACKAGE_NAME')    
IOS_BUNDLE_ID= os.environ.get('IOS_BUNDLE_ID')
AWS_SQS_ACCESS_KEY_ID=os.environ.get('AWS_SQS_ACCESS_KEY_ID')
AWS_SQS_SECRET_ACCESS_KEY=os.environ.get('AWS_SQS_SECRET_ACCESS_KEY')
CSV_BASE_AWS_URL = os.environ.get('CSV_BASE_AWS_URL')
class Config(object):
    CSRF_ENABLED = True
    """
    Common configurations
    """
    FIXED_RATE = 000
    URL_PREFIX = 'api'
    SECRET_KEY = 'your_secret_key'

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'postgresql://' + os.environ.get('POSTGRES_USER') + ':' + os.environ.get('POSTGRES_PASS') + '@' + os.environ.get('POSTGRES_HOST') + ':' + os.environ.get('POSTGRES_PORT') + '/' + os.environ.get('POSTGRES_DB')
    # SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI']
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_ECHO = True
    DEVELOPMENT = True
    DEBUG = True
    FIXED_RATE = 200


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'postgresql://' + os.environ.get('POSTGRES_USER') + ':' + os.environ.get('POSTGRES_PASS') + '@' + os.environ.get('POSTGRES_HOST') + ':' + os.environ.get('POSTGRES_PORT') + '/' + os.environ.get('POSTGRES_DB')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG = True
    FIXED_RATE = 300


app_config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}
