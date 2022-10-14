from sqlalchemy import *
from ruqqus.helpers.base36 import *
from ruqqus.helpers.security import *
from ruqqus.helpers.lazy import lazy
from ruqqus.__main__ import Base

# The alt class is for admin tracking of users across multiple accounts.
# The information provided by this is not available to regular users.


class Alt(Base):

    __tablename__ = "alts"

    id = Column(Integer, primary_key=True)
    user1 = Column(Integer, ForeignKey("users.id"))
    user2 = Column(Integer, ForeignKey("users.id"))
    is_manual=Column(Boolean, default=False)

    def __repr__(self):

        return f"<Alt(id={self.id})>"
