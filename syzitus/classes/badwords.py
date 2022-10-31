from sqlalchemy import *
import re

from ruqqus.__main__ import Base


class BadWord(Base):

    __tablename__ = "badwords"

    id = Column(Integer, primary_key=True)
    keyword = Column(String(64))
    regex = Column(String(256))

    def check(self, text):
        return bool(re.search(self.regex,
                              text,
                              re.IGNORECASE
                              )
                    )
