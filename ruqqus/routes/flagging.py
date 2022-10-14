import time
from ruqqus.classes import *
from ruqqus.helpers.wrappers import *
from ruqqus.helpers.get import *
from ruqqus.helpers.base36 import *
from flask import g
from ruqqus.__main__ import app


@app.route("/api/flag/post/<pid>", methods=["POST"])
@is_not_banned
def api_flag_post(pid, v):

    post = get_post(pid)

    kind = request.form.get("report_type")

    if kind == "admin":
        existing = g.db.query(Flag).filter_by(
            user_id=v.id, post_id=post.id).filter(
            Flag.created_utc >= post.edited_utc).first()

        if existing:
            return "", 409

        flag = Flag(post_id=post.id,
                    user_id=v.id,
                    created_utc=int(time.time())
                    )

    elif kind == "guild":
        existing = g.db.query(Report).filter_by(
            user_id=v.id, post_id=post.id).filter(
            Report.created_utc >= post.edited_utc).first()

        if existing:
            return "", 409

        flag = Report(post_id=post.id,
                      user_id=v.id,
                      created_utc=int(time.time())
                      )
    else:
        return "", 422

    g.db.add(flag)

    return "", 204


@app.route("/api/flag/comment/<cid>", methods=["POST"])
@is_not_banned
def api_flag_comment(cid, v):

    comment = get_comment(cid)

    existing = g.db.query(CommentFlag).filter_by(
        user_id=v.id, comment_id=comment.id).filter(
        CommentFlag.created_utc >= comment.edited_utc).first()

    if existing:
        return "", 409

    flag = CommentFlag(comment_id=comment.id,
                       user_id=v.id,
                       created_utc=int(time.time())
                       )

    g.db.add(flag)

    return "", 204
