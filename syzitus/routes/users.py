from urllib.parse import urlparse
from sqlalchemy import func
from bs4 import BeautifulSoup
from pyotp import TOTP
from qrcode import QRCode
from qrcode.constants import ERROR_CORRECT_L
from io import BytesIO
from flask import g, session, abort, render_template, jsonify, redirect, send_file
# import gevent

from syzitus.helpers.wrappers import *
from syzitus.helpers.base36 import *
from syzitus.helpers.sanitize import *
from syzitus.helpers.filters import *
from syzitus.helpers.embed import *
from syzitus.helpers.markdown import *
from syzitus.helpers.get import *
from syzitus.classes import *
from syzitus.mail import *
from syzitus.__main__ import app, cache, limiter, db_session

BAN_REASONS = ['',
               "URL shorteners are not permitted."
               ]


@app.route("/2faqr/<secret>", methods=["GET"])
@auth_required
def mfa_qr(secret):
    x = TOTP(secret)
    qr = QRCode(
        error_correction=ERROR_CORRECT_L
    )
    qr.add_data(x.provisioning_uri(g.user.username, issuer_name=app.config["SITE_NAME"]))
    img = qr.make_image(fill_color="#"+app.config["COLOR_PRIMARY"], back_color="white")

    mem = BytesIO()

    img.save(mem, format="PNG")
    mem.seek(0, 0)
    return send_file(mem, mimetype="image/png", as_attachment=False)


@app.route("/uid/<uid>", methods=["GET"])
def user_uid(uid):
    return redirect(get_account(uid).permalink)


        
@app.route("/u/<username>", methods=["GET"])
def redditor_moment_redirect(username):

    return redirect(f"/@{username}")


@app.route("/@<username>", methods=["GET"])
@app.get("/api/v2/users/<username>/submissions")
@auth_desired
@no_archive
@api("read")
def u_username(username):
    """
Get posts created by another user.

URL path parameters:
* `username` - The user whose posts are being fetched.

Optional query parameters:
* `sort` - One of `hot`, `new`, `old`, `top`, `activity`, or `disputed`. Default `new`.
* `t` - One of `day`, `week`, `month`, `year`, `all`. Default `all`.
* `page` - Page of results to return. Default `1`.
"""

    # username is unique so at most this returns one result. Otherwise 404

    # case insensitive search

    u = get_user(username)

    if u.reserved:
        return {'html': lambda: render_template("userpage_reserved.html",
                                                u=u),
                'api': lambda: {"error": f"That username is reserved for: {u.reserved}"}
                }

    if u.is_suspended and not (g.user and (g.user.admin_level >=3 or g.user.id==u.id)):
        return {'html': lambda: render_template("userpage_banned.html",
                                                u=u),
                'api': lambda: {"error": "That user is banned"}
                }

    if u.is_deleted and not (g.user and g.user.admin_level >= 3):
        return {'html': lambda: render_template("userpage_deleted.html",
                                                u=u),
                'api': lambda: {"error": "That user deactivated their account."}
                }

    if u.is_private and not (g.user and (g.user.admin_level >=3 or g.user.id==u.id)):
        return {'html': lambda: render_template("userpage_private.html",
                                                u=u),
                'api': lambda: {"error": "That userpage is private"}
                }

    if u.is_blocking and not (g.user and g.user.admin_level >= 3):
        return {'html': lambda: render_template("userpage_blocking.html",
                                                u=u),
                'api': lambda: {"error": f"You are blocking @{u.username}."}
                }

    if u.is_blocked and not (g.user and g.user.admin_level >= 3):
        return {'html': lambda: render_template("userpage_blocked.html",
                                                u=u),
                'api': lambda: {"error": "This person is blocking you."}
                }

    sort = request.args.get("sort", "new")
    t = request.args.get("t", "all")
    page = int(request.args.get("page", "1"))
    page = max(page, 1)

    ids = u.userpagelisting(page=page, sort=sort, t=t)

    # we got 26 items just to see if a next page exists
    next_exists = (len(ids) == 26)
    ids = ids[0:25]

    listing = get_posts(ids)

    return {'html': lambda: render_template("userpage.html",
                                            u=u,
                                            listing=listing,
                                            page=page,
                                            next_exists=next_exists,
                                            is_following=(g.user and u.has_follower(g.user))),
            'api': lambda: jsonify({"data": [x.json for x in listing]})
            }


@app.route("/@<username>/comments", methods=["GET"])
@app.get("/api/v2/users/<username>/comments")
@auth_desired
@no_archive
@api("read")
def u_username_comments(username, v=None):
    """
Get comments created by another user.

URL path parameters:
* `username` - The user whose comments are being fetched.

Optional query parameters:
* `sort` - One of `hot`, `new`, `old`, `top`, or `disputed`. Default `new`.
* `t` - One of `day`, `week`, `month`, `year`, `all`. Default `all`.
* `page` - Page of results to return. Default `1`.
"""

    # username is unique so at most this returns one result. Otherwise 404

    # case insensitive search

    user = get_user(username)

    # check for wrong cases

    if username != user.username:
        return redirect(f'{user.url}/comments')

    u = user

    if u.reserved:
        return {'html': lambda: render_template("userpage_reserved.html",
                                                u=u),
                'api': lambda: {"error": f"That username is reserved for: {u.reserved}"}
                }

    if u.is_suspended and not (g.user and (g.user.admin_level >=3 or g.user.id==u.id)):
        return {'html': lambda: render_template("userpage_banned.html",
                                                u=u),
                'api': lambda: {"error": "That user is banned"}
                }

    if u.is_deleted and not (g.user and g.user.admin_level >= 3):
        return {'html': lambda: render_template("userpage_deleted.html",
                                                u=u),
                'api': lambda: {"error": "That user deactivated their account."}
                }

    if u.is_private and not (g.user and (g.user.admin_level >=3 or g.user.id==u.id)):
        return {'html': lambda: render_template("userpage_private.html",
                                                u=u),
                'api': lambda: {"error": "That userpage is private"}
                }

    if u.is_blocking and not (g.user and g.user.admin_level >= 3):
        return {'html': lambda: render_template("userpage_blocking.html",
                                                u=u),
                'api': lambda: {"error": f"You are blocking @{u.username}."}
                }

    if u.is_blocked and not (g.user and g.user.admin_level >= 3):
        return {'html': lambda: render_template("userpage_blocked.html",
                                                u=u),
                'api': lambda: {"error": "This person is blocking you."}
                }

    page = int(request.args.get("page", "1"))

    ids = user.commentlisting(
        page=page,
        sort=request.args.get("sort","new"),
        t=request.args.get("t","all")
        )

    # we got 26 items just to see if a next page exists
    next_exists = (len(ids) == 26)
    ids = ids[0:25]

    listing = get_comments(ids)

    is_following = (g.user and user.has_follower(g.user))

    return {"html": lambda: render_template("userpage_comments.html",
                                            u=user,
                                            listing=listing,
                                            page=page,
                                            next_exists=next_exists,
                                            is_following=is_following,
                                            standalone=True),
            "api": lambda: jsonify({"data": [c.json for c in listing]})
            }

@app.get("/api/v2/users/<username>")
@auth_desired
@api("read")
def u_username_info(username, v=None):
    """
Get information about another user.

URL path parameters:
* `username` - A user's name.
"""

    user=get_user(username)

    if user.is_blocking:
        return jsonify({"error": "You're blocking this user."}), 401
    elif user.is_blocked:
        return jsonify({"error": "This user is blocking you."}), 403

    return jsonify(user.json)


@app.route("/api/follow/<username>", methods=["POST"])
@app.post("/api/v2/users/<username>/follow")
@auth_required
def follow_user(username):
    """
Follow another user.

URL path parameters:
* `username` - A user's name.
"""

    target = get_user(username)

    if target.id==g.user.id:
        return jsonify({"error": "You can't follow yourself!"}), 400

    # check for existing follow
    if g.db.query(Follow).filter_by(user_id=g.user.id, target_id=target.id).first():
        return jsonify({"error": f"You're already following @{target.username}"}), 409

    if target.is_blocking:
        return jsonify({"error": "You're blocking this user."}), 401
    elif target.is_blocked:
        return jsonify({"error": "This user is blocking you."}), 403

    new_follow = Follow(user_id=g.user.id,
                        target_id=target.id)

    g.db.add(new_follow)
    g.db.flush()
    target.stored_subscriber_count=target.follower_count
    g.db.add(target)
    g.db.commit()

    cache.delete_memoized(User.idlist)

    return "", 204


@app.route("/api/unfollow/<username>", methods=["POST"])
@app.delete("/api/v2/users/<username>/follow")
@auth_required
def unfollow_user(username):
    """
Unfollow another user.

URL path parameters:
* `username` - A user's name.
"""

    target = get_user(username)

    # check for existing follow
    follow = g.db.query(Follow).filter_by(
        user_id=g.user.id, target_id=target.id).first()

    if not follow:
        return jsonify({"error": f"You already aren't following @{target.username}"}), 409

    g.db.delete(follow)
    g.db.flush()
    target.stored_subscriber_count=target.follower_count
    g.db.add(target)
    g.db.commit()

    cache.delete_memoized(User.idlist)

    return "", 204


@app.get("/uid/<uid>/pic/profile")
def old_user_profile(uid):
    return redirect(get_account(uid).dynamic_profile_url)

@app.get("/@<username>/pic/profile/<profile_nonce>")
@cf_cache
@limiter.exempt
def user_profile(username, profile_nonce):
    x = get_user(username)
    return redirect(x.profile_url), 301

@app.get("/uid/<uid>/pic/profile/<profile_nonce>")
@cf_cache
@limiter.exempt
def user_profile_uid(uid, profile_nonce):
    x=get_account(uid)
    return redirect(x.profile_url), 301


# @app.route("/saved", methods=["GET"])
# @app.get("/api/v2/me/saved")
# @auth_required
# @api("read")
# def saved_listing():

#     print("saved listing")

#     page=int(request.args.get("page",1))

#     ids=g.user.saved_idlist(page=page)

#     next_exists=len(ids)==26

#     ids=ids[0:25]

#     print(ids)

#     listing = get_posts(ids, sort="new")

#     return {'html': lambda: render_template("home.html",
#                                             listing=listing,
#                                             page=page,
#                                             next_exists=next_exists
#                                             ),
#             'api': lambda: jsonify({"data": [x.json for x in listing]})
#             }


@app.post("/@<username>/toggle_bell")
@app.post("/api/v2/users/<username>/toggle_bell")
@auth_required
@api("update")
def toggle_user_bell(username):
    """
Toggle notifications for new posts by a user. You must be following the user.

URL path parameters:
* `username` - Another user's name
"""

    user=get_user(username, graceful=True)
    if not user:
        return jsonify({"error": f"User '@{username}' not found."}), 404

    follow=g.db.query(Follow).filter_by(user_id=g.user.id, target_id=user.id).first()
    if not follow:
        return jsonify({"error": f"You aren't following @{user.username}"}), 404

    follow.get_notifs = not follow.get_notifs
    g.db.add(follow)
    g.db.commit()

    return jsonify({"message":f"Notifications {'en' if follow.get_notifs else 'dis'}abled for @{user.username}"})


# def convert_file(html):

#     if not isinstance(html, str):
#         return html

#     soup=BeautifulSoup(html, 'html.parser')

#     for thing in soup.find_all('link', rel="stylesheet"):

#         if not thing['href'].startswith('https'):

#             if app.config["FORCE_HTTPS"]:
#                 thing["href"]=f"https://{app.config['SERVER_NAME']}{thing['href']}"
#             else: 
#                 thing["href"]=f"https://{app.config['SERVER_NAME']}{thing['href']}"

#     for thing in soup.find_all('a', href=True):

#         if thing["href"].startswith('/') and not thing["href"].startswith(("javascript",'//')):
#             if app.config["FORCE_HTTPS"]:
#                 thing["href"]=f"https://{app.config['SERVER_NAME']}{thing['href']}"
#             else:
#                 thing["href"]=f"http://{app.config['SERVER_NAME']}{thing['href']}"

#     for thing in soup.find_all('img', src=True):

#         if thing["src"].startswith('/') and not thing["src"].startswith('//'):
#             if app.config["FORCE_HTTPS"]:
#                 thing["src"]=f"https://{app.config['SERVER_NAME']}{thing['src']}"
#             else:
#                 thing["src"]=f"http://{app.config['SERVER_NAME']}{thing['src']}"




#     return str(soup)


# def info_packet(username, method="html"):

#     print(f"starting {username}")

#     packet={}

#     with app.test_request_context("/my_info"):

#         db=db_session()
#         g.timestamp=int(time.time())
#         g.db=db

#         user=get_user(username)

#         #submissions
#         post_ids=db.query(Submission.id).filter_by(author_id=user.id).order_by(Submission.created_utc.desc()).all()
#         post_ids=[i[0] for i in post_ids]
#         posts=get_posts(post_ids, v=user)
#         packet["posts"]={
#             'html':lambda:render_template("userpage.html", v=None, u=user, listing=posts, page=1, next_exists=False),
#             'json':lambda:[x.self_download_json for x in posts]
#         }

#         #comments
#         comment_ids=db.query(Comment.id).filter_by(author_id=user.id).order_by(Comment.created_utc.desc()).all()
#         comment_ids=[x[0] for x in comment_ids]
#         comments=get_comments(comment_ids, v=user)
#         packet["comments"]={
#             'html':lambda:render_template("userpage_comments.html", v=None, u=user, listing=comments, page=1, next_exists=False),
#             'json':lambda:[x.self_download_json for x in comments]
#         }

#         #upvoted posts
#         upvote_query=db.query(Vote.submission_id).filter_by(user_id=user.id, vote_type=1).order_by(Vote.id.desc()).all()
#         upvote_posts=get_posts([i[0] for i in upvote_query], v=user)
#         upvote_posts=[i for i in upvote_posts]
#         for post in upvote_posts:
#             post.__dict__['voted']=1
#         packet['upvoted_posts']={
#             'html':lambda:render_template("userpage.html", v=None, listing=posts, page=1, next_exists=False),
#             'json':lambda:[x.json_core for x in upvote_posts]
#         }

#         print('post_downvotes')
#         downvote_query=db.query(Vote.submission_id).filter_by(user_id=user.id, vote_type=-1).order_by(Vote.id.desc()).all()
#         downvote_posts=get_posts([i[0] for i in downvote_query], v=user)
#         packet['downvoted_posts']={
#             'html':lambda:render_template("userpage.html", v=None, listing=posts, page=1, next_exists=False),
#             'json':lambda:[x.json_core for x in downvote_posts]
#         }

#         print('comment_upvotes')
#         upvote_query=db.query(CommentVote.comment_id).filter_by(user_id=user.id, vote_type=1).order_by(CommentVote.id.desc()).all()
#         upvote_comments=get_comments([i[0] for i in upvote_query], v=user)
#         packet["upvoted_comments"]={
#             'html':lambda:render_template("userpage_comments.html", v=None, listing=upvote_comments, page=1, next_exists=False),
#             'json':lambda:[x.json_core for x in upvote_comments]
#         }

#         print('comment_downvotes')
#         downvote_query=db.query(CommentVote.comment_id).filter_by(user_id=user.id, vote_type=-1).order_by(CommentVote.id.desc()).all()
#         downvote_comments=get_comments([i[0] for i in downvote_query], v=user)
#         packet["downvoted_comments"]={
#             'html':lambda:render_template("userpage_comments.html", v=None, listing=downvote_comments, page=1, next_exists=False),
#             'json':lambda:[x.json_core for x in downvote_comments]
#         }

#         print('blocked users')
#         blocked_users=db.query(UserBlock.target_id).filter_by(user_id=user.id).order_by(UserBlock.id.desc()).all()
#         users=[get_account(base36encode(x[0])) for x in blocked_users]
#         packet["blocked_users"]={
#             "html":lambda:render_template("admin/new_users.html", users=users, v=None, page=1, next_exists=False),
#             "json":lambda:[x.json_core for x in users]
#         }




#         send_mail(
#             user.email,
#             "Your Ruqqus Data",
#             "Your Ruqqus data is attached.",
#             "Your Ruqqus data is attached.",
#             files={f"{user.username}_{entry}.{method}": io.StringIO(convert_file(str(packet[entry][method]()))) for entry in packet}
#         )


#     print("finished")



#@app.route("/my_info", methods=["POST"])
#@limiter.limit("2/day")
# @auth_required
# @validate_formkey
# def my_info_post():

#     if not g.user.is_activated:
#         return redirect("/settings/security")

#     method=request.values.get("method","html")
#     if method not in ['html','json']:
#         abort(400)

#     gevent.spawn_later(5, info_packet, g.user.username, method=method)

#     return "started"



