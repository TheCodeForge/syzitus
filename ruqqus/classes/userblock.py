from flask import *
from sqlalchemy import *
from sqlalchemy.orm import relationship

import ruqqus.helpers.aws as aws
from .mix_ins import *
from ruqqus.__main__ import Base, cache


class UserBlock(Base, Stndrd, Age_times):

    __tablename__ = "userblocks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    target_id = Column(Integer, ForeignKey("users.id"))
    created_utc = Column(Integer)

    user = relationship(
        "User",
        innerjoin=True,
        primaryjoin="User.id==UserBlock.user_id",
        backref="blocking")
    target = relationship(
        "User",
        innerjoin=True,
        primaryjoin="User.id==UserBlock.target_id",
        backref="blocked")

    def __repr__(self):

        return f"<UserBlock(user={user.username}, target={target.username})>"
