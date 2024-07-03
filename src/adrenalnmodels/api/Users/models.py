import uuid

from sqlalchemy import Column, String, DateTime, Integer, Boolean, Enum, inspect, ForeignKey, VARCHAR, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import column_property

from app import db
from app.models import BaseModel


class Users(BaseModel):
    __tablename__ = 'users'
    id = Column(primary_key=True, default=uuid.uuid4)
    first_name = Column(String(50))
    last_name = Column(String(50))
    middle_name = Column(String(50))
    # name = column_property(first_name + "  " + last_name)
    nickname = Column(String(50))
    password = Column(String(255))
    gender = Column(Enum('Male', 'Female', 'Others', name='gender_type'))
    email = Column(String(255), nullable=False)
    phone = Column(String(10))
    phone_code = Column(Integer)
    date_of_birth = Column(DateTime)
    city = Column(String(50))
    about_me = Column(String(255))
    title = Column(String(255))
    can_follows = Column(Boolean,default=False)
    education_qualification = Column(String(255))
    college_name = Column(String(255))
    work_place = Column(String(255))
    marital_status = Column(String(255))
    business_account = Column(Boolean,default=False)
    profile_image = Column(JSON)
    user_deleted_at = Column(DateTime)


class Membership(BaseModel):
    __tablename__ = 'membership'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    password = Column(String(255))
    password_salt = Column(String(255))
    encrption_type = Column(String(50))
    password_update_on = Column(DateTime)
    last_login_attempts = Column(DateTime)
    login_attempts = Column(Integer)
    membership_type = Column(Enum('admin', 'general'))
    membership_status = Column(String(50))
    phone_verified = Column(Boolean)
    email_verified = Column(Boolean)
    role = Column(VARCHAR)
    last_feed_viewed = Column(DateTime)
    fcm_token = Column(Text)
    post_visibility = Column(Enum('all', 'friends', 'private', 'custom', 'group', 'followers', name='visibility_type'))


class UserProfile(BaseModel):
    __tablename__ = 'userprofile'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    education_quelification = Column(String(255))
    college_name = Column(String(255))
    work_place = Column(String(255))
    marital_status = Column(Enum('Single', 'married', 'Widowed', 'Divorced', name='STRINGS'))


class Verification(BaseModel):
    __tablename__ = "verification"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(255))
    code = Column(Integer)
    payload = Column(String(255))
    attempts = Column(Integer)


class Device(BaseModel):
    __serialize_attributes__ = (
        'id', 'fingerprint', 'device_name', 'device_type', "os", "os_version", "browser", "browser_version",
        "app_type", "app_version", "session_code", "status")

    __tablename__ = 'device'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    users_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    fingerprint = Column(String(225), unique=True)
    device_name = Column(String(100))
    device_type = Column(Enum('Mobile', 'Desktop', name='devices_type'))
    os = Column(String(20))
    os_version = Column(String(20))
    browser = Column(String(250), nullable=True)
    browser_version = Column(String(20), nullable=True)
    app_type = Column(String(20), nullable=True)
    app_version = Column(String(20), nullable=True)
    device_ip = Column(String(100))
    session_code = Column(String(10))
    status = Column(Enum('ACTIVE', 'INACTIVE', 'BLOCKED', name='devices_status'))

    def to_dict(self):
        res = {c: getattr(self, c) for c in inspect(self).attrs.keys()}
        return res


class UserDevice(BaseModel):
    __serialize_attributes__ = (
        "id", "user_id", "device_id", "session_code", "status")

    __tablename__ = 'user_device'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    # fingerprint = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    device_id = db.Column(UUID(as_uuid=True), db.ForeignKey('device.id'))
    # device_name = Column(String(255))
    session_code = Column(String(255))
    status = Column(Enum('ACTIVE', 'INACTIVE', 'BLOCKED', name='devices_status'))

    def to_dict(self):
        res = {c: getattr(self, c) for c in inspect(self).attrs.keys()}
        return res


class Actions(BaseModel):
    __tablename__ = "actions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(255))
    key = Column(VARCHAR(255))
    description = Column(VARCHAR(255))
    dependency = Column(JSON)
    group = Column(VARCHAR(255))
    sorting_position = Column(Integer)


class Roles(BaseModel):
    __tablename__ = "roles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(255))
    key = Column(VARCHAR(255))
    membership_type= Column(Enum('general', 'admin', name='devices_status'))


class RoleActions(BaseModel):
    __tablename__ = "role_actions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_key = Column(VARCHAR(255))
    action_key = Column(VARCHAR(255))
    status = Column(VARCHAR(255))
