import re
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey, Date, Enum, JSON, VARCHAR, TEXT
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from app import db
from app.models import BaseModel


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

