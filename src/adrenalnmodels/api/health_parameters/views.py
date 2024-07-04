from flask import request, Blueprint

from api.health_parameters.services import add_health_profile, add_health_parameters, \
    add_health_report, update_health_profiles, \
    master_health_parameters, get_list_health_parameters, \
    get_list_profile, health_report_single_date, get_health_report_parameter, get_health_report_dates, \
    get_list_health_profile, health_report_table, update_health_records
from common.response import failure
from middleware.auth import token_required, validate_token

health_paramters_api = Blueprint('health_paramters_api', __name__, url_prefix='/healthparamters')


@health_paramters_api.route('/profile', methods=['POST'])
@validate_token(action='add_health_profile')
def add_health_profile_details(current_user):
    try:
        data = request.get_json()
        return add_health_profile(current_user, data)

    except Exception as e:
        return failure("Something went wrong.")


@health_paramters_api.route('/profile/<healthprofile_id>', methods=["PUT"])
@validate_token(action='update_health_details')
def update_health_profile(current_user, healthprofile_id):
    data = request.get_json()
    return update_health_profiles(current_user, data, healthprofile_id)



@health_paramters_api.route('/profile/<health_profile_id>', methods=['GET'])
@validate_token(action='get_health_profile_detail')
def get_health_parameters_details(current_user, health_profile_id):
    health_profile = get_list_health_profile(current_user ,health_profile_id)
    return health_profile


@health_paramters_api.route('/profile', methods=['GET'])
@validate_token(action='get_health_profile')
def get_list_health(current_user):
    return get_list_profile(current_user)


@health_paramters_api.route('/', methods=['GET'])
@validate_token(action='get_master_health_parameters')
def get_list_health_parameter(current_user):
    health_params = get_list_health_parameters(current_user)
    return health_params


@health_paramters_api.route('/values/<healthprofile_id>', methods=['POST'])
@validate_token(action='add_health_report')
def health_reports(current_user, healthprofile_id):
    return add_health_report(current_user, healthprofile_id)


@health_paramters_api.route('/custom', methods=['POST'])
@validate_token(action='add_custom_parameter')
def add_custom_parem(current_user):
    return add_health_parameters(current_user)


@health_paramters_api.route('/add_master_parameter', methods=['POST'])
@validate_token(action='add_master_parameter')
def add(current_user):
    return master_health_parameters(current_user)


@health_paramters_api.route('/health_report/<health_profile_id>', methods=['POST'])
@validate_token(action='health_report')
def health_report(current_user, health_profile_id):
    return health_report_single_date(current_user, health_profile_id)


@health_paramters_api.route('/health_report/parameter/<health_profile_id>', methods=['POST'])
@validate_token(action='health_report_parameter')
def multi_health_reports(current_user, health_profile_id):
    return get_health_report_parameter(current_user, health_profile_id)


@health_paramters_api.route('/health_report/table_report/<health_profile_id>', methods=['POST'])
@validate_token(action='health_report_parameter')
def multi_health_reports_table(current_user, health_profile_id):
    return health_report_table(current_user, health_profile_id)



@health_paramters_api.route('/reported_dates/<healthprofile_id>', methods=['GET'])
@validate_token(action='healthparamters_reported_dates')
def health_report_dates(current_user, healthprofile_id):
    health_profile = get_health_report_dates(current_user, healthprofile_id)
    return health_profile


@health_paramters_api.route('/values/<healthprofile_id>/<health_report_id>', methods=['PUT'])
@validate_token(action='update_health_report')
def update_records(current_user, healthprofile_id,health_report_id):
    return update_health_records(current_user, healthprofile_id,health_report_id)