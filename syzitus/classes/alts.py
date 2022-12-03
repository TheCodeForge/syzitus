from sqlalchemy import Column, Integer, Boolean, UniqueConstraint, ForeignKey

from syzitus.__main__ import Base

# The alt class is for admin tracking of users across multiple accounts.
# The information provided by this is not available to regular users.


class Alt(Base):

    __tablename__ = "alts"

    id = Column(Integer, primary_key=True)
    user1 = Column(Integer, ForeignKey("users.id"), index=True)
    user2 = Column(Integer, ForeignKey("users.id"), index=True)
    is_manual=Column(Boolean, default=False)

    unique_pairs = UniqueConstraint("user1", "user2")

    def __repr__(self):

        return f"<Alt(id={self.id})>"
