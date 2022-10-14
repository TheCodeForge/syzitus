from werkzeug.security import generate_password_hash, check_password_hash
from flask import *
import time
from sqlalchemy import *
from sqlalchemy.orm import relationship, deferred, joinedload, lazyload, contains_eager, aliased, Load
from os import environ
from secrets import token_hex
import random
import pyotp

from ruqqus.helpers.base36 import *
from ruqqus.helpers.security import *
from ruqqus.helpers.lazy import lazy
import ruqqus.helpers.aws as aws
from ruqqus.helpers.discord import add_role, delete_role, discord_log_event
#from ruqqus.helpers.alerts import send_notification
from .votes import Vote
from .alts import Alt
from .titles import Title
from .submission import Submission, SubmissionAux, SaveRelationship
from .comment import Comment, Notification
from .boards import Board
from .board_relationships import *
from .mix_ins import *
from .subscriptions import *
from .userblock import *
from .badges import *
from .clients import *
from .paypal import PayPalTxn
from .flags import Report
from ruqqus.__main__ import Base, cache, app


class User(Base, Stndrd, Age_times):

    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, default=None)
    email = Column(String, default=None)
    passhash = deferred(Column(String, default=None))
    created_utc = Column(Integer, default=0)
    admin_level = Column(Integer, default=0)
    is_activated = Column(Boolean, default=False)
    over_18 = Column(Boolean, default=False)
    creation_ip = Column(String, default=None)
    submissions = relationship(
        "Submission",
        lazy="dynamic",
        primaryjoin="Submission.author_id==User.id",
        backref="author_rel")
    comments = relationship(
        "Comment",
        lazy="dynamic",
        primaryjoin="Comment.author_id==User.id")
    votes = relationship("Vote", lazy="dynamic", backref="users")
    commentvotes = relationship("CommentVote", lazy="dynamic", backref="users")
    bio = Column(String, default="")
    bio_html = Column(String, default="")
    _badges = relationship("Badge", lazy="dynamic", backref="user")
    real_id = Column(String, default=None)
    notifications = relationship(
        "Notification",
        lazy="dynamic")

    #unread_notifications_relationship=relationship(
    #    "Notification",
    #    primaryjoin="and_(Notification.user_id==User.id, Notification.read==False)")

    referred_by = Column(Integer, default=None)
    is_banned = Column(Integer, default=0)
    unban_utc = Column(Integer, default=0)
    ban_reason = Column(String, default="")
    defaultsorting = Column(String, default="hot")
    defaulttime = Column(String, default="all")
    feed_nonce = Column(Integer, default=0)
    login_nonce = Column(Integer, default=0)
    title_id = Column(Integer, ForeignKey("titles.id"), default=None)
    title = relationship("Title", lazy="joined")
    has_profile = Column(Boolean, default=False)
    has_banner = Column(Boolean, default=False)
    reserved = Column(String(256), default=None)
    is_nsfw = Column(Boolean, default=False)
    tos_agreed_utc = Column(Integer, default=0)
    profile_nonce = Column(Integer, default=0)
    banner_nonce = Column(Integer, default=0)
    last_siege_utc = Column(Integer, default=0)
    mfa_secret = deferred(Column(String(16), default=None))
    hide_offensive = Column(Boolean, default=True)
    hide_bot = Column(Boolean, default=False)
    show_nsfl = Column(Boolean, default=False)
    is_private = Column(Boolean, default=False)
    unban_utc = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)
    delete_reason = Column(String(500), default='')
    filter_nsfw = Column(Boolean, default=False)
    stored_karma = Column(Integer, default=0)
    stored_subscriber_count=Column(Integer, default=0)
    """posts_last_checked_utc = Column(Integer, default=0)
    replies_last_checked_utc = Column(Integer, default=0)
    mentions_last_checked_utc = Column(Integer, default=0)"""

    auto_join_chat=Column(Boolean, default=False)

    coin_balance=Column(Integer, default=0)
    premium_expires_utc=Column(Integer, default=0)
    negative_balance_cents=Column(Integer, default=0)

    is_nofollow = Column(Boolean, default=False)
    custom_filter_list=Column(String(1000), default="")
    discord_id=Column(String(64), default=None)
    creation_region=Column(String(2), default=None)
    ban_evade=Column(Integer, default=0)

    profile_upload_ip=deferred(Column(String(255), default=None))
    banner_upload_ip=deferred(Column(String(255), default=None))
    profile_upload_region=deferred(Column(String(2)))
    banner_upload_region=deferred(Column(String(2)))
    
    color=Column(String(6), default="805ad5")
    secondary_color=Column(String(6), default="ffff00")
    signature=Column(String(280), default='')
    signature_html=Column(String(512), default="")

    #stuff to support name changes
    profile_set_utc=deferred(Column(Integer, default=0))
    banner_set_utc=deferred(Column(Integer, default=0))
    original_username=deferred(Column(String(255)))
    name_changed_utc=deferred(Column(Integer, default=0))


    moderates = relationship("ModRelationship")
    banned_from = relationship("BanRelationship",
                               primaryjoin="BanRelationship.user_id==User.id")
    subscriptions = relationship("Subscription")
    boards_created = relationship("Board", lazy="dynamic")
    contributes = relationship(
        "ContributorRelationship",
        lazy="dynamic",
        primaryjoin="ContributorRelationship.user_id==User.id")
    board_blocks = relationship("BoardBlock", lazy="dynamic")

    following = relationship("Follow", primaryjoin="Follow.user_id==User.id")
    followers = relationship("Follow", primaryjoin="Follow.target_id==User.id")

    blocking = relationship(
        "UserBlock",
        lazy="dynamic",
        primaryjoin="User.id==UserBlock.user_id")
    blocked = relationship(
        "UserBlock",
        lazy="dynamic",
        primaryjoin="User.id==UserBlock.target_id")

    _applications = relationship("OauthApp", lazy="dynamic")
    authorizations = relationship("ClientAuth", lazy="dynamic")
    #notification_subscriptions = relationship("PostNotificationSubscriptions", lazy="dynamic")

    saved_posts=relationship(
        "SaveRelationship",
        lazy="dynamic",
        primaryjoin="User.id==SaveRelationship.user_id")

    _transactions = relationship(
        "PayPalTxn",
        lazy="dynamic",
        primaryjoin="PayPalTxn.user_id==User.id")

    # properties defined as SQL server-side functions
    energy = deferred(Column(Integer, server_default=FetchedValue()))
    comment_energy = deferred(Column(Integer, server_default=FetchedValue()))
    referral_count = deferred(Column(Integer, server_default=FetchedValue()))
    follower_count = deferred(Column(Integer, server_default=FetchedValue()))

    def __init__(self, **kwargs):

        if "password" in kwargs:

            kwargs["passhash"] = self.hash_password(kwargs["password"])
            kwargs.pop("password")

        kwargs["created_utc"] = int(time.time())

        super().__init__(**kwargs)

    def has_block(self, target):

        return g.db.query(UserBlock).filter_by(
            user_id=self.id, target_id=target.id).first()

    def is_blocked_by(self, user):

        return g.db.query(UserBlock).filter_by(
            user_id=user.id, target_id=self.id).first()

    def any_block_exists(self, other):

        return g.db.query(UserBlock).filter(or_(and_(UserBlock.user_id == self.id, UserBlock.target_id == other.id), and_(
            UserBlock.user_id == other.id, UserBlock.target_id == self.id))).first()

    def has_blocked_guild(self, board):

        return g.db.query(BoardBlock).filter_by(
            user_id=self.id, board_id=board.id).first()

    def validate_2fa(self, token):

        x = pyotp.TOTP(self.mfa_secret)
        return x.verify(token, valid_window=1)

    @property
    def mfa_removal_code(self):

        hashstr = f"{self.mfa_secret}+{self.id}+{self.original_username}"

        hashstr= generate_hash(hashstr)

        removal_code = base36encode(int(hashstr,16))

        #should be 25char long, left pad if needed
        while len(removal_code)<25:
            removal_code="0"+removal_code

        return removal_code

    @property
    def boards_subscribed(self):

        boards = [
            x.board for x in self.subscriptions if x.is_active and not x.board.is_banned]
        return boards

    @property
    def age(self):
        return int(time.time()) - self.created_utc

    @cache.memoize(timeout=300)
    def idlist(self, sort=None, page=1, t=None, filter_words="", **kwargs):

        posts = g.db.query(Submission.id).options(lazyload('*')).filter_by(is_banned=False,
                                                                           deleted_utc=0,
                                                                           stickied=False
                                                                           )

        if not self.over_18:
            posts = posts.filter_by(over_18=False)

        if self.hide_offensive:
            posts = posts.filter_by(is_offensive=False)

        if self.hide_bot:
            posts = posts.filter_by(is_bot=False)

        if not self.show_nsfl:
            posts = posts.filter_by(is_nsfl=False)

        board_ids = g.db.query(
            Subscription.board_id).filter_by(
            user_id=self.id,
            is_active=True).subquery()
        user_ids = g.db.query(
            Follow.user_id).filter_by(
            user_id=self.id).join(
            Follow.target).filter(
                User.is_private == False,
            User.is_nofollow == False).subquery()

        posts = posts.filter(
            or_(
                Submission.board_id.in_(board_ids),
                Submission.author_id.in_(user_ids)
            )
        )

        if self.admin_level < 4:
            # admins can see everything

            m = g.db.query(
                ModRelationship.board_id).filter_by(
                user_id=self.id,
                invite_rescinded=False).subquery()
            c = g.db.query(
                ContributorRelationship.board_id).filter_by(
                user_id=self.id).subquery()
            posts = posts.filter(
                or_(
                    Submission.author_id == self.id,
                    Submission.post_public == True,
                    Submission.board_id.in_(m),
                    Submission.board_id.in_(c)
                )
            )

            blocking = g.db.query(
                UserBlock.target_id).filter_by(
                user_id=self.id).subquery()
            # blocked = g.db.query(
            #     UserBlock.user_id).filter_by(
            #     target_id=self.id).subquery()

            posts = posts.filter(
                Submission.author_id.notin_(blocking) #,
                #Submission.author_id.notin_(blocked)
            ).join(Submission.board).filter(Board.is_banned==False)

        if filter_words:
            posts=posts.join(Submission.submission_aux)
            for word in filter_words:
                #print(word)
                posts=posts.filter(not_(SubmissionAux.title.ilike(f'%{word}%')))

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

        if sort == None:
            sort= self.defaultsorting or "hot"

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

        return [x[0] for x in posts.offset(25 * (page - 1)).limit(26).all()]

    @cache.memoize(300)
    def userpagelisting(self, v=None, page=1, sort="new", t="all"):

        submissions = g.db.query(Submission.id).options(
            lazyload('*')).filter_by(author_id=self.id)

        if not (v and v.over_18):
            submissions = submissions.filter_by(over_18=False)

        if v and v.hide_offensive and v.id!=self.id:
            submissions = submissions.filter_by(is_offensive=False)

        if v and v.hide_bot:
            submissions = submissions.filter_by(is_bot=False)

        if not (v and (v.admin_level >= 3)):
            submissions = submissions.filter_by(deleted_utc=0)

        if not (v and (v.admin_level >= 3 or v.id == self.id)):
            submissions = submissions.filter_by(is_banned=False).join(Submission.board).filter(Board.is_banned==False)

        if v and v.admin_level >= 4:
            pass
        elif v:
            m = g.db.query(
                ModRelationship.board_id).filter_by(
                user_id=v.id,
                invite_rescinded=False).subquery()
            c = g.db.query(
                ContributorRelationship.board_id).filter_by(
                user_id=v.id).subquery()
            submissions = submissions.filter(
                or_(
                    Submission.author_id == v.id,
                    Submission.post_public == True,
                    Submission.board_id.in_(m),
                    Submission.board_id.in_(c)
                )
            )
        else:
            submissions = submissions.filter(Submission.post_public == True)
        if sort == "hot":
            submissions = submissions.order_by(Submission.score_best.desc())
        elif sort == "new":
            submissions = submissions.order_by(Submission.created_utc.desc())
        elif sort == "old":
            submissions = submissions.order_by(Submission.created_utc.asc())
        elif sort == "disputed":
            submissions = submissions.order_by(Submission.score_disputed.desc())
        elif sort == "top":
            submissions = submissions.order_by(Submission.score_top.desc())
        elif sort == "activity":
            submissions = submissions.order_by(Submission.score_activity.desc())

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
        submissions = submissions.filter(Submission.created_utc >= cutoff)

        listing = [x[0] for x in submissions.offset(25 * (page - 1)).limit(26)]
        return listing

    @cache.memoize(300)
    def commentlisting(self, v=None, page=1, sort="new", t="all"):
        comments = self.comments.options(
            lazyload('*')).filter(Comment.parent_submission is not None).join(Comment.post)

        if not (v and v.over_18):
            comments = comments.filter(Submission.over_18 == False)

        if v and v.hide_offensive and v.id != self.id:
            comments = comments.filter(Comment.is_offensive == False)

        if v and v.hide_bot:
            comments = comments.filter(Comment.is_bot == False)

        if v and not v.show_nsfl:
            comments = comments.filter(Submission.is_nsfl == False)

        if (not v) or v.admin_level < 3:
            comments = comments.filter(Comment.deleted_utc == 0)

        if not (v and (v.admin_level >= 3 or v.id == self.id)):
            comments = comments.filter(Comment.is_banned == False)

        if v and v.admin_level >= 4:
            pass
        elif v:
            m = g.db.query(ModRelationship).filter_by(user_id=v.id, invite_rescinded=False).subquery()
            c = v.contributes.subquery()

            comments = comments.join(m,
                                     m.c.board_id == Submission.board_id,
                                     isouter=True
                                     ).join(c,
                                            c.c.board_id == Submission.board_id,
                                            isouter=True
                                            ).join(Board, Board.id == Submission.board_id)
            comments = comments.filter(or_(Comment.author_id == v.id,
                                           Submission.post_public == True,
                                           Board.is_private == False,
                                           m.c.board_id != None,
                                           c.c.board_id != None),
                                      Board.is_banned==False
                                      )
        else:
            comments = comments.join(Board, Board.id == Submission.board_id).filter(
                or_(Submission.post_public == True, Board.is_private == False), Board.is_banned==False)

        comments = comments.options(contains_eager(Comment.post))


        if sort == "hot":
            comments = comments.order_by(Comment.score_hot.desc())
        elif sort == "new":
            comments = comments.order_by(Comment.created_utc.desc())
        elif sort == "old":
            comments = comments.order_by(Comment.created_utc.asc())
        elif sort == "disputed":
            comments = comments.order_by(Comment.score_disputed.desc())
        elif sort == "top":
            comments = comments.order_by(Comment.score_top.desc())

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
        comments = comments.filter(Comment.created_utc >= cutoff)

        comments = comments.offset(25 * (page - 1)).limit(26)

        listing = [c.id for c in comments]
        return listing

    @property
    @lazy
    def mods_anything(self):

        return bool([i for i in self.moderates if i.accepted])


    @property
    @lazy
    def subscribed_to_anything(self):
        return bool([i for i in self.subscriptions if i.is_active])

    @property
    def boards_modded(self):

        z = [x.board for x in self.moderates if x and x.board and x.accepted and not x.board.is_banned]
        z = sorted(z, key=lambda x: x.name)

        return z

    @property
    @cache.memoize(timeout=3600)  # 1hr cache time for user rep
    def karma(self):
        return 503 if self.id==1 else int(self.energy) - self.post_count

    @property
    @cache.memoize(timeout=3600)
    def comment_karma(self):
        return 0 if self.id==1 else int(self.comment_energy) - self.comments.filter(
            Comment.parent_submission is not None).filter_by(is_banned=False).count()

    @property
    @cache.memoize(timeout=3600)
    def true_score(self):

        self.stored_karma=max((self.karma + self.comment_karma), -5)

        g.db.add(self)
        g.db.commit()
        return self.stored_karma

    @property
    def base36id(self):
        return base36encode(self.id)

    @property
    def fullname(self):
        return f"t1_{self.base36id}"

    @property
    #@cache.memoize(timeout=60)
    @lazy
    def has_report_queue(self):
        board_ids = g.db.query(ModRelationship.board_id).options(lazyload('*')).filter(
                ModRelationship.user_id==self.id,
                ModRelationship.accepted==True,
                or_(
                    ModRelationship.perm_full==True,
                    ModRelationship.perm_content==True
                )
                ).subquery()
        
        posts=g.db.query(Submission).options(lazyload('*')).filter(
            Submission.board_id.in_(
                board_ids
            ), 
            Submission.mod_approved == None, 
            Submission.is_banned == False,
            Submission.deleted_utc==0
            ).join(Report, Report.post_id==Submission.id)
        
        if not self.over_18:
            posts=posts.filter(Submission.over_18==False)
            
        return bool(posts.first())
           

    @property
    def banned_by(self):

        if not self.is_banned:
            return None

        return g.db.query(User).filter_by(id=self.is_banned).first()

    def has_badge(self, badgedef_id):
        return self._badges.filter_by(badge_id=badgedef_id).first()

    def vote_status_on_post(self, post):

        return post.voted

    def vote_status_on_comment(self, comment):

        return comment.voted

    def hash_password(self, password):
        return generate_password_hash(
            password, method='pbkdf2:sha512', salt_length=8)

    def verifyPass(self, password):
        return check_password_hash(self.passhash, password)

    @property
    def feedkey(self):

        return generate_hash(f"{self.username}{self.id}{self.feed_nonce}{self.created_utc}")

    @property
    def formkey(self):

        if "session_id" not in session:
            session["session_id"] = token_hex(16)

        msg = f"{session['session_id']}+{self.id}+{self.login_nonce}"

        return generate_hash(msg)

    def validate_formkey(self, formkey):

        return validate_hash(f"{session['session_id']}+{self.id}+{self.login_nonce}", formkey)

    @property
    def url(self):
        return f"/@{self.username}"

    @property
    def permalink(self):
        return self.url

    @property
    def uid_permalink(self):
        return f"/uid/{self.base36id}"

    @property
    def original_link(self):
        return f"/@{self.original_username}"


    def __repr__(self):
        return f"<User(username={self.username})>"

    def notification_commentlisting(self, page=1, all_=False, replies_only=False, mentions_only=False, system_only=False):


        notifications = self.notifications.options(
            lazyload('*'),
            joinedload(Notification.comment).lazyload('*'),
            joinedload(Notification.comment).joinedload(Comment.comment_aux)
            ).join(
            Notification.comment
            ).filter(
            Comment.is_banned == False,
            Comment.deleted_utc == 0)



        if replies_only:
            cs=g.db.query(Comment.id).filter(Comment.author_id==self.id).subquery()
            ps=g.db.query(Submission.id).filter(Submission.author_id==self.id).subquery()
            notifications=notifications.filter(
                or_(
                    Comment.parent_comment_id.in_(cs),
                    and_(
                        Comment.level==1,
                        Comment.parent_submission.in_(ps)
                        )
                    )
                )

        elif mentions_only:
            cs=g.db.query(Comment.id).filter(Comment.author_id==self.id).subquery()
            ps=g.db.query(Submission.id).filter(Submission.author_id==self.id).subquery()
            notifications=notifications.filter(
                and_(
                    Comment.parent_comment_id.notin_(cs),
                    or_(
                        Comment.level>1,
                        Comment.parent_submission.notin_(ps)
                        )
                    )
                )
        elif system_only:
            notifications=notifications.filter(Comment.author_id==1)

        elif not all_:
            notifications = notifications.filter(Notification.read == False)


        notifications = notifications.options(
            contains_eager(Notification.comment)
        )

        notifications = notifications.order_by(
            Notification.id.desc()).offset(25 * (page - 1)).limit(26)

        output = []
        for x in notifications[0:25]:
            x.read = True
            g.db.add(x)
            output.append(x.comment_id)

        g.db.commit()

        return output

    def notification_postlisting(self, all_=False, page=1):

        notifications=self.notifications.join(
            Notification.post
            ).filter(
            Submission.is_banned==False, 
            Submission.deleted_utc==0
            )

        if not all_:
            notifications=notifications.filter(Notification.read==False)

        notifications=notifications.options(
                contains_eager(Notification.post)
            ).order_by(
                Notification.id.desc()
            ).offset(25*(page-1)).limit(26)

        output=[]
        for x in notifications[0:25]:
            x.read=True
            g.db.add(x)
            output.append(x.submission_id)

        g.db.commit()
        return output

    @property
    @lazy
    def mentions_count(self):
        cs=g.db.query(Comment.id).filter(Comment.author_id==self.id).subquery()
        ps=g.db.query(Submission.id).filter(Submission.author_id==self.id).subquery()
        return self.notifications.options(
            lazyload('*')
            ).join(
            Notification.comment
            ).filter(
            Notification.read==False,
            Comment.is_banned == False,
            Comment.deleted_utc == 0
            ).filter(
                and_(
                    Comment.parent_comment_id.notin_(cs),
                    or_(
                        Comment.level>1,
                        Comment.parent_submission.notin_(ps)
                    )
                )
            ).count()


    @property
    @lazy
    def replies_count(self):
        cs=g.db.query(Comment.id).filter(Comment.author_id==self.id).subquery()
        ps=g.db.query(Submission.id).filter(Submission.author_id==self.id).subquery()
        return self.notifications.options(
            lazyload('*')
            ).join(
            Notification.comment
            ).filter(
            Comment.is_banned == False,
            Comment.deleted_utc == 0
            ).filter(
            Notification.read==False,
            or_(
                Comment.parent_comment_id.in_(cs),
                and_(
                    Comment.level==1,
                    Comment.parent_submission.in_(ps)
                    )
                )
            ).count()

    @property
    @lazy
    def post_notifications_count(self):
        return self.notifications.filter(
            Notification.read==False
            ).join(
            Submission,
            Submission.id==Notification.submission_id
            ).filter(
            Submission.is_banned==False,
            Submission.deleted_utc==0,
            ).count()

    @property
    @lazy
    def system_notif_count(self):
        return self.notifications.options(
            lazyload('*')
            ).join(
            Notification.comment
            ).filter(
            Notification.read==False,
            Comment.author_id==1
            ).count()

    @property
    @lazy
    def notifications_count(self):
        return self.notifications.options(
            lazyload('*')
            ).filter(
                Notification.read==False
            ).join(Notification.comment, isouter=True
            ).join(Notification.post, isouter=True
            ).filter(
                or_(
                    and_(
                        Comment.is_banned==False,
                        Comment.deleted_utc==0
                    ),
                    and_(
                        Submission.is_banned==False,
                        Submission.deleted_utc==0
                    )
                )
            ).count()




    @property
    def post_count(self):

        return self.submissions.filter_by(is_banned=False).count()

    @property
    def comment_count(self):

        return self.comments.filter(Comment.parent_submission!=None).filter_by(
            is_banned=False, deleted_utc=0).count()

    @property
    @lazy
    def alts(self):

        subq = g.db.query(Alt).filter(
            or_(
                Alt.user1==self.id,
                Alt.user2==self.id
                )
            ).subquery()

        data = g.db.query(
            User,
            aliased(Alt, alias=subq)
            ).join(
            subq,
            or_(
                subq.c.user1==User.id,
                subq.c.user2==User.id
                )
            ).filter(
            User.id != self.id
            ).order_by(User.username.asc()).all()

        data=[x for x in data]
        output=[]
        for x in data:
            user=x[0]
            user._is_manual=x[1].is_manual
            output.append(user)

        return output
    
    def alts_subquery(self):
        return g.db.query(User.id).filter(
            or_(
                User.id.in_(
                    g.db.query(Alt.user1).filter(
                        Alt.user2==self.id
                    ).subquery()
                ),
                User.id.in_(
                    g.db.query(Alt.user2).filter(
                        Alt.user1==self.id
                    ).subquery()
                ).subquery()
            )
        ).subquery()
        

    def alts_threaded(self, db):

        subq = db.query(Alt).filter(
            or_(
                Alt.user1==self.id,
                Alt.user2==self.id
                )
            ).subquery()

        data = db.query(
            User,
            aliased(Alt, alias=subq)
            ).join(
            subq,
            or_(
                subq.c.user1==User.id,
                subq.c.user2==User.id
                )
            ).filter(
            User.id != self.id
            ).order_by(User.username.asc()).all()

        data=[x for x in data]
        output=[]
        for x in data:
            user=x[0]
            user._is_manual=x[1].is_manual
            output.append(user)

        return output

    def has_follower(self, user):

        return g.db.query(Follow).filter_by(
            target_id=self.id, user_id=user.id).first()

    def set_profile(self, file):

        self.del_profile()
        self.profile_nonce += 1

        aws.upload_file(name=f"uid/{self.base36id}/profile-{self.profile_nonce}.png",
                        file=file,
                        resize=(100, 100)
                        )
        self.has_profile = True
        self.profile_upload_ip=request.remote_addr
        self.profile_set_utc=int(time.time())
        self.profile_upload_region=request.headers.get("cf-ipcountry")
        g.db.add(self)

    def set_banner(self, file):

        self.del_banner()
        self.banner_nonce += 1

        aws.upload_file(name=f"uid/{self.base36id}/banner-{self.banner_nonce}.png",
                        file=file)

        self.has_banner = True
        self.banner_upload_ip=request.remote_addr
        self.banner_set_utc=int(time.time())
        self.banner_upload_region=request.headers.get("cf-ipcountry")

        g.db.add(self)

    def del_profile(self):

        if self.profile_set_utc>1616443200:
            aws.delete_file(name=f"uid/{self.base36id}/profile-{self.profile_nonce}.png")
        else:
            aws.delete_file(name=f"users/{self.username}/profile-{self.profile_nonce}.png")
        self.has_profile = False
        try:
            g.db.add(self)
        except:
            pass

    def del_banner(self):

        if self.banner_set_utc>1616443200:
            aws.delete_file(name=f"uid/{self.base36id}/banner-{self.banner_nonce}.png")
        else:
            aws.delete_file(name=f"users/{self.username}/banner-{self.banner_nonce}.png")
        self.has_banner = False
        try:
            g.db.add(self)
        except:
            pass

    @property
    def banner_url(self):

        if self.has_banner:
            if self.banner_set_utc>1616443200:
                return f"https://i.ruqqus.com/uid/{self.base36id}/banner-{self.banner_nonce}.png"
            else:
                return f"https://i.ruqqus.com/users/{self.username}/banner-{self.banner_nonce}.png"
        else:
            return "/assets/images/profiles/default_bg.png"

    @property
    def profile_url(self):

        if self.has_profile and not self.is_deleted:
            if self.profile_set_utc>1616443200:
                return f"https://{app.config['S3_BUCKET']}/uid/{self.base36id}/profile-{self.profile_nonce}.png"
            else:
                return f"https://{app.config['S3_BUCKET']}/users/{self.username}/profile-{self.profile_nonce}.png"
        else:
            return f"http{'s' if app.config['FORCE_HTTPS'] else ''}://{app.config['SERVER_NAME']}/assets/images/profiles/default-profile-pic.png"

    @property
    def available_titles(self):

        locs = {"v": self,
                "Board": Board,
                "Submission": Submission
                }

        titles = [
            i for i in g.db.query(Title).order_by(
                text("id asc")).all() if eval(
                i.qualification_expr, {}, locs)]
        return titles

    @property
    def can_make_guild(self):

        if app.config["GUILD_CREATION_REQ"]==-1:
            return self.admin_level >=3

        elif app.config["GUILD_CREATION_REQ"]]==0:
            return self.can_join_gms
            
        return (self.has_premium or self.admin_level>=3 or self.true_score >= 250 or (self.created_utc <= 1592974538 and self.true_score >= 50)) and self.can_join_gms

    @property
    def can_join_gms(self):

        if app.config["MAX_GUILD_COUNT"]==0:
            return True
        
        return len([x for x in self.boards_modded if x.is_siegable]) < app.config["MAX_GUILD_COUNT"]

    @property
    def can_siege(self):

        if self.is_suspended:
            return False

        now = int(time.time())

        return now - max(self.last_siege_utc,
                         self.created_utc) > 60 * 60 * 24 * 7

    @property
    def can_submit_image(self):
        # Has premium
        # Has 1000 Rep, or 500 for older accounts
        # if connecting through Tor, must have verified email
        return (self.has_premium or self.true_score >= 500) and (self.is_activated or request.headers.get("cf-ipcountry")!="T1")

    @property
    def can_upload_avatar(self):
        return (self.has_premium or self.true_score >= 300 or self.created_utc <= 1592974538) and (self.is_activated or request.headers.get("cf-ipcountry")!="T1")

    @property
    def can_upload_banner(self):
        return (self.has_premium or self.true_score >= 500 or self.created_utc <= 1592974538) and (self.is_activated or request.headers.get("cf-ipcountry")!="T1")

    @property
    def json_raw(self):
        data= {'username': self.username,
                'permalink': self.permalink,
                'is_banned': self.is_suspended,
                'is_premium': self.has_premium_no_renew,
                'created_utc': self.created_utc,
                'id': self.base36id,
                'is_private': self.is_private,
                'profile_url': self.profile_url,
                'banner_url': self.banner_url,
                'title': self.title.json if self.title else None,
                'bio': self.bio,
                'bio_html': self.bio_html
                }

        if self.real_id:
            data['real_id']=self.real_id

        return data
    

    @property
    def json_core(self):

        now=int(time.time())
        if self.is_suspended:
            return {'username': self.username,
                    'permalink': self.permalink,
                    'is_banned': True,
                    'is_permanent_ban':not bool(self.unban_utc),
                    'ban_reason': self.ban_reason,
                    'id': self.base36id
                    }

        elif self.is_deleted:
            return {'username': self.username,
                    'permalink': self.permalink,
                    'is_deleted': True,
                    'id': self.base36id
                    }
        return self.json_raw
        


    @property
    def json(self):
        data= self.json_core

        if self.is_suspended or self.is_deleted:
            return data

        data["badges"]=[x.json_core for x in self.badges]
        data['post_rep']= int(self.karma)
        data['comment_rep']= int(self.comment_karma)
        data['post_count']=self.post_count
        data['comment_count']=self.comment_count

        return data
    

    @property
    def total_karma(self):

        return 503 if self.id==1 else max(self.karma + self.comment_karma, -5)

    @property
    def can_use_darkmode(self):
        return True
        # return self.referral_count or self.has_earned_darkmode or
        # self.has_badge(16) or self.has_badge(17)

    @property
    def is_valid(self):
        if self.is_banned and self.unban_utc==0:
            return False

        elif self.is_deleted:
            return False

        else:
            return True
    

    def ban(self, admin=None, reason=None,  days=0):
        
        admin=admin if admin else g.db.query(User).filter_by(id=1).first()

        self.is_banned = admin.id if admin else 1
        if reason:
            self.ban_reason = reason

        g.db.add(self)
        g.db.flush()

        if days > 0:
            ban_time = int(time.time()) + (days * 86400)
            self.unban_utc = ban_time

        else:
            # Takes care of all functions needed for account termination
            self.unban_utc = 0
            if self.has_banner:
                self.del_banner()
            if self.has_profile:
                self.del_profile()

            add_role(self, "banned")
            delete_role(self, "member")

            #unprivate guilds if no mods remaining
            for b in self.boards_modded:
                if b.mods_count == 0:
                    b.is_private = False
                    b.restricted_posting = False
                    #b.all_opt_out = False
                    g.db.add(b)

        try:
            g.db.add(self)
        except:
            pass
        
        discord_ban_action = f"{days} Day Ban" if days else "Perm Ban"
        discord_log_event(discord_ban_action, self, admin, reason=reason)

    def unban(self):

        # Takes care of all functions needed for account reinstatement.

        self.is_banned = 0
        self.unban_utc = 0

        delete_role(self, "banned")

        g.db.add(self)
        
        discord_log_event("Unban", self, g.v, reason=self.ban_reason)


    @property
    def is_suspended(self):
        return (self.is_banned and (self.unban_utc ==
                                    0 or self.unban_utc > time.time()))

    @property
    def is_blocking(self):
        return self.__dict__.get('_is_blocking', 0)

    @property
    def is_blocked(self):
        return self.__dict__.get('_is_blocked', 0)

    def refresh_selfset_badges(self):

        # check self-setting badges
        badge_types = g.db.query(BadgeDef).filter(
            BadgeDef.qualification_expr.isnot(None)).all()
        for badge in badge_types:
            if eval(badge.qualification_expr, {}, {'v': self}):
                if not self.has_badge(badge.id):
                    new_badge = Badge(user_id=self.id,
                                      badge_id=badge.id,
                                      created_utc=int(time.time())
                                      )
                    g.db.add(new_badge)

            else:
                bad_badge = self.has_badge(badge.id)
                if bad_badge:
                    g.db.delete(bad_badge)

        try:
            g.db.add(self)
        except:
            pass

    @property
    def applications(self):
        return [x for x in self._applications.order_by(
            OauthApp.id.asc()).all()]


    def saved_idlist(self, page=1):

        posts = g.db.query(Submission.id).options(lazyload('*')).filter_by(is_banned=False,
                                                                           deleted_utc=0
                                                                           )

        if not self.over_18:
            posts = posts.filter_by(over_18=False)


        saved=g.db.query(SaveRelationship.submission_id).filter(SaveRelationship.user_id==self.id).subquery()
        posts=posts.filter(Submission.id.in_(saved))



        if self.admin_level < 4:
            # admins can see everything

            m = g.db.query(
                ModRelationship.board_id).filter_by(
                user_id=self.id,
                invite_rescinded=False).subquery()
            c = g.db.query(
                ContributorRelationship.board_id).filter_by(
                user_id=self.id).subquery()
            posts = posts.filter(
                or_(
                    Submission.author_id == self.id,
                    Submission.post_public == True,
                    Submission.board_id.in_(m),
                    Submission.board_id.in_(c)
                )
            )

            blocking = g.db.query(
                UserBlock.target_id).filter_by(
                user_id=self.id).subquery()
            blocked = g.db.query(
                UserBlock.user_id).filter_by(
                target_id=self.id).subquery()

            posts = posts.filter(
                Submission.author_id.notin_(blocking),
                Submission.author_id.notin_(blocked)
            )

        posts=posts.order_by(Submission.created_utc.desc())
        
        return [x[0] for x in posts.offset(25 * (page - 1)).limit(26).all()]



    def guild_rep(self, guild, recent=0):

        

        posts=g.db.query(Submission.score_top).filter_by(
            is_banned=False,
            original_board_id=guild.id,
            is_bot=False)

        if recent:
            cutoff=int(time.time())-60*60*24*recent
            posts=posts.filter(Submission.created_utc>cutoff)

        posts=posts.all()

        post_rep= sum([x[0] for x in posts]) - len(posts)


        comments=g.db.query(Comment.score_top).filter_by(
            is_banned=False,
            original_board_id=guild.id,
            is_bot=False)

        if recent:
            cutoff=int(time.time())-60*60*24*recent
            comments=comments.filter(Comment.created_utc>cutoff)

        comments=comments.all()

        comment_rep=sum([x[0] for x in comments]) - len(comments)

        return int(post_rep + comment_rep)

    @property
    def has_premium(self):
        
        now=int(time.time())

        if self.negative_balance_cents:
            return False

        elif self.premium_expires_utc > now:
            return True

        elif self.coin_balance >=1:
            self.coin_balance -=1
            self.premium_expires_utc = now + 60*60*24*7

            add_role(self, "premium")

            g.db.add(self)

            return True

        else:

            if self.premium_expires_utc:
                delete_role(self, "premium")
                self.premium_expires_utc=0
                g.db.add(self)

            return False

    @property
    def has_premium_no_renew(self):
        
        now=int(time.time())

        if self.negative_balance_cents:
            return False
        elif self.premium_expires_utc > now:
            return True
        elif self.coin_balance>=1:
            return True
        else:
            return False
    
    
    @property
    def renew_premium_time(self):
        return time.strftime("%d %b %Y at %H:%M:%S",
                             time.gmtime(self.premium_expires_utc))
    

    @property
    def filter_words(self):
        l= [i.lstrip().rstrip() for i in self.custom_filter_list.split('\n')] if self.custom_filter_list else []
        l=[i for i in l if i]
        return l
                             
    @property
    def boards_modded_ids(self):
        return [x.id for x in self.boards_modded]

    @property
    def txn_history(self):
        
        return self._transactions.filter(PayPalTxn.status!=1).order_by(PayPalTxn.created_utc.desc()).all()
    

    @property
    def json_admin(self):
        data=self.json_raw

        data['creation_ip']=self.creation_ip
        data['creation_region']=self.creation_region
        data['email']=self.email
        data['email_verified']=self.is_activated

        return data

    @property
    def can_upload_comment_image(self):
        return self.has_premium and (request.headers.get("cf-ipcountry")!="T1" or self.is_activated)

    @property
    def can_change_name(self):
        return self.name_changed_utc < int(time.time())-60*60*24*7 and self.coin_balance>=20

    @property
    @cache.memoize(60*60*24)
    def badges(self):
        self.refresh_selfset_badges()
        g.db.commit()
        return self._badges.all()

    @property
    def is_following(self):
        return self.__dict__.get('_is_following',None)
    
    @property
    def unban_string(self):
        if self.unban_utc==0:
            return "Permanent Ban"

        wait = self.unban_utc - int(time.time())

        if wait<60:
            text="just a moment"
        else:
            days = wait // (60*60*24)
            wait -= days*60*60*24

            hours=wait // (60*60)
            wait -= hours*60*60

            minutes=wait//60

            text=f"{days}d {hours:02d}h {minutes:02d}m"

        return f"Unban in {text}"
    
