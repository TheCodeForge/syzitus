from ruqqus.classes import *
from ruqqus.helpers.wrappers import *
from urllib.parse import quote
import re

from sqlalchemy import *

from flask import *
from ruqqus.classes.domains import reasons as REASONS
from ruqqus.__main__ import app, cache



query_regex=re.compile("(\w+):(\S+)")
valid_params=[
    'author',
    'domain',
    'guild',
    'url'
]

def searchparse(text):

    #takes test in filter:term format and returns data

    criteria = {x[0]:x[1] for x in query_regex.findall(text)}

    for x in criteria:
        if x in valid_params:
            text = text.replace(f"{x}:{criteria[x]}", "")

    text=text.lstrip().rstrip()

    if text:
        criteria['q']=text

    return criteria



@cache.memoize(300)
def searchlisting(criteria, v=None, page=1, t="None", sort="top", b=None):

    posts = g.db.query(Submission).options(
                lazyload('*')
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
        
    if 'author' in criteria:
        posts=posts.filter(
                Submission.author_id==get_user(criteria['author']).id,
                User.is_private==False,
                User.is_deleted==False
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
        domain=re.sub("[^a-z0-9.]","", domain)
        #escape periods
        domain=domain.replace(".","\.")

        posts=posts.filter(
            SubmissionAux.url.op('~')(
                "https?://([^/]*\.)?"+domain+"(/|$)"
                )
            )

            # or_(
            #     SubmissionAux.url.ilike("https://"+domain+'/%'),
            #     SubmissionAux.url.ilike("http://"+domain+'/%'),
            #     SubmissionAux.url.ilike("https://"+domain),
            #     SubmissionAux.url.ilike("http://"+domain),
            #     SubmissionAux.url.ilike("https://%."+domain+'/%'),
            #     SubmissionAux.url.ilike("http://%."+domain+'/%'),
            #     SubmissionAux.url.ilike("https://%."+domain),
            #     SubmissionAux.url.ilike("http://%."+domain)
            #     ),
            # not_(SubmissionAux.url.ilike("https://%/%"+domain)),
            # not_(SubmissionAux.url.ilike("http://%/%"+domain))


    if not (v and v.over_18):
        posts = posts.filter(Submission.over_18 == False)

    if v and v.hide_offensive:
        posts = posts.filter(Submission.is_offensive == False)
		
    if v and v.hide_bot:
        posts = posts.filter(Submission.is_bot == False)

    if not(v and v.admin_level >= 3):
        posts = posts.filter(
            Submission.deleted_utc == 0,
            Submission.is_banned == False,
            )

    if v and v.admin_level >= 4:
        pass
    elif v:
        m = g.db.query(ModRelationship.board_id).filter_by(
            user_id=v.id, invite_rescinded=False).subquery()
        c = g.db.query(
            ContributorRelationship.board_id).filter_by(
            user_id=v.id).subquery()
        posts = posts.filter(
            or_(
                Submission.author_id == v.id,
                Submission.post_public == True,
                Submission.board_id.in_(m),
                Submission.board_id.in_(c)
            )
        )

        blocking = g.db.query(
            UserBlock.target_id).filter_by(
            user_id=v.id).subquery()
        blocked = g.db.query(
            UserBlock.user_id).filter_by(
            target_id=v.id).subquery()

        posts = posts.filter(
            Submission.author_id.notin_(blocking),
            #Submission.author_id.notin_(blocked),
            Board.is_banned==False,
        )
    else:
        posts = posts.filter(
            Submission.post_public == True,
            Board.is_banned==False,
            )

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
    posts = [x for x in posts.offset(25 * (page - 1)).limit(26).all()]

    return total, [x.id for x in posts]


@app.route("/search", methods=["GET"])
@app.route("/api/v1/search", methods=["GET"])
@app.route("/api/vue/search")
@auth_desired
@api("read")
def search(v, search_type="posts"):

    query = request.args.get("q", '').lstrip().rstrip()

    page = max(1, int(request.args.get("page", 1)))

    if query.startswith("+"):

        # guild search stuff here
        sort = request.args.get("sort", "subs").lower()
    
        term=query.lstrip('+')
        term=term.replace('\\','')
        term=term.replace('_','\_')

        boards = g.db.query(Board).filter(
            Board.name.ilike(f'%{term}%'))

        if not(v and v.over_18):
            boards = boards.filter_by(over_18=False)

        if not (v and v.admin_level >= 3):
            boards = boards.filter_by(is_banned=False)

        if v:
            joined = g.db.query(Subscription).filter_by(user_id=v.id, is_active=True).subquery()

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
                               v=v,
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
        
        now=int(time.time())
        users=g.db.query(User).filter(
            User.username.ilike(f'%{term}%'))
        
        
        if not (v and v.admin_level >= 3):
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
                       v=v,
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
        total, ids = searchlisting(criteria, v=v, page=page, t=t, sort=sort)

        next_exists = (len(ids) == 26)
        ids = ids[0:25]

        posts = get_posts(ids, v=v)

        if v and v.admin_level>3 and "domain" in criteria:
            domain=criteria['domain']
            domain_obj=get_domain(domain)
        else:
            domain=None
            domain_obj=None

        return {"html":lambda:render_template("search.html",
                               v=v,
                               query=query,
                               total=total,
                               page=page,
                               listing=posts,
                               sort_method=sort,
                               time_filter=t,
                               next_exists=next_exists,
                               domain=domain,
                               domain_obj=domain_obj,
                               reasons=REASONS
                               ),
                "api":lambda:jsonify({"data":[x.json for x in posts]})
                }


@app.route("/+<name>/search", methods=["GET"])
@auth_desired
def search_guild(name, v, search_type="posts"):


    query=request.args.get("q","").lstrip().rstrip()

    if query.startswith(("+","@")):
        return redirect(f"/search?q={quote(query)}")

    b = get_guild(name, graceful=True)
    if not b:
        abort(404)

    if b.is_banned:
        return render_template("board_banned.html", v=v, b=b)

    page=max(1, int(request.args.get("page", 1)))

    sort=request.args.get("sort", "hot").lower()
    
    
    t = request.args.get('t', 'all').lower()

    #posts search

    total, ids = searchlisting(searchparse(query), v=v, page=page, t=t, sort=sort, b=b)

    next_exists=(len(ids)==26)
    ids=ids[0:25]

    posts=get_posts(ids, v=v)

    return render_template("search.html",
                   v=v,
                   query=query,
                   total=total,
                   page=page,
                   listing=posts,
                       sort_method=sort,
                           next_exists=next_exists,
               time_filter=t,
                           b=b
                   )
