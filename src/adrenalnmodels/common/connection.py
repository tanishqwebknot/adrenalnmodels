import datetime
import json
from uuid import UUID
from sqlalchemy import text

from app import db


def add_item(obj):
    try:
        db.session.add(obj)
        db.session.commit()
        return obj
    except Exception as err:
        print("add_item", err)
        return None


def get_item(*args):
    try:
        result = db.session.query(*args)
        return result
    except Exception as err:
        print("add_item", err)
        return None


def update_item(obj):
    try:
        db.session.commit()
        return obj
    except Exception as err:
        print("update_item", err)
        return None


def delete_item(obj):
    try:
        db.session.delete(obj)
        db.session.commit()
        return obj
    except Exception as err:
        print("delete_item", err)
        return None


def raw_select(sql):
    try:
        result_proxy = raw_execution(sql)
        result = []
        for row in result_proxy:
            print(row.items())
            print(isinstance(row, datetime.datetime))
            row_as_dict = dict(row)
            date_ = row_as_dict.values()
            print(date_)
            result.append(row_as_dict)
        return result
    except Exception as err:
        print("raw_select", str(err))
        return []


def raw_execution(sql):
    try:
        result = db.engine.execute(text(sql).execution_options(autocommit=True))
        print(result)
        return result
    except Exception as err:
        print("raw_execution", str(err))
        return None


def get_count(sql):
    try:
        result = db.engine.execute(sql)
        one_row = result.fetchone()
        return one_row[0]
    except Exception as err:
        print("raw_execution", str(err))
        return None

class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            # if the obj is uuid, we simply return the value of uuid
            print('in uuidencode', obj)
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def _query_execution(sql, params=None):
    """
    Getting list from SQL query
    :param sql: sql string
    :param params (dict): the parameters to pass with the sql query
    :return: QuerySet list
    """
    try:
        print("INPUT QUERY ===>", sql)
        response = db.session.execute(
            text(sql).execution_options(autocommit=True), params=params
        )
        fields = response.keys()
        # offers = db.session.execute(
        #     text(sql).execution_options(autocommit=True), params=params
        # )
        # print("RESPONSE offers ===>", offers)
        table_fields = []
        for field in fields:
            table_fields.append(field)
        response_data = []
        for offer in response:
            response_row = {}
            count = 0
            for item in offer:
                response_row[table_fields[count]] = item
                count += 1
            response_data.append(response_row)
        return response_data
    except Exception as err:
        print("query_execution Exception %s", str(err))
        return None