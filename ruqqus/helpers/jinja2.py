import time
import json
from os import environ, path
from sqlalchemy import text, func
from flask import g
import calendar
import re
from urllib.parse import quote_plus

from ruqqus.classes.user import User
from .get import *
import requests

from ruqqus.__main__ import app, cache


post_regex = re.compile("^https?://[a-zA-Z0-9_.-]+/\+\w+/post/(\w+)(/[a-zA-Z0-9_-]+/?)?$")


@app.template_filter("total_users")
@cache.memoize(timeout=60)
def total_users(x):

    return db.query(User).filter_by(is_banned=0).count()


@app.template_filter("source_code")
@cache.memoize(timeout=60 * 60 * 24)
def source_code(file_name):

    return open(path.expanduser('~') + '/ruqqus/' +
                file_name, mode="r+").read()


@app.template_filter("full_link")
def full_link(url):

    return f"https://{app.config['SERVER_NAME']}{url}"


@app.template_filter("env")
def env_var_filter(x):

    x = environ.get(x, 1)

    try:
        return int(x)
    except BaseException:
        try:
            return float(x)
        except BaseException:
            return x


@app.template_filter("js_str_escape")
def js_str_escape(s):

    s = s.replace("'", r"\'")

    return s


@app.template_filter("is_mod")
@cache.memoize(60)
def jinja_is_mod(uid, bid):

    return bool(get_mod(uid, bid))

@app.template_filter("coin_goal")
@cache.cached(timeout=600, key_prefix="premium_coin_goal")
def coin_goal(x):
    
    now = time.gmtime()
    midnight_month_start = time.struct_time((now.tm_year,
                                              now.tm_mon,
                                              1,
                                              0,
                                              0,
                                              0,
                                              now.tm_wday,
                                              now.tm_yday,
                                              0)
                                             )
    cutoff = calendar.timegm(midnight_month_start)
    
    coins=g.db.query(func.sum(PayPalTxn.coin_count)).filter(
        PayPalTxn.created_utc>cutoff,
        PayPalTxn.status==3).all()[0][0] or 0
    
    
    return int(100*coins/500)


@app.template_filter("app_config")
def app_config(x):
    return app.config.get(x)

# @app.template_filter("eval")
# def eval_filter(s):

#     return render_template_string(s)

@app.template_filter("urlencode")
def urlencode(s):
    return quote_plus(s)


@app.template_filter("post_embed")
def crosspost_embed(url):

    matches = re.match(post_regex, url)

    b36id = matches.group(1)

    p = get_post(b36id, v=g.v, graceful=True)

    if not p or p.is_deleted or p.is_banned or not p.is_public:
        return ""

    return render_template(
        "submission_listing.html",
        listing=[p],
        v=g.v
        )

# @app.template_filter("general_chat_count")
# def general_chat_count(x):
#     return get_guild("general").chat_count


@app.template_filter("lines")
def lines_count(x):

    return x.count("\n")+1