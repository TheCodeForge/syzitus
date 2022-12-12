from sqlalchemy import Column, Integer, BigInteger, String, Boolean, ForeignKey, FetchedValue
from sqlalchemy.orm import relationship
from flask import g

from syzitus.__main__ import Base, cache


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), index=True)
    board_id = Column(BigInteger, ForeignKey("boards.id"), index=True)
    created_utc = Column(BigInteger, default=0)
    is_active = Column(Boolean, default=True)
    get_notifs=Column(Boolean, default=False)

    user = relationship("User", uselist=False, viewonly=True)
    board = relationship("Board", uselist=False, viewonly=True)

    def __init__(self, *args, **kwargs):
        if "created_utc" not in kwargs:
            kwargs["created_utc"] = g.timestamp

        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"<Subscription(id={self.id})>"


class Follow(Base):
    __tablename__ = "follows"
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), index=True)
    target_id = Column(BigInteger, ForeignKey("users.id"), index=True)
    created_utc = Column(BigInteger, default=0)
    get_notifs=Column(Boolean, default=False)

    user = relationship(
        "User",
        uselist=False,
        primaryjoin="User.id==Follow.user_id",
        viewonly=True)
    target = relationship(
        "User",
        lazy="joined",
        primaryjoin="User.id==Follow.target_id",
        viewonly=True)

    def __init__(self, *args, **kwargs):
        if "created_utc" not in kwargs:
            kwargs["created_utc"] = g.timestamp

        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"<Follow(id={self.id})>"
