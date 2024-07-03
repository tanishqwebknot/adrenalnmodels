import uuid

from sqlalchemy import Column, String, DateTime, Integer, Boolean, Enum, inspect, ForeignKey, VARCHAR, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.models import BaseModel


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

