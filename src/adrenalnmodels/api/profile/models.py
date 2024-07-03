import uuid
from sqlalchemy import Column, String, ForeignKey, Text, JSON, Enum, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.models import BaseModel
from sqlalchemy import Column, Boolean, inspect, ForeignKey, TEXT, VARCHAR, JSON
from sqlalchemy.dialects.postgresql import UUID


class Master_course(BaseModel):
    __tablename__ = 'master_course'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255))
    field = Column(String(255))
    media = Column(String(255))
    level = Column(JSON)


class Expert(BaseModel):
    __tablename__ = 'expert'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sport_level = Column(String(255))
    adrenln_fitness = Column(String(255))
    level = Column(String(255))
    user_id = Column(UUID(as_uuid=True))


class Hall_of_fame(BaseModel):
    __tablename__ = 'hall_of_fame'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255))
    description = Column(Text())
    level = Column(String(255))
    image=Column(JSON)
    user_id = Column(UUID(as_uuid=True), ForeignKey('expert.id'), nullable=False)


class Fitness_level(BaseModel):
    __tablename__ = 'fitness_level'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(String(255))
    user_id = Column(UUID(as_uuid=True), ForeignKey('expert.id'), nullable=False)
    value = Column(String(50))
    seconds = Column(String(255))
    visibility = Column(Enum('all', 'friends', 'custom', 'group', 'private', 'followers', name='visibility_type'))


class Sport_level(BaseModel):
    __tablename__ = 'sport_level'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    is_primary = Column(String(255))
    sport_id = Column(UUID)
    more_info = Column(JSON)
    sorting_position = Column(String(255))
    playing_level = Column(VARCHAR(255))
    secondary_visibility = Column(Enum('all', 'friends', 'custom', 'group', 'private', 'followers', name='visibility_type'))
    sport_level_visibility = Column(Enum('all', 'friends', 'custom', 'group', 'private', 'followers', name='visibility_type'))
    primary_deleted_at = Column(DateTime)
    secondary_deleted_at = Column(DateTime)


class Experties_background(BaseModel):
    __tablename__ = 'experties_background'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    description = Column(TEXT)
    experties_in = Column(JSON)
    city = Column(VARCHAR(255))
    is_offer_programme = Column(Boolean)
    is_remote_consulting = Column(Boolean)


class Programme(BaseModel):
    __tablename__ = 'programme'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    description = Column(TEXT)
    title = Column(VARCHAR(255))
    category = Column(VARCHAR(255))
    city = Column(VARCHAR(255))
    media = Column(JSON)
    is_featured = Column(Integer)
    master_programs_id = Column(UUID(as_uuid=True),default=uuid.uuid4)


class FeaturedMedia(BaseModel):
    __tablename__ = 'featured_media'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    description = Column(TEXT)
    title = Column(VARCHAR(255))
    media = Column(JSON)


class CustomerTestimonials(BaseModel):
    __tablename__ = 'customer_testimonials'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(255))
    description = Column(TEXT)
    media = Column(JSON)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))


class ContactMe(BaseModel):
    __tablename__ = 'contact_me'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    to_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    description = Column(TEXT)
    name = Column(VARCHAR(255))
    email = Column(VARCHAR(255))
    mobile = Column(VARCHAR(255))
    is_submited = Column(Boolean)

    def to_dict(self):
        res = {c: getattr(self, c) for c in inspect(self).attrs.keys()}
        return res


class SelectedPrograms(BaseModel):
    __tablename__ = 'selected_programs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    programme_id = Column(UUID(as_uuid=True), ForeignKey('programme.id'))
    connect = Column(Boolean)


class MasterProgram(BaseModel):
    __tablename__ = 'master_programs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(225))


class MasterSports(BaseModel):
    __tablename__ = 'master_sport'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(VARCHAR(225))
    logo = Column(JSON)
    fields = Column(JSON)


class ProfileVisibility(BaseModel):
    __tablename__ = 'profile_visibility'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section = Column(VARCHAR(225))
    visibility = Column(VARCHAR(225))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))


class TermsConditions(BaseModel):
    __tablename__ = 'terms_conditions'
    id = Column(UUID(as_uuid=True),primary_key=True, default=uuid.uuid4)
    section = Column(VARCHAR(255))
    terms_condition = Column(TEXT)

