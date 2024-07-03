import uuid

from sqlalchemy import Column, String, DateTime, Boolean, Enum, ForeignKey, func, VARCHAR
from sqlalchemy.dialects.postgresql import UUID

from app.models import BaseModel


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
