from urllib.parse import urlparse
from calendar import timegm as calendar_timegm
from sqlalchemy import func, or_
from sqlalchemy.orm import lazyload, contains_eager, load_only
from imagehash import phash
from os import remove
from PIL import Image as IMAGE
import threading
from jinja2.exceptions import TemplateNotFound
from flask import g, session, abort, render_template, jsonify, redirect
import mistletoe

from syzitus.helpers.wrappers import *
from syzitus.helpers.alerts import send_notification
from syzitus.helpers.sanitize import *
from syzitus.helpers.get import *
from syzitus.classes import *
from syzitus.classes.domains import reasons as REASONS
from syzitus.classes.badges import BADGE_DEFS
from syzitus.helpers.aws import delete_file
from syzitus.helpers.alerts import send_notification
from syzitus.helpers.markdown import *
from syzitus.helpers.security import *
from syzitus.helpers.discord import discord_log_event

#from syzitus.routes.admin_api import user_stat_data
from syzitus.classes.categories import CATEGORIES

import time

import syzitus.helpers.aws as aws
from syzitus.__main__ import app, cache, debug


@app.route("/admin/flagged/posts", methods=["GET"])
@admin_level_required(3)
def flagged_posts():

    page = max(1, int(request.args.get("page", 1)))

    posts = g.db.query(Submission).options(load_only(Submission.id)).filter(
        or_(
            Submission.is_approved.is_(None),
            Submission.is_approved==0
            ),
        Submission.purged_utc==0,
        Submission.is_banned==False
    ).join(
        Submission.flags
    ).options(
        contains_eager(Submission.flags)
    ).order_by(
        Submission.id.desc()
    ).offset(25 * (page - 1)).limit(26)

    listing = [p.id for p in posts]
    next_exists = (len(listing) == 26)
    listing = listing[0:25]

    listing = get_posts(listing)

    return render_template("admin/flagged_posts.html",
                           next_exists=next_exists, listing=listing, page=page)


@app.get("/admin/all")
@admin_level_required(3)
def admin_all_posts():

    page = int(request.args.get('page', 1))
    post_ids = g.db.query(Submission).options(load_only(Submission.id)
        ).order_by(Submission.id.desc()).offset(25*(page-1)).limit(26)

    post_ids = [x.id for x in post_ids]
    next_exists = (len(post_ids) == 26)
    post_ids = post_ids[0:25]

    posts = get_posts(post_ids)

    return render_template(
        "home.html",
        listing=posts,
        next_exists=next_exists,
        page=page,
        sort_method="new"
        )

@app.route("/admin/image_posts", methods=["GET"])
@admin_level_required(3)
def image_posts_listing():

    page = int(request.args.get('page', 1))

    post_ids = g.db.query(Submission).options(load_only(Submission.id)
        ).filter_by(domain_ref=1).order_by(Submission.id.desc()
        ).offset(25 * (page - 1)
        ).limit(26)

    post_ids = [x.id for x in post_ids]
    next_exists = (len(post_ids) == 26)
    post_ids = post_ids[0:25]

    posts = get_posts(post_ids)

    return render_template(
        "admin/image_posts.html",
        listing=posts,
        next_exists=next_exists,
        page=page,
        sort_method="new"
        )


@app.route("/admin/flagged/comments", methods=["GET"])
@admin_level_required(3)
def flagged_comments():

    page = max(1, int(request.args.get("page", 1)))

    posts = g.db.query(
        Comment
        ).filter_by(
        is_approved=0,
        purged_utc=0,
        is_banned=False
        ).filter(
        Comment.parent_submission != None
    ).join(Comment.flags).options(
    load_only(Comment.id),
    contains_eager(Comment.flags)
    ).order_by(Comment.id.desc()).offset(25 * (page - 1)).limit(26).all()

    listing = [p.id for p in posts]
    next_exists = (len(listing) == 26)
    listing = listing[0:25]

    listing = get_comments(listing)

    return render_template("admin/flagged_comments.html",
                           next_exists=next_exists,
                           listing=listing,
                           page=page,
                           standalone=True)

@app.route("/admin/all/comments", methods=["GET"])
@admin_level_required(3)
def admin_all_comments():

    page = max(1, int(request.args.get("page", 1)))

    posts = g.db.query(
        Comment
        ).options(load_only(Comment.id)
        ).filter(
        Comment.parent_submission != None
        ).order_by(
        Comment.id.desc()
        ).offset(25 * (page - 1)).limit(26).all()

    listing = [p.id for p in posts]
    next_exists = (len(listing) == 26)
    listing = listing[0:25]

    listing = get_comments(listing)

    return render_template("home_comments.html",
                           next_exists=next_exists,
                           comments=listing,
                           page=page,
                           standalone=True
                           )

# @app.route("/admin/<path>", methods=["GET"])
# @admin_level_required(3):
# def admin_path():
# try:
# return render_template(safe_join("admin", path+".html"))
# except jinja2.exceptions.TemplateNotFound:
# abort(404)

@app.route("/admin", methods=["GET"])
@admin_level_required(3)
def admin_home():
    return render_template("admin/admin_home.html")


@app.route("/admin/badge_grant", methods=["GET"])
@admin_level_required(4)
def badge_grant_get():

    badge_types = [x for x in BADGE_DEFS.values()]

    errors = {"already_owned": "That user already has that badge.",
              "no_user": "That user doesn't exist."
              }

    return render_template("admin/badge_grant.html",
                           badge_types=badge_types,
                           error=errors.get(
                               request.args.get("error"),
                               None) if request.args.get('error') else None,
                           msg="Badge successfully assigned" if request.args.get(
                               "msg") else None
                           )


@app.route("/badge_grant", methods=["POST"])
@admin_level_required(4)
def badge_grant_post():

    user = get_user(request.form.get("username"), graceful=True)
    if not user:
        return redirect("/badge_grant?error=no_user")

    badge_id = int(request.form.get("badge_id"))

    if user.has_badge(badge_id):
        return redirect("/badge_grant?error=already_owned")

    badge = BADGE_DEFS[badge_id]
    if badge.kind != 2:
        abort(403)

    new_badge = Badge(badge_id=badge_id,
                      user_id=user.id,
                      created_utc=g.timestamp
                      )

    desc = request.form.get("description")
    if desc:
        new_badge.description = desc

    url = request.form.get("url")
    if url:
        new_badge.url = url

    g.db.add(new_badge)

    g.db.commit()
    cache.delete_memoized(User.badges_function, user)

    text = f"""
@{g.user.username} has given you the following profile badge:
\n\n![]({new_badge.path})
\n\n{new_badge.name}
"""

    send_notification(user, text)

    return redirect(user.permalink)


@app.route("/admin/users", methods=["GET"])
@admin_level_required(2)
def users_list():

    page = int(request.args.get("page", 1))

    users = g.db.query(User)
    
    show_all=int(request.args.get('all','0'))
    
    if not show_all:
        users=users.filter(
            or_(
                User.is_banned==0,
                User.unban_utc>0
                ),
             User.is_deleted==False
             )
        
    users=users.order_by(User.created_utc.desc()).offset(25 * (page - 1)).limit(26)

    users = [x for x in users]

    next_exists = (len(users) == 26)
    users = users[0:25]

    return render_template("admin/new_users.html",
                           users=users,
                           next_exists=next_exists,
                           page=page,
                           show_all=show_all
                           )

# @app.route("/admin/data", methods=["GET"])
# @admin_level_required(2)
# def admin_data():

#     data = user_stat_data().get_json()

#     return render_template("admin/new_users.html",
#                            next_exists=False,
#                            page=1,
#                            single_plot=data['single_plot'],
#                            multi_plot=data['multi_plot']
#                            )


@app.route("/admin/content_stats", methods=["GET"])
@admin_level_required(2)
def participation_stats():

    if 'year' in request.args:
        now = time.gmtime(g.timestamp)
        target_year = int(request.args['year'])
        midnight_year_start = time.struct_time(
            (
                target_year,
                1,
                1,
                0,
                0,
                0,
                now.tm_wday,
                now.tm_yday,
                0
                )
            )
        cutoff_start = calendar_timegm(midnight_year_start)

        midnight_year_end = time.struct_time(
            (
                target_year + 1,
                1,
                1,
                0,
                0,
                0,
                now.tm_wday,
                now.tm_yday,
                0
                )
            )
        cutoff_end = calendar_timegm(midnight_year_end)
    else:
        cutoff_start = 0
        cutoff_end = g.timestamp

    archive_cutoff = g.timestamp - 60*60*24*180

    data = {"valid_users": g.db.query(User).filter_by(is_deleted=False).filter(User.created_utc > cutoff_start, User.created_utc < cutoff_end, or_(User.is_banned == 0, and_(User.is_banned > 0, User.unban_utc > 0))).count(),
            "private_users": g.db.query(User).filter_by(is_deleted=False, is_private=False).filter(User.created_utc > cutoff_start, User.created_utc < cutoff_end, User.is_banned > 0, or_(User.unban_utc > g.timestamp, User.unban_utc == 0)).count(),
            "total_banned_users": g.db.query(User).filter(User.created_utc > cutoff_start, User.created_utc < cutoff_end, User.is_banned > 0, User.unban_utc == 0).count(),
            "auto_banned_users": g.db.query(User).filter(User.created_utc > cutoff_start, User.created_utc < cutoff_end, User.is_banned > 0, User.unban_utc == 0, User.is_banned == 1).count(),
            "manual_banned_users": g.db.query(User).filter(User.created_utc > cutoff_start, User.created_utc < cutoff_end, User.is_banned > 0, User.unban_utc == 0, User.is_banned != 1).count(),
            "deleted_users": g.db.query(User).filter_by(is_deleted=True).filter(User.created_utc > cutoff_start, User.created_utc < cutoff_end).count(),
            "locked_negative_users": g.db.query(User).filter(User.created_utc > cutoff_start, User.created_utc < cutoff_end, User.negative_balance_cents>0).count(),
            "total_posts": g.db.query(Submission).filter(Submission.created_utc > cutoff_start, Submission.created_utc < cutoff_end).count(),
            "active_posts": g.db.query(Submission).filter_by(is_banned=False).filter(Submission.created_utc > cutoff_start, Submission.created_utc < cutoff_end, Submission.deleted_utc == 0, Submission.created_utc > archive_cutoff).count(),
            "archived_posts":g.db.query(Submission).filter_by(is_banned=False).filter(Submission.created_utc > cutoff_start, Submission.created_utc < cutoff_end, Submission.deleted_utc == 0, Submission.created_utc < archive_cutoff).count(),
            "posting_users": g.db.query(Submission.author_id).filter(Submission.created_utc > cutoff_start, Submission.created_utc < cutoff_end).distinct().count(),
            "listed_posts": g.db.query(Submission).filter_by(is_banned=False).filter(Submission.created_utc > cutoff_start, Submission.created_utc < cutoff_end, Submission.deleted_utc == 0).count(),
            "removed_posts": g.db.query(Submission).filter_by(is_banned=True).filter(Submission.created_utc > cutoff_start, Submission.created_utc < cutoff_end).count(),
            "deleted_posts": g.db.query(Submission).filter_by(is_banned=False).filter(Submission.created_utc > cutoff_start, Submission.created_utc < cutoff_end, Submission.deleted_utc > 0).count(),
            "total_comments":       g.db.query(Comment).join(Comment.post).filter(Comment.created_utc > cutoff_start, Comment.created_utc < cutoff_end).count(),
            "active_comments":      g.db.query(Comment).join(Comment.post).filter(Comment.created_utc > cutoff_start, Comment.created_utc < cutoff_end, Comment.is_banned==False, Comment.deleted_utc==0, Submission.created_utc>archive_cutoff).count(),
            "archived_comments":    g.db.query(Comment).join(Comment.post).filter(Comment.created_utc > cutoff_start, Comment.created_utc < cutoff_end, Comment.is_banned==False, Comment.deleted_utc==0, Submission.created_utc<archive_cutoff).count(),
            "commenting_users": g.db.query(Comment.author_id).filter(Comment.created_utc > cutoff_start, Comment.created_utc < cutoff_end).distinct().count(),
            "removed_comments": g.db.query(Comment).filter_by(is_banned=True).filter(Comment.created_utc > cutoff_start, Comment.created_utc < cutoff_end).count(),
            "deleted_comments": g.db.query(Comment).filter(Comment.created_utc > cutoff_start, Comment.created_utc < cutoff_end, Comment.deleted_utc>0).count(),
            "total_guilds": g.db.query(Board).filter(Board.created_utc > cutoff_start, Board.created_utc < cutoff_end).count(),
            "listed_guilds": g.db.query(Board).filter_by(is_banned=False, is_private=False).filter(Board.created_utc > cutoff_start, Board.created_utc < cutoff_end).count(),
            "private_guilds": g.db.query(Board).filter_by(is_banned=False, is_private=True).filter(Board.created_utc > cutoff_start, Board.created_utc < cutoff_end).count(),
            "banned_guilds": g.db.query(Board).filter_by(is_banned=True).filter(Board.created_utc > cutoff_start, Board.created_utc < cutoff_end).count(),
            "guilds_removed_from_all": g.db.query(Board).filter_by(is_banned=False, all_opt_out=True, is_locked_category=True).filter(Board.created_utc > cutoff_start, Board.created_utc < cutoff_end).count(),
            "guilds_locked_nsfw": g.db.query(Board).filter_by(is_banned=False, over_18=True, is_locked_category=True).filter(Board.created_utc > cutoff_start, Board.created_utc < cutoff_end).count(),
            "total_guilds_locked_settings": g.db.query(Board).filter_by(is_banned=False, is_locked_category=True).filter(Board.created_utc > cutoff_start, Board.created_utc < cutoff_end).count(),
            "post_votes": g.db.query(Vote).filter(Vote.created_utc > cutoff_start, Vote.created_utc < cutoff_end).count(),
            "post_voting_users": g.db.query(Vote.user_id).filter(Vote.created_utc > cutoff_start, Vote.created_utc < cutoff_end).distinct().count(),
            "comment_votes": g.db.query(CommentVote).filter(CommentVote.created_utc > cutoff_start, CommentVote.created_utc < cutoff_end).count(),
            "comment_voting_users": g.db.query(CommentVote.user_id).filter(CommentVote.created_utc > cutoff_start, CommentVote.created_utc < cutoff_end).distinct().count()
            }

    #data = {x: f"{data[x]:,}" for x in data}

    return render_template("admin/content_stats.html", title="Content Statistics", data=data)


@app.route("/admin/money", methods=["GET"])
@admin_level_required(2)
def money_stats():

    now = time.gmtime(g.timestamp)
    midnight_year_start = time.struct_time(
        (
            now.tm_year,
            1,
            1,
            0,
            0,
            0,
            now.tm_wday,
            now.tm_yday,
            0
            )
        )
    midnight_year_start = calendar_timegm(midnight_year_start)

    
    intake=sum([int(x[0] - (x[0] * 0.029) - 30 )  for x in g.db.query(PayPalTxn.usd_cents).filter(PayPalTxn.status==3, PayPalTxn.created_utc>midnight_year_start).all()])
    loss=sum([x[0] for x in g.db.query(PayPalTxn.usd_cents).filter(PayPalTxn.status<0, PayPalTxn.created_utc>midnight_year_start).all()])
    revenue=str(intake-loss)

    data={
        "cents_received_last_24h":g.db.query(func.sum(PayPalTxn.usd_cents)).filter(PayPalTxn.status==3, PayPalTxn.created_utc>g.timestamp-60*60*24).scalar(),
        "cents_received_last_week":g.db.query(func.sum(PayPalTxn.usd_cents)).filter(PayPalTxn.status==3, PayPalTxn.created_utc>g.timestamp-60*60*24*7).scalar(),
        "sales_count_last_24h":g.db.query(PayPalTxn).filter(PayPalTxn.status==3, PayPalTxn.created_utc>g.timestamp-60*60*24).count(),
        "sales_count_last_week":g.db.query(PayPalTxn).filter(PayPalTxn.status==3, PayPalTxn.created_utc>g.timestamp-60*60*24*7).count(),
        "receivables_outstanding_cents": g.db.query(func.sum(User.negative_balance_cents)).filter(User.is_deleted==False, or_(User.is_banned == 0, and_(User.is_banned > 0, User.unban_utc > 0))).scalar(),
        "cents_written_off":g.db.query(func.sum(User.negative_balance_cents)).filter(or_(User.is_deleted==True, User.unban_utc > 0)).scalar(),
        "coins_redeemed_last_24_hrs": g.db.query(User).filter(User.premium_expires_utc>g.timestamp+60*60*24*6, User.premium_expires_utc < now+60*60*24*7).count(),
        "coins_redeemed_last_week": g.db.query(User).filter(User.premium_expires_utc>g.timestamp, User.premium_expires_utc < now+60*60*24*7).count(),
        "coins_in_circulation": g.db.query(func.sum(User.coin_balance)).filter(User.is_deleted==False, or_(User.is_banned==0, and_(User.is_banned>0, User.unban_utc>0))).scalar(),
        "coins_vanished": g.db.query(func.sum(User.coin_balance)).filter(or_(User.is_deleted==True, and_(User.is_banned>0, User.unban_utc==0))).scalar(),
        "receivables_outstanding_cents": g.db.query(func.sum(User.negative_balance_cents)).filter(User.is_deleted==False, or_(User.is_banned == 0, and_(User.is_banned > 0, User.unban_utc > 0))).scalar(),
        "coins_sold_ytd":g.db.query(func.sum(PayPalTxn.coin_count)).filter(PayPalTxn.status==3, PayPalTxn.created_utc>midnight_year_start).scalar(),
        "revenue_usd_ytd":f"{revenue[0:-2]}.{revenue[-2:]}"
    }
    return render_template("admin/content_stats.html", title="Financial Statistics", data=data)


@app.route("/admin/vote_info", methods=["GET"])
@admin_level_required(4)
def admin_vote_info_get():

    if not request.args.get("link"):
        return render_template("admin/votes.html")

    thing = get_from_permalink(request.args.get("link"))

    if isinstance(thing, Submission):

        ups = g.db.query(Vote
                         ).options(joinedload(Vote.user)
                                   ).filter_by(submission_id=thing.id, vote_type=1
                                               ).order_by(Vote.creation_ip.asc()
                                                          ).all()

        downs = g.db.query(Vote
                           ).options(joinedload(Vote.user)
                                     ).filter_by(submission_id=thing.id, vote_type=-1
                                                 ).order_by(Vote.creation_ip.asc()
                                                            ).all()

    elif isinstance(thing, Comment):

        ups = g.db.query(CommentVote
                         ).options(joinedload(CommentVote.user)
                                   ).filter_by(comment_id=thing.id, vote_type=1
                                               ).order_by(CommentVote.creation_ip.asc()
                                                          ).all()

        downs = g.db.query(CommentVote
                           ).options(joinedload(CommentVote.user)
                                     ).filter_by(comment_id=thing.id, vote_type=-1
                                                 ).order_by(CommentVote.creation_ip.asc()
                                                            ).all()

    else:
        abort(400)

    return render_template("admin/votes.html",
                           thing=thing,
                           ups=ups,
                           downs=downs)


@app.route("/admin/alt_votes", methods=["GET"])
@admin_level_required(4)
def alt_votes_get():

    if not request.args.get("u1") or not request.args.get("u2"):
        return render_template("admin/alt_votes.html")

    u1 = request.args.get("u1")
    u2 = request.args.get("u2")

    if not u1 or not u2:
        return redirect("/admin/alt_votes")

    u1 = get_user(u1)
    u2 = get_user(u2)

    u1_post_ups = g.db.query(
        Vote.submission_id).filter_by(
        user_id=u1.id,
        vote_type=1).all()
    u1_post_downs = g.db.query(
        Vote.submission_id).filter_by(
        user_id=u1.id,
        vote_type=-1).all()
    u1_comment_ups = g.db.query(
        CommentVote.comment_id).filter_by(
        user_id=u1.id,
        vote_type=1).all()
    u1_comment_downs = g.db.query(
        CommentVote.comment_id).filter_by(
        user_id=u1.id,
        vote_type=-1).all()
    u2_post_ups = g.db.query(
        Vote.submission_id).filter_by(
        user_id=u2.id,
        vote_type=1).all()
    u2_post_downs = g.db.query(
        Vote.submission_id).filter_by(
        user_id=u2.id,
        vote_type=-1).all()
    u2_comment_ups = g.db.query(
        CommentVote.comment_id).filter_by(
        user_id=u2.id,
        vote_type=1).all()
    u2_comment_downs = g.db.query(
        CommentVote.comment_id).filter_by(
        user_id=u2.id,
        vote_type=-1).all()

    data = {}
    data['u1_only_post_ups'] = len(
        [x for x in u1_post_ups if x not in u2_post_ups])
    data['u2_only_post_ups'] = len(
        [x for x in u2_post_ups if x not in u1_post_ups])
    data['both_post_ups'] = len(list(set(u1_post_ups) & set(u2_post_ups)))

    data['u1_only_post_downs'] = len(
        [x for x in u1_post_downs if x not in u2_post_downs])
    data['u2_only_post_downs'] = len(
        [x for x in u2_post_downs if x not in u1_post_downs])
    data['both_post_downs'] = len(
        list(set(u1_post_downs) & set(u2_post_downs)))

    data['u1_only_comment_ups'] = len(
        [x for x in u1_comment_ups if x not in u2_comment_ups])
    data['u2_only_comment_ups'] = len(
        [x for x in u2_comment_ups if x not in u1_comment_ups])
    data['both_comment_ups'] = len(
        list(set(u1_comment_ups) & set(u2_comment_ups)))

    data['u1_only_comment_downs'] = len(
        [x for x in u1_comment_downs if x not in u2_comment_downs])
    data['u2_only_comment_downs'] = len(
        [x for x in u2_comment_downs if x not in u1_comment_downs])
    data['both_comment_downs'] = len(
        list(set(u1_comment_downs) & set(u2_comment_downs)))

    data['u1_post_ups_unique'] = 100 * \
        data['u1_only_post_ups'] // len(u1_post_ups) if u1_post_ups else 0
    data['u2_post_ups_unique'] = 100 * \
        data['u2_only_post_ups'] // len(u2_post_ups) if u2_post_ups else 0
    data['u1_post_downs_unique'] = 100 * \
        data['u1_only_post_downs'] // len(
            u1_post_downs) if u1_post_downs else 0
    data['u2_post_downs_unique'] = 100 * \
        data['u2_only_post_downs'] // len(
            u2_post_downs) if u2_post_downs else 0

    data['u1_comment_ups_unique'] = 100 * \
        data['u1_only_comment_ups'] // len(
            u1_comment_ups) if u1_comment_ups else 0
    data['u2_comment_ups_unique'] = 100 * \
        data['u2_only_comment_ups'] // len(
            u2_comment_ups) if u2_comment_ups else 0
    data['u1_comment_downs_unique'] = 100 * \
        data['u1_only_comment_downs'] // len(
            u1_comment_downs) if u1_comment_downs else 0
    data['u2_comment_downs_unique'] = 100 * \
        data['u2_only_comment_downs'] // len(
            u2_comment_downs) if u2_comment_downs else 0

    return render_template("admin/alt_votes.html",
                           u1=u1,
                           u2=u2,
                           data=data
                           )


@app.route("/admin/link_accounts", methods=["POST"])
@admin_level_required(4)
def admin_link_accounts():

    u1 = int(request.form.get("u1"))
    u2 = int(request.form.get("u2"))

    new_alt = Alt(
        user1=u1, 
        user2=u2,
        is_manual=True
        )

    g.db.add(new_alt)
    g.db.commit()

    return redirect(f"/admin/alt_votes?u1={g.db.query(User).get(u1).username}&u2={g.db.query(User).get(u2).username}")


@app.route("/admin/<pagename>", methods=["GET"])
@admin_level_required(3)
def admin_tools(pagename):
    try:
        return render_template(f"admin/{pagename}.html")
    except TemplateNotFound:
        abort(404)

@app.route("/admin/removed", methods=["GET"])
@admin_level_required(3)
def admin_removed():

    page = int(request.args.get("page", 1))

    ids = g.db.query(Submission.id).options(lazyload('*')).filter_by(is_banned=True).order_by(
        Submission.id.desc()).offset(25 * (page - 1)).limit(26).all()

    ids=[x[0] for x in ids]

    next_exists = len(ids) == 26

    ids = ids[0:25]

    posts = get_posts(ids)

    return render_template("admin/removed_posts.html",
                           listing=posts,
                           page=page,
                           next_exists=next_exists
                           )

@app.route("/admin/gm", methods=["GET"])
@admin_level_required(3)
def admin_gm():
    
    username=request.args.get("user")

    include_banned=int(request.args.get("with_banned",0))

    if username:
        user=get_user(username)
        
        boards=user.boards_modded

        alts=user.alts
        main=user
        main_count=user.submissions.count() + user.comments.count()
        for alt in alts:

            if not alt.is_valid and not include_banned:
                continue

            count = alt.submissions.count() + alt.comments.count()
            if count > main_count:
                main_count=count
                main=alt

            for b in alt.boards_modded:
                if b not in boards:
                    boards.append(b)

           
        return render_template("admin/alt_gms.html",
            user=user,
            first=main,
            boards=boards
            )
    else:
        return render_template("admin/alt_gms.html")
    


@app.route("/admin/appdata", methods=["GET"])
@admin_level_required(4)
def admin_appdata():

    url=request.args.get("link")

    if url:

        thing = get_from_permalink(url)

        return render_template(
            "admin/app_data.html",
            thing=thing
            )

    else:
        return render_template("admin/app_data.html")

@app.route("/admin/ban_analysis")
@admin_level_required(3)
def admin_ban_analysis():

    banned_accounts = g.db.query(User).filter(User.is_banned>0, User.unban_utc==0).all()

    uniques=set()

    seen_so_far=set()

    for user in banned_accounts:


        if user.id not in seen_so_far:

            print(f"Unique - @{user.username}")

            uniques.add(user.id)

        else:
            print(f"Repeat - @{user.username}")
            continue

        alts=user.alts
        print(f"{len(alts)} alts")

        for alt in user.alts:
            seen_so_far.add(alt.id)


    return str(len(uniques))


@app.route("/admin/paypaltxns", methods=["GET"])
@admin_level_required(4)
def admin_paypaltxns():

    page=int(request.args.get("page",1))
    user=request.args.get('user','')

    txns = g.db.query(PayPalTxn).filter(PayPalTxn.status!=1)

    if user:
        user=get_user(user)
        txns=txns.filter_by(user_id=user.id)


    txns=txns.order_by(PayPalTxn.created_utc.desc())

    txns = [x for x in txns.offset(100*(page-1)).limit(101).all()]

    next_exists=len(txns)==101
    txns=txns[0:100]

    return render_template(
        "single_txn.html", 
        txns=txns, 
        next_exists=next_exists,
        page=page
        )

@app.route("/admin/domain/<domain_name>", methods=["GET"])
@admin_level_required(4)
def admin_domain_domain(domain_name):

    d_query=domain_name.replace("_","\_")
    domain=g.db.query(Domain).filter_by(domain=d_query).first()

    if not domain:
        domain=Domain(domain=domain_name)

    return render_template(
        "admin/manage_domain.html",
        domain_name=domain_name,
        domain=domain,
        reasons=REASONS
        )

@app.route("/admin/category", methods=["POST"])
@admin_level_required(4)
def admin_category_lock():

    board=get_guild(request.form.get("board"))

    cat_id=int(request.form.get("category"))

    sc=g.db.query(SubCategory).filter_by(id=cat_id).first()
    if not sc:
        abort(400)

    board.subcat_id=cat_id
    lock=bool(request.form.get("lock"))

    g.db.add(board)

    ma1=ModAction(
        board_id=board.id,
        user_id=g.user.id,
        kind="update_settings",
        note=f"category={sc.category.name} / {sc.name} | admin action"
        )
    g.db.add(ma1)

    if lock != board.is_locked_category:
        board.is_locked_category = lock
        ma2=ModAction(
            board_id=board.id,
            user_id=g.user.id,
            kind="update_settings",
            note=f"category_locked={lock} | admin action"
            )
        g.db.add(ma2)

    return redirect(f"{board.permalink}/mod/log")

@app.route("/admin/user_data/<username>", methods=["GET"])
@admin_level_required(5)
def admin_user_data_get(username, v):

    user=get_user(username, graceful=True)

    if not user:
        return render_template("admin/user_data.html")

    post_ids = [x[0] for x in g.db.query(Submission.id).filter_by(author_id=user.id).order_by(Submission.created_utc.desc()).all()]
    posts=get_posts(post_ids)

    comment_ids=[x[0] for x in g.db.query(Comment.id).filter_by(author_id=user.id).order_by(Comment.created_utc.desc()).all()]
    comments=get_comments(comment_ids)



    return jsonify(
        {
        "submissions":[x.json_admin for x in posts],
        "comments":[x.json_admin for x in comments],
        "user":user.json_admin
            }
        )

@app.route("/admin/account_data/<username>", methods=["GET"])
@admin_level_required(5)
def admin_account_data_get(username, v):

    user=get_user(username, graceful=True)

    if not user:
        return render_template("admin/user_data.html")

    return jsonify(
        {
        "user":user.json_admin
            }
        )

@app.route("/admin/image_purge", methods=["POST"])
@admin_level_required(5)
def admin_image_purge():
    
    url=request.form.get("url")

    parsed_url=urlparse(url)

    name=parsed_url.path.lstrip('/')

    try:
        print(name)
    except:
        pass


    aws.delete_file(name)

    return redirect("/admin/image_purge")


@app.route("/admin/ip/<ipaddr>", methods=["GET"])
@admin_level_required(5)
def admin_ip_addr(ipaddr):

    pids=[x.id for x in g.db.query(Submission).filter_by(creation_ip=ipaddr).order_by(Submission.created_utc.desc()).all()]

    cids=[x.id for x in g.db.query(Comment).filter(Comment.creation_ip==ipaddr, Comment.parent_submission!=None).order_by(Comment.created_utc.desc()).all()]

    ip_record=g.db.query(IP).filter_by(addr=ipaddr).first()

    return render_template(
        "admin/ip.html",
        users=g.db.query(User).filter_by(creation_ip=ipaddr).order_by(User.created_utc.desc()).all(),
        listing=get_posts(pids) if pids else [],
        comments=get_comments(cids) if cids else [],
        standalone=True,
        ip=ipaddr,
        ip_record=ip_record
        )

@app.route("/admin/test", methods=["GET"])
@admin_level_required(5)
def admin_test_ip():

    return f"IP: {request.remote_addr}; fwd: {request.headers.get('X-Forwarded-For')}"


@app.route("/admin/siege_count")
@admin_level_required(3)
def admin_siege_count():

    board=get_guild(request.args.get("board"))
    recent=int(request.args.get("days",0))

    now=g.timestamp

    cutoff=board.stored_subscriber_count//10 + min(recent, (now-board.created_utc)//(60*60*24))

    uids=g.db.query(Subscription.user_id).filter_by(is_active=True, board_id=board.id).all()
    uids=[x[0] for x in uids]

    can_siege=0
    total=0
    for uid in uids:
        posts=sum([x[0] for x in g.db.query(Submission.score_top).options(lazyload('*')).filter_by(author_id=uid).filter(Submission.created_utc>g.timestamp-60*60*24*recent).all()])
        comments=sum([x[0] for x in g.db.query(Comment.score_top).options(lazyload('*')).filter_by(author_id=uid).filter(   Comment.created_utc>g.timestamp-60*60*24*recent).all()])
        rep=posts+comments
        if rep>=cutoff:
            can_siege+=1
        total+=1
        print(f"{can_siege}/{total}")



    return jsonify(
        {
        "guild":f"+{board.name}",
        "requirement":cutoff,
        "eligible_users":can_siege
        }
        )


@app.route("/admin/purge_guild_images/<boardname>", methods=["POST"])
@admin_level_required(5)
def admin_purge_guild_images(boardname):

    #Iterates through all posts in guild with thumbnail, and nukes thumbnails and i.syzitus uploads

    board=get_guild(boardname)

    if not board.is_banned:
        return jsonify({"error":"This guild isn't banned"}), 409

    if board.has_profile:
        board.del_profile()

    if board.has_banner:
        board.del_banner()

    posts = g.db.query(Submission).options(lazyload('*')).filter_by(board_id=board.id, has_thumb=True)


    def del_function(post):

        del_function
        aws.delete_file(urlparse(post.thumb_url).path.lstrip('/'))
        #post.has_thumb=False

        if post.url and post.domain==app.config["S3_BUCKET"]:
            aws.delete_file(urlparse(post.url).path.lstrip('/'))

    i=0
    threads=[]
    for post in posts.all():
        i+=1
        threads.append(threading.Thread(target=del_function, args=(post,)))
        post.has_thumb=False
        g.db.add(post)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    g.db.commit()

    return redirect(board.permalink)

@app.route("/admin/image_ban", methods=["POST"])
@admin_level_required(4)
def admin_image_ban():

    i=request.files['file']


    #make phash
    tempname = f"admin_image_ban_{g.user.username}_{g.timestamp}"

    i.save(tempname)

    h=phash(IMAGE.open(tempname))
    h=hex2bin(str(h))

    #check db for existing
    badpic = g.db.query(BadPic).filter_by(
        phash=h
        ).first()

    remove(tempname)

    if badpic:
        return render_template("admin/image_ban.html", existing=badpic)

    new_bp=BadPic(
        phash=h,
        ban_reason=request.form.get("ban_reason"),
        ban_time=int(request.form.get("ban_length",0))
        )

    g.db.add(new_bp)
    g.db.commit()

    return render_template("admin/image_ban.html", success=True)

@app.route("/admin/ipban", methods=["POST"])
@admin_level_required(7)
def admin_ipban():

    #bans all non-Tor IPs associated with a given account
    #only use for obvious proxys

    target_ip=request.values.get("ip")

    new_ipban=IP(
        banned_by=g.user.id,
        addr=target_ip
        )
    g.db.add(new_ipban)

    g.db.commit()

    return redirect(f"/admin/ip/{target_ip}")


@app.route("/admin/user_ipban", methods=["POST"])
@admin_level_required(7)
def admin_user_ipban():

    #bans all non-Tor IPs associated with a given account
    #only use for obvious proxys

    target_user=get_user(request.values.get("username"))

    targets=[target_user]+[alt for alt in target_user.alts]

    ips=set()
    for user in targets:
        if user.creation_region != "T1":
            ips.add(user.creation_ip)

        for post in g.db.query(Submission).options(lazyload('*')).filter_by(author_id=user.id).all():
            if post.creation_region != "T1":
                ips.add(post.creation_ip)

        for comment in g.db.query(Comment).options(lazyload('*')).filter_by(author_id=user.id).all():
            if comment.creation_region != "T1":
                ips.add()

    
    for ip in ips:

        new_ipban=IP(
            banned_by=g.user.id,
            addr=ip
            )
        g.db.add(new_ipban)

    g.db.commit()

@app.route("/admin/get_ip", methods=["GET"])
@admin_level_required(4)
def admin_get_ip_info():

    link=request.args.get("link","")

    if not link:
        return render_template(
            "admin/ip_info.html",
            )

    thing=get_from_permalink(link)

    if isinstance(thing, User):
        if request.values.get("ipnuke"):

            target_user=thing
            targets=[target_user]+[alt for alt in target_user.alts]

            ips=set()
            for user in targets:
                if user.creation_region != "T1":
                    ips.add(user.creation_ip)

                for post in g.db.query(Submission).options(lazyload('*')).filter_by(author_id=user.id).all():
                    if post.creation_region != "T1":
                        ips.add(post.creation_ip)

                for comment in g.db.query(Comment).options(lazyload('*')).filter_by(author_id=user.id).all():
                    if comment.creation_region != "T1":
                        ips.add()

            
            for ip in ips:

                if g.db.query(IP).filter_by(addr=ip).first():
                    continue

                new_ipban=IP(
                    banned_by=g.user.id,
                    addr=ip
                    )
                g.db.add(new_ipban)


            g.db.commit()

            return f"{len(ips)} ips banned"

    return redirect(f"/admin/ip/{thing.creation_ip}")


def print_(*x):
    try:
        print(*x)
    except:
        pass

@app.route("/admin/siege_guild", methods=["POST"])
@admin_level_required(3)
def admin_siege_guild():

    now = g.timestamp
    guild = request.form.get("guild")

    user=get_user(request.form.get("username"))
    guild = get_guild(guild)

    if now-g.user.created_utc < 60*60*24*30:
        return render_template("message.html",
                               title=f"Siege on +{guild.name} Failed",
                               error=f"@{user.username}'s account is too new."
                               ), 403

    if g.user.is_suspended or g.user.is_deleted:
        return render_template("message.html",
                               title=f"Siege on +{guild.name} Failed",
                               error=f"@{user.username} is deleted/suspended."
                               ), 403


    # check time
    #if user.last_siege_utc > now - (60 * 60 * 24 * 7):
    #    return render_template("message.html",
    #                           title=f"Siege on +{guild.name} Failed",
    #                           error=f"@{user.username} needs to wait 7 days between siege attempts."
    #                           ), 403
    # check guild count
    if not user.can_join_gms and guild not in user.boards_modded:
        return render_template("message.html",
                               title=f"Siege on +{guild.name} Failed",
                               error=f"@{user.username} already leads the maximum number of guilds."
                               ), 403

    # Can't siege if exiled
    if g.db.query(BanRelationship).filter_by(is_active=True, user_id=user.id, board_id=guild.id).first():
        return render_template(
            "message.html",
            title=f"Siege on +{guild.name} Failed",
            error=f"@{user.username} is exiled from +{guild.name}."
            ), 403

    # Cannot siege certain admin guilds
    if not guild.is_siegable:
        return render_template("message.html",
                               title=f"Siege on +{guild.name} Failed",
                               error=f"+{guild.name} is an admin-controlled guild and is immune to siege."
                               ), 403
    
    #cannot be installed within 7 days of a successful siege
    recent = g.db.query(ModAction).filter(
        ModAction.target_user_id==user.id,
        ModAction.kind=="add_mod",
        ModAction.created_utc>g.timestamp-60*60*24*7
    ).first()
    
    if recent:
        return render_template("message.html",
                               title=f"Siege on +{guild.name} Failed",
                               error=f"@{user.username} sieged +{recent.board.name} within the past 7 days.",
                               link=recent.permalink,
                               link_text="View mod log record"
                               ), 403
        
        

    # update siege date
    user.last_siege_utc = now
    g.db.add(user)
    for alt in g.user.alts:
        alt.last_siege_utc = now
        g.db.add(user)


    # check user activity
    #if guild not in user.boards_modded and user.guild_rep(guild, recent=180) < guild.siege_rep_requirement and not guild.has_contributor():
    #    return render_template(
    #       "message.html",
    #        title=f"Siege against +{guild.name} Failed",
    #        error=f"@{user.username} does not have enough recent Reputation in +{guild.name} to siege it. +{guild.name} currently requires {guild.siege_rep_requirement} Rep within the last 180 days, and @{user.username} has {g.user.guild_rep(guild, recent=180)}."
    #        ), 403

    # Assemble list of mod ids to check
    # skip any user with a perm site-wide ban
    # skip any deleted mod

    #check mods above user
    mods=[]
    for x in guild.mods_list:
        if (x.user.is_banned and not x.user.unban_utc) or x.user.is_deleted:
            continue

        if x.user_id==user.id:
            break
        mods.append(x)
    # if no mods, skip straight to success
    if mods and not request.values.get("activity_bypass"):
    #if False:
        ids = [x.user_id for x in mods]

        # cutoff
        cutoff = now - 60 * 60 * 24 * 60

        # check mod actions
        ma = g.db.query(ModAction).join(ModAction.user).filter(
            User.is_deleted==False,
            or_(
                User.is_banned==0,
                and_(
                    User.is_banned>0,
                    User.unban_utc>0
                    )
                ),
            or_(
                #option 1: mod action by user
                and_(
                    ModAction.user_id.in_(tuple(ids)),
                    ModAction.board_id==guild.id
                    ),
                #option 2: ruqqus adds user as mod due to siege
                and_(
                    ModAction.user_id==1,
                    ModAction.target_user_id.in_(tuple(ids)),
                    ModAction.kind=="add_mod",
                    ModAction.board_id==guild.id
                    )
                ),
                ModAction.created_utc > cutoff
            ).options(contains_eager(ModAction.User)
            ).first()
        if ma:
            return render_template("message.html",
                                   title=f"Siege against +{guild.name} Failed",
                                   error=f" One of the guildmasters has performed a mod action in +{guild.name} within the last 60 days. You may try again in 7 days.",
                                   link=ma.permalink,
                                   link_text="View mod log record"
                                   ), 403

        #check submissions
        post= g.db.query(Submission).filter(Submission.author_id.in_(tuple(ids)), 
                                        Submission.created_utc > cutoff,
                                        Submission.original_board_id==guild.id,
                                        Submission.deleted_utc==0,
                                        Submission.is_banned==False).order_by(Submission.board_id==guild.id).first()
        if post:
            return render_template("message.html",
                                   title=f"Siege against +{guild.name} Failed",
                                   error=f"One of the guildmasters created a post in +{guild.name} within the last 60 days. You may try again in 7 days.",
                                   link=post.permalink,
                                   link_text="View post"
                                   ), 403

        # check comments
        comment= g.db.query(Comment
            ).options(
                lazyload('*')
            ).filter(
                Comment.author_id.in_(tuple(ids)),
                Comment.created_utc > cutoff,
                Comment.original_board_id==guild.id,
                Comment.deleted_utc==0,
                Comment.is_banned==False
            ).join(
                Comment.post
            ).order_by(
                Submission.board_id==guild.id
            ).options(
                contains_eager(Comment.post)
            ).first()

        if comment:
            return render_template("message.html",
                                   title=f"Siege against +{guild.name} Failed",
                                   error=f"One of the guildmasters created a comment in +{guild.name} within the last 60 days. You may try again in 7 days.",
                                   link=comment.permalink,
                                   link_text="View comment"
                                   ), 403


    #Siege is successful

    #look up current mod record if one exists
    m=guild.has_mod(user)

    #remove current mods. If they are at or below existing mod, leave in place
    for x in guild.moderators:

        if m and x.id>=m.id and x.accepted:
            continue

        if x.accepted:
            send_notification(x.user,
                              f"You have been overthrown from +{guild.name}.")


            ma=ModAction(
                kind="remove_mod",
                user_id=g.user.id,
                board_id=guild.id,
                target_user_id=x.user_id,
                note="siege"
            )
            g.db.add(ma)
        else:
            ma=ModAction(
                kind="uninvite_mod",
                user_id=g.user.id,
                board_id=guild.id,
                target_user_id=x.user_id,
                note="siege"
            )
            g.db.add(ma)

        g.db.delete(x)


    if not m:
        new_mod = ModRelationship(user_id=user.id,
                                  board_id=guild.id,
                                  created_utc=now,
                                  accepted=True,
                                  perm_full=True,
                                  perm_access=True,
                                  perm_appearance=True,
                                  perm_content=True,
                                  perm_config=True
                                  )

        g.db.add(new_mod)
        ma=ModAction(
            kind="add_mod",
            user_id=g.user.id,
            board_id=guild.id,
            target_user_id=user.id,
            note="siege"
        )
        g.db.add(ma)

        send_notification(user, f"You have been added as a Guildmaster to +{guild.name}")

    elif not m.perm_full:
        m.perm_full=True
        m.perm_access=True
        m.perm_appearance=True
        m.perm_config=True
        m.perm_content=True
        g.db.add(m)
        ma=ModAction(
            kind="change_perms",
            user_id=g.user.id,
            board_id=guild.id,
            target_user_id=user.id,
            note="siege"
        )
        g.db.add(ma)        

    return redirect(f"/+{guild.name}/mod/mods")

@app.get('/admin/email/<email>')
@admin_level_required(4)
def user_by_email(email, v):
    
    email=email.replace('_', '\_')
    
    user=g.db.query(User).filter(User.email.ilike(email)).first()
    
    if not user:
        abort(404)
    
    return redirect(user.permalink)
    
    
@app.post("/admin/domain_nuke/<domain>")
@admin_level_required(5)
def admin_domain_nuke(domain):

    domain=domain.lower()
    domain_regex=re.sub("[^a-z0-9.]","", domain)
    #escape periods
    domain_regex=domain_regex.replace(".","\.")

    posts=g.db.query(Submission).join(
        Submission.submission_aux
        ).filter(
        SubmissionAux.url.op('~')(
            "https?://([^/]*\.)?"+domain_regex+"(/|$)"
            )
        ).all()

    for post in posts:
        post.is_banned=True
        g.db.add(post)


    d=get_domain(domain)
    if d:
        reason=d.reason
    else:
        reason="none"

    g.db.commit()
    discord_log_event("Nuke Domain", domain, g.user, reason=reason, admin_action=True)

    return redirect(f"/search?q=domain:{domain}")


@app.route("/admin/csam_nuke/<pid>", methods=["POST"])
@admin_level_required(4)
def admin_csam_nuke(pid):

    post = get_post(pid)

    post.is_banned = True
    post.ban_reason = "CSAM [1]"
    g.db.add(post)
    ma=ModAction(
        user_id=1,
        target_submission_id=post.id,
        board_id=post.board_id,
        kind="ban_post",
        note="CSAM detected"
        )

    user = post.author
    user.is_banned = g.user.id
    g.db.add(user)
    for alt in user.alts:
        alt.is_banned = g.user.id
        g.db.add(alt)

    if post.domain == app.config['S3_BUCKET']:

        x = requests.get(url)
        # load image into PIL
        # take phash
        # add phash to db

        name = urlparse(post.url).path.lstrip('/')
        delete_file(name)  # this also dumps cloudflare


@app.route("/admin/dump_cache", methods=["POST"])
@admin_level_required(3)
def admin_dump_cache():

    cache.clear()

    return jsonify({"message": "Internal cache cleared."})



@app.route("/admin/ban_domain", methods=["POST"])
@admin_level_required(4)
def admin_ban_domain():

    domain=request.form.get("domain",'').lstrip().rstrip().lower()

    if not domain:
        abort(400)

    reason=int(request.form.get("reason",0))
    if not reason:
        abort(400)

    if domain==app.config["SERVER_NAME"].lower() or domain==app.config["S3_BUCKET"].lower():
        return jsonify({"error":f"{app.config['SITE_NAME']} can't ban itself!"}), 422

    d=get_domain(domain)
    if d:
        d.is_banned=True
        d.reason=reason
    else:
        d=Domain(
            domain=domain,
            is_banned=True,
            reason=reason,
            show_thumbnail=False,
            embed_function=None,
            embed_template=None
            )

    g.db.add(d)
    g.db.commit()

    discord_log_event("Ban Domain", domain, g.user, reason=reason, admin_action=True)

    if request.form.get("from")=="admin":
        return redirect(d.permalink)
    else:
        return redirect(f"/search?q=domain:{domain}")


@app.route("/admin/nuke_user", methods=["POST"])
@admin_level_required(4)
def admin_nuke_user():

    user=get_user(request.form.get("user"))

    note='admin action'
    if user.ban_reason:
        note+=f" | {user.ban_reason}"


    for post in g.db.query(Submission).filter_by(author_id=user.id).all():
        if post.is_banned:
            continue
            
        post.is_banned=True
        post.ban_reason=user.ban_reason
        g.db.add(post)

        ma=ModAction(
            kind="ban_post",
            user_id=g.user.id,
            target_submission_id=post.id,
            board_id=post.board_id,
            note=note
            )
        g.db.add(ma)

    for comment in g.db.query(Comment).filter_by(author_id=user.id).all():
        if comment.is_banned:
            continue

        comment.is_banned=True
        g.db.add(comment)

        ma=ModAction(
            kind="ban_comment",
            user_id=g.user.id,
            target_comment_id=comment.id,
            board_id=comment.post.board_id,
            note=note
            )
        g.db.add(ma)

    g.db.commit()


    post_flags=select(Flag).filter(
                Flag.post_id.in_(
                    select(Submission.id).filter(Submission.author_id==user.id)
                    ),
                Flag.resolution_notif_sent==False
        )

    comment_flags=select(CommentFlag).filter(
                CommentFlag.comment_id.in_(
                    select(Comment.id).filter(Comment.author_id==user.id)
                    ),
                CommentFlag.resolution_notif_sent==False
        )
 

    post_users=g.db.query(User).filter(
        User.id.in_(
            select(Flag.user_id).filter(
                Flag.post_id.in_(
                    select(Submission.id).filter(Submission.author_id==user.id)
                    ),
                Flag.resolution_notif_sent==False)
            )
        )
    
    comment_users=g.db.query(User).filter(
        User.id.in_(
            select(CommentFlag.user_id).filter(
                CommentFlag.post_id.in_(
                    select(Comment.id).filter(Comment.author_id==user.id)
                    ),
                CommentFlag.resolution_notif_sent==False)
            )
        )

    for flagging_user in post_users:
        send_notification(flagging_user, f"A post you reported has been removed. Thank you for your help in keeping {app.config['SITE_NAME']} safe.")
    for flagging_user in comment_users:
        send_notification(flagging_user, f"A comment you reported has been removed. Thank you for your help in keeping {app.config['SITE_NAME']} safe.")

    for flag in post_flags:
        flag.resolution_notif_sent=True
        g.db.add(flag)
    for flag in comment_flags:
        flag.resolution_notif_sent=True
        g.db.add(flag)

    g.db.commit()

    discord_log_event("Nuke user", user, g.user, reason=user.ban_reason, admin_action=True)

    return redirect(user.permalink)

@app.route("/admin/demod_user", methods=["POST"])
@admin_level_required(4)
def admin_demod_user():

    user=get_user(request.form.get("user"))

    for mod in g.db.query(ModRelationship).filter_by(user_id=user.id, accepted=True):

        ma=ModAction(
            user_id=g.user.id,
            target_user_id=user.id,
            board_id=mod.board_id,
            kind="remove_mod",
            note="admin_action"
            )
        g.db.add(ma)

        g.db.delete(mod)

    g.db.commit()

    discord_log_event("Global De-Mod", user, g.user, admin_action=True)

    return redirect(user.permalink)

@app.route("/api/ban_user/<user_id>", methods=["POST"])
@admin_level_required(3)
def ban_user(user_id):

    user = g.db.query(User).filter_by(id=user_id).first()
    if not user:
        abort(404)

    # check for number of days for suspension
    days = int(request.form.get("days")) if request.form.get('days') else 0
    reason = request.form.get("reason", "")
    message = request.form.get("message", "")


    user.ban(admin=g.user, days=days, reason=reason, message=message)


    for x in user.alts:
        if x.admin_level:
            continue
        if not x.is_deleted and not x.is_permbanned:
            x.ban(admin=g.user, reason=reason)

    return (redirect(user.url), user)


@app.route("/api/unban_user/<user_id>", methods=["POST"])
@admin_level_required(3)
def unban_user(user_id):

    user = g.db.query(User).filter_by(id=user_id).first()

    if not user:
        abort(404)

    user.unban()

    return (redirect(user.url), user)


@app.route("/api/ban_post/<post_id>", methods=["POST"])
@admin_level_required(3)
def ban_post(post_id):

    post = get_post(post_id)

    if not post:
        abort(400)

    post.is_banned = True
    post.is_approved = None
    post.approved_utc = 0
    post.stickied = False
    post.is_pinned = False

    ban_reason=request.form.get("reason", "")
    with CustomRenderer() as renderer:
        ban_reason = renderer.render(mistletoe.Document(ban_reason))
    ban_reason = sanitize(ban_reason, linkgen=True)

    post.ban_reason = ban_reason

    g.db.add(post)

    cache.delete_memoized(Board.idlist, post.board)

    if post.author.is_suspended and post.author.ban_reason:
        note = f"admin action | {post.author.ban_reason}"
    else:
        note="admin action"

    ma=ModAction(
        kind="ban_post",
        user_id=g.user.id,
        target_submission_id=post.id,
        board_id=post.board_id,
        note=note
        )
    g.db.add(ma)
    g.db.commit()

    #notify users who reported it
    users=g.db.query(User).filter(
        User.id.in_(
            select(Flag.user_id).filter_by(
                post_id=post.id,
                resolution_notif_sent=False)
            )
        )

    for user in users:
        send_notification(user, f"A post you reported has been removed. Thank you for your help in keeping {app.config['SITE_NAME']} safe.")

    for flag in g.db.query(Flag).filter_by(post_id=post.id, resolution_notif_sent=False).all():
        flag.resolution_notif_sent=True
        g.db.add(flag)
    g.db.commit()

    return jsonify({"message":f"Post {post.base36id} removed"})


@app.route("/api/unban_post/<post_id>", methods=["POST"])
@admin_level_required(3)
def unban_post(post_id):

    post = get_post(post_id)

    if not post:
        abort(400)

    if post.is_banned:
        ma=ModAction(
            kind="unban_post",
            user_id=g.user.id,
            target_submission_id=post.id,
            board_id=post.board_id,
            note="admin action"
        )
        g.db.add(ma)

    post.is_banned = False
    post.is_approved = g.user.id
    post.approved_utc = g.timestamp

    g.db.add(post)
    g.db.commit()


    #notify users who reported it
    users=g.db.query(User).filter(
        User.id.in_(
            select(Flag.user_id).filter_by(
                post_id=post.id,
                resolution_notif_sent=False)
            )
        )

    for user in users:
        send_notification(user, f"You had previously reported the post linked below. After review, it was determined that it did not violate the {app.config['SITE_NAME']} [terms of service](/help/terms) or [content rules](/help/rules).\n\n{post.permalink_full}\n\nThank you for your assistance in keeping {app.config['SITE_NAME']} safe.")

    for flag in g.db.query(Flag).filter_by(post_id=post.id, resolution_notif_sent=False).all():
        flag.resolution_notif_sent=True
        g.db.add(flag)
    g.db.commit()

    return jsonify({"message":f"Post {post.base36id} approved"})


@app.route("/api/distinguish/<post_id>", methods=["POST"])
@admin_level_required(1)
def api_distinguish_post(post_id):

    post = get_post(post_id)

    if not post:
        abort(404)

    if not post.author_id == g.user.id:
        abort(403)

    if post.distinguish_level:
        post.distinguish_level = 0
    else:
        post.distinguish_level = g.user.admin_level

    g.db.add(post)
    g.db.commit()

    return (redirect(post.permalink), post)


@app.route("/api/sticky/<post_id>", methods=["POST"])
@admin_level_required(3)
def api_sticky_post(post_id):

    post = get_post(post_id)
    post.stickied = not post.stickied
    g.db.add(post)
    g.db.commit()
    return redirect(post.permalink)


@app.route("/api/ban_comment/<c_id>", methods=["post"])
@admin_level_required(1)
def api_ban_comment(c_id):

    comment = get_comment(c_id)
    if not comment:
        abort(404)

    comment.is_banned = True
    comment.is_approved = 0
    comment.approved_utc = 0

    g.db.add(comment)


    if comment.author.is_suspended and comment.author.ban_reason:
        note = f"admin action | {comment.author.ban_reason}"
    else:
        note="admin action"

    ma=ModAction(
        kind="ban_comment",
        user_id=g.user.id,
        target_comment_id=comment.id,
        board_id=comment.post.board_id,
        note=note
        )
    g.db.add(ma)
    g.db.commit()

    #notify users who reported it
    users=g.db.query(User).filter(
        User.id.in_(
            select(CommentFlag.user_id).filter_by(
                comment_id=comment.id,
                resolution_notif_sent=False)
            )
        )

    for user in users:
        send_notification(user, f"A comment you reported has been removed. Thank you for your help in keeping {app.config['SITE_NAME']} safe.")

    for flag in g.db.query(CommentFlag).filter_by(comment_id=comment.id, resolution_notif_sent=False).all():
        flag.resolution_notif_sent=True
        g.db.add(flag)
    g.db.commit()

    return jsonify({"message":f"Comment {comment.base36id} removed"})


@app.route("/api/unban_comment/<c_id>", methods=["post"])
@admin_level_required(1)
def api_unban_comment(c_id):

    comment = get_comment(c_id)
    if not comment:
        abort(404)

    if comment.is_banned:
        ma=ModAction(
            kind="unban_comment",
            user_id=g.user.id,
            target_comment_id=comment.id,
            board_id=comment.post.board_id,
            note="admin action"
            )
        g.db.add(ma)

    comment.is_banned = False
    comment.is_approved = g.user.id
    comment.approved_utc = g.timestamp

    g.db.add(comment)
    g.db.commit()


    #notify users who reported it
    users=g.db.query(User).filter(
        User.id.in_(
            select(CommentFlag.user_id).filter_by(
                comment_id=comment.id,
                resolution_notif_sent=False)
            )
        )

    for user in users:
        send_notification(user, f"You had previously reported the comment linked below. After review, it was determined that it did not violate the {app.config['SITE_NAME']} [terms of service](/help/terms) or [content rules](/help/rules). Thank you for your help in keeping {app.config['SITE_NAME']} safe.\n\n{comment.permalink_full}")

    for flag in g.db.query(CommentFlag).filter_by(comment_id=comment.id, resolution_notif_sent=False).all():
        flag.resolution_notif_sent=True
        g.db.add(flag)
    g.db.commit()

    return jsonify({"message":f"Comment {comment.base36id} approved"})


@app.route("/api/distinguish_comment/<c_id>", methods=["post"])
@admin_level_required(1)
def admin_distinguish_comment(c_id):

    comment = get_comment(c_id)

    if comment.author_id != g.user.id:
        abort(403)

    comment.distinguish_level = 0 if comment.distinguish_level else g.user.admin_level

    g.db.add(comment)
    g.db.commit()

    html=render_template(
                "comments.html",
                comments=[comment],
                render_replies=False,
                is_allowed_to_comment=True
                )

    html=str(BeautifulSoup(html, features="html.parser").find(id=f"comment-{comment.base36id}-only"))

    return jsonify({"html":html})



@app.route("/api/ban_guild/<bid>", methods=["POST"])
@admin_level_required(4)
def api_ban_guild(bid):

    board = get_board(bid)

    board.is_banned = True
    board.ban_reason = request.form.get("reason", "")

    g.db.add(board)
    g.db.commit()

    discord_log_event("Ban Guild", board, g.user, reason=board.ban_reason, admin_action=True)

    return redirect(board.permalink)


@app.route("/api/unban_guild/<bid>", methods=["POST"])
@admin_level_required(4)
def api_unban_guild(bid):

    board = get_board(bid)

    board.is_banned = False
    original_ban_reason=board.ban_reason
    board.ban_reason = ""

    g.db.add(board)
    g.db.commit()

    discord_log_event("Unban Guild", board, g.user, reason=original_ban_reason, admin_action=True)

    return redirect(board.permalink)


@app.route("/api/mod_self/<bid>", methods=["POST"])
@admin_level_required(4)
def mod_self_to_guild(bid):

    board = get_board(bid)
    if not board.has_mod(g.user):
        mr = ModRelationship(user_id=g.user.id,
                             board_id=board.id,
                             accepted=True,
                             perm_full=True,
                             perm_access=True,
                             perm_config=True,
                             perm_appearance=True,
                             perm_content=True)
        g.db.add(mr)

        ma=ModAction(
            kind="add_mod",
            user_id=g.user.id,
            target_user_id=g.user.id,
            board_id=board.id,
            note="admin action"
        )
        g.db.add(ma)
        g.db.commit()

    return redirect(f"/+{board.name}/mod/mods")


@app.post("/admin/ban_ip")
@admin_level_required(5)
def admin_ban_ip():

    ip=request.form.get("addr")

    existing_ban=get_ip(ip)

    if existing_ban:
        return jsonify({"error":f"IP address {ip} already banned"}), 409

    new_ipban=IP(
        addr=ip,
        reason=request.form.get("reason"),
        banned_by=g.user.id
        )

    g.db.add(new_ipban)
    g.db.commit()
    return jsonify({"message":f"IP address {ip} banned"})

@app.post("/admin/give_coins")
@admin_level_required(6)
def admin_give_coins():

    target_user=g.db.query(User).with_for_update().filter_by(id=base36decode(request.form.get("target_user_id"))).first()
    if not target_user:
        return jsonify({"error":f"User ID {request.form.get('target_user_id')} not found"}), 404

    coin_count=max(int(request.form.get("coin_count",0)), 0)
    if not coin_count:
        return jsonify({"error":"Cannot give zero coins"}), 400

    target_user.coin_balance += coin_count

    g.db.add(target_user)
    g.db.commit()

    send_notification(target_user, f"{coin_count} Coin{' has' if coin_count==1 else 's have'} been added to your account by {app.config['SITE_NAME']} staff.")

    debug(f"Give coins: @{g.user.username} gave {coin_count} Coins to @{target_user.username}")

    return jsonify({"message":f"{coin_count} Coins given to @{target_user.username}"})


@app.get("/admin/useragent")
@admin_level_required(5)
def admin_useragent_kwd():

    kwd=request.args.get("kwd")

    if kwd:
        ua_ban = g.db.query(Agent).filter(
            or_(
                Agent.kwd.in_(kwd.split()),
                Agent.kwd.ilike(kwd)
                )
            ).first()
    else:
        ua_ban=None

    return render_template(
        "admin/useragent.html",
        kwd=kwd,
        ban=ua_ban
        )

@app.post("/admin/useragent")
@admin_level_required(5)
def post_admin_useragent_kwd():

    new_ban=Agent(
        kwd=        request.form.get("kwd"),
        reason=     request.form.get("reason"),
        mock=       request.form.get("mock"),
        status_code=request.form.get("status"),
        banned_by=  g.user.id
        )

    g.db.add(new_ban)
    g.db.commit()
    return redirect(new_ban.permalink)