import gevent.monkey
gevent.monkey.patch_all()

#import eventlet
#eventlet.monkey_patch()

#import psycogreen.gevent
#psycogreen.gevent.patch_psycopg()

import os
from os import environ
import secrets
from flask import *
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_compress import Compress
#from flask_socketio import SocketIO
from time import sleep
from collections import deque
import psycopg2

from flaskext.markdown import Markdown
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError, StatementError, InternalError
from sqlalchemy.orm import Session, sessionmaker, scoped_session, Query as _Query
from sqlalchemy import *
from sqlalchemy.pool import QueuePool
import threading
import requests
import random
import redis
import gevent
import sys

from redis import BlockingConnectionPool, ConnectionPool

from werkzeug.middleware.proxy_fix import ProxyFix


_version = "3.0.8"

app = Flask(__name__,
            template_folder='./templates'
            )
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=3)
app.url_map.strict_slashes = False

app.config["SITE_NAME"]=environ.get("SITE_NAME", "Ruqqus").lstrip().rstrip()

app.config["COLOR_PRIMARY"]=environ.get("COLOR_PRIMARY", "805AD5").lstrip().rstrip()
app.config["COLOR_SECONDARY"]=environ.get("COLOR_SECONDARY", "E2E8F0").lstrip().rstrip()

app.config["RUQQUSPATH"]=environ.get("RUQQUSPATH", os.path.dirname(os.path.realpath(__file__)))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DATABASE_URL'] = environ.get("DATABASE_URL","").replace("postgres://", "postgresql://")

# app.config['SQLALCHEMY_READ_URIS'] = [
#     environ.get("DATABASE_CONNECTION_READ_01_URL"),
#     environ.get("DATABASE_CONNECTION_READ_02_URL"),
#     environ.get("DATABASE_CONNECTION_READ_03_URL")
# ]

app.config['SECRET_KEY'] = environ.get('SECRET_KEY')

SERVER_NAME = environ.get("SERVER_NAME", environ.get("domain", "ruqqus.com")).lstrip().rstrip()
# ONION_NAME = environ.get("ONION_NAME", "")

class DomainMatcher(str):

    def __init__(self, *names):

        self.names = list(names)

    def __eq__(self, other):

        return other in self.names

app.config["SERVER_NAME"] = SERVER_NAME #DomainMatcher(SERVER_NAME, ONION_NAME)

#environ.get(
#    "domain", environ.get(
#        "SERVER_NAME", "")).lstrip().rstrip()


app.config["SHORT_DOMAIN"]=environ.get("SHORT_DOMAIN","").lstrip().rstrip()
app.config["SESSION_COOKIE_NAME"] = "session_ruqqus"
app.config["VERSION"] = _version
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024
app.config["SESSION_COOKIE_SECURE"] = bool(int(environ.get("FORCE_HTTPS", 1)))
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 365
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

app.config["FORCE_HTTPS"] = int(environ.get("FORCE_HTTPS", 1)) if ("localhost" not in app.config["SERVER_NAME"] and "127.0.0.1" not in app.config["SERVER_NAME"]) else 0
app.config["DISABLE_SIGNUPS"]=int(environ.get("DISABLE_SIGNUPS",0))

app.jinja_env.cache = {}

app.config["UserAgent"] = f"Content Aquisition for Porpl message board v{_version}."

if "localhost" in app.config["SERVER_NAME"]:
    app.config["CACHE_TYPE"] = "null"
else:
    app.config["CACHE_TYPE"] = environ.get("CACHE_TYPE", 'filesystem').lstrip().rstrip()

app.config["CACHE_DIR"] = environ.get("CACHE_DIR", "ruqquscache")

# captcha configs
app.config["HCAPTCHA_SITEKEY"] = environ.get("HCAPTCHA_SITEKEY","").lstrip().rstrip()
app.config["HCAPTCHA_SECRET"] = environ.get(
    "HCAPTCHA_SECRET","").lstrip().rstrip()
app.config["SIGNUP_HOURLY_LIMIT"]=int(environ.get("SIGNUP_HOURLY_LIMIT",0))

# antispam configs
app.config["SPAM_SIMILARITY_THRESHOLD"] = float(
    environ.get("SPAM_SIMILARITY_THRESHOLD", 0.5))
app.config["SPAM_SIMILAR_COUNT_THRESHOLD"] = int(
    environ.get("SPAM_SIMILAR_COUNT_THRESHOLD", 5))
app.config["SPAM_URL_SIMILARITY_THRESHOLD"] = float(
    environ.get("SPAM_URL_SIMILARITY_THRESHOLD", 0.1))
app.config["COMMENT_SPAM_SIMILAR_THRESHOLD"] = float(
    environ.get("COMMENT_SPAM_SIMILAR_THRESHOLD", 0.5))
app.config["COMMENT_SPAM_COUNT_THRESHOLD"] = int(
    environ.get("COMMENT_SPAM_COUNT_THRESHOLD", 5))

app.config["CACHE_REDIS_URL"] = environ.get(
    "REDIS_URL").rstrip().lstrip() if environ.get("REDIS_URL") else None
app.config["CACHE_DEFAULT_TIMEOUT"] = 60
app.config["CACHE_KEY_PREFIX"] = "flask_caching_"

app.config["S3_BUCKET"]=environ.get("S3_BUCKET_NAME","i.ruqqus.com").lstrip().rstrip()

app.config["REDIS_POOL_SIZE"]=int(environ.get("REDIS_POOL_SIZE", 10))

redispool=ConnectionPool(
    max_connections=app.config["REDIS_POOL_SIZE"],
    host=app.config["CACHE_REDIS_URL"][8:]
    ) if app.config["CACHE_TYPE"]=="redis" else None
app.config["CACHE_OPTIONS"]={'connection_pool':redispool} if app.config["CACHE_TYPE"]=="redis" else {}

app.config["READ_ONLY"]=bool(int(environ.get("READ_ONLY", False)))
app.config["BOT_DISABLE"]=bool(int(environ.get("BOT_DISABLE", False)))

app.config["TENOR_KEY"]=environ.get("TENOR_KEY",'').lstrip().rstrip()

app.config["PROFILE_UPLOAD_REP"]=int(environ.get("PROFILE_UPLOAD_REP", "300").lstrip().rstrip())
app.config["BANNER_UPLOAD_REP"]=int(environ.get("BANNER_UPLOAD_REP", "500").lstrip().rstrip())
app.config["GUILD_CREATION_REQ"]=int(environ.get("GUILD_CREATION_REQ", "500").lstrip().rstrip())
app.config["MAX_GUILD_COUNT"]=int(environ.get("MAX_GUILD_COUNT", "10").lstrip().rstrip())
app.config['UPLOAD_IMAGE_REP']=int(environ.get("UPLOAD_IMAGE_REP","10").lstrip().rstrip())

app.config["DEBUG"]=bool(int(environ.get("DEBUG", 0)))

Markdown(app)
cache = Cache(app)
Compress(app)

class CorsMatch(str):

    def __eq__(self, other):
        if isinstance(other, str):
            if other == f'https://{app.config["SERVER_NAME"]}':
                return True

            elif other.endswith(f".{app.config['SERVER_NAME']}"):
                return True

        elif isinstance(other, list):
            if f'https://{app.config["SERVER_NAME"]}' in other:
                return True
            elif any([x.endswith(f".{app.config['SERVER_NAME']}") for x in other]):
                return True

        return False




# app.config["CACHE_REDIS_URL"]
app.config["RATELIMIT_STORAGE_URL"] = environ.get("REDIS_URL").lstrip().rstrip() if environ.get("REDIS_URL") else 'memory://'
app.config["RATELIMIT_KEY_PREFIX"] = "flask_limiting_"
app.config["RATELIMIT_ENABLED"] = True
app.config["RATELIMIT_DEFAULTS_DEDUCT_WHEN"]=lambda x:True
app.config["RATELIMIT_DEFAULTS_EXEMPT_WHEN"]=lambda:False
app.config["RATELIMIT_HEADERS_ENABLED"]=True


def limiter_key_func():
    return request.remote_addr


limiter = Limiter(
    app,
    key_func=limiter_key_func,
    default_limits=["100/minute"],
    headers_enabled=True,
    strategy="fixed-window",
    storage_options={'max_connections':100}
    #storage_options={'connection_pool':redispool}
)

# setup db
                         
#engines = {
#    "leader": create_engine(app.config['DATABASE_URL'], pool_size=pool_size, pool_use_lifo=True),
#    "followers": [create_engine(x, pool_size=pool_size, pool_use_lifo=True) for x in app.config['SQLALCHEMY_READ_URIS'] if x] if any(i for i in app.config['SQLALCHEMY_READ_URIS']) else [create_engine(app.config['DATABASE_URL'], pool_size=pool_size, pool_use_lifo=True)]
#}

_engine=create_engine(
    app.config['DATABASE_URL'],
    poolclass=QueuePool,
    pool_size=int(environ.get("PG_POOL_SIZE",10)),
    pool_use_lifo=True
)


#These two classes monkey patch sqlalchemy

# class RoutingSession(Session):
#     def get_bind(self, mapper=None, clause=None):
#         try:
#             if self._flushing or request.method == "POST":
#                 return engines['leader']
#             else:
#                 return random.choice(engines['followers'])
#         except BaseException:
#             if self._flushing:
#                 return engines['leader']
#             else:
#                 return random.choice(engines['followers'])


def retry(f):

    def wrapper(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except OperationalError as e:
            #self.session.rollback()
            raise(DatabaseOverload)
        except:
            self.session.rollback()
            return f(self, *args, **kwargs)

    wrapper.__name__=f.__name__
    return wrapper


# class RetryingQuery(_Query):

#     @retry
#     def all(self):
#         return super().all()

#     @retry
#     def count(self):
#         return super().count()

#     @retry
#     def first(self):
#         return super().first()

#db_session = scoped_session(sessionmaker(class_=RoutingSession))#, query_cls=RetryingQuery))
db_session=scoped_session(sessionmaker(bind=_engine)) #, query_cls=RetryingQuery))

Base = declarative_base()


#set the shared redis cache for misc stuff

r=redis.Redis(
    host=app.config["CACHE_REDIS_URL"][8:], 
    decode_responses=True, 
    ssl_cert_reqs=None,
    connection_pool = redispool
    ) if app.config["CACHE_REDIS_URL"] else None



local_ban_cache={}

IP_BAN_CACHE_TTL = int(environ.get("IP_BAN_CACHE_TTL", 3600))
UA_BAN_CACHE_TTL = int(environ.get("UA_BAN_CACHE_TTL", 3600))

#debug function

def debug(text):
    if app.config["DEBUG"]:
        print(text)

# import and bind all routing functions
import ruqqus.classes
from ruqqus.routes import *
import ruqqus.helpers.jinja2

#purge css from cache
cache.delete_memoized(ruqqus.routes.main_css)


@cache.memoize(UA_BAN_CACHE_TTL)
def get_useragent_ban_response(user_agent_str):
    """
    Given a user agent string, returns a tuple in the form of:
    (is_user_agent_banned, (insult, status_code))
    """
    #if request.path.startswith("/socket.io/"):
    #    return False, (None, None)

    result = g.db.query(
        ruqqus.classes.Agent).filter(
        ruqqus.classes.Agent.kwd.in_(
            user_agent_str.split())).first()
    if result:
        return True, (result.mock or "Follow the robots.txt, dumbass",
                      result.status_code or 418)
    return False, (None, None)

def drop_connection():

    g.db.close()
    gevent.getcurrent().kill()


# enforce https
@app.before_request
def before_request():

    if request.method.lower() != "get" and app.config["READ_ONLY"] and request.path != "/login":
        return jsonify({"error":f"{app.config['SITE_NAME']} is currently in read-only mode."}), 400

    if app.config["BOT_DISABLE"] and request.headers.get("X-User-Type")=="Bot":
        abort(503)



    if r and bool(r.get(f"ban_ip_{request.remote_addr}")):
        return jsonify({"error":"Too many requests. You are in time out for 1 hour. Rate limit is 100/min; less for authentication and content creation endpoints."}), 429

    g.db = db_session()

    if g.db.query(IP).filter_by(addr=request.remote_addr).first():
        abort(503)

    g.timestamp = int(time.time())

    session.permanent = True

    ua_banned, response_tuple = get_useragent_ban_response(
        request.headers.get("User-Agent", "NoAgent"))
    if ua_banned:
        return response_tuple

    if app.config["FORCE_HTTPS"] and request.url.startswith(
            "http://") and "localhost" not in app.config["SERVER_NAME"]:
        url = request.url.replace("http://", "https://", 1)
        return redirect(url, code=301)

    if not session.get("session_id"):
        session["session_id"] = secrets.token_hex(16)

    #default user to none
    g.user=None

    ua=request.headers.get("User-Agent","")
    if "CriOS/" in ua:
        g.system="ios/chrome"
    elif "Version/" in ua:
        g.system="android/webview"
    elif "Mobile Safari/" in ua:
        g.system="android/chrome"
    elif "Safari/" in ua:
        g.system="ios/safari"
    elif "Mobile/" in ua:
        g.system="ios/webview"
    else:
        g.system="other/other"


# def log_event(name, link):

#     x = requests.get(link)

#     if x.status_code != 200:
#         return

#     text = f'> **{name}**\r> {link}'

#     url = os.environ.get("DISCORD_WEBHOOK")
#     headers = {"Content-Type": "application/json"}
#     data = {"username": "ruqqus",
#             "content": text
#             }

#     x = requests.post(url, headers=headers, json=data)
#     print(x.status_code)


@app.after_request
def after_request(response):

    try:
        debug([g.get('user'), request.path, request.url_rule])
    except:
        debug(["<detached>", request.path, request.url_rule])
    response.headers.add('Access-Control-Allow-Headers',
                         "Origin, X-Requested-With, Content-Type, Accept, x-auth"
                         )
    # response.headers.add("Cache-Control",
    #                      "maxage=600")
    response.headers.add("Strict-Transport-Security", "max-age=31536000")
    response.headers.add("Referrer-Policy", "same-origin")
    # response.headers.add("X-Content-Type-Options","nosniff")
    response.headers.add("Feature-Policy",
                         "geolocation 'none'; midi 'none'; notifications 'none'; push 'none'; sync-xhr 'none'; microphone 'none'; camera 'none'; magnetometer 'none'; gyroscope 'none'; vibrate 'none'; fullscreen 'none'; payment 'none';")
    if not request.path.startswith("/embed/"):
        response.headers.add("X-Frame-Options", "deny")


    if not g.get('user'):
        response.headers.add("Cache-Control", "public")

    # signups - hit discord webhook
    # if request.method == "POST" and response.status_code in [
    #         301, 302] and request.path == "/signup":
    #     link = f'https://{app.config["SERVER_NAME"]}/@{request.form.get("username")}'
    #     thread = threading.Thread(
    #         target=lambda: log_event(
    #             name="Account Signup", link=link))
    #     thread.start()

    # req_stop = time.time()

    # try:
    #     req_time=req_stop - g.timestamp
    #     site_performance(req_time)
    # except AttributeError:
    #     pass

    g.db.close()

    return response


@app.route("/<path:path>", subdomain="www")
def www_redirect(path):

    return redirect(f"https://{app.config['SERVER_NAME']}/{path}")

#engines["leader"].dispose()
#for engine in engines["followers"]:
#    engine.dispose()

