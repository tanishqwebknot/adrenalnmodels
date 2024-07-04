import csv
import datetime
import json
import os

import pytz
from flask import jsonify, request, Response, session
from sqlalchemy import or_, and_, func
from dateutil.tz import tzutc, tzlocal
from dateutil import parser
from sqlalchemy.dialects.postgresql import psycopg2

from api.Users.models import Users
from common.utils.json_utils import query_list_to_dict
from api.health_parameters.models import HealthProfile, MasterHealthParameters, HealthReport, \
    HealthParameterValues
from common.connection import add_item, update_item, delete_item
from common.response import success, failure
from flask.wrappers import Response
from flask import request
from app import db
from fpdf import FPDF
import psycopg2
import psycopg2.extras
import dateutil

from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME, CSV_BASE_AWS_URL

timeObj = datetime.datetime

# v2
def add_health_profile(current_user, data):
    name = data.get('name', None)
    health_parameters = data.get('health_parameters')
    if not name or not health_parameters:
        return success('SUCCESS',meta={'message': 'Please add name'})
    # health_parameters_data = json.dumps(health_parameters)
    health_parameters = HealthProfile(name=data.get('name', None), gender=data.get('gender', None),
                                      date_of_birth=data.get('date_of_birth', None),

                                      health_parameters=health_parameters, user_id=current_user.id)
    add_item(health_parameters)
    result = {}
    result['health_profile_id'] = health_parameters.id
    return success('SUCCESS', result, meta={'message': "health profile is created"})


#v2
def update_health_profiles(current_user, data, healthprofile_id):
    name = data.get('name', None)
    health_parameters = data.get('health_parameters')
    gender = data.get('gender', None)
    date_of_birth =data.get('date_of_birth', None)
    if not name:
        return success('SUCCESS',meta={'message': 'Please add name'})
    update_profile = HealthProfile.query.filter_by(user_id=current_user.id, id=healthprofile_id,deleted_at=None).first()
    if update_profile:
        parameters = []
        for data in update_profile.health_parameters:
            parameters.append(data)
        if health_parameters:
            for param in health_parameters:
                if param not in parameters:
                    parameters.append(param)
        update_profile.name = name
        update_profile.gender = gender
        update_profile.date_of_birth = date_of_birth
        update_profile.health_parameters = parameters
        update_item(update_profile)
        return success('SUCCESS', meta={'message': "health profile details are updated"})
    else:
        return success('SUCCESS', meta={"data is not there"})


def get_list_health_profile(current_user, health_profile_id):
    get_health_profiles = HealthProfile.query.filter_by(user_id=current_user.id, id=health_profile_id).all()
    result = []
    for get_health_profile in get_health_profiles:
        user_data, master_health = {}, []
        for data in get_health_profile.health_parameters:
            sub_response = {}
            master_data = MasterHealthParameters.query.filter_by(id=data['parameter_id']).first()
            sub_response["parameter_id"] = master_data.id
            sub_response["parameter_name"] = master_data.name
            sub_response["sorting_position"] =data["sorting_position"]
            master_health.append(sub_response)

        user_data['id'] = get_health_profile.id
        user_data['health_parameters'] = master_health  # get_health_profile.health_parameters
        user_data['name'] = get_health_profile.name
        user_data['gender'] = get_health_profile.gender
        user_data['date_of_birth'] = get_health_profile.date_of_birth.strftime("%Y-%m-%d %H:%M:%S")
        result.append(user_data)
    if len(result):
        return success('SUCCESS', result)
    else:
        return success('EMPTY', result)


def get_list_profile(current_user):
    get_health_profiles = HealthProfile.query.filter_by(user_id=current_user.id).order_by(
                HealthProfile.created_at.desc()).all()
    result = []
    for get_health_profile in get_health_profiles:
        user_data ,master_health= {},[]
        for data in get_health_profile.health_parameters:
            sub_response = {}
            master_data = MasterHealthParameters.query.filter_by(id=data['parameter_id']).first()
            sub_response["parameter_id"] = master_data.id
            sub_response["parameter_name"] = master_data.name
            sub_response["sorting_position"] = data["sorting_position"]
            sub_response["unit"] = master_data.unit
            # sub_response["sorting_position"] = master_data.sorting_position
            master_health.append(sub_response)

        user_data['id'] = get_health_profile.id
        user_data['health_parameters'] = master_health#get_health_profile.health_parameters
        # user_data['sorting_position'] = master_health#get_health_profile.health_parameters
        user_data['name'] = get_health_profile.name
        user_data['gender'] = get_health_profile.gender
        user_data['date_of_birth'] = get_health_profile.date_of_birth.strftime("%Y-%m-%d %H:%M:%S")

        result.append(user_data)
    if len(result):
        return success('SUCCESS', result)
    else:
        return success('EMPTY', result)


def get_health_report_dates(current_user, healthprofile_id):
    health_param = HealthProfile.query.filter_by(id=healthprofile_id, user_id=current_user.id).first()
    result = {}
    if health_param:
        get_health_profile_date = HealthReport.query.filter_by(healthprofile_id=healthprofile_id).order_by(HealthReport.report_date.desc()).all()
        for data in get_health_profile_date:
            if data.report_date:
                reportDate = data.report_date
                if reportDate.strftime("%Y%m%d") in result:
                    report_data = result[reportDate.strftime("%Y%m%d")]
                    report_data['report_count'] = report_data['report_count'] + 1
                    result[reportDate.strftime("%Y%m%d")] = report_data
                else:
                    result[reportDate.strftime("%Y%m%d")] = {}
                    result[reportDate.strftime("%Y%m%d")]["report_date"] = reportDate.strftime("%Y-%m-%d %H:%M:%S+00")
                    result[reportDate.strftime("%Y%m%d")]["report_count"] = 1
        return success('SUCCESS', list(result.values()),meta={'message':'Health Report'})
    else:
        return success('SUCCESS',meta={'message':'No Data Found'})


def get_list_health_parameters(current_user):
    list_health_parameters = db.session.query(MasterHealthParameters).all()
    result = []
    # for data in list_health_parameters.all():
    for data in list_health_parameters:
        user_data = {}
        user_data['parameter_id'] = data.id
        user_data['name'] = data.name
        user_data['sorting_position'] = data.sorting_position
        user_data['unit'] = data.unit
        result.append(user_data)
    sorting = sorted(result, key=lambda x: x.get('sorting_position') or -1)
    return success('SUCCESS', sorting,meta={'message':'Healthparameters'})


#v2
def add_health_report(current_user, healthprofile_id):
    data = request.get_json()
    report = data.get('image', None)
    health_parameters=data.get('health_parameters',None)
    report_date=data.get('report_date',None)
    if not health_parameters or not report_date:
        return success('SUCCESS', meta={'message': 'Invalid Data'})
    health_profile = HealthProfile.query.filter_by(user_id=current_user.id, id=healthprofile_id).first()
    if health_profile:
        health_profile_parameters = health_profile.health_parameters
        existing_parameters = []
        if health_profile_parameters:
            for data in health_profile_parameters:
                existing_parameters.append(data['parameter_id'])
        #add health report
        health_report = HealthReport(healthprofile_id=healthprofile_id,
                                     report_date=report_date,
                                     report=report)
        add_item(health_report)
        for health_parameter in health_parameters:
            health_parem = MasterHealthParameters.query.filter_by(
                id=health_parameter['parameter_id']).first()
            if health_parameter['parameter_id'] not in existing_parameters:
                delete_item(health_report)
                return success('SUCCESS', meta={'message': 'Invalid parameter'})
            if health_parem:
                health_parem_value = HealthParameterValues(healthreport_id=health_report.id,
                                                           healthparameters_id=health_parem.id,
                                                           value=health_parameter['value'])

                add_item(health_parem_value)
            else:
                delete_item(health_report)
                return success('SUCCESS', {'message': "Invalid Parameters"})
        return success('SUCCESS', {'message': "Parameters added successfully"})

    else:
        return success('SUCCESS', {'message': "health profile not found"})



def add_health_parameters(current_user):
    data = request.json
    if data :
        name = data.get('name')
        for elem in name:
            if name.count(elem) > 1:
                return failure('Add Unique parameters')
            else:
                results = []
                for custom in name:
                    existing_parameters = MasterHealthParameters.query.filter_by(name=custom, user_id=current_user.id).first()
                    if existing_parameters:
                        return failure("Add unique parameter")
                    else:
                        health_parameters = MasterHealthParameters(name=custom, user_id=current_user.id)
                        add_item(health_parameters)
                        hparam={}
                        hparam['parameter_name'] =health_parameters.name
                        hparam['parameter_id'] =health_parameters.id
                        results.append(hparam)
                    return success('SUCCESS', results ,meta={'message':'Custom Parameters Added Successfully'})


def master_health_parameters(current_user):
    data = request.json
    name = data.get('name')
    average_range_start = data.get('average_range_start', None)
    average_range_end = data.get('average_range_end', None)
    good_range_start = data.get('good_range_start', None)
    good_range_end = data.get('good_range_end', None)
    unit = data.get('unit')
    health_parameters = MasterHealthParameters(name=name, average_range_start=average_range_start,
                                               average_range_end=average_range_end, good_range_start=good_range_start,
                                               good_range_end=good_range_end,
                                               unit=unit, user_id=current_user.id)
    add_item(health_parameters)
    return success('SUCCESS', meta={'message': 'added health_parameters details successfully'})


def health_report_single_date(current_user, health_profile_id):
    data = request.get_json()
    if data.get('report_date', None):
        from_date = parser.parse(data.get('report_date'))
        to_date = from_date + datetime.timedelta(days=1)
        utc_from_date = from_date.astimezone(pytz.utc)
        utc_to_date = to_date.astimezone(pytz.utc)
        user_health_profile = db.session.query(HealthProfile).filter_by(user_id=current_user.id,
                                                                        id=health_profile_id).first()
        master_health_param = {}
        if user_health_profile:
            health_parameter_list, health_report_id_list = {}, []
            for data in user_health_profile.health_parameters:
                master_data = db.session.query(MasterHealthParameters).filter_by(id=data["parameter_id"]).first()
                if master_data:
                    health_parameter_list[data["parameter_id"]] = master_data
                    master_health_param[str(master_data.id)] = master_data.name

            health_reports = db.session.query(HealthReport).filter(
                HealthReport.healthprofile_id == user_health_profile.id, utc_from_date <= HealthReport.report_date,
                utc_to_date > HealthReport.report_date).order_by(
HealthReport.created_at.desc()).all()
            results = {}
            for health_report in health_reports:
                results[str(health_report.id)] = {
                    "health_report_id": health_report.id,
                    "report_date": health_report.report_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "report": health_report.report,
                    "values": []
                }
                health_parameter_values = db.session.query(HealthParameterValues).filter(
                    HealthParameterValues.healthreport_id == health_report.id).all()
                for table_value in health_parameter_values:
                    sub_response = {}
                    param_name = master_health_param.get(str(table_value.healthparameters_id))
                    master_data = health_parameter_list[str(table_value.healthparameters_id)]
                    result = calculate_result(master_data, table_value.value)
                    sub_response["parameter_id"] = table_value.healthparameters_id
                    sub_response["parameter_name"] = param_name
                    sub_response["value"] = table_value.value
                    sub_response["units"] = master_data.unit
                    sub_response["result"] = result
                    results[str(health_report.id)]["values"].append(sub_response)

            return success('SUCCESS', list(results.values()))
        return success("SUCCESS",meta={'check your date'})

    else:
        return success("SUCCESS",meta={"report time missing"})


def get_health_report_parameter(current_user, health_profile_id):
    data = request.get_json()
    exist_user = Users.query.filter_by(id=current_user.id,user_deleted_at=None,deleted_at=None).first()
    if exist_user:
        from_date = parser.parse(data.get('from_date'))
        to_date = parser.parse(data.get('to_date'))
        if (from_date < to_date):
            number_of_days = (to_date - from_date)
            number_of_days = number_of_days.days
            health_parameters = data['health_parameters']
            month_list = {1: "JANUARY",
                          2: "FEBRAURY",
                          3: "MARCH",
                          4: "APRIL",
                          5: "MAY",
                          6: "JUNE",
                          7: "JULY",
                          8: "AUGUST",
                          9: "SEPTEMBER",
                          10: "OCTOBER",
                          11: "NOVEMBER",
                          12: "DECEMBER"
                          }
            is_health_profile = db.session.query(HealthProfile).filter_by(user_id=current_user.id, id=health_profile_id,
                                                                          deleted_at=None).first()
            if is_health_profile:
                if number_of_days < 7:
                    result = []
                    for health_parameter in health_parameters:
                        date_of_entry = {}
                        date_count = {}
                        values = []
                        health_reports = db.session.query(HealthReport).filter(
                            and_(func.date(HealthReport.report_date) >= from_date),
                            func.date(HealthReport.report_date) <= to_date).filter(
                            HealthReport.healthprofile_id == health_profile_id,
                            HealthReport.deleted_at == None).all()
                        # health_reports = db.session.query(HealthReport).filter(
                        #     HealthReport.healthprofile_id == health_profile_id, HealthReport.report_date >= utc_from_date,
                        #     HealthReport.report_date < utc_to_date, HealthReport.deleted_at == None).all()
                        if health_reports is not None:
                            for reports in health_reports:
                                health_parameter_values = db.session.query(HealthParameterValues).filter(
                                    HealthParameterValues.healthreport_id == reports.id,
                                    HealthParameterValues.healthparameters_id == health_parameter,
                                    HealthParameterValues.deleted_at == None).first()
                                if health_parameter_values:
                                    parameter_list = {}
                                    count=HealthReport.query.filter_by(healthprofile_id=health_profile_id,report_date=reports.report_date,deleted_at=None).count()
                                    week_no, month = day_number(reports.report_date,count)
                                    month_day = (reports.report_date).day
                                    key = month_list[month][:3] + '_' + "DAY" + str(month_day)
                                    if key not in date_of_entry:
                                        date_of_entry[key] = [int(float(health_parameter_values.value))]
                                    else:
                                        date_of_entry[key].append(int(float(health_parameter_values.value)))
                        for day, value in date_of_entry.items():
                            total = sum(value) / len(value)
                            details = {}
                            details['key'] = day
                            details['value'] = total
                            values.append(details)

                        values = sorted(values, key=lambda x: x['key'].split('_DAY'))
                        parameter = MasterHealthParameters.query.filter_by(id=health_parameter, deleted_at=None).first()
                        if parameter:
                            final_data = {}
                            final_data['parameter_id'] = health_parameter
                            final_data['parameter_unit'] = parameter.unit
                            final_data['parameter_name'] = parameter.name
                            final_data['type'] = "days"
                            final_data['values'] = values
                            result.append(final_data)
                    if data["csv_required"]:
                        status = generate_csv(result, current_user.id)
                        if status:
                            return success("Success", meta={"message": "File is sent to the user register mail"})
                        return success('SUCCESS', meta={'failed to send email'})
                    return success("Success", result)

                elif number_of_days > 7 and number_of_days <= 31:
                    result = []
                    for health_parameter in health_parameters:
                        date_of_entry = {}
                        date_count = {}
                        values = []
                        health_reports = db.session.query(HealthReport).filter(
                            and_(func.date(HealthReport.report_date) >= from_date),
                            func.date(HealthReport.report_date) <= to_date).filter(
                            HealthReport.healthprofile_id == health_profile_id,
                            HealthReport.deleted_at == None).all()
                        if health_reports is not None:
                            for reports in health_reports:
                                health_parameter_values = db.session.query(HealthParameterValues).filter(
                                    HealthParameterValues.healthreport_id == reports.id,
                                    HealthParameterValues.healthparameters_id == health_parameter,HealthParameterValues.deleted_at==None).first()
                                if health_parameter_values:
                                    parameter_list = {}
                                    week_no, month = get_week_number(reports.report_date)
                                    key = month_list[month][:3] + "_WEEK" + str(week_no)
                                    if key not in date_of_entry:
                                        date_of_entry[key] = [int(float(health_parameter_values.value))]
                                    else:
                                        date_of_entry[key].append(int(float(health_parameter_values.value)))
                        for week, value in date_of_entry.items():
                            total = sum(value) / len(value)
                            details = {}
                            details['key'] = week
                            details['value'] = total
                            values.append(details)
                        values = sorted(values, key=lambda x: x['key'].split('_WEEK'))
                        parameter = MasterHealthParameters.query.filter_by(id=health_parameter,deleted_at=None).first()
                        if parameter:
                            final_data = {}
                            final_data['parameter_id'] = health_parameter
                            final_data['parameter_unit'] = parameter.unit
                            final_data['parameter_name'] = parameter.name
                            final_data['type'] = "weekly"
                            final_data['values'] = values
                            result.append(final_data)

                    if data["csv_required"]:
                        status = generate_csv(result, current_user.id)
                        if status:
                            return success("Success", {"message": "File is sent to the user"})
                        return failure('FAILURE', meta={'message': 'failed to send email'})
                    return success("Success", result)
                    # return success("Success", result)

                else:
                    result = []
                    for health_parameter in health_parameters:
                        date_of_entry = {}
                        date_count = {}
                        values = []
                        health_reports = db.session.query(HealthReport).filter(
                            and_(func.date(HealthReport.report_date) >= from_date),
                            func.date(HealthReport.report_date) <= to_date).filter(
                            HealthReport.healthprofile_id == health_profile_id,
                            HealthReport.deleted_at == None, ).all()
                        if health_reports is not None:
                            for reports in health_reports:
                                health_parameter_values = db.session.query(HealthParameterValues).filter(
                                    HealthParameterValues.healthreport_id == reports.id,
                                    HealthParameterValues.healthparameters_id == health_parameter,HealthParameterValues.deleted_at==None).first()
                                if health_parameter_values:
                                    month_no = reports.report_date.month
                                    # month = month_list[month_no]+ '_' + str(month_no)
                                    month = month_list[month_no]
                                    if month not in date_of_entry:
                                        date_of_entry[month] = [int(float(health_parameter_values.value))]
                                    else:
                                        date_of_entry[month].append(int(float(health_parameter_values.value)))
                        for month, value in date_of_entry.items():
                            from datetime import datetime
                            mnum = datetime.strptime(month, '%B').month

                            month_total = sum(value) / len(value)
                            details = {}
                            details['key'] = month[:3]
                            details['no'] = mnum
                            details['value'] = month_total
                            values.append(details)
                        values = sorted(values, key=lambda x: x['no'])
                        parameter = MasterHealthParameters.query.filter_by(id=health_parameter,deleted_at=None).first()
                        if parameter:
                            final_data = {}
                            final_data['parameter_id'] = health_parameter
                            final_data['parameter_unit'] = parameter.unit
                            final_data['parameter_name'] = parameter.name
                            final_data['type'] = "monthly"
                            final_data['values'] = values
                            result.append(final_data)

                        # check if user selected export file option (key - csv_required - True)
                    if data["csv_required"]:
                        status = generate_csv(result, current_user.id)
                        if status:
                            return success("Success", {"message": "File is sent to the user"})
                        return failure('FAILURE', meta={'message': 'failed to send email'})
                    return success("Success", result)
            else:
                return failure('FAILURE', meta={'message': 'No profile found'})
        else:
            return success('SUCCESS', meta={'message': 'Give correct date range'})
    else:
        return success('SUCCESS', meta={'message': 'Invalid user'})


def calculate_result(master_data, value):
    result = {}
    if str(master_data.good_range_start) and str(master_data.average_range_start):
        result["status"] = "BAD"
        result["range"] = str(master_data.average_range_start) + '-' + str(master_data.average_range_end)
        if str(master_data.good_range_start) < str(value) < str(master_data.good_range_end):
            result["status"] = "GOOD"
            result["range"] = str(master_data.good_range_start) + '-' + str(master_data.good_range_end)
        elif str(master_data.average_range_start) < str(value) < str(master_data.average_range_end):
            result["status"] = "AVERAGE"
            result["range"] = str(master_data.average_range_start) + '-' + str(master_data.average_range_end)
    else:
        result = {}
    return result


def health_report_table(current_user, health_profile_id):
    data = request.get_json()
    from_date = parser.parse(data.get('from_date'))
    to_date = parser.parse(data.get('to_date'))
    utc_from_date = from_date.astimezone(pytz.utc)
    utc_to_date = to_date.astimezone(pytz.utc)
    health_parameters = data['health_parameters']
    no_of_days = (utc_to_date - utc_from_date).days
    user_health_profile = db.session.query(HealthProfile).filter_by(user_id=current_user.id,id=health_profile_id).first()
    master_health_param = {}
    if user_health_profile:
        results = {}
        health_parameter_list, health_report_id_list, health_parem_masters = [], [], {}
        for health_parameter in health_parameters:
            master_data = db.session.query(MasterHealthParameters).filter_by(id=health_parameter).first()
            master_health_param[str(master_data.id)] = master_data.name
            if master_data:
                results[health_parameter] = {
                    "parameter_id": master_data.id,
                    "unit": master_data.unit,
                    "average": 0,
                    "values": []
                }
                health_parem_masters[health_parameter] = master_data
                health_parameter_list.append(health_parameter)
        health_reports = db.session.query(HealthReport).filter(
            HealthReport.healthprofile_id == user_health_profile.id, HealthReport.report_date >= utc_from_date,
            HealthReport.report_date < utc_to_date).all()
        total_count = 0
        unique_date = []
        for health_report in health_reports:
            if health_report.report_date not in unique_date:
                unique_date.append(health_report.report_date)
            average_value = 0
            health_parameter_values = db.session.query(HealthParameterValues).filter(
                HealthParameterValues.healthreport_id == health_report.id,
                HealthParameterValues.healthparameters_id.in_(health_parameter_list)).all()
            for table_value in health_parameter_values:
                total_count += int(table_value.value)
            average_value = total_count/len(unique_date)
            for table_value in health_parameter_values:
                sub_response = {}
                param_name = master_health_param.get(str(table_value.healthparameters_id))
                sub_response["date"] = health_report.report_date
                sub_response["month"] = health_report.report_date.strftime("%B")
                sub_response["parameter_name"] = param_name
                sub_response["value"] = table_value.value
                # sub_response["average"]=average_value
                results[str(table_value.healthparameters_id)]["average"] = average_value
                results[str(table_value.healthparameters_id)]["values"].append(sub_response)
        return success('SUCCESS', list(results.values()))
    return failure(' check your date')


def day_number(date,count):
    month_day = date.day
    week_day = (month_day - 1) // count
    return week_day, date.month


def get_week_number(date):
    # import datetime
    month_day = date.day
    week_day = (month_day - 1) // 7 + 1
    return week_day, date.month


def generate_csv(report_data, user_id):
    import csv
    import boto3
    header = ['Parameter']
    data = []
    for user_data in report_data:
        data.append(user_data["parameter_name"])
        for item in user_data['values']:
            for csv_header in item.values():
                if type(csv_header) == str:
                    header.append(csv_header)
                else:
                    data.append(csv_header)
    with open('health_parameter_report', 'w') as f:
        writer = csv.writer(f)
        # write the header
        writer.writerow(header)
        # write the data
        writer.writerows([data])
    from config import AWS_REGION_NAME
    s3_resource = boto3.resource(service_name='s3',
                                 region_name=AWS_REGION_NAME,
                                 aws_access_key_id=AWS_ACCESS_KEY_ID,
                                 aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                                 )
    local_file_path = 'health_parameter_report'
    s3_path = local_file_path + '_' + '.csv' # add start_date and end date
    # before uploading check if file already existing in bucket
    s3_resource.Object(AWS_BUCKET_NAME, s3_path).upload_file(Filename=local_file_path)  # make acl public
    s3_path = CSV_BASE_AWS_URL + s3_path
    os.remove('health_parameter_report')
    # send email to mail
    return True


def update_health_records(current_user, healthprofile_id,healthreport_id):
    data = request.get_json()
    health_profile = HealthProfile.query.filter_by(user_id=current_user.id, id=healthprofile_id).first()
    if health_profile:
        now = timeObj.utcnow()
        date_time = now.strftime("%y-%m-%d %H:%M:%S+00")
        if data.get('report_date', None):
            report_date = data.get('report_date')
        else:
            report_date = date_time
        report = data.get('image', None)
        health_parameters = data.get('health_parameters', None)
        health_report = HealthReport.query.filter_by(healthprofile_id=healthprofile_id,id=healthreport_id).first()
        if health_report:
            health_report.report_date = report_date
            health_report.report = report
            update_item(health_report)
        else:
            return success('SUCCESS',meta={'message':'Health Record Not Found'})
        if health_parameters:
            for health_parameter in health_parameters:
                health_parem = MasterHealthParameters.query.filter_by(
                    id=health_parameter['parameter_id']).first()
                if health_parem:
                    health_parem_value = HealthParameterValues.query.filter_by(healthreport_id=healthreport_id,healthparameters_id=health_parameter['parameter_id'],deleted_at=None).first()
                    if health_parem_value:
                        delete_item(health_parem_value)
                        add_health_parem_value = HealthParameterValues(healthreport_id=healthreport_id,
                                                                   healthparameters_id=health_parameter['parameter_id'],
                                                                   value=health_parameter['value'])
                        add_item(add_health_parem_value)
                    else:
                        add_health_parem_value = HealthParameterValues(healthreport_id=healthreport_id,
                                                                       healthparameters_id=health_parameter[
                                                                           'parameter_id'],
                                                                       value=health_parameter['value'])
                        add_item(add_health_parem_value)
                else:
                    return failure("invalid Healthparameter")
            return success('SUCCESS', {'message': "health record updated successfully"})
        else:
            return failure("invalid Healthparameter")
    else:
        return failure("invalid health profile")

