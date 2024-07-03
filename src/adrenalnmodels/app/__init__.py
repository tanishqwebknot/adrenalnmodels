from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import app_config

db = SQLAlchemy()
BASE_URL_PREFIX = ''


def create_app(config_name):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(app_config[config_name])

    ''' App initialisation '''
    db.init_app(app)

    # Enabling Migration Setup
    migrate = Migrate(app, db)

    # Enabling CORS
    CORS(app)
    ''' Accessing Configuration'''
    # print('SECRET_KEY', app_config[config_name].SECRET_KEY)
    print('URL_PREFIX', app.config['URL_PREFIX'])

    return app

