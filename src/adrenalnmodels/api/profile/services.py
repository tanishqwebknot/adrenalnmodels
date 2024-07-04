import datetime
import json
from flask import jsonify, request
from api.Group.models import GroupMembers, Group
from api.Post.models import PostCustomVisibility, PostReact, Post
from api.Users.services import get_user_profile_details
from api.comment.models import CommentTagging, Comment
from api.contact.models import Contact
from api.health_parameters.models import HealthParameterValues, HealthProfile, HealthReport
from api.media.models import Media
from api.notification.models import Notification
from api.profile.models import Hall_of_fame, Expert, Sport_level, Fitness_level, Master_course, MasterSports, \
    ProfileVisibility, TermsConditions
from sqlalchemy import func, or_
from api.Users.models import Users, Membership, UserDevice
from api.profile.models import Experties_background, CustomerTestimonials, FeaturedMedia, \
    ContactMe, Programme, SelectedPrograms, MasterProgram
from app import db
from common.connection import add_item, update_item, _query_execution
from common.response import success, failure


def add_expert_details(current_user):
    data = request.json
    expert_details = Expert(users_id=current_user.id, sport_level=data.get("sport_level", None),
                            adrenln_fitness=data.get("adrenln_fitness", None), level=data.get('level', None))
    add_item(expert_details)
    return success('SUCCESS', meta={'message': "expert details are added successfully"})


def add__hall_fame(current_user,data):
    if not data.get('level'):
        return success('SUCCESS', meta={'message': 'Please provied required field'})
    if not data.get('title'):
        return success('SUCCESS', meta={'message': 'Please add title'})
    hallOffame = Hall_of_fame(user_id=current_user.id, description=data.get('description', None),
                              title=data.get('title', None),
                              level=data.get('level', None), image=data.get('image', None))
    add_item(hallOffame)
    return success('SUCCESS', meta={'message': "hall of fame added successfully"})


def Update_hallofame_details(current_user, data, hall_of_fame_id):
    if not data.get('level'):
        return success('SUCCESS', meta={'meta': 'Please provied required field'})
    if not data.get('title'):
        return success('SUCCESS', meta={'meta': 'Please add title'})
    is_hall_of_fame = Hall_of_fame.query.filter_by(user_id=current_user.id, id=hall_of_fame_id).first()
    if is_hall_of_fame:
        is_hall_of_fame.title = data.get('title', None)
        is_hall_of_fame.description = data.get('description', None)
        is_hall_of_fame.level = data.get('level', None)
        is_hall_of_fame.image = data.get('image', None)
        update_item(is_hall_of_fame)
        return success('SUCCESS', meta={'message': 'hall of fame details updated Successfully'})
    else:
        return success('SUCCESS', meta={'message': 'Hall Of Fame Not Exists'})


def delete_hallOf_fame(current_user, hall_of_fame_id):
    is_hall_of_fame = Hall_of_fame.query.filter_by(id=hall_of_fame_id, user_id=current_user.id).first()
    if is_hall_of_fame:
        is_hall_of_fame.deleted_at = datetime.datetime.now()
        update_item(is_hall_of_fame)
        return success('SUCCESS', meta={'message': 'hall of fame deleted Successfully'})



def get_hall_of_fame(current_user, user_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    get_hall_fame_all = Hall_of_fame.query.filter_by(user_id=user_id, deleted_at=None).all()
    offset = per_page * (page - 1)
    get_hall_fame = """select * from hall_of_fame where user_id='{user_id}' and deleted_at is null ORDER BY greatest(created_at,
    update_at) DESC LIMIT {per_page} OFFSET {offset}""".format(user_id=user_id, per_page=per_page, offset=offset)
    get_hall_fame = _query_execution(get_hall_fame)
    total_record = len(get_hall_fame_all)
    total_pages = total_record // per_page + 1
    result = []
    if get_hall_fame:
        for halloffame_details in get_hall_fame:
            get_hall_fame_data = {}
            get_hall_fame_data['hall_of_fame_id'] = halloffame_details['id']
            get_hall_fame_data['title'] = halloffame_details['title']
            get_hall_fame_data['description'] = halloffame_details['description']
            get_hall_fame_data['level'] = halloffame_details['level']
            get_hall_fame_data['image'] = halloffame_details['image']
            result.append(get_hall_fame_data)
        return success("SUCCESS", result,
                       meta={"message": 'Hall Of Fame List',
                             'page_info': {'current_page': page, 'total_record': total_record,
                                           'total_pages': total_pages,
                                           'limit': per_page}})
    else:
        return success('SUCCESS', meta={'message': 'No data found'})


def get_primary_sport(current_user,user_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    all_sport_level = Sport_level.query.filter_by(user_id=user_id, is_primary=True,primary_deleted_at=None).all()
    get_sport_level = Sport_level.query.filter_by(user_id=user_id, is_primary=True,primary_deleted_at=None).order_by(Sport_level.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    get_sport_level = get_sport_level.items
    total_record = len(all_sport_level)
    total_pages = total_record // per_page + 1
    result = []
    if get_sport_level:
        for data in get_sport_level:
            master_sport = MasterSports.query.filter_by(id=data.sport_id).first()
            get_data = {}
            get_data['id'] = data.id
            get_data['is_primary'] = data.is_primary
            get_data['sport_id'] = data.sport_id
            get_data['name'] = master_sport.name
            get_data['logo'] = master_sport.logo
            get_data['fields'] = master_sport.fields
            result.append(get_data)
    return success('SUCCESS', result,meta={'message':'Primary Sports','page_info': {'current_page': page, 'total_record': total_record,
                                       'total_pages': total_pages,
                                       'limit': per_page}})


def get_secondry_sport(current_user, user_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    all_sport_level = Sport_level.query.filter_by(user_id=user_id, is_primary=False, secondary_deleted_at=None).all()
    get_sport_level = Sport_level.query.filter_by(user_id=user_id, is_primary=False,
                                                  secondary_deleted_at=None).order_by(
        Sport_level.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    get_sport_level = get_sport_level.items
    total_record = len(all_sport_level)
    total_pages = total_record // per_page + 1
    result = []
    if get_sport_level:
        for get_primary_details in get_sport_level:
            master_sport = MasterSports.query.filter_by(id=get_primary_details.sport_id,deleted_at=None).first()
            if master_sport:
                get_data = {}
                get_data['sport_level_id'] = get_primary_details.id
                get_data['is_primary'] = get_primary_details.is_primary
                get_data['sport_id'] = get_primary_details.sport_id
                get_data['name'] = master_sport.name
                get_data['logo'] = master_sport.logo
                result.append(get_data)
        return success('SUCCESS', result, meta={'message': 'Secondary Sports',
                                                'page_info': {'current_page': page, 'total_record': total_record,
                                                              'total_pages': total_pages,
                                                              'limit': per_page}})
    else:
        return success('SUCCESS', result, meta={'message': 'No data found'})


def sport_level(current_user, data):
    data = request.json
    sport_id = data.get("sport_id")
    more_info = data.get("more_info")
    parameters = data.get('parameters')
    if sport_id:
        sportDetails = Sport_level.query.filter_by(user_id=current_user.id, sport_id=sport_id,
                                                   is_primary=True, primary_deleted_at=None).first()
        if sportDetails and parameters:
            sport_level_parameters = prepare_sport_level(sport_id, parameters, more_info)
            if sport_level_parameters:
                for item in sport_level_parameters['parameters']:
                    if item['key'] == 'playing_level':
                        sportDetails.playing_level = item['value']
                        sportDetails.more_info = sport_level_parameters
                        sportDetails.deleted_at = None
                        update_item(sportDetails)
                return success('SUCCESS', meta={'message': 'Sport Level Updated'})
            else:
                return success('SUCCESS', meta={'message': 'Invalid data'})
        else:
            return success('SUCCESS', meta={'message': 'Data not found'})
    else:
        return success('SUCCESS', meta={'message': 'Please provide sportid'})


def prepare_sport_level(sport_id,parameters,more_info):
    final_sports = {"sport_id": sport_id,"more_info":more_info}
    master_sport = MasterSports.query.filter_by(id=sport_id,deleted_at=None).first()
    if master_sport:
        sport_fields = master_sport.fields
        master_sport_fields = []
        for fields in sport_fields:
            fields = fields['key']
            for item in parameters:
                if fields == item['key']:
                    master_sport_fields.append(item)
        final_sports['parameters'] = master_sport_fields
    return final_sports


def update_sport_levels(current_user, sport_level_id, data):
    more_info = data.get("more_info",None)
    parameters = data.get('parameters',None)
    sport_id = data.get('sport_id',None)
    if sport_level_id:
        sportDetails = Sport_level.query.filter_by(user_id=current_user.id, id=sport_level_id,is_primary=True, deleted_at=None,primary_deleted_at=None).first()
        if sportDetails and parameters:
            sport_level_parameters = prepare_sport_level(sport_id, parameters, more_info)
            if sport_level_parameters:
                for item in sport_level_parameters['parameters']:
                    if item['key'] == 'playing_level':
                        sportDetails.playing_level = item['value']
                        sportDetails.more_info = sport_level_parameters
                        update_item(sportDetails)
                return success('SUCCESS', meta={'message': 'updated successfully'})
            else:
                return success('SUCCESS', meta={'message': 'Invalid data'})
        else:
            return success('SUCCESS', meta={'message': 'data not found'})
    else:
        return success('SUCCESS', meta={'message': 'Please enter sport id'})


def fitness_level(current_user):
    data = request.json
    # time = data.get('time',None)
    value = data.get('value', None)
    seconds = sum(x * int(t) for x, t in zip([3600, 60, 1], value.split(":")))
    course_id = data.get('course_id', None)
    if not value:
        return success('SUCCESS', meta={'meta': 'Please provide time taken'})
    if not course_id:
        return success('SUCCESS', meta={'meta': 'Please select course'})
    course = Master_course.query.filter_by(id=course_id).first()
    if course:
        is_exist = Fitness_level.query.filter_by(user_id=current_user.id,course_id=course_id,deleted_at=None).first()
        if is_exist:
            is_exist.value = value
            is_exist.seconds = seconds
            update_item(is_exist)
            return success("SUCCESS", meta={'message': 'fitness level details are added successfully'})
        else:
            f_level = Fitness_level(value=value, course_id=course_id, user_id=current_user.id,seconds=seconds)
            add_item(f_level)
            return success("SUCCESS", meta={'message': ' fit_ness level details are added successfully'})
        level =course.level
        for val in level:
            if seconds <= val['lt'] and seconds >= val['gt']:
               fitness_level=val['level']
               f_level = Fitness_level(value=value,course_id=course_id,user_id=current_user.id,seconds=seconds)
               add_item(f_level)

        couser = Master_course.query.filter_by(users_id=g.user_id).first()
        fitness_details = Fitness_level( time=time ,expert_id=experts.id ,course_id =couser.id )
        add_item(fitness_details)

    else:
        return success('SUCCESS', meta={'message': ' data not found'})



def get_fitness_level(current_user,user_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    all_f_level = Fitness_level.query.filter_by(user_id=user_id, deleted_at=None).all()
    f_level = Fitness_level.query.filter_by(user_id=user_id, deleted_at=None).order_by(Fitness_level.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    f_level = f_level.items
    total_record = len(all_f_level)
    total_pages = total_record // per_page + 1
    if f_level:
        result = []
        for levels in f_level:
            course = Master_course.query.filter_by(id=levels.course_id).first()
            if course:
                fitness_level = course.level
                for level in fitness_level:
                    if int(levels.seconds) < level['lt'] and int(levels.seconds) > level['gt']:
                        fit_level = {}
                        fit_level['fitness_level'] = level['level']
                        fit_level['time_taken'] = levels.value
                        fit_level['course_id'] = course.id
                        fit_level['course_name'] = course.name
                        result.append(fit_level)
        fitness_levels = []
        for res in result:
            if res['fitness_level'] not in fitness_levels:
                fitness_levels.append(res['fitness_level'])
        if 'supreme' in fitness_levels:
            return success('SUCCESS', {'result': result, 'highest_level': 'supreme'},
                           meta={'message': 'Adrenline Fitness Level',
                                 'page_info': {'current_page': page, 'total_record': total_record,
                                               'total_pages': total_pages,
                                               'limit': per_page}})
        elif 'strong' in fitness_levels:
            return success('SUCCESS', {'result': result, 'highest_level': 'strong', },
                           meta={'message': 'Adrenliness Fitness Level',
                                 'page_info': {'current_page': page, 'total_record': total_record,
                                               'total_pages': total_pages,
                                               'limit': per_page}})
        else:
            return success('SUCCESS', {'result': result, 'highest_level': 'fit'},
                           meta={'message': 'Adrenlinerr Fitness Level',
                                 'page_info': {'current_page': page, 'total_record': total_record,
                                               'total_pages': total_pages,
                                               'limit': per_page}})
    else:
        return success("SUCCESS", meta={'message': 'Empty'})



def update_fitness_levels(current_user, course_id, data):
    value = data.get('value', None)
    seconds = sum(x * int(t) for x, t in zip([3600, 60, 1], value.split(":")))
    if not value:
        return success('SUCCESS', meta={'meta': 'Please provide time taken'})
    if not course_id:
        return success('SUCCESS', meta={'meta': 'Please select course'})
    if value:
        fitness_data = Fitness_level.query.filter_by(user_id=current_user.id, course_id=course_id,
                                                     deleted_at=None).first()
        if fitness_data:
            fitness_data.value = value
            fitness_data.seconds = seconds
            update_item(fitness_data)
            return success("SUCCESS", meta={'message': 'updated successfully'})
        else:
            return success('SUCCESS', meta={'message': 'data not found'})
    else:
        return success('SUCCESS', meta={'message': 'value not found'})



def delete_fitness_level(current_user, course_id):
    fitness_data = Fitness_level.query.filter_by(course_id=course_id, user_id=current_user.id, deleted_at=None).first()
    if fitness_data:
        fitness_data.deleted_at = datetime.datetime.now()
        update_item(fitness_data)
        return success('SUCCESS', meta={'message': 'deleted successfully'})
    else:
        return success('SUCCESS', meta={'message': 'data not found'})


def master_course(current_user):
    data = request.json
    name = data.get('name')
    field = data.get('field')
    media = data.get('media')
    level = data.get('level')
    # level = json.dumps(level)
    courses = Master_course(name=name, level=level, media=media, field=field)
    add_item(courses)
    return success('SUCCESS', meta={'message': 'master course details are added successfully'})


def add_expertise(current_user, data):
    experties_in = data.get('experties_in', None)
    description = data.get('description', None)
    if not experties_in:
        return success('SUCCESS',meta={'message':'Please select category'})
    if not description:
        return success('SUCCESS',meta={'message':'Please add description'})
    city = data.get('city', None)
    is_offer_programme = data.get('is_offer_programme', None)
    is_remote_consulting = data.get('is_remote_consulting', None)
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_user:
        if experties_in and city and description and \
                is_offer_programme is not None and is_remote_consulting is not None:
            experties_data = Experties_background(description=description, experties_in=experties_in,
                                                  city=city,
                                                  is_offer_programme=is_offer_programme,
                                                  is_remote_consulting=is_remote_consulting,
                                                  user_id=current_user.id)
            add_item(experties_data)
            return success('SUCCESS', meta={'message': 'added successfully'})
        else:
            return success('SUCCESS', meta={'message': "incomplete data"})
    else:
        return success('SUCCESS', meta={'message': "user not found"})


def updateExpertise(current_user, data, expertise_id):
    experties_in = data.get('experties_in', None)
    description = data.get('description', None)
    city = data.get('city', None)
    is_offer_programme = data.get('is_offer_programme', None)
    is_remote_consulting = data.get('is_remote_consulting', None)
    if not experties_in:
        return success('SUCCESS',meta={'message':'Please select category'})
    if not description:
        return success('SUCCESS',meta={'message':'Please add description'})
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_user:
        if experties_in and city and description:
            expertise_data = Experties_background.query.filter_by(user_id=current_user.id, id=expertise_id,
                                                                  deleted_at=None).first()
            if expertise_data:
                if experties_in:
                    expertise_data.experties_in = experties_in
                if description:
                    expertise_data.description = description
                if city:
                    expertise_data.city = city
                if is_offer_programme:
                    expertise_data.is_offer_programme = True
                else:
                    expertise_data.is_offer_programme = False

                if is_remote_consulting:
                    expertise_data.is_remote_consulting = True
                else:
                    expertise_data.is_remote_consulting = False
                update_item(existing_user)
                return success('SUCCESS', meta={'message': 'updated successfully'})
            else:
                return success('SUCCESS', meta={'message': 'data not found'})
        else:
            return success('SUCCESS', meta={'message': 'incomplete data '})
    else:
        return success('SUCCESS', meta={'message': 'invalid user'})


def get_expertise(current_user,user_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    all_expertise = Experties_background.query.filter_by(user_id=user_id, deleted_at=None).all()
    expertise = Experties_background.query.filter_by(user_id=user_id, deleted_at=None).order_by(Experties_background.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    expertise = expertise.items
    total_records = len(all_expertise)
    total_pages = total_records // per_page + 1
    if expertise:
        result = []
        for data in expertise:
            expertise_data = []
            for item in data.experties_in:
                name = MasterProgram.query.filter_by(id=item).first()
                experties_details ={}
                experties_details['category_id']=item
                experties_details['name']=name.name
                expertise_data.append(experties_details)
            experties_background = {}
            experties_background['id'] = data.id
            experties_background['description'] = data.description
            experties_background['city'] = data.city
            experties_background['experties_in'] = expertise_data
            experties_background['is_offer_programme'] = data.is_offer_programme
            experties_background['is_remote_consulting'] = data.is_remote_consulting
            result.append(experties_background)
        return success('SUCCESS', result, meta={'message': 'expertise and background list',
                                                'page_info': {'current_page': page, 'total_record': total_records,
                                                              'total_pages': total_pages,
                                                              'limit': per_page}})
    else:
        return success('SUCCESS', meta={'message': 'no data found'})


def delete_expertise_details(current_user, experties_background_id):
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_user:
        expertise_data = Experties_background.query.filter_by(id=experties_background_id, deleted_at=None).first()
        if expertise_data:
            expertise_data.deleted_at = datetime.datetime.now()
            update_item(expertise_data)
            return success('SUCCESS', meta={'message': 'deleted successfully'})
        else:
            return success('SUCCESS', meta={'message': 'data not found'})
    else:
        return success('SUCCESS', meta={'message': 'invalid user'})


def featured_media(current_user, data):
    title = data.get('title', None)
    media = data.get('media', None)
    if not title:
        return success('SUCCESS',meta={'message':'Please add title'})
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_user.business_account == True:
        featured_media = FeaturedMedia(title=title, description=data.get('description', None),
                                       media=media, user_id=current_user.id)
        add_item(featured_media)
        return success('SUCCESS', meta={'message': 'Media Added'})
    else:
        return success('SUCCESS', meta={'message': 'User Not Found'})


def featured_media_update(current_user, data, media_id):
    title=data.get('title', None)
    media=data.get('media', None)
    if not title:
        return success('SUCCESS',meta={'message': 'Please add title'})
    is_featured_media = FeaturedMedia.query.filter_by(user_id=current_user.id, id=media_id, deleted_at=None).first()
    if is_featured_media:
        is_featured_media.title = data.get('title', None)
        is_featured_media.description = data.get('description', None)
        is_featured_media.media = media
        update_item(is_featured_media)
        return success('SUCCESS', meta={'message': 'Featured Media Details Updated Successfully'})


def get_featured_media(current_user,user_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    all_featured_media = FeaturedMedia.query.filter_by(user_id=user_id,deleted_at=None).all()
    my_featured_media = FeaturedMedia.query.filter_by(user_id=user_id,deleted_at=None).order_by(FeaturedMedia.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    my_featured_media = my_featured_media.items
    total_record = len(all_featured_media)
    total_pages = total_record // per_page + 1
    if my_featured_media:
        result = []
        for data in my_featured_media:
            featured_media = {}
            featured_media['id'] = data.id
            featured_media['title'] = data.title
            featured_media['description'] = data.description
            featured_media['media'] = data.media
            result.append(featured_media)
        return success('SUCCESS', result, meta={'message': 'Featured Media',
                                                'page_info': {'current_page': page, 'total_record': total_record,
                                                              'total_pages': total_pages,
                                                              'limit': per_page}})
    else:
        return success('SUCCESS',meta={'No Media Added'})


def addProgramme(current_user, data):
    category_id = data.get('category_id', None)
    title = data.get('title', None)
    media = data.get('media', [])
    city = data.get('city', None)
    if not title:
        return success('SUCCESS', meta={'message': 'Please add title'})
    if not city:
        return success('SUCCESS', meta={'message': 'Please add your city'})
    if not category_id:
        return success('SUCCESS', meta={'message': 'Please add category'})
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None, user_deleted_at=None).first()
    if existing_user:
        master_programme = MasterProgram.query.filter_by(id=category_id, deleted_at=None).first()
        if master_programme:
            if existing_user.business_account == True:
                my_programmes = Programme(description=data.get('description', None), city=city,
                                          title=title, category=master_programme.name,
                                          media=media, master_programs_id=category_id,
                                          user_id=current_user.id,is_featured=0)
                add_item(my_programmes)
                return success('SUCCESS', meta={'message': 'Programme Added'})
            else:
                return success('SUCCESS', meta={'message': 'Not a business account holder'})
        else:
            return success('SUCCESS', meta={'message': 'No master programme'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid user'})



def get_my_programme(current_user, user_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    all_progremme = Programme.query.filter_by(user_id=user_id, deleted_at=None).order_by(Programme.created_at.desc()).all()
    get_progremme = Programme.query.filter_by(user_id=user_id, deleted_at=None).order_by(Programme.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    get_progremme = get_progremme.items
    total_records = len(all_progremme)
    total_pages = total_records // per_page + 1
    if get_progremme:
        result = []
        for data in get_progremme:
            category = MasterProgram.query.filter_by(id=data.master_programs_id, deleted_at=None).first()
            category_data = {}
            if category:
                category_data['id'] = category.id
                category_data['name'] = category.name
            user_programme = {}
            user_programme['id'] = data.id
            user_programme['title'] = data.title
            user_programme['description'] = data.description
            user_programme['city'] = data.city
            user_programme['category'] = category_data
            user_programme['media'] = data.media
            user_programme['is_featured'] = data.is_featured
            result.append(user_programme)
        return success('SUCCESS', result, meta={'message': 'Featured Programmes',
                                                'page_info': {'current_page': page, 'limit': per_page,
                                                              'total_record': total_records,
                                                              'total_pages': total_pages}})
    return success('SUCCESS', meta={'message': 'No Programme Found'})


def get_all_programme(current_user):
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_user:
        page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
        all_progremme = Programme.query.filter_by(deleted_at=None).all()
        get_progremme = Programme.query.filter_by(deleted_at=None).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        get_progremme = get_progremme.items
        total_records = len(all_progremme)
        total_pages = total_records // per_page + 1
        if get_progremme:
            result = []
            for data in get_progremme:
                category = MasterProgram.query.filter_by(id=data.master_programs_id, deleted_at=None).first()
                category_data = {}
                if category:
                    category_data['id'] = category.id
                    category_data['name'] = category.name
                user_programme = {}
                user_programme['id'] = data.id
                user_programme['description'] = data.description
                user_programme['city'] = data.city
                user_programme['category'] = category_data
                user_programme['title'] = data.title
                user_programme['media'] = data.media
                result.append(user_programme)
            return success('SUCCESS', result, meta={'message': 'Featured Programmes',
                                                    'page_info': {'current_page': page, 'limit': per_page,
                                                                  'total_record': total_records,
                                                                'total_pages': total_pages}})
        else:
            return success('SUCCESS', meta={'message': 'No Programme Found'})
    else:
        return success('SUCCESS', meta={'message': 'User Not Found'})


def updateProgramme(current_user, data, programme_id):
    title = data.get('title', None)
    city = data.get('city', None)
    category_id = data.get('category_id', None)
    media = data.get('media', None)
    if not title:
        return success('SUCCESS',meta={'message': 'Please add title'})
    if not city:
        return success('SUCCESS',meta={'message': 'Please add your city'})
    if not category_id:
        return success('SUCCESS',meta={'message': 'Please add category'})
    is_programme = Programme.query.filter_by(user_id=current_user.id, id=programme_id, deleted_at=None).first()
    if is_programme:
        master_programme = MasterProgram.query.filter_by(id=category_id, deleted_at=None).first()
        if master_programme:
            is_programme.title = data.get('title', None)
            is_programme.city = data.get('city', None)
            is_programme.category = master_programme.name
            is_programme.description = data.get('description', None)
            is_programme.media = data.get('media', None)
            update_item(is_programme)
            return success('SUCCESS', meta={'message': 'Programme Details Updated Successfully'})
        else:
            return success('SUCCESS', meta={'message': 'Invalid master programme'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid programme'})


def addTestimonials(current_user, data):
    description=data.get('description', None)
    name=data.get('name', None)
    media = data.get('media', None)
    if not description:
        return success('SUCCESS',meta={'message':'Please add description'})
    if not name:
        return success('SUCCESS',meta={'message':'Please add name'})
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_user.business_account == True:
        testimonials = CustomerTestimonials(description=description,user_id=current_user.id, name=data.get('name', None),media=media)
        add_item(testimonials)
        return success('SUCCESS',meta={'message':'Customer Testimonial Added'})
    else:
        return success('SUCCESS',meta={'message':'You are not a business User.'})


def get_testimonials(current_user,user_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    all_testimonials = CustomerTestimonials.query.filter_by(user_id=user_id,deleted_at=None).all()
    testimonials = CustomerTestimonials.query.filter_by(user_id=user_id,deleted_at=None).order_by(CustomerTestimonials.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
    testimonials = testimonials.items
    total_records = len(all_testimonials)
    total_pages = total_records // per_page + 1
    if testimonials:
        result = []
        for data in testimonials:
            testimonials = {}
            testimonials['id'] = data.id
            testimonials['name'] = data.name
            testimonials['description'] = data.description
            testimonials['media'] = data.media
            result.append(testimonials)
        return success('SUCCESS',result,meta={'message':'customer Testimonials','page_info': {'current_page': page, 'limit': per_page,
                                                              'total_record': total_records,
                                                              'total_pages': total_pages}})
    else:
        return success('SUCCESS', meta={'message': 'No Data Found'})


def updateTestimonials(current_user, data, testimonials_id):
    description = data.get('description', None)
    name = data.get('name', None)
    media = data.get('media', None)
    if not description:
        return success('SUCCESS',meta={'message': 'Please add description'})
    if not name:
        return success('SUCCESS',meta={'message': 'Please add name'})
    is_testimonial = CustomerTestimonials.query.filter_by(user_id=current_user.id, id=testimonials_id,deleted_at=None).first()
    if is_testimonial:
        is_testimonial.name = data.get('name', None)
        is_testimonial.media = data.get('media', None)
        is_testimonial.description = data.get('description', None)
        update_item(is_testimonial)
        return success('SUCCESS',meta={'message':'Details Updated'})
    else:
        return success('SUCCESS', meta={'message': 'data not found'})


def add_contact_me(current_user, data, business_account_id):
    existing_user = Users.query.filter_by(id=current_user.id,deleted_at=None,user_deleted_at=None).first()
    contact_me = ContactMe(from_user_id=current_user.id, to_user_id=business_account_id, name=existing_user.first_name,
                           email=existing_user.email, mobile=existing_user.phone, is_submited=False)
    add_item(contact_me)

    is_submited = data.get('is_submited')
    if is_submited:
        contact_me.name = data.get('name')
        contact_me.email = data.get('email')
        contact_me.mobile = data.get('mobile')
        contact_me.description = data.get('description', None)
        contact_me.is_submited = data.get('is_submited')
        update_item(contact_me)
        return success("SUCCESS", meta={"message": "Contact Details Added"})


def get_list_expert(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if existing_user:
        all_experts = Users.query.filter_by(business_account=True,user_deleted_at=None,deleted_at=None).all()
        experts = Users.query.filter_by(business_account=True,user_deleted_at=None,deleted_at=None).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        total_records = len(all_experts)
        experts = experts.items
        total_pages = total_records // per_page + 1
        result = []
        for data in experts:
            expert_in = Programme.query.filter_by(user_id=data.id).first()
            expert_list = {}
            if expert_in:
                expert_list['expertise'] = expert_in.title
            expert_list['id'] = data.id
            expert_list['name'] = data.first_name
            expert_list['profile_image'] = data.profile_image
            result.append(expert_list)
        return success('SUCCESS', result, meta={'message': 'Expert List',
                                                'page_info': {'current_page': page, 'limit': per_page,
                                                              'total_record': total_records,
                                                              'total_pages': total_pages}})


def search_master_program_list(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    keyword = request.args.get('keyword')
    if keyword:
        search_string = '%{}%'.format(keyword)
        search_program_list = Programme.query.filter(or_(
            Programme.title.ilike(search_string), Programme.category.ilike(search_string)),
            Programme.deleted_at == None).order_by(Programme.is_featured.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
        program_list = search_program_list.items
        total_record = len(program_list)
        total_pages = total_record // per_page + 1
        if program_list:
            result = []
            for data in program_list:
                user_programme = {}
                user_programme['id'] = data.id
                user_programme['title'] = data.title
                user_programme['description'] = data.description
                user_programme['city'] = data.city
                user_programme['category'] = data.category
                user_programme['meta_data'] = data.media
                result.append(user_programme)
            return success("SUCCESS", result, meta={"message": "Program Search List",
                                                        'page_info': {'total_record': total_record,
                                                                      'limit': per_page}})
        else:
            return success('SUCCESS', meta={'message': "No Programmes Found"})

    else:
        return success('SUCCESS', meta={'message': "Please add keywords"})


def select_programme(current_user, data):
    if data:
        programme_id = data.get('programme_id')
        existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
        if existing_user:
            for program in programme_id:
                list_programs = SelectedPrograms(programme_id=program, user_id=current_user.id)
                add_item(list_programs)
    return success("SUCCESS", meta={'message': "programs are added successfully"})


def program_suggesion(current_user, data):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    result=[]
    id=data.get('id', [])
    for list_ids in id:
        get_expert_list = """SELECT * FROM programme WHERE (master_programs_id::text LIKE '%{list_ids}%') 
            AND (deleted_at is null)""".format(list_ids=list_ids)
        offset = per_page * (page - 1)
        program_list = """SELECT * FROM programme WHERE (master_programs_id::text LIKE '%{list_ids}%') AND 
            (deleted_at is null) ORDER BY is_featured desc ,greatest(created_at,update_at) DESC LIMIT {per_page} OFFSET {offset}""".format(list_ids=list_ids,
                                                                                        per_page=per_page,offset=offset)
        programs = _query_execution(program_list)
        if programs:
            for data_item in programs:
                contact = Contact.query.filter_by(contact_id=data_item['user_id'], user_id=current_user.id,
                                                    deleted_at=None).first()
                user_programme = {}
                user_programme['user_info'] = get_user_profile_details(data_item['user_id'])
                if contact:
                    user_programme['is_following'] = contact.is_following
                    user_programme['friend_status'] = contact.friend_status
                else:
                    user_programme['is_following'] = False
                    user_programme['friend_status'] = False
                user_programme['media'] = data_item.get('media')
                user_programme['category'] = data_item.get('category')
                user_programme['description'] = data_item.get('description')
                user_programme['id'] = data_item.get('id')
                user_programme['title'] = data_item.get('title')
                user_programme['is_featured'] = data_item.get('is_featured')
                user_programme['city'] = data_item.get('city')
                result.append(user_programme)
    total_records = len(result)
    total_pages = total_records // per_page + 1
    return success('SUCCESS', result, meta={'message': 'Expert List',
                                                        'page_info': {'current_page': page, 'limit': per_page,
                                                            'total_record': total_records,
                                                            'total_pages': total_pages}})



def master_programs(current_user):
    data = request.json
    name = data.get('name')
    add_master = MasterProgram(name=name)
    add_item(add_master)
    return success('SUCCESS', meta={'message': 'master_program  details  are add successfully'})


def get_list_master_programs():
    master_programs = MasterProgram.query.order_by(MasterProgram.name).all()
    if master_programs:
        result = []
        for data in master_programs:
            master_list = {}
            master_list['name'] = data.name
            master_list['id'] = data.id
            result.append(master_list)
        return success('SUCCESS', result, meta={'message': 'Master probrams'})
    else:
        return success('SUCCESS',meta={'message':'No data found'})


def sport_level_list(current_user, user_id):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    all_sport_level = Sport_level.query.filter_by(user_id=user_id, deleted_at=None,primary_deleted_at=None).all()
    sport_level = Sport_level.query.filter_by(user_id=user_id, deleted_at=None, is_primary=True,primary_deleted_at=None).order_by(
        Sport_level.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    sport_level = sport_level.items
    total_records = len(all_sport_level)
    total_pages = total_records // per_page + 1
    if sport_level:
        result = []
        highest_level = ''
        for data in sport_level:
            json_data = data.more_info
            if json_data:

                sport_name = MasterSports.query.filter_by(id=data.sport_id, deleted_at=None).first()

                json_data['sport_name'] = sport_name.name
                json_data['sport_logo'] = sport_name.logo
                if sport_name:
                    get_data = {}
                    get_data['id'] = data.id
                    get_data['is_primary'] = data.is_primary
                    get_data['sport_level_data'] = json_data
                    result.append(get_data)
                else:
                    return success('SUCCESS', meta={'message': 'sport not found'})

        p_level = []
        level_list = Sport_level.query.filter_by(user_id=user_id, deleted_at=None, is_primary=True,primary_deleted_at=None).all()
        for detail in level_list:
            p_level.append(detail.playing_level)
        if 'worldchampion' in p_level:
            highest_level = 'worldchampion'

        elif 'national' in p_level:
            highest_level = 'national'

        elif 'competition' in p_level:
            highest_level = 'competition'

        elif 'performance' in p_level:
            highest_level = 'performance'

        elif 'recreational' in p_level:
            highest_level = 'recreational'
        return success('SUCCESS', {'result': result, 'highest_level': highest_level},
                       meta={'message': 'Master Sports List',
                             'page_info': {'current_page': page, 'limit': per_page,
                                           'total_record': total_records,
                                           'total_pages': total_pages}})
    else:
        return success('SUCCESS', meta={'message': 'no data found'})


def get_master_sports():
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    master_sports = MasterSports.query.filter_by(deleted_at=None).all()
    list_master_sports = MasterSports.query.filter_by(deleted_at=None).order_by(
        MasterSports.name.asc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    list_master_sports = list_master_sports.items
    total_records = len(master_sports)
    total_pages = total_records // per_page + 1
    if list_master_sports:
        result = []
        for data in list_master_sports:
            sport_list = {}
            sport_list['name'] = data.name
            sport_list['logo'] = data.logo
            sport_list['id'] = data.id
            sport_list['feilds'] = data.fields
            result.append(sport_list)
        return success('SUCCESS', result, meta={'message': 'Master Sports List',
                                                'page_info': {'current_page': page, 'limit': per_page,
                                                              'total_record': total_records,
                                                              'total_pages': total_pages}})
    else:
        return success('SUCCESS',meta={'message':'No data found'})


def search_sport(current_user):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    keyword = request.args.get('keyword')
    if keyword:
        search_string = '%{}%'.format(keyword)

        search_sports_lists = MasterSports.query.filter(MasterSports.name.ilike(search_string),
                                                        MasterSports.deleted_at == None).all
        search_sports_list = MasterSports.query.filter(MasterSports.name.ilike(search_string),
                                                       MasterSports.deleted_at == None).paginate(
            page=page,
            per_page=per_page,
            error_out=False)

        sport_list = search_sports_list.items
        if sport_list:
            result = []
            for data in sport_list:
                sport_list_data = {}
                sport_list_data['id'] = data.id
                sport_list_data['name'] = data.name
                sport_list_data['logo'] = data.logo
                # sport_list['logo'] = int(data.logo)
                result.append(sport_list_data)
            return success("SUCCESS", result, meta={"message": "Master Sports Search List",
                                                    'page_info': {'limit': per_page, 'current_page': page}})
        else:
            return success("SUCCESS", meta={'message': "Not Found"})
    else:
        return success("SUCCESS", meta={'message': "Please enter keywords"})


def master_course_list():
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    course_list_all = Master_course.query.all()
    course_list = Master_course.query.paginate(
        page=page,
        per_page=per_page,
        error_out=False)
    course_list = course_list.items
    total_records = len(course_list_all)
    total_pages = total_records // per_page + 1
    if course_list:
        result = []
        for data in course_list:
            master_course = {}
            master_course['id'] = data.id
            master_course['name'] = data.name
            master_course['field'] = data.field
            master_course['media'] = data.media
            master_course['level'] = data.level
            result.append(master_course)
        return success('SUCCESS', result, meta={'message': 'Master Course List',
                                                'page_info': {'current_page': page, 'limit': per_page,
                                                              'total_record': total_records,
                                                              'total_pages': total_pages}})
    else:
        return success('SUCCESS',meta={'message': 'No Data Found'})


def add_visibility(current_user, data):
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        visibility = data.get("visibility", None)
        section = data.get("section", None)

        sections = ["hall_of_fame", "fitness_level", "secondary_sport", "sport_level", "primary_sport"]
        visibilities = ['all', 'friends', 'private']

        if visibility not in visibilities:
            return success('SUCCESS', meta={'message': 'Invalid visibility'})
        if section not in sections:
            return success('SUCCESS', meta={'message': 'Invalid section'})

        user_already_exist = ProfileVisibility.query.filter_by(user_id=current_user.id,
                                                               section=section, deleted_at=None).first()
        if user_already_exist:
            user_already_exist.visibility = visibility
            update_item(user_already_exist)
            return success('SUCCESS', meta={'message': 'visibility updated'})
        else:
            new_user = ProfileVisibility(section=section, visibility=visibility, user_id=current_user.id)
            add_item(new_user)
            return success('SUCCESS', meta={'message': 'visibility added'})
    else:
        return success('SUCCESS', meta={'message': 'invalid user'})


def profile_visibility_section(current_user):
    visibility= ProfileVisibility.query.filter_by(user_id=current_user.id , deleted_at=None).all()
    result=[]
    profile_visibility = {}
    if visibility:
        for data in visibility:
            profile_visibility[data.section] =data.visibility
        result.append(profile_visibility)
        return success('SUCCESS', result, meta={'message': 'Profile Visibility'})
    else:
        profile_visibility['fitness_level']='all'
        profile_visibility['hall_of_fame']='all'
        profile_visibility['primary_sport']='all'
        profile_visibility['secondary_sport']='all'
        profile_visibility['sport_level']='all'
        result.append(profile_visibility)
        return success('SUCCESS', result, meta={'message':'Profile Visibility'})


def profile_terms_conditions(current_user, section):
    existing_user = Users.query.filter_by(id=current_user.id,deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        section_exist = TermsConditions.query.filter_by(section=section,deleted_at=None).first()
        if section_exist:
            result = {}
            result['id'] = section_exist.id
            result['section'] = section_exist.section
            result['terms_condition'] = section_exist.terms_condition
            return success('SUCCESS', result, meta={'message': 'Terms and Conditions'})
        else:
            return success('SUCCESS', meta={'message': 'Invalid Section'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid User'})


def delete_account(current_user):
    exist_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if exist_user:
        status_exist = Membership.query.filter_by(user_id=current_user.id, membership_status='active',
                                                  deleted_at=None).first()
        if status_exist:
            status_exist.membership_status = 'inactive'
            update_item(status_exist)
            exist_user.deleted_at = datetime.datetime.now()
            update_item(exist_user)
            return success('SUCCESS', meta={'message': 'Deleted account successfully'})
        else:
            return success('SUCCESS', meta={'message': 'Invalid membership status'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid user'})


def user_delete_account(current_user):
    exist_user = Users.query.filter_by(id=current_user.id, deleted_at=None, user_deleted_at=None).first()
    if exist_user:
        status_exist = Membership.query.filter_by(user_id=current_user.id, membership_status='active',
                                                  deleted_at=None).first()
        if status_exist:
            status_exist.membership_status = 'deleted'
            update_item(status_exist)
            exist_user.user_deleted_at = datetime.datetime.now()
            update_item(exist_user)

            # delete posts
            user_posts = Post.query.filter_by(user_id=current_user.id, deleted_at=None).all()
            if user_posts:
                for item in user_posts:
                    item.deleted_at = datetime.datetime.now()
                    update_item(user_posts)

            # delete hall_of_fame
            user_hall_of_fame = Hall_of_fame.query.filter_by(user_id=current_user.id, deleted_at=None).all()
            if user_hall_of_fame:
                for item in user_hall_of_fame:
                    item.deleted_at = datetime.datetime.now()
                    update_item(user_hall_of_fame)

            # delete sports/sport_level
            user_sports = Sport_level.query.filter_by(user_id=current_user.id, deleted_at=None).all()
            if user_sports:
                for item in user_sports:
                    item.deleted_at = datetime.datetime.now()
                    item.primary_deleted_at = datetime.datetime.now()
                    item.secondary_deleted_at = datetime.datetime.now()
                    update_item(user_sports)

            # delete friends and followers
            my_contact = Contact.query.filter(or_(Contact.contact_id == current_user.id,
                                                    Contact.user_id == current_user.id),
                                                Contact.deleted_at == None).all()
            if my_contact:
                for item in my_contact:
                    item.deleted_at = datetime.datetime.now()
                    update_item(my_contact)

            # user groups
            user_groups = GroupMembers.query.filter_by(user_id=current_user.id, status='active', deleted_at=None).all()
            if user_groups:
                for item in user_groups:
                    if item.type == 'admin':
                        check_admin_id = Group.query.filter_by(id=item.group_id, user_id=current_user.id,
                                                               deleted_at=None).first()
                        if check_admin_id:
                            check_existing_admin = GroupMembers.query.filter(GroupMembers.group_id == item.group_id,
                                                                             GroupMembers.type == 'admin',
                                                                             GroupMembers.user_id != current_user.id,
                                                                             GroupMembers.status=='active',
                                                                             GroupMembers.deleted_at == None).first()
                            # if no other admin exist
                            if check_existing_admin is None:
                                sorted_list = GroupMembers.query.filter(GroupMembers.group_id == item.group_id,
                                                                        GroupMembers.type == 'user',
                                                                        GroupMembers.status == 'active',
                                                                        GroupMembers.user_id != current_user.id,
                                                                        GroupMembers.deleted_at == None) \
                                    .order_by(GroupMembers.created_at)
                                if list(sorted_list):
                                    member_data = list(sorted_list)[0]
                                    check_admin_id.user_id = member_data.user_id
                                    db.session.commit()

                                    make_admin = GroupMembers.query.filter_by(user_id=member_data.user_id,
                                                                              group_id=item.group_id,
                                                                              status='active').first()
                                    if make_admin:
                                        make_admin.type='admin'
                                        update_item(make_admin)
                                else:
                                    check_admin_id.deleted_at=datetime.datetime.now()
                                    update_item(check_admin_id)

                            else:
                                # if there is another admin
                                sorted_list = GroupMembers.query.filter(GroupMembers.group_id == item.group_id,
                                                                        GroupMembers.type == 'admin',
                                                                        GroupMembers.user_id != current_user.id,
                                                                        GroupMembers.deleted_at == None) \
                                    .order_by(GroupMembers.created_at)
                                if list(sorted_list):
                                    member_data = list(sorted_list)[0]
                                    check_admin_id.user_id = member_data.user_id
                                    db.session.commit()
                    delete_group_member = GroupMembers.query.filter(GroupMembers.group_id == item.group_id,
                                                                    GroupMembers.user_id == current_user.id,
                                                                    GroupMembers.deleted_at == None).first()
                    if delete_group_member:
                        delete_group_member.deleted_at = datetime.datetime.now()
                        db.session.commit()

            # user fitness level
            user_fitness=Fitness_level.query.filter_by(user_id=current_user.id,deleted_at=None).all()
            if user_fitness:
                for item in user_fitness:
                    item.deleted_at = datetime.datetime.now()
                    update_item(user_fitness)

            # user device
            user_device = UserDevice.query.filter_by(user_id=current_user.id, deleted_at=None).all()
            if user_device:
                for item in user_device:
                    item.deleted_at = datetime.datetime.now()
                    update_item(user_device)

            # user media
            user_media = Media.query.filter_by(user_id=current_user.id, deleted_at=None).all()
            if user_media:
                for item in user_media:
                    item.deleted_at = datetime.datetime.now()
                    update_item(user_media)

            # user programme
            user_programme = Programme.query.filter_by(user_id=current_user.id,deleted_at=None).all()
            if user_programme:
                for item in user_programme:
                    item.deleted_at=datetime.datetime.now()
                    update_item(user_programme)

            # user_profile_visibility
            user_profile_visibility = ProfileVisibility.query.filter_by(user_id=current_user.id,deleted_at=None).all()
            if user_profile_visibility:
                for item in user_profile_visibility:
                    item.deleted_at=datetime.datetime.now()
                    update_item(user_profile_visibility)

            # user_post_react
            user_post_react=PostReact.query.filter_by(user_id=current_user.id,deleted_at=None).all()
            if user_post_react:
                for item in user_post_react:
                    item.deleted_at=datetime.datetime.now()
                    update_item(user_post_react)

            # user post_custom_visibility
            user_post_custom_visibility = PostCustomVisibility.query.filter_by(user_id=current_user.id,deleted_at=None).all()
            if user_post_custom_visibility:
                for item in user_post_custom_visibility:
                    item.deleted_at=datetime.datetime.now()
                    update_item(user_post_custom_visibility)

            # user post_comment
            user_post_comment = Comment.query.filter_by(user_id=current_user.id,deleted_at=None).all()
            if user_post_comment:
                for item in user_post_comment:
                    item.deleted_at=datetime.datetime.now()
                    update_item(user_post_comment)
                    parent_comment = Comment.query.filter_by(parent_id=item.id,deleted_at=None).all()
                    if parent_comment:
                        for comment in parent_comment:
                            comment.deleted_at=datetime.datetime.now()
                            update_item(parent_comment)


            # user health_profile
            user_health_profile = HealthProfile.query.filter_by(user_id=current_user.id,deleted_at=None).all()
            if user_health_profile:
                for item in user_health_profile:
                    item.deleted_at=datetime.datetime.now()
                    update_item(user_health_profile)
                    health_report = HealthReport.query.filter_by(healthprofile_id=item.id,deleted_at=None).all()
                    if health_report:
                        for report in health_report:
                            report.deleted_at=datetime.datetime.now()
                            update_item(health_report)
                            health_para = HealthParameterValues.query.filter_by(healthreport_id=report.id,deleted_at=None).all()
                            if health_para:
                                for para in health_para:
                                    para.deleted_at=datetime.datetime.now()
                                    update_item(health_para)

            # user_featued_media
            user_featued_media = FeaturedMedia.query.filter_by(user_id=current_user.id,deleted_at=None).all()
            if user_featued_media:
                for media in user_featued_media:
                    media.deleted_at = datetime.datetime.now()
                    update_item(user_featued_media)

            # user_experties_background
            user_experties_background= Experties_background.query.filter_by(user_id=current_user.id,deleted_at=None).all()
            if user_experties_background:
                for expert in user_experties_background:
                    expert.deleted_at = datetime.datetime.now()
                    update_item(user_experties_background)

            # user_customer_testimonials
            user_customer_testimonials = CustomerTestimonials.query.filter_by(user_id=current_user.id,deleted_at=None).all()
            if user_customer_testimonials:
                for testmonial in user_customer_testimonials:
                    testmonial.deleted_at = datetime.datetime.now()
                    update_item(user_customer_testimonials)

            # user contact me
            user_contact_me=ContactMe.query.filter(or_(ContactMe.from_user_id == current_user.id,
                                                       ContactMe.to_user_id == current_user.id),
                                                   Contact.deleted_at == None).all()
            if user_contact_me:
                for contact_me in user_contact_me:
                    contact_me.deleted_at = datetime.datetime.now()
                    update_item(user_contact_me)

            # user comment_tagging
            user_comment_tagging = CommentTagging.query.filter_by(user_id=current_user.id,deleted_at=None).all()
            if user_comment_tagging:
                for tagging in user_comment_tagging:
                    tagging.deleted_at = datetime.datetime.now()
                    update_item(user_comment_tagging)

            # user_notification
            user_notification = Notification.query.filter_by(user_id=current_user.id,deleted_at=None).all()
            if user_notification:
                for notify in user_notification:
                    notify.deleted_at = datetime.datetime.now()
                    update_item(user_notification)

            # user bettings
            user_bettings = UserBettings.query.filter_by(user_id=current_user.id, deleted_at=None).all()
            if user_bettings:
                for betting in user_bettings:
                    betting.deleted_at = datetime.datetime.now()
                    update_item(user_bettings)

            # user betting post
            betting_post = BettingPost.query.filter_by(user_id=current_user.id, deleted_at=None).all()
            if betting_post:
                for post in betting_post:
                    post.deleted_at = datetime.datetime.now()
                    update_item(betting_post)
            return success('SUCCESS', meta={'message': 'Deleted account successfully'})
        else:
            return success('SUCCESS', meta={'message': 'Invalid membership status'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid user'})


def admin_delete_account(current_user, data):
    user = data.get('user_id', None)
    exist_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if exist_user:
        if user:
            status_exist = Membership.query.filter_by(user_id=user, membership_status='active',
                                                      deleted_at=None).first()
            user_exist = Users.query.filter_by(id=user, deleted_at=None,user_deleted_at=None).first()
            if status_exist and user_exist:
                status_exist.membership_status = 'inactive'
                update_item(status_exist)
                user_exist.deleted_at = datetime.datetime.now()
                update_item(user_exist)

                # delete posts
                user_posts = Post.query.filter_by(user_id=user, deleted_at=None).all()
                if user_posts:
                    for item in user_posts:
                        item.deleted_at = datetime.datetime.now()
                        update_item(user_posts)

                # delete hall_of_fame
                user_hall_of_fame = Hall_of_fame.query.filter_by(user_id=user, deleted_at=None).all()
                if user_hall_of_fame:
                    for item in user_hall_of_fame:
                        item.deleted_at = datetime.datetime.now()
                        update_item(user_hall_of_fame)

                # delete sports
                user_sports = Sport_level.query.filter_by(user_id=user, deleted_at=None).all()
                if user_sports:
                    for item in user_sports:
                        item.deleted_at = datetime.datetime.now()
                        update_item(user_sports)

                # delete friends and followers
                user_contact = Contact.query.filter(or_(Contact.contact_id == user,
                                                        Contact.user_id == user),
                                                    Contact.deleted_at == None).all()
                if user_contact:
                    for item in user_contact:
                        item.deleted_at = datetime.datetime.now()
                        update_item(user_contact)

                # user groups
                user_groups = GroupMembers.query.filter_by(user_id=user, status='active',
                                                           deleted_at=None).all()
                if user_groups:
                    for item in user_groups:
                        if item.type == 'admin':
                            check_admin_id = Group.query.filter_by(id=item.group_id, user_id=user,
                                                                   deleted_at=None).first()
                            if check_admin_id:
                                check_existing_admin = GroupMembers.query.filter(GroupMembers.group_id == item.group_id,
                                                                                 GroupMembers.type == 'admin',
                                                                                 GroupMembers.user_id != user,
                                                                                 GroupMembers.status == 'active',
                                                                                 GroupMembers.deleted_at == None).first()
                                # if no other admin exist
                                if check_existing_admin is None:
                                    sorted_list = GroupMembers.query.filter(GroupMembers.group_id == item.group_id,
                                                                            GroupMembers.type == 'user',
                                                                            GroupMembers.status == 'active',
                                                                            GroupMembers.user_id != user,
                                                                            GroupMembers.deleted_at == None) \
                                        .order_by(GroupMembers.created_at)
                                    if list(sorted_list):
                                        member_data = list(sorted_list)[0]
                                        check_admin_id.user_id = member_data.user_id
                                        db.session.commit()

                                        make_admin = GroupMembers.query.filter_by(user_id=member_data.user_id,
                                                                                  group_id=item.group_id,
                                                                                  status='active').first()
                                        if make_admin:
                                            make_admin.type = 'admin'
                                            update_item(make_admin)
                                    else:
                                        check_admin_id.deleted_at = datetime.datetime.now()
                                        update_item(check_admin_id)

                                else:
                                    # if there is another admin
                                    sorted_list = GroupMembers.query.filter(GroupMembers.group_id == item.group_id,
                                                                            GroupMembers.type == 'admin',
                                                                            GroupMembers.user_id != user,
                                                                            GroupMembers.deleted_at == None) \
                                        .order_by(GroupMembers.created_at)
                                    if list(sorted_list):
                                        member_data = list(sorted_list)[0]
                                        check_admin_id.user_id = member_data.user_id
                                        db.session.commit()
                        delete_group_member = GroupMembers.query.filter(GroupMembers.group_id == item.group_id,
                                                                        GroupMembers.user_id == user,
                                                                        GroupMembers.deleted_at == None).first()
                        if delete_group_member:
                            delete_group_member.deleted_at = datetime.datetime.now()
                            db.session.commit()

                # user fitness level
                user_fitness = Fitness_level.query.filter_by(user_id=user, deleted_at=None).all()
                if user_fitness:
                    for item in user_fitness:
                        item.deleted_at = datetime.datetime.now()
                        update_item(user_fitness)

                # user device
                user_device = UserDevice.query.filter_by(user_id=user, deleted_at=None).all()
                if user_device:
                    for item in user_device:
                        item.deleted_at = datetime.datetime.now()
                        update_item(user_device)

                # user media
                user_media = Media.query.filter_by(user_id=user, deleted_at=None).all()
                if user_media:
                    for item in user_media:
                        item.deleted_at = datetime.datetime.now()
                        update_item(user_media)

                # user programme
                user_programme = Programme.query.filter_by(user_id=user, deleted_at=None).all()
                if user_programme:
                    for item in user_programme:
                        item.deleted_at = datetime.datetime.now()
                        update_item(user_programme)

                # user_profile_visibility
                user_profile_visibility = ProfileVisibility.query.filter_by(user_id=user,
                                                                            deleted_at=None).all()
                if user_profile_visibility:
                    for item in user_profile_visibility:
                        item.deleted_at = datetime.datetime.now()
                        update_item(user_profile_visibility)

                # user_post_react
                user_post_react = PostReact.query.filter_by(user_id=user, deleted_at=None).all()
                if user_post_react:
                    for item in user_post_react:
                        item.deleted_at = datetime.datetime.now()
                        update_item(user_post_react)

                # user post_custom_visibility
                user_post_custom_visibility = PostCustomVisibility.query.filter_by(user_id=user,
                                                                                   deleted_at=None).all()
                if user_post_custom_visibility:
                    for item in user_post_custom_visibility:
                        item.deleted_at = datetime.datetime.now()
                        update_item(user_post_custom_visibility)

                # user post_comment
                user_post_comment = Comment.query.filter_by(user_id=user, deleted_at=None).all()
                if user_post_comment:
                    for item in user_post_comment:
                        item.deleted_at = datetime.datetime.now()
                        update_item(user_post_comment)
                        parent_comment = Comment.query.filter_by(parent_id=item.id, deleted_at=None).all()
                        if parent_comment:
                            for comment in parent_comment:
                                comment.deleted_at = datetime.datetime.now()
                                update_item(parent_comment)

                # user health_profile
                user_health_profile = HealthProfile.query.filter_by(user_id=user, deleted_at=None).all()
                if user_health_profile:
                    for item in user_health_profile:
                        item.deleted_at = datetime.datetime.now()
                        update_item(user_health_profile)
                        health_report = HealthReport.query.filter_by(healthprofile_id=item.id, deleted_at=None).all()
                        if health_report:
                            for report in health_report:
                                report.deleted_at = datetime.datetime.now()
                                update_item(health_report)
                                health_para = HealthParameterValues.query.filter_by(healthreport_id=report.id,
                                                                                    deleted_at=None).all()
                                if health_para:
                                    for para in health_para:
                                        para.deleted_at = datetime.datetime.now()
                                        update_item(health_para)

                # user_featued_media
                user_featued_media = FeaturedMedia.query.filter_by(user_id=user, deleted_at=None).all()
                if user_featued_media:
                    for media in user_featued_media:
                        media.deleted_at = datetime.datetime.now()
                        update_item(user_featued_media)

                # user_experties_background
                user_experties_background = Experties_background.query.filter_by(user_id=user,
                                                                                 deleted_at=None).all()
                if user_experties_background:
                    for expert in user_experties_background:
                        expert.deleted_at = datetime.datetime.now()
                        update_item(user_experties_background)

                # user_customer_testimonials
                user_customer_testimonials = CustomerTestimonials.query.filter_by(user_id=user,
                                                                                  deleted_at=None).all()
                if user_customer_testimonials:
                    for testmonial in user_customer_testimonials:
                        testmonial.deleted_at = datetime.datetime.now()
                        update_item(user_customer_testimonials)

                # user contact me
                user_contact_me = ContactMe.query.filter(or_(ContactMe.from_user_id == user,
                                                             ContactMe.to_user_id == user),
                                                         Contact.deleted_at == None).all()
                if user_contact_me:
                    for contact_me in user_contact_me:
                        contact_me.deleted_at = datetime.datetime.now()
                        update_item(user_contact_me)

                # user comment_tagging
                user_comment_tagging = CommentTagging.query.filter_by(user_id=user, deleted_at=None).all()
                if user_comment_tagging:
                    for tagging in user_comment_tagging:
                        tagging.deleted_at = datetime.datetime.now()
                        update_item(user_comment_tagging)

                # user_notification
                user_notification = Notification.query.filter_by(user_id=user, deleted_at=None).all()
                if user_notification:
                    for notify in user_notification:
                        notify.deleted_at = datetime.datetime.now()
                        update_item(user_notification)
                return success('SUCCESS', meta={'message': 'Deleted account successfully'})
            else:
                return success('SUCCESS', meta={'message': 'Invalid user data'})
        else:
            return success('SUCCESS', meta={'message': 'User not Found'})

    else:
        return success('SUCCESS', meta={'message': 'Invalid user'})


def master_sport_lists(current_user,data):
    result = []
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        sport_id=data.get("sport_id")
        if sport_id:
             for ids in sport_id:
                 getSports=MasterSports.query.filter_by(id=ids,deleted_at=None).all()
                 if getSports:
                     for list in getSports:
                         master_sport_list={}
                         master_sport_list['id']=list.id
                         master_sport_list["name"]=list.name
                         master_sport_list['logo']=list.logo
                         master_sport_list['fields']=list.fields
                         result.append(master_sport_list)
                 else:
                     return success('SUCCESS', meta={'message': 'invalid sport_id'})
             return success('SUCCESS',result,meta={'message':'Master sport list'})

        else:
            return success('SUCCESS', meta={'message': 'enter valid sport_id'})
    else:
        return success('SUCCESS',meta={'message':'invalid user'})


def get_programs(current_user, data):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    result=[]
    program = Programme.query.filter_by(deleted_at=None).order_by(Programme.is_featured,Programme.is_featured==1,Programme.created_at.desc(),Programme.update_at.desc()).all()
    programs = Programme.query.filter_by(deleted_at=None).order_by(Programme.is_featured,Programme.is_featured==1,Programme.created_at.desc(),Programme.update_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False)
    programs = programs.items
    total_records = len(program)
    total_pages = total_records // per_page + 1
    if programs:
        for datas in programs:
            user_programme={}
            contacts = Contact.query.filter_by(user_id=current_user.id, contact_id=datas.user_id,deleted_at=None).first()
            if contacts:
                user_programme['is_following'] = contacts.is_following
                user_programme['friend_status'] = contacts.friend_status
            else:
                user_programme['is_following'] = False
                user_programme['friend_status'] = False
            user_programme['media'] = datas.media
            user_programme['category'] = datas.category
            user_programme['description'] = datas.description
            user_programme['is_featured'] = datas.is_featured
            user_programme['id'] = datas.id
            user_programme['title'] = datas.title
            user_programme['city'] = datas.city
            user_programme['user_info'] = get_user_profile_details(datas.user_id)
            result.append(user_programme)
        return success('SUCCESS', result,meta={"message": "Program List",
                                                        'page_info': {'current_page': page, 'limit': per_page,
                                                              'total_record': total_records,
                                                              'total_pages': total_pages}})


def search_expert_list(current_user, data):
    page, per_page = request.args.get('page', 1, type=int), request.args.get('limit', 10, type=int)
    name = data.get('name', None)
    city = data.get('city', None)
    category_id = data.get('category', None)

    offset = per_page * (page - 1)
    result = []

    if city and category_id:
        total_ids = []
        idds = []
        for data in category_id:
            all_expert_list__e = """SELECT * from experties_background where experties_in::text LIKE '%{data}%' AND 
            experties_background.city ILIKE '{city}' and experties_background.deleted_at is null""".format(
                data=data, city=city)
            all_expert_list__e = _query_execution(all_expert_list__e)
            if all_expert_list__e:
                for j in all_expert_list__e:
                    total_ids.append(j['user_id'])

            all_expert_list__p = """SELECT * FROM programme WHERE ( programme.master_programs_id='{data}' AND 
            programme.deleted_at is null AND programme.city ILIKE '{city}') """.format(data=data,city=city)
            all_expert_list__p = _query_execution(all_expert_list__p)
            if all_expert_list__p:
                for k in all_expert_list__p:
                    total_ids.append(k['user_id'])



            expert_list__e = """SELECT * from experties_background where experties_in::text LIKE '%{data}%' AND 
            experties_background.city ILIKE '{city}' and experties_background.deleted_at is null ORDER BY 
            experties_background.created_at DESC LIMIT {per_page} OFFSET {offset}""".format(
                data=data, city=city, per_page=per_page, offset=offset)
            expert_list__e = _query_execution(expert_list__e)
            if expert_list__e:
                for j in expert_list__e:
                    idds.append(j['user_id'])

            expert_list__p = """SELECT * FROM programme WHERE ( programme.master_programs_id='{data}' AND 
            programme.deleted_at is null AND programme.city ILIKE '{city}') ORDER BY programme.created_at DESC LIMIT 
            {per_page} OFFSET {offset}""".format(
                data=data,city=city, per_page=per_page, offset=offset)
            expert_list__p = _query_execution(expert_list__p)
            if expert_list__p:
                for k in expert_list__p:
                    idds.append(k['user_id'])


            if idds:
                for expert in idds:
                    if expert != current_user.id:
                        user_data = Users.query.filter_by(id=expert, deleted_at=None,
                                                          user_deleted_at=None).first()
                        contact = Contact.query.filter_by(contact_id=expert, user_id=current_user.id,
                                                          deleted_at=None).first()
                        expert_details = Experties_background.query.filter_by(user_id=expert,city=city,deleted_at=None).first()
                        expert_data = {}
                        if user_data:
                            expert_data['name'] = user_data.first_name
                            expert_data['id'] = user_data.id
                            expert_data['profile_image'] = user_data.profile_image

                        # if expert_details:
                        #     expert_data['description'] = expert_details.description
                        # else:
                        #     expert_data['description'] = None

                        items = {}
                        if expert_details:
                            for expert_ids in expert_details.experties_in:
                                if expert_ids == data:
                                    expert_data['description'] = expert_details.description
                                    category_name = db.session.query(MasterProgram).filter_by(id=expert_ids,
                                                                                              deleted_at=None).first()
                                    if category_name:
                                        items['category_id'] = category_name.id
                                        items['category_name'] = category_name.name
                                        expert_data['category'] = items
                                else:
                                    program_details = Programme.query.filter_by(user_id=expert,master_programs_id=data,
                                                                                          deleted_at=None).first()
                                    expert_data['description'] = program_details.description

                        if contact:
                            expert_data['is_following'] = contact.is_following
                            expert_data['friend_status'] = contact.friend_status
                        else:
                            expert_data['is_following'] = False
                            expert_data['friend_status'] = False
                        result.append(expert_data)
        total_records = len(total_ids)
        total_pages = total_records // per_page + 1
        return success('SUCCESS', result, meta={'message': 'Expert List',
                                                'page_info': {'current_page': page, 'limit': per_page,
                                                              'total_record': total_records,
                                                              'total_pages': total_pages}})

    elif name:
        search_string = '{}%'.format(name)
        get_users_data = Users.query.join(Membership, Membership.user_id == Users.id).filter(
            Users.first_name.ilike(search_string), Users.deleted_at == None,
                                                   Users.user_deleted_at == None, Users.business_account == True,
                                                   Membership.user_id == Users.id,
                                                   Membership.user_id != current_user.id,
                                                   Membership.membership_status == 'active',
                                                   Membership.deleted_at == None).all()
        users_data = Users.query.join(Membership, Membership.user_id == Users.id).filter(
            Users.first_name.ilike(search_string), Users.deleted_at == None,
                                                   Users.user_deleted_at == None, Users.business_account == True,
                                                   Membership.user_id == Users.id,
                                                   Membership.user_id != current_user.id,
                                                   Membership.membership_status == 'active',
                                                   Membership.deleted_at == None).paginate(
            page=page,
            per_page=per_page,
            error_out=False)

        users_data = users_data.items
        users_id = []
        experts_exist = []
        if users_data:
            for item in users_data:
                expert_list = Experties_background.query.filter_by(user_id=item.id, deleted_at=None).first()
                if expert_list:
                    experts_exist.append(str(item.id))
                else:
                    users_id.append(str(item.id))

            experts = experts_exist + users_id

            if experts:
                for expert in experts:
                    if expert != current_user.id:
                        user_data = Users.query.filter_by(id=expert, business_account='true', deleted_at=None,
                                                          user_deleted_at=None).first()
                        contact = Contact.query.filter_by(contact_id=expert, user_id=current_user.id,
                                                          deleted_at=None).first()
                        expert_details = Experties_background.query.filter_by(user_id=expert, deleted_at=None).first()
                        # if expert_details and user_data:
                        expert_data = {}
                        if user_data:
                            expert_data['name'] = user_data.first_name
                            expert_data['id'] = user_data.id
                            expert_data['profile_image'] = user_data.profile_image
                        if expert_details:
                            expert_data['description'] = expert_details.description
                            items = {}
                            for expert_ids in expert_details.experties_in:
                                category_name = db.session.query(MasterProgram).filter_by(id=expert_ids,
                                                                                          deleted_at=None).first()
                                if category_name:
                                    items['category_id'] = category_name.id
                                    items['category_name'] = category_name.name
                                expert_data['category'] = items
                        if contact:
                            expert_data['is_following'] = contact.is_following
                            if contact.friend_status == 'friends':
                                expert_data['friend_status'] = True
                            else:
                                expert_data['friend_status'] = False
                        else:
                            expert_data['is_following'] = False
                            expert_data['friend_status'] = False
                        result.append(expert_data)
                total_records = len(get_users_data)

                total_pages = total_records // per_page + 1
                return success('SUCCESS', result, meta={'message': 'Expert List',
                                                        'page_info': {'current_page': page, 'limit': per_page,
                                                                      'total_record': total_records,
                                                                      'total_pages': total_pages}})
        else:
            return success('SUCCESS', meta={'message': 'No data found'})

    elif category_id:
        for list_ids in category_id:
            get_expert_list = """SELECT * FROM experties_background WHERE (experties_in::text LIKE '%{list_ids}%') 
            AND (deleted_at is null)""".format(list_ids=list_ids)
            expert_lists = """SELECT * FROM experties_background WHERE (experties_in::text LIKE '%{list_ids}%') AND 
            (deleted_at is null) ORDER BY created_at DESC LIMIT {per_page} OFFSET {offset}""".format(list_ids=list_ids,
                                                                                                     per_page=per_page,
                                                                                                     offset=offset)
            experts = _query_execution(expert_lists)
            if experts:
                for expert in experts:
                    if expert['user_id'] != current_user.id:
                        user_ids = [d['id'] for d in result if 'id' in d]
                        if expert['user_id'] not in user_ids:
                            user_data = Users.query.filter_by(id=expert['user_id'], deleted_at=None,
                                                              user_deleted_at=None).first()
                            contact = Contact.query.filter_by(contact_id=expert['user_id'], user_id=current_user.id,
                                                              deleted_at=None).first()
                            expert_data = {}
                            if user_data:
                                expert_data['name'] = user_data.first_name
                                expert_data['id'] = user_data.id
                                expert_data['profile_image'] = user_data.profile_image
                            expert_data['description'] = expert['description']
                            items = {}
                            for expert_ids in expert['experties_in']:
                                if expert_ids == list_ids:
                                    category_name = db.session.query(MasterProgram).filter_by(id=expert_ids,
                                                                                              deleted_at=None).first()
                                    if category_name:
                                        items['category_id'] = category_name.id
                                        items['category_name'] = category_name.name
                                        expert_data['category'] = items

                            if contact:
                                expert_data['is_following'] = contact.is_following
                                expert_data['friend_status'] = contact.friend_status
                            else:
                                expert_data['is_following'] = False
                                expert_data['friend_status'] = False
                            result.append(expert_data)
        total_records = len(result)
        total_pages = total_records // per_page + 1
        return success('SUCCESS', result, meta={'message': 'Expert List',
                                                'page_info': {'current_page': page, 'limit': per_page,
                                                              'total_record': total_records,
                                                              'total_pages': total_pages}})
    else:
        return success('SUCCESS', meta={"Please search either by name or location"})




