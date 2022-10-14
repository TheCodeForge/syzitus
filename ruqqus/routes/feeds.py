from flask import *
import hmac
import html
from .front import frontlist
from datetime import datetime
from ruqqus.classes import *
from ruqqus.helpers.security import *
from ruqqus.helpers.jinja2 import full_link
from ruqqus.helpers.get import *
from yattag import Doc

from ruqqus.__main__ import app, limiter


# @app.route('/feeds/<sort>', methods=["GET"])
# def feeds_public(sort=None):

#     page = int(request.args.get("page", 1))
#     t = request.args.get('t')

#     posts = frontlist(
#         sort=sort,
#         page=page,
#         t=t,
#         v=None,
#         hide_offensive=False,
#         ids_only=False)

#     feed = AtomFeed(title=f'Top 5 {sort} Posts from ruqqus',
#                     feed_url=request.url,
#                     url=request.url_root
#                     )

#     for post in posts:
#         feed.add(post.title, post.body_html,
#                  content_type='html',
#                  author=post.author.username,
#                  url=full_link(post.permalink),
#                  updated=datetime.fromtimestamp(post.created_utc),
#                  published=datetime.fromtimestamp(post.created_utc),
#                  links=[{'href': post.url}]
#                  )

#     return feed.get_response()


@app.route('/feeds/@<username>/<key>/<sort>', methods=["GET"])
def feeds_user(sort=None, username=None, key=None):
    if not username and key:
        return abort(501)

    user = get_user(username)
    if user.is_banned or user.is_deleted:
        abort(403)

    if not hmac.compare_digest(key, user.feedkey):
        # invalid feedkey
        abort(403)

    page = int(request.args.get("page", 1))
    t = request.args.get('t')

    ids = user.idlist(sort=sort, page=page, t=t)
    posts = get_posts(ids, sort=sort, v=user)

    domain = environ.get(
    "domain", environ.get(
        "SERVER_NAME", None)).lstrip().rstrip()

    doc, tag, text = Doc().tagtext()

    with tag("feed", ("xmlns:media","http://search.yahoo.com/mrss/"), xmlns="http://www.w3.org/2005/Atom",):
        with tag("title", type="text"):
            text(f"{sort} posts from {domain}")

        doc.stag("link", href=request.url)
        doc.stag("link", href=request.url_root)

        for post in posts:
            #print("POST IMAGE "+ str( post.is_image ))
            board_name = f"+{post.board.name}"
            with tag("entry", ("xml:base", request.url)):
                with tag("title", type="text"):
                    text(post.title)

                with tag("id"):
                    text(post.fullname)

                if (post.edited_utc > 0):
                    with tag("updated"):
                        text(datetime.utcfromtimestamp(post.edited_utc).isoformat())

                with tag("published"):
                    text(datetime.utcfromtimestamp(post.created_utc).isoformat())
                
                doc.stag("link", href=post.url)

                with tag("author"):
                    with tag("name"):
                        text(post.author.username)
                    with tag("uri"):
                        text(f'https://{domain}/@{post.author.username}')

                doc.stag("link", href=full_link(post.permalink))

                doc.stag("category", term=board_name, label=board_name, schema=full_link("/" + board_name))

                image_url = post.thumb_url or post.embed_url or post.url
                #print("IS IMAGE")

                doc.stag("media:thumbnail", url=image_url)

                if len(post.body_html) > 0:
                    with tag("content", type="html"):
                        text(html.escape(f"<img src={image_url}/><br/>{post.body_html}"))

    return Response( "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"+ doc.getvalue(), mimetype="application/xml")


#@app.route('/feeds/+<guildname>/<sort>', methods=["GET"])
# def feeds_guild(sort=None, guildname=None):
#     if not guildname:
#         abort(404)
#     guild = get_guild(guildname)

#     page = int(request.args.get("page", 1))
#     t = request.args.get('t')

#     ids = guild.idlist(sort=sort, page=page, t=t)
#     posts = get_posts(ids, sort=sort)

#     feed = AtomFeed(title=f'{sort.capitalize()} posts from +{guild.name} on ruqqus',
#                     feed_url=request.url, url=request.url_root)

#     for post in posts:

#         feed.add(post.title, post.body_html,
#                  content_type='html',
#                  author=post.author.username,
#                  url=full_link(post.permalink),
#                  updated=datetime.fromtimestamp(post.created_utc),
#                  published=datetime.fromtimestamp(post.created_utc),
#                  links=[{'href': post.url}]
#                  )

#     return feed.get_response()
