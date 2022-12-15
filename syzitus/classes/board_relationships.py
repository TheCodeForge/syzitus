from sqlalchemy import Column, Integer, BigInteger, Boolean, ForeignKey, String
from sqlalchemy.orm import relationship
from flask import g

from .mix_ins import *
from syzitus.__main__ import Base, cache


class ModRelationship(Base, standard_mixin, age_mixin):
    __tablename__ = "mods"
    id = Column(BigInteger, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    board_id = Column(Integer, ForeignKey("boards.id"), index=True)
    created_utc = Column(Integer, default=0)
    accepted = Column(Boolean, default=False)
    invite_rescinded = Column(Boolean, default=False)

    perm_content = Column(Boolean, default=False)
    perm_appearance = Column(Boolean, default=False)
    perm_config = Column(Boolean, default=False)
    perm_access = Column(Boolean, default=False)
    perm_full = Column(Boolean, default=False)

    user = relationship("User", lazy="joined", viewonly=True)
    board = relationship("Board", lazy="joined", viewonly=True)

    def __init__(self, *args, **kwargs):
        if "created_utc" not in kwargs:
            kwargs["created_utc"] = g.timestamp

        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"<Mod(id={self.id}, uid={self.user_id}, board_id={self.board_id})>"

    @property
    def permlist(self):
        if self.perm_full:
            return "full"

        output=[]
        for p in ["access","appearance", "config","content"]:
            if self.__dict__[f"perm_{p}"]:
                output.append(p)

        
        return ", ".join(output) if output else "none"

    @property
    def permchangelist(self):
        output=[]
        for p in ["full", "access","appearance","config","content"]:
            if self.__dict__.get(f"perm_{p}"):
                output.append(f"+{p}")
            else:
                output.append(f"-{p}")

        return ", ".join(output)


    @property
    def json_core(self):
        return {
            'user_id':self.user_id,
            'board_id':self.board_id,
            'created_utc':self.created_utc,
            'accepted':self.accepted,
            'invite_rescinded':self.invite_rescinded,
            'perm_content':self.perm_full or self.perm_content,
            'perm_config':self.perm_full or self.perm_config,
            'perm_access':self.perm_full or self.perm_access,
            'perm_appearance':self.perm_full or self.perm_appearance,
            'perm_full':self.perm_full
        }


    @property
    def json(self):
        data=self.json_core

        data["user"]=self.user.json_core
        #data["guild"]=self.board.json_core
    
        return data
    
    


class BanRelationship(Base, standard_mixin, age_mixin):

    __tablename__ = "bans"
    id = Column(BigInteger, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    board_id = Column(Integer, ForeignKey("boards.id"))
    created_utc = Column(BigInteger, default=0)
    banning_mod_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=False)
    mod_note = Column(String(128), default="")

    user = relationship(
        "User",
        lazy="joined",
        primaryjoin="User.id==BanRelationship.user_id",
        viewonly=True)
    banning_mod = relationship(
        "User",
        lazy="joined",
        primaryjoin="User.id==BanRelationship.banning_mod_id",
        viewonly=True)
    board = relationship("Board", viewonly=True)

    def __init__(self, *args, **kwargs):
        if "created_utc" not in kwargs:
            kwargs["created_utc"] = g.timestamp

        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"<Ban(id={self.id}, uid={self.uid}, board_id={self.board_id})>"

    @property
    def json_core(self):
        return {
            'user_id':self.user_id,
            'board_id':self.board_id,
            'created_utc':self.created_utc,
            'mod_id':self.banning_mod_id
        }


    @property
    def json(self):
        data=self.json_core

        data["user"]=self.user.json_core
        data["mod"]=self.banning_mod.json_core
        data["guild"]=self.board.json_core

        return data


class ContributorRelationship(Base, standard_mixin, age_mixin):

    __tablename__ = "contributors"
    id = Column(BigInteger, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    board_id = Column(Integer, ForeignKey("boards.id"))
    created_utc = Column(BigInteger, default=0)
    is_active = Column(Boolean, default=True)
    approving_mod_id = Column(Integer, ForeignKey("users.id"))

    user = relationship(
        "User",
        lazy="joined",
        primaryjoin="User.id==ContributorRelationship.user_id", 
        viewonly=True)
    approving_mod = relationship(
        "User",
        lazy='joined',
        primaryjoin="User.id==ContributorRelationship.approving_mod_id",
        viewonly=True)
    board = relationship("Board", lazy="subquery", viewonly=True)

    def __init__(self, *args, **kwargs):
        if "created_utc" not in kwargs:
            kwargs["created_utc"] = g.timestamp

        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"<Contributor(id={self.id}, uid={self.uid}, board_id={self.board_id})>"


class PostRelationship(Base):

    #Documents self-yoink

    __tablename__ = "postrels"
    id = Column(BigInteger, primary_key=True)
    post_id = Column(Integer, ForeignKey("submissions.id"))
    board_id = Column(Integer, ForeignKey("boards.id"))

    post = relationship("Submission", lazy="subquery", viewonly=True)
    board = relationship("Board", lazy="subquery", viewonly=True)

    def __repr__(self):
        return f"<PostRel(id={self.id}, pid={self.post_id}, board_id={self.board_id})>"

"""class PostNotificationSubscriptions(Base):

    __tablename__ = "post_notification_subscriptions"
    id = Column(BigInteger, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    board_id = Column(Integer,ForeignKey("boards.id"), default=0)
    subbed_to_user_id = Column(Integer, ForeignKey("users.id"), default=0)
    #post_id = Column(Integer,ForeignKey("submissions.id"), default=0)

    #user = relationship("User", lazy="subquery")
    board = relationship("Board", lazy="subquery")
    #post = relationship("Submission", lazy="subquery")

    def __repr__(self):
        return f"<PostNotificationSubscription(id={self.id}"
"""


class BoardBlock(Base, standard_mixin, age_mixin):

    __tablename__ = "boardblocks"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    board_id = Column(Integer, ForeignKey("boards.id"))
    created_utc = Column(Integer)

    user = relationship("User", viewonly=True)
    board = relationship("Board", viewonly=True)

    def __repr__(self):
        return f"<BoardBlock(id={self.id}, uid={self.user_id}, board_id={self.board_id})>"
