from .mix_ins import standard_mixin

from syzitus.__main__ import Base, cache, debug, app


class Category(standard_mixin):


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

class SubCategory(standard_mixin):


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
    1: {'icon': 'fa-palette', 'name': 'Arts', 'icon_text': ''},
    2: {'icon': 'fa-chart-line', 'name': 'Business', 'icon_text': ''},
    3: {'icon': 'fa-building-columns', 'name': 'Culture', 'icon_text': ''},
    4: {'icon': 'fa-comment-lines', 'name': 'Discussion', 'icon_text': ''},
    5: {'icon': 'fa-masks-theater', 'name': 'Entertainment', 'icon_text': ''},
    6: {'icon': 'fa-gamepad', 'name': 'Gaming', 'icon_text': ''},
    7: {'icon': 'fa-wrench', 'name': 'Hobbies', 'icon_text': ''},
    8: {'icon': 'fa-heart', 'name': 'Health', 'icon_text': ''},
    9: {'icon': 'fa-shirt', 'name': 'Lifestyle', 'icon_text': ''},
    10: {'icon': 'fa-face-grin-beam', 'name': 'Memes', 'icon_text': ''},
    11: {'icon': 'fa-newspaper', 'name': 'News', 'icon_text': ''},
    12: {'icon': 'fa-podium', 'name': 'Politics', 'icon_text': ''},
    13: {'icon': 'fa-atom', 'name': 'Science', 'icon_text': ''},
    14: {'icon': 'fa-baseball', 'name': 'Sports', 'icon_text': ''},
    15: {'icon': 'fa-microchip', 'name': 'Technology', 'icon_text': ''}
}

SUBCAT_DATA={
    1:  {'cat_id': 12, 'name': 'Activism',          'icon': 'fa-podium', 'icon_text': ''},
    2:  {'cat_id': 9,  'name': 'Animals',           'icon': 'fa-dog', 'icon_text': ''},
    3:  {'cat_id': 3,  'name': 'Architecture',      'icon': 'fa-building-columns', 'icon_text': ''},
    4:  {'cat_id': 12, 'name': 'Authoritarian',     'icon': 'fa-sickle', 'icon_text': ''},
    5:  {'cat_id': 9,  'name': 'Beauty',            'icon': 'fa-podium', 'icon_text': ''},
    6:  {'cat_id': 9,  'name': 'Career',            'icon': 'fa-handshake', 'icon_text': ''},
    7:  {'cat_id': 10, 'name': 'Casual',            'icon': 'fa-face-laugh', 'icon_text': ''},
    8:  {'cat_id': 4,  'name': 'Casual Discussion', 'icon': 'fa-comment-dots', 'icon_text': ''},
    9:  {'cat_id': 5,  'name': 'Celebrities',       'icon': 'fa-star', 'icon_text': ''},
    10: {'cat_id': 14, 'name': 'Combat',            'icon': 'fa-boxing-glove', 'icon_text': ''},
    11: {'cat_id': 15, 'name': 'Computers',         'icon': 'fa-computer', 'icon_text': ''},
    12: {'cat_id': 6,  'name': 'Console',           'icon': 'fa-podium', 'icon_text': ''},
    13: {'cat_id': 3,  'name': 'Counter-Culture',   'icon': 'fa-podium', 'icon_text': ''},
    14: {'cat_id': 7,  'name': 'Crafts',            'icon': 'fa-podium', 'icon_text': ''},
    15: {'cat_id': 3,  'name': 'Cuisine',           'icon': 'fa-pot-food', 'icon_text': ''},
    16: {'cat_id': 7,  'name': 'DIY',               'icon': 'fa-wrench', 'icon_text': ''},
    17: {'cat_id': 1,  'name': 'Dance',             'icon': 'fa-shoe-prints', 'icon_text': ''},
    18: {'cat_id': 10, 'name': 'Dank',              'icon': 'fa-face-laugh-squint', 'icon_text': ''},
    19: {'cat_id': 6,  'name': 'Development',       'icon': 'fa-gamepad', 'icon_text': ''},
    20: {'cat_id': 4,  'name': 'Drama',             'icon': 'fa-comment-exclamation', 'icon_text': ''},
    21: {'cat_id': 15, 'name': 'Engineering',       'icon': 'fa-gears', 'icon_text': ''},
    22: {'cat_id': 2,  'name': 'Entrepreneurship',  'icon': 'fa-user-tie', 'icon_text': ''},
    23: {'cat_id': 14, 'name': 'Extreme',           'icon': 'fa-motorcycle', 'icon_text': ''},
    24: {'cat_id': 9,  'name': 'Fashion',           'icon': 'fa-shirt', 'icon_text': ''},
    25: {'cat_id': 1,  'name': 'Film & TV',         'icon': 'fa-film', 'icon_text': ''},
    26: {'cat_id': 5,  'name': 'Film & TV',         'icon': 'fa-tv-retro', 'icon_text': ''},
    27: {'cat_id': 2,  'name': 'Finance',           'icon': 'fa-chart-line-up', 'icon_text': ''},
    28: {'cat_id': 8,  'name': 'Fitness',           'icon': 'fa-person-running', 'icon_text': ''},
    29: {'cat_id': 9,  'name': 'Food',              'icon': 'fa-bowl-food', 'icon_text': ''},
    30: {'cat_id': 15, 'name': 'Gadgets',           'icon': 'fa-mobile', 'icon_text': ''},
    32: {'cat_id': 13, 'name': 'Hard Sciences',     'icon': 'fa-atom', 'icon_text': ''},
    33: {'cat_id': 15, 'name': 'Hardware',          'icon': 'fa-microchip', 'icon_text': ''},
    34: {'cat_id': 15, 'name': 'Help',              'icon': 'fa-comments-question', 'icon_text': ''},
    35: {'cat_id': 3,  'name': 'History',           'icon': 'fa-landmark', 'icon_text': ''},
    36: {'cat_id': 12, 'name': 'Identity Politics', 'icon': 'fa-venus-mars', 'icon_text': ''},
    37: {'cat_id': 14, 'name': 'Individual',        'icon': 'fa-person-skiing', 'icon_text': ''},
    38: {'cat_id': 5,  'name': 'Influencers',       'icon': 'fa-podium', 'icon_text': ''},
    39: {'cat_id': 3,  'name': 'Language',          'icon': 'fa-language', 'icon_text': ''},
    40: {'cat_id': 12, 'name': 'Left',              'icon': 'fa-democrat', 'icon_text': ''},
    41: {'cat_id': 12, 'name': 'Libertarian',       'icon': 'fa-podium', 'icon_text': ''},
    42: {'cat_id': 1,  'name': 'Literature',        'icon': 'fa-book-open-cover', 'icon_text': ''},
    43: {'cat_id': 11, 'name': 'Local',             'icon': 'fa-podium', 'icon_text': ''},
    44: {'cat_id': 2,  'name': 'Management',        'icon': 'fa-sitemap', 'icon_text': ''},
    45: {'cat_id': 13, 'name': 'Mathematics',       'icon': 'fa-function', 'icon_text': ''},
    46: {'cat_id': 15, 'name': 'Mechanics',         'icon': 'fa-podium', 'icon_text': ''},
    47: {'cat_id': 8,  'name': 'Medical',           'icon': 'fa-podium', 'icon_text': ''},
    48: {'cat_id': 8,  'name': 'Mental Health',     'icon': 'fa-podium', 'icon_text': ''},
    49: {'cat_id': 1,  'name': 'Music',             'icon': 'fa-podium', 'icon_text': ''},
    50: {'cat_id': 13, 'name': 'Natural Sciences',  'icon': 'fa-podium', 'icon_text': ''},
    51: {'cat_id': 5,  'name': 'News',              'icon': 'fa-podium', 'icon_text': ''},
    31: {'cat_id': 6,  'name': 'News',              'icon': 'fa-trophy', 'icon_text': ''},
    52: {'cat_id': 15, 'name': 'News',              'icon': 'fa-podium', 'icon_text': ''},
    53: {'cat_id': 13, 'name': 'News',              'icon': 'fa-podium', 'icon_text': ''},
    54: {'cat_id': 12, 'name': 'News',              'icon': 'fa-podium', 'icon_text': ''},
    55: {'cat_id': 11, 'name': 'North America',     'icon': 'fa-podium', 'icon_text': ''},
    56: {'cat_id': 10, 'name': 'Offensive',         'icon': 'fa-podium', 'icon_text': ''},
    57: {'cat_id': 7,  'name': 'Outdoors',          'icon': 'fa-podium', 'icon_text': ''},
    58: {'cat_id': 6,  'name': 'PC',                'icon': 'fa-podium', 'icon_text': ''},
    59: {'cat_id': 14, 'name': 'Partner',           'icon': 'fa-podium', 'icon_text': ''},
    60: {'cat_id': 9,  'name': 'Personal Finance',  'icon': 'fa-podium', 'icon_text': ''},
    61: {'cat_id': 3,  'name': 'Philosophy',        'icon': 'fa-podium', 'icon_text': ''},
    62: {'cat_id': 1,  'name': 'Photography',       'icon': 'fa-podium', 'icon_text': ''},
    63: {'cat_id': 10, 'name': 'Political',         'icon': 'fa-podium', 'icon_text': ''},
    64: {'cat_id': 2,  'name': 'Product',           'icon': 'fa-podium', 'icon_text': ''},
    65: {'cat_id': 15, 'name': 'Programming',       'icon': 'fa-podium', 'icon_text': ''},
    66: {'cat_id': 6,  'name': 'Puzzle',            'icon': 'fa-podium', 'icon_text': ''},
    67: {'cat_id': 4,  'name': 'Q&A',               'icon': 'fa-podium', 'icon_text': ''},
    68: {'cat_id': 9,  'name': 'Relationships',     'icon': 'fa-podium', 'icon_text': ''},
    69: {'cat_id': 3,  'name': 'Religion',          'icon': 'fa-podium', 'icon_text': ''},
    70: {'cat_id': 12, 'name': 'Right',             'icon': 'fa-podium', 'icon_text': ''},
    71: {'cat_id': 4,  'name': f'{app.config["SITE_NAME"]} Meta', 'icon': 'fa-podium', 'icon_text': ''},
    72: {'cat_id': 1,  'name': 'Sculpture',         'icon': 'fa-podium', 'icon_text': ''},
    73: {'cat_id': 4,  'name': 'Serious',           'icon': 'fa-podium', 'icon_text': ''},
    74: {'cat_id': 7,  'name': 'Skills',            'icon': 'fa-podium', 'icon_text': ''},
    75: {'cat_id': 13, 'name': 'Soft Sciences',     'icon': 'fa-podium', 'icon_text': ''},
    76: {'cat_id': 15, 'name': 'Software',          'icon': 'fa-podium', 'icon_text': ''},
    77: {'cat_id': 13, 'name': 'Space',             'icon': 'fa-podium', 'icon_text': ''},
    78: {'cat_id': 2,  'name': 'Startups',          'icon': 'fa-podium', 'icon_text': ''},
    79: {'cat_id': 8,  'name': 'Support',           'icon': 'fa-podium', 'icon_text': ''},
    80: {'cat_id': 6,  'name': 'Tabletop',          'icon': 'fa-podium', 'icon_text': ''},
    81: {'cat_id': 14, 'name': 'Team',              'icon': 'fa-podium', 'icon_text': ''},
    82: {'cat_id': 1,  'name': 'Theater',           'icon': 'fa-podium', 'icon_text': ''},
    83: {'cat_id': 11, 'name': 'Upbeat',            'icon': 'fa-podium', 'icon_text': ''},
    84: {'cat_id': 1,  'name': 'Visual Arts',       'icon': 'fa-podium', 'icon_text': ''},
    85: {'cat_id': 10, 'name': 'Wholesome',         'icon': 'fa-podium', 'icon_text': ''},
    86: {'cat_id': 11, 'name': 'World',             'icon': 'fa-podium', 'icon_text': ''}
 }

CATEGORIES={x:Category(id=x) for x in CATEGORY_DATA}