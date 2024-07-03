import uuid

from sqlalchemy import Column, String, DateTime, Enum, JSON,Text,Integer,Float
from sqlalchemy.dialects.postgresql import UUID

from app import db
from app.models import BaseModel


class HealthProfile(BaseModel):
    __tablename__ = 'health_profile'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255))
    gender = Column(Enum('Male', 'Female', 'Others', name='gender_type'))
    date_of_birth = Column(DateTime)
    # date_of_entry=Column(DateTime)
    user_id = Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    health_parameters = Column(JSON)


class MasterHealthParameters(BaseModel):
    __tablename__ = 'master_health_parameters'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255))
    user_id = Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    unit = Column(String(255))
    good_range_start = Column(String(100))
    good_range_end = Column(String(100))
    average_range_start = Column(String(100))
    average_range_end = Column(String(100))
    sorting_position = Column(Integer)


class HealthParameters(BaseModel):
    __tablename__ = 'health_parameters'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    label = Column(String(255))
    unit = Column(String(255))


class HealthReport(BaseModel):
    __tablename__ = 'health_report'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    healthprofile_id = Column(UUID(as_uuid=True), db.ForeignKey('health_profile.id'))
    report_date = Column(Text())
    report = Column(JSON)


class HealthParameterValues(BaseModel):
    __tablename__ = 'health_parameter_values'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    healthreport_id = Column(UUID(as_uuid=True), db.ForeignKey('health_profile.id'))
    healthparameters_id = Column(UUID(as_uuid=True), db.ForeignKey('health_parameters.id'))
    value = Column(String(255))
