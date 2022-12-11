from syzitus.helpers.base36 import base36encode
from syzitus.helpers.lazy import lazy
from flask import g
from math import floor, ceil
from random import randint
import time

from syzitus.__main__ import cache, app


class Stndrd:

    @property
    @lazy
    def base36id(self):
        return base36encode(self.id)

    @property
    @lazy
    def created_date(self):
        return time.strftime("%d %B %Y", time.gmtime(self.created_utc))

    @property
    @lazy
    def created_datetime(self):
        return time.strftime("%d %B %Y at %H:%M:%S",
                             time.gmtime(self.created_utc))

    @property
    @lazy
    def created_iso(self):

        t = time.gmtime(self.created_utc)
        return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", t)

    @property
    def permalink_full(self):
        return f"http{'s' if app['FORCE_HTTPS'] else ''}://{app['SERVER_NAME']}{self.permalink}"
    


class Age_times:

    @property
    def age(self):

        now = g.timestamp

        return now - self.created_utc

    @property
    def created_date(self):

        return time.strftime("%d %b %Y", time.gmtime(self.created_utc))

    @property
    def created_datetime(self):

        return time.strftime("%d %b %Y at %H:%M:%S",
                             time.gmtime(self.created_utc))

    @property
    def age_string(self):

        age = self.age

        if age < 60:
            return "just now"
        elif age < 3600:
            minutes = int(age / 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        elif age < 86400:
            hours = int(age / 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif age < 2678400:
            days = int(age / 86400)
            return f"{days} day{'s' if days > 1 else ''} ago"

        now = time.gmtime()
        ctd = time.gmtime(self.created_utc)

        # compute number of months
        months = now.tm_mon - ctd.tm_mon + 12 * (now.tm_year - ctd.tm_year)
        # remove a month count if current day of month < creation day of month
        if now.tm_mday < ctd.tm_mday:
            months -= 1

        if months < 12:
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = int(months / 12)
            return f"{years} year{'s' if years > 1 else ''} ago"

    @property
    def edited_string(self):

        if not self.edited_utc:
            return "never"

        age = int(time.time()) - self.edited_utc

        if age < 60:
            return "just now"
        elif age < 3600:
            minutes = int(age / 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        elif age < 86400:
            hours = int(age / 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif age < 2678400:
            days = int(age / 86400)
            return f"{days} day{'s' if days > 1 else ''} ago"

        now = time.gmtime()
        ctd = time.gmtime(self.edited_utc)
        months = now.tm_mon - ctd.tm_mon + 12 * (now.tm_year - ctd.tm_year)

        if months < 12:
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = now.tm_year - ctd.tm_year
            return f"{years} year{'s' if years > 1 else ''} ago"

    @property
    def edited_date(self):
        return time.strftime("%d %B %Y", time.gmtime(self.edited_utc))

    @property
    def edited_datetime(self):
        return time.strftime("%d %B %Y at %H:%M:%S",
                             time.gmtime(self.edited_utc))
    
    @property
    @lazy
    def age_years(self):
        
        now=time.gmtime()
        ctd=time.gmtime(self.created_utc)
        
        years = now.tm_year - ctd.tm_year
        
        if now.tm_yday < ctd.tm_yday:
            years-=1
            
        return years


class Scores:

    @property
    #@cache.memoize(timeout=60)
    def score_percent(self):
        # try:
        # return int((self.ups/(self.ups+self.downs))*100)
        # except ZeroDivisionError:
        # return 0

        return 101

    @property
    #@cache.memoize(timeout=60)
    def score(self):
        return int(self.score_top) or 0


class Fuzzing:

    @property
    #@cache.memoize(timeout=60)
    def score_fuzzed(self):

        real = self.score_top if self.score_top else self.score
        real = int(real)
        if real <= 10:
            return real

        k = 0.01

        a = floor(real * (1 - k))
        b = ceil(real * (1 + k))
        return randint(a, b)

    @property
    def upvotes_fuzzed(self):

        if self.upvotes <= 10 or self.is_archived:
            return self.upvotes

        lower = int(self.upvotes * 0.99)
        upper = int(self.upvotes * 1.01) + 1

        return randint(lower, upper)

    @property
    def downvotes_fuzzed(self):
        if self.downvotes <= 10 or self.is_archived:
            return self.downvotes

        lower = int(self.downvotes * 0.99)
        upper = int(self.downvotes * 1.01) + 1

        return randint(lower, upper)
