from syzitus.classes import *
from syzitus.helpers.wrappers import *
from syzitus.helpers.get import *
from flask import g, session, abort, render_template, jsonify
from syzitus.__main__ import app


@app.route("/api/flag/post", methods=["POST"])
@is_not_banned
def api_flag_post():

    pid=request.form.get("post_id")

    post = get_post(pid)

    kind = request.form.get("report_type")

    if kind == "admin":
        existing = g.db.query(Flag).filter_by(
            user_id=g.user.id, post_id=post.id).filter(
            Flag.created_utc >= post.edited_utc).first()

        if existing:
            return "", 409

        flag = Flag(post_id=post.id,
                    user_id=g.user.id,
                    created_utc=g.timestamp
                    )

    elif kind == "guild":
        existing = g.db.query(Report).filter_by(
            user_id=g.user.id, post_id=post.id).filter(
            Report.created_utc >= post.edited_utc).first()

        if existing:
            return "", 409

        flag = Report(post_id=post.id,
                      user_id=g.user.id,
                      created_utc=g.timestamp
                      )
    else:
        return "", 422

    g.db.add(flag)

    return jsonify({"message": "Your report has been received."})


@app.route("/api/flag/comment", methods=["POST"])
@is_not_banned
def api_flag_comment():

    cid=request.form.get("comment_id")

    comment = get_comment(cid)

    existing = g.db.query(CommentFlag).filter_by(
        user_id=g.user.id, comment_id=comment.id).filter(
        CommentFlag.created_utc >= comment.edited_utc).first()

    if existing:
        return "", 409

    flag = CommentFlag(comment_id=comment.id,
                       user_id=g.user.id,
                       created_utc=g.timestamp
                       )

    g.db.add(flag)

    return jsonify({"message": "Your report has been received."})
