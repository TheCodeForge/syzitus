from sqlalchemy import *

from syzitus.__main__ import app, Base

class RegionBlock(Base):

    __tablename__="regionblocks"

    id      =Column(Integer, primary_key=True)
    country =Column(String(2))
    post_id =Column(Integer, ForeignKey("submissions.id"))
    board_id=Column(integer, ForeignKey("boards.id"))
    note    =Column(String(512))
