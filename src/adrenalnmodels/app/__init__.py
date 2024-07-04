from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from pymongo import MongoClient

from config import app_config
from middleware import logger, auth 

db = SQLAlchemy()
BASE_URL_PREFIX = ''
bcrypt = Bcrypt()
client = MongoClient("mongodb+srv://lfsakkus4f:aIfaG5Zv0N2GiZnn@cluster0.petmkcb.mongodb.net/?retryWrites=true&w=majority")
mongodb = client['test']

def create_app(config_name):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(app_config[config_name])

    ''' App initialisation '''
    db.init_app(app)
    bcrypt.init_app(app)

    # Enabling Migration Setup
    migrate = Migrate(app, db)

    # Enabling CORS
    CORS(app)
    from api.fitbit.views import fitbit_api
    from api.garmin_users.views import garmin_api
    from api.gfit.views import gfit_api
    from api.watch.views import watch
    from api.cms.views import cms_api
    from api.comment.views import comment_api
    from api.contact.views import contact_api
    from api.Post.views import post_api
    from api.Group.views import group_api
    from api.health_parameters.views import health_paramters_api
    from api.media.views import media_api
    from api.notification.views import notification_api
    from api.Post.views import post_api
    from api.profile.views import profile_api
    from api.suggestions.views import suggestion_api
    from api.Users.views import users_api, verification_api

    from middleware.auth import auth_api_v1
    app.register_blueprint(fitbit_api)
    app.register_blueprint(garmin_api)
    app.register_blueprint(gfit_api)
    app.register_blueprint(watch)
    app.register_blueprint(auth_api_v1)
    app.register_blueprint(cms_api)
    app.register_blueprint(comment_api)
    app.register_blueprint(contact_api)
    app.register_blueprint(group_api)
    app.register_blueprint(health_paramters_api)
    app.register_blueprint(media_api)
    app.register_blueprint(notification_api)
    app.register_blueprint(post_api)
    app.register_blueprint(profile_api)
    app.register_blueprint(suggestion_api)
    app.register_blueprint(users_api)
    app.register_blueprint(verification_api)

    # register_blueprints(app)
    ''' Accessing Configuration'''
    # print('SECRET_KEY', app_config[config_name].SECRET_KEY)
    print('URL_PREFIX', app.config['URL_PREFIX'])

    return app


def attach_middleware(app):
    # Enabling Logger
    app.wsgi_app = logger.LoggerMiddleware(app.wsgi_app)

    # JWT Authentication
    app.wsgi_app = auth.AuthMiddleware(app.wsgi_app)

    # Enabling Common url prefix Validator
    # app.wsgi_app = api_prefix.PrefixMiddleware(app.wsgi_app, prefix='/api/v')


# def register_blueprints(app):
#     from api.garmin_users.views import garmin_api
#     from api.gfit.views import gfit_api
#     from api.watch.views import watch
#     from middleware.auth import auth_api_v1


#     if BASE_URL_PREFIX:
#         app.register_blueprint(auth_api_v1, url_prefix=BASE_URL_PREFIX)
#         app.register_blueprint(garmin_api, url_prefix=BASE_URL_PREFIX)
#         app.register_blueprint(gfit_api, url_prefix=BASE_URL_PREFIX)
#         app.register_blueprint(watch, url_prefix=BASE_URL_PREFIX)

#     else:
#         app.register_blueprint(auth_api_v1)
#         app.register_blueprint(garmin_api)
#         app.register_blueprint(gfit_api)
#         app.register_blueprint(watch)

#     # Listing all API endpoints
    print(app.url_map)