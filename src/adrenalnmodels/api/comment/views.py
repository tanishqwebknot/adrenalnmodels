import datetime
from flask import request,abort, Blueprint

from api.Post.models import Post
from api.Users.models import Users
from api.comment.models import Comment
from api.comment.services import add_comment, fetch_comment, update_parent_comment, add_comment_react
from common.connection import delete_item, update_item
from common.response import success
from middleware.auth import token_required, validate_token


comment_api = Blueprint('post_comment', __name__, url_prefix='/comment')


@comment_api.route('', methods=['POST'])
@validate_token(action='add_comment')
def create_comment(current_user):
    data = request.get_json()
    return add_comment(current_user, data)


@comment_api.route('/<post_id>', methods=['GET'])
@validate_token(action='get_comment_list')
def get_comment(current_user,post_id):
    # data = request.get_json()
    result = fetch_comment(current_user,post_id)
    return result


@comment_api.route('/react', methods=['POST'])
@validate_token(action='add_comment_react')
def add_comment_reaction(current_user):
    data = request.get_json()
    return add_comment_react(current_user, data)


@comment_api.route('/<comment_id>', methods=['PUT'])
@validate_token(action='update_comment')
def edit_comment(current_user, comment_id):
    data = request.get_json()
    return update_parent_comment(data, comment_id, current_user)



@comment_api.route('/<comment_id>', methods=['DELETE'])
@validate_token(action='delete_comment')
def delete_comment(current_user, comment_id):
    existing_user = Users.query.filter_by(id=current_user.id,deleted_at=None,user_deleted_at=None)
    if existing_user:
        my_comment = Comment.query.get(comment_id)
        post_owner = Post.query.filter_by(id=my_comment.post_id).first()
        if my_comment.user_id == current_user.id:
            my_comment.deleted_at = datetime.datetime.now()
            update_item(my_comment)
            return success('SUCCESS', meta={'message': "Comment deleted successfully!"})
        elif post_owner.user_id == current_user.id:
            my_comment.deleted_at = datetime.datetime.now()
            update_item(my_comment)
            return success('SUCCESS', meta={'message': "Comment deleted successfully!"})
        else:
            return success('SUCCESS', meta={'message': "Can't Delete!"})
    else:
        return success('SUCCESS', meta={'message': "User Not Found"})



