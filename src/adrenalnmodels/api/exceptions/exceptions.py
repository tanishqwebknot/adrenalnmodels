from enum import Enum

from api.exceptions.adernaline import AdernalineException


class Exception(AdernalineException):
    def getHTTPCode(self):
        return 400


class Error(Enum):
    SENDING_EMAIL_FAILED = {'code': 'SE001', 'msg': 'Sending Email Failed.'}
    OTP_VERIFY_FAILED = {'code': 'UOT01', 'msg': 'OTP verification failed'}
    USER_NOT_FOUND = {'code': 'US001', 'msg': 'User not found.'}
    USER_UPDATE_FAILED = {'code': 'US002', 'msg': 'User update failed.'}
    LOGIN_FAILED = {'code': 'US003', 'msg': 'Email or Password incorrect'}