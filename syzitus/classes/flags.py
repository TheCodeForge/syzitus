from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, FetchedValue

from .mix_ins import standard_mixin

from syzitus.__main__ import Base, cache


class Flag(Base, standard_mixin):

    __tablename__ = "flags"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("submissions.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_utc = Column(Integer)
    resolution_notif_sent=Column(Boolean, default=False, nullable=False)

    def __repr__(self):

        return f"<Flag(id={self.id})>"


class CommentFlag(Base, standard_mixin):

    __tablename__ = "commentflags"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    comment_id = Column(Integer, ForeignKey("comments.id"))
    created_utc = Column(Integer)
    resolution_notif_sent=Column(Boolean, default=False, nullable=False)

    def __repr__(self):

        return f"<CommentFlag(id={self.id})>"


class Report(Base):

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("submissions.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_utc = Column(Integer)

    board_id = Column(Integer, server_default=FetchedValue())

    def __repr__(self):

        return f"<Report(id={self.id})>"
