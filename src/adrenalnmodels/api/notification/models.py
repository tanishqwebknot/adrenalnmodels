import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, VARCHAR, JSON, Boolean, INTEGER, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.models import BaseModel


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

