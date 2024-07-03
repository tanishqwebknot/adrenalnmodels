import re
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey, Date, Enum, JSON, VARCHAR, TEXT
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from app import db
from app.models import BaseModel


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