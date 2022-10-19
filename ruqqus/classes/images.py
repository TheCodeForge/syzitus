import time
from sqlalchemy import *
from sqlalchemy.orm import relationship
from flask import g
import random

from ruqqus.helpers.base36 import *
from ruqqus.__main__ import Base


class Image(Base):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @property
    def path(self):
        return f"/assets/images/states/{self.state.lower()}-{self.number}.jpg"

IMG_DATA={
    1: {'number': 1, 'state': 'SD', 'text': 'Mount Rushmore, South Dakota'},
    2: {'number': 1, 'state': 'ME', 'text': 'Acadia National Park, Maine'},
    3: {'number': 1, 'state': 'UT', 'text': 'Arches National Park, Utah'},
    4: {'number': 1, 'state': 'NV', 'text': 'Las Vegas, NV'},
    5: {'number': 1, 'state': 'NY', 'text': 'Freedom Tower, New York'},
    6: {'number': 1, 'state': 'SC', 'text': 'The Peachoid, South Carolina'},
    7: {'number': 2, 'state': 'NH', 'text': 'Kancamangus Highway, New Hampshire'},
    8: {'number': 1, 'state': 'FL', 'text': 'Everglades, Florida'},
    9: {'number': 1, 'state': 'MT', 'text': 'Glacier National Park, Montana'},
    10: {'number': 1, 'state': 'WY', 'text': 'Jackson Hole Valley, Wyoming'},
    11: {'number': 1, 'state': 'AK', 'text': 'Mount Denali, Alaska'},
    12: {'number': 1, 'state': 'AZ', 'text': 'Horseshoe Bend, Arizona'},
    13: {'number': 1, 'state': 'CA', 'text': 'Redwood National Forest, California'},
    14: {'number': 1, 'state': 'DC', 'text': 'Lincoln Memorial, Washington DC'},
    15: {'number': 1, 'state': 'MA', 'text': 'USS Constitution, Massachusetts'},
    16: {'number': 1, 'state': 'NE', 'text': 'Downtown Omaha, Nebraska'},
    17: {'number': 1, 'state': 'OK', 'text': 'Gaylord Stadium, Oklahoma'}
}

IMAGES={x: Image(id=x, **IMG_DATA[x]) for x in IMG_DATA}

def random_image():
    return random.choice(IMAGES)



class BadPic(Base):

    #Class for tracking fuzzy hashes of banned csam images

    __tablename__="badpics"
    id = Column(BigInteger, primary_key=True)
    description=Column(String(255), default=None)
    phash=Column(String(64))
    ban_reason=Column(String(64))
    ban_time=Column(Integer)
