from sqlalchemy import Column, DateTime, func, BigInteger

from app import db
from common.utils.json_utils import serialize


class BaseModel(db.Model):
    __abstract__ = True
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    update_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), default=None)

    def _asdict(self):
        return serialize(self)

    def objects(*args):
        return db.session.query(*args)