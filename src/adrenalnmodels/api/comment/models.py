import uuid

from sqlalchemy import Column, ForeignKey, Text, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID

from app.models import BaseModel


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
