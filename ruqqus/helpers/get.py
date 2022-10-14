from .base36 import *
from .sqla_values import *
from ruqqus.classes import *
from flask import g
from sqlalchemy import *
from sqlalchemy.orm import *
from urllib.parse import urlparse

import re


def get_user(username, v=None, nSession=None, graceful=False):

    username = username.replace('\\', '')
    username = username.replace('_', '\_')
    username = username.replace('%', '')

    if not nSession:
        nSession = g.db

    if v:
        isblocking = nSession.query(UserBlock).filter(
            UserBlock.user_id == v.id).subquery()

        isblocked =  nSession.query(UserBlock).filter(
            UserBlock.target_id==v.id).subquery()

        follow=nSession.query(Follow).filter_by(user_id=v.id).subquery()

        items=nSession.query(
            User,
            aliased(UserBlock, alias=isblocking),
            aliased(UserBlock, alias=isblocked),
            aliased(Follow, alias=follow)
            ).filter(or_(
                User.username.ilike(username),
                User.original_username.ilike(username)
            )).join(
            isblocking,
            isblocking.c.target_id==User.id,
            isouter=True
            ).join(
            isblocked,
            isblocked.c.user_id==User.id,
            isouter=True
            ).join(
            follow,
            follow.c.target_id==User.id,
            isouter=True
            ).first()

        if not items:
            if not graceful:
                abort(404)
            else:
                return None

        user=items[0]
        user._is_blocking = items[1]
        user._is_blocked = items[2]
        user._is_following = items[3]

    else:
        user = nSession.query(
        User
        ).filter(
        or_(
            User.username.ilike(username),
            User.original_username.ilike(username)
            )
        ).first()

        if not user:
            if not graceful:
                abort(404)
            else:
                return None


    return user


def get_account(base36id, v=None, nSession=None, graceful=False):

    if not nSession:
        nSession = g.db

    id = base36decode(base36id)

    user = nSession.query(User
                          ).filter(
        User.id == id
    ).first()

    if not user:
        if not graceful:
            abort(404)
        else:
            return None

    if v:
        block = nSession.query(UserBlock).filter(
            or_(
                and_(
                    UserBlock.user_id == v.id,
                    UserBlock.target_id == user.id
                ),
                and_(UserBlock.user_id == user.id,
                     UserBlock.target_id == v.id
                     )
            )
        ).first()

        user._is_blocking = block and block.user_id == v.id
        user._is_blocked = block and block.target_id == v.id

    return user


def get_post(pid, v=None, graceful=False, nSession=None, no_text=False, **kwargs):

    if isinstance(pid, str):
        i = base36decode(pid)
    else:
        i = pid

    nSession = nSession or kwargs.get("session")or g.db

    # exile=nSession.query(ModAction).options(
    #     lazyload('*')
    #     ).filter_by(
    #     kind="exile_user",
    #     target_submission_id=i
    #     ).subquery()

    if v:
        vt = nSession.query(Vote).filter_by(
            user_id=v.id, submission_id=i).subquery()
        mod = nSession.query(ModRelationship).filter_by(
            user_id=v.id, accepted=True, invite_rescinded=False).subquery()
        boardblocks = nSession.query(
            BoardBlock).filter_by(user_id=v.id).subquery()
        blocking = v.blocking.subquery()
        blocked = v.blocked.subquery()
        sub = nSession.query(Subscription).filter_by(user_id=v.id, is_active=True).subquery()

        items = nSession.query(
            Submission,
            vt.c.vote_type,
            aliased(ModRelationship, alias=mod),
            boardblocks.c.id,
            blocking.c.id,
            blocked.c.id,
            aliased(Subscription, alias=sub)
            # aliased(ModAction, alias=exile)
        ).options(
            lazyload('*'),
            joinedload(Submission.submission_aux),
            joinedload(Submission.author),
            Load(User).lazyload('*'),
            joinedload(Submission.author).joinedload(User.title),
            Load(Board).lazyload('*'),
            joinedload(Submission.board),
            joinedload(Submission.original_board),
            Load(UserBlock).lazyload('*'),
            joinedload(Submission.awards),
            joinedload(Submission.domain_obj),
            joinedload(Submission.reposts).lazyload('*'),
            Load(AwardRelationship).lazyload('*')
        )
        
        if no_text:
            items=items.options(lazyload(Submission.submission_aux))

        if v.admin_level>=4:
            items=items.options(joinedload(Submission.oauth_app))

        items=items.filter(Submission.id == i
        ).join(
            vt, 
            vt.c.submission_id == Submission.id, 
            isouter=True
        ).join(
            mod, 
            mod.c.board_id == Submission.board_id, 
            isouter=True
        ).join(
            boardblocks, 
            boardblocks.c.board_id == Submission.board_id, 
            isouter=True
        ).join(
            blocking, 
            blocking.c.target_id == Submission.author_id, 
            isouter=True
        ).join(
            blocked, 
            blocked.c.user_id == Submission.author_id, 
            isouter=True
        ).join(
            sub,
            sub.c.board_id == Submission.board_id,
            isouter=True
        # ).join(
        #     exile,
        #     and_(exile.c.target_submission_id==Submission.id, exile.c.board_id==Submission.original_board_id),
        #     isouter=True
        ).first()

        if not items and not graceful:
            abort(404)

        x = items[0]
        x._voted = items[1] or 0
        x._is_guildmaster = items[2] or 0
        x._is_blocking_guild = items[3] or 0
        x._is_blocking = items[4] or 0
        x._is_blocked = items[5] or 0
        x.board._is_subscribed=items[6] or 0
        # x._is_exiled_for=items[5] or 0

    else:
        items = nSession.query(
            Submission,
            # aliased(ModAction, alias=exile)
        ).options(
            lazyload('*'),
            joinedload(Submission.submission_aux),
            joinedload(Submission.author),
            Load(User).lazyload('*'),
            joinedload(Submission.author).joinedload(User.title),
            Load(Board).lazyload('*'),
            joinedload(Submission.board),
            joinedload(Submission.original_board),
            Load(UserBlock).lazyload('*'),
            joinedload(Submission.awards),
            joinedload(Submission.domain_obj),
            joinedload(Submission.reposts).lazyload('*'),
            Load(AwardRelationship).lazyload('*')
        # ).join(
        #     exile,
        #     and_(exile.c.target_submission_id==Submission.id, exile.c.board_id==Submission.original_board_id),
        #     isouter=True
        ).filter(Submission.id == i).first()

        if not items and not graceful:
            abort(404)

        x=items
        # x._is_exiled_for=items[1] or 0

    return x


def get_posts(pids, sort="hot", v=None):

    if not pids:
        return []

    pids=tuple(pids)

    # exile=g.db.query(ModAction).options(
    #     lazyload('*')
    #     ).filter(
    #     ModAction.kind=="exile_user",
    #     ModAction.target_submission_id.in_(pids)
    #     ).subquery()

    if v:
        vt = g.db.query(Vote).filter(
            Vote.submission_id.in_(pids), 
            Vote.user_id==v.id
            ).subquery()

        mod = g.db.query(ModRelationship).filter_by(
            user_id=v.id, accepted=True, invite_rescinded=False).subquery()

        boardblocks = g.db.query(BoardBlock).filter_by(
            user_id=v.id).subquery()
        blocking = v.blocking.subquery()
        blocked = v.blocked.subquery()
        subs = g.db.query(Subscription).filter_by(user_id=v.id, is_active=True).subquery()

        query = g.db.query(
            Submission,
            vt.c.vote_type,
            aliased(ModRelationship, alias=mod),
            boardblocks.c.id,
            blocking.c.id,
            blocked.c.id,
            subs.c.id,
            # aliased(ModAction, alias=exile)
        ).options(
            lazyload('*'),
            joinedload(Submission.submission_aux),
            joinedload(Submission.author),
            Load(User).lazyload('*'),
            joinedload(Submission.author).joinedload(User.title),
            Load(Board).lazyload('*'),
            joinedload(Submission.board),
            joinedload(Submission.original_board),
            Load(UserBlock).lazyload('*'),
            joinedload(Submission.awards),
            joinedload(Submission.domain_obj),
            joinedload(Submission.reposts).lazyload('*'),
            Load(AwardRelationship).lazyload('*')
        ).filter(
            Submission.id.in_(pids)
        ).join(
            vt, vt.c.submission_id==Submission.id, isouter=True
        ).join(
            mod, 
            mod.c.board_id == Submission.board_id, 
            isouter=True
        ).join(
            boardblocks, 
            boardblocks.c.board_id == Submission.board_id, 
            isouter=True
        ).join(
            blocking, 
            blocking.c.target_id == Submission.author_id, 
            isouter=True
        ).join(
            blocked, 
            blocked.c.user_id == Submission.author_id, 
            isouter=True
        ).join(
            subs, 
            subs.c.board_id == Submission.board_id, 
            isouter=True
        # ).join(
        #     exile,
        #     and_(exile.c.target_submission_id==Submission.id, exile.c.board_id==Submission.original_board_id),
        #     isouter=True
        ).order_by(None).all()

        posts=[x for x in query]

        output = [p[0] for p in query]
        for i in range(len(output)):
            output[i]._voted = posts[i][1] or 0
            output[i]._is_guildmaster = posts[i][2] or 0
            output[i]._is_blocking_guild = posts[i][3] or 0
            output[i]._is_blocking = posts[i][4] or 0
            output[i]._is_blocked = posts[i][5] or 0
            output[i]._is_subscribed = posts[i][6] or 0
            output[i].board._is_subscribed=posts[i][6] or 0
            # output[i]._is_exiled_for=posts[i][7] or 0
    else:
        query = g.db.query(
            Submission,
            # aliased(ModAction, alias=exile)
        ).options(
            lazyload('*'),
            joinedload(Submission.submission_aux),
            joinedload(Submission.author),
            Load(User).lazyload('*'),
            joinedload(Submission.author).joinedload(User.title),
            Load(Board).lazyload('*'),
            joinedload(Submission.board),
            joinedload(Submission.original_board),
            Load(UserBlock).lazyload('*'),
            joinedload(Submission.awards),
            joinedload(Submission.domain_obj),
            joinedload(Submission.reposts).lazyload('*'),
            Load(AwardRelationship).lazyload('*')
        ).filter(Submission.id.in_(pids)
        # ).join(
        #     exile,
        #     and_(exile.c.target_submission_id==Submission.id, exile.c.board_id==Submission.original_board_id),
        #     isouter=True
        ).order_by(None).all()

        output=[x for x in query]

        # output=[]
        # for post in posts:
        #     p=post[0]
        #     p._is_exiled_for=post[1] or 0
        #     output.append(p)

    return sorted(output, key=lambda x: pids.index(x.id))


def get_post_with_comments(pid, sort_type="top", v=None):

    post = get_post(pid, v=v)

    exile=g.db.query(ModAction
        ).options(
        lazyload('*')
        ).filter_by(
        kind="exile_user"
        ).distinct(ModAction.target_comment_id).subquery()

    if v:
        votes = g.db.query(CommentVote).filter_by(user_id=v.id).subquery()

        blocking = v.blocking.subquery()

        blocked = v.blocked.subquery()

        comms = g.db.query(
            Comment,
            votes.c.vote_type,
            blocking.c.id,
            blocked.c.id,
            aliased(ModAction, alias=exile)
        ).options(
            lazyload('*'),
            joinedload(Comment.comment_aux),
            joinedload(Comment.author),
            joinedload(Comment.distinguished_board),
            joinedload(Comment.awards),
            Load(User).lazyload('*'),
            Load(User).joinedload(User.title),
            joinedload(Comment.post),
            Load(Submission).lazyload('*'),
            Load(Submission).joinedload(Submission.submission_aux),
            Load(Submission).joinedload(Submission.board),
            Load(CommentVote).lazyload('*'),
            Load(UserBlock).lazyload('*'),
            Load(ModAction).lazyload('*'),
            Load(Board).lazyload('*'),
            Load(AwardRelationship).lazyload('*')
        ).filter(
            Comment.parent_submission == post.id,
            Comment.level <= 6
        )


        if v.admin_level >=4:

            comms=comms.options(joinedload(Comment.oauth_app))

        comms=comms.join(
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
            and_(exile.c.target_comment_id==Comment.id, exile.c.board_id==Comment.original_board_id),
            isouter=True
        )

        if sort_type == "hot":
            comments = comms.order_by(Comment.score_hot.desc()).all()
        elif sort_type == "top":
            comments = comms.order_by(Comment.score_top.desc()).all()
        elif sort_type == "new":
            comments = comms.order_by(Comment.created_utc.desc()).all()
        elif sort_type == "old":
            comments = comms.order_by(Comment.created_utc.asc()).all()
        elif sort_type == "disputed":
            comments = comms.order_by(Comment.score_disputed.desc()).all()
        elif sort_type == "random":
            c = comms.all()
            comments = random.sample(c, k=len(c))
        else:
            abort(422)

        output = []
        for c in comments:
            comment = c[0]
            comment._voted = c[1] or 0
            comment._is_blocking = c[2] or 0
            comment._is_blocked = c[3] or 0
            comment._is_guildmaster=post._is_guildmaster
            comment._is_exiled_for=c[4]
            output.append(comment)
        post._preloaded_comments = output

    else:
        comms = g.db.query(
            Comment,
            aliased(ModAction, alias=exile)
        ).options(
            lazyload('*'),
            joinedload(Comment.comment_aux),
            joinedload(Comment.author),
            Load(User).lazyload('*'),
            Load(User).joinedload(User.title),
            joinedload(Comment.post),
            Load(Submission).lazyload('*'),
            Load(Submission).joinedload(Submission.submission_aux),
            Load(Submission).joinedload(Submission.board),
            Load(CommentVote).lazyload('*'),
            Load(UserBlock).lazyload('*'),
            Load(ModAction).lazyload('*'),
            joinedload(Comment.distinguished_board),
            joinedload(Comment.awards),
            Load(Board).lazyload('*'),
            Load(AwardRelationship).lazyload('*')
        ).filter(
            Comment.parent_submission == post.id,
            Comment.level <= 6
        ).join(
            exile,
            and_(exile.c.target_comment_id==Comment.id, exile.c.board_id==Comment.original_board_id),
            isouter=True
        )

        if sort_type == "hot":
            comments = comms.order_by(Comment.score_hot.desc()).all()
        elif sort_type == "top":
            comments = comms.order_by(Comment.score_top.desc()).all()
        elif sort_type == "new":
            comments = comms.order_by(Comment.created_utc.desc()).all()
        elif sort_type == "old":
            comments = comms.order_by(Comment.created_utc.asc()).all()
        elif sort_type == "disputed":
            comments = comms.order_by(Comment.score_disputed.desc()).all()
        elif sort_type == "random":
            c = comms.all()
            comments = random.sample(c, k=len(c))
        else:
            abort(422)

        output = []
        for c in comments:
            comment=c[0]
            comment._is_exiled_for=c[1]
            output.append(comment)

        # output=[x for x in comments]


        post._preloaded_comments = output

    return post


def get_comment(cid, nSession=None, v=None, graceful=False, no_text=False, **kwargs):

    if isinstance(cid, str):
        i = base36decode(cid)
    else:
        i = cid

    nSession = nSession or kwargs.get('session') or g.db

    exile = nSession.query(ModAction
         ).options(
         lazyload('*')
         ).filter_by(
         kind="exile_user"
         ).subquery()

    if v:
        blocking = v.blocking.subquery()
        blocked = v.blocked.subquery()
        vt = nSession.query(CommentVote).filter(
            CommentVote.user_id == v.id,
            CommentVote.comment_id == i).subquery()

        mod=nSession.query(ModRelationship
            ).filter_by(
            user_id=v.id,
            accepted=True
            ).subquery()


        items = nSession.query(
            Comment, 
            vt.c.vote_type,
            aliased(ModRelationship, alias=mod),
            aliased(ModAction, alias=exile)
        ).options(
            lazyload('*'),
            joinedload(Comment.comment_aux),
            joinedload(Comment.author),
            Load(User).lazyload('*'),
            Load(User).joinedload(User.title),
            joinedload(Comment.post),
            Load(Submission).lazyload('*'),
            Load(Submission).joinedload(Submission.submission_aux),
            Load(Submission).joinedload(Submission.board),
            Load(CommentVote).lazyload('*'),
            Load(UserBlock).lazyload('*'),
            Load(ModAction).lazyload('*'),
            joinedload(Comment.distinguished_board),
            joinedload(Comment.awards),
            Load(Board).lazyload('*'),
            Load(AwardRelationship).lazyload('*')
        )
        
        if no_text:
            items=items.options(lazyload(Comment.comment_aux))

        if v.admin_level >=4:
            items=items.options(joinedload(Comment.oauth_app))

        items=items.filter(
            Comment.id == i
        ).join(
            vt, 
            vt.c.comment_id == Comment.id, 
            isouter=True
        ).join(
            Comment.post,
            isouter=True
        ).join(
            mod,
            mod.c.board_id==Submission.board_id,
            isouter=True
        ).join(
            exile,
            and_(exile.c.target_comment_id==Comment.id, exile.c.board_id==Comment.original_board_id),
            isouter=True
        ).first()

        if not items and not graceful:
            abort(404)

        x = items[0]
        x._voted = items[1] or 0
        x._is_guildmaster=items[2] or 0
        x._is_exiled_for=items[3] or 0

        block = nSession.query(UserBlock).filter(
            or_(
                and_(
                    UserBlock.user_id == v.id,
                    UserBlock.target_id == x.author_id
                ),
                and_(UserBlock.user_id == x.author_id,
                     UserBlock.target_id == v.id
                     )
            )
        ).first()

        x._is_blocking = block and block.user_id == v.id
        x._is_blocked = block and block.target_id == v.id

    else:
        q = nSession.query(
            Comment,
            aliased(ModAction, alias=exile)
        ).options(
            joinedload(Comment.author).joinedload(User.title),
        ).join(
            exile,
            and_(exile.c.target_comment_id==Comment.id, exile.c.board_id==Comment.original_board_id),
            isouter=True
        ).filter(Comment.id == i).first()

        if not q and not graceful:
            abort(404)

        x=q[0]
        x._is_exiled_for=q[1]


    return x


def get_comments(cids, v=None, nSession=None, sort_type=None,
                 load_parent=False, **kwargs):

    if not cids:
        return []

    cids=tuple(cids)

    nSession = nSession or kwargs.get('session') or g.db

    exile=nSession.query(ModAction
        ).options(
        lazyload('*')
        ).filter(
        ModAction.kind=="exile_user",
        ModAction.target_comment_id.in_(cids)
        ).distinct(ModAction.target_comment_id).subquery()

    if v:
        votes = nSession.query(CommentVote).filter_by(user_id=v.id).subquery()

        blocking = v.blocking.subquery()

        blocked = v.blocked.subquery()

        mod = g.db.query(ModRelationship).filter_by(user_id=v.id, accepted=True).subquery()

        comms = nSession.query(
            Comment,
            votes.c.vote_type,
            blocking.c.id,
            blocked.c.id,
            aliased(ModAction, alias=exile),
            aliased(ModRelationship, alias=mod)
        ).options(
            lazyload('*'),
            joinedload(Comment.comment_aux),
            joinedload(Comment.author),
            joinedload(Comment.post),
            Load(User).lazyload('*'),
            Load(User).joinedload(User.title),
            Load(Submission).lazyload('*'),
            Load(Submission).joinedload(Submission.submission_aux),
            Load(Submission).joinedload(Submission.board),
            Load(CommentVote).lazyload('*'),
            Load(UserBlock).lazyload('*'),
            Load(ModAction).lazyload('*'),
            Load(ModRelationship).lazyload('*'),
            joinedload(Comment.distinguished_board),
            joinedload(Comment.awards),
            Load(Board).lazyload('*'),
            Load(AwardRelationship).lazyload('*')
        ).filter(
            Comment.id.in_(cids)
        )


        if v.admin_level >=4:

            comms=comms.options(joinedload(Comment.oauth_app))

        comms=comms.join(
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
            and_(exile.c.target_comment_id==Comment.id, exile.c.board_id==Comment.original_board_id),
            isouter=True
        ).join(
            mod,
            mod.c.board_id==Comment.original_board_id,
            isouter=True
        )

        if sort_type == "hot":
            comments = comms.order_by(Comment.score_hot.desc()).all()
        elif sort_type == "top":
            comments = comms.order_by(Comment.score_top.desc()).all()
        elif sort_type == "new":
            comments = comms.order_by(Comment.created_utc.desc()).all()
        elif sort_type == "old":
            comments = comms.order_by(Comment.created_utc.asc()).all()
        elif sort_type == "disputed":
            comments = comms.order_by(Comment.score_disputed.desc()).all()
        elif sort_type == "random":
            c = comms.all()
            comments = random.sample(c, k=len(c))
        else:
            comments=comms.all()

        output = []
        for c in comments:
            comment = c[0]
            comment._voted = c[1] or 0
            comment._is_blocking = c[2] or 0
            comment._is_blocked = c[3] or 0
            
            comment._is_exiled_for=c[4]
            comment._is_guildmaster=c[5] or None
            output.append(comment)

    else:
        comms = nSession.query(
            Comment,
            aliased(ModAction, alias=exile)
        ).options(
            lazyload('*'),
            joinedload(Comment.post),
            joinedload(Comment.comment_aux),
            joinedload(Comment.author),
            Load(User).lazyload('*'),
            Load(User).joinedload(User.title),
            Load(Submission).lazyload('*'),
            Load(Submission).joinedload(Submission.submission_aux),
            Load(Submission).joinedload(Submission.board),
            Load(CommentVote).lazyload('*'),
            Load(UserBlock).lazyload('*'),
            Load(ModAction).lazyload('*'),
            Load(ModRelationship).lazyload('*'),
            joinedload(Comment.distinguished_board),
            joinedload(Comment.awards),
            Load(Board).lazyload('*'),
            Load(AwardRelationship).lazyload('*')
        ).filter(
            Comment.id.in_(cids)
        ).join(
            exile,
            and_(exile.c.target_comment_id==Comment.id, exile.c.board_id==Comment.original_board_id),
            isouter=True
        )

        if sort_type == "hot":
            comments = comms.order_by(Comment.score_hot.desc()).all()
        elif sort_type == "top":
            comments = comms.order_by(Comment.score_top.desc()).all()
        elif sort_type == "new":
            comments = comms.order_by(Comment.created_utc.desc()).all()
        elif sort_type == "old":
            comments = comms.order_by(Comment.created_utc.asc()).all()
        elif sort_type == "disputed":
            comments = comms.order_by(Comment.score_disputed.desc()).all()
        elif sort_type == "random":
            c = comms.all()
            comments = random.sample(c, k=len(c))
        else:
            comments=comms.all()

        output = []
        for c in comments:
            comment=c[0]
            comment._is_exiled_for=c[1]
            output.append(comment)


    output = sorted(output, key=lambda x: cids.index(x.id))

    if load_parent:
        parents=get_comments(
            [x.parent_comment_id for x in output if x.parent_comment_id], 
            v=v, 
            nSession=nSession, 
            load_parent=False
            )

        parents={x.id: x for x in parents}

        for c in output:
            c._parent_comment=parents.get(c.parent_comment_id)

    return output


def get_board(bid,v=None, graceful=False):

    if isinstance(bid, str):
        bid=base36decode(bid)

        
    if v:
        sub = g.db.query(Subscription).filter_by(user_id=v.id, is_active=True).subquery()
        items = g.db.query(
            Board,
            aliased(Subscription, alias=sub)
            ).options(
            joinedload(Board.moderators).joinedload(ModRelationship.user),
            joinedload(Board.subcat).joinedload(SubCategory.category)
            ).filter(
                Board.id==bid
            ).join(
            sub,
            sub.c.board_id==Board.id,
            isouter=True
        ).first()

        if items:
            board=items[0]
            board._is_subscribed=items[1]
        else:
            board=None
    else:
            
        query = g.db.query(Board).options(
            joinedload(Board.moderators).joinedload(ModRelationship.user),
            joinedload(Board.subcat).joinedload(SubCategory.category)
            ).filter(
                    Board.id==bid)
        board=query.first()
    
    
    
    if not board:
        if graceful:
            return None
        else:
            abort(404)
    return board


def get_boards(bids, v=None, graceful=False):
        
    if v:
        sub = g.db.query(Subscription).filter_by(user_id=v.id, is_active=True).subquery()
        items = g.db.query(
            Board,
            aliased(Subscription, alias=sub)
            ).options(
            joinedload(Board.moderators).joinedload(ModRelationship.user),
            joinedload(Board.subcat).joinedload(SubCategory.category)
            ).filter(
                Board.id.in_(tuple(bids))
            ).join(
            sub,
            sub.c.board_id==Board.id,
            isouter=True
        ).all()

        
        output=[]
        for entry in items:
            board=entry[0]
            board._is_subscribed=entry[1]
            output.append(board)
    else:
            
        output = g.db.query(Board).options(
            joinedload(Board.moderators).joinedload(ModRelationship.user),
            joinedload(Board.subcat).joinedload(SubCategory.category)
            ).filter(
                    Board.id.in_(bids)
        ).all()
    
    
    
    if not output:
        if graceful:
            return []
        else:
            abort(404)
            
    output=sorted(output, key=lambda x:bids.index(x.id))
    
    return output



def get_guild(name, v=None, graceful=False, db=None):

    if not db:
        db=g.db

    name = name.lstrip('+')

    name = name.replace('\\', '')
    name = name.replace('_', '\_')
    name = name.replace('%', '')

    if v:
        sub = g.db.query(Subscription).filter_by(user_id=v.id, is_active=True).subquery()

        items = g.db.query(
            Board,
            aliased(Subscription, alias=sub)
            ).options(
            joinedload(Board.moderators).joinedload(ModRelationship.user),
            joinedload(Board.subcat).joinedload(SubCategory.category)
            ).filter(
                    Board.name.ilike(name)
            ).join(
            sub,
            sub.c.board_id==Board.id,
            isouter=True
            ).first()

        if items:
            board=items[0]
            board._is_subscribed=items[1]
        else:
            board=None
    else:
            
        query = g.db.query(Board).options(
            joinedload(Board.moderators).joinedload(ModRelationship.user),
            joinedload(Board.subcat).joinedload(SubCategory.category)
            ).filter(
                    Board.name.ilike(name)
        )
        board=query.first()
    
    if not board:
        if not graceful:
            abort(404)
        else:
            return None

    return board


def get_domain(s):

    # parse domain into all possible subdomains
    parts = s.split(".")
    domain_list = set([])
    for i in range(len(parts)):
        new_domain = parts[i]
        for j in range(i + 1, len(parts)):
            new_domain += "." + parts[j]

        domain_list.add(new_domain)

    domain_list = tuple(list(domain_list))

    doms = [x for x in g.db.query(Domain).filter(
        Domain.domain.in_(domain_list)).all()]

    if not doms:
        return None

    # return the most specific domain - the one with the longest domain
    # property
    doms = sorted(doms, key=lambda x: len(x.domain), reverse=True)

    return doms[0]


def get_title(x):

    title = g.db.query(Title).filter_by(id=x).first()

    if not title:
        abort(400)

    else:
        return title


def get_mod(uid, bid):

    mod = g.db.query(ModRelationship).filter_by(board_id=bid,
                                                user_id=uid,
                                                accepted=True,
                                                invite_rescinded=False).first()

    return mod


def get_application(client_id, graceful=False):

    application = g.db.query(OauthApp).filter_by(client_id=client_id).first()
    if not application and not graceful:
        abort(404)

    return application


def get_from_permalink(link, v=None):

    link=urlparse(link).path

    if "@" in link:

        name = re.search("/@(\w+)", link)
        if name:
            name=name.group(1)
            return get_user(name, v=v)

    if "+" in link:

        x = re.search("/\+(\w+)$", link)
        if x:
            name=x.group(1)
            return get_guild(name, v=v)

    ids = re.search("/\+\w+/post/(\w+)/[^/]+(/(\w+))?", link)

    post_id = ids.group(1)
    comment_id = ids.group(3)

    if comment_id:
        return get_comment(comment_id, v=v)

    else:
        return get_post(post_id, v=v)


def get_from_fullname(fullname, v=None, graceful=False):

    parts = fullname.split('_')

    if len(parts) != 2:
        if graceful:
            return None
        else:
            abort(400)

    kind = parts[0]
    b36 = parts[1]

    if kind == 't1':
        return get_account(b36, v=v, graceful=graceful)
    elif kind == 't2':
        return get_post(b36, v=v, graceful=graceful)
    elif kind == 't3':
        return get_comment(b36, v=v, graceful=graceful)
    elif kind == 't4':
        return get_board(b36, graceful=graceful)

def get_txn(paypal_id):

    txn= g.db.query(PayPalTxn).filter_by(paypal_id=paypal_id).first()

    if not txn:
        abort(404)

    return txn

def get_txid(txid):

    txn= g.db.query(PayPalTxn).filter_by(id=base36decode(txid)).first()

    if not txn:
        abort(404)
    elif txn.status==1:
        abort(404)

    return txn


def get_promocode(code):

    code = code.replace('\\', '')
    code = code.replace("_", "\_")

    code = g.db.query(PromoCode).filter(PromoCode.code.ilike(code)).first()

    return code
