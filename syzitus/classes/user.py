from werkzeug.security import generate_password_hash, check_password_hash
from flask import g, session, abort, request
from time import strftime, gmtime
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, ForeignKey, FetchedValue, Index, and_, or_, select, func
from sqlalchemy.orm import relationship, deferred, joinedload, lazyload, contains_eager, aliased, Load, load_only
from os import environ
from secrets import token_hex
from pyotp import TOTP
from mistletoe import markdown
import threading

from syzitus.helpers.base36 import base36encode
from syzitus.helpers.security import generate_hash, validate_hash
from syzitus.helpers.lazy import lazy
from syzitus.helpers.user_imports import send_notif
import syzitus.helpers.aws as aws
from syzitus.helpers.discord import add_role, delete_role, discord_log_event
from .alts import Alt
from .titles import TITLES
from .submission import Submission, SubmissionAux #, SaveRelationship
from .comment import Comment, CommentAux, Notification
from .boards import Board
from .board_relationships import ModRelationship, BanRelationship, ContributorRelationship, BoardBlock
from .mix_ins import *
from .subscriptions import Subscription, Follow
from .userblock import UserBlock
from .badges import *
from .clients import *
from .paypal import PayPalTxn
from .flags import Report
from .votes import Vote

from syzitus.__main__ import Base, cache, app, g, db_session, debug

class User(Base, standard_mixin, age_mixin):

    __tablename__ = "users"

    #basic stuff
    id = Column(Integer, primary_key=True)
    username = Column(String, default=None)
    email = Column(String, default=None)
    passhash = deferred(Column(String, default=None))
    created_utc = Column(Integer, default=0)
    admin_level = Column(Integer, default=0)
    is_activated = Column(Boolean, default=False)
    over_18 = Column(Boolean, default=False)
    creation_ip = Column(String, default=None)
    bio = Column(String, default="")
    bio_html = Column(String, default="")
    real_id = Column(String, default=None)
    referred_by = Column(Integer, default=None)
    is_deleted = Column(Boolean, default=False)
    delete_reason = Column(String(500), default='')
    creation_region=Column(String(2), default=None)

    #ban & admin actions
    is_banned = Column(Integer, default=0)
    unban_utc = Column(Integer, default=0)
    ban_reason = Column(String, default="")
    ban_evade=Column(Integer, default=0)

    #content preferences
    defaultsorting = Column(String, default="hot")
    defaulttime = Column(String, default="all")
    hide_offensive = Column(Boolean, default=True)
    hide_bot = Column(Boolean, default=False)
    show_nsfl = Column(Boolean, default=False)
    custom_filter_list=Column(String(1000), default="")
    filter_nsfw = Column(Boolean, default=False)
    per_page_preference=Column(Integer, default=25)

    #security
    login_nonce = Column(Integer, default=0)
    mfa_secret = deferred(Column(String(64), default=None))
    is_private = Column(Boolean, default=False)
    is_nofollow = Column(Boolean, default=False)

    #profile
    title_id = Column(Integer)
    has_profile = Column(Boolean, default=False)
    has_banner = Column(Boolean, default=False)
    reserved = Column(String(256), default=None)
    is_nsfw = Column(Boolean, default=False)
    profile_nonce = Column(Integer, default=0)
    banner_nonce = Column(Integer, default=0)
    profile_upload_ip=deferred(Column(String(255), default=None))
    banner_upload_ip=deferred(Column(String(255), default=None))
    profile_upload_region=deferred(Column(String(2)))
    banner_upload_region=deferred(Column(String(2)))
    original_username=deferred(Column(String(255)))
    name_changed_utc=deferred(Column(Integer, default=0))

    #siege
    last_siege_utc = Column(Integer, default=0)

    #stored values from db-side functions
    stored_karma = Column(Integer, default=0)
    stored_subscriber_count=Column(Integer, default=0)

    #premium
    coin_balance=Column(Integer, default=0)
    premium_expires_utc=Column(Integer, default=0)
    negative_balance_cents=Column(Integer, default=0)

    #discord
    discord_id=Column(String(64), default=None)


    
    # color=Column(String(6), default="805ad5")
    # secondary_color=Column(String(6), default="ffff00")
    # signature=Column(String(280), default='')
    # signature_html=Column(String(512), default="")


    ## === RELATIONSHIPS ===

    #Content
    submissions = relationship(
        "Submission",
        lazy="dynamic",
        primaryjoin="Submission.author_id==User.id")
    comments = relationship(
        "Comment",
        lazy="dynamic",
        primaryjoin="Comment.author_id==User.id")
    notifications = relationship("Notification")

    #profile
    _badges = relationship("Badge", lazy="dynamic", backref="user")

    #Guild relationships
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

    #Inter-user relationships
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

    #apps
    _applications = relationship("OauthApp", lazy="dynamic")
    authorizations = relationship("ClientAuth", lazy="dynamic")

    # properties defined as SQL server-side functions
    energy =            deferred(Column(Integer, server_default=FetchedValue()))
    comment_energy =    deferred(Column(Integer, server_default=FetchedValue()))
    referral_count =    deferred(Column(Integer, server_default=FetchedValue()))
    follower_count =    deferred(Column(Integer, server_default=FetchedValue()))

    __table_args__=(
        Index(
            "users_username_trgm_idx", "username",
            postgresql_using="gin",
            postgresql_ops={
                'username':'gin_trgm_ops'
                }
            ),
        Index(
            "users_original_username_trgm_idx", "original_username",
            postgresql_using="gin",
            postgresql_ops={
                'original_username':'gin_trgm_ops'
                }
            ),
        Index(
            "users_email_trgm_idx", "email",
            postgresql_using="gin",
            postgresql_ops={
                'email':'gin_trgm_ops'
                }
            ),
        Index(
            "users_created_utc_idx", "created_utc",
            postgresql_using="btree",
            postgresql_ops={
                'created_utc':'DESC'
                }
            )
        )

    def __init__(self, **kwargs):

        if "password" in kwargs:

            kwargs["passhash"] = self.hash_password(kwargs["password"])
            kwargs.pop("password")

        if "created_utc" not in kwargs:
            kwargs["created_utc"] = g.timestamp

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

        x = TOTP(self.mfa_secret)
        return x.verify(token, valid_window=1)

    @property
    def mfa_removal_code(self):

        hashstr = f"{self.mfa_secret}+{self.id}+{self.original_username}"

        hashstr= generate_hash(hashstr)

        removal_code = base36encode(int(hashstr,16) % int('z'*25, 36))

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
        return g.timestamp - self.created_utc

    @property
    def title(self):
        return TITLES.get(self.title_id)
    
    @cache.memoize(300)
    def recommended_list(self, page=1, per_page=25, filter_words=[], **kwargs):

        # get N most recent upvotes
        # get those posts
        # get a list of all users who also upvoted those things
        # get their upvotes
        # get those posts ordered by number of upvotes among those users
        # eliminate content based on personal filters

        #hard check to prevent this feature from being used as a "vote stalker"
        #Recommendations must be based on 4 other co-voting users minimum
        user_count=g.db.query(Vote.user_id).filter(
            Vote.vote_type==1,
            Vote.user_id.in_(
                select(Vote.user_id).filter(
                    Vote.vote_type==1,
                    Vote.submission_id.in_(
                        select(Vote.submission_id).filter(
                            Vote.vote_type==1, 
                            Vote.user_id==self.id
                            ).order_by(Vote.created_utc.desc()).limit(50)
                        )
                    )
                )
            ).distinct().count()

        if user_count < 4:
            return []


        #select post IDs, with global restrictions - no deleted, removed, or front-page-sticky content
        posts=g.db.query(
            Submission.id,
            Submission.author_id,
            Submission.board_id,
            Submission.created_utc
            ).options(
            load_only(
                Submission.id,
                Submission.author_id,
                Submission.board_id,
                Submission.created_utc
                ), lazyload('*')
            ).filter_by(
            is_banned=False,
            deleted_utc=0,
            stickied=False
            )


        #filter out anything that's yours,
        #or that you've already voted on,
        #or that's too old
        
        posts=posts.filter(
            Submission.author_id!=self.id,
            Submission.created_utc > g.timestamp-2592000,
            Submission.id.notin_(
                select(Vote.submission_id).filter(Vote.user_id==self.id, Vote.vote_type!=0)
                )
            )

        #no nsfw content if personal settings dicate
        if self.filter_nsfw or not self.over_18:
            posts = posts.filter_by(over_18=False)

        #no racial slur content if personal settings dictate
        if self.hide_offensive:
            posts = posts.filter_by(is_offensive=False)

        #no bot content if personal settings dictate
        if self.hide_bot:
            posts = posts.filter_by(is_bot=False)

        #no disturbing/gruesome content if personal settings dictate
        if not self.show_nsfl:
            posts = posts.filter_by(is_nsfl=False)

        #no content from guilds on user's personal block list
        posts = posts.filter(
            Submission.board_id.notin_(
                select(BoardBlock.board_id).filter_by(
                    user_id=g.user.id
                    )
                )
            )

        #subquery - guilds where user is mod or has mod invite
        m = select(
            ModRelationship.board_id).filter_by(
            user_id=self.id,
            invite_rescinded=False)

        #subquery - guilds where user is added as contributor
        c = select(
            ContributorRelationship.board_id).filter_by(
            user_id=self.id)

        #no content from private guilds, unless the post was made while guild was public,
        #or the user is mod, or has mod invite, or is contributor, or is the post author
        posts = posts.filter(
            or_(
                # Submission.author_id == self.id,
                Submission.post_public == True,
                Submission.board_id.in_(m),
                Submission.board_id.in_(c)
            )
        )

        #subquery - other users who you are blocking
        blocking = select(
            UserBlock.target_id).filter_by(
            user_id=self.id)

        #subquery - other users you are blocked by
        blocked = select(
            UserBlock.user_id).filter_by(
            target_id=self.id)

        #no content where you're blocking the user or they're blocking you
        posts = posts.filter(
            Submission.author_id.notin_(blocking),
            Submission.author_id.notin_(blocked)
        )

        #guild-based restrictions on recommended content
        #no content from banned guilds, and no content from opt-out guilds unless the user is sub'd
        board_ids=select(Board.id).filter(
            Board.is_banned==False,
            or_(
                Board.all_opt_out == False,
                Submission.board_id.in_(
                    select(
                        Subscription.board_id).filter_by(
                        user_id=g.user.id,
                        is_active=True)
                    )
                )
            )
        posts=posts.filter(Submission.board_id.in_(board_ids))

        #personal filter word restrictions
        #no content whose title contains a personal filter word
        if filter_words:
            posts=posts.join(Submission.submission_aux)
            for word in filter_words:
                posts=posts.filter(not_(SubmissionAux.title.ilike(f'%{word}%')))


        ### Algorithm core part 1

        #read this code inside -> outside
        #select your 50 most recent upvoted posts,
        #then select the users who also upvoted those posts ("co-voting users")
        #then select the other stuff they upvoted
        #filter out any posts not in that list

        posts=posts.filter(
            Submission.id.in_(
                select(Vote.submission_id).filter(
                    Vote.vote_type==1,
                    Vote.user_id.in_(
                        select(Vote.user_id).filter(
                            Vote.vote_type==1,
                            Vote.submission_id.in_(
                                select(Vote.submission_id).filter(
                                    Vote.vote_type==1, 
                                    Vote.user_id==self.id
                                    ).order_by(Vote.created_utc.desc()).limit(50)
                                )
                            )
                        )
                    )
                )
            )

        #at this point we have an unfinished query representing the pool of all possible For You posts
        #The next steps involve some heavy lifting on the part of the database
        #To save computation resources in the next steps, sort by Top and cut off everything below the first 500

        #this is now an unsent db query that can be used in subsequent steps
        posts_subq=posts.order_by(Submission.score_top.desc()).limit(500).subquery()


        #Votes subquery - the only votes we care about are those from users who co-voted the user's last 100 upvotes
        #this is similar to the algoritm core part 1, with an added filter of only paying attention to votes on the final pool of 500
        votes=select(Vote).options(lazyload('*')).filter(
            Vote.vote_type==1,
            Vote.user_id.in_(
                select(Vote.user_id).filter(
                    Vote.vote_type==1,
                    Vote.submission_id.in_(
                        select(Vote.submission_id).filter(
                            Vote.vote_type==1, 
                            Vote.user_id==self.id
                            ).order_by(Vote.created_utc.desc()).limit(50)
                        ),
                    )
                ),
            Vote.submission_id.in_(select(posts_subq.c.id))
            )


        #This assigns posts their initial score - the number of upvotes it has from co-voting users
        starting_rank=func.count(votes.c.submission_id).label('rank')
        vote_scores=g.db.query(
            votes.c.submission_id.label('id'),
            starting_rank
            ).group_by(votes.c.submission_id).order_by(starting_rank.desc()).subquery()


        #create final scoring matrix, starting with post id, author_id, and board_id,
        #join it with the vote scores above
        #and add in penalty columns based on age and prior entries of the same author/board (promoting variety)

        age_penalty = ((g.timestamp - posts_subq.c.created_utc)//(60*60*24*2)).label('age_penalty')
        scores=g.db.query(
            posts_subq.c.id,
            posts_subq.c.author_id,
            posts_subq.c.board_id,
            posts_subq.c.created_utc,
            vote_scores.c.rank,
            age_penalty,
            func.row_number().over(
                partition_by=posts_subq.c.author_id,
                order_by=(vote_scores.c.rank - age_penalty).desc()
                ).label('user_penalty'),
            func.row_number().over(
                partition_by=posts_subq.c.board_id,
                order_by=(vote_scores.c.rank - age_penalty).desc()
                ).label('board_penalty')
            ).join(
            vote_scores, posts_subq.c.id==vote_scores.c.id).subquery()

        # everything so far has been for the purpose of putting all candidate entries 
        # into an ephemeral score table, which has columns:
        # id | author_id | board_id | created_utc | vote_rank | age_penalty | user_penalty | board_penalty

        # Last step, get *just* the ids, sorted by (vote_rank - age_penalty*a - user_penalty-b - board_penalty*c)

        post_ids=g.db.query(
            scores.c.id
            ).order_by(
            # Submission.score_best.desc()
            # scores.c.rank.desc()
            (scores.c.rank - scores.c.user_penalty - scores.c.board_penalty*2 - scores.c.age_penalty).desc(),
            scores.c.created_utc.desc()
            )
    
        #and paginate
        post_ids=post_ids.offset(per_page * (page - 1)).limit(per_page+1).all()

        return [x.id for x in post_ids]


    @cache.memoize()
    def idlist(self, sort=None, page=1, t=None, filter_words=[], per_page=25, **kwargs):

        posts = g.db.query(Submission).options(load_only(Submission.id), lazyload('*')).filter_by(
            is_banned=False,
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

        board_ids = select(
            Subscription.board_id).filter_by(
            user_id=self.id,
            is_active=True)
        user_ids = select(
            Follow.user_id).filter_by(
            user_id=self.id).join(
            Follow.target).filter(
                User.is_private == False,
            User.is_nofollow == False)

        posts = posts.filter(
            or_(
                Submission.board_id.in_(board_ids),
                Submission.author_id.in_(user_ids)
            )
        )

        if self.admin_level < 4:
            # admins can see everything

            m = select(
                ModRelationship.board_id).filter_by(
                user_id=self.id,
                invite_rescinded=False)
            c = select(
                ContributorRelationship.board_id).filter_by(
                user_id=self.id)
            posts = posts.filter(
                or_(
                    Submission.author_id == self.id,
                    Submission.post_public == True,
                    Submission.board_id.in_(m),
                    Submission.board_id.in_(c)
                )
            )

            blocking = select(
                UserBlock.target_id).filter_by(
                user_id=self.id)
            blocked = select(
                UserBlock.user_id).filter_by(
                target_id=self.id)

            posts = posts.filter(
                Submission.author_id.notin_(blocking) #,
                #Submission.author_id.notin_(blocked)
            ).join(Submission.board).filter(Board.is_banned==False)

        if filter_words:
            posts=posts.join(Submission.submission_aux)
            for word in filter_words:
                posts=posts.filter(not_(SubmissionAux.title.ilike(f'%{word}%')))

        if t:
            now = g.timestamp
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

        return [x.id for x in posts.offset(per_page * (page - 1)).limit(per_page+1).all()]

    @cache.memoize()
    def userpagelisting(self, page=1, sort="new", t="all", per_page=25):

        submissions = g.db.query(Submission).options(
            load_only(Submission.id)).filter_by(author_id=self.id)

        if not (g.user and g.user.over_18):
            submissions = submissions.filter_by(over_18=False)

        if g.user and g.user.hide_offensive and g.user.id!=self.id:
            submissions = submissions.filter_by(is_offensive=False)

        if not (g.user and g.user.admin_level >= 3):
            submissions = submissions.filter_by(deleted_utc=0, is_banned=False).join(Submission.board).filter(Board.is_banned==False)

        if g.user and g.user.admin_level >= 4:
            pass
        elif g.user:
            m = select(
                ModRelationship.board_id).filter_by(
                user_id=g.user.id,
                invite_rescinded=False)
            c = select(
                ContributorRelationship.board_id).filter_by(
                user_id=g.user.id)
            submissions = submissions.filter(
                or_(
                    Submission.author_id == g.user.id,
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

        now = g.timestamp
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

        listing = [x.id for x in submissions.offset(per_page * (page - 1)).limit(per_page+1)]
        return listing

    @cache.memoize()
    def commentlisting(self, page=1, sort="new", t="all", per_page=25):
        comments = self.comments.options(
            load_only(Comment.id)).filter(Comment.parent_submission is not None).join(Comment.post)

        if not (g.user and g.user.over_18):
            comments = comments.filter(Submission.over_18 == False)

        if g.user and g.user.hide_offensive and g.user.id != self.id:
            comments = comments.filter(Comment.is_offensive == False)

        if g.user and not g.user.show_nsfl:
            comments = comments.filter(Submission.is_nsfl == False)

        if not (g.user and g.user.admin_level >= 3):
            comments = comments.filter(
                Comment.deleted_utc == 0,
                Comment.is_banned == False
                )

        if g.user and g.user.admin_level >= 4:
            pass
        elif g.user:
            m = select(ModRelationship).filter_by(user_id=g.user.id, invite_rescinded=False)
            c = select(ContributorRelationship).filter_by(user_id=g.user.id)

            comments = comments.join(
                m, m.c.board_id == Submission.board_id, isouter=True
                ).join(
                c, c.c.board_id == Submission.board_id, isouter=True
                ).join(
                Board, Board.id == Submission.board_id
                )
                
            comments = comments.filter(
                or_(
                    Comment.author_id == g.user.id,
                    Submission.post_public == True,
                    Board.is_private == False,
                    m.c.board_id != None,
                    c.c.board_id != None),
                Board.is_banned==False
                )
        else:
            comments = comments.join(
                Board, 
                Board.id == Submission.board_id
                ).filter(
                    or_(
                        Submission.post_public == True, 
                        Board.is_private == False
                        ), 
                    Board.is_banned==False
                    )

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

        now = g.timestamp
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

        comments = comments.offset(per_page * (page - 1)).limit(per_page+1)

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
    @cache.memoize()  # 1hr cache time for user rep
    def karma(self):
        if self.id==1:
            return 503

        return self.energy - self.post_count

    @property
    @cache.memoize()
    def comment_karma(self):

        if self.id==1:
            return 0

        return self.comment_energy - self.comment_count

    @property
    @cache.memoize()
    def true_score(self):   
        
        return max((self.karma + self.comment_karma), -5)

    @property
    def fullname(self):
        return f"t1_{self.base36id}"

    @property
    @cache.memoize()
    @lazy
    def has_report_queue(self):
        board_ids = select(ModRelationship.board_id).options(lazyload('*')).filter(
                ModRelationship.user_id==self.id,
                ModRelationship.accepted==True,
                or_(
                    ModRelationship.perm_full==True,
                    ModRelationship.perm_content==True
                )
            )
        
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


        notifications = g.db.query(Notification
            ).options(
            lazyload('*'),
            ).join(
            Notification.comment
            ).filter(
            Notification.user_id==self.id,
            Comment.is_banned == False,
            Comment.deleted_utc == 0)



        if replies_only:
            cs=select(Comment.id).filter(Comment.author_id==self.id)
            ps=select(Submission.id).filter(Submission.author_id==self.id)
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
            cs=select(Comment.id).filter(Comment.author_id==self.id)
            ps=select(Submission.id).filter(Submission.author_id==self.id)
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
            #staying at 25 for performance reasons
            Notification.id.desc()).offset(25 * (page - 1)).limit(26).all()

        mark_as_read=False
        for x in notifications[0:25]:

            if x.read:
                continue

            x.read = True
            g.db.add(x)
            mark_as_read=True

        if mark_as_read:
            g.db.commit()

        return [x.comment_id for x in notifications]

    def notification_postlisting(self, all_=False, page=1):

        notifications=g.db.query(Notification).options(lazyload('*')).join(
            Notification.post
            ).filter(
            Notification.user_id==self.id,
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

        mark_as_read=False
        for x in notifications[0:25]:

            if x.read:
                continue

            x.read=True
            g.db.add(x)
            mark_as_ready=True

        if mark_as_read:
            g.db.commit()

        g.db.commit()
        return [x.submission_id for x in notifications]

    @property
    @lazy
    def mentions_count(self):
        cs=select(Comment.id).filter(Comment.author_id==self.id)
        ps=select(Submission.id).filter(Submission.author_id==self.id)
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
        cs=select(Comment.id).filter(Comment.author_id==self.id)
        ps=select(Submission.id).filter(Submission.author_id==self.id)
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
        return g.db.query(Notification).filter(
            Notification.user_id==self.id,
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
        return g.db.query(Notification).options(
            lazyload('*')
            ).join(
            Notification.comment
            ).filter(
            Notification.user_id==self.id,
            Notification.read==False,
            Comment.author_id==1
            ).count()

    @property
    @lazy
    def notifications_count(self):
        return g.db.query(Notification).options(
            lazyload('*')
            ).filter(
                Notification.user_id==self.id,
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
            is_banned=False, 
            deleted_utc=0
            ).count()

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
        returnselect(User.id).filter(
            or_(
                User.id.in_(
                    select(Alt.user1).filter(
                        Alt.user2==self.id
                    )
                ),
                User.id.in_(
                    select(Alt.user2).filter(
                        Alt.user1==self.id
                    )
                )
            )
        )
        

    def alts_threaded(self, db):

        subq = select(Alt).filter(
            or_(
                Alt.user1==self.id,
                Alt.user2==self.id
                )
            )

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
        self.profile_set_utc=g.timestamp
        self.profile_upload_region=request.headers.get("cf-ipcountry")
        g.db.add(self)
        g.db.commit()

    def set_banner(self, file):

        self.del_banner()
        self.banner_nonce += 1

        aws.upload_file(name=f"uid/{self.base36id}/banner-{self.banner_nonce}.png",
                        file=file)

        self.has_banner = True
        self.banner_upload_ip=request.remote_addr
        self.banner_upload_region=request.headers.get("cf-ipcountry")

        g.db.add(self)
        g.db.commit()

    def del_profile(self, db=None):

        aws.delete_file(name=f"uid/{self.base36id}/profile-{self.profile_nonce}.png")
        self.has_profile = False
        self.profile_nonce+=1
        if db:
            db.add(self)
            db.commit()
            db.close()
        else:
            g.db.add(self)
            g.db.commit()

    def del_banner(self, db=None):

        aws.delete_file(name=f"uid/{self.base36id}/banner-{self.banner_nonce}.png")
        self.has_banner = False
        self.banner_nonce+=1
        if db:
            db.add(self)
            db.commit()
            db.close()
        else:
            g.db.add(self)
            g.db.commit()

    @property
    def banner_url(self):

        if self.has_banner:
            return f"https://{app.config['S3_BUCKET']}/uid/{self.base36id}/banner-{self.banner_nonce}.png"
        else:
            return app.config["IMG_URL_JUMBOTRON"]

    @property
    def dynamic_profile_url(self):
        return f'/uid/{self.base36id}/pic/profile/{self.profile_nonce}'
    

    @property
    def profile_url(self):

        if self.has_profile and not self.is_deleted:
            return f"https://{app.config['S3_BUCKET']}/uid/{self.base36id}/profile-{self.profile_nonce}.png"
        else:
            return f"http{'s' if app.config['FORCE_HTTPS'] else ''}://{app.config['SERVER_NAME']}/logo/fontawesome/solid//{app.config['COLOR_PRIMARY']}/150"

    @property
    def can_make_guild(self):

        if app.config["GUILD_CREATION_REQ"]==-1:
            return self.admin_level >=3

        elif app.config["GUILD_CREATION_REQ"]==0:
            return self.can_join_gms
            
        return (self.has_premium or self.admin_level>=3 or self.true_score >= app.config["GUILD_CREATION_REQ"]) and self.can_join_gms

    @property
    def can_join_gms(self):

        if app.config["MAX_GUILD_COUNT"]==0:
            return True
        
        return len([x for x in self.boards_modded if x.is_siegable]) < app.config["MAX_GUILD_COUNT"]

    @property
    def can_siege(self):

        if self.is_suspended:
            return False

        now = g.timestamp

        return now - max(self.last_siege_utc,
                         self.created_utc) > 60 * 60 * 24 * 7

    @property
    def can_submit_image(self):
        # Has premium
        return (self.has_premium or self.true_score >= app.config['UPLOAD_IMAGE_REP']) and not g.is_tor

    @property
    def can_upload_avatar(self):
        return (self.has_premium or self.true_score >= app.config["PROFILE_UPLOAD_REP"]) and not g.is_tor

    @property
    def can_upload_banner(self):
        return (self.has_premium or self.true_score >= app.config["BANNER_UPLOAD_REP"]) and not g.is_tor

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

        now=g.timestamp
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
    def is_valid(self):
        if self.is_banned and self.unban_utc==0:
            return False

        elif self.is_deleted:
            return False

        else:
            return True
    

    def ban(self, admin=None, reason=None, message=None, days=0):

        self.is_banned = admin.id if admin else 1

        if reason:
            self.ban_reason = reason


        g.db.add(self)
        g.db.flush()

        #send message

        text="Your account has been"

        if not admin:
            text += " automatically"

        if days:
            text += f" suspended for {days} day{'s' if days>1 else ''}"
        else:
            text += " terminated"

        if reason:
            text += f" for the following reason:\n\n> {reason}"
        else:
            text += "."

        if not admin:
            text += f"\n\nBecause this ban was performed automatically, it may be appealed. If your ban was applied in error, [join the {app.config['SITE_NAME']} discord server](/discord), and you will be automatically added to the ban appeals channel."

        if message:
            text += f"\n\nAdditional private message from the admins:\n\n{message}"

        send_notif(self, text)

        if days > 0:
            ban_time = g.timestamp + (days * 86400)
            self.unban_utc = ban_time

        else:
            # Takes care of all functions needed for account termination
            self.unban_utc = 0
            if self.has_banner:
                thread1=threading.Thread(target=self.del_banner, kwargs={'db': db_session()})
                thread1.start()
            if self.has_profile:
                thread2=threading.Thread(target=self.del_profile, kwargs={'db': db_session()})
                thread2.start()

            add_role(self, "banned")
            delete_role(self, "member")

            #unprivate guilds if no mods remaining
            for b in self.boards_modded:
                if b.mods_count == 0:
                    b.is_private = False
                    b.restricted_posting = False
                    #b.all_opt_out = False
                    g.db.add(b)

            #ban api applications
            for application in self.applications:
                application.is_banned=True
                g.db.add(application)


            self.has_profile = False
            self.profile_nonce+=1
            self.has_banner = False
            self.banner_nonce+=1
        
        g.db.add(self)
        g.db.commit()
        
        discord_ban_action = f"{days} Day Ban" if days else "Perm Ban"
        discord_log_event(discord_ban_action, self, admin, reason=reason, admin_action=True)

    def unban(self):

        # Takes care of all functions needed for account reinstatement.

        self.is_banned = 0
        self.unban_utc = 0

        delete_role(self, "banned")

        g.db.add(self)
        
        discord_log_event("Unban", self, g.user, reason=self.ban_reason, admin_action=True)

        text = f'Your {app.config["SITE_NAME"]} account has been reinstated. Please review the [Terms of Service](/help/terms) and [Rules](/help/rules), and avoid breaking them in the future.'
        send_notif(self, text)

    @property
    def is_suspended(self):
        return (self.is_banned and (self.unban_utc ==
                                    0 or self.unban_utc > g.timestamp))

    @property
    def is_permbanned(self):
        return self.is_banned and not self.unban_utc
    

    @property
    def is_blocking(self):
        return self.__dict__.get('_is_blocking', 0)

    @property
    def is_blocked(self):
        return self.__dict__.get('_is_blocked', 0)

    def refresh_selfset_badges(self):

        for badge in BADGE_DEFS.values():
            if not badge.__dict__.get('expr'):
                continue
                
            should_have = badge.evaluate(self)
            if should_have:
                if not self.has_badge(badge.id):
                    new_badge = Badge(user_id=self.id,
                                      badge_id=badge.id,
                                      created_utc=g.timestamp
                                      )
                    g.db.add(new_badge)

            elif should_have==False:
                bad_badge = self.has_badge(badge.id)
                if bad_badge:
                    g.db.delete(bad_badge)

        g.db.commit()


    @property
    def applications(self):
        return [x for x in self._applications.order_by(
            OauthApp.id.asc()).all()]


    # def saved_idlist(self, page=1, per_page=25):

    #     posts = g.db.query(Submission.id).options(lazyload('*')).filter_by(is_banned=False,
    #                                                                        deleted_utc=0
    #                                                                        )

    #     if not self.over_18:
    #         posts = posts.filter_by(over_18=False)


    #     saved=select(SaveRelationship.submission_id).filter(SaveRelationship.user_id==self.id)
    #     posts=posts.filter(Submission.id.in_(saved))



    #     if self.admin_level < 4:
    #         # admins can see everything

    #         m = select(
    #             ModRelationship.board_id).filter_by(
    #             user_id=self.id,
    #             invite_rescinded=False)
    #         c = select(
    #             ContributorRelationship.board_id).filter_by(
    #             user_id=self.id)
    #         posts = posts.filter(
    #             or_(
    #                 Submission.author_id == self.id,
    #                 Submission.post_public == True,
    #                 Submission.board_id.in_(m),
    #                 Submission.board_id.in_(c)
    #             )
    #         )

    #         blocking = select(
    #             UserBlock.target_id).filter_by(
    #             user_id=self.id)
    #         blocked = select(
    #             UserBlock.user_id).filter_by(
    #             target_id=self.id)

    #         posts = posts.filter(
    #             Submission.author_id.notin_(blocking),
    #             Submission.author_id.notin_(blocked)
    #         )

    #     posts=posts.order_by(Submission.created_utc.desc())
        
    #     return [x[0] for x in posts.offset(per_page * (page - 1)).limit(per_page+1).all()]



    def guild_rep(self, guild, recent=0):

        

        posts=g.db.query(Submission.score_top).filter_by(
            is_banned=False,
            original_board_id=guild.id,
            is_bot=False)

        if recent:
            cutoff=g.timestamp-60*60*24*recent
            posts=posts.filter(Submission.created_utc>cutoff)

        posts=posts.all()

        post_rep= sum([x[0] for x in posts]) - len(posts)


        comments=g.db.query(Comment.score_top).filter_by(
            is_banned=False,
            original_board_id=guild.id,
            is_bot=False)

        if recent:
            cutoff=g.timestamp-60*60*24*recent
            comments=comments.filter(Comment.created_utc>cutoff)

        comments=comments.all()

        comment_rep=sum([x[0] for x in comments]) - len(comments)

        return int(post_rep + comment_rep)

    @property
    def has_premium(self):
        
        now=g.timestamp

        if self.negative_balance_cents:
            return False

        if self.is_permbanned:
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
        
        now=g.timestamp

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
        return strftime("%d %b %Y at %H:%M:%S", gmtime(self.premium_expires_utc))
    

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
        return self.has_premium and not g.is_tor

    @property
    def can_change_name(self):
        return self.name_changed_utc < g.timestamp - 60*60*24*app.config['COOLDOWN_DAYS_CHANGE_USERNAME'] and self.coin_balance>=app.config['COINS_REQUIRED_CHANGE_USERNAME']

    @cache.memoize(60*60*24)
    def badges_function(self):
        self.refresh_selfset_badges()
        return self._badges.all()

    badges = property(badges_function)

    @property
    def is_following(self):
        return self.__dict__.get('_is_following',None)
    
    @property
    def unban_string(self):
        if self.unban_utc==0:
            return "Permanent Ban"

        wait = self.unban_utc - g.timestamp

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
    
