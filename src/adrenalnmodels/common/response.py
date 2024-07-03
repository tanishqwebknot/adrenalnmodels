from flask import jsonify
from common.response_code import RESPONSE_CODE


def success(response_code=None, data=None, meta=None, page_info=None):
    if not response_code or response_code not in RESPONSE_CODE:
        if response_code and meta == None:
            meta = {'message': response_code}
        response_code = 'SUCCESS'

    response_obj = RESPONSE_CODE[response_code]
    http_status = 200
    if meta:
        if 'page_info' in meta:
            response_obj['page_info'] = meta['page_info']
        if 'http_status' in meta:
            response_obj['http_status'] = int(meta['http_status'])
        if 'code' in meta:
            response_obj['code'] = int(meta['code'])
        if 'message' in meta:
            response_obj['message'] = meta['message']
        if 'status' in meta:
            response_obj['status'] = meta['status']
    if 'http_status' in response_obj:
        http_status = response_obj['http_status']
        del (response_obj['http_status'])

    response = {
        "response": response_obj
    }
    if data:
        response['data'] = data
    resp = jsonify(response)
    resp.status_code = http_status
    resp.content_type = "application/json"
    return resp


def failure(response_code=None, data=None, meta=None):
    if not response_code or response_code not in RESPONSE_CODE:
        if response_code and meta == None:
            meta = {'message': response_code}
        response_code = 'FAILURE'
    response_obj = RESPONSE_CODE[response_code]
    http_status = 400
    if meta:
        if 'http_status' in meta:
            response_obj['http_status'] = int(meta['http_status'])
        if 'code' in meta:
            response_obj['code'] = int(meta['code'])
        if 'message' in meta:
            response_obj['message'] = meta['message']
        if 'status' in meta:
            response_obj['status'] = meta['status']
    if 'http_status' in response_obj:
        http_status = response_obj['http_status']
        del (response_obj['http_status'])

    response = {
        "response": response_obj
    }
    if data:
        response['data'] = data
    resp = jsonify(response)
    resp.status_code = http_status
    resp.content_type = "application/json"
    return resp