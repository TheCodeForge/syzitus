import time
from sqlalchemy import Column, BigInteger, String, Integer, Index
from sqlalchemy.orm import relationship
from flask import g

from syzitus.helpers.base36 import *
from syzitus.__main__ import Base


class Image():

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @property
    def path(self):
        return f"/assets/images/states/{self.state.lower()}-{self.number}.jpg"

IMG_DATA=[
    {'number': 1, 'state': 'AL', 'text': 'Bellingrath Gardens, Alabama'},
    {'number': 1, 'state': 'AK', 'text': 'Mount Denali, Alaska'},
    {'number': 1, 'state': 'AR', 'text': "Devil's Den State Park, Arkansas"},
    {'number': 1, 'state': 'AZ', 'text': 'Horseshoe Bend, Arizona'},
    {'number': 1, 'state': 'CA', 'text': 'Redwood National Forest, California'},
    {'number': 1, 'state': 'CT', 'text': 'Yale University, Connecticut'},
    {'number': 1, 'state': 'CO', 'text': "Pikes Peak Highway, Colorado"},
    {'number': 1, 'state': 'DC', 'text': 'Lincoln Memorial, Washington DC'},
    {'number': 1, 'state': 'DE', 'text': 'Breakwater East End Lighthouse, Delaware'},
    {'number': 1, 'state': 'FL', 'text': 'Cape Canaveral, Florida'},
    {'number': 1, 'state': 'GA', 'text': 'Atlanta, Georgia'},
    {'number': 1, 'state': 'HI', 'text': 'Waikiki Beach, Hawaii'},
    {'number': 1, 'state': 'IA', 'text': 'Des Moines State Capitol, Iowa'},
    {'number': 1, 'state': 'ID', 'text': 'Lochsa River, Idaho'},
    {'number': 1, 'state': 'IL', 'text': 'Chicago skyline, Illinois'},
    {'number': 1, 'state': 'IN', 'text': 'Indianapolis Motor Speedway, Indiana'},
    {'number': 1, 'state': 'KS', 'text': 'Keeper of the Plains, Kansas'},
    {'number': 1, 'state': 'KY', 'text': 'Frankfort Capitol Plaza, Kentucky'},
    {'number': 1, 'state': 'LA', 'text': 'Oak Alley Plantation, Louisiana'},
    {'number': 1, 'state': 'MA', 'text': 'Boston skyline, Massachusetts'},
    {'number': 1, 'state': 'MD', 'text': 'George Peabody Library, Maryland'},
    {'number': 1, 'state': 'ME', 'text': 'Acadia National Park, Maine'},
    {'number': 1, 'state': 'MI', 'text': 'Mackinac Bridge, Michigan'},
    {'number': 1, 'state': 'MN', 'text': 'Spoonbridge And Cherry, Minnesota'},
    {'number': 1, 'state': 'MO', 'text': 'Nelson-Atkins Museum of Art, Missouri'},
    {'number': 1, 'state': 'MT', 'text': 'Glacier National Park, Montana'},
    {'number': 1, 'state': 'MS', 'text': 'Longwood House, Mississippi'},
    {'number': 1, 'state': 'NC', 'text': 'Wright Brothers National Memorial, North Carolina'},
    {'number': 1, 'state': 'ND', 'text': 'Theodore Roosevelt National Park, North Dakota'},
    {'number': 1, 'state': 'NE', 'text': 'Carhenge, Nebraska'},
    {'number': 1, 'state': 'NH', 'text': 'Kancamangus Highway, New Hampshire'},
    {'number': 1, 'state': 'NJ', 'text': 'Ocean City Boardwalk, New Jersey'},
    {'number': 1, 'state': 'NM', 'text': 'Shiprock, New Mexico'},
    {'number': 1, 'state': 'NV', 'text': 'Las Vegas, Nevada'},
    {'number': 1, 'state': 'NY', 'text': 'Freedom Tower, New York'},
    {'number': 1, 'state': 'OH', 'text': 'Cleveland Arcade, Ohio'},
    {'number': 1, 'state': 'OK', 'text': 'Gaylord Stadium, Oklahoma'},
    {'number': 1, 'state': 'OR', 'text': 'McKenzie River'},
    {'number': 1, 'state': 'PA', 'text': 'Bushkill Falls, Pennsylvania'},
    {'number': 1, 'state': 'RI', 'text': 'The Marble House, Rhode Island'},
    {'number': 1, 'state': 'SC', 'text': 'The Peachoid, South Carolina'},
    {'number': 1, 'state': 'SD', 'text': 'Mount Rushmore, South Dakota'},
    {'number': 1, 'state': 'TN', 'text': 'Nashville fireworks, Tennessee'},
    {'number': 1, 'state': 'TX', 'text': 'Thanks-Giving Square, Texas'},
    {'number': 1, 'state': 'UT', 'text': 'Arches National Park, Utah'},
    {'number': 1, 'state': 'VA', 'text': 'Luray Caverns, Virginia'},
    {'number': 1, 'state': 'VT', 'text': 'Montpelier Capitol, Vermont'},
    {'number': 1, 'state': 'WI', 'text': 'Milwaukee Art Museum, Wisconsin'},
    {'number': 1, 'state': 'WV', 'text': 'Glade Creek Grist Mill, West Virginia'},
    {'number': 1, 'state': 'WY', 'text': 'Jackson Hole Valley, Wyoming'}
]

#IMAGES=[Image(**x) for x in IMG_DATA]

def random_image():
    return Image(**IMAGE_DATA[g.timestamp % len(IMAGES) + 1])



class BadPic(Base):

    #Class for tracking fuzzy hashes of banned csam images

    __tablename__="badpics"
    id = Column(BigInteger, primary_key=True)
    description=Column(String(255), default=None)
    phash=Column(String(64), index=True)
    ban_reason=Column(String(64))
    ban_time=Column(Integer)

    __table_args__=(
        Index(
            "badpics_phash_trgm_idx", "phash",
            postgresql_using="gin",
            postgresql_ops={
                'phash':'gin_trgm_ops'
                }
            ),
        )
