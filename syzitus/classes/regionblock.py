from sqlalchemy import *

from syzitus.helpers.countries import COUNTRY_CODES
from syzitus.__main__ import app, Base

class RegionBlock(Base):

    __tablename__="regionblocks"

    id      =Column(Integer, primary_key=True)
    cc      =Column(String(2))
    post_id =Column(Integer, ForeignKey("submissions.id"))
    board_id=Column(integer, ForeignKey("boards.id"))
    source  =Column(String(512))

    post    =relationship("Submission")
    board   =relationship("Board")

    @property
    def country(self):
        return COUNTRY_CODES[self.cc]
    