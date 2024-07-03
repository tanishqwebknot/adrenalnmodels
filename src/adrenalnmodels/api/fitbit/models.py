import re
import uuid
from datetime import datetime
from sqlalchemy import Column, String,DECIMAL, DateTime, Integer, Boolean, ForeignKey, Date, Enum, JSON, VARCHAR, TEXT,ARRAY,Float
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from app import db
from app.models import BaseModel


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