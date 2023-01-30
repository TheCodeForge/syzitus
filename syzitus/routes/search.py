from urllib.parse import quote
from re import compile as re_compile, sub as re_sub
from flask import g, session, abort, render_template, jsonify, redirect
from sqlalchemy import select
from sqlalchemy.orm import contains_eager, lazyload, joinedload, load_only

from syzitus.classes import *
from syzitus.helpers.wrappers import *
from syzitus.classes.domains import reasons as REASONS

from syzitus.__main__ import app, cache



query_regex=re_compile('(\w+):(".+"|\S+)')
valid_params=[
    'author',
    'domain',
    'guild',
    'url',
    'ip'
]

def searchparse(text):

    #takes test in filter:term format and returns data

    criteria = {x[0]:x[1].lstrip('"').rstrip('"') for x in query_regex.findall(text)}

    for x in criteria:
        if x in valid_params:
            text = text.replace(f"{x}:{criteria[x]}", "")

    if text:
        criteria['q']=text.lstrip().rstrip()

    return criteria


@cache.memoize()
def searchlisting(criteria, page=1, t="None", sort="top", b=None):

    posts = g.db.query(Submission).options(
                lazyload('*'), load_only(Submission.id)
            ).join(
                Submission.submission_aux,
            ).join(
                Submission.author
            ).join(
                Submission.board
            )
    
    if 'q' in criteria:
        words=criteria['q'].split()
        words=[SubmissionAux.title.ilike('%'+x+'%') for x in words]
        words=tuple(words)
        posts=posts.filter(*words)

    if 'text' in criteria:
        words=criteria['text'].split()
        words=[SubmissionAux.body.ilike('%'+x+'%') for x in words]
        words=tuple(words)
        posts=posts.filter(*words)
        
    if 'author' in criteria:
        posts=posts.filter(
                Submission.author_id==get_user(criteria['author']).id,
                User.is_private==False,
                User.is_deleted==False,
                or_(
                    User.is_banned==0,
                    and_(
                        User.is_banned>0,
                        User.unban_utc<g.timestamp
                    )
                )
            )

    if b:
        posts=posts.filter(Submission.board_id==b.id)
    elif 'guild' in criteria:
        board=get_guild(criteria["guild"])
        posts=posts.filter(
                Submission.board_id==board.id,
            )

    if 'url' in criteria:
        url=criteria['url']
        url=url.replace('%','\%')
        url=url.replace('_','\_')
        posts=posts.filter(
            SubmissionAux.url.ilike("%"+criteria['url']+"%")
            )

    if 'domain' in criteria:
        domain=criteria['domain']

        #sanitize domain by removing anything that isn't [a-z0-9.]
        domain=domain.lower()
        domain=re_sub("[^a-z0-9.-]","", domain)
        #escape periods
        domain=domain.replace(".","\.")

        posts=posts.filter(
            SubmissionAux.url.op('~')(
                "https?://([^/]*\.)?"+domain+"(/|$)"
                )
            )

    if 'ip' in criteria and g.user and g.user.admin_level>=5:
        ipaddr=criteria['ip']
        ipaddr=ipaddr.replace(".","\.")
        posts=posts.filter(
            Submission.creation_ip.op("~")(ipaddr)
            )
    elif 'ip' in criteria:
        abort(403)


    if not (g.user and g.user.over_18):
        posts = posts.filter(Submission.over_18 == False)

    if g.user and g.user.hide_offensive:
        posts = posts.filter(Submission.is_offensive == False)
		
    if g.user and g.user.hide_bot:
        posts = posts.filter(Submission.is_bot == False)

    if not(g.user and g.user.admin_level >= 3):
        posts = posts.filter(
            Submission.deleted_utc == 0,
            Submission.is_banned == False,
            Board.is_banned == False
            )

    if g.user and g.user.admin_level >= 4:
        pass
    elif g.user:
        m = select(ModRelationship.board_id).filter_by(
            user_id=g.user.id, invite_rescinded=False)
        c = select(
            ContributorRelationship.board_id).filter_by(
            user_id=g.user.id)
        posts = posts.filter(
            or_(
                Submission.author_id == g.user.id,
                Submission.post_public == True,
                Submission.board_id.in_(m),
                Submission.board_id.in_(c)
            )
        )

        blocking = select(
            UserBlock.target_id).filter_by(
            user_id=g.user.id)
        blocked = select(
            UserBlock.user_id).filter_by(
            target_id=g.user.id)

        posts = posts.filter(
            Submission.author_id.notin_(blocking),
            Submission.author_id.notin_(blocked),
            Board.is_banned==False,
        )
    else:
        posts = posts.filter(
            Submission.post_public == True,
            Board.is_banned==False,
            )

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

    posts=posts.options(
        contains_eager(Submission.submission_aux),
        contains_eager(Submission.author),
        contains_eager(Submission.board)
        )

    if sort == "hot":
        posts = posts.order_by(Submission.score_hot.desc())
    elif sort == "new":
        posts = posts.order_by(Submission.created_utc.desc())
    elif sort == "old":
        posts = posts.order_by(Submission.created_utc.asc())
    elif sort == "disputed":
        posts = posts.order_by(Submission.score_disputed.desc())
    elif sort == "top":
        posts = posts.order_by(Submission.score_top.desc())

    total = posts.count()

    return total, [x.id for x in posts.offset(25 * (page - 1)).limit(26).all()]


@app.route("/search", methods=["GET"])
@auth_desired
@api("read")
def search(search_type="posts"):

    query = request.args.get("q", '').lstrip().rstrip()

    if f"//{app.config['SERVER_NAME']}" in query:
        thing=get_from_permalink(query)
        if thing:
            return redirect(thing.permalink)

    page = max(1, int(request.args.get("page", 1)))

    if query.startswith("+"):

        # guild search stuff here
        sort = request.args.get("sort", "subs").lower()
    
        term=query.lstrip('+')
        term=term.replace('\\','')
        term=term.replace('_','\_')

        boards = g.db.query(Board).filter(
            Board.name.ilike(f'%{term}%'))

        if not(g.user and g.user.over_18):
            boards = boards.filter_by(over_18=False)

        if not (g.user and g.user.admin_level >= 3):
            boards = boards.filter_by(is_banned=False)

        if g.user:
            joined = g.db.query(Subscription).filter_by(user_id=g.user.id, is_active=True).subquery()

            boards=boards.join(
                joined,
                joined.c.board_id==Board.id,
                isouter=True
                )

            boards=boards.order_by(
                Board.name.ilike(term).desc(),
                joined.c.id.is_(None).asc(),
                Board.stored_subscriber_count.desc(),
                )



        else:

            boards = boards.order_by(
                Board.name.ilike(term).desc(), 
                Board.stored_subscriber_count.desc()
                )

        total = boards.count()

        boards = [x for x in boards.offset(25 * (page - 1)).limit(26)]
        next_exists = (len(boards) == 26)
        boards = boards[0:25]

        return {"html":lambda:render_template("search_boards.html",
                               query=query,
                               total=total,
                               page=page,
                               boards=boards,
                               sort_method=sort,
                               next_exists=next_exists
                               ),
                "api":lambda:jsonify({"data":[x.json for x in boards]})
                }

    elif query.startswith("@"):
            
        term=query.lstrip('@')
        term=term.replace('\\','')
        term=term.replace('_','\_')
        
        now=g.timestamp
        users=g.db.query(User).filter(
            User.username.ilike(f'%{term}%'))
        
        
        if not (g.user and g.user.admin_level >= 3):
            users=users.filter(
            User.is_private==False,
            User.is_deleted==False,
            or_(
              User.is_banned==0,
              and_(
                User.is_banned>0,
		User.unban_utc>0,
                User.unban_utc<now
              )
            )
        )
        users=users.order_by(User.username.ilike(term).desc(), User.stored_subscriber_count.desc())
        
        total=users.count()
        
        users=[x for x in users.offset(25 * (page-1)).limit(26)]
        next_exists=(len(users)==26)
        users=users[0:25]
        
        
        
        return {"html":lambda:render_template("search_users.html",
                       query=query,
                       total=total,
                       page=page,
                       users=users,
                       next_exists=next_exists
                      ),
                "api":lambda:jsonify({"data":[x.json for x in users]})
                }
                   
    

    else:
        sort = request.args.get("sort", "top").lower()
        t = request.args.get('t', 'all').lower()



        # posts search

        criteria=searchparse(query)
        total, ids = searchlisting(criteria, page=page, t=t, sort=sort)

        next_exists = (len(ids) == 26)
        ids = ids[0:25]

        posts = get_posts(ids)

        if g.user and g.user.admin_level>3 and "domain" in criteria:
            domain=criteria['domain']
            domain_obj=get_domain(domain)
        else:
            domain=None
            domain_obj=None

        if g.user and g.user.admin_level>=5 and 'ip' in criteria:
            ip=criteria['ip']
            ip_ban=get_ip(ip)
        else:
            ip=None
            ip_ban=None

        return {"html":lambda:render_template("search.html",
                               query=query,
                               total=total,
                               page=page,
                               listing=posts,
                               sort_method=sort,
                               time_filter=t,
                               next_exists=next_exists,
                               domain=domain,
                               domain_obj=domain_obj,
                               ip=ip,
                               ip_ban=ip_ban,
                               reasons=REASONS
                               ),
                "api":lambda:jsonify({"data":[x.json for x in posts]})
                }


@app.route("/+<name>/search", methods=["GET"])
@auth_desired
def search_guild(name, search_type="posts"):


    query=request.args.get("q","").lstrip().rstrip()

    if query.startswith(("+","@")):
        return redirect(f"/search?q={quote(query)}")

    b = get_guild(name)

    if b.is_banned:
        return render_template("board_banned.html", b=b)

    page=max(1, int(request.args.get("page", 1)))

    sort=request.args.get("sort", "hot").lower()
    
    
    t = request.args.get('t', 'all').lower()

    #posts search

    total, ids = searchlisting(searchparse(query), page=page, t=t, sort=sort, b=b)

    next_exists=(len(ids)==26)
    ids=ids[0:25]

    posts=get_posts(ids)

    return render_template("search.html",
                   query=query,
                   total=total,
                   page=page,
                   listing=posts,
                       sort_method=sort,
                           next_exists=next_exists,
               time_filter=t,
                           b=b
                   )
