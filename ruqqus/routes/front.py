import time
from flask import *
from sqlalchemy import *
from sqlalchemy.orm import lazyload
import random

from ruqqus.helpers.wrappers import *
from ruqqus.helpers.get import *

from ruqqus.__main__ import app, cache
from ruqqus.classes.submission import Submission
from ruqqus.classes.categories import CATEGORIES


@app.route("/post/", methods=["GET"])
def slash_post():
    return redirect("/")


@app.get("/notifications")
@app.get("/notifications/all")
@app.get("/notifications/mentions")
@app.get("/notifications/replies")
@app.get("/notifications/system")
@app.route("/api/v1/notifications", methods=["GET"])
@auth_required
@api("read")
def notifications(v):

    page = int(request.args.get('page', 1))
    all_ = request.args.get('all', False)

    cids = v.notification_commentlisting(page=page,
                                         all_=request.path=="/notifications/all",
                                         mentions_only=request.path=="/notifications/mentions",
                                         replies_only=request.path=="/notifications/replies",
                                         system_only=request.path=="/notifications/system"
                                         )
    next_exists = (len(cids) == 26)
    cids = cids[0:25]

    comments = get_comments(cids, v=v, sort_type="new", load_parent=True)

    listing = []
    for c in comments:
        c._is_blocked = False
        c._is_blocking = False
        c.replies = []
        if c.author_id == 1:
            c._is_system = True
            listing.append(c)
        elif c.level > 1 and c.parent_comment and c.parent_comment.author_id == v.id:
            c._is_comment_reply = True
            parent = c.parent_comment

            if parent in listing:
                parent.replies = parent.replies + [c]
            else:
                parent.replies = [c]
                listing.append(parent)

        elif c.level == 1 and c.post.author_id == v.id:
            c._is_post_reply = True
            listing.append(c)
        else:
            c._is_username_mention = True
            listing.append(c)

    return {'html': lambda: render_template("notifications.html",
                            v=v,
                            notifications=listing,
                            next_exists=next_exists,
                            page=page,
                            standalone=True,
                            render_replies=True,
                            is_notification_page=True),
            'api': lambda: jsonify({"data": [x.json for x in listing]})}

@app.get("/notifications/posts")
@auth_required
@api("read")
def notifications_posts(v):

    page=int(request.args.get("page", 1))

    pids=v.notification_postlisting(
        page=page,
        all_=request.args.get("all")
        )

    next_exists=(len(pids)==26)
    pids=pids[0:25]

    posts=get_posts(pids, v=v, sort="new")

    return {'html': lambda: render_template("notifications_posts.html",
                            v=v,
                            notifications=posts,
                            next_exists=next_exists,
                            page=page,
                            is_notification_page=True),
            'api': lambda: jsonify({"data": [x.json for x in listing]})
            }

@cache.memoize(timeout=900)
def frontlist(v=None, sort=None, page=1, nsfw=False, nsfl=False,
              t=None, categories=[], filter_words='', **kwargs):

    # cutoff=int(time.time())-(60*60*24*30)

    if sort == None:
        if v: sort = v.defaultsorting
        else: sort = "hot"

    if sort == "hot":
        sort_func = Submission.score_hot.desc
    elif sort == "new":
        sort_func = Submission.created_utc.desc
    elif sort == "old":
        sort_func = Submission.created_utc.asc
    elif sort == "disputed":
        sort_func = Submission.score_disputed.desc
    elif sort == "top":
        sort_func = Submission.score_top.desc
    elif sort == "activity":
        sort_func = Submission.score_activity.desc
    else:
        abort(400)

    posts = g.db.query(
        Submission
        ).options(
            lazyload('*'),
            Load(Board).lazyload('*')
        ).filter_by(
            is_banned=False,
            stickied=False
        ).filter(Submission.deleted_utc == 0)

    if not nsfw:
        posts = posts.filter_by(over_18=False)
    
    if not nsfl:
        posts = posts.filter_by(is_nsfl=False)

    if (v and v.hide_offensive) or not v:
        posts = posts.filter_by(is_offensive=False)
    
    if v and v.hide_bot:
        posts = posts.filter(Submission.is_bot==False)

    if v and v.admin_level >= 4:
        board_blocks = g.db.query(
            BoardBlock.board_id).filter_by(
            user_id=v.id).subquery()

        posts = posts.filter(Submission.board_id.notin_(board_blocks))
    elif v:
        m = g.db.query(ModRelationship.board_id).filter_by(
            user_id=v.id, invite_rescinded=False).subquery()
        c = g.db.query(
            ContributorRelationship.board_id).filter_by(
            user_id=v.id).subquery()

        posts = posts.filter(
            or_(
                Submission.author_id == v.id,
                Submission.post_public == True,
                Submission.board_id.in_(m),
                Submission.board_id.in_(c)
            )
        )

        blocking = g.db.query(
            UserBlock.target_id).filter_by(
            user_id=v.id).subquery()
        # blocked = g.db.query(
        #     UserBlock.user_id).filter_by(
        #     target_id=v.id).subquery()
        posts = posts.filter(
            Submission.author_id.notin_(blocking) #,
        #    Submission.author_id.notin_(blocked)
        )

        board_blocks = g.db.query(
            BoardBlock.board_id).filter_by(
            user_id=v.id).subquery()

        posts = posts.filter(Submission.board_id.notin_(board_blocks))
    else:
        posts = posts.filter(Submission.post_public==True)

    # board opt out of all
    if v:
        posts = posts.join(Submission.board).filter(
            or_(
                Board.all_opt_out == False,
                Submission.board_id.in_(
                    g.db.query(
                        Subscription.board_id).filter_by(
                        user_id=v.id,
                        is_active=True).subquery()
                )
            )
        )
    else:

        posts = posts.join(
            Submission.board).filter_by(
            all_opt_out=False)

    
    if categories:
        posts=posts.filter(Board.subcat_id.in_(tuple(categories)))
        
    if (v and v.hide_offensive) or not v:
        posts=posts.filter(
            Board.subcat_id.notin_([44, 108]) 
            )

    posts=posts.filter(Submission.board_id!=1)

    posts=posts.options(contains_eager(Submission.board))


    #custom filter
    #print(filter_words)
    if v and filter_words:
        posts=posts.join(Submission.submission_aux)
        for word in filter_words:
            #print(word)
            posts=posts.filter(not_(SubmissionAux.title.ilike(f'%{word}%')))

    if t == None and v: t = v.defaulttime
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

    gt = kwargs.get("gt")
    lt = kwargs.get("lt")

    if gt:
        posts = posts.filter(Submission.created_utc > gt)

    if lt:
        posts = posts.filter(Submission.created_utc < lt)

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
        abort(400)

    return [x.id for x in posts.offset(25 * (page - 1)).limit(26).all()]
    

@app.route("/", methods=["GET"])
@app.route("/api/v1/front/listing", methods=["GET"])
@app.route("/api/v2/me/submissions")
@auth_desired
@api("read")
def home(v):
    """
Get personalized home page based on subscriptions and personal settings.

Optional query parameters:
* `sort` - One of `hot`, `new`, `top`, `disputed`, `activity`. Default `hot`.
* `t` - One of `day`, `week`, `month`, `year`, `all`. Default `all`.
* `page` - Page of results to return. Default `1`.
"""

    if v and [i for i in v.subscriptions if i.is_active]:

        only=request.args.get("only",None)

        if v:
            defaultsorting = v.defaultsorting
            defaulttime = v.defaulttime
        else:
            defaultsorting = "hot"
            defaulttime = "all"

        sort=request.args.get("sort",defaultsorting)
        t=request.args.get('t', defaulttime)
        page=max(int(request.args.get("page",1)),0)
        ignore_pinned = bool(request.args.get("ignore_pinned", False))

        
        ids=v.idlist(sort=sort,
                     page=page,
                     only=only,
                     t=t,
                     filter_words=v.filter_words,

                     # these arguments don't really do much but they exist for
                     # cache memoization differentiation
                     allow_nsfw=v.over_18,
                     hide_offensive=v.hide_offensive,
                     hide_bot=v.hide_bot,

                     #greater/less than
                     gt=int(request.args.get("utc_greater_than",0)),
                     lt=int(request.args.get("utc_less_than",0)),

                     )

        next_exists=(len(ids)==26)
        ids=ids[0:25]

        # If page 1, check for sticky
        if page == 1 and not ignore_pinned:
            sticky = g.db.query(Submission.id).filter_by(stickied=True).first()


            if sticky:
                ids=[sticky.id]+ids


        posts = get_posts(ids, sort=sort, v=v)

        return {'html': lambda: render_template("subscriptions.html",
                                                v=v,
                                                listing=posts,
                                                next_exists=next_exists,
                                                sort_method=sort,
                                                time_filter=t,
                                                page=page,
                                                only=only),
                'api': lambda: jsonify({"data": [x.json for x in posts],
                                        "next_exists": next_exists
                                        }
                                       )
                }
    else:
        return front_all()


def default_cat_cookie():

    output=[]
    for cat in CATEGORIES:
        for subcat in cat.subcats:
            if subcat.visible:
                output.append(subcat.id)

    output += [0]
    return output

@app.route("/categories", methods=["GET"])
@auth_desired
def categories_select(v):
    return render_template(
        "categorylisting.html",
        v=v,
        categories=CATEGORIES
        )


@app.route("/all", methods=["GET"])
@app.route("/api/v1/all/listing", methods=["GET"])
@app.route("/inpage/all")
@app.get("/api/v2/submissions")
@auth_desired
@api("read")
def front_all(v):
    """
Get all posts, minus filtered content based on personal settings.

Optional query parameters:
* `sort` - One of `hot`, `new`, `top`, `disputed`, `activity`. Default `hot`.
* `t` - One of `day`, `week`, `month`, `year`, `all`. Default `all`.
* `page` - Page of results to return. Default `1`.
"""

    page = int(request.args.get("page") or 1)

    # prevent invalid paging
    page = max(page, 1)

    if v:
        defaultsorting = v.defaultsorting
        defaulttime = v.defaulttime
    else:
        defaultsorting = "hot"
        defaulttime = "all"

    sort=request.args.get("sort",defaultsorting)
    t=request.args.get('t', defaulttime)
    ignore_pinned = bool(request.args.get("ignore_pinned", False))


    cats=session.get("catids")
    new_cats=request.args.get('cats','')
    if not cats and not new_cats and not request.path.startswith('/api/'):
        return make_response(
            render_template(
                "categorylisting.html",
                v=v,
                categories=CATEGORIES
                )
            )


    if new_cats:
        #print('overwrite cats')
        new_cats=[int(x) for x in new_cats.split(',')]
        session['catids']=new_cats
        cats=new_cats
        session.modified=True

    #handle group cookie
    groups = request.args.get("groups")
    if groups:
        session['groupids']=[int(x) for x in groups.split(',')]
        session.modified=True

    #print(cats)

    ids = frontlist(sort=sort,
                    page=page,
                    nsfw=(v and v.over_18 and not v.filter_nsfw),
                    nsfl=(v and v.show_nsfl),
                    t=t,
                    v=v,
                    hide_offensive=(v and v.hide_offensive) or not v,
                    hide_bot=(v and v.hide_bot),
                    gt=int(request.args.get("utc_greater_than", 0)),
                    lt=int(request.args.get("utc_less_than", 0)),
                    filter_words=v.filter_words if v else [],
                    categories=[] if request.path.startswith("/api/") else cats
                    )

    # check existence of next page
    next_exists = (len(ids) == 26)
    ids = ids[0:25]

   # If page 1, check for sticky
    if page == 1 and not ignore_pinned:
        sticky = []
        sticky = g.db.query(Submission.id).filter_by(stickied=True).first()
        if sticky:
            ids = [sticky.id] + ids
    # check if ids exist
    posts = get_posts(ids, sort=sort, v=v)

    return {'html': lambda: render_template("home.html",
                                            v=v,
                                            listing=posts,
                                            next_exists=next_exists,
                                            sort_method=sort,
                                            time_filter=t,
                                            page=page,
                                            CATEGORIES=CATEGORIES
                                            ),
            'inpage': lambda: render_template("submission_listing.html",
                                              v=v,
                                              listing=posts
                                              ),
            'api': lambda: jsonify({"data": [x.json for x in posts],
                                    "next_exists": next_exists
                                    }
                                   )
            }

@app.route("/subcat/<name>", methods=["GET"])
@auth_desired
@api("read")
def subcat(name, v):

    if v:
        defaultsorting = v.defaultsorting
        defaulttime = v.defaulttime
    else:
        defaultsorting = "hot"
        defaulttime = "all"

    sort=request.args.get("sort",defaultsorting)
    t=request.args.get('t', defaulttime)

    page = int(request.args.get("page") or 1)

    # prevent invalid paging
    page = max(page, 1)
    
    if "+" in name:
        ids = []
        for name in name.split("+"):
            ids += frontlist(sort=sort,
                            page=page,
                            nsfw=(v and v.over_18 and not v.filter_nsfw),
                            nsfl=(v and v.show_nsfl),
                            t=t,
                            v=v,
                            hide_offensive=(v and v.hide_offensive) or not v,
                            hide_bot=(v and v.hide_bot),
                            gt=int(request.args.get("utc_greater_than", 0)),
                            lt=int(request.args.get("utc_less_than", 0)),
                            filter_words=v.filter_words if v else [],
                            categories=[name]
                            )
    else:
        ids = frontlist(sort=sort,
                        page=page,
                        nsfw=(v and v.over_18 and not v.filter_nsfw),
                        nsfl=(v and v.show_nsfl),
                        t=t,
                        v=v,
                        hide_offensive=(v and v.hide_offensive) or not v,
                        hide_bot=(v and v.hide_bot),
                        gt=int(request.args.get("utc_greater_than", 0)),
                        lt=int(request.args.get("utc_less_than", 0)),
                        filter_words=v.filter_words if v else [],
                        categories=[name]
                        )

    # check existence of next page
    next_exists = (len(ids) == 26)
    ids = ids[0:25]

    # check if ids exist
    posts = get_posts(ids, sort=sort_method, v=v)

    return {'html': lambda: render_template("home.html",
                                            v=v,
                                            listing=posts,
                                            next_exists=next_exists,
                                            sort_method=sort,
                                            time_filter=t,
                                            page=page,
                                            CATEGORIES=CATEGORIES
                                            ),
            'inpage': lambda: render_template("submission_listing.html",
                                              v=v,
                                              listing=posts
                                              ),
            'api': lambda: jsonify({"data": [x.json for x in posts],
                                    "next_exists": next_exists})}


@cache.memoize(600)
def guild_ids(sort="subs", page=1, nsfw=False, cats=[]):
    # cutoff=int(time.time())-(60*60*24*30)

    guilds = g.db.query(Board).filter_by(is_banned=False).filter(
        Board.subcat_id != 108
    )

    if not nsfw:
        guilds = guilds.filter_by(over_18=False)

    if cats:
        guilds=guilds.filter(Board.subcat.in_(tuple(cats)))

    if sort == "subs":
        guilds = guilds.order_by(Board.stored_subscriber_count.desc())
    elif sort == "new":
        guilds = guilds.order_by(Board.created_utc.desc())
    elif sort == "trending":
        guilds = guilds.order_by(Board.rank_trending.desc())

    else:
        abort(400)

    guilds = [x.id for x in guilds.offset(25 * (page - 1)).limit(26).all()]

    return guilds


@app.route("/browse", methods=["GET"])
@app.get("/api/v1/guilds")
@app.get("/api/v2/guilds")
@auth_desired
@api("read")
def browse_guilds(v):
    """
Get a listing of guilds

Optional query parameters:
* `sort` - One of `trending`, `new`, or `subs`. Default `trending`.
* `page` - Page of results to return. Defualt `1`.
"""


    page = int(request.args.get("page", 1))

    # prevent invalid paging
    page = max(page, 1)

    sort_method = request.args.get("sort", "trending")

    # get list of ids
    ids = guild_ids(
        sort=sort_method, 
        page=page, 
        nsfw=(v and v.over_18),
        cats=request.args.get("cats").split(',') if request.args.get("cats") else None
        )

    # check existence of next page
    next_exists = (len(ids) == 26)
    ids = ids[0:25]

    # check if ids exist
    if ids:

        boards = get_boards(ids, v=v)
    else:
        boards = []

    return {"html": lambda: render_template("boards.html",
                                            v=v,
                                            boards=boards,
                                            page=page,
                                            next_exists=next_exists,
                                            sort_method=sort_method
                                            ),
            "api": lambda: jsonify({"data": [board.json for board in boards]})
            }


@app.route('/mine/guilds', methods=["GET"])
@app.route("/api/v1/mine/guilds", methods=["GET"])
@app.get("/api/v2/me/guilds")
@auth_required
@api("read")
def my_guilds(v, kind=None):

    """
Get guilds with which the user has a connection

Optional query parameters:
`page` - Page of results to return. Default `1`

"""
    page = max(int(request.args.get("page", 1)), 1)


    b = g.db.query(Board)

    contribs = g.db.query(ContributorRelationship.board_id).filter_by(user_id=v.id, is_active=True).subquery()
    m = g.db.query(ModRelationship.board_id).filter_by(user_id=v.id, accepted=True).subquery()
    s = g.db.query(Subscription.board_id).filter_by(user_id=v.id, is_active=True).subquery()

    content = b.filter(
        or_(
            Board.id.in_(contribs),
            Board.id.in_(m),
            Board.id.in_(s)
            )
        )
    content = content.order_by(Board.name.asc())

    content = [x for x in content.offset(25 * (page - 1)).limit(26)]
    next_exists = (len(content) == 26)
    content = content[0:25]
    
    for board in content:
        board._is_subscribed=True

    return {"html": lambda: render_template("mine/boards.html",
                           v=v,
                           boards=content,
                           next_exists=next_exists,
                           page=page,
                           kind="guilds"),
            "api": lambda: jsonify({"data": [x.json for x in content]})}




@app.route('/mine', methods=["GET"])
def mine_redirect():
    return redirect("/mine/guilds")

@app.get("/mine/users")
@app.route("/api/v1/mine", methods=["GET"])
@app.get("/api/v2/me/users")
@auth_required
@api("read")
def my_subs(v, kind=None):

    """
Get users that the authenticated user is following

Optional query parameters:
`page` - Page of results to return. Default `1`

"""
    page = max(int(request.args.get("page", 1)), 1)

    u = g.db.query(User).filter_by(is_banned=0, is_deleted=False)

    follows = g.db.query(Follow).filter_by(user_id=v.id).subquery()

    content = u.join(follows,
                     User.id == follows.c.target_id,
                     isouter=False)

    content = content.order_by(User.stored_subscriber_count.desc())

    content = [x for x in content.offset(25 * (page - 1)).limit(26)]
    next_exists = (len(content) == 26)
    content = content[0:25]

    return {"html": lambda: render_template("mine/users.html",
                           v=v,
                           users=content,
                           next_exists=next_exists,
                           page=page,
                           kind="users"),
            "api": lambda: jsonify({"data": [x.json for x in content]})}


@app.route("/random/post", methods=["GET"])
@auth_desired
def random_post(v):

    x = g.db.query(Submission).options(
        lazyload('board')).filter_by(
        is_banned=False,
        ).filter(Submission.deleted_utc == 0)

    now = int(time.time())
    cutoff = now - (60 * 60 * 24 * 180)
    x = x.filter(Submission.created_utc >= cutoff)

    if not (v and v.over_18):
        x = x.filter_by(over_18=False)

    if not (v and v.show_nsfl):
        x = x.filter_by(is_nsfl=False)

    if v and v.hide_offensive:
        x = x.filter_by(is_offensive=False)
        
    if v and v.hide_bot:
        x = x.filter_by(is_bot=False)

    if v:
        bans = g.db.query(
            BanRelationship.board_id).filter_by(
            user_id=v.id).subquery()
        x = x.filter(Submission.board_id.notin_(bans))

    x=x.join(Submission.board).filter(Board.is_banned==False)

    total = x.count()
    n = random.randint(0, total - 1)

    post = x.order_by(Submission.id.asc()).offset(n).limit(1).first()
    return redirect(post.permalink)


@app.route("/random/guild", methods=["GET"])
@auth_desired
def random_guild(v):

    x = g.db.query(Board).filter_by(
        is_banned=False,
        is_private=False,
        over_18=False,
        is_nsfl=False)

    if v:
        bans = g.db.query(BanRelationship.id).filter_by(user_id=v.id).all()
        x = x.filter(Board.id.notin_([i[0] for i in bans]))

    total = x.count()
    n = random.randint(0, total - 1)

    board = x.order_by(Board.id.asc()).offset(n).limit(1).first()

    return redirect(board.permalink)


@app.route("/random/comment", methods=["GET"])
@auth_desired
def random_comment(v):

    x = g.db.query(Comment).filter_by(is_banned=False,
                                      over_18=False,
                                      is_nsfl=False,
                                      is_offensive=False,
                                      is_bot=False).filter(Comment.parent_submission.isnot(None))
    if v:
        bans = g.db.query(BanRelationship.id).filter_by(user_id=v.id).all()
        x = x.filter(Comment.board_id.notin_([i[0] for i in bans]))

    total = x.count()
    n = random.randint(0, total - 1)
    comment = x.order_by(Comment.id.asc()).offset(n).limit(1).first()

    return redirect(comment.permalink)


@app.route("/random/user", methods=["GET"])
@auth_desired
def random_user(v):
    x = g.db.query(User).filter(or_(User.is_banned == 0, and_(
        User.is_banned > 0, User.unban_utc < int(time.time()))))

    x = x.filter_by(is_private=False)

    total = x.count()
    n = random.randint(0, total - 1)

    user = x.offset(n).limit(1).first()

    return redirect(user.permalink)


@cache.memoize(600)
def comment_idlist(page=1, v=None, nsfw=False, **kwargs):

    posts = g.db.query(Submission).options(
        lazyload('*')).join(Submission.board)

    if not nsfw:
        posts = posts.filter_by(over_18=False)

    if v and not v.show_nsfl:
        posts = posts.filter_by(is_nsfl=False)

    if v and v.admin_level >= 4:
        pass
    elif v:
        m = g.db.query(ModRelationship.board_id).filter_by(
            user_id=v.id, invite_rescinded=False).subquery()
        c = g.db.query(
            ContributorRelationship.board_id).filter_by(
            user_id=v.id).subquery()

        posts = posts.filter(
            or_(
                Submission.author_id == v.id,
                Submission.post_public == True,
                Submission.board_id.in_(m),
                Submission.board_id.in_(c),
                Board.is_private == False
            )
        )
    else:
        posts = posts.filter(or_(Submission.post_public ==
                                 True, Board.is_private == False))

    posts = posts.subquery()

    comments = g.db.query(Comment).options(lazyload('*'))

    if v and v.hide_offensive:
        comments = comments.filter_by(is_offensive=False)
        
    if v and v.hide_bot:
        comments = comments.filter_by(is_bot=False)

    if v and v.admin_level <= 3:
        # blocks
        blocking = g.db.query(
            UserBlock.target_id).filter_by(
            user_id=v.id).subquery()
        blocked = g.db.query(
            UserBlock.user_id).filter_by(
            target_id=v.id).subquery()

        comments = comments.filter(
            Comment.author_id.notin_(blocking),
            Comment.author_id.notin_(blocked)
        )

    if not v or not v.admin_level >= 3:
        comments = comments.filter_by(is_banned=False).filter(Comment.deleted_utc == 0)

    comments = comments.join(posts, Comment.parent_submission == posts.c.id)

    comments = comments.order_by(Comment.created_utc.desc()).offset(
        25 * (page - 1)).limit(26).all()

    return [x.id for x in comments]


@app.route("/all/comments", methods=["GET"])
@app.route("/api/v1/front/comments", methods=["GET"])
@app.get("/api/v2/comments")
@auth_desired
@api("read")
def all_comments(v):
    """
Get all comments

Optional query parameters:
* `page` - Page of results to return. Default `1`
"""

    page = int(request.args.get("page", 1))

    idlist = comment_idlist(v=v,
                            page=page,
                            nsfw=v and v.over_18,
                            nsfl=v and v.show_nsfl,
                            hide_offensive=v and v.hide_offensive,
                            hide_bot=v and v.hide_bot)

    comments = get_comments(idlist, v=v)

    next_exists = len(idlist) == 26

    idlist = idlist[0:25]

    return {"html": lambda: render_template("home_comments.html",
                                            v=v,
                                            page=page,
                                            comments=comments,
                                            standalone=True,
                                            next_exists=next_exists),
            "api": lambda: jsonify({"data": [x.json for x in comments]})}


@app.route("/api/v1/categories", methods=["GET"])
@auth_desired
@api()
def categories(v):

    return make_response(
        jsonify(
            {"data":[x.json for x in CATEGORIES]}
            )
        )
