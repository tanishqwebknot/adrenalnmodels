from api.Users.models import UserDevice, Device
from api.Users.services import generate_session_code
from common.connection import update_item, add_item


# def update_session(user_id, device_id=None, update_device=True):
#     session_code = generate_session_code()
#     if device_id:
#         user_devices = UserDevice.query.filter_by(user_id=user_id, device_id=device_id).all()
#         if not user_devices:
#             user_device = UserDevice(user_id=user_id, device_id=device_id, session_code=session_code, status='ACTIVE')
#             add_item(user_device)
#         if update_device:
#             devices = Device.query.filter_by(id=device_id).first()
#             devices.session_code = session_code
#             update_item(devices)
#     else:
#         user_devices = UserDevice.query.filter_by(user_id=user_id).all()
#     for user_device in user_devices:
#         user_device.session_code = session_code
#         update_item(user_device)
#     return session_code

#testing
def update_session(user_id, device_id=None, update_device=True):
    session_code = generate_session_code()
    if device_id:
        user_devices = UserDevice.query.filter_by(user_id=user_id, device_id=device_id).all()
        if not user_devices:
            user_device = UserDevice(user_id=user_id, device_id=device_id, session_code=session_code, status='ACTIVE')
            add_item(user_device)
        else:
            for user_device in user_devices:
                user_device.session_code = session_code
                update_item(user_device)
        if update_device:
            devices = Device.query.filter_by(id=device_id).first()
            devices.session_code = session_code
            update_item(devices)
    else:
        user_devices = UserDevice.query.filter_by(user_id=user_id).all()
    for user_device in user_devices:
        user_device.session_code = session_code
        update_item(user_device)
    return session_code
