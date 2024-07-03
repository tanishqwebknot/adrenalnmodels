RESPONSE_CODE = {
    'SUCCESS': {
        "http_status": 200,
        "code": 200,
        "message": "Success",
        "status": "success"
    },
    'FAILURE': {
        "http_status": 400,
        "code": 400,
        "message": "Failed",
        "status": "failure"
    },
    'EMPTY': {
        "http_status": 204,
        "code": 204,
        "message": "No Content",
        "status": "success"
    },
    'INVALID_ACCOUNT_CREDENTIALS': {
        "http_status": 400,
        "code": 10001,
        "message": "Invalid Account Credentials",
        "status": "failure"
    }
}