import os
from dotenv import load_dotenv
# print(os.environ)

load_dotenv()
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM')
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
JWT_TOKEN_TIME_OUT_IN_MINUTES = 600
ENABLE_AUTH = False


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
