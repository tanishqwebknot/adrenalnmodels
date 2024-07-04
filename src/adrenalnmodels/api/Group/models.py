
import uuid

from sqlalchemy import Column, String, Enum, ForeignKey, Text, JSON, VARCHAR
from sqlalchemy.dialects.postgresql import UUID

from app.models import BaseModel


class Group(BaseModel):
    __tablename__ = 'user_group'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_name = Column(String(255))
    description = Column(Text())
    sport_type = Column(String(255))
    city = Column(String(255))
    image = Column(JSON)
    topic = Column(VARCHAR(255))
    visibility = Column(Enum('all', 'friends', 'custom', 'group_members', name='visibility_type'))
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
