import uuid

from sqlalchemy import Column, String, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID

from app import db
from app.models import BaseModel


class Media(BaseModel):
    __tablename__ = 'media'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    source_id = db.Column(UUID(as_uuid=True))
    file_size = Column(Integer)
    path = Column(String(255))
    type = Column(String(255))
    source_type = Column(Enum('profile_image','gallery',name='upload_type'))
