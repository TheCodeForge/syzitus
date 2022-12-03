from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from syzitus.__main__ import Base


class IP(Base):

    __tablename__ = "ips"

    id = Column(Integer, primary_key=True)
    addr = Column(String(64), index=True, unique=True)
    reason = Column(String(256), default="")
    banned_by = Column(Integer, ForeignKey("users.id"), default=True)
    unban_utc = Column(Integer, default=None)


class Agent(Base):

    __tablename__ = "useragents"

    id = Column(Integer, primary_key=True)
    kwd = Column(String(64), index=True)
    reason = Column(String(256), default="")
    banned_by = Column(Integer, ForeignKey("users.id"))
    mock = Column(String(256), default="")
    status_code = Column(Integer, default=418)
    instaban = Column(Boolean, default=False)
