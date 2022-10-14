from ruqqus.helpers.base36 import *
from ruqqus.helpers.security import *
from sqlalchemy import *
from sqlalchemy.orm import relationship
from ruqqus.__main__ import Base, cache
from .mix_ins import *
import time



class Lodge(Base, Stndrd, Age_times):
    __tablename__ = "lodges"
    id = Column(BigInteger, primary_key=True)
    name = Column(String(20), default="")
    color = Column(String(6), default="")
    description = Column(String(250), default="")
    user_id = Column(Integer, ForeignKey("users.id"))
    board_id = Column(Integer, ForeignKey("boards.id"))
    created_utc = Column(Integer, default=0)

    def __init__(self, *args, **kwargs):
        if "created_utc" not in kwargs:
            kwargs["created_utc"] = int(time.time())