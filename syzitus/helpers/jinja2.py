from time import struct_time, gmtime
from sqlalchemy import text, func
from flask import g, session
from calendar import timegm as calendar_timegm
from urllib.parse import quote_plus
from io import BytesIO
from qrcode import QRCode
from base64 import b64encode

from syzitus.classes.user import User
from .get import *
from .security import generate_hash

from syzitus.__main__ import app, cache

@app.template_filter("total_users")
@cache.memoize(timeout=60)
def total_users(x):

    return db.query(User).filter_by(is_banned=0).count()


@app.template_filter("source_code")
@cache.memoize(timeout=60 * 60 * 24)
def source_code(file_name):

    return open(f"./{file_name}", mode="r+").read()


@app.template_filter("full_link")
def full_link(url):

    return f"https://{app.config['SERVER_NAME']}{url}"


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
    
    now = gmtime()
    midnight_month_start = struct_time((now.tm_year,
                                              now.tm_mon,
                                              1,
                                              0,
                                              0,
                                              0,
                                              now.tm_wday,
                                              now.tm_yday,
                                              0)
                                             )
    cutoff = calendar_timegm(midnight_month_start)
    
    coins=g.db.query(func.sum(PayPalTxn.coin_count)).filter(
        PayPalTxn.created_utc>cutoff,
        PayPalTxn.status==3).all()[0][0] or 0
    
    
    return int(100*coins/15)


@app.template_filter("app_config")
def app_config(x):
    return app.config.get(x)


@app.template_filter("urlencode")
def urlencode(s):
    return quote_plus(s)


@app.template_filter("lines")
def lines_count(x):

    return x.count("\n")+1

@app.template_filter('qrcode_img_data')
def qrcode_filter(x):
  
    mem=BytesIO()
    qr=QRCode()
    qr.add_data(x)
    img=qr.make_image(
        fill_color=f"#{app.config['COLOR_PRIMARY']}",
        back_color="white",
    )
    img.save(
        mem, 
        format="PNG"
    )
    mem.seek(0)
    
    data=b64encode(mem.read()).decode('ascii')
    return f"data:image/png;base64,{data}"


@app.template_filter("formkey")
def logged_out_formkey(t):
    return generate_hash(f"{t}+{session['session_id']}")

@app.template_filter("event_score")
@cache.memoize(600)
def event_faction_score(x):

    guilds=[
        "Team_Halloween",
        "Team_Christmas"
        ]

    guild=get_guild(x)

    modulo=guilds.index(x)

    post_karma = (g.db.query(func.sum(Submission.score_top)).filter(
        Submission.board_id==guild.id,
        Submission.author_id.op('%')(2)==modulo
        ).scalar() or 0) -(
        g.db.query(Submission).filter(
            Submission.board_id==guild.id,
            Submission.author_id.op('%')(2)==modulo
            ).count()
        )

    comment_karma=(g.db.query(func.sum(Comment.score_top)).filter(
        Comment.parent_submission.in_(
            select(Submission.id).filter(
                Submission.board_id==guild.id,
                )
            ),
        Comment.author_id.op('%')(2)==modulo
        ).scalar() or 0) - (
        g.db.query(Comment).filter(
        Comment.parent_submission.in_(
            select(Submission.id).filter(
                Submission.board_id==guild.id
                )
            ),
        Comment.author_id.op('%')(2)==modulo
        ).count()
        )

    return int(post_karma+comment_karma)