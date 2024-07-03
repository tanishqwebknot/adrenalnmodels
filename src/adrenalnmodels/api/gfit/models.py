import re
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey, Date, Enum, JSON, VARCHAR
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from app import db
from app.models import BaseModel


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

