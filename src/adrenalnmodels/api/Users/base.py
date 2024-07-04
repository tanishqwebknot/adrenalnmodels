"""
from sqlalchemy.ext.declarative import declarative_base
from flask_sqlalchemy_session import current_session as session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, DateTime, func, BigInteger
from sqlalchemy import create_engine
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:iphone21@127.0.0.1:5432/adrenaline'
engine = create_engine(SQLALCHEMY_DATABASE_URI)
print(engine)
Session = sessionmaker(bind=engine, autoflush=False)
base = declarative_base()

class BaseModel(base):
    __abstract__ = True
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    update_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), default=None)



def re():
    return None"""