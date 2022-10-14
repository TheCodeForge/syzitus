from ruqqus.helpers.base36 import *
from ruqqus.helpers.security import *
from ruqqus.helpers.lazy import lazy
from sqlalchemy import *
from sqlalchemy.orm import relationship
from ruqqus.__main__ import db_session, Base, cache
from .mix_ins import *
import time


class Category(Base, Stndrd):
    __tablename__ = "categories"
    id = Column(BigInteger, primary_key=True)
    name = Column(String(20), default="")
    description = Column(String(250), default="")
    icon = Column(String(256), default="")
    color = Column(String(128), default="805ad5")
    visible = Column(Boolean, default=True)
    is_nsfw = Column(Boolean, default=False)
    _subcats = relationship("SubCategory", lazy="joined", primaryjoin="SubCategory.cat_id==Category.id")

    @property
    @lazy
    def subcats(self):
        l=[i for i in self._subcats]

        return sorted(l, key=lambda x:x.name)
    

    @property
    def json(self):
        return {
            "id": self.id,
            "name": self.name,
            "subcategories": [x.json for x in self.subcats]
        }


class SubCategory(Base, Stndrd):
    __tablename__ = "subcategories"
    id = Column(BigInteger, primary_key=True)
    cat_id = Column(Integer, ForeignKey("categories.id"))
    name = Column(String(20), default="")
    description = Column(String(250), default="")
    _visible = Column(Boolean, default=0)

    category = relationship("Category", lazy="joined")

    @property
    def visible(self):
        return self._visible if self._visible in [True, False] else self.category.visible
    
    @property
    def json(self):
        return {
            "id": self.id,
            "category_id": self.cat_id,
            "name": self.name
        }

db=db_session()
CATEGORIES = [i for i in db.query(Category).order_by(Category.name.asc()).all()]
db.close()

# class GuildCategory(Base, Stndrd, Age_times):
#     __tablename__ = "guildcategories"
#     id = Column(BigInteger, primary_key=True)
#     subcat_id = Column(Integer, ForeignKey("subcategories.id"), default=0)
#     board_id = Column(Integer, ForeignKey("boards.id"), default=0)
#     created_utc = Column(integer, default=0)

#     subcat = relationship("SubCategory", lazy="joined")
#     board = relationship("Board", lazy="joined")

#     def __init__(self, *args, **kwargs):
#         if "created_utc" not in kwargs:
#             kwargs["created_utc"] = int(time.time())
