from syzitus.helpers.wrappers import *
from syzitus.helpers.base36 import base36decode
from syzitus.helpers.sanitize import *
from syzitus.helpers.get import get_post, get_comment
from syzitus.classes import *
from flask import g, session, abort, render_template, jsonify
from syzitus.__main__ import app, debug


@app.route("/api/vote/post/<pid>/<x>", methods=["POST"])
@app.post("/api/v2/submissions/<pid>/votes/<x>")
@is_not_banned
@no_negative_balance("toast")
@api("vote")
def api_vote_post(pid, x):

    """
Cast a vote on a post.

URL path parameters:
* `pid` - The base 36 post ID
* `x` - One of `1`, `0`, or `-1`, indicating upvote, novote, or downvote respectively
"""

    if x not in ["-1", "0", "1"]:
        abort(400)

    # disallow bots
    if request.headers.get("X-User-Type","").lower()=="bot":
        abort(403)

    x = int(x)

    # if x==-1:
    #     count=g.db.query(Vote).filter(
    #         Vote.user_id.in_(
    #             tuple(
    #                 [g.user.id]+[x.id for x in g.user.alts]
    #                 )
    #             ),
    #         Vote.created_utc > (g.timestamp-3600), 
    #         Vote.vote_type==-1
    #         ).count()
    #     if count >=15:
    #         return jsonify({"error": "You're doing that too much. Try again later."}), 403

    post = get_post(pid, no_text=True)

    if post.is_blocking:
        return jsonify({"error":"You can't vote on posts made by users who you are blocking."}), 403
    if post.is_blocked:
        return jsonify({"error":"You can't vote on posts made by users who are blocking you."}), 403


    if post.is_banned:
        return jsonify({"error":"That post has been removed."}), 403
    elif post.deleted_utc > 0:
        return jsonify({"error":"That post has been deleted."}), 403
    elif post.is_archived:
        return jsonify({"error":"That post is archived and can no longer be voted on."}), 403
    elif post.board.is_locked:
        return jsonify({"error":"This guild is locked and its content can no longer be voted on."}), 403

    # check for existing vote
    existing = g.db.query(Vote).filter_by(
        user_id=g.user.id, submission_id=post.id).first()
    if existing:
        existing.change_to(x)
        g.db.add(existing)

    else:
        vote = Vote(user_id=g.user.id,
                    vote_type=x,
                    submission_id=base36decode(pid),
                    creation_ip=request.remote_addr,
                    app_id=g.client.application.id if g.client else None
                    )

        g.db.add(vote)



    try:
        g.db.flush()
    except:
        return jsonify({"error":"Vote already exists."}), 422
        
    post.upvotes = post.ups
    post.downvotes = post.downs
    
    g.db.add(post)
    g.db.flush()

    post.score_hot = post.rank_hot
    post.score_disputed = post.rank_fiery
    post.score_top = post.score
    # post.score_activity=post.rank_activity
    post.score_best = post.rank_best

    g.db.add(post)

    g.db.commit()

    return "", 204


@app.route("/api/vote/comment/<cid>/<x>", methods=["POST"])
@app.post("/api/v2/comments/<cid>/votes/<x>")
@is_not_banned
@no_negative_balance("toast")
@api("vote")
def api_vote_comment(cid, x):

    """
Cast a vote on a comment.

URL path parameters:
* `cid` - The base 36 comment ID
* `x` - One of `1`, `0`, or `-1`, indicating upvote, novote, or downvote respectively
"""

    if x not in ["-1", "0", "1"]:
        abort(400)

    # disallow bots
    if request.headers.get("X-User-Type","").lower()=="bot":
        abort(403)

    x = int(x)

    comment = get_comment(cid, no_text=True)

    if comment.is_blocking:
        return jsonify({"error":"You can't vote on comments made by users who you are blocking."}), 403
    if comment.is_blocked:
        return jsonify({"error":"You can't vote on comments made by users who are blocking you."}), 403

    if comment.is_banned:
        return jsonify({"error":"That comment has been removed."}), 403
    elif comment.deleted_utc > 0:
        return jsonify({"error":"That comment has been deleted."}), 403
    elif comment.post.is_archived:
        return jsonify({"error":"This post and its comments are archived and can no longer be voted on."}), 403
    elif comment.board.is_locked:
        return jsonify({"error":"This guild is locked and its content can no longer be voted on."}), 403

    # check for existing vote
    existing = g.db.query(CommentVote).filter_by(
        user_id=g.user.id, comment_id=comment.id).first()
    if existing:
        existing.change_to(x)
        g.db.add(existing)
    else:

        vote = CommentVote(user_id=g.user.id,
                           vote_type=x,
                           comment_id=base36decode(cid),
                           creation_ip=request.remote_addr,
                           app_id=g.client.application.id if g.client else None
                           )

        g.db.add(vote)
    try:
        g.db.flush()
    except:
        return jsonify({"error":"Vote already exists."}), 422

    comment.upvotes = comment.ups
    comment.downvotes = comment.downs
    g.db.add(comment)
    g.db.flush()

    comment.score_disputed=comment.rank_fiery
    comment.score_hot = comment.rank_hot
    comment.score_top = comment.score

    g.db.add(comment)
    g.db.commit()

    return make_response(""), 204
