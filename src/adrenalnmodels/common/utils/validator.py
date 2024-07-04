import re
from xmlrpc.client import DateTime
from common.response import success, failure
from sqlalchemy.orm import  validates

def is_mobile_no(mobile_no):
    try:
        if re.match(r'[6789]\d{9}$', mobile_no):
            return True
        else:
            return False
    except Exception as err:
        return False


def is_email_id(email_id):
    try:
        if re.match(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', email_id, re.I):
            return True
        else:
            return False
    except Exception as err:
        return False


def is_valid_password(password):
    try:
        password = str(password)

        # todo rule to be added
        if not password:
            return False
        else:
            return True
    except Exception as err:
        return False

@validates('name')
def validate_name(self, key, name):
    if not name:
        raise AssertionError('No name provided')
    if len(name) < 5 or len(name) > 20:
        raise AssertionError('Username must be between 5 and 20 characters')
    return name


def validate_mobile_number(phone):
    if not phone:
        return True
    if len(phone) != 10:
        return False
        # return failure('Mobile number must be of 10 digits')
    return phone

# @validates('password')
def validate_password(password):
    if not password:
        raise AssertionError('Please enter password')

    if not re.match('\d.*[A-Z]|[A-Z].*\d', password):
        raise AssertionError('Password must contain 1 capital letter and 1 number')

    if len(password) < 8 or len(password) > 25:
        raise AssertionError('Password must be between 8 and 25 characters')
    return password


def validate_email(email):
    regex = r'^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,5})+$'
    if re.search(regex, email):
        return True
    else:
        return False

@validates('city')
def validate_city(self, key, city):
    if not city:
        raise AssertionError('Please enter city')
    return city

@validates('gender')
def validate_gender(self, key, gender):
    if not gender:
        raise AssertionError('Please enter gender')
    return gender

@validates('date_of_birth')
def validate_dob(self, key, date_of_birth):
    if not date_of_birth:
        raise AssertionError('Please enter your Date Of Birth')
    if date_of_birth != DateTime.strptime(date_of_birth, "%Y-%m-%d").strftime('%Y-%m-%d'):
        raise AssertionError('Data not Valid')
    return date_of_birth