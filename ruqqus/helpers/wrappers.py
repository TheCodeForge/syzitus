from flask import *
from os import environ
import requests
from werkzeug.wrappers.response import Response as RespObj
import time
import random

from ruqqus.classes import *
from .get import *
from .alerts import send_notification
from ruqqus.__main__ import Base, app, g, debug


def get_logged_in_user():

    if "user_id" in session:

        uid = session.get("user_id")
        nonce = session.get("login_nonce", 0)
        if not uid:
            g.user=None
            g.client=None
            return

        user=g.db.query(User).options(
            joinedload(User.moderates).joinedload(ModRelationship.board), #joinedload(Board.reports),
            joinedload(User.subscriptions).joinedload(Subscription.board),
            joinedload(User.notifications)
            ).filter_by(
            id=uid,
            is_deleted=False
            ).first()

        if request.path.startswith("/api/") and user.admin_level<3:
            g.user=None
            g.client=None
            return

        if user and (nonce < user.login_nonce):
            g.user=None
            g.client=None
            return
        else:
            g.user=user
            g.client=None
            return


    if request.path.startswith("/api/v1"):

        token = request.headers.get("Authorization")
        if not token:
            
            g.user=None
            g.client=None
            return

            # #let admins hit api/v1 from browser
            # x=session.get('user_id')
            # nonce=session.get('login_nonce')
            # if not x or not nonce:
            #     g.user=None
            #     g.client=None
            #     return
            # user=g.db.query(User).filter_by(id=x).first()
            # if not user:
            #     g.user=None
            #     g.client=None
            #     return
            # if user.admin_level >=3 and nonce>=user.login_nonce:
            #     g.user=user
            #     g.client=None
            #     return
            # else:
            #     g.user=None
            #     g.client=None
            #     return

        token = token.split()
        if len(token) < 2:
            
            g.user=None
            g.client=None
            return

        token = token[1]
        if not token:
            
            g.user=None
            g.client=None
            return

        client =g.db.query(ClientAuth).filter(
            ClientAuth.access_token == token,
            ClientAuth.access_token_expire_utc > int(time.time())
        ).first()

        g.user=client.user
        g.client=client
        return

    g.user=None
    g.client=None
    return

#this isn't a wrapper; it's just called by them
def validate_csrf_token():

    if request.method not in ["POST", "PUT", "PATCH", "DELETE"]:
        debug("req does not need csrf")
        return

    if request.path.startswith("/api/v2/") and g.user:
        debug("req is api call, does not need csrf")

    submitted_key = request.values.get("formkey", "none")

    #logged in users
    if g.user:
        if not g.user.validate_formkey(submitted_key):
            debug('logged in user, failed token')
            abort(401)

    else:
        #logged out users
        t=int(request.values.get("time", 0))

        if g.timestamp-t > 3600:
            debug('logged out user, token expired')
            abort(401)

        if not validate_hash(f"{t}+{session['session_id']}", submitted_key):
            debug('logged out user, invalid token')
            abort(401)

    debug("successful csrf")

def check_ban_evade():

    if not g.user or not g.user.ban_evade:
        return
    
    if random.randint(0,30) < g.user.ban_evade and not g.user.is_suspended:
        g.user.ban(reason="Evading a site-wide ban")
        send_notification(g.user, f"Your {app_config['SITE_NAME']} account has been permanently suspended for the following reason:\n\n> ban evasion")

        for post in g.db.query(Submission).filter_by(author_id=g.user.id).all():
            if post.is_banned:
                continue

            post.is_banned=True
            post.ban_reason=f"Ban evasion. This submission's owner was banned from {app_config['SITE_NAME']} on another account."
            g.db.add(post)

            ma=ModAction(
                kind="ban_post",
                user_id=1,
                target_submission_id=post.id,
                board_id=post.board_id,
                note="ban evasion"
                )
            g.db.add(ma)

        g.db.commit()

        for comment in g.db.query(Comment).filter_by(author_id=g.user.id).all():
            if comment.is_banned:
                continue

            comment.is_banned=True
            comment.ban_reason=f"Ban evasion. This comment's owner was banned from {app_config['SITE_NAME']} on another account."
            g.db.add(comment)

            ma=ModAction(
                kind="ban_comment",
                user_id=1,
                target_comment_id=comment.id,
                board_id=comment.post.board_id,
                note="ban evasion"
                )
            g.db.add(ma)

        g.db.commit()
        abort(403)

    else:
        g.user.ban_evade +=1
        g.db.add(g.user)
        g.db.commit()




# Wrappers
def auth_desired(f):
    # decorator for any view that changes if user is logged in (most pages)

    def wrapper(*args, **kwargs):

        get_logged_in_user()
            
        check_ban_evade()

        validate_csrf_token()

        resp = make_response(f(*args, **kwargs))
        if g.user:
            resp.headers.add("Cache-Control", "private")
            resp.headers.add(
                "Access-Control-Allow-Origin",
                app.config["SERVER_NAME"])
        else:
            resp.headers.add("Cache-Control", "public")
        return resp

    wrapper.__name__ = f.__name__
    wrapper.__doc__ = f.__doc__
    return wrapper


def auth_required(f):
    # decorator for any view that requires login (ex. settings)

    def wrapper(*args, **kwargs):

        get_logged_in_user()

        validate_csrf_token()

        if not g.user:
            abort(401)
            
        check_ban_evade()

        resp = make_response(f(*args, **kwargs))

        resp.headers.add("Cache-Control", "private")
        resp.headers.add(
            "Access-Control-Allow-Origin",
            app.config["SERVER_NAME"])
        return resp

    wrapper.__name__ = f.__name__
    wrapper.__doc__ = f.__doc__
    return wrapper


def is_not_banned(f):
    # decorator that enforces lack of ban

    def wrapper(*args, **kwargs):

        get_logged_in_user()

        if not g.user:
            abort(401)
            
        check_ban_evade()

        if g.user.is_suspended:
            abort(403)

        validate_csrf_token()

        resp = make_response(f(*args, **kwargs))
        resp.headers.add("Cache-Control", "private")
        resp.headers.add(
            "Access-Control-Allow-Origin",
            app.config["SERVER_NAME"])
        return resp

    wrapper.__name__ = f.__name__
    wrapper.__doc__ = f.__doc__
    return wrapper

def premium_required(f):

    #decorator that enforces valid premium status
    #use under auth_required or is_not_banned

    def wrapper(*args, **kwargs):

        if not g.user or not g.user.has_premium:
            abort(403)

        return f(*args, **kwargs)

    wrapper.__name__=f.__name__
    wrapper.__doc__ = f.__doc__
    return wrapper


def no_negative_balance(s):

    def wrapper_maker(f):

    #decorator that enforces valid premium status
    #use under auth_required or is_not_banned

        def wrapper(*args, **kwargs):

            if g.user.negative_balance_cents:
                if s=="toast":
                    return jsonify({"error":"You can't do that while your account balance is negative. Visit your account settings to bring your balance up to zero."}), 402
                elif s=="html":
                    raise(PaymentRequired)
                else:
                    raise(PaymentRequired)

            return f(*args, **kwargs)

        wrapper.__name__=f.__name__
        wrapper.__doc__ = f.__doc__
        return wrapper

    return wrapper_maker

def is_guildmaster(*perms):
    # decorator that enforces guildmaster status and verifies permissions
    # use under auth_required
    def wrapper_maker(f):

        def wrapper(*args, **kwargs):

            boardname = kwargs.get("guildname", kwargs.get("boardname"))
            board_id = kwargs.get("bid")
            bid=request.values.get("bid", request.values.get("board_id"))

            if boardname:
                board = get_guild(boardname)
            elif board_id:
                board = get_board(board_id)
            elif bid:
                board = get_board(bid)
            else:
                return jsonify({"error": f"no guild specified"}), 400

            m=board.has_mod(g.user)
            if not m:
                return jsonify({"error":f"You aren't a guildmaster of +{board.name}"}), 403

            if perms:
                for perm in perms:
                    if not m.__dict__.get(f"perm_{perm}") and not m.perm_full:
                        return jsonify({"error":f"Permission `{perm}` required"}), 403


            if g.user.is_banned and not g.user.unban_utc:
                abort(403)

            return f(*args, board=board, **kwargs)

        wrapper.__name__ = f.__name__
        wrapper.__doc__ = f"<small>guildmaster permissions: <code>{', '.join(perms)}</code></small><br>{f.__doc__}" if perms else f.__doc__
        return wrapper

    return wrapper_maker


# this wrapper takes args and is a bit more complicated
def admin_level_required(x):

    def wrapper_maker(f):

        def wrapper(*args, **kwargs):

            get_logged_in_user()

            validate_csrf_token()

            if g.client:
                return jsonify({"error": "No admin api client access"}), 403

            if not g.user:
                abort(401)

            if g.user.is_banned:
                abort(403)

            if g.user.admin_level < x:
                abort(403)

            response = f(*args, **kwargs)

            if isinstance(response, tuple):
                resp = make_response(response[0])
            else:
                resp = make_response(response)

            resp.headers.add("Cache-Control", "private")
            resp.headers.add(
                "Access-Control-Allow-Origin",
                app.config["SERVER_NAME"])
            return resp

        wrapper.__name__ = f.__name__
        wrapper.__doc__ = f.__doc__
        return wrapper

    return wrapper_maker

def user_update_lock(f):

    def wrapper(*args, **kwargs):

        #user below authentication to make user be with for update
        g.user =g.db.query(User).with_for_update().options(lazyload('*')).filter_by(id=g.user.id).first()

        return f(*args, **kwargs)

    wrapper.__name__=f.__name__
    wrapper.__doc__=f.__doc__
    return wrapper

def no_cors(f):
    """
    Decorator prevents content being iframe'd
    """

    def wrapper(*args, **kwargs):

        origin = request.headers.get("Origin", None)

        if origin and origin != "https://" + app.config["SERVER_NAME"] and app.config["FORCE_HTTPS"]==1:

            return "This page may not be embedded in other webpages.", 403

        resp = make_response(f(*args, **kwargs))
        resp.headers.add("Access-Control-Allow-Origin",
                         app.config["SERVER_NAME"]
                         )

        return resp

    wrapper.__name__ = f.__name__
    wrapper.__doc__ = f.__doc__
    return wrapper

# wrapper for api-related things that discriminates between an api url
# and an html url for the same content
# f should return {'api':lambda:some_func(), 'html':lambda:other_func()}


def api(*scopes, no_ban=False):

    def wrapper_maker(f):

        def wrapper(*args, **kwargs):

            if request.path.startswith('/api/v2'):

                if g.client:

                    if not g.user or not g.client:
                        return jsonify(
                            {"error": "401 Not Authorized. Invalid or Expired Token"}), 401

                    kwargs.pop('c')

                    # validate app associated with token
                    if client.application.is_banned:
                        return jsonify({"error": f"403 Forbidden. The application `{client.application.app_name}` is suspended."}), 403

                    # validate correct scopes for request
                    for scope in scopes:
                        if not client.__dict__.get(f"scope_{scope}"):
                            return jsonify({"error": f"401 Not Authorized. Scope `{scope}` is required."}), 403

                    if (request.method == "POST" or no_ban) and g.user.is_suspended:
                        return jsonify({"error": f"403 Forbidden. The user account is suspended."}), 403

                if not g.user:
                    return jsonify({"error": f"401 Not Authorized. You must log in."}), 401

                if g.user.is_suspended:
                    return jsonify({"error": f"403 Forbidden. You are banned."}), 403
                    

                result = f(*args, **kwargs)

                if isinstance(result, dict):
                    try:
                        resp = result['api']()
                    except KeyError:
                        resp=result
                else:
                    resp = result

                if not isinstance(resp, RespObj):
                    resp = make_response(resp)

                resp.headers.add("Cache-Control", "private")
                resp.headers.add(
                    "Access-Control-Allow-Origin",
                    app.config["SERVER_NAME"])
                return resp

            else:

                result = f(*args, **kwargs)

                if not isinstance(result, dict):
                    return result

                try:
                    if request.path.startswith('/inpage/'):
                        return result['inpage']()
                    elif request.path.startswith(('/api/vue/','/test/')):
                        return result['api']()
                    else:
                        return result['html']()
                except KeyError:
                    return result

        wrapper.__name__ = f.__name__
        wrapper.__doc__ = f"<small>oauth scopes: <code>{', '.join(scopes)}</code></small><br>{f.__doc__}" if scopes else f.__doc__
        return wrapper

    return wrapper_maker


SANCTIONS=[
    "CU",   #Cuba
    "IR",   #Iran
    "KP",   #North Korea
    "SY",   #Syria
    "TR",   #Turkey
    "VE",   #Venezuela
]

def no_sanctions(f):

    def wrapper(*args, **kwargs):

        if request.headers.get("cf-ipcountry","") in SANCTIONS:
            abort(451)

        return f(*args, **kwargs)

    wrapper.__name__=f.__name__
    wrapper.__doc__ = f.__doc__
    return wrapper


def public_cache(f):

    def wrapper(*args, **kwargs):

        resp = f(*args, **kwargs)
        debug(f"remove deprecated wrapper public_cache from function {f.__name__}")
        return resp

    wrapper.__name__=f.__name__
    wrapper.__doc__=f.__doc__
    return wrapper
