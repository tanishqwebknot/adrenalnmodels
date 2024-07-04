from flask import request

from api.Users.models import Users
from api.Users.views import users_api
from common.connection import update_item
from common.response import success, failure

password_reset = Blueprint('/password_reset', __name__, url_prefix='/users')


@password_reset.route('/change_Password', methods=['POST'])
# Function to Change password of existing user
def new_password():
    try:
        data = request.get_json()
        password = data['password']
        email = data['email']
        existing_user = Users.query.filter_by(email=email).first()
        if existing_user is not None:
            existing_user.password = password
            existing_user.confirm_password = password
            update_item(existing_user)
            name = existing_user.full_name.title()
            return success("Password has been reset successfully!", [])
        else:
            return failure("Please check the details entered")
    except Exception as e:
        print(e)
        return failure("Something went wrong")


@password_reset.route('/fgt_password', methods=['POST'])
# Function to Change password of existing user
def forget_password():
    try:
        data = request.get_json()
        new_password = data['new_password']
        email = data['email']
        existing_user = Users.query.filter_by(email=email).first()
        if existing_user is not None:
            existing_user.new_password = new_password
            existing_user.confirm_password = new_password
            update_item(existing_user)
            name = existing_user.full_name.title()
            return success("Password has been changed  successfully!", [])
        else:
            return failure("Please check the details entered")
    except Exception as e:
        print(e)
        return failure("Something went wrong")
