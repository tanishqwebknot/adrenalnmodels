import re


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