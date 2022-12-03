import time
from sqlalchemy.orm import relationship

from .mix_ins import Stndrd

from syzitus.__main__ import Base, cache, debug, app


class Category(Stndrd):


    def __init__(self, id):

        self.id=id
        self.__dict__.update(**CATEGORY_DATA[self.id])

    @property
    def subcats(self):
        return {x:SubCategory(id=x) for x in SUBCAT_DATA if SUBCAT_DATA[x]['cat_id']==self.id}
    
    
    @property
    def json(self):
        return {
            "id": self.id,
            "name": self.name,
            "subcategories": [x.json for x in self.subcats]
        }

class SubCategory(Stndrd):


    def __init__(self, id):

        self.id=id
        self.__dict__.update(**SUBCAT_DATA[self.id])

    @property
    def category(self):
        return Category(self.cat_id)

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

CATEGORY_DATA={
    1: {'icon': 'fa-palette', 'name': 'Arts'},
    2: {'icon': 'fa-chart-line', 'name': 'Business'},
    3: {'icon': 'fa-users', 'name': 'Culture'},
    4: {'icon': 'fa-podium', 'name': 'Discussion'},
    5: {'icon': 'fa-theater-masks', 'name': 'Entertainment'},
    6: {'icon': 'fa-alien-monster', 'name': 'Gaming'},
    7: {'icon': 'fa-wrench', 'name': 'Hobbies'},
    8: {'icon': 'fa-heart', 'name': 'Health'},
    9: {'icon': 'fa-tshirt', 'name': 'Lifestyle'},
    10: {'icon': 'fa-grin', 'name': 'Memes'},
    11: {'icon': 'fa-newspaper', 'name': 'News'},
    12: {'icon': 'fa-university', 'name': 'Politics'},
    13: {'icon': 'fa-flask', 'name': 'Science'},
    14: {'icon': 'fa-baseball-ball', 'name': 'Sports'},
    15: {'icon': 'fa-microchip', 'name': 'Technology'}
}

SUBCAT_DATA={
    1: {'cat_id': 12, 'name': 'Activism'},
    2: {'cat_id': 9, 'name': 'Animals'},
    3: {'cat_id': 3, 'name': 'Architecture'},
    4: {'cat_id': 12, 'name': 'Authoritarian'},
    5: {'cat_id': 9, 'name': 'Beauty'},
    6: {'cat_id': 9, 'name': 'Career'},
    7: {'cat_id': 10, 'name': 'Casual'},
    8: {'cat_id': 4, 'name': 'Casual Discussion'},
    9: {'cat_id': 5, 'name': 'Celebrities'},
    10: {'cat_id': 14, 'name': 'Combat'},
    11: {'cat_id': 15, 'name': 'Computers'},
    12: {'cat_id': 6, 'name': 'Console'},
    13: {'cat_id': 3, 'name': 'Counter-Culture'},
    14: {'cat_id': 7, 'name': 'Crafts'},
    15: {'cat_id': 3, 'name': 'Cuisine'},
    16: {'cat_id': 7, 'name': 'DIY'},
    17: {'cat_id': 1, 'name': 'Dance'},
    18: {'cat_id': 10, 'name': 'Dank'},
    19: {'cat_id': 6, 'name': 'Development'},
    20: {'cat_id': 4, 'name': 'Drama'},
    21: {'cat_id': 15, 'name': 'Engineering'},
    22: {'cat_id': 2, 'name': 'Entrepreneurship'},
    23: {'cat_id': 14, 'name': 'Extreme'},
    24: {'cat_id': 9, 'name': 'Fashion'},
    25: {'cat_id': 1, 'name': 'Film & TV'},
    26: {'cat_id': 5, 'name': 'Film & TV'},
    27: {'cat_id': 2, 'name': 'Finance'},
    28: {'cat_id': 8, 'name': 'Fitness'},
    29: {'cat_id': 9, 'name': 'Food'},
    30: {'cat_id': 15, 'name': 'Gadgets'},
    31: {'cat_id': 6, 'name': 'Gaming news'},
    32: {'cat_id': 13, 'name': 'Hard Sciences'},
    33: {'cat_id': 15, 'name': 'Hardware'},
    34: {'cat_id': 15, 'name': 'Help'},
    35: {'cat_id': 3, 'name': 'History'},
    36: {'cat_id': 12, 'name': 'Identity Politics'},
    37: {'cat_id': 14, 'name': 'Individual'},
    38: {'cat_id': 5, 'name': 'Influencers'},
    39: {'cat_id': 3, 'name': 'Language'},
    40: {'cat_id': 12, 'name': 'Left'},
    41: {'cat_id': 12, 'name': 'Libertarian'},
    42: {'cat_id': 1, 'name': 'Literature'},
    43: {'cat_id': 11, 'name': 'Local'},
    44: {'cat_id': 2, 'name': 'Management'},
    45: {'cat_id': 13, 'name': 'Mathematics'},
    46: {'cat_id': 15, 'name': 'Mechanics'},
    47: {'cat_id': 8, 'name': 'Medical'},
    48: {'cat_id': 8, 'name': 'Mental Health'},
    49: {'cat_id': 1, 'name': 'Music'},
    50: {'cat_id': 13, 'name': 'Natural Sciences'},
    51: {'cat_id': 5, 'name': 'News'},
    52: {'cat_id': 15, 'name': 'News'},
    53: {'cat_id': 13, 'name': 'News'},
    54: {'cat_id': 12, 'name': 'News'},
    55: {'cat_id': 11, 'name': 'North America'},
    56: {'cat_id': 10, 'name': 'Offensive'},
    57: {'cat_id': 7, 'name': 'Outdoors'},
    58: {'cat_id': 6, 'name': 'PC'},
    59: {'cat_id': 14, 'name': 'Partner'},
    60: {'cat_id': 9, 'name': 'Personal Finance'},
    61: {'cat_id': 3, 'name': 'Philosophy'},
    62: {'cat_id': 1, 'name': 'Photography'},
    63: {'cat_id': 10, 'name': 'Political'},
    64: {'cat_id': 2, 'name': 'Product'},
    65: {'cat_id': 15, 'name': 'Programming'},
    66: {'cat_id': 6, 'name': 'Puzzle'},
    67: {'cat_id': 4, 'name': 'Q&A'},
    68: {'cat_id': 9, 'name': 'Relationships'},
    69: {'cat_id': 3, 'name': 'Religion'},
    70: {'cat_id': 12, 'name': 'Right'},
    71: {'cat_id': 4, 'name': f'{app.config["SITE_NAME"]} Meta'},
    72: {'cat_id': 1, 'name': 'Sculpture'},
    73: {'cat_id': 4, 'name': 'Serious'},
    74: {'cat_id': 7, 'name': 'Skills'},
    75: {'cat_id': 13, 'name': 'Soft Sciences'},
    76: {'cat_id': 15, 'name': 'Software'},
    77: {'cat_id': 13, 'name': 'Space'},
    78: {'cat_id': 2, 'name': 'Startups'},
    79: {'cat_id': 8, 'name': 'Support'},
    80: {'cat_id': 6, 'name': 'Tabletop'},
    81: {'cat_id': 14, 'name': 'Team'},
    82: {'cat_id': 1, 'name': 'Theater'},
    83: {'cat_id': 11, 'name': 'Upbeat'},
    84: {'cat_id': 1, 'name': 'Visual Arts'},
    85: {'cat_id': 10, 'name': 'Wholesome'},
    86: {'cat_id': 11, 'name': 'World'}
 }

CATEGORIES={x:Category(id=x) for x in CATEGORY_DATA}