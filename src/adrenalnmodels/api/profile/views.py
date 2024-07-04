import datetime

from flask import request, jsonify, Blueprint
from api.Users.models import Users, Membership
from api.contact.models import Contact
from api.profile.models import Hall_of_fame, Sport_level, CustomerTestimonials, Experties_background, FeaturedMedia, \
    Programme, ProfileVisibility
from api.profile.services import add_expert_details, sport_level, fitness_level, master_course, \
    add__hall_fame, Update_hallofame_details, get_hall_of_fame, get_primary_sport, get_secondry_sport, addProgramme, \
    addTestimonials, updateTestimonials, updateExpertise, \
    updateProgramme, get_expertise, get_testimonials, featured_media, add_contact_me, get_list_expert, \
    search_master_program_list, select_programme, get_all_programme, get_my_programme, search_expert_list, \
    master_programs, \
    get_list_master_programs, delete_hallOf_fame, sport_level_list, get_featured_media, featured_media_update, \
    update_sport_levels, get_fitness_level, delete_fitness_level, update_fitness_levels, delete_expertise_details, \
    add_expertise, get_master_sports, search_sport, master_course_list, add_visibility, program_suggesion, \
    profile_visibility_section, profile_terms_conditions, delete_account, user_delete_account, master_sport_lists, \
    get_programs
from common.connection import add_item, delete_item, update_item
from common.response import success, failure
from middleware.auth import validate_token
from api.exceptions.exceptions import Exception

profile_api = Blueprint('profile_api', __name__, url_prefix='/profile')


# HALL OF FAME APIS
@profile_api.route('/hall_of_fame', methods=['POST'])
@validate_token(action="add_hall_of_fame")
def hall_of_fame(current_user):
    data = request.json
    return add__hall_fame(current_user,data)


# get halloffame details api
@profile_api.route('/hall_of_fame/<user_id>', methods=['GET'])
@validate_token(action='get_hall_fame')
def get_hall_of_fame_details(current_user, user_id):
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    is_admin = Membership.query.filter_by(user_id=current_user.id, membership_status='active', membership_type='admin',
                                          deleted_at=None).first()
    if is_admin:
        return get_hall_of_fame(current_user, user_id)
    if existing_user:
        if str(current_user.id) == user_id:
            return get_hall_of_fame(current_user, user_id)
        valid_user = Users.query.filter_by(id=user_id, deleted_at=None,user_deleted_at=None).first()
        if valid_user:
            check_visibility = ProfileVisibility.query.filter_by(user_id=user_id, section='hall_of_fame',
                                                                 deleted_at=None).first()
            if check_visibility:
                if check_visibility.visibility == 'friends':
                    is_friends = Contact.query.filter_by(contact_id=current_user.id, user_id=user_id, deleted_at=None,
                                                         friend_status='friends').first()
                    if is_friends:
                        return get_hall_of_fame(current_user, user_id)
                    else:
                        return success('SUCCESS', meta={'message': 'Not allowed'})
                elif check_visibility.visibility == 'private':
                    return success('SUCCESS', meta={'message': 'Not allowed'})
                else:
                    return get_hall_of_fame(current_user, user_id)
            else:
                return get_hall_of_fame(current_user, user_id)
        else:
            return success('SUCCESS', meta={'message': 'User does not exist'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid User'})


# update halloffame details api
@profile_api.route('/hall_of_fame/<hall_of_fame_id>', methods=['PUT'])
@validate_token(action="update_hall_fame")
def update_hallfame(current_user, hall_of_fame_id):
    try:
        if request.method == 'PUT':
            data = request.get_json()
            return Update_hallofame_details(current_user, data, hall_of_fame_id)
    except Exception as e:
        return failure("Something went wrong.")


# hallOFFAME delete api
@profile_api.route('/hall_of_fame/<hall_of_fame_id>', methods=['DELETE'])
@validate_token(action="delete_hall_fame")
def delete_hall_Of_fame(current_user, hall_of_fame_id):
    return delete_hallOf_fame(current_user,hall_of_fame_id)


# FEATURED PROGRAMME
@profile_api.route('/programme', methods=['POST'])
@validate_token(action="add_programme")
def programme(current_user):
    try:
        data = request.get_json()
        return addProgramme(current_user, data)
    except Exception as e:
        return failure("Something went wrong.")


# get all programme
@profile_api.route('/programme', methods=['GET'])
@validate_token(action="get_programme")
def get_programmer(current_user):
    return get_all_programme(current_user)


#get my programme
@profile_api.route('/programme_list/<user_id>', methods=['GET'])
@validate_token(action="list_program_details")
def list_programs(current_user,user_id):
    return get_my_programme(current_user,user_id)


# update programme
@profile_api.route('/programme/<programme_id>', methods=['PUT'])
@validate_token(action="update_programme")
def update_programme(current_user, programme_id):
    # try:
    if request.method == 'PUT':
        data = request.get_json()
        existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
        if existing_user is not None:
            return updateProgramme(current_user, data, programme_id)
        else:
            return success("check details!", {})
    # except Exception as e:
    #     return failure("Something went wrong.")


#search program
@profile_api.route('/search_programme', methods=['GET'])
@validate_token(action='search_programme')
def search_programs(current_user):
    return search_master_program_list(current_user)


# Programme delete
@profile_api.route('/programme/<programme_id>', methods=['DELETE'])
@validate_token(action="delete_programme")
def delete_programme(current_user, programme_id):
    existing_user = Users.query.filter_by(id=current_user.id,deleted_at=None,user_deleted_at=None).first()
    if existing_user:
        my_programme = Programme.query.filter_by(id=programme_id, user_id=current_user.id, deleted_at=None).first()
        if my_programme:
            my_programme.deleted_at = datetime.datetime.now()
            update_item(my_programme)
            return success("SUCCESS", meta={'message': 'Programme Deleted Successfully'})
        else:
            return success("SUCCESS", meta={'message': 'Invalid programme'})
    else:
        return success("SUCCESS", meta={'message': 'Invalid user'})


@profile_api.route('/program_suggesion' , methods=['POST'])
@validate_token(action='program_suggesion')
def media_suggesion(current_user):
    data = request.get_json()
    return program_suggesion(current_user,data)


#search expert by programme api
@profile_api.route('/search_expert', methods=['POST'])
@validate_token(action='search_expert_details')
def search_expert(current_user ):
    try:
        data = request.get_json()
        return search_expert_list(current_user,data)
    except Exception as e:
        return failure("Something went wrong.")


#  FEATURED MEDIA
@profile_api.route('/featured_media', methods=['POST'])
@validate_token(action="add_featured_media")
def add_featured_media(current_user):
    try:
        data = request.get_json()
        return featured_media(current_user, data)

    except Exception as e:
        return failure("Something went wrong.")


# API to get featured_media list
@profile_api.route('/featured_media/<user_id>', methods=['GET'])
@validate_token(action="get_featured_media")
def featured_media_list(current_user,user_id):
    try:
        data = request.get_json()
        return get_featured_media(current_user,user_id)
    except Exception as e:
        return failure("Something went wrong.")


# update featured media
@profile_api.route('/featured_media/<media_id>', methods=['PUT'])
@validate_token(action="update_featured_media")
def update_featured_media(current_user, media_id):
    # try:
    if request.method == 'PUT':
        data = request.get_json()
        existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
        if existing_user is not None:
            return featured_media_update(current_user, data, media_id)
        else:
            return success("check details!", {})
    # except Exception as e:
    #     return failure("Something went wrong.")


# featured_media delete api
@profile_api.route('/featured_media/<media_id>', methods=['DELETE'])
@validate_token(action="delete_featured_media")
def delete_featured_media(current_user, media_id):
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None)
    if existing_user:
        my_featured_media = FeaturedMedia.query.filter_by(id=media_id,user_id=current_user.id,deleted_at=None).first()
        if my_featured_media:
            my_featured_media.deleted_at=datetime.datetime.now()
            update_item(my_featured_media)
            return success('SUCCESS',meta={'message':'Media deleted successfully!'})


# API for customer Testimonials
@profile_api.route('/testimonials', methods=['POST'])
@validate_token(action="add_testimonials")
def customer_testimonials(current_user):
    try:
        data = request.get_json()
        return addTestimonials(current_user, data)
    except Exception as e:
        return failure("Something went wrong.")


# customer_testimonials list
@profile_api.route('/testimonials/<user_id>', methods=['GET'])
@validate_token(action="get_testimonials")
def get_testprograme(current_user,user_id):
    return get_testimonials(current_user,user_id)


# update customer_testimonials Api
@profile_api.route('/testimonials/<testimonials_id>', methods=['PUT'])
@validate_token(action="update_testimonials")
def update_testimonials(current_user, testimonials_id):
    # try:
    if request.method == 'PUT':
        data = request.get_json()
        existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
        if existing_user is not None:
            return updateTestimonials(current_user, data, testimonials_id)
        else:
            return success("User Not Found", {})
    # except Exception as e:
    #     return failure("Something went wrong.")


# customer_testimonials delete api
@profile_api.route('/testimonials/<testimonials_id>', methods=['DELETE'])
@validate_token(action="delete_testimonials")
def delete_testimonials(current_user, testimonials_id):
    existing_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None)
    if existing_user:
        customer_testimonials = CustomerTestimonials.query.filter_by(id=testimonials_id,user_id=current_user.id,deleted_at=None).first()
        if customer_testimonials:
            customer_testimonials.deleted_at=datetime.datetime.now()
            update_item(customer_testimonials)
            return success("SUCCESS",meta={'message':'Deleted successfully!'})


# # to add primary/secondary sports
@profile_api.route('/sports', methods=['POST'])
@validate_token(action="add_sports")
def add_sports(current_user):
    data = request.json
    sport_id = data.get('sport_id')
    is_primary = data.get('is_primary')
    if not sport_id:
        return success('SUCCESS', meta={'message': 'Please provide required field'})
    if not is_primary:
        return success('SUCCESS', meta={'message': 'Invalid Data'})
    if is_primary == 'true':
        for sport in sport_id:
            is_sport = Sport_level.query.filter_by(sport_id=sport, user_id=current_user.id).first()
            if is_sport and is_sport.is_primary == False and is_sport.secondary_deleted_at == None:
                pass
            elif is_sport and is_sport.is_primary == True and is_sport.primary_deleted_at == None:
                pass
            elif is_sport and is_sport.is_primary == True and is_sport.primary_deleted_at != None:
                is_sport.primary_deleted_at = None
                update_item(is_sport)
            else:
                sport_details = Sport_level(is_primary=is_primary, sport_id=sport, user_id=current_user.id)
                add_item(sport_details)
        return success('SUCCESS', meta={'message': 'Added successfully'})
    elif is_primary == 'false':
        for sport in sport_id:
            is_sport = Sport_level.query.filter_by(sport_id=sport, user_id=current_user.id).first()
            if is_sport and is_sport.is_primary == True and is_sport.primary_deleted_at == None:
                pass
            elif is_sport and is_sport.is_primary == False and is_sport.secondary_deleted_at == None:
                pass
            elif is_sport and is_sport.is_primary == False and is_sport.secondary_deleted_at != None:
                is_sport.secondary_deleted_at = None
                update_item(is_sport)
            else:
                sport_details = Sport_level(is_primary=is_primary, sport_id=sport, user_id=current_user.id)
                add_item(sport_details)
        return success('SUCCESS', meta={'message': 'Added successfully'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid Data'})


# get primary sport
@profile_api.route('/primary_sports/<user_id>', methods=['GET'])
@validate_token(action="primary_sports")
def get_primary_sports(current_user, user_id):
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    is_admin = Membership.query.filter_by(user_id=current_user.id, membership_status='active', membership_type='admin',
                                          deleted_at=None).first()
    if is_admin:
        return get_primary_sport(current_user, user_id)
    if existing_user:
        if str(current_user.id) == user_id:
            return get_primary_sport(current_user, user_id)
        valid_user = Users.query.filter_by(id=user_id, deleted_at=None,user_deleted_at=None).first()
        if valid_user:
            check_visibility = ProfileVisibility.query.filter_by(user_id=user_id, section='primary_sport',
                                                                 deleted_at=None).first()
            if check_visibility:
                if check_visibility.visibility == 'friends':
                    is_friends = Contact.query.filter_by(contact_id=current_user.id, user_id=user_id, deleted_at=None,
                                                         friend_status='friends').first()
                    if is_friends:
                        return get_primary_sport(current_user, user_id)
                    else:
                        return success('SUCCESS', meta={'message': 'Not allowed'})
                elif check_visibility.visibility == 'private':
                    return success('SUCCESS', meta={'message': 'Not allowed'})
                else:
                    return get_primary_sport(current_user, user_id)
            else:
                return get_primary_sport(current_user, user_id)
        else:
            return success('SUCCESS', meta={'message': 'User does not exist'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid User'})


# get secondary sport
@profile_api.route('/secondary_sports/<user_id>', methods=['GET'])
@validate_token(action="secondry_sports")
def get_secondry_sports(current_user, user_id):
    try:
        existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
        is_admin = Membership.query.filter_by(user_id=current_user.id, membership_status='active', membership_type='admin',
                                              deleted_at=None).first()
        if is_admin:
            return get_secondry_sport(current_user, user_id)
        if existing_user:
            if str(current_user.id) == user_id:
                return get_secondry_sport(current_user, user_id)
            valid_user = Users.query.filter_by(id=user_id, deleted_at=None,user_deleted_at=None).first()
            if valid_user:
                check_visibility = ProfileVisibility.query.filter_by(user_id=user_id, section='secondary_sport',
                                                                     deleted_at=None).first()
                if check_visibility:
                    if check_visibility.visibility == 'friends':
                        is_friends = Contact.query.filter_by(contact_id=current_user.id, user_id=user_id, deleted_at=None,
                                                             friend_status='friends').first()
                        if is_friends:
                            return get_secondry_sport(current_user, user_id)
                        else:
                            return success('SUCCESS', meta={'message': 'Not allowed'})
                    elif check_visibility.visibility == 'private':
                        return success('SUCCESS', meta={'message': 'Not allowed'})
                    else:
                        return get_secondry_sport(current_user, user_id)
                else:
                    return get_secondry_sport(current_user, user_id)
            else:
                return success('SUCCESS', meta={'message': 'User does not exist'})
        else:
            return success('SUCCESS', meta={'message': 'Invalid User'})
    except Exception as e:
        return failure("Something went wrong.")


@profile_api.route('/sports/<sport_id>', methods=['DELETE'])
@validate_token(action="delete_sport_level")
def delete_sport(current_user, sport_id):
    user = Users.query.filter_by(id=current_user.id, user_deleted_at=None, deleted_at=None).first()
    if user:
        my_sports = Sport_level.query.filter_by(sport_id=sport_id, user_id=current_user.id, primary_deleted_at=None,
                                                secondary_deleted_at=None).first()
        if my_sports:
            if my_sports.is_primary == True and my_sports.primary_deleted_at == None:
                delete_item(my_sports)
                return success("SUCCESS", meta={'message': 'Deleted Successfully'})

            if my_sports.is_primary == False and my_sports.secondary_deleted_at == None:
                delete_item(my_sports)
                return success("SUCCESS", meta={'message': 'Deleted Successfully'})
        else:
            return success('SUCCESS', meta={'message': 'Not Found'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid User'})


# bulk delete primary/secondary sport
@profile_api.route('/delete_sports', methods=['POST'])
@validate_token(action="delete_sport_level")
def bulk_delete_sport(current_user):
    data = request.json
    sport_id = data.get('sport_id')
    if not sport_id:
        return success('SUCCESS', meta={'message': 'Please provied required field'})
    user = Users.query.filter_by(id=current_user.id,deleted_at=None,user_deleted_at=None).first()
    if user and sport_id:
        for sport in sport_id:
            my_sports = Sport_level.query.filter_by(sport_id=sport,user_id=current_user.id,primary_deleted_at=None,secondary_deleted_at=None).first()
            if my_sports:
                if my_sports.is_primary == True and my_sports.primary_deleted_at == None:
                    my_sports.primary_deleted_at=datetime.datetime.now()
                    if my_sports.playing_level != None:
                        my_sports.deleted_at=datetime.datetime.now()
                    update_item(my_sports)
                    # delete_item(my_sports)
                if my_sports.is_primary == False and my_sports.secondary_deleted_at == None:
                    my_sports.secondary_deleted_at=datetime.datetime.now()
                    update_item(my_sports)
        return success("SUCCESS",meta={'message':'Deleted Successfully'})
    else:
        return success('SUCCESS',meta={'message':'Not Found'})


# SPORT LEVEL API
# to add sports level
@profile_api.route('/sport_level', methods=['POST'])
@validate_token(action="add_sport_level")
def sport_levels(current_user):
    data=request.get_json()
    return sport_level(current_user,data)



@profile_api.route('/sport_level/<sport_level_id>', methods=['PUT'])
@validate_token(action="update_sport_level")
def update_sport_level(current_user, sport_level_id):
    data = request.get_json()
    return update_sport_levels(current_user, sport_level_id, data)


# to get list of sports level
@profile_api.route('/sport_level/<user_id>', methods=['GET'])
@validate_token(action="get_sport_level")
def get_sport_levels(current_user, user_id):
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    is_admin = Membership.query.filter_by(user_id=current_user.id, membership_status='active', membership_type='admin',
                                          deleted_at=None).first()
    if is_admin:
        return sport_level_list(current_user, user_id)
    if existing_user:
        if str(current_user.id) == user_id:
            return sport_level_list(current_user, user_id)
        valid_user = Users.query.filter_by(id=user_id, deleted_at=None,user_deleted_at=None).first()
        if valid_user:
            check_visibility = ProfileVisibility.query.filter_by(user_id=user_id, section='sport_level',
                                                                 deleted_at=None).first()
            if check_visibility:
                if check_visibility.visibility == 'friends':
                    is_friends = Contact.query.filter_by(contact_id=current_user.id, user_id=user_id, deleted_at=None,
                                                         friend_status='friends').first()
                    if is_friends:
                        return sport_level_list(current_user, user_id)
                    else:
                        return success('SUCCESS', meta={'message': 'Not allowed'})
                elif check_visibility.visibility == 'private':
                    return success('SUCCESS', meta={'message': 'Not allowed'})
                else:
                    return sport_level_list(current_user, user_id)
            else:
                return sport_level_list(current_user, user_id)
        else:
            return success('SUCCESS', meta={'message': 'User does not exist'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid User'})


@profile_api.route('/sport_level/<sport_id>', methods=['DELETE'])
@validate_token(action="delete_sport_level")
def delete_sport_level(current_user, sport_id):
    user = Users.query.filter_by(id=current_user.id, user_deleted_at=None, deleted_at=None).first()
    if user:
        my_sports = Sport_level.query.filter_by(id=sport_id, user_id=current_user.id, deleted_at=None).first()
        if my_sports:
            if my_sports.is_primary == True and my_sports.deleted_at == None:
                my_sports.deleted_at = datetime.datetime.now()
                update_item(my_sports)
                return success("SUCCESS", meta={'message': 'Deleted Successfully'})
        else:
            return success('SUCCESS', meta={'message': 'Not Found'})

# FITNESS LEVEL API
#add Fitness level
@profile_api.route('/fitness_level', methods=['POST'])
@validate_token(action="add_fitness_level")
def fitness_levels(current_user):
    return fitness_level(current_user)


# get fitness level
@profile_api.route('/fitness_level/<user_id>', methods=['GET'])
@validate_token(action="get_fitness_level")
def fitness_level_list(current_user, user_id):
    existing_user = Users.query.filter_by(id=current_user.id, deleted_at=None,user_deleted_at=None).first()
    is_admin = Membership.query.filter_by(user_id=current_user.id, membership_status='active', membership_type='admin',
                                          deleted_at=None).first()
    if is_admin:
        return get_fitness_level(current_user, user_id)
    if existing_user:
        if str(current_user.id) == user_id:
            return get_fitness_level(current_user, user_id)
        valid_user = Users.query.filter_by(id=user_id, deleted_at=None,user_deleted_at=None).first()
        if valid_user:
            check_visibility = ProfileVisibility.query.filter_by(user_id=user_id, section='fitness_level',
                                                                 deleted_at=None).first()
            if check_visibility:
                if check_visibility.visibility == 'friends':
                    is_friends = Contact.query.filter_by(contact_id=current_user.id, user_id=user_id, deleted_at=None,
                                                         friend_status='friends').first()
                    if is_friends:
                        return get_fitness_level(current_user, user_id)
                    else:
                        return success('SUCCESS', meta={'message': 'Not allowed'})
                elif check_visibility.visibility == 'private':
                    return success('SUCCESS', meta={'message': 'Not allowed'})
                else:
                    return get_fitness_level(current_user, user_id)
            else:
                return get_fitness_level(current_user, user_id)
        else:
            return success('SUCCESS', meta={'message': 'User does not exist'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid User'})


#update fitness level
@profile_api.route('/update_fitness_level/<course_id>', methods=['PUT'])
@validate_token(action="update_fitness_level")
def update_fitness(current_user, course_id):
    data = request.get_json()
    return update_fitness_levels(current_user, course_id, data)


# delete fitness level
@profile_api.route('/delete_fitness_level/<course_id>', methods=['DELETE'])
@validate_token(action="delete_fitness_level")
def delete_fitness_levels(current_user, course_id):
    return delete_fitness_level(current_user, course_id)


@profile_api.route('/master_course', methods=['POST'])
@validate_token(action="master_course")
def add_master_course(current_user):
    add_master_course = master_course(current_user)
    return add_master_course


# API to add contact me
@profile_api.route('/contact_me/<business_account_id>', methods=['POST'])
@validate_token(action="add_contact_me")
def contact_me(current_user,business_account_id):
    try:
        data = request.get_json()
        add_contact_me(current_user, data,business_account_id)
        return success("SUCCESS")
    except Exception as e:
        return failure("Something went wrong.")


# add expertise nd bg
@profile_api.route('/expertise', methods=['POST'])
@validate_token(action='add_expertise')
def expertise(current_user):
    data = request.get_json()
    return add_expertise(current_user,data)


# update expertise Api
@profile_api.route('/expertise/<expertise_id>', methods=['PUT'])
@validate_token(action="update_expertise")
def update_expertise(current_user, expertise_id):
    data = request.get_json()
    return updateExpertise(current_user, data, expertise_id)


# expertise delete api
@profile_api.route('/expertise/<experties_background_id>', methods=['DELETE'])
@validate_token(action="delete_experties")
def delete_expertise(current_user, experties_background_id):
    return delete_expertise_details(current_user, experties_background_id)


# get expertise nd bg list
@profile_api.route('/expertise/<user_id>', methods=['GET'])
@validate_token(action="get_expertise_details")
def get_expertise_background(current_user,user_id):
    return get_expertise(current_user,user_id)


@profile_api.route('/get_expert_list', methods=['GET'])
@validate_token(action="get_expert_list")
def list_expert(current_user):
    t_testimonials = get_list_expert(current_user)
    return t_testimonials


#select programdetails api
@profile_api.route('/select_programs', methods=['POST'])
@validate_token(action='select_programs')
def add_program_details(current_user):
    try:
        data = request.get_json()
        return select_programme(current_user , data)

    except Exception as e:
        return failure("Something went wrong.")


@profile_api.route('/add_expert_details', methods=['POST'])
@validate_token(action="add_expert_details")
def add_details(current_user):
    try:
        add = add_expert_details(current_user)
        return add
    except Exception as e:
        return failure("Something went wrong.")


#MASTER APIS
@profile_api.route('/master_program', methods=['POST'])
@validate_token(action='master_program')
def master_program(current_user ):
    add_master_programs=master_programs(current_user)
    return add_master_programs


@profile_api.route('/master_programs', methods=['GET'])
# @validate_token(action='get_master_programs')
def master():
    get_master=get_list_master_programs()
    return get_master


@profile_api.route('/master_sport', methods=['GET'])
# @validate_token(action='get_master_programs')
def master_sport():
    return get_master_sports()


# Master Sports Search
@profile_api.route('/search_sports', methods=['GET'])
@validate_token(action='search_sports')
def search_sports(current_user):
    return search_sport(current_user)


# master_course list
@profile_api.route('/adrenalin_master_course_list', methods=['GET'])
def get_master_course_list():
    return master_course_list()


# set profile visibility
@profile_api.route('/add_visibility', methods=['POST'])
@validate_token(action='set_visibility')
def user_set_visibility(current_user):
    data = request.get_json()
    return add_visibility(current_user, data)


@profile_api.route('/get_visibility', methods=['GET'])
@validate_token(action="profile_visibility")
def section_visibility(current_user):
    return profile_visibility_section(current_user)


@profile_api.route('/terms_conditions/<section>', methods=['GET'])
@validate_token(action="terms_conditions")
def terms_and_conditions(current_user,section):
    return profile_terms_conditions(current_user,section)


# delete account
@profile_api.route('/delete_account', methods=['POST'])
@validate_token(action='delete_account')
def delete_user_account(current_user):
    # return delete_account(current_user)
    return user_delete_account(current_user)



@profile_api.route('/get_master_sports', methods=['POST'])
@validate_token(action='get_master_sport_list')
def master_sport_list(current_user):
    data=request.json
    return master_sport_lists(current_user,data)

# feature programme list
@profile_api.route('/get_program_list' , methods=['GET'])
@validate_token(action='program_suggesion')
def get_program_list(current_user):
    try:
        data = request.get_json()
        return get_programs(current_user,data)
    except Exception as e:
        return failure("Something went wrong.")


