from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from app import db
import re
import uuid
from datetime import datetime
from sqlalchemy import Column, String,DECIMAL, DateTime, Integer, Boolean, ForeignKey, Date, Enum, JSON, VARCHAR, TEXT,ARRAY,Float, Text, REAL, inspect, func
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from config import SQLALCHEMY_DATABASE_URI
from sqlalchemy import inspect

engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=True)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

def serialize(self):
    return {c: getattr(self, c) for c in inspect(self).attrs.keys()}

# Set your classes here.
class BaseModel(db.Model):
    __abstract__ = True
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    update_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), default=None)

    def _asdict(self):
        return serialize(self)

    def objects(*args):
        return db.session.query(*args)

class FitbitUsers(BaseModel):
     __tablename__ = 'fitbitusers'
     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
     access_token = Column(String(350))
     refresh_token = Column(String(350))
     scope = Column(ARRAY(String))
     expires_in = Column(Integer)
     register_at = Column(Date)
     deregister_at = Column(Date)
     fitbit_id = Column(String(100))
     user_id = Column(UUID(as_uuid=True), nullable=False,default=uuid.uuid4)
     expires_at=Column(DECIMAL(20,6))

class GarminUsers(BaseModel):
    __tablename__ = 'garminusers'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_token = Column(String(150))
    request_token_secret = Column(String(150))
    access_token = Column(String(150))
    access_token_secret = Column(String(150))
    verifier = Column(String(150))
    deregister_at = Column(Date)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    garmin_id = Column(UUID(as_uuid=True), nullable=False)

class GfitUsers(BaseModel):
    __tablename__ = 'gfitusers'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth_code = Column(String(255))
    access_token = Column(String(255))
    refresh_token = Column(String(255))
    activity_last_synced = Column(DateTime(timezone=True))
    refresh_token_exp = Column(Date)
    deregister_at = Column(Date)
    user_id = Column(UUID(as_uuid=True), nullable=False)

class Activity(BaseModel):
    __tablename__ = 'activity'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # access_token = Column(VARCHAR(150))
    # garmin_id = Column(UUID(as_uuid=True))
    summaryid = Column(VARCHAR(255))
    activityid = Column(VARCHAR(255))
    activityname = Column(VARCHAR(255))
    activitytype = Column(VARCHAR(255))
    description = Column(VARCHAR(255))
    location_data = Column(JSON)
    summary = Column(JSON)
    laps = Column(JSON)
    # garminusers_table_id = Column(UUID(as_uuid=True), ForeignKey('garminusers.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True))
    source = Column(VARCHAR(255))


class User_activity_mapping(BaseModel):
    __tablename__ = 'user_activity_mapping'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True))
    activity_table_id = Column(UUID(as_uuid=True))
    
class Group(BaseModel):
    __tablename__ = 'user_group'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_name = Column(String(255))
    description = Column(Text())
    sport_type = Column(String(255))
    city = Column(String(255))
    image = Column(JSON)
    topic = Column(VARCHAR(255))
    visibility = Column(Enum('all', 'friends', 'custom', 'group_members'))
    user_id = Column(UUID(as_uuid=True))
    sport_master_id = Column(UUID(as_uuid=True), ForeignKey('sport_master.id'), nullable=False)


class GroupMembers(BaseModel):
    __tablename__ = 'group_members'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    group_id = Column(UUID(as_uuid=True), ForeignKey('user_group.id'), nullable=False)
    type = Column(Enum('admin', 'user', name='group_type'))
    status = Column(Enum('active', 'inactive', 'invited', name='status_type'))


class SportMaster(BaseModel):
    __tablename__ = 'sport_master'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255))

class Post(BaseModel):
    __tablename__ = 'post'
    # __serialize_attributes__ = (
    #     'id', 'type', 'title', 'visibility', "user_id", "group_id", "meta_data", "location",
    #     "description", "expire_on")
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(Enum('regular', 'sports_activity', 'betting', 'repost','activity','betting_result','watch_activity','record_activity', name='post_type'))
    title = Column(VARCHAR(100))
    visibility = Column(Enum('admin','all', 'friends', 'private', 'custom', 'group', 'followers', name='visibility_type'))
    # group_id = Column(UUID(as_uuid=True) , default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey('user_group.id'), default=None)
    meta_data = Column(JSON)
    location = Column(JSON)
    description = Column(Text())
    expire_on = Column(DateTime)
    is_tag = Column(Boolean)
    promotion = Column(Boolean,default=False)
    share_link = Column(VARCHAR(255))
    status = Column(Enum('active', 'inactive', 'invited', name='status_type'),default='active')

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class PostViews(BaseModel):
    __tablename__ = 'post_views'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey('post.id'), default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), default=uuid.uuid4)


class MasterActivity(BaseModel):
    __tablename__ = 'master_activity'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(255))
    fields = Column(JSON)
    logo = Column(JSON)


class PostCustomVisibility(BaseModel):
    __tablename__ = 'post_custom_visibility'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tag = Column(Boolean)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey('post.id'), nullable=False)


class PostReact(BaseModel):
    __tablename__ = 'post_react'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(Enum('like', 'sad', 'happy', 'angry', 'love', name='post_react_type'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey('post.id'), nullable=False)
    is_liked = Column(Boolean)


class BettingPost(BaseModel):
    __tablename__ = 'betting_post'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    primary_team = Column(VARCHAR(255))
    secondary_team = Column(VARCHAR(255))
    betting_for = Column(VARCHAR(255))
    oods = Column(VARCHAR(255))
    results = Column(VARCHAR(255))
    betting_status = Column(VARCHAR(255))
    description = Column(VARCHAR(255))
    favour_of = Column(VARCHAR(255))
    expire_on = Column(DateTime)
    result_status = Column(VARCHAR(255))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey('post.id'), nullable=False)


class UserBettings(BaseModel):
    __tablename__ = 'user_bettings'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    betting_status = Column(VARCHAR(255))
    result_status = Column(VARCHAR(255))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey('post.id'), nullable=False)


class Post_comments(BaseModel):
    __tablename__ = 'post_comments'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_comments = Column(Text)
    parent_id = Column(UUID(as_uuid=True))
    users_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey('post.id'), nullable=False)


class Post_shares(BaseModel):
    __tablename__ = 'post_shares'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_users_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    users_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey('post.id'), nullable=False)


class Comment_interests(BaseModel):
    __tablename__ = 'comment_interests'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(Enum('Regular', 'Activity', 'Betting', name='comment_interests_typ'))
    users_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)


class MasterBettingItems(BaseModel):
    __tablename__ = 'master_betting_items'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(255))
    image = Column(JSON)


class AdminPost(BaseModel):
    __tablename__ = 'admin_post'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey('post.id'), nullable=False)
    is_priority = Column(Boolean)
    reviewer_status = Column(Boolean)
    publisher_status = Column(Boolean)
    reviewer_approved_at = Column(DateTime(timezone=True), default=None)
    publisher_approved_at = Column(DateTime(timezone=True), default=None)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    publisher_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    expiry_date = Column(Date)
    s_id = Column(REAL)
    promotion=Column(VARCHAR(50))


class UserPostStatus(BaseModel):
    __tablename__ = 'user_post_status'
    id = Column(UUID(as_uuid=True),primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey('post.id'),nullable=False)
    is_priority = Column(Boolean)
    is_approved = Column(Boolean)
    approved_at = Column(DateTime(timezone=True), default=None)
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class PublisherPost(BaseModel):
    __tablename__ = 'publisher_post'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(JSON)
    bucket = Column(JSON)
    is_priority = Column(Boolean)
    is_approved = Column(Boolean)
    approved_at = Column(DateTime(timezone=True), default=None)
    approved_by = Column(UUID(as_uuid=True),ForeignKey('users.id'), nullable=True)
#
# class PublisherPost(BaseModel):
#     __tablename__ = 'publisher_post'
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     post_id = Column(UUID(as_uuid=True), ForeignKey('post.id'), nullable=False)
#     bucket = Column(VARCHAR(100))
#     is_priority = Column(Boolean)
#     is_approved = Column(Boolean)
#     approved_at = Column(DateTime(timezone=True), default=None)
#     approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class AdminPostViews(BaseModel):
    __tablename__ = 'admin_post_views'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_post_id = Column(UUID(as_uuid=True), ForeignKey('admin_post.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)


class UserBucket(BaseModel):
    __tablename__ = 'user_bucket'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    bucket_key = Column(VARCHAR(255))
    is_primary = Column(Boolean)


class MasterBucket(BaseModel):
    __tablename__ = 'master_bucket'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255))
    key = Column(VARCHAR(255))
    category_type = Column(VARCHAR(255))


class PostBucketMapping(BaseModel):
    __tablename__ = 'post_bucket_mapping'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True),ForeignKey('post.id'), default=uuid.uuid4)
    key = Column(VARCHAR(255),ForeignKey('master_bucket.key'))
    type = Column(VARCHAR(255))
    category_value=Column(VARCHAR(255))


class ReportedPost(BaseModel):
    __tablename__ = 'reported_post'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey('post.id'), default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

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

class Comment(BaseModel):
    __tablename__ = 'post_comment'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comment = Column(Text)
    parent_id = Column(UUID(as_uuid=True), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey('post.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('post.id'), nullable=False)


class CommentReact(BaseModel):
    __tablename__ = 'comment_react'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(Enum('like', 'sad', 'happy', 'angry', 'love', name='comment_react_type'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    comment_id = Column(UUID(as_uuid=True), ForeignKey('post_comment.id'), nullable=False)
    is_liked = Column(Boolean)


class CommentTagging(BaseModel):
    __tablename__ = 'comment_tagging'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey('post.id'), nullable=False)

class Contact(BaseModel):
    __tablename__ = 'contact'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), default=uuid.uuid4)
    contact_id = Column(UUID(as_uuid=True), default=uuid.uuid4)
    type = Column(Enum('Individual', 'Influencer', 'Expert', name='user_type'))
    friend_status = Column(String(255))
    following_status = Column(String(255))
    is_following = Column(Boolean,default=False)
    following_on = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    unfollowed_on = Column(DateTime)
    friend_since = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    block_on = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    unblock_on = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class UserTopics(BaseModel):
    __tablename__ = 'user_topics'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    topic = Column(VARCHAR(255))

class HealthProfile(BaseModel):
    __tablename__ = 'health_profile'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255))
    gender = Column(Enum('Male', 'Female', 'Others', name='gender_type'))
    date_of_birth = Column(DateTime)
    # date_of_entry=Column(DateTime)
    user_id = Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    health_parameters = Column(JSON)


class MasterHealthParameters(BaseModel):
    __tablename__ = 'master_health_parameters'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255))
    user_id = Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    unit = Column(String(255))
    good_range_start = Column(String(100))
    good_range_end = Column(String(100))
    average_range_start = Column(String(100))
    average_range_end = Column(String(100))
    sorting_position = Column(Integer)


class HealthParameters(BaseModel):
    __tablename__ = 'health_parameters'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    label = Column(String(255))
    unit = Column(String(255))


class HealthReport(BaseModel):
    __tablename__ = 'health_report'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    healthprofile_id = Column(UUID(as_uuid=True), db.ForeignKey('health_profile.id'))
    report_date = Column(Text())
    report = Column(JSON)


class HealthParameterValues(BaseModel):
    __tablename__ = 'health_parameter_values'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    healthreport_id = Column(UUID(as_uuid=True), db.ForeignKey('health_profile.id'))
    healthparameters_id = Column(UUID(as_uuid=True), db.ForeignKey('health_parameters.id'))
    value = Column(String(255))

class Media(BaseModel):
    __tablename__ = 'media'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    source_id = db.Column(UUID(as_uuid=True))
    file_size = Column(Integer)
    path = Column(String(255))
    type = Column(String(255))
    source_type = Column(Enum('profile_image','gallery',name='upload_type'))

class Notification(BaseModel):
    __tablename__ = 'notification'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    type = Column(Enum('friend', 'group', 'general','post', name='notification_type'))
    title = Column(VARCHAR(255))
    description = Column(VARCHAR(255))
    read_status = Column(Boolean)
    meta_data = Column(JSON)
    c_user=Column(UUID(as_uuid=True))
    # expiry_date = Column(DateTime)
    notification_status = Column(VARCHAR(20))

class Master_course(BaseModel):
    __tablename__ = 'master_course'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255))
    field = Column(String(255))
    media = Column(String(255))
    level = Column(JSON)


class Expert(BaseModel):
    __tablename__ = 'expert'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sport_level = Column(String(255))
    adrenln_fitness = Column(String(255))
    level = Column(String(255))
    user_id = Column(UUID(as_uuid=True))


class Hall_of_fame(BaseModel):
    __tablename__ = 'hall_of_fame'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255))
    description = Column(Text())
    level = Column(String(255))
    image=Column(JSON)
    user_id = Column(UUID(as_uuid=True), ForeignKey('expert.id'), nullable=False)


class Fitness_level(BaseModel):
    __tablename__ = 'fitness_level'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(String(255))
    user_id = Column(UUID(as_uuid=True), ForeignKey('expert.id'), nullable=False)
    value = Column(String(50))
    seconds = Column(String(255))
    visibility = Column(Enum('all', 'friends', 'custom', 'group', 'private', 'followers', name='visibility_type'))


class Sport_level(BaseModel):
    __tablename__ = 'sport_level'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    is_primary = Column(String(255))
    sport_id = Column(UUID)
    more_info = Column(JSON)
    sorting_position = Column(String(255))
    playing_level = Column(VARCHAR(255))
    secondary_visibility = Column(Enum('all', 'friends', 'custom', 'group', 'private', 'followers', name='visibility_type'))
    sport_level_visibility = Column(Enum('all', 'friends', 'custom', 'group', 'private', 'followers', name='visibility_type'))
    primary_deleted_at = Column(DateTime)
    secondary_deleted_at = Column(DateTime)


class Experties_background(BaseModel):
    __tablename__ = 'experties_background'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    description = Column(TEXT)
    experties_in = Column(JSON)
    city = Column(VARCHAR(255))
    is_offer_programme = Column(Boolean)
    is_remote_consulting = Column(Boolean)


class Programme(BaseModel):
    __tablename__ = 'programme'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    description = Column(TEXT)
    title = Column(VARCHAR(255))
    category = Column(VARCHAR(255))
    city = Column(VARCHAR(255))
    media = Column(JSON)
    is_featured = Column(Integer)
    master_programs_id = Column(UUID(as_uuid=True),default=uuid.uuid4)


class FeaturedMedia(BaseModel):
    __tablename__ = 'featured_media'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    description = Column(TEXT)
    title = Column(VARCHAR(255))
    media = Column(JSON)


class CustomerTestimonials(BaseModel):
    __tablename__ = 'customer_testimonials'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(255))
    description = Column(TEXT)
    media = Column(JSON)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))


class ContactMe(BaseModel):
    __tablename__ = 'contact_me'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    to_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    description = Column(TEXT)
    name = Column(VARCHAR(255))
    email = Column(VARCHAR(255))
    mobile = Column(VARCHAR(255))
    is_submited = Column(Boolean)

    def to_dict(self):
        res = {c: getattr(self, c) for c in inspect(self).attrs.keys()}
        return res


class SelectedPrograms(BaseModel):
    __tablename__ = 'selected_programs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    programme_id = Column(UUID(as_uuid=True), ForeignKey('programme.id'))
    connect = Column(Boolean)


class MasterProgram(BaseModel):
    __tablename__ = 'master_programs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(225))


class MasterSports(BaseModel):
    __tablename__ = 'master_sport'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(225))
    logo = Column(JSON)
    fields = Column(JSON)


class ProfileVisibility(BaseModel):
    __tablename__ = 'profile_visibility'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section = Column(VARCHAR(225))
    visibility = Column(VARCHAR(225))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))


class TermsConditions(BaseModel):
    __tablename__ = 'terms_conditions'
    id = Column(UUID(as_uuid=True),primary_key=True, default=uuid.uuid4)
    section = Column(VARCHAR(255))
    terms_condition = Column(TEXT)

# Create tables.
Base.metadata.create_all(bind=engine)