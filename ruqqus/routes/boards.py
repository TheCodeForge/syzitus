from urllib.parse import urlparse
import mistletoe
import re
import sass
import threading
import time
import os.path
from bs4 import BeautifulSoup 
import cssutils

from ruqqus.helpers.wrappers import *
from ruqqus.helpers.base36 import *
from ruqqus.helpers.sanitize import *
from ruqqus.helpers.markdown import *
from ruqqus.helpers.get import *
from ruqqus.helpers.alerts import *
from ruqqus.helpers.session import *
from ruqqus.helpers.aws import check_csam_url
from ruqqus.classes import *
from .front import guild_ids
from ruqqus.classes.rules import *
from ruqqus.classes.categories import CATEGORIES
from flask import *

from ruqqus.__main__ import app, limiter, cache

valid_board_regex = re.compile("^[a-zA-Z0-9][a-zA-Z0-9_]{2,24}$")

@app.route("/m/<name>", methods=["GET"])
@app.route("/api/v1/multi/<name>/listing", methods=["GET"])
@auth_desired
@api("read")
def multiboard(name, v):
    
    if v:
        defaultsorting = v.defaultsorting
        defaulttime = v.defaulttime
    else:
        defaultsorting = "hot"
        defaulttime = "all"

    sort = request.args.get("sort", defaultsorting)
    t = request.args.get("t", defaulttime)
    page = int(request.args.get("page", 1))

    board_ids=[]
    
    for name in name.split("+"):
        board = get_guild(name)
        if board.is_banned and not (v and v.admin_level >= 3): continue
        if board.over_18 and not (v and v.over_18) and not session_over18(board): continue
        if not board.can_view(v): continue

        board_ids.append(board.id)

    posts = g.db.query(Submission.id).options(lazyload('*')).filter_by(is_banned=False).filter(Submission.deleted_utc == 0,
                                                                                                                                                Submission.board_id.in_(tuple(board_ids)))
    
    if v:
        blocking = g.db.query(UserBlock.target_id).filter_by(user_id=v.id).subquery()
        posts = posts.filter(Submission.author_id.notin_(blocking))

    if v and not v.over_18:
        posts = posts.filter_by(over_18=False)

    if v and v.hide_offensive:
        posts = posts.filter_by(is_offensive=False)
        
    if v and v.hide_bot:
        posts = posts.filter_by(is_bot=False)

    if v and not v.show_nsfl:
        posts = posts.filter_by(is_nsfl=False)

    if t:
        now = int(time.time())
        if t == 'day':
            cutoff = now - 86400
        elif t == 'week':
            cutoff = now - 604800
        elif t == 'month':
            cutoff = now - 2592000
        elif t == 'year':
            cutoff = now - 31536000
        else:
            cutoff = 0
        posts = posts.filter(Submission.created_utc >= cutoff)

    if sort == "hot":
        posts = posts.order_by(Submission.score_best.desc())
    elif sort == "new":
        posts = posts.order_by(Submission.created_utc.desc())
    elif sort == "old":
        posts = posts.order_by(Submission.created_utc.asc())
    elif sort == "disputed":
        posts = posts.order_by(Submission.score_disputed.desc())
    elif sort == "top":
        posts = posts.order_by(Submission.score_top.desc())
    elif sort == "activity":
        posts = posts.order_by(Submission.score_activity.desc())
    else:
        abort(422)
    
    posts = [x[0] for x in posts.offset(25 * (page - 1)).limit(26).all()]
    
    next_exists = (len(posts) == 26)
    posts = posts[0:25]

    posts = get_posts(posts,
                      sort=sort,
                      v=v)

    return {'html': lambda: render_template("home.html",
                                            b=None,
                                            v=v,
                                            time_filter=t,
                                            listing=posts,
                                            next_exists=next_exists,
                                            sort_method=sort,
                                            page=page
                                           ),
            'api': lambda: jsonify({"data": [x.json for x in posts],
                                    "next_exists": next_exists})}

@app.route("/create_guild", methods=["GET"])
@is_not_banned
@no_negative_balance("html")
def create_board_get(v):
    if not v.can_make_guild:
        return render_template("message.html",
                               v=v,
                               title=f"You already lead {app.config['MAX_GUILD_COUNT']} guilds." if not v.can_join_gms else "Unable to make a guild. For now.",
                               message="You need to step down from a guild before you can make any more." if not v.can_join_gms else "You need more Reputation.")

    # check # recent boards made by user
    cutoff = int(time.time()) - 60 * 60 * 24
    recent = g.db.query(Board).filter(
        Board.creator_id == v.id,
        Board.created_utc >= cutoff).all()
    if v.admin_level<3 and len([x for x in recent]) >= 2:
        return render_template("message.html",
                               v=v,
                               title="You need to wait a bit.",
                               message="You can only create up to 2 guilds per day. Try again later."
                               ), 429

    return render_template(
        "make_board.html", 
        v=v,
        categories=CATEGORIES
        )


@app.route("/api/board_available/<name>", methods=["GET"])
@app.route("/api/v1/board_available/<name>", methods=["GET"])
@auth_desired
@api()
def api_board_available(name, v):
    if get_guild(name, graceful=True) or not re.match(valid_board_regex, name):
        return jsonify({"board": name, "available": False})
    else:
        return jsonify({"board": name, "available": True})


@app.route("/create_guild", methods=["POST"])
@app.post("/api/v2/guilds")
@is_not_banned
@no_negative_balance("html")
@api("create")
@validate_formkey
def create_board_post(v):
    """
Create a Guild

Required form data:
* `name` - Name of Guild to create

Optional form data:
* `description` - Guild description
    """

    if not v.can_make_guild:
        return render_template("make_board.html",
                               title="Unable to make board",
                               error="You need more Reputation before you can make a Guild."
                               )

    board_name = request.form.get("name")
    board_name = board_name.lstrip("+")
    description = request.form.get("description")

    if not re.match(valid_board_regex, board_name):
        return render_template("make_board.html",
                               v=v,
                               error="Guild names must be 3-25 letters or numbers.",
                               description=description
                               )

    # check name
    if get_guild(board_name, graceful=True):
        return render_template("make_board.html",
                               v=v,
                               error="That Guild already exists.",
                               description=description
                               )

    # check # recent boards made by user
    cutoff = int(time.time()) - 60 * 60 * 24
    alt_ids=[x.id for x in v.alts]
    user_ids=[v.id]+alt_ids
    recent = g.db.query(Board).filter(
        Board.creator_id.in_(user_ids),
        Board.created_utc >= cutoff).all()
    if v.admin_level<3 and len([x for x in recent]) >= 2:
        return render_template("message.html",
                               title="You need to wait a bit.",
                               message="You can only create up to 2 guilds per day. Try again later."
                               ), 429

    subcat=int(request.form.get("category",0))
    subcat=g.db.query(SubCategory).filter_by(id=subcat).first()
    if not subcat:
        return render_template("message.html",
                               title="Category required.",
                               message="You need to select a category."
                               ), 400


    with CustomRenderer() as renderer:
        description_md = renderer.render(mistletoe.Document(description))
    description_html = sanitize(description_md, linkgen=True)

    # make the board

    new_board = Board(name=board_name,
                      description=description,
                      description_html=description_html,
                      over_18=bool(request.form.get("over_18", "")),
                      creator_id=v.id,
                      subcat_id=subcat.id
                      )

    g.db.add(new_board)

    g.db.commit()

    # add user as mod
    mod = ModRelationship(user_id=v.id,
                          board_id=new_board.id,
                          accepted=True,
                          perm_full=True,
                          perm_access=True,
                          perm_content=True,
                          perm_appearance=True,
                          perm_config=True)
    g.db.add(mod)

    # add subscription for user
    sub = Subscription(user_id=v.id,
                       board_id=new_board.id)
    g.db.add(sub)

    #add guild creation mod log entry
    ma = ModAction(
        user_id=v.id,
        board_id=new_board.id,
        kind="create_guild",
        )
    g.db.add(ma)

    # clear cache
    cache.delete_memoized(guild_ids, sort="new")

    return redirect(new_board.permalink)


@app.route("/r/<name>")
def reddit_moment_redirect(name):
    return redirect(f"/+{name}")


@app.route("/+<guildname>", methods=["GET"])
@app.route("/api/v1/guild/<guildname>/listing", methods=["GET"])
@app.get("/api/v2/guilds/<guildname>/submissions")
@auth_desired
@api("read")
def board_name(guildname, v):
    """
Get a guild's submissions

URL path parameter:
* `guildname` - The name of the guild

Optional query parameters:
* `page` - Page number. Contents are returned in pages of 25 entries. Default `1`.
* `sort` - Sort order. One of `hot`, `top`, `new`, `old`, `disputed`, and `activity`. Default `hot`.
* `t` - Time filter. One of `day`, `week`, `month`, `year`, and `all`. Default `all`.
    """

    board = get_guild(guildname, v=v)

    #print(board.is_subscribed)

    #if not board.name == name and not request.path.startswith('/api/v1'):
        #return redirect(request.path.replace(name, board.name))

    if board.is_banned and not (v and v.admin_level >= 3):
        return {'html': lambda: (render_template("board_banned.html",
                                                 v=v,
                                                 b=board,
                                                 p=True
                                                 ), 410),
                'api': lambda: (jsonify({'error': f'410 Gone - +{board.name} is banned.'}), 410)
                }
    if board.over_18 and not (v and v.over_18) and not session_over18(board):
        t = int(time.time())
        return {'html': lambda: render_template("errors/nsfw.html",
                                                v=v,
                                                t=t,
                                                lo_formkey=make_logged_out_formkey(
                                                    t),
                                                board=board
                                                ),
                'api': lambda: jsonify({'error': f'+{board.name} is NSFW.'})
                }

    if v:
        defaultsorting = v.defaultsorting
        defaulttime = v.defaulttime
    else:
        defaultsorting = "hot"
        defaulttime = "all"

    sort = request.args.get("sort", defaultsorting)
    t = request.args.get("t", defaulttime)
    page = int(request.args.get("page", 1))
    ignore_pinned = bool(request.args.get("ignore_pinned", False))

    ids = board.idlist(sort=sort,
                       t=t,
                       page=page,
                       nsfw=(v and v.over_18) or session_over18(board),
                       v=v,
                       gt=int(request.args.get("utc_greater_than", 0)),
                       lt=int(request.args.get("utc_less_than", 0))
                       )

    next_exists = (len(ids) == 26)
    ids = ids[0:25]

    if page == 1 and sort != "new" and sort != "old" and not ignore_pinned:
        if (v and v.over_18) or session_over18(board):
            stickies = g.db.query(Submission.id).filter_by(board_id=board.id,
                                                        is_banned=False,
                                                        is_pinned=True,
                                                        deleted_utc=0).order_by(Submission.id.asc()).limit(4)
        else:
            stickies = g.db.query(Submission.id).filter_by(board_id=board.id,
                                                       is_banned=False,
                                                       is_pinned=True,
                                                       over_18=False,
                                                       deleted_utc=0).order_by(Submission.id.asc()).limit(4)
        stickies = [x[0] for x in stickies]
        ids = stickies + ids

    posts = get_posts(ids,
                      sort=sort,
                      v=v)

    return {'html': lambda: render_template("board.html",
                                            b=board,
                                            v=v,
                                            time_filter=t,
                                            listing=posts,
                                            next_exists=next_exists,
                                            sort_method=sort,
                                            page=page#,
                                            #is_subscribed=board.is_subscribed
                                            ),
            'api': lambda: jsonify({"data": [x.json for x in posts],
                                    "next_exists": next_exists
                                    }
                                   )
            }    

@app.route("/mod/distinguish_post/<guildname>/<pid>", methods=["POST"])
@app.route("/api/v1/distinguish_post/<guildname>/<pid>", methods=["POST"])
@app.patch("/api/v2/guilds/<guildname>/submissions/<pid>/herald")
@auth_required
@is_guildmaster("content")
@api("guildmaster")
def mod_distinguish_post(guildname, pid, board, v):

    """
Toggle Herald status on your post.

URL path parameters:
* `guildname` - The guild in which you are a guildmaster
* `pid` - The base 36 post ID
"""

    #print(pid, board, v)

    post = get_post(pid, v=v)

    if not post.board_id==board.id:
        abort(400)

    if post.author_id != v.id:
        abort(403)

    if post.gm_distinguish:
        post.gm_distinguish = 0
    else:
        post.gm_distinguish = board.id
    g.db.add(post)

    ma=ModAction(
        kind="herald_post" if post.gm_distinguish else "unherald_post",
        user_id=v.id,
        target_submission_id=post.id,
        board_id=board.id
        )
    g.db.add(ma)

    return "", 204

@app.route("/mod/distinguish_comment/<guildname>/<cid>", methods=["POST"])
@app.route("/api/v1/distinguish_comment/<guildname>/<cid>", methods=["POST"])
@app.patch("/api/v2/guilds/<guildname>/comments/<cid>/herald")
@auth_required
@is_guildmaster('content')
@api("guildmaster")
def mod_distinguish_comment(guildname, cid, board, v):
    """
Toggle Herald status on your comment.

URL path parameters:
* `guildname` - The guild in which you are a guildmaster
* `cid` - The base 36 comment ID
"""
    comment = get_comment(cid, v=v)

    if not comment.post.board_id==board.id:
        abort(400)

    if comment.author_id != v.id:
        abort(403)

    if comment.gm_distinguish:
        comment.gm_distinguish = 0
    else:
        comment.gm_distinguish = board.id

    g.db.add(comment)

    ma=ModAction(
        kind="herald_comment" if comment.gm_distinguish else "unherald_comment",
        user_id=v.id,
        target_comment_id=comment.id,
        board_id=board.id
        )
    g.db.add(ma)

    html=render_template(
                "comments.html",
                v=v,
                comments=[comment],
                render_replies=False,
                is_allowed_to_comment=True
                )

    html=str(BeautifulSoup(html, features="html.parser").find(id=f"comment-{comment.base36id}-only"))

    return jsonify({"html":html})

@app.route("/mod/kick/<guildname>/<pid>", methods=["POST"])
@app.route("/api/v1/kick/<guildname>/<pid>", methods=["POST"])
@app.patch("/api/v2/guilds/<guildname>/submissions/<pid>/kick")
@auth_required
@is_guildmaster('content')
@api("guildmaster")
@validate_formkey
def mod_kick_bid_pid(guildname, pid, board, v):
    """
Kick a post from your guild.

URL path parameters:
* `guildname` - The guild in which you are a guildmaster
* `pid` - The base 36 post ID
"""
    post = get_post(pid)

    if not post.board_id == board.id:
        abort(400)

    post.board_id = 1
    #post.guild_name = "general"
    post.is_pinned = False
    g.db.add(post)

    cache.delete_memoized(Board.idlist, board)

    ma=ModAction(
        kind="kick_post",
        user_id=v.id,
        target_submission_id=post.id,
        board_id=board.id
        )
    g.db.add(ma)
    g.db.commit()

    return jsonify({
        'data':render_template(
            "submission_listing.html",
            v=v,
            listing=[post])
        })


@app.route("/mod/accept/<guildname>/<pid>", methods=["POST"])
@app.route("/api/v1/accept/<guildname>/<pid>", methods=["POST"])
@app.patch("/api/v2/guilds/<guildname>/submissions/<pid>/approve")
@auth_required
@is_guildmaster('content')
@api("guildmaster")
@validate_formkey
def mod_accept_bid_pid(guildname, pid, board, v):
    """
Dismiss reports on submission and keep it in your guild.

URL path parameters:
* `guildname` - The guild in which you are a guildmaster
* `pid` - The base 36 id of the post
"""

    post = get_post(pid)
    if not post.board_id == board.id:
        abort(400)

    if post.mod_approved:
        return ({"error":"Already approved"})

    post.mod_approved = v.id
    g.db.add(post)

    ma=ModAction(
        kind="approve_post",
        user_id=v.id,
        target_submission_id=post.id,
        board_id=board.id
        )
    g.db.add(ma)

    return "", 204


@app.route("/mod/exile/<guildname>", methods=["POST"])
@app.route("/api/v1/exile/<guildname>", methods=["POST"])
@app.post("/api/v2/guilds/<guildname>/exiles")
@auth_required
@is_guildmaster('access')
@api("guildmaster")
@validate_formkey
def mod_ban_bid_user(guildname, board, v):
    """
Exile a user from a Guild

URL path parameters:
* `guildname` - The guild in which you are a guildmaster

Required form data:
* `username` - The username of the user to exile.

Optional form data:
* `thing` - The fullname of the post or comment to associate with the exile
"""

    user = get_user(request.values.get("username"), graceful=True)

    #check for post/comment
    item = request.values.get("thing")
    if item:
        item=get_from_fullname(item)

        if item.original_board_id != board.id:
            return jsonify({"error":f"That was originally created in +{item.original_board.name}, not +{board.name}"}), 400

    if not user or user.is_deleted:
        return jsonify({"error": "That user doesn't exist."}), 404

    if user.id == v.id:
        return jsonify({"error": "You can't exile yourself."}), 409

    if g.db.query(BanRelationship).filter_by(user_id=user.id, board_id=board.id, is_active=True).first():
        return jsonify({"error": f"@{user.username} is already exiled from +{board.name}."}), 409

    if board.has_contributor(user):
        return jsonify({"error": f"@{user.username} is an approved contributor to +{board.name} and can't currently be exiled."}), 409

    if board.has_mod(user):
        return jsonify({"error": "You can't exile other guildmasters."}), 409

    # you can only exile a user who has previously participated in the guild
    if not board.has_participant(user):
        return jsonify({"error": f"@{user.username} hasn't participated in +{board.name}."}), 403

    if item:
        if isinstance(item, Submission):
            target_submission_id=item.id
            target_comment_id=None
        elif isinstance(item, Comment):
            target_submission_id=None
            target_comment_id=item.id
    else:
        target_submission_id=None
        target_comment_id=None


    # check for an existing deactivated ban
    existing_ban = g.db.query(BanRelationship).filter_by(
        user_id=user.id, board_id=board.id, is_active=False).first()
    if existing_ban:
        existing_ban.is_active = True
        existing_ban.created_utc = int(time.time())
        existing_ban.banning_mod_id = v.id
        existing_ban.target_submission_id=target_submission_id
        existing_ban.target_comment_id=target_comment_id
        g.db.add(existing_ban)
    else:
        new_ban = BanRelationship(user_id=user.id,
                                  board_id=board.id,
                                  banning_mod_id=v.id,
                                  is_active=True)
        g.db.add(new_ban)

        text = f"You have been exiled from +{board.name}.\n\nNone of your existing posts or comments have been removed, however, you will not be able to make any new posts or comments in +{board.name}."
        if item:
            text+= "\n\nYou were exiled for [this "
            text+= "comment" if isinstance(item, Comment) else "post"
            text+= f"]({item.permalink})."

        send_notification(user, text)


    ma=ModAction(
        kind="exile_user",
        user_id=v.id,
        target_user_id=user.id,
        board_id=board.id,
        target_submission_id=target_submission_id,
        target_comment_id=target_comment_id
        )
    g.db.add(ma)

    g.db.commit()


    if request.args.get("toast"):
        return jsonify({"message": f"@{user.username} was exiled from +{board.name}"})
    else:
        return "", 204


@app.route("/mod/unexile/<guildname>/<username>", methods=["POST"])
@app.route("/api/v1/unexile/<guildname>/<username>", methods=["POST"])
@app.delete("/api/v2/guilds/<guildname>/exiles/<username>")
@auth_required
@is_guildmaster('access')
@api("guildmaster")
@validate_formkey
def mod_unban_bid_user(guildname, username, board, v):
    """
Un-exile a user from a Guild

URL path parameters:
* `guildname` - The guild in which you are a guildmaster
* `username` - The username of the user to exile.
"""

    user = get_user(username)

    x =  g.db.query(BanRelationship).filter_by(board_id=board.id, user_id=user.id, is_active=True).first()

    if not x:
        abort(409)

    x.is_active = False

    g.db.add(x)

    ma=ModAction(
        kind="unexile_user",
        user_id=v.id,
        target_user_id=user.id,
        board_id=board.id
        )
    g.db.add(ma)

    return "", 204


@app.route("/user/kick/<pid>", methods=["POST"])
@app.patch("/api/v2/me/submissions/<pid>/unyank")
@auth_required
@api("update")
@validate_formkey
def user_kick_pid(pid, v):
    """
Un-yank your post back to +general

URL path parameters:
* `pid` - The base 36 id of the post to un-yank
"""

    post = get_post(pid)

    current_board = post.board

    if not post.author_id == v.id:
        abort(403)

    if post.board_id == post.original_board_id:
        abort(403)

    if post.board_id == 1:
        abort(400)

    # block further yanks to the same board
    new_rel = PostRelationship(post_id=post.id,
                               board_id=post.board.id)
    g.db.add(new_rel)

    post.board_id = 1
    post.is_pinned = False

    g.db.add(post)

    #un-pin any comments
    pinned_comments = g.db.query(Comment).filter_by(
        is_pinned=True,
        parent_submission=post.id
        ).all()
    for comment in pinned_comments:
        comment.is_pinned=False
        g.db.add(comment)

    g.db.commit()

    # clear board's listing caches
    cache.delete_memoized(Board.idlist, current_board)

    return "", 204


@app.route("/mod/take/<pid>", methods=["POST"])
@app.post("/api/v1/mod/take/<pid>")
#@app.patch("/api/v2/guilds/<guildname>/submissions/<pid>/yank")
@auth_required
@is_guildmaster("content")
@validate_formkey
@api("guildmaster")
def mod_take_pid(pid, board, v):

    bid = request.form.get("board_id", request.form.get("guild", None))
    if not bid:
        abort(400)

    post = get_post(pid, graceful=True)
    if not post:
        return jsonify({"error": "invalid post id"}), 404

    #check cooldowns
    now=int(time.time())
    if post.original_board_id != board.id and post.author_id != v.id:
        #look for modlog action with either board or user

        recent_yank = g.db.query(ModAction).filter(
            #yank records for the guild or user within the last hour..
            ModAction.kind=="yank_post",
            ModAction.created_utc>now-3600,
            or_(
                ModAction.user_id==v.id,
                ModAction.board_id==board.id
                )
            ).join(
            ModAction.target_post
            #...which were not originally from the user or guild
            ).filter(
                Submission.original_board_id!=board.id,
                Submission.author_id!=v.id
            ).order_by(
                ModAction.user_id==v.id,
                ModAction.created_utc.desc()
            ).options(
                contains_eager(ModAction.target_post)
            ).first()


        if recent_yank:
            if recent_yank.user_id==v.id:
                return jsonify({'error':f"You've yanked a post recently. You need to wait 1 hour between yanks."}), 401
            else:
                return jsonify({'error':f"+{board.name} has yanked a post recently. The Guild needs to wait 1 hour between yanks."}), 401


    if board.is_banned:
        return jsonify({'error': f"+{board.name} is banned. You can't yank anything there."}), 403

    if not post.board_id == 1:
        return jsonify({'error': f"This post is no longer in +general"}), 403

    if not board.has_mod(v):
        return jsonify({'error': f"You are no longer a guildmaster of +{board.name}"}), 403

    if board.has_ban(post.author):
        return jsonify({'error': f"@{post.author.username} is exiled from +{board.name}, so you can't yank their post there."}), 403

    if post.author.any_block_exists(v):
        return jsonify({'error': f"You can't yank @{post.author.username}'s content."}), 403

    if not board.can_take(post):
        return jsonify({'error': f"You can't yank this particular post to +{board.name}."}), 403

    if board.is_private and post.original_board_id != board.id:
        return jsonify({'error': f"+{board.name} is private, so you can only yank content that started there."}), 403

    post.board_id = board.id
    post.guild_name = board.name
    g.db.add(post)

    if post.original_board_id != board.id and post.author_id != v.id:

        notif_text=f"Your post [{post.title}]({post.permalink}) has been Yanked from +general to +{board.name}.\n\nIf you don't want it there, just click `Remove from +{board.name}` on the post."
        send_notification(post.author, notif_text)
        g.db.commit()

    # clear board's listing caches
    cache.delete_memoized(Board.idlist, board)

    ma=ModAction(
        kind="yank_post",
        user_id=v.id,
        target_submission_id=post.id,
        board_id=board.id
        )
    g.db.add(ma)

    return "", 204


@app.route("/mod/invite_mod/<bid>", methods=["POST"])
@auth_required
@is_guildmaster("full")
@validate_formkey
def mod_invite_username(bid, board, v):

    username = request.form.get("username", '').lstrip('@')
    user = get_user(username)
    if not user:
        return jsonify({"error": "That user doesn't exist."}), 404

    if board.has_ban(user):
        return jsonify({"error": f"@{user.username} is exiled from +{board.name} and can't currently become a guildmaster."}), 409
    if not user.can_join_gms:
        return jsonify({"error": f"@{user.username} already leads enough guilds."}), 409
        
    if user.is_deleted:
        return jsonify({"error": f"@{user.username} is deleted."}), 409
        
    if user.is_suspended:
        return jsonify({"error": f"@{user.username} is suspended."}), 409

    x = g.db.query(ModRelationship).filter_by(
        user_id=user.id, board_id=board.id).first()

    if x and x.accepted:
        return jsonify({"error": f"@{user.username} is already a mod."}), 409

    if x and not x.invite_rescinded:
        return jsonify({"error": f"@{user.username} has already been invited."}), 409

    if x:

        x.invite_rescinded = False
        g.db.add(x)

    else:
        x = ModRelationship(
            user_id=user.id,
            board_id=board.id,
            accepted=False,
            perm_full=True,
            perm_content=True,
            perm_appearance=True,
            perm_access=True,
            perm_config=True
            )

        text = f"You have been invited to join +{board.name} as a guildmaster. You can [click here]({board.permalink}/mod/mods) and accept this invitation. Or, if you weren't expecting this, you can ignore it."
        send_notification(user, text)

        g.db.add(x)

    ma=ModAction(
        kind="invite_mod",
        user_id=v.id,
        target_user_id=user.id,
        board_id=board.id,
        note=x.permchangelist
        )
    g.db.add(ma)

    return "", 204


@app.route("/mod/<bid>/rescind/<username>", methods=["POST"])
@auth_required
@is_guildmaster("full")
@validate_formkey
def mod_rescind_bid_username(bid, username, board, v):

    user = get_user(username)

    invitation = g.db.query(ModRelationship).filter_by(board_id=board.id,
                                                       user_id=user.id,
                                                       accepted=False).first()
    if not invitation:
        abort(404)

    invitation.invite_rescinded = True

    g.db.add(invitation)
    ma=ModAction(
        kind="uninvite_mod",
        user_id=v.id,
        target_user_id=user.id,
        board_id=board.id
        )
    g.db.add(ma)
    return "", 204


@app.route("/mod/accept/<bid>", methods=["POST"])
@app.route("/api/v1/accept_invite/<bid>", methods=["POST"])
@auth_required
@validate_formkey
@api("guildmaster")
def mod_accept_board(bid, v):

    board = get_board(bid, v=v)

    x = g.db.query(ModRelationship
        ).options(
        lazyload('*')
        ).filter_by(
        user_id=v.id,
        board_id=board.id,
        accepted=False,
        invite_rescinded=False
        ).first()

    if not x:
        return jsonify({"error":"Unable to find invitation"}), 404

    if not v.can_join_gms:
        return jsonify({"error": f"You already lead enough guilds."}), 409
    if board.has_ban(v):
        return jsonify({"error": f"You are exiled from +{board.name} and can't currently become a guildmaster."}), 409
    x.accepted = True
    x.created_utc=int(time.time())
    g.db.add(x)

    ma=ModAction(
        kind="accept_mod_invite",
        user_id=v.id,
        target_user_id=v.id,
        board_id=board.id
        )
    g.db.add(ma)

    g.db.commit()
    
    return "", 204

@app.route("/mod/<bid>/step_down", methods=["POST"])
@auth_required
@is_guildmaster()
@validate_formkey
def mod_step_down(bid, board, v):


    v_mod = board.has_mod(v)

    if not v_mod:
        abort(404)

    g.db.delete(v_mod)

    ma=ModAction(
        kind="dethrone_self",
        user_id=v.id,
        target_user_id=v.id,
        board_id=board.id
        )
    g.db.add(ma) 

    g.db.flush()

    if board.mods_count == 0:
        board.is_private = False
        board.restricted_posting = False
        board.all_opt_out = False
        g.db.add(board)

    return "", 204



@app.route("/mod/<bid>/remove/<username>", methods=["POST"])
@auth_required
@is_guildmaster("full")
@validate_formkey
def mod_remove_username(bid, username, board, v):

    user = get_user(username)

    u_mod = board.has_mod(user)
    v_mod = board.has_mod(v)

    if not u_mod:
        abort(400)
    elif not v_mod:
        abort(400)

    if not u_mod.board_id==board.id:
        abort(400)

    if not v_mod.board_id==board.id:
        abort(400)

    if v_mod.id > u_mod.id:
        abort(403)

    g.db.delete(u_mod)

    ma=ModAction(
        kind="remove_mod",
        user_id=v.id,
        target_user_id=user.id,
        board_id=board.id
        )
    g.db.add(ma)

    return "", 204


@app.route("/mod/is_banned/<bid>/<username>", methods=["GET"])
@auth_required
@is_guildmaster("access")
@validate_formkey
def mod_is_banned_board_username(bid, username, board, v):

    user = get_user(username)

    result = {"board": board.name,
              "user": user.username}

    if board.has_ban(user):
        result["is_banned"] = True
    else:
        result["is_banned"] = False

    return jsonify(result)


@app.route("/mod/<bid>/settings/over_18", methods=["POST"])
@auth_required
@is_guildmaster("config")
@validate_formkey
def mod_bid_settings_nsfw(bid, board, v):

    # nsfw
    board.over_18 = bool(request.form.get("over_18", False) == 'true')

    g.db.add(board)

    ma=ModAction(
        kind="update_settings",
        user_id=v.id,
        board_id=board.id,
        note=f"over_18={board.over_18}"
        )
    g.db.add(ma)
    return "", 204


@app.route("/mod/<bid>/settings/opt_out", methods=["POST"])
@auth_required
@is_guildmaster("config")
@validate_formkey
def mod_bid_settings_optout(bid, board, v):

    # nsfw
    board.all_opt_out = bool(request.form.get("opt_out", False) == 'true')

    g.db.add(board)

    ma=ModAction(
        kind="update_settings",
        user_id=v.id,
        board_id=board.id,
        note=f"all_opt_out={board.all_opt_out}"
        )
    g.db.add(ma)
    return "", 204

@app.route("/mod/<bid>/settings/disallowbots", methods=["POST"])
@auth_required
@is_guildmaster("config")
@validate_formkey
def mod_bid_settings_disallowbots(bid, board, v):

    # toggle disallowing bots setting
    board.disallowbots = bool(
        request.form.get(
            "disallowbots",
            False) == 'true')
    g.db.add(board)
    ma=ModAction(
        kind="update_settings",
        user_id=v.id,
        board_id=board.id,
        note=f"disallow_bots={board.disallowbots}"
    )
    g.db.add(ma)
    return "", 204

@app.route("/mod/<bid>/settings/public_chat", methods=["POST"])
@auth_required
@is_guildmaster("config", "chat")
@validate_formkey
def mod_bid_settings_public_chat(bid, board, v):

    # nsfw
    board.public_chat = bool(request.form.get("public_chat", False) == 'true')

    g.db.add(board)

    ma=ModAction(
        kind="update_settings",
        user_id=v.id,
        board_id=board.id,
        note=f"public_chat={board.public_chat}"
        )
    g.db.add(ma)
    return "", 204

@app.route("/mod/<bid>/settings/restricted", methods=["POST"])
@auth_required
@is_guildmaster("config")
@validate_formkey
def mod_bid_settings_restricted(bid, board, v):

    # toggle restricted setting
    board.restricted_posting = bool(
        request.form.get(
            "restrictswitch",
            False) == 'true')

    g.db.add(board)

    ma=ModAction(
        kind="update_settings",
        user_id=v.id,
        board_id=board.id,
        note=f"restricted={board.restricted_posting}"
        )
    g.db.add(ma)
    return "", 204


@app.route("/mod/<bid>/settings/private", methods=["POST"])
@auth_required
@is_guildmaster("config")
@validate_formkey
def mod_bid_settings_private(bid, board, v):

    # toggle privacy setting
    board.is_private = bool(request.form.get("guildprivacy", False) == 'true')

    g.db.add(board)
    g.db.flush()
    board.stored_subscriber_count=board.subscriber_count
    g.db.add(board)
    g.db.commit()

    ma=ModAction(
        kind="update_settings",
        user_id=v.id,
        board_id=board.id,
        note=f"private={board.is_private}"
        )
    g.db.add(ma)


    return "", 204


@app.route("/mod/<bid>/settings/name", methods=["POST"])
@auth_required
@is_guildmaster("config")
@validate_formkey
def mod_bid_settings_name(bid, board, v):
    # name capitalization
    new_name = request.form.get("guild_name", "").lstrip("+")

    if new_name.lower() == board.name.lower():
        board.name = new_name
        g.db.add(board)


        ma=ModAction(
            kind="update_settings",
            user_id=v.id,
            board_id=board.id,
            note=f"name={board.name}"
            )
        g.db.add(ma)
        return "", 204
    else:
        return "", 422


@app.route("/mod/<bid>/settings/description", methods=["POST"])
@auth_required
@is_guildmaster("config")
@validate_formkey
def mod_bid_settings_description(bid, board, v):
    # board description
    description = request.form.get("description")
    with CustomRenderer() as renderer:
        description_md = renderer.render(mistletoe.Document(description))
    description_html = sanitize(description_md, linkgen=True)

    board.description = description
    board.description_html = description_html

    g.db.add(board)

    ma=ModAction(
        kind="update_settings",
        user_id=v.id,
        board_id=board.id,
        note=f"update description"
        )
    g.db.add(ma)
    return "", 204


@app.route("/mod/<bid>/settings/banner", methods=["POST"])
@auth_required
@is_guildmaster("appearance")
@validate_formkey
def mod_settings_toggle_banner(bid, board, v):
    # toggle show/hide banner
    board.hide_banner_data = bool(
        request.form.get(
            "hidebanner",
            False) == 'true')

    g.db.add(board)
    return "", 204


@app.route("/mod/<bid>/settings/add_rule", methods=["POST"])
@auth_required
@is_guildmaster("full")
@validate_formkey
def mod_add_rule(bid, board, v):
    # board description
    rule = request.form.get("rule1")
    rule2 = request.form.get("rule2")
    if not rule2:
        with CustomRenderer() as renderer:
            rule_md = renderer.render(mistletoe.Document(rule))
        rule_html = sanitize(rule_md, linkgen=True)

        new_rule = Rules(board_id=bid, rule_body=rule, rule_html=rule_html)
        g.db.add(new_rule)

    else:
        """
        im guessing here we should
        do a loop for
        adding multiple rules
        """
        pass

    return "", 204


@app.route("/mod/<bid>/settings/edit_rule", methods=["POST"])
@auth_required
@is_guildmaster("full")
@validate_formkey
def mod_edit_rule(bid, board, v):
    r = base36decode(request.form.get("rid"))
    r = g.db.query(Rules).filter_by(id=r)

    if not r:
        abort(500)

    if board.is_banned:
        abort(403)

    if board.has_ban(v):
        abort(403)

    body = request.form.get("body", "")
    with CustomRenderer() as renderer:
        body_md = renderer.render(mistletoe.Document(body))
    body_html = sanitize(body_md, linkgen=True)

    r.rule_body = body
    r.rule_html = body_html
    r.edited_utc = int(time.time())

    g.db.add(r)

    return "", 204


@app.route("/+<guildname>/mod/settings", methods=["GET"])
@auth_required
@is_guildmaster("config")
def board_about_settings(guildname, board, v):

    return render_template(
        "guild/settings.html",
        v=v,
        b=board,
        categories=CATEGORIES
        )


@app.route("/+<guildname>/mod/appearance", methods=["GET"])
@auth_required
@is_guildmaster("appearance")
def board_about_appearance(guildname, board, v):

    return render_template("guild/appearance.html", v=v, b=board)


@app.route("/+<guildname>/mod/mods", methods=["GET"])
@app.route("/api/vue/+<guildname>/mod/mods",  methods=["GET"])
@app.route("/api/v1/<guildname>/mod/mods", methods=["GET"])
@app.get("/api/v2/guilds/<guildname>/mods")
@auth_desired
@api("read")
def board_about_mods(guildname, v):
    """
Get a list of users who are guildmasters of a guild.

URL path parameters:
* `guildname` - The name of a guild
"""

    board = get_guild(guildname, v=v)

    if board.is_banned:
        return {
        "html":lambda:(render_template("board_banned.html", v=v, b=board), 403),
        "api":lambda:(jsonify({"error":f"+{board.name} is banned"}), 403)
        }

    me = board.has_mod(v)

    return {
        "html":lambda:render_template("guild/mods.html", v=v, b=board, me=me),
        "api":lambda:jsonify({"data":[x.json for x in board.mods_list]})
        }

@app.route("/+<guildname>/mod/css", methods=["GET"])
@app.route("/api/vue/+<guildname>/mod/css",  methods=["GET"])
@app.route("/api/v1/<guildname>/mod/css", methods=["GET"])
@auth_desired
@api("read")
def board_about_css(guildname, v):

    board = get_guild(guildname, v=v)

    if board.is_banned:
        return {
        "html":lambda:(render_template("board_banned.html", v=v, b=board), 403),
        "api":lambda:(jsonify({"error":f"+{board.name} is banned"}), 403)
        }

    me = board.has_mod(v)

    return {
        "html":lambda:render_template("guild/css.html", v=v, b=board, me=me),
        "api":lambda:jsonify({"data":board.css})
        }

@app.post("/mod/<bid>/settings/css")
@auth_required
@is_guildmaster("config", "appearance")
@api("guildmaster")
def board_edit_css(bid, board, v):

    new_css = request.form.get("css").replace('\\','')

    #css validation / sanitization
    parser=cssutils.CSSParser(
        raiseExceptions=True,
        fetcher= lambda url: None
        )
    try:
        css = parser.parseString(
            new_css
            )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    allowed_rules=[
        cssutils.css.CSSComment,
        cssutils.css.CSSFontFaceRule,
        cssutils.css.MarginRule,
        cssutils.css.CSSMediaRule,
        cssutils.css.CSSStyleRule,
        cssutils.css.CSSUnknownRule,
        cssutils.css.CSSStyleDeclaration,
        cssutils.css.CSSVariablesRule
    ]

    def clean_block(rule):
        if not any([isinstance(rule, x) for x in allowed_rules]):
            return jsonify({"error": f"Invalid rule: {str(rule)}"}), 422
        
        if isinstance(rule, cssutils.css.CSSStyleRule):
            
            for property in rule.style.children():
                for pv in property.propertyValue:
                    if isinstance(pv, cssutils.css.URIValue):
                        domain = urlparse(pv.uri).netloc

                        if domain != app.config["S3_BUCKET"]:
                            return jsonify({"error":"No external links allowed."}), 422

        if getattr(rule, "children", None):
            for child in rule.children():
                clean_block(child)
         
        return False


    for rule in css:
        x=clean_block(rule)
        if x:
            return x

    css=css.cssText.decode('utf-8')

    board.css = css
    board.css_nonce += 1

    g.db.add(board)
    
    ma=ModAction(
        kind="update_stylesheet",
        user_id=v.id,
        board_id=board.id,
    )
    g.db.add(ma)
    g.db.commit()

    return '', 204

@app.get("/+<guildname>/css")
def board_get_css(guildname):

    board=get_guild(guildname)

    css="@media (min-width: 992px) {\n" + board.css +"\n}"



    resp=make_response(css)
    resp.headers.add("Content-Type", "text/css")
    return resp


@app.route("/+<guildname>/mod/exiled", methods=["GET"])
@app.route("/api/v1/<guildname>/mod/exiled", methods=["GET"])
@app.get("/api/v2/guilds/<guildname>/exiles")
@auth_required
@is_guildmaster("access")
@api("read", "guildmaster")
def board_about_exiled(guildname, board, v):
    """
View guild exile entries.

URL path parameters:
* `guildname` - The guild in which you are a guildmaster

Optional query parameters
* `page` - The page of items to view. Default `1`.
"""

    page = int(request.args.get("page", 1))

    bans = board.bans.filter_by(
        is_active=True
        ).join(BanRelationship.user
        ).filter(
        User.is_deleted==False
        ).order_by(
        BanRelationship.created_utc.desc()
        ).offset(25 * (page - 1)).limit(26).all()

    next_exists = (len(bans) == 26)
    bans = bans[0:25]

    return {
        "html":lambda:render_template(
            "guild/bans.html", 
            v=v, 
            b=board, 
            bans=bans,
            page=page,
            next_exists=next_exists
            ),
        "api":lambda:jsonify({"data":[x.json for x in bans]})
        }

@app.route("/+<guildname>/mod/chatbans", methods=["GET"])
@app.route("/api/v1/<guildname>/mod/chatbans", methods=["GET"])
@auth_required
@is_guildmaster("chat")
@api("read", "guildmaster")
def board_about_chatbanned(guildname, board, v):

    page = int(request.args.get("page", 1))

    bans = board.chatbans.order_by(
        ChatBan.created_utc.desc()).offset(25 * (page - 1)).limit(26)

    bans = [ban for ban in bans]
    next_exists = (len(bans) == 26)
    bans = bans[0:25]

    return {
        "html":lambda:render_template(
            "guild/chatbans.html", 
            v=v, 
            b=board, 
            bans=bans,
            page=page,
            next_exists=next_exists
            ),
        "api":lambda:jsonify({"data":[x.json for x in bans]})
        }



@app.route("/+<guildname>/mod/contributors", methods=["GET"])
@app.route("/api/v2/guilds/<guildname>/contributors")
@auth_required
@is_guildmaster("access")
@api("read", "guildmaster")
def board_about_contributors(guildname, board, v):
    """
View guild contributor list.

URL path parameters:
* `guildname` - The guild in which you are a guildmaster

Optional query parameters
* `page` - The page of items to view. Default `1`.
"""

    page = int(request.args.get("page", 1))

    contributors = board.contributors.filter_by(is_active=True).order_by(
        ContributorRelationship.created_utc.desc()).offset(25 * (page - 1)).limit(26)

    # Deleted users will still remove a spot on the page but this will stop them from cluttering it
    contributors = [x for x in contributors if not x.user.is_deleted]

    next_exists = (len(contributors) == 26)
    contributors = contributors[0:25]

    return {
        'html':
            lambda:render_template(
                "guild/contributors.html", 
                v=v,
                b=board, 
                contributors=contributors,
                page=page,
                next_exists=next_exists
                ),
        "api":lambda:jsonify({"data":[x.json for x in contributors]})
        }



@app.route("/api/subscribe/<guildname>", methods=["POST"])
@app.post("/api/v2/me/subscriptions/<guildname>")
@auth_required
def subscribe_board(guildname, v):
    """
Subscribe to a Guild.

URL path parameters:
* `guildname` - The name of a guild
"""

    board = get_guild(guildname, v=v)

    # check for existing subscription, canceled or otherwise
    sub = g.db.query(Subscription).filter_by(
        user_id=v.id, board_id=board.id).first()
    if sub:
        if sub.is_active:
            return jsonify({"error": f"You are already a member of +{board.name}"}), 409
        else:
            # reactivate canceled sub
            sub.is_active = True
            g.db.add(sub)

    else:

        new_sub = Subscription(user_id=v.id,
                               board_id=board.id)

        g.db.add(new_sub)

    g.db.flush()

    # clear your cached guild listings
    cache.delete_memoized(User.idlist, v, kind="board")

    # update board trending rank
    board.rank_trending = board.trending_rank
    board.stored_subscriber_count = board.subscriber_count
    g.db.add(board)

    return jsonify({"message": f"Joined +{board.name}"}), 200


@app.route("/api/unsubscribe/<guildname>", methods=["POST"])
@app.delete("/api/v2/me/subscriptions/<guildname>")
@auth_required
def unsubscribe_board(guildname, v):
    """
Unsubscribe from a Guild.

URL path parameters:
* `guildname` - The name of a guild
"""

    board = get_guild(guildname, v=v)

    # check for existing subscription
    sub = g.db.query(Subscription).filter_by(
        user_id=v.id, board_id=board.id).first()

    if not sub or not sub.is_active:
        return jsonify({"error": f"You aren't a member of +{board.name}"}), 409

    sub.is_active = False

    g.db.add(sub)
    g.db.flush()

    # clear your cached guild listings
    cache.delete_memoized(User.idlist, v, kind="board")

    board.rank_trending = board.trending_rank
    board.stored_subscriber_count = board.subscriber_count
    g.db.add(board)

    return jsonify({"message": f"Left +{board.name}"}), 200


@app.route("/+<guildname>/mod/queue", methods=["GET"])
@app.get("/api/v2/guilds/<guildname>/modqueue")
@auth_required
@api("read", "guildmaster")
@is_guildmaster("content")
def board_mod_queue(guildname, board, v):
    """
Get reported posts in a guild.

URL path parameters:
* `guildname` - The name of a guild
"""

    page = int(request.args.get("page", 1))

    ids = g.db.query(Submission.id).filter_by(board_id=board.id,
                                              is_banned=False,
                                              mod_approved=None,
                                              deleted_utc=0
                                              ).join(Report, Report.post_id == Submission.id)

    if not v.over_18:
        ids = ids.filter(Submission.over_18 == False)

    ids = ids.order_by(Submission.id.desc()).offset((page - 1) * 25).limit(26).all()

    ids = [x[0] for x in ids]

    next_exists = (len(ids) == 26)

    ids = ids[0:25]

    posts = get_posts(ids, v=v)

    return {"html":lambda:render_template("guild/reported_posts.html",
                           listing=posts,
                           next_exists=next_exists,
                           page=page,
                           v=v,
                           b=board),
            "api":lambda:jsonify({"data":[x.json for x in posts]})
            }


@app.route("/mod/queue", methods=["GET"])
@app.get("/api/v2/me/modqueue")
@auth_required
@api("read", "guildmaster")
def all_mod_queue(v):
    """Get reported posts in all of your guilds."""

    page = int(request.args.get("page", 1))

    board_ids = g.db.query(ModRelationship.board_id).filter(
        ModRelationship.user_id==v.id, 
        ModRelationship.accepted==True, 
        or_(ModRelationship.perm_content==True, ModRelationship.perm_full==True)
    ).subquery()

    ids = g.db.query(Submission.id).options(lazyload('*')).filter(Submission.board_id.in_(board_ids),
                                                                  Submission.mod_approved==None,
                                                                  Submission.is_banned == False,
                                                                  Submission.deleted_utc==0
                                                                  ).join(Report, Report.post_id == Submission.id)

    if not v.over_18:
        ids = ids.filter(Submission.over_18 == False)

    ids = ids.order_by(Submission.id.desc()).offset((page - 1) * 25).limit(26).all()
    
    ids = [x[0] for x in ids]
   
    next_exists = (len(ids) == 26)

    ids = ids[0:25]

    posts = get_posts(ids, v=v)

    return {"html":lambda:render_template("guild/reported_posts.html",
                           listing=posts,
                           next_exists=next_exists,
                           page=page,
                           v=v,
                           b=None),
            "api":lambda:jsonify({"data":[x.json for x in posts]})
            }


@app.route("/mod/<bid>/images/profile", methods=["POST"])
@auth_required
@is_guildmaster("appearance")
@validate_formkey
def mod_board_images_profile(bid, board, v):

    if request.headers.get("cf-ipcountry")=="T1" and not v.is_activated:
        return jsonfiy({"error":"You must have a verified email address to upload images via Tor."}), 401

    board.set_profile(request.files["profile"])

    # anti csam
    new_thread = threading.Thread(target=check_csam_url,
                                  args=(board.profile_url,
                                        v,
                                        lambda: board.del_profile()
                                        )
                                  )
    new_thread.start()

    ma=ModAction(
        kind="update_appearance",
        user_id=v.id,
        board_id=board.id,
        note=f"uploaded profile image"
        )
    g.db.add(ma)

    return redirect(f"/+{board.name}/mod/appearance?msg=Success#images")


@app.route("/mod/<bid>/images/banner", methods=["POST"])
@auth_required
@is_guildmaster("appearance")
@validate_formkey
def mod_board_images_banner(bid, board, v):

    if request.headers.get("cf-ipcountry")=="T1" and not v.is_activated:
        return jsonify({"error":"You must have a verified email address to upload images via Tor."}), 401

    board.set_banner(request.files["banner"])

    # anti csam
    new_thread = threading.Thread(target=check_csam_url,
                                  args=(board.banner_url,
                                        v,
                                        lambda: board.del_banner()
                                        )
                                  )
    new_thread.start()

    ma=ModAction(
        kind="update_appearance",
        user_id=v.id,
        board_id=board.id,
        note=f"uploaded banner image"
        )
    g.db.add(ma)

    return redirect(f"/+{board.name}/mod/appearance?msg=Success#images")


@app.route("/mod/<bid>/delete/profile", methods=["POST"])
@auth_required
@is_guildmaster("appearance")
@validate_formkey
def mod_board_images_delete_profile(bid, board, v):

    board.del_profile()

    ma=ModAction(
        kind="update_appearance",
        user_id=v.id,
        board_id=board.id,
        note=f"removed profile image"
        )
    g.db.add(ma)

    return redirect(f"/+{board.name}/mod/appearance?msg=Success#images")


@app.route("/mod/<bid>/delete/banner", methods=["POST"])
@auth_required
@is_guildmaster("appearance")
@validate_formkey
def mod_board_images_delete_banner(bid, board, v):

    board.del_banner()

    ma=ModAction(
        kind="update_appearance",
        user_id=v.id,
        board_id=board.id,
        note=f"removed banner image"
        )
    g.db.add(ma)

    return redirect(f"/+{board.name}/mod/appearance?msg=Success#images")


@app.route("/assets/<board_fullname>/<theme>/<x>.css", methods=["GET"])
@cache.memoize()
def board_css(board_fullname, theme, x):

    if theme not in ["main", "dark"]:
        abort(404)

    try:
        b36id=board_fullname.split('_')[1]
    except IndexError:
        #print(request.headers.get("Referer",request.headers.get("Referrer")))
        abort(400)

    board = get_board(b36id)

    if int(x) != board.color_nonce:
        return redirect(board.css_url)

    if theme=="main":
        path=f"{app.config['RUQQUSPATH']}/assets/style/main.scss"
    else:
        path=f"{app.config['RUQQUSPATH']}/assets/style/main_dark.scss"

    try:
        with open(path, "r") as file:
            raw = file.read()
    except FileNotFoundError:
        return redirect("/assets/style/main.css")

    # This doesn't use python's string formatting because
    # of some odd behavior with css files
    scss = raw.replace("{boardcolor}", board.color)
    scss = scss.replace("{maincolor}", app.config["SITE_COLOR"])
    scss = scss.replace("{ruqquspath}", app.config["RUQQUSPATH"])

    try:
        resp = Response(sass.compile(string=scss), mimetype='text/css')
    except sass.CompileError:
        return redirect("/assets/style/main.css")

    resp.headers.add("Cache-Control", "public")

    return resp


@app.route("/mod/<bid>/color", methods=["POST"])
@auth_required
@is_guildmaster("appearance")
@validate_formkey
def mod_board_color(bid, board, v):

    color = str(request.form.get("color", "")).strip()

    # Remove the '#' from the beginning in case it was entered.
    if color.startswith('#'):
        color = color[1:]

    if len(color) != 6:
        return render_template("guild/appearance.html",
                               v=v, b=board, error="Invalid color code."), 400

    red = color[0:1]
    green = color[2:3]
    blue = color[4:5]

    try:
        if any([int(x, 16) > 255 for x in [red, green, blue]]):
            return render_template(
                "guild/appearance.html", v=v, b=board, error="Invalid color code."), 400
    except ValueError:
        return render_template("guild/appearance.html",
                               v=v, b=board, error="Invalid color code."), 400

    board.color = color
    board.color_nonce += 1

    g.db.add(board)

    try:
        cache.delete_memoized(board_css, board.name)
        cache.delete_memoized(board_dark_css, board.name)
    except BaseException:
        pass

    ma=ModAction(
        kind="update_appearance",
        user_id=v.id,
        board_id=board.id,
        note=f"color=#{board.color}"
        )
    g.db.add(ma)

    return redirect(f"/+{board.name}/mod/appearance?msg=Success")


@app.route("/mod/approve/<guildname>", methods=["POST"])
@app.post("/api/v2/guilds/<guildname>/contributors")
@auth_required
@is_guildmaster("access")
@api("guildmaster")
@validate_formkey
def mod_approve_bid_user(guildname, board, v):
    """
Approve a user as a Contributor in a Guild

URL path parameters:
* `guildname` - The guild in which you are a guildmaster

Required form data:
* `username` - The username of the user to approve.
"""

    user = get_user(request.values.get("username"), graceful=True)

    if not user or user.is_deleted:
        return jsonify({"error": "That user doesn't exist."}), 404

    if board.has_ban(user):
        return jsonify({"error": f"@{user.username} is exiled from +{board.name} and can't currently be approved."}), 409
    if board.has_contributor(user):
        return jsonify({"error": f"@{user.username} is already an approved user."})

    # check for an existing deactivated approval
    existing_contrib = g.db.query(ContributorRelationship).filter_by(
        user_id=user.id, board_id=board.id, is_active=False).first()
    if existing_contrib:
        existing_contrib.is_active = True
        existing_contrib.created_utc = int(time.time())
        existing_contrib.approving_mod_id = v.id
        g.db.add(existing_contrib)
    else:
        new_contrib = ContributorRelationship(user_id=user.id,
                                              board_id=board.id,
                                              is_active=True,
                                              approving_mod_id=v.id)
        g.db.add(new_contrib)
        g.db.commit()

        if user.id != v.id:
            text = f"You have been added as an approved contributor to +{board.name}."
            send_notification(user, text)

    ma=ModAction(
        kind="contrib_user",
        user_id=v.id,
        board_id=board.id,
        target_user_id=user.id
        )
    g.db.add(ma)

    return "", 204


@app.route("/mod/unapprove/<bid>", methods=["POST"])
@app.delete("/api/v2/guilds/<guildname>/contributors")
@auth_required
@is_guildmaster("access")
@api("guildmaster")
@validate_formkey
def mod_unapprove_bid_user(bid, board, v):
    """
Un-approve a user as a Contributor in a Guild

URL path parameters:
* `guildname` - The guild in which you are a guildmaster

Required form data:
* `username` - The username of the user to remove contributor status from.
"""

    user = get_user(request.values.get("username"))

    x = board.has_contributor(user)
    if not x:
        abort(409)

    if not x.board_id==board.id:
        abort(400)

    x.is_active = False

    g.db.add(x)
    g.db.commit()
    ma=ModAction(
        kind="uncontrib_user",
        user_id=v.id,
        board_id=board.id,
        target_user_id=user.id
        )
    g.db.add(ma)
    return "", 204


@app.route("/+<guild>/pic/profile")
@limiter.exempt
def guild_profile(guild):
    x = get_guild(guild)

    if x.over_18:
        return redirect("/assets/images/icons/nsfw_guild_icon.png")
    else:
        return redirect(x.profile_url)

@app.route("/mod/post_pin/<guildname>/<pid>/<x>", methods=["POST"])
@app.patch("/api/v2/guilds/<guildname>/submissions/<pid>/pin/<x>")
@auth_required
@is_guildmaster("content")
@api("guildmaster")
@validate_formkey
def mod_toggle_post_pin(guildname, pid, x, board, v):
    """
Set pin status on a post

URL path parameters:
* `guildname` - The guild to pin the post in
* `pid` - The base 36 id of the post to pin
* `x` - One of `0` or `1`, corresponding to unpinned and pinned statuses respectively
"""

    post = get_post(pid)

    if post.board_id != board.id:
        abort(400)

    try:
        x = bool(int(x))
    except BaseException:
        abort(400)

    if x and not board.can_pin_another:
        return jsonify({"error": f"+{board.name} already has the maximum number of pinned posts."}), 409

    post.is_pinned = x

    cache.delete_memoized(Board.idlist, post.board)

    g.db.add(post)

    ma=ModAction(
        kind="pin_post" if post.is_pinned else "unpin_post",
        user_id=v.id,
        board_id=board.id,
        target_submission_id=post.id
    )
    g.db.add(ma)

    return "", 204


@app.get("/+<guildname>/comments")
@app.get("/api/v1/guild/<guildname>/comments")
@app.get("/api/v2/guilds/<guildname>/comments")
@auth_desired
@api("read")
def board_comments(guildname, v):
    """
Get comments in a guild

URL parameters:
* `guildname` - The name of a guild

Optional query parameters:
* `page` - Page of comments to get. Default `1`.
"""

    b = get_guild(guildname, v=v)

    page = int(request.args.get("page", 1))

    idlist = b.comment_idlist(v=v,
                              page=page,
                              nsfw=v and v.over_18,
                              nsfl=v and v.show_nsfl,
                              hide_offensive=(v and v.hide_offensive) or not v,
                              hide_bot=v and v.hide_bot)

    next_exists = len(idlist) == 26

    idlist = idlist[0:25]

    comments = get_comments(idlist, v=v)

    return {"html": lambda: render_template("board_comments.html",
                                            v=v,
                                            b=b,
                                            page=page,
                                            comments=comments,
                                            standalone=True,
                                            next_exists=next_exists),
            "api": lambda: jsonify({"data": [x.json for x in comments]})}


@app.route("/mod/<bid>/category/<category>", methods=["POST"])
@auth_required
@is_guildmaster("config")
@validate_formkey
def change_guild_category(v, board, bid, category):

    category = int(category)

    sc=g.db.query(SubCategory).filter_by(id=category).first()
    if not sc:
        return jsonify({"error": f"Invalid category id"}), 400

    if board.is_locked_category:
        return jsonify({"error": "You can't do that right now."}), 403

    board.subcat_id=sc.id
    g.db.add(board)
    g.db.flush()

    ma=ModAction(
        kind="update_settings",
        user_id=v.id,
        board_id=board.id,
        note=f"category={sc.category.name} / {sc.name}"
    )
    g.db.add(ma)

    return jsonify({"message": f"Category changed to {sc.category.name} / {sc.name}"})



@app.route("/+<guildname>/mod/log", methods=["GET"])
@app.route("/api/v1/mod_log/<guildname>", methods=["GET"])
@app.get("/api/v2/guilds/<guildname>/modlogs")
@auth_desired
@api("read")
def board_mod_log(guildname, v):
    """
View guild mod log data.

URL path parameters:
* `guildname` - The guild in which you are a guildmaster

Optional query parameters
* `page` - The page of items to view. Default `1`.
"""

    page=int(request.args.get("page",1))
    board=get_guild(guildname, v=v)

    if board.is_banned and not (v and v.admin_level>=4):
        return {
            "html":lambda:(render_template("board_banned.html", v=v, b=board), 403),
            "api":lambda:(jsonify({"error":f"+{board.name} is banned"}), 403)
            }

    actions=g.db.query(ModAction).options(
        joinedload(ModAction.target_post).lazyload('*'),
        Load(Submission).joinedload(Submission.submission_aux),
        joinedload(ModAction.target_comment).lazyload('*'),
        joinedload(ModAction.target_user).lazyload('*'),
        joinedload(ModAction.user).lazyload('*'),
        joinedload(ModAction.board)
        ).filter_by(
        board_id=board.id
        ).order_by(
        ModAction.id.desc()
        ).offset(25*(page-1)).limit(26).all()
    actions=[i for i in actions]

    next_exists=len(actions)==26
    actions=actions[0:25]

    return {
        "html":lambda:render_template(
            "guild/modlog.html",
            v=v,
            b=board,
            actions=actions,
            next_exists=next_exists,
            page=page
        ),
        "api":lambda:jsonify({"data":[x.json for x in actions]})
        }

@app.route("/+<guildname>/mod/log/<id>", methods=["GET"])
@app.get("/api/v2/guilds/<guildname>/modlogs/<id>")
@auth_desired
@api("read")
def mod_log_item(guildname, id, v):
    """
View a guild mod log entry.

URL path parameters:
* `guildname` - The guild in which you are a guildmaster
* `id` - The base 36 id of the mod log entry
"""

    action=g.db.query(ModAction).filter_by(id=base36decode(id)).first()

    if not action:
        abort(404)

    if action.board.name.lower() != guildname.lower():
        abort(404)

    return render_template("guild/modlog.html",
        v=v,
        b=action.board,
        actions=[action],
        next_exists=False,
        page=1,
        action=action
        )

@app.route("/+<guildname>/mod/edit_perms", methods=["POST"])
@auth_required
@is_guildmaster("full")
@validate_formkey
def board_mod_perms_change(guildname, board, v):

    user=get_user(request.form.get("username"))

    v_mod=board.has_mod(v)
    u_mod=board.has_mod_record(user)

    if v_mod.id > u_mod.id:
        return jsonify({"error":"You can't change perms on guildmasters above you."}), 403

    #print({x:request.form.get(x) for x in request.form})

    u_mod.perm_full         = bool(request.form.get("perm_full"         , False))
    u_mod.perm_access       = bool(request.form.get("perm_access"       , False))
    u_mod.perm_appearance   = bool(request.form.get("perm_appearance"   , False))
    u_mod.perm_chat         = bool(request.form.get("perm_chat"       , False))
    u_mod.perm_config       = bool(request.form.get("perm_config"       , False))
    u_mod.perm_content      = bool(request.form.get("perm_content"      , False))

    g.db.add(u_mod)
    g.db.commit()

    ma=ModAction(
        kind="change_perms" if u_mod.accepted else "change_invite",
        user_id=v.id,
        board_id=board.id,
        target_user_id=user.id,
        note=u_mod.permchangelist
    )
    g.db.add(ma)

    return redirect(f"{board.permalink}/mod/mods")

# @app.route("/mod/chatban/<bid>", methods=["POST"])
# @app.route("/api/v1/chatban/<bid>", methods=["POST"])
# @auth_required
# @is_guildmaster('chat')
# @api("guildmaster")
# @validate_formkey
# def mod_chatban_bid_user(bid, board, v):

#     user = get_user(request.values.get("username"), graceful=True)

#     if not user:
#         return jsonify({"error": "That user doesn't exist."}), 404

#     if user.id == v.id:
#         return jsonify({"error": "You can't chatban yourself."}), 409

#     if g.db.query(ChatBan).filter_by(user_id=user.id, board_id=board.id, is_active=True).first():
#         return jsonify({"error": f"@{user.username} is already chatbanned from +{board.name}."}), 409

#     if board.has_contributor(user):
#         return jsonify({"error": f"@{user.username} is an approved contributor to +{board.name} and can't currently be chatbanned."}), 409

#     if board.has_mod(user):
#         return jsonify({"error": "You can't chatban other guildmasters."}), 409

#     new_ban = BanRelationship(user_id=user.id,
#                               board_id=board.id,
#                               banning_mod_id=v.id,
#                               is_active=True)
#     g.db.add(new_ban)

#     ma=ModAction(
#         kind="chatban_user",
#         user_id=v.id,
#         target_user_id=user.id,
#         board_id=board.id
#         )
#     g.db.add(ma)

#     g.db.commit()


#     if request.args.get("toast"):
#         return jsonify({"message": f"@{user.username} was exiled from +{board.name}"})
#     else:
#         return "", 204


@app.route("/mod/unchatban/<bid>", methods=["POST"])
@app.route("/api/v1/unchatban/<bid>", methods=["POST"])
@auth_required
@is_guildmaster('chat')
@api("guildmaster")
@validate_formkey
def mod_unchatban_bid_user(bid, board, v):

    user = get_user(request.values.get("username"))

    x =  g.db.query(ChatBan).filter_by(board_id=board.id, user_id=user.id).first()

    if not x:
        abort(409)

    g.db.delete(x)

    ma=ModAction(
        kind="unchatban_user",
        user_id=v.id,
        target_user_id=user.id,
        board_id=board.id
        )
    g.db.add(ma)

    g.db.commit()

    return "", 204


@app.route("/siege_guild", methods=["POST"])
@is_not_banned
@validate_formkey
def siege_guild(v):

    now = int(time.time())
    guild = request.form.get("guild", None)

    if not guild:
        abort(400)

    guild = get_guild(guild, v=v)

    # check time
    if v.last_siege_utc > now - (60 * 60 * 24 * 7):
        return render_template("message.html",
                               v=v,
                               title=f"Siege against +{guild.name} Failed",
                               error="You need to wait 7 days between siege attempts."
                               ), 403
    # check guild count
    if not v.can_join_gms and guild not in v.boards_modded:
        return render_template("message.html",
                               v=v,
                               title=f"Siege against +{guild.name} Failed",
                               error="You already lead the maximum number of guilds."
                               ), 403
                               
    # Cannot siege banned guilds
    if guild.is_banned:
        return render_template("message.html",
                               v=v,
                               title=f"Siege against +{guild.name} Failed",
                               error=f"+{guild.name} is banned."
                               ), 403

    # Can't siege if exiled
    if g.db.query(BanRelationship).filter_by(is_active=True, user_id=v.id, board_id=guild.id).first():
        return render_template(
            "message.html",
            v=v,
            title=f"Siege against +{guild.name} Failed",
            error=f"You may not siege guilds that you are exiled from."
            ), 403

    # Cannot siege +general, +ruqqus, +ruqquspress, +ruqqusdmca
    if not guild.is_siegable:
        return render_template("message.html",
                               v=v,
                               title=f"Siege against +{guild.name} Failed",
                               error=f"+{guild.name} is an admin-controlled guild and is immune to siege."
                               ), 403

    # update siege date
    v.last_siege_utc = now
    g.db.add(v)
    for alt in v.alts:
        alt.last_siege_utc = now
        g.db.add(v)

    #check user subscription time



    # check user activity
    if guild not in v.boards_modded and v.guild_rep(guild, recent=180) < guild.siege_rep_requirement and not guild.has_contributor(v):
        return render_template(
            "message.html",
            v=v,
            title=f"Siege against +{guild.name} Failed",
            error=f"You do not have enough recent Reputation in +{guild.name} to siege it. +{guild.name} currently requires {guild.siege_rep_requirement} Rep within the last 180 days, and you only have {v.guild_rep(guild, recent=180)}. You may try again in 7 days."
            ), 403

    # Assemble list of mod ids to check
    # skip any user with a perm site-wide ban
    # skip any deleted mod

    #check mods above user
    mods=[]
    for x in guild.mods_list:
        if x.user_id==v.id:
            break
        mods.append(x)
    # if no mods, skip straight to success
    if mods:

        ids = [x.user_id for x in mods]

        # cutoff
        cutoff = now - 60 * 60 * 24 * 60

        # check submissions

        post= g.db.query(Submission).filter(Submission.author_id.in_(tuple(ids)), 
                                        or_(Submission.created_utc > cutoff, Submission.edited_utc > cutoff),
                                        Submission.original_board_id==guild.id,
                                        Submission.deleted_utc==0,
                                        Submission.is_banned==False).first()
        if post:
            return render_template("message.html",
                                   v=v,
                                   title=f"Siege against +{guild.name} Failed",
                                   error=f"Your siege failed. One of the guildmasters created or edited a post in +{guild.name} within the last 60 days. You may try again in 7 days.",
                                   link=post.permalink,
                                   link_text="View post"
                                   ), 403

        # check comments
        comment= g.db.query(Comment).filter(
            Comment.author_id.in_(tuple(ids)),
            or_(Comment.created_utc > cutoff, Comment.edited_utc > cutoff),
            Comment.original_board_id==guild.id,
            Comment.deleted_utc==0,
            Comment.is_banned==False).first()

        if comment:
            return render_template("message.html",
                                   v=v,
                                   title=f"Siege against +{guild.name} Failed",
                                   error=f"Your siege failed. One of the guildmasters created or edited a comment in +{guild.name} within the last 60 days. You may try again in 7 days.",
                                   link=comment.permalink,
                                   link_text="View comment"
                                   ), 403

        # check mod actions
        ma = g.db.query(ModAction).filter(
            or_(
                #option 1: mod action by user
                and_(
                    ModAction.user_id.in_(tuple(ids)),
                    ModAction.created_utc > cutoff,

                    ModAction.board_id==guild.id
                    ),
                #option 2: ruqqus adds user as mod due to siege
                and_(
                    ModAction.target_user_id.in_(tuple(ids)),
                    ModAction.kind=="add_mod",
                    ModAction.board_id==guild.id
                    )
                )
            ).first()
        if ma:
            return render_template("message.html",
                                   v=v,
                                   title=f"Siege against +{guild.name} Failed",
                                   error=f"Your siege failed. One of the guildmasters has performed a mod action in +{guild.name} within the last 60 days. You may try again in 7 days.",
                                   link=ma.permalink,
                                   link_text="View mod log record"
                                   ), 403

    #Siege is successful

    #look up current mod record if one exists
    m=guild.has_mod(v)

    #remove current mods. If they are at or below existing mod, leave in place
    for x in guild.moderators:

        if m and x.id>=m.id and x.accepted:
            continue

        if x.accepted:
            send_notification(x.user,
                              f"You have been overthrown from +{guild.name}.")


            ma=ModAction(
                kind="remove_mod",
                user_id=1,
                board_id=guild.id,
                target_user_id=x.user_id,
                note="siege"
            )
            g.db.add(ma)
        else:
            ma=ModAction(
                kind="uninvite_mod",
                user_id=1,
                board_id=guild.id,
                target_user_id=x.user_id,
                note="siege"
            )
            g.db.add(ma)

        g.db.delete(x)


    if not m:
        new_mod = ModRelationship(user_id=v.id,
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
            user_id=1,
            board_id=guild.id,
            target_user_id=v.id,
            note="siege"
        )
        g.db.add(ma)

    elif not m.perm_full:
        m.perm_full=True
        m.perm_access=True
        m.perm_appearance=True
        m.perm_config=True
        m.perm_content=True
        g.db.add(m)
        ma=ModAction(
            kind="change_perms",
            user_id=1,
            board_id=guild.id,
            target_user_id=v.id,
            note="siege"
        )
        g.db.add(ma)        

    return redirect(f"/+{guild.name}/mod/mods")


@app.post("/+<guildname>/toggle_bell")
@app.patch("/api/v2/guilds/<guildname>/toggle_bell")
@auth_required
@api("update")
def toggle_guild_bell(guildname, v):
    """
Toggle notifications for new posts in a guild. You must be a member of the guild.

URL path parameters:
* `guildname` - The name of a guild.
"""

    guild=get_guild(guildname, v=v, graceful=True)
    if not guild:
        return jsonify({"error": f"Guild '+{guildname}' not found."}), 404

    sub=g.db.query(Subscription).filter_by(user_id=v.id, board_id=guild.id, is_active=True).first()
    if not sub:
        return jsonify({"error": f"You aren't a member of +{guild.name}"}), 404

    sub.get_notifs = not sub.get_notifs
    g.db.add(sub)
    g.db.commit()

    return jsonify({"message":f"Notifications {'en' if sub.get_notifs else 'dis'}abled for +{guild.name}"})
