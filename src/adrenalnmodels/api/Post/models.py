import re
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey, Date, Enum, VARCHAR, JSON, Text, REAL
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from app import db
from app.models import BaseModel


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
    key = Column(VARCHAR(255), unique=True)
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
