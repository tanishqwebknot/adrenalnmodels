import datetime
import json
from sqlalchemy import func
from api.Post.mongo_services import UserIntermediateRepository, ViewPostRepository, UserTimeLineRepository
from api.Post.services import add_intermediate_post, create_post, fetch_post, add_master_activity, get_activity, \
    betting_react, get_admin_posts, \
    get_wall_content, update_post, result_update, result_confirmation, fetch_post_own, add_post_react, \
    update_post_visibility, get_master_betting_items, get_promo_feeds, get_betting_members, remove_betting_members, \
    check_if_admin_post, add_admin_post, post_saved_posts, get_save_later, prepare_post_display_fileds, betting_details, \
    betting_conforamtion, check_expiry, post_list, set_default_visibility, post_detail_list, add_broadcast_post, \
    create_post_v2, betting_react_v2, result_update_v2, user_location, user_likes_list, reported_posts
from api.Users.models import Users, Membership
from api.Users.services import get_user_profile_details,membership
from api.comment.models import Comment
from api.contact.models import Contact
from flask import request, session, jsonify, Blueprint
from api.Post.models import AdminPost, Post, MasterActivity, BettingPost, Post_comments, PostCustomVisibility, \
    PostReact, MasterBettingItems, UserBettings
from common.connection import add_item, update_item, raw_select, delete_item, get_item
from common.response import success, failure
from middleware.auth import token_required, validate_token

post_api = Blueprint('user_post', __name__, url_prefix='/post')


# create Post
@post_api.route('', methods=['POST'])
@validate_token(action='create_post')
def post_create(current_user):
    data = request.json
    result = create_post_v2(current_user=current_user, data=data)
    return result


# delete Post
@post_api.route('/<post_id>', methods=['DELETE'])
@validate_token(action='delete_post')
def post_delete(current_user, post_id):
    data = request.json
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None)
    if existing_user:
        my_post = Post.query.get(post_id)
        if my_post.user_id == current_user.id:
            my_post.deleted_at = datetime.datetime.now()
            update_item(my_post)
    return success("SUCCESS", None, {"message": "Post deleted successfully!"})


# update post
@post_api.route('/update/<post_id>', methods=['PUT'])
@token_required
def edit_post(current_user, post_id):
    data = request.get_json()
    result = update_post(data, post_id, current_user)
    return result


@post_api.route('/feeds', methods=['GET'])
@validate_token(action='post_react')
def get_user_post(current_user):
    user_id = str(current_user.id)
    # try:
    """To get the timeline post of a user in the pagination format"""
    page, limit = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    add_admin_post(user_id)
    list = UserTimeLineRepository.get_user_post(user_id, page, limit)[0]
    page_details = list['metadata']
    post_list = [each.get('post_sequence') for each in list['data']]
    result = []
    if post_list:
        for data in post_list:
            post_data = {}
            user_tagged=[]
            post_details = Post.query.filter_by(id=data,deleted_at=None,status='active').first()
            if post_details:
                user_data = Users.query.filter_by(id=post_details.user_id, deleted_at=None,user_deleted_at=None).first()
                if user_data:
                    if post_details.is_tag == True:
                        tagged=PostCustomVisibility.query.filter_by(post_id=data,deleted_at=None).all()
                        if tagged:
                            for each in tagged:
                                tagged_users = {}
                                user_name=Users.query.filter_by(id=each.user_id,deleted_at=None,user_deleted_at=None).first()
                                tagged_users['name']=user_name.first_name
                                tagged_users['id']=user_name.id
                                user_tagged.append(tagged_users)
                    activity_meta_data={}
                    if post_details.type == 'record_activity':
                        post_data['meta_data'] = post_details.meta_data
                    if post_details.type == 'watch_activity':
                        post_data['meta_data'] = post_details.meta_data
                    if post_details.type == 'regular':
                        post_data['meta_data'] = post_details.meta_data
                    if post_details.type == 'activity':
                        activity_id = post_details.meta_data['activity']['activity_id']
                        activity_data = MasterActivity.query.filter_by(id=activity_id, deleted_at=None).first()
                        if activity_data:
                            activity_meta_data=post_details.meta_data
                            activity_meta_data['activity']['activity_name']=activity_data.name
                            activity_meta_data['activity']['activity_logo']=activity_data.logo
                            post_data['meta_data'] = activity_meta_data
                    if post_details.type == 'betting':
                        activity_meta_data=post_details.meta_data
                        if activity_meta_data:
                            post_data['meta_data'] = activity_meta_data
                        is_accepted = UserBettings.query.filter(UserBettings.user_id == user_id,
                                                                UserBettings.post_id == data,
                                                                UserBettings.deleted_at == None,
                                                                UserBettings.betting_status == 'confirmed').first()
                        if is_accepted:
                            post_data['is_accepted'] = True
                        else:
                            post_data['is_accepted'] = False
                        if post_details.expire_on:
                            post_data['expire_on'] = post_details.expire_on
                        member = UserBettings.query.filter_by(post_id=data,user_id=user_id, deleted_at=None).first()
                        if member:
                            post_data['betting_status'] = member.betting_status
                    post_data['user_info'] = get_user_profile_details(post_details.user_id)
                    post_data['id'] = data
                    post_data['location'] = post_details.location
                    post_data['title'] = post_details.title
                    post_data['description'] =post_details.description
                    post_data['created_at'] = post_details.created_at
                    post_data['visibility'] = post_details.visibility
                    post_data['promotion'] = post_details.promotion
                    post_data['type'] = post_details.type
                    post_data['share_url'] = post_details.share_link
                    post_data['tagged_users'] = user_tagged

                    like_count = PostReact.query.filter(PostReact.post_id == data, PostReact.type == 'like',
                                                        PostReact.is_liked == True).count()
                    comment_count = Comment.query.filter(Comment.post_id == data, Comment.deleted_at == None).count()
                    is_reacted = PostReact.query.filter(PostReact.user_id == current_user.id, PostReact.post_id == data,
                                                        PostReact.deleted_at == None).first()
                    if like_count >= 0:
                        post_data['likes'] = like_count
                    if comment_count >= 0:
                        post_data['comments'] = comment_count
                    if is_reacted is not None:
                        post_data['is_liked'] = is_reacted.is_liked
                    else:
                        post_data['is_liked'] = False

                    result.append(post_data)

            else:
                continue
        return success('SUCCESS',result,meta={'message':'Post Feed'})
    # except Exception as err:
    #     return failure(str(err))


########
@post_api.route('/promotion/feeds', methods=['GET'])
@token_required
def promo_post_wall(current_user):
    result = get_promo_feeds(current_user=current_user)
    return result


@post_api.route('/betting/react', methods=['POST'])
@token_required
def react_betting(current_user):
    data = request.json
    betting_react_v2(current_user=current_user, data=data)
    return success("SUCCESS", None, {"message": "Betting React updated"})


# to check betting post expiray time
@post_api.route('/check_post_expiry/<post_id>', methods=['POST'])
@validate_token(action='check_post_expiry')
def post_expiry(current_user,post_id):
    return check_expiry(current_user,post_id)


@post_api.route('/betting/result_update', methods=['POST'])
@validate_token(action='result_update')
def betting_result_update(current_user):
    data = request.json
    return result_update_v2(current_user, data)


@post_api.route('/betting/result_confirmation', methods=['POST'])
@token_required
def betting_result_confirmation(current_user):
    data = request.json
    result_confirmation(current_user, data)
    return success("SUCCESS", None, {"message": "Betting Result updated"})


@post_api.route('', methods=['GET'])
@token_required
def get_own_post(current_user):
    data = request.json
    return fetch_post_own(current_user, data)


@post_api.route('/<user_id>', methods=['GET'])
@token_required
def get_post(current_user, user_id=None):
    data = request.json
    result = fetch_post(current_user, user_id, data)
    return result



@post_api.route('/master/activity', methods=['POST'])
def master_activity():
    data = request.json
    result = add_master_activity(data)
    return result


@post_api.route('/master/activity', methods=['GET'])
def get_master_activity():
    data = request.json
    result = get_activity()
    return result


@post_api.route('/post_save_later/<post_id>', methods=['POST'])
@validate_token(action='post_saved_posts')
def user_post_saved(current_user,post_id):
    return post_saved_posts(current_user,post_id)


# GET save later post
@post_api.route('/save_later', methods=['GET'])
@validate_token(action='get_save_later')
def save_later_posts(current_user):
    return get_save_later(current_user)


@post_api.route('/post', methods=['GET'])
def get_data():
    data = request.json
    metadata = {}
    ROWS_PER_PAGE = 10
    page = request.args.get('page', 1, type=int)
    list_data = Post.query.paginate(page=page, per_page=ROWS_PER_PAGE, error_out=False)
    paginated_data = (list_data.items)
    for post_data in paginated_data:
        if post_data.metadatas:
            media_data = json.loads(post_data.metadatas)
            metadata["media"] = media_data
        post_list = Post.query.filter_by().first()
        if post_list:
            metadata["media"] = {
                "sorting_position": post_list.sorting_position,
                "type": post_list.type,
                "path": post_list.path,
                "thumbnaail": post_list.thumbnail,
                "media_id": post_list.media_id
            }
        post_data = Activity.query.filter_by().first()
        if post_data:
            metadata["activity"] = {
                "score": post_data.score,
                'difficulty': post_data.difficulty,
                'result': post_data.result,
                'duration': post_data.duration,
                'distance': post_data.distance,
                'calorie_burned': post_data.calorie_burned,
                'more_info':
                    [{
                        "label": "-",
                        "value": "-",
                        "sorting_position": 0
                    }]
            }

        post_data = BettingPost.query.filter_by().first()
        if post_data:
            metadata["betting"] = {"bet_on1": post_data.bet_on1,
                                   'bet_on2': post_data.bet_on2,
                                   'oods': post_data.oods,
                                   'betting_for': post_data.betting_for,
                                   'results': post_data.results,
                                   'participants': post_data.participants,

                                   }

    content = [{
        'id': data.id,
        'type': data.type,
        'title': data.title,
        'description': data.description,

    } for data in paginated_data]
    total_record = 0
    total_record = len(paginated_data)
    total_pages = total_record // ROWS_PER_PAGE + 1
    page_info = {
        'total_data': total_record,
        'total_pages': total_pages,
        'current_page': 1,
        'limit': ROWS_PER_PAGE
    }
    return jsonify({
        'success': True,
        'content': content,
        'page_info': page_info,
    })


@post_api.route('/comment', methods=['POST'])
def comment():
    data = request.json
    post_id = data['post_id']
    post_comments = data['post_comments']
    users_id = data['users_id']
    post_details = Post_comments(post_id=post_id, post_comments=post_comments, users_id=users_id)
    add_item(post_details)
    return success("SUCCESS", None, {"message": "comment is added "})


@post_api.route('/comments/post', methods=['GET'])
def commnt_details():
    data = request.json
    post_id = data['post_id']
    users_id = data['users_id']
    post_details = Post_comments(post_id=post_id, users_id=users_id)
    add_item(post_details)

    comment_details = Post_comments.query.all()
    result = []
    for comment_detail in comment_details:
        comment_fields = {}
        comment_fields['id'] = comment_detail.id
        comment_fields['comment'] = comment_fields.comment
        comment_fields['created_on'] = comment_fields.created_on
        comment_fields['like_count'] = comment_fields.like_count
        comment_fields['users_id'] = comment_fields.user_id
        comment_fields['reply'] = comment_fields.reply
        result.append(comment_detail)


@post_api.route('/react', methods=['POST'])
@validate_token(action='post_react')
def post_react(current_user):
    data = request.json
    return add_post_react(data, current_user)



@post_api.route('/update_visibility', methods=['POST'])
@validate_token(action='update_visibility')
def update_visibility(current_user):
    data = request.json
    return update_post_visibility(data, current_user)


# ADD master table for items
@post_api.route('/master_betting_items', methods=['POST'])
def master_betting_items():
    data = request.json
    add_items = MasterBettingItems(name=data.get('item'))
    add_item(add_items)
    return success("SUCCESS", {"message": "Items Added"})


# GET master table for items
@post_api.route('/master_betting_items', methods=['GET'])
def betting_items():
    get_items = get_master_betting_items()
    return get_items


@post_api.route('/betting_members/<post_id>', methods=['GET'])
def betting_members(post_id):
    get_members = get_betting_members(post_id)
    return get_members


@post_api.route('/remove_betting_member', methods=['POST'])
def remove_member():
    data = request.json
    post_id= data.get('post_id')
    user_id= data.get('user_id')
    delete_member = remove_betting_members(post_id,user_id)
    return success("SUCCESS", {})


@post_api.route('/betting_details/<post_id>', methods=['GET'])
@validate_token(action='betting_details')
def get_betting_details(current_user, post_id):
    return betting_details(current_user, post_id)


#owner betting confirmation
@post_api.route('/betting_confirmation', methods=['POST'])
@validate_token(action='betting_confirmation')
def confirm_betting(current_user):
    data = request.json
    return betting_conforamtion(current_user=current_user, data=data)



@post_api.route('/wall/<user_id>', methods=['POST'])
def get_wall(user_id):
    try:
        """To add the particular post in the timeline of the followers"""
        payload = request.get_json()
        post_id = payload['post_id']
        time_line = UserTimeLineRepository.get_one_by_user_id(user_id)
        if time_line is not None:
            if not check_if_admin_post(post_id[0]):
                time_line_post = time_line.post_sequence
                time_line_post = post_id + time_line_post
                UserTimeLineRepository.update(time_line, time_line_post)
            else:
                pass
        else:
            data = {'user_id': user_id, 'post_sequence': post_id}
            UserTimeLineRepository.create(data)
        return success('Success')
    except Exception as err:
        return failure(str(err))


#CRON
@post_api.route('/remove/Expired', methods=['GET'])
def remove_expired_post():
    try:
        posts = AdminPost.query.filter_by(func.date(post_expiry)==datetime.datetime.today()).all()
        post_list = [each.post_id for each in posts]
        timeline = UserTimeLineRepository.get_all_timelines()
        for each in timeline:
            updated_timeline = [post for post in each.post_sequence if post not in post_list]
            UserTimeLineRepository.update(each, updated_timeline)
        return success('Success')
    except Exception as err:
        return failure(str(err))


# GET my posts
@post_api.route('/user_posts/<user_id>', methods=['GET'])
@validate_token(action='get_my_post_list')
def list_of_posts(current_user,user_id):
    return post_list(current_user,user_id)


@post_api.route('/default_visibility', methods=['POST'])
@validate_token(action='post_visibility')
def default_visibility(current_user):
    data=request.json
    return set_default_visibility(current_user,data)


@post_api.route('/post_detail/<post_id>', methods=['GET'])
@validate_token(action='post_details')
def detail_post(current_user,post_id):
    return post_detail_list(current_user,post_id)


@post_api.route('/wall/intermediate', methods=['GET'])
def get_intermediate_wall():
    try:
        user_list = Membership.query.filter_by(membership_type='general',membership_status='active').all()
        for each in user_list:
            view_post = ViewPostRepository.get_one_by_user_id(str(each.user_id))
            viewed_post_list = []
            if view_post is not None:
                viewed_post_list = view_post.posts
            time_line = UserIntermediateRepository.get_one_by_user_id(str(each.user_id))
            if time_line is not None and time_line.is_dumped is False:
                continue
            add_intermediate_post(str(each.user_id), viewed_post_list)
        return success('Success', 'Admin post added')
    except Exception as err:
        return failure(str(err))


@post_api.route('/geo_location', methods=['POST'])
@validate_token(action='get_geo_location')
def get_user_location(current_user):
    data = request.json
    return user_location(data,current_user)


@post_api.route('/like_user_list/<post_id>', methods=['GET'])
@validate_token(action='post_liked_users_list')
def liked_users(current_user,post_id):
    return user_likes_list(current_user,post_id)


@post_api.route('/report', methods=['POST'])
@validate_token(action='post_report')
def reported_post(current_user):
    data = request.json
    return reported_posts(current_user,data)
