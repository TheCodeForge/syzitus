from urllib.parse import urlparse
from mistletoe import document
from sqlalchemy import func, literal
from sqlalchemy.orm import contains_eager
from bs4 import BeautifulSoup
from datetime import datetime
import secrets
import threading
from os import environ
from flask import g, session, abort, render_template, jsonify, make_response, redirect, request

from syzitus.helpers.wrappers import *
from syzitus.helpers.base36 import base36encode
from syzitus.helpers.sanitize import sanitize
from syzitus.helpers.filters import *
from syzitus.helpers.embed import *
from syzitus.helpers.markdown import *
from syzitus.helpers.get import get_post, get_comment
from syzitus.helpers.session import *
from syzitus.helpers.alerts import *
from syzitus.helpers.aws import *
from syzitus.classes import *

from syzitus.__main__ import app, limiter, cache


BUCKET=app.config["S3_BUCKET"]


@app.route("/comment/<cid>", methods=["GET"])
@app.route("/post_short/<pid>/<cid>", methods=["GET"])
@app.route("/post_short/<pid>/<cid>/", methods=["GET"])
def comment_cid(cid, pid=None):

    try:
        x=int(cid, 36)
    except:
        abort(400)
        
    comment = get_comment(cid)
    if not comment.parent_submission:
        abort(403)
    return redirect(comment.permalink)


@app.route("/+<guildname>/post/<pid>/<anything>/<cid>", methods=["GET"])
@app.get("/api/v2/comments/<cid>")
@auth_desired
@api("read")
def post_pid_comment_cid(cid, pid=None, guildname=None, anything=None):
    """
Fetch a single comment and up to 5 total layers above and below.

URL path parameters:
* `cid` - The base 36 comment id

Optional query parameters:
* `context` - Integer between `0` and `4` inclusive. Number of generations of parent comments to fetch. Default `0`
"""

    comment = get_comment(cid)
    
    # prevent api shenanigans
    if not pid:
        pid = base36encode(comment.parent_submission)
    
    post = get_post(pid)
    board = post.board
    
    if not guildname:
        guildname = board.name
    
    # fix incorrect guildname and pid
    if (request.path != comment.permalink) and not request.path.startswith("/api/"):

        #special case to handle incoming ruqqus redirects
        if request.args.get("from_ruqqus"):
            abort(410)

        return redirect(comment.permalink)

    if board.is_banned and not (g.user and g.user.admin_level > 3):
        return {'html': lambda: render_template("board_banned.html",
                                                b=board),

                'api': lambda: {'error': f'+{board.name} is banned.'}

                }

    if post.over_18 and not (
            g.user and g.user.over_18) and not session_over18(comment.board):
        t = int(time.time())
        return {'html': lambda: render_template("errors/nsfw.html",
                                                t=t,
                                                lo_formkey=make_logged_out_formkey(
                                                    t),
                                                board=comment.board
                                                ),
                'api': lambda: {'error': f'This content is not suitable for some users and situations.'}

                }

    if post.is_nsfl and not (
            g.user and g.user.show_nsfl) and not session_isnsfl(comment.board):
        t = int(time.time())
        return {'html': lambda: render_template("errors/nsfl.html",
                                                t=t,
                                                lo_formkey=make_logged_out_formkey(
                                                    t),
                                                board=comment.board
                                                ),

                'api': lambda: {'error': f'This content is not suitable for some users and situations.'}

                }

    # check guild ban
    board = post.board
    if board.is_banned and g.user.admin_level < 3:
        return {'html': lambda: render_template("board_banned.html",
                                                b=board),
                'api': lambda: {'error': f'+{board.name} is banned.'}
                }

    post._preloaded_comments = [comment]

    # context improver
    context = min(int(request.args.get("context", 0)), 4)
    comment_info = comment
    c = comment
    while context > 0 and not c.is_top_level:

        parent = get_comment(c.parent_comment_id)

        post._preloaded_comments += [parent]

        c = parent
        context -= 1
    top_comment = c

    sort_type = request.args.get("sort", "hot")
    # children comments

    current_ids = [comment.id]

    exile=g.db.query(ModAction
        ).filter_by(
        kind="exile_user"
        ).distinct(ModAction.target_comment_id).subquery()

    for i in range(6 - context):
        if g.user:

            votes = g.db.query(CommentVote).filter(
                CommentVote.user_id == g.user.id).subquery()

            blocking = g.user.blocking.subquery()
            blocked = g.user.blocked.subquery()


            comms = g.db.query(
                Comment,
                votes.c.vote_type,
                blocking.c.id,
                blocked.c.id,
                aliased(ModAction, alias=exile)
            ).select_from(Comment).options(
                lazyload('*'),
                joinedload(Comment.comment_aux),
                joinedload(Comment.author),
                Load(User).lazyload('*'),
                Load(User),
                joinedload(Comment.post),
                Load(Submission).lazyload('*'),
                Load(Submission).joinedload(Submission.submission_aux),
                Load(Submission).joinedload(Submission.board),
                Load(CommentVote).lazyload('*'),
                Load(UserBlock).lazyload('*'),
                Load(ModAction).lazyload('*')
            ).filter(
                Comment.parent_comment_id.in_(current_ids)
            ).join(
                votes,
                votes.c.comment_id == Comment.id,
                isouter=True
            ).join(
                blocking,
                blocking.c.target_id == Comment.author_id,
                isouter=True
            ).join(
                blocked,
                blocked.c.user_id == Comment.author_id,
                isouter=True
            ).join(
                exile,
                exile.c.target_comment_id==Comment.id,
                isouter=True
            )

            if sort_type == "hot":
                comments = comms.order_by(Comment.score_hot.asc()).all()
            elif sort_type == "top":
                comments = comms.order_by(Comment.score_top.asc()).all()
            elif sort_type == "new":
                comments = comms.order_by(Comment.created_utc.desc()).all()
            elif sort_type == "old":
                comments = comms.order_by(Comment.created_utc.asc()).all()
            elif sort_type == "disputed":
                comments = comms.order_by(Comment.score_disputed.asc()).all()
            elif sort_type == "random":
                c = comms.all()
                comments = random.sample(c, k=len(c))
            else:
                abort(422)

            output = []
            for c in comms:
                comment = c[0]
                comment._voted = c[1] or 0
                comment._is_blocking = c[2] or 0
                comment._is_blocked = c[3] or 0
                comment._is_guildmaster=top_comment._is_guildmaster
                comment._is_exiled_for=c[4] or 0
                output.append(comment)
        else:

            comms = g.db.query(
                Comment,
                aliased(ModAction, alias=exile)
            ).options(
                joinedload(Comment.author)
            ).filter(
                Comment.parent_comment_id.in_(current_ids)
            ).join(
                exile,
                exile.c.target_comment_id==Comment.id,
                isouter=True
            )

            if sort_type == "hot":
                comments = comms.order_by(Comment.score_hot.asc()).all()
            elif sort_type == "top":
                comments = comms.order_by(Comment.score_top.asc()).all()
            elif sort_type == "new":
                comments = comms.order_by(Comment.created_utc.desc()).all()
            elif sort_type == "old":
                comments = comms.order_by(Comment.created_utc.asc()).all()
            elif sort_type == "disputed":
                comments = comms.order_by(Comment.score_disputed.asc()).all()
            elif sort_type == "random":
                c = comms.all()
                comments = random.sample(c, k=len(c))
            else:
                abort(422)

            output = []
            for c in comms:
                comment=c[0]
                comment._is_exiled_for=c[1] or 0
                output.append(comment)

        post._preloaded_comments += output

        current_ids = [x.id for x in output]


    post.tree_comments()

    post.replies=[top_comment]

    return {'html': lambda: post.rendered_page(comment=top_comment, comment_info=comment_info),
            'api': lambda: top_comment.json
            }

#if the guild name is missing, add it to the url and redirect
@app.route("/post/<pid>/<anything>/<cid>", methods=["GET"])
@auth_desired
@api("read")
def post_pid_comment_cid_noboard(pid, cid, anything=None):
    comment=get_comment(cid)
    
    return redirect(comment.permalink)


@app.route("/api/comment", methods=["POST"])
@app.post("/api/v2/comments")
@limiter.limit("6/minute")
@is_not_banned
@no_negative_balance('toast')
@api("create")
def api_comment():
    """
Create a comment

Required form data:
* `parent_fullname` - The fullname of the post or comment that is being replied to
* `body` - Raw comment text

Optional file data:
* `file` - An image to upload and append to the comment body. Requires premium.
""" 
    parent_fullname = request.form.get("parent_fullname")

    # get parent item info
    parent_id = parent_fullname.split("_")[1]
    if parent_fullname.startswith("t2"):
        parent_post = get_post(parent_id)
        parent = parent_post
        parent_comment_id = None
        level = 1
        parent_submission = int(parent_id, 36)
    elif parent_fullname.startswith("t3"):
        parent = get_comment(parent_id)
        parent_comment_id = parent.id
        level = parent.level + 1
        parent_id = parent.parent_submission
        parent_submission = parent_id
        parent_post = get_post(parent_id)
    else:
        abort(400)

    #process and sanitize
    body = request.form.get("body", "")[0:10000]
    body = body.lstrip().rstrip()

    if not body and not (g.user.has_premium and request.files.get('file')):
        return jsonify({"error":"You need to actually write something!"}), 400
    
    if parent_post.board.disallowbots and request.headers.get("X-User-Type")=="Bot":
        return jsonify({"error":f"403 Not Authorized - +{board.name} disallows bots from posting and commenting!"}), 403

    body=preprocess(body)
    with CustomRenderer(post_id=parent_id) as renderer:
        body_md = renderer.render(Document(body))
    body_html = sanitize(body_md, linkgen=True)

    # Run safety filter
    bans = filter_comment_html(body_html)

    if bans:
        ban = bans[0]
        reason = f"Remove the {ban.domain} link from your comment and try again."
        if ban.reason:
            reason += f" {ban.reason_text}"
            
        #auto ban for digitally malicious content
        if any([x.reason==7 for x in bans]):
            g.user.ban(reason="Sexualizing minors")
        elif any([x.reason==4 for x in bans]):
            g.user.ban(days=30, reason="Digitally malicious content")
        elif any([x.reason==9 for x in bans]):
            g.user.ban(days=7, reason="Engaging in illegal activity")
        
        return jsonify({"error": reason}), 401

    # check existing
    existing = g.db.query(Comment).join(CommentAux).filter(Comment.author_id == g.user.id,
                                                           Comment.deleted_utc == 0,
                                                           Comment.parent_comment_id == parent_comment_id,
                                                           Comment.parent_submission == parent_submission,
                                                           CommentAux.body == body
                                                           ).options(contains_eager(Comment.comment_aux)).first()
    if existing:
        return jsonify({"error": f"You already made that comment: {existing.permalink}"}), 409

    # No commenting on deleted/removed things
    if parent.is_banned or parent.deleted_utc > 0:
        return jsonify(
            {"error": "You can't comment on things that have been deleted."}), 403

    if parent.is_blocking and not g.user.admin_level>=3 and not parent.board.has_mod(g.user, "content"):
        return jsonify(
            {"error": "You can't reply to users that you're blocking."}
            ), 403

    if parent.is_blocked and not g.user.admin_level>=3 and not parent.board.has_mod(g.user, "content"):
        return jsonify(
            {"error": "You can't reply to users that are blocking you."}
            ), 403

    # check for archive and ban state
    post = get_post(parent_id)
    if post.is_archived or not post.board.can_comment(g.user):

        return jsonify({"error": "You can't comment on this."}), 403

    # get bot status
    is_bot = request.headers.get("X-User-Type","").lower()=="bot"
    # check spam - this should hopefully be faster
    if not is_bot:
        now = int(time.time())
        cutoff = now - 60 * 60 * 24

        similar_comments = g.db.query(Comment
                                      ).options(
            lazyload('*')
        ).join(Comment.comment_aux
               ).filter(
            Comment.author_id == g.user.id,
            CommentAux.body.op(
                '<->')(body) < app.config["COMMENT_SPAM_SIMILAR_THRESHOLD"],
            Comment.created_utc > cutoff
        ).options(contains_eager(Comment.comment_aux)).all()

        threshold = app.config["COMMENT_SPAM_COUNT_THRESHOLD"]
        if g.user.age >= (60 * 60 * 24 * 7):
            threshold *= 3
        elif g.user.age >= (60 * 60 * 24):
            threshold *= 2

        if len(similar_comments) > threshold:
            text = "Your Ruqqus account has been suspended for 1 day for the following reason:\n\n> Too much spam!"
            send_notification(g.user, text)

            g.user.ban(reason="Spamming.",
                  days=1)

            for alt in g.user.alts:
                if not alt.is_suspended:
                    alt.ban(reason="Spamming.", days=1)

            for comment in similar_comments:
                comment.is_banned = True
                comment.ban_reason = "Automatic spam removal. This happened because the post's creator submitted too much similar content too quickly."
                g.db.add(comment)
                ma=ModAction(
                    user_id=1,
                    target_comment_id=comment.id,
                    kind="ban_comment",
                    board_id=comment.post.board_id,
                    note="spam"
                    )
                g.db.add(ma)

            g.db.commit()
            return jsonify({"error": "Too much spam!"}), 403

    badwords=g.db.query(BadWord).all()
    if badwords:
        for x in badwords:
            if x.check(body):
                is_offensive = True
                break
            else:
                is_offensive = False
    else:
        is_offensive=False

    # check badlinks
    soup = BeautifulSoup(body_html, features="html.parser")
    links = [x['href'] for x in soup.find_all('a') if x.get('href')]

    for link in links:
        parse_link = urlparse(link)
        check_url = ParseResult(scheme="https",
                                netloc=parse_link.netloc,
                                path=parse_link.path,
                                params=parse_link.params,
                                query=parse_link.query,
                                fragment='')
        check_url = urlunparse(check_url)

        badlink = g.db.query(BadLink).filter(
            literal(check_url).contains(
                BadLink.link)).first()

        if badlink:
            return jsonify({"error": f"Remove the following link and try again: `{check_url}`. Reason: {badlink.reason_text}"}), 403

    #admin growth hack
    if g.user.admin_level and app.config["GROWTH_HACK"] and request.form.get("ident"):
        author=get_user(request.form.get("ident"), graceful=True)
        if not author:
            return jsonify({"error": "That account doesn't exist."}), 404
        if author not in g.user.alts:
            return jsonify({"error": "You can only altpost to accounts that you own."}), 403
        author_id = author.id
    else:
        author_id=g.user.id


    # create comment
    c = Comment(author_id=author_id,
                parent_submission=parent_submission,
                #parent_fullname=parent.fullname,
                parent_comment_id=parent_comment_id,
                level=level,
                over_18=post.over_18,
                is_nsfl=post.is_nsfl,
                is_offensive=is_offensive,
                original_board_id=parent_post.board_id,
                is_bot=is_bot,
                app_id=g.client.application.id if g.client else None,
                creation_region=request.headers.get("cf-ipcountry")
                )

    g.db.add(c)
    g.db.flush()


    if g.user.has_premium:
        if request.files.get("file"):
            file=request.files["file"]
            if not file.content_type.startswith('image/'):
                return jsonify({"error": "That wasn't an image!"}), 400
            
            name = f'comment/{c.base36id}/{secrets.token_urlsafe(8)}'
            upload_file(name, file)

            body = request.form.get("body") + f"\n\n![](https://{BUCKET}/{name})"
            body=preprocess(body)
            with CustomRenderer(post_id=parent_id) as renderer:
                body_md = renderer.render(Document(body))
            body_html = sanitize(body_md, linkgen=True)
            
            #csam detection
            def del_function():
                delete_file(name)
                c.is_banned=True
                g.db.add(c)
                g.db.commit()
                
            csam_thread=threading.Thread(target=check_csam_url, 
                                         args=(f"https://{BUCKET}/{name}", 
                                               g.user, 
                                               del_function
                                              )
                                        )
            csam_thread.start()



    c_aux = CommentAux(
        id=c.id,
        body_html=body_html,
        body=body
    )

    g.db.add(c_aux)
    g.db.flush()

    notify_users = set()

    # queue up notification for parent author
    if parent.author.id != g.user.id:
        notify_users.add(parent.author.id)

    # queue up notifications for username mentions
    soup = BeautifulSoup(body_html, features="html.parser")
    mentions = soup.find_all("a", href=re.compile("^/@(\w+)"), limit=3)
    for mention in mentions:
        username = mention["href"].split("@")[1]

        user = g.db.query(User).filter_by(username=username).first()

        if user:
            if g.user.any_block_exists(user):
                continue
            if user.id != g.user.id:
                notify_users.add(user.id)

    for x in notify_users:
        n = Notification(comment_id=c.id,
                         user_id=x)
        g.db.add(n)


    # create auto upvote
    vote = CommentVote(user_id=author_id,
                       comment_id=c.id,
                       vote_type=1
                       )

    g.db.add(vote)

    c.post.score_activity = c.post.rank_activity
    g.db.add(c.post)

    g.db.commit()

    c=get_comment(c.id)


    # print(f"Content Event: @{g.user.username} comment {c.base36id}")


    return {"html": lambda: jsonify({"html": render_template("comments.html",
                                                             comments=[c],
                                                             render_replies=False,
                                                             is_allowed_to_comment=True
                                                             )}),
            "api": lambda: c.json
            }



@app.route("/edit_comment/<cid>", methods=["POST"])
@app.patch("/api/v2/comments/<cid>")
@is_not_banned
@api("update")
def edit_comment(cid):
    """
Edit your comment.

URL path parameters:
* `cid` - The base 36 id of the comment to edit

Required form data:
* `body` - The new raw comment text
"""

    c = get_comment(cid)

    if not c.author_id == g.user.id:
        abort(403)

    if c.is_banned or c.deleted_utc > 0:
        abort(403)

    if c.board.has_ban(g.user):
        abort(403)

    body = request.form.get("body", "")[0:10000]
    body=preprocess(body)
    with CustomRenderer(post_id=c.post.base36id) as renderer:
        body_md = renderer.render(Document(body))
    body_html = sanitize(body_md, linkgen=True)

    # Run safety filter
    bans = filter_comment_html(body_html)

    if bans:
        
        ban = bans[0]
        reason = f"Remove the {ban.domain} link from your comment and try again."

        #auto ban for digitally malicious content
        if any([x.reason==4 for x in bans]):
            g.user.ban(days=30, reason="Digitally malicious content is not allowed.")
            return jsonify({"error":"Digitally malicious content is not allowed."})
        
        if ban.reason:
            reason += f" {ban.reason_text}"    
          
        return jsonify({"error": reason}), 401
    
        return {'html': lambda: render_template("comment_failed.html",
                                                action=f"/edit_comment/{c.base36id}",
                                                badlinks=[
                                                    x.domain for x in bans],
                                                body=body,
                                                ),
                'api': lambda: ({'error': f'A blacklisted domain was used.'}, 400)
                }

    for x in g.db.query(BadWord).all():
        if x.check(body):
            c.is_offensive = True
            break

        else:
            c.is_offensive = False

    # check badlinks
    soup = BeautifulSoup(body_html, features="html.parser")
    links = [x['href'] for x in soup.find_all('a') if x.get('href')]

    for link in links:
        parse_link = urlparse(link)
        check_url = ParseResult(scheme="https",
                                netloc=parse_link.netloc,
                                path=parse_link.path,
                                params=parse_link.params,
                                query=parse_link.query,
                                fragment='')
        check_url = urlunparse(check_url)

        badlink = g.db.query(BadLink).filter(
            literal(check_url).contains(
                BadLink.link)).first()

        if badlink:
            return jsonify({"error": f"Remove the following link and try again: `{check_url}`. Reason: {badlink.reason_text}"}), 403

    # check spam - this should hopefully be faster
    now = int(time.time())
    cutoff = now - 60 * 60 * 24

    similar_comments = g.db.query(Comment
                                  ).options(
        lazyload('*')
    ).join(Comment.comment_aux
           ).filter(
        Comment.author_id == g.user.id,
        CommentAux.body.op(
            '<->')(body) < app.config["SPAM_SIMILARITY_THRESHOLD"],
        Comment.created_utc > cutoff
    ).options(contains_eager(Comment.comment_aux)).all()

    threshold = app.config["SPAM_SIMILAR_COUNT_THRESHOLD"]
    if g.user.age >= (60 * 60 * 24 * 30):
        threshold *= 4
    elif g.user.age >= (60 * 60 * 24 * 7):
        threshold *= 3
    elif g.user.age >= (60 * 60 * 24):
        threshold *= 2

    if len(similar_comments) > threshold:
        text = "Your Ruqqus account has been suspended for 1 day for the following reason:\n\n> Too much spam!"
        send_notification(g.user, text)

        g.user.ban(reason="Spamming.",
              include_alts=True,
              days=1)

        for comment in similar_comments:
            comment.is_banned = True
            comment.ban_reason = "Automatic spam removal. This happened because the post's creator submitted too much similar content too quickly."
            g.db.add(comment)

        g.db.commit()
        return jsonify({"error": "Too much spam!"}), 403

    c.body = body
    c.body_html = body_html

    c.edited_utc = int(time.time())

    g.db.add(c)

    g.db.commit()

    path = request.form.get("current_page", "/")

    return jsonify({"html": c.body_html})


@app.post("/delete/comment/<cid>")
@app.delete("/api/v2/comments/<cid>")
@auth_required
@api("delete")
def delete_comment(cid):
    """
Delete your comment.

URL path parameters:
* `cid` - The base 36 id of the comment to delete
"""


    c = g.db.query(Comment).filter_by(id=int(cid, 36)).first()

    if not c:
        return jsonify({"error": f"Comment ID `{cid}` not found"}), 404

    if not c.author_id == g.user.id:
        return jsonify({"error": f"That's not your comment to delete!"}), 403

    c.deleted_utc = int(time.time())

    g.db.add(c)
    g.db.commit()


    cache.delete_memoized(User.commentlisting)

    return "", 204


@app.route("/embed/comment/<cid>", methods=["GET"])
@app.route("/embed/post/<pid>/comment/<cid>", methods=["GET"])
def embed_comment_cid(cid, pid=None):

    comment = get_comment(cid)

    if not comment.parent:
        abort(403)

    if comment.board.is_banned:
        abort(410)

    return render_template("embeds/comment.html", thing=comment)

@app.route("/mod/comment_pin/<guildname>/<cid>", methods=["POST"])
@app.patch("/api/v2/guilds/<guildname>/comments/<cid>/pin")
@auth_required
@is_guildmaster("content")
@api("guildmaster")
def mod_toggle_comment_pin(guildname, cid, board):
    """
Toggle pin status on a top-level comment.

URL path parameters:
* `guildname` - The guild in which you are a guildmaster
* `cid` - The base 36 comment id
"""

    comment = get_comment(cid)

    if comment.post.board_id != board.id:
        abort(400)
        
    #remove previous pin (if exists)
    if not comment.is_pinned:
        previous_sticky = g.db.query(Comment).filter(
            and_(
                Comment.parent_submission == comment.post.id, 
                Comment.is_pinned == True
                )
            ).first()
        if previous_sticky:
            previous_sticky.is_pinned = False
            g.db.add(previous_sticky)

    comment.is_pinned = not comment.is_pinned

    g.db.add(comment)
    ma=ModAction(
        kind="pin_comment" if comment.is_pinned else "unpin_comment",
        user_id=g.user.id,
        board_id=board.id,
        target_comment_id=comment.id
    )
    g.db.add(ma)

    g.db.commit()

    html=render_template(
                "comments.html",
                comments=[comment],
                render_replies=False,
                is_allowed_to_comment=True
                )

    html=str(BeautifulSoup(html, features="html.parser").find(id=f"comment-{comment.base36id}-only"))

    return jsonify({"html":html})
