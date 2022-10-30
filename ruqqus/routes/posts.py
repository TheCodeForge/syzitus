from urllib.parse import urlparse, ParseResult, urlunparse, urlencode
import mistletoe
from sqlalchemy import func
from sqlalchemy.orm import aliased
from bs4 import BeautifulSoup
import secrets
import threading
import requests
import re
import bleach
import time
import gevent

from ruqqus.helpers.wrappers import *
from ruqqus.helpers.base36 import *
from ruqqus.helpers.sanitize import *
from ruqqus.helpers.filters import *
from ruqqus.helpers.embed import *
from ruqqus.helpers.markdown import *
from ruqqus.helpers.get import *
from ruqqus.helpers.thumbs import *
from ruqqus.helpers.session import *
from ruqqus.helpers.aws import *
from ruqqus.helpers.alerts import send_notification
from ruqqus.classes import *
from .front import frontlist
from flask import *
from ruqqus.__main__ import app, limiter, cache, db_session


BAN_REASONS = ['',  #placeholder
               "URL shorteners are not permitted.",
               "",  # placeholder, formerly "no porn"
               "Copyright infringement is not permitted.",
               "Digitally malicious content is not permitted.",
               "Spam",
               "No doxxing",
               "Sexualizing minors",
               'User safety - This site is a Ruqqus clone which is still displaying "Ruqqus" as its site name.',
               "Engaging in or planning unlawful activity"
               ]

BUCKET = app.config.get("S3_BUCKET", "i.ruqqus.com")


@app.route("/post_short/", methods=["GET"])
@app.route("/post_short/<base36id>", methods=["GET"])
@app.route("/post_short/<base36id>/", methods=["GET"])
def incoming_post_shortlink(base36id=None):

    if not base36id:
        return redirect('/')

    if base36id == "robots.txt":
        return redirect('/robots.txt')

    try:
        x=base36decode(base36id)
    except:
        abort(400)

    post = get_post(base36id)
    return redirect(post.permalink)

@app.get("/+<boardname>/post/<pid>")
def post_redirect(boardname, pid):
    return redirect(get_post(pid).permalink)

@app.get("/api/v2/submissions/<pid>")
@auth_desired
@api("read")
def post_base36id_no_comments(pid):
    """
Get a single submission (without comments).

URL path parameters:
* `pid` - The base 36 post id
"""
    
    post = get_post(pid)
    board = post.board

    if board.is_banned and not (g.user and g.user.admin_level > 3):
        return render_template("board_banned.html",
                               b=board,
                               p=True)

    if post.over_18 and not (g.user and g.user.over_18) and not session_over18(board):
        t = int(time.time())
        return {"html":lambda:render_template("errors/nsfw.html",
                               t=t,
                               lo_formkey=make_logged_out_formkey(t),
                               board=post.board

                               ),
                "api":lambda:(jsonify({"error":"Must be 18+ to view"}), 451)
                }



    return {
        "html":lambda:post.rendered_page(),
        "api":lambda:jsonify(post.json)
        }


@app.route("/+<boardname>/post/<pid>/", methods=["GET"])
@app.route("/+<boardname>/post/<pid>/<anything>", methods=["GET"])
@app.get("/api/v2/submissions/<pid>/comments")
@auth_desired
@api("read")
def post_base36id_with_comments(pid, boardname=None, anything=None):
    """
Get the comment tree for a submission.

URL path parameters:
* `pid` - The base 36 post id

Optional query parameters:
* `sort` - Comment sort order. One of `hot`, `new`, `top`, `disputed`, `old`. Default `hot`.
"""
    
    post = get_post_with_comments(
        pid, sort_type=request.args.get(
            "sort", "top"))

    board = post.board
    #if the guild name is incorrect, fix the link and redirect

    if boardname and not boardname == board.name:
        return redirect(post.permalink)

    if board.is_banned and not (g.user and g.user.admin_level > 3):
        return render_template("board_banned.html",
                               b=board,
                               p=True)

    if post.over_18 and not (g.user and g.user.over_18) and not session_over18(board):
        t = int(time.time())
        return {"html":lambda:render_template("errors/nsfw.html",
                               t=t,
                               lo_formkey=make_logged_out_formkey(t),
                               board=post.board

                               ),
                "api":lambda:(jsonify({"error":"Must be 18+ to view"}), 451)
                }
    
    post.tree_comments()

    return {
        "html":lambda:post.rendered_page(),
        "api":lambda:jsonify({"data":[x.json for x in post.replies]})
        }

#if the guild name is missing from the url, add it and redirect
@app.route("/post/<base36id>", methods=["GET"])
@app.route("/post/<base36id>/", methods=["GET"])
@app.route("/post/<base36id>/<anything>", methods=["GET"])
@auth_desired
@api("read")
def post_base36id_noboard(base36id, anything=None):
    
    post=get_post_with_comments(base36id, sort_type=request.args.get("sort","top"))

    #board=post.board
    return redirect(post.permalink)



@app.route("/submit", methods=["GET"])
@is_not_banned
@no_negative_balance("html")
def submit_get():

    board = request.args.get("guild")
    b = get_guild(board, graceful=True) if board else None


    return render_template("submit.html",
                           b=b
                           )


@app.route("/edit_post/<pid>", methods=["POST"])
@app.patch("/api/v2/submissions/<pid>")
@is_not_banned
@no_negative_balance("html")
@api("update")
def edit_post(pid):
    """
Edit your post text.

URL path parameters:
* `pid` - The base 36 id of the post to edit

Required form data:
* `body` - The new raw comment text
"""

    p = get_post(pid)

    if not p.author_id == g.user.id:
        abort(403)

    if p.is_banned:
        abort(403)

    if p.board.has_ban(g.user):
        abort(403)

    body = request.form.get("body", "")
    body=preprocess(body)
    with CustomRenderer() as renderer:
        body_md = renderer.render(mistletoe.Document(body))
    body_html = sanitize(body_md, linkgen=True)


    # Run safety filter
    bans = filter_comment_html(body_html)
    if bans:
        ban = bans[0]
        reason = f"Remove the {ban.domain} link from your post and try again."
        if ban.reason:
            reason += f" {ban.reason_text}"
            
        #auto ban for digitally malicious content
        if any([x.reason==4 for x in bans]):
            g.user.ban(days=30, reason="Digitally malicious content is not allowed.")
            abort(403)
            
        return {"error": reason}, 403

    # check spam
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
            if badlink.autoban:
                g.user.ban(days=1, reason="spam")
                return redirect('/notifications')
            else:

                return {"error": f"The link `{badlink.link}` is not allowed. Reason: {badlink.reason}"}, 400


    p.body = body
    p.body_html = body_html
    p.edited_utc = int(time.time())

    # offensive
    p.is_offensive = False
    for x in g.db.query(BadWord).all():
        if (p.body and x.check(p.body)) or x.check(p.title):
            p.is_offensive = True
            break

    g.db.add(p)
    g.db.commit()

    return redirect(p.permalink)


@app.route("/submit/title", methods=['GET'])
@limiter.limit("6/minute")
@is_not_banned
@no_negative_balance("html")
def get_post_title():

    url = request.args.get("url", None)
    if not url:
        return abort(400)

    #mimic chrome browser agent
    headers = {"User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 Safari/537.36"}
    try:
        x = requests.get(url, headers=headers)
    except BaseException:
        return jsonify({"error": "Could not reach page"}), 400


    if not x.status_code == 200:
        return jsonify({"error": f"Page returned {x.status_code}"}), x.status_code


    try:
        soup = BeautifulSoup(x.content, 'html.parser')

        data = {"url": url,
                "title": soup.find('title').string
                }

        return jsonify(data)
    except BaseException:
        return jsonify({"error": f"Could not find a title"}), 400


@app.route("/submit", methods=['POST'])
@app.post("/api/v2/submissions")
@limiter.limit("6/minute")
@is_not_banned
@no_negative_balance('html')
@api("create")
def submit_post():
    """
Create a post

Required form data:
* `title` - The post title
* `guild` - The name of the guild to submit to

At least one of the following form items is required:
* `url` - The link being submitted. Uploading an image file counts as a url.
* `body` - The text body of the post

Optional file data:
* `file` - An image to upload as the post target. Requires premium or 500 Rep.
"""

    title = request.form.get("title", "").lstrip().rstrip()

    title = title.lstrip().rstrip()
    title = title.replace("\n", "")
    title = title.replace("\r", "")
    title = title.replace("\t", "")
    
    # sanitize title
    title = bleach.clean(title)

    url = request.form.get("url", "")

    board = get_guild(request.form.get('board', request.form.get("guild")), graceful=True)
    if not board:
        board = get_guild('general')

    if not title:
        return jsonify({"error": "Please enter a better title"}), 400

    # if len(title)<10:
    #     return render_template("submit.html",
    #                            error="Please enter a better title.",
    #                            title=title,
    #                            url=url,
    #                            body=request.form.get("body",""),
    #                            b=board
    #                            )


    elif len(title) > 250:
        return jsonify({"error": "250 character limit for titles"}), 400

    parsed_url = urlparse(url)
    if not (parsed_url.scheme and parsed_url.netloc) and not request.form.get(
            "body") and not request.files.get("file", None):
        return jsonify({"error": "`url` or `body` required"}), 400

    # sanitize title
    title = bleach.clean(title, tags=[])

    # Force https for submitted urls

    if request.form.get("url"):
        new_url = ParseResult(scheme="https",
                              netloc=parsed_url.netloc,
                              path=parsed_url.path,
                              params=parsed_url.params,
                              query=parsed_url.query,
                              fragment=parsed_url.fragment)
        url = urlunparse(new_url)
    else:
        url = ""

    body = request.form.get("body", "")
    # check for duplicate
    dup = g.db.query(Submission).join(Submission.submission_aux).filter(

        Submission.author_id == g.user.id,
        Submission.deleted_utc == 0,
        Submission.board_id == board.id,
        SubmissionAux.title == title,
        SubmissionAux.url == url,
        SubmissionAux.body == body
    ).first()

    if dup:
        return redirect(dup.permalink)


    # check for domain specific rules

    parsed_url = urlparse(url)

    domain = parsed_url.netloc

    # check ban status
    domain_obj = get_domain(domain)
    #print('domain_obj', domain_obj)
    if domain_obj:
        if domain_obj.is_banned:
          
            if domain_obj.reason==4:
                g.user.ban(days=30, reason="Digitally malicious content")
            elif domain_obj.reason==9:
                g.user.ban(days=7, reason="Engaging in illegal activity")
            elif domain_obj.reason==7:
                g.user.ban(reason="Sexualizing minors")

            return jsonify({"redirect":"/notifications"}), 301

        # check for embeds
        if domain_obj.embed_function:
            #print('domainobj embed function', domain_obj.embed_function)
            try:
                embed = eval(domain_obj.embed_function)(url)
            except BaseException as e:
                #print('exception', e)
                embed = ""
        else:
            embed = ""
    else:

        embed = ""

    # board
    board_name = request.form.get("board", "general")
    board_name = board_name.lstrip("+")
    board_name = board_name.rstrip()

    board = get_guild(board_name, graceful=True)

    if not board:
        return jsonify({"error": f"That guild doesn't exist."}), 400

    if board.is_banned:
        return jsonify({"error": f"+{board.name} is banned."}), 403

    if board.has_ban(g.user):
        return jsonify({"error": f"You are exiled from +{board.name}."}), 403

    if (board.restricted_posting or board.is_private) and not (
            board.can_submit(g.user)):
        return jsonify({"error": f"You are not an approved contributor for +{board.name}."}), 403

    if board.disallowbots and request.headers.get("X-User-Type")=="Bot":
        return jsonify({"error": f"403 Not Authorized - +{board.name} disallows bots."}), 403

    # similarity check
    now = int(time.time())
    cutoff = now - 60 * 60 * 24


    similar_posts = g.db.query(Submission).options(
        lazyload('*')
        ).join(
            Submission.submission_aux
        ).filter(
            or_(
               and_(
                    Submission.author_id == g.user.id,
                    SubmissionAux.title.op('<->')(title) < app.config["SPAM_SIMILARITY_THRESHOLD"],
                    Submission.created_utc > cutoff
               ),
               and_(
                   SubmissionAux.title.op('<->')(title) < app.config["SPAM_SIMILARITY_THRESHOLD"]/2,
                   Submission.created_utc > cutoff
               )
            )
    ).all()

    if url:
        similar_urls = g.db.query(Submission).options(
            lazyload('*')
        ).join(
            Submission.submission_aux
        ).filter(
            #or_(
            #    and_(
                    Submission.author_id == g.user.id,
                    SubmissionAux.url.op('<->')(url) < app.config["SPAM_URL_SIMILARITY_THRESHOLD"],
                    Submission.created_utc > cutoff
            #    ),
            #    and_(
            #        SubmissionAux.url.op('<->')(url) < app.config["SPAM_URL_SIMILARITY_THRESHOLD"]/2,
            #        Submission.created_utc > cutoff
            #    )
            #)
        ).all()
    else:
        similar_urls = []

    threshold = app.config["SPAM_SIMILAR_COUNT_THRESHOLD"]
    if g.user.age >= (60 * 60 * 24 * 7):
        threshold *= 3
    elif g.user.age >= (60 * 60 * 24):
        threshold *= 2

    if max(len(similar_urls), len(similar_posts)) >= threshold:

        g.user.ban(reason="Spamming.",
              days=1)

        for alt in g.user.alts:
            if not alt.is_suspended:
                alt.ban(reason="Spamming.", days=1)

        for post in similar_posts + similar_urls:
            post.is_banned = True
            post.is_pinned = False
            post.ban_reason = "Automatic spam removal. This happened because the post's creator submitted too much similar content too quickly."
            g.db.add(post)
            ma=ModAction(
                    user_id=1,
                    target_submission_id=post.id,
                    kind="ban_post",
                    board_id=post.board_id,
                    note="spam"
                    )
            g.db.add(ma)
        g.db.commit()
        return jsonify({"redirect":"/notifications"}), 301

    # catch too-long body
    if len(str(body)) > 10000:
        return jsonify({"error": f"10000 character limit for text body"}), 400

    if len(url) > 2048:
        return jsonify({"error": f"2048 character limit for URL"}), 400

    # render text

    body=preprocess(body)

    with CustomRenderer() as renderer:
        body_md = renderer.render(mistletoe.Document(body))
    body_html = sanitize(body_md, linkgen=True)

    # Run safety filter
    bans = filter_comment_html(body_html)
    if bans:
        ban = bans[0]
        reason = f"Remove the {ban.domain} link from your post and try again."
        if ban.reason:
            reason += f" {ban.reason_text}"
            
        #auto ban for digitally malicious content
        if any([x.reason==4 for x in bans]):
            g.user.ban(days=30, reason="Digitally malicious content is not allowed.")
            abort(403)
            
        return jsonify({"redirect":"/notifications"}), 301

    # check spam
    soup = BeautifulSoup(body_html, features="html.parser")
    links = [x['href'] for x in soup.find_all('a') if x.get('href')]

    if url:
        links = [url] + links

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
            if badlink.autoban:
                g.user.ban(days=1, reason="spam")

                return redirect('/notifications')
            else:

                return jsonify({"error": f"The link `{badlink.link}` is not allowed. Reason: {badlink.reason}"}), 400

    # check for embeddable video
    domain = parsed_url.netloc

    if url:
        repost = g.db.query(Submission).join(Submission.submission_aux).filter(
            SubmissionAux.url.ilike(url),
            Submission.board_id == board.id,
            Submission.deleted_utc == 0,
            Submission.is_banned == False
        ).order_by(
            Submission.id.asc()
        ).first()
    else:
        repost = None

    if repost and request.values.get("no_repost"):
        return {
            'html':lambda:(jsonify({"redirect":repost.permalink}),301),
            'api': lambda:({"error":"This content has already been posted", "repost":repost.json}, 409)
        }

    if request.files.get('file') and not g.user.can_submit_image:
        abort(403)

    # offensive
    is_offensive = False
    for x in g.db.query(BadWord).all():
        if (body and x.check(body)) or x.check(title):
            is_offensive = True
            break

    #admin growth hack
    if g.user.admin_level and app.config["GROWTH_HACK"] and request.form.get("ident"):
        author=get_user(request.form.get("ident"), graceful=True)
        if not author:
            return jsonify({"error": "That account doesn't exist."})
        if author not in g.user.alts:
            return jsonify({"error": "You can only altpost to accounts that you own."})
        author_id = author.id
    else:
        author_id=g.user.id

    new_post = Submission(
        author_id=author_id,
        domain_ref=domain_obj.id if domain_obj else None,
        board_id=board.id,
        original_board_id=board.id,
        over_18=(
            bool(
                request.form.get(
                    "over_18",
                    "")
                ) or board.over_18
            ),
        post_public=not board.is_private,
        repost_id=repost.id if repost else None,
        is_offensive=is_offensive,
        app_id=g.client.application.id if g.client else None,
        creation_region=request.headers.get("cf-ipcountry"),
        is_bot = request.headers.get("X-User-Type","").lower()=="bot"
    )

    g.db.add(new_post)
    g.db.flush()

    new_post_aux = SubmissionAux(id=new_post.id,
                                 url=url,
                                 body=body,
                                 body_html=body_html,
                                 embed_url=embed,
                                 title=title
                                 )
    g.db.add(new_post_aux)
    g.db.flush()

    vote = Vote(user_id=g.user.id,
                vote_type=1,
                submission_id=new_post.id
                )
    g.db.add(vote)
    g.db.flush()

    g.db.refresh(new_post)

    # check for uploaded image
    if request.files.get('file'):

        #check file size
        if request.content_length > 16 * 1024 * 1024 and not g.user.has_premium:
            g.db.rollback()
            abort(413)

        file = request.files['file']
        if not file.content_type.startswith('image/'):
            g.db.rollback()
            return jsonify({"error": "Image files only"}), 400

        name = f'post/{new_post.base36id}/{secrets.token_urlsafe(8)}'
        upload_file(name, file)

        # thumb_name=f'posts/{new_post.base36id}/thumb.png'
        #upload_file(name, file, resize=(375,227))

        # update post data
        new_post.url = f'https://{BUCKET}/{name}'
        new_post.is_image = True
        new_post.domain_ref = 1  # id of i.ruqqus.com domain
        g.db.add(new_post)
        g.db.add(new_post.submission_aux)
        g.db.commit()

        #csam detection
        def del_function():
            db=db_session()
            delete_file(name)
            new_post.is_banned=True
            db.add(new_post)
            db.commit()
            ma=ModAction(
                kind="ban_post",
                user_id=1,
                note="banned image",
                target_submission_id=new_post.id
                )
            db.add(ma)
            db.commit()
            db.close()

            
        csam_thread=threading.Thread(target=check_csam_url, 
                                     args=(f"https://{BUCKET}/{name}", 
                                           g.user, 
                                           del_function
                                          )
                                    )
        csam_thread.start()
    
    g.db.commit()

    # spin off thumbnail generation and csam detection as  new threads
    if (new_post.url or request.files.get('file')) and (g.user.is_activated or request.headers.get('cf-ipcountry')!="T1"):
        new_thread = gevent.spawn(
            thumbnail_thread,
            new_post.base36id
        )

    # expire the relevant caches: front page new, board new
    cache.delete_memoized(frontlist)
    g.db.commit()
    cache.delete_memoized(Board.idlist, board, sort="new")
    
    
    # queue up notifications for username mentions
    notify_users = set()
	
    soup = BeautifulSoup(body_html, features="html.parser")
    for mention in soup.find_all("a", href=re.compile("^/@(\w+)"), limit=3):
        username = mention["href"].split("@")[1]
        user = g.db.query(User).filter_by(username=username).first()
        if user and not g.user.any_block_exists(user) and user.id != g.user.id: 
            notify_users.add(user.id)
    
    debug(f"Content Event: @{new_post.author.username} post {new_post.permalink}")

    #Bell notifs
    board_uids = g.db.query(
        Subscription.user_id
        ).options(lazyload('*')).filter(
        Subscription.board_id==new_post.board_id, 
        Subscription.is_active==True,
        Subscription.get_notifs==True,
        Subscription.user_id != g.user.id,
        Subscription.user_id.notin_(
            g.db.query(UserBlock.user_id).filter_by(target_id=g.user.id).subquery()
            )
        )

    follow_uids=g.db.query(
        Follow.user_id
        ).options(lazyload('*')).filter(
        Follow.target_id==g.user.id,
        Follow.get_notifs==True,
        Follow.user_id!=g.user.id,
        Follow.user_id.notin_(
            g.db.query(UserBlock.user_id).filter_by(target_id=g.user.id).subquery()
            ),
        Follow.user_id.notin_(
            g.db.query(UserBlock.target_id).filter_by(user_id=g.user.id).subquery()
            )
        ).join(Follow.target).filter(
        User.is_private==False,
        User.is_nofollow==False,
        )

    if not new_post.is_public:

        contribs=g.db.query(ContributorRelationship).filter_by(board_id=new_post.board_id, is_active=True).subquery()
        mods=g.db.query(ModRelationship).filter_by(board_id=new_post.board_id, accepted=True).subquery()

        board_uids=board_uids.join(
            contribs,
            contribs.c.user_id==Subscription.user_id,
            isouter=True
            ).join(
            mods,
            mods.c.user_id==Subscription.user_id,
            isouter=True
            ).filter(
                or_(
                    mods.c.id != None,
                    contribs.c.id !=None
                )
            )

        follow_uids=follow_uids.join(
            contribs,
            contribs.c.user_id==Follow.user_id,
            isouter=True
            ).join(
            mods,
            mods.c.user_id==Follow.user_id,
            isouter=True
            ).filter(
                or_(
                    mods.c.id != None,
                    contribs.c.id !=None
                )
            )

    uids=list(set([x[0] for x in board_uids.all()] + [x[0] for x in follow_uids.all()]).union(notify_users))

    for uid in uids:
        new_notif=Notification(
            user_id=uid,
            submission_id=new_post.id
            )
        g.db.add(new_notif)

    g.db.commit()

    return {"html": lambda: (jsonify({"redirect":new_post.permalink}), 301),
            "api": lambda: jsonify(new_post.json)
            }

# @app.route("/api/nsfw/<pid>/<x>", methods=["POST"])
# @auth_required
# def api_nsfw_pid(pid, x):

#     try:
#         x=bool(int(x))
#     except:
#         abort(400)

#     post=get_post(pid)

#     if not g.user.admin_level >=3 and not post.author_id==g.user.id and not post.board.has_mod():
#         abort(403)

#     post.over_18=x
#     g.db.add(post)
#

#     return "", 204


@app.route("/delete_post/<pid>", methods=["POST"])
@app.delete("/api/v2/submissions/<pid>")
@auth_required
@api("delete")
def delete_post_pid(pid):
    """
Delete your post.

URL path parameters:
* `pid` - The base 36 id of the post being deleted
"""

    post = get_post(pid)
    if not post.author_id == g.user.id:
        abort(403)
        
    if post.is_deleted:
        abort(404)
        
    post.deleted_utc = int(time.time())
    post.is_pinned = False
    post.stickied = False

    g.db.add(post)

    # clear cache
    cache.delete_memoized(User.userpagelisting, g.user, sort="new")
    cache.delete_memoized(Board.idlist, post.board)

    if post.age >= 3600 * 6:
        cache.delete_memoized(Board.idlist, post.board, sort="new")
        cache.delete_memoized(frontlist, sort="new")

    # delete i.ruqqus.com
    if post.domain == "i.ruqqus.com":

        segments = post.url.split("/")
        pid = segments[4]
        rand = segments[5]
        if pid == post.base36id:
            key = f"post/{pid}/{rand}"
            delete_file(key)
            post.is_image = False
            g.db.add(post)

    g.db.commit()

    return "", 204


@app.route("/embed/post/<pid>", methods=["GET"])
def embed_post_pid(pid):

    post = get_post(pid)

    if post.is_banned or post.board.is_banned:
        abort(410)

    return render_template("embeds/submission.html", p=post)


@app.route("/api/toggle_post_nsfw/<pid>", methods=["POST"])
@app.patch("/api/v2/submissions/<pid>/toggle_nsfw")
@is_not_banned
@api("update")
def toggle_post_nsfw(pid):
    """
Toggle "NSFW" status on a post.

URL path parameters:
* `pid` - The base 36 post id.
"""


    post = get_post(pid)

    mod=post.board.has_mod(g.user)

    if not post.author_id == g.user.id and not g.user.admin_level >= 3 and not mod:
        abort(403)

    if post.board.over_18 and post.over_18:
        abort(403)

    post.over_18 = not post.over_18
    g.db.add(post)

    if post.author_id!=g.user.id:
        ma=ModAction(
            kind="set_nsfw" if post.over_18 else "unset_nsfw",
            user_id=g.user.id,
            target_submission_id=post.id,
            board_id=post.board.id,
            note = None if mod else "admin action"
            )
        g.db.add(ma)

    g.db.commit()

    return "", 204


@app.route("/api/toggle_post_nsfl/<pid>", methods=["POST"])
@app.patch("/api/v2/submissions/<pid>/toggle_nsfl")
@is_not_banned
@api("update")
def toggle_post_nsfl(pid):
    """
Toggle "NSFL" status on a post.

URL path parameters:
* `pid` - The base 36 post id.
"""

    post = get_post(pid)

    mod=post.board.has_mod(g.user)

    if not post.author_id == g.user.id and not g.user.admin_level >= 3 and not mod:
        abort(403)

    if post.board.is_nsfl and post.is_nsfl:
        abort(403)

    post.is_nsfl = not post.is_nsfl
    g.db.add(post)

    if post.author_id!=g.user.id:
        ma=ModAction(
            kind="set_nsfl" if post.is_nsfl else "unset_nsfl",
            user_id=g.user.id,
            target_submission_id=post.id,
            board_id=post.board.id,
            note = None if mod else "admin action"
            )
        g.db.add(ma)

    g.db.commit()

    return "", 204


@app.route("/retry_thumb/<pid>", methods=["POST"])
@app.put("/api/v2/submissions/<pid>/thumb")
@is_not_banned
@api("identity")
def retry_thumbnail(pid):
    """
Retry thumbnail scraping on your post.

URL path parameters:
* `pid` - The base 36 post id.
"""

    post = get_post(pid)

    if post.author_id != g.user.id and g.user.admin_level < 3:
        return jsonify({"error": "That isn't your post."}), 403

    if post.is_archived:
        return jsonify({"error": "Post is archived"}), 409

    try:
        success= thumbnail_thread(post.base36id)
    except Exception as e:
        return jsonify({"error":str(e)}), 500

    if not success:
        return jsonify({"error":msg}), 500


    return jsonify({"message": "Success"})


@app.route("/save_post/<base36id>", methods=["POST"])
#@app.post("/api/v2/submissions/<base36id>/save")
@auth_required
def save_post(base36id):

    post=get_post(base36id)

    new_save=SaveRelationship(
        user_id=g.user.id,
        submission_id=post.id)

    g.db.add(new_save)

    try:
        g.db.flush()
    except:
        abort(422)

    g.db.commit()

    return "", 204


@app.route("/unsave_post/<base36id>", methods=["POST"])
#@app.delete("/api/v2/submissions/<base36id>/save")
@auth_required
def unsave_post(base36id):

    post=get_post(base36id)

    save=g.db.query(SaveRelationship).filter_by(user_id=g.user.id, submission_id=post.id).first()

    g.db.delete(save)

    g.db.commit()

    return "", 204
