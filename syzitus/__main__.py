import gevent.monkey
gevent.monkey.patch_all()

#import gc

from os import environ, path
from secrets import token_hex
from flask import Flask, redirect, render_template, jsonify, abort, g, request
from flask_caching import Cache
from flask_limiter import Limiter
from flask_minify import Minify
from collections import deque
from psycopg2.errors import UndefinedColumn
from sys import getsizeof
import time

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError, StatementError, InternalError, IntegrityError, ProgrammingError
from sqlalchemy.orm import Session, sessionmaker, scoped_session
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
#import threading
#import random
from redis import Redis

from redis import BlockingConnectionPool, ConnectionPool

from werkzeug.middleware.proxy_fix import ProxyFix


_version = "4.5.1"

app = Flask(__name__,
            template_folder='./templates'
            )

app.config["PROXYFIX_X_FOR"]=int(environ.get("PROXYFIX", "2").lstrip().rstrip())
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=app.config["PROXYFIX_X_FOR"])
app.url_map.strict_slashes = False

app.config["SITE_NAME"]=environ.get("SITE_NAME", "Syzitus").lstrip().rstrip()
app.config["TAGLINE"]=environ.get("TAGLINE", "Set a TAGLINE!").lstrip().rstrip()
app.config["SUBTITLE"]=environ.get("SUBTITLE", "").lstrip().rstrip()

app.config["COLOR_PRIMARY"]=environ.get("COLOR_PRIMARY", "805AD5").lstrip().rstrip()
app.config["COLOR_SECONDARY"]=environ.get("COLOR_SECONDARY", "E2E8F0").lstrip().rstrip()
app.config["COLOR_PRIMARY_NAME"]=environ.get("COLOR_PRIMARY_NAME","Porpl").lstrip().rstrip()

app.config["RUQQUSPATH"]=environ.get("RUQQUSPATH", path.dirname(path.realpath(__file__)))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DATABASE_URL'] = environ.get("DATABASE_URL","").replace("postgres://", "postgresql://")

# app.config['SQLALCHEMY_READ_URIS'] = [
#     environ.get("DATABASE_CONNECTION_READ_01_URL"),
#     environ.get("DATABASE_CONNECTION_READ_02_URL"),
#     environ.get("DATABASE_CONNECTION_READ_03_URL")
# ]

app.config['SECRET_KEY'] = environ.get('SECRET_KEY')
app.config["ADMIN_EMAIL"]=environ.get("ADMIN_EMAIL","").lstrip().rstrip()

SERVER_NAME = environ.get("SERVER_NAME", environ.get("domain", "syzitus.com")).lstrip().rstrip()
# ONION_NAME = environ.get("ONION_NAME", "")

# class DomainMatcher(str):

#     def __init__(self, *names):

#         self.names = list(names)

#     def __eq__(self, other):

#         return other in self.names

app.config["SERVER_NAME"] = SERVER_NAME #DomainMatcher(SERVER_NAME, ONION_NAME)

#environ.get(
#    "domain", environ.get(
#        "SERVER_NAME", "")).lstrip().rstrip()



# Cookie stuff
app.config["SHORT_DOMAIN"]=environ.get("SHORT_DOMAIN","").lstrip().rstrip()
app.config["SESSION_COOKIE_NAME"] = f"__Host-{app.config['SERVER_NAME']}"
app.config["VERSION"] = _version
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024
app.config["SESSION_COOKIE_SECURE"] = bool(int(environ.get("FORCE_HTTPS", 1)))
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_DOMAIN"] = False

app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 365
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

app.config["FORCE_HTTPS"] = int(environ.get("FORCE_HTTPS", 1)) if not any([x in app.config["SERVER_NAME"] for x in ["localhost","127.0.0.1"]]) else 0
app.config["DISABLE_SIGNUPS"]=int(environ.get("DISABLE_SIGNUPS",0))
app.config["DISABLE_CATEGORIES"]=int(environ.get("DISABLE_CATEGORIES",0))

app.jinja_env.cache = {}

app.config["UserAgent"] = f"Content Aquisition for {app.config['SERVER_NAME']} message board v{_version}."

if "localhost" in app.config["SERVER_NAME"]:
    app.config["CACHE_TYPE"] = "NullCache"
elif not environ.get("REDIS_URL"):
    app.config["CACHE_TYPE"] = "FileSystemCache"
else:
    app.config["CACHE_TYPE"] = environ.get("CACHE_TYPE", 'NullCache').lstrip().rstrip()

app.config["CACHE_DIR"] = environ.get("CACHE_DIR", "ruqquscache")

# captcha configs
app.config["HCAPTCHA_SITEKEY"] = environ.get("HCAPTCHA_SITEKEY","").lstrip().rstrip()
app.config["HCAPTCHA_SECRET"] = environ.get("HCAPTCHA_SECRET","").lstrip().rstrip()
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

# Redis configs
app.config["CACHE_REDIS_URL"] = environ.get("REDIS_URL","").rstrip().lstrip()
app.config["CACHE_DEFAULT_TIMEOUT"] = 60
app.config["CACHE_KEY_PREFIX"] = "flask_caching_"
app.config["REDIS_POOL_SIZE"]=int(environ.get("REDIS_POOL_SIZE", 3))

# AWS configs
app.config["S3_BUCKET"]=environ.get("S3_BUCKET_NAME","i.syzitus.com").lstrip().rstrip()


redispool=ConnectionPool(
    max_connections=app.config["REDIS_POOL_SIZE"],
    host=app.config["CACHE_REDIS_URL"].split("://")[1]
    ) if app.config["CACHE_TYPE"]=="redis" else None
app.config["CACHE_OPTIONS"]={'connection_pool':redispool} if app.config["CACHE_TYPE"]=="redis" else {}

app.config["READ_ONLY"]=bool(int(environ.get("READ_ONLY", False)))
app.config["BOT_DISABLE"]=bool(int(environ.get("BOT_DISABLE", False)))

app.config["PROFILE_UPLOAD_REP"]=int(environ.get("PROFILE_UPLOAD_REP", "300").lstrip().rstrip())
app.config["BANNER_UPLOAD_REP"]=int(environ.get("BANNER_UPLOAD_REP", "500").lstrip().rstrip())
app.config["GUILD_CREATION_REQ"]=int(environ.get("GUILD_CREATION_REQ", "500").lstrip().rstrip())
app.config["MAX_GUILD_COUNT"]=int(environ.get("MAX_GUILD_COUNT", "10").lstrip().rstrip())
app.config['UPLOAD_IMAGE_REP']=int(environ.get("UPLOAD_IMAGE_REP","10").lstrip().rstrip())

app.config["DEBUG"]=bool(int(environ.get("DEBUG", 0)))
app.config["GROWTH_HACK"]=bool(int(environ.get("GROWTH_HACK", 0)))

#discord configs
app.config['DISCORD_SERVER_ID'] = environ.get("DISCORD_SERVER_ID",'').rstrip()
app.config['DISCORD_CLIENT_ID'] = environ.get("DISCORD_CLIENT_ID",'').rstrip()
app.config['DISCORD_CLIENT_SECRET'] = environ.get("DISCORD_CLIENT_SECRET",'').rstrip()
app.config['DISCORD_BOT_TOKEN'] = environ.get("DISCORD_BOT_TOKEN",'').rstrip()
app.config['DISCORD_ENDPOINT'] = "https://discordapp.com/api/v6"

app.config["DISCORD_ROLE_IDS"]={
    "banned":  environ.get("DISCORD_BANNED_ROLE_ID",'').rstrip(),
    "member":  environ.get("DISCORD_MEMBER_ROLE_ID",'').rstrip(),
    "realid":  environ.get("DISCORD_REALID_ROLE_ID",'').rstrip(),
    "premium": environ.get("DISCORD_PREMIUM_ROLE_ID",'').rstrip(),
}

app.config["DISCORD_CHANNEL_IDS"]={
    "welcome": environ.get("DISCORD_WELCOME_CHANNEL_ID",'').rstrip(),
    "log": environ.get("DISCORD_LOG_CHANNEL_ID",'').rstrip()
}

#premium related configs
app.config["COINS_REQUIRED_CHANGE_USERNAME"]=int(environ.get("COINS_REQUIRED_CHANGE_USERNAME", 20))
app.config["COOLDOWN_DAYS_CHANGE_USERNAME"]=int(environ.get("COOLDOWN_DAYS_CHANGE_USERNAME", 7))
app.config["WEEKLY_COIN_TARGET"]=int(environ.get("WEEKLY_COIN_TARGET", 20))

#precompute logo urls
app.config["IMG_URL_MASCOT"] = f"/mascot/{app.config['COLOR_PRIMARY'].lower()}"
app.config["IMG_URL_LOGO_WHITE"] = f"/logo/white/{app.config['COLOR_PRIMARY'].lower()}/{app.config['SITE_NAME'][0].lower()}"
app.config["IMG_URL_LOGO_MAIN"] = f"/logo/main/{app.config['COLOR_PRIMARY'].lower()}/{app.config['SITE_NAME'][0].lower()}"
app.config["IMG_URL_JUMBOTRON"] = f"/logo/jumbotron/{app.config['COLOR_PRIMARY'].lower()}/{app.config['SITE_NAME'][0].lower()}"
app.config["IMG_URL_FAVICON"]=f"/logo/splash/{app.config['COLOR_PRIMARY']}/{app.config['SITE_NAME'][0].lower()}/64/64"
app.config["IMG_URL_THUMBSPLASH"]=f"/logo/splash/{app.config['COLOR_PRIMARY']}/{app.config['SITE_NAME'][0].lower()}/1200/630"
app.config["FEATURE_ENABLE_EMOJI"]=bool(int(environ.get("FEATURE_ENABLE_EMOJI",1)))
app.config["FEATURE_ENABLE_GIFS"]=bool(int(environ.get("FEATURE_ENABLE_GIFS",bool(environ.get('GIPHY_KEY')))))

#GIPHY
app.config["GIPHY_KEY"] = environ.get('GIPHY_KEY','').lstrip().rstrip()

#Cloudflare Turnstile
app.config["CLOUDFLARE_TURNSTILE_KEY"]=environ.get("CLOUDFLARE_TURNSTILE_KEY",'').lstrip().rstrip()
app.config["CLOUDFLARE_TURNSTILE_SECRET"]=environ.get("CLOUDFLARE_TURNSTILE_SECRET",'').lstrip().rstrip()

#Event configs
app.config["EVENT_SNOWBALL_FIGHT"]=bool(int(environ.get("EVENT_SNOWBALL_FIGHT", 0)))

#random other configs
app.config['BYPASS_CATEGORIES']=bool(int(environ.get("BYPASS_CATEGORIES", 0)))

cache = Cache(app)

if bool(int(environ.get("MINIFY",0))):
    Minify(app)

# class CorsMatch(str):

#     def __eq__(self, other):
#         if isinstance(other, str):
#             if other == f'https://{app.config["SERVER_NAME"]}':
#                 return True

#             elif other.endswith(f".{app.config['SERVER_NAME']}"):
#                 return True

#         elif isinstance(other, list):
#             if f'https://{app.config["SERVER_NAME"]}' in other:
#                 return True
#             elif any([x.endswith(f".{app.config['SERVER_NAME']}") for x in other]):
#                 return True

#         return False

# app.config["CACHE_REDIS_URL"]
app.config["RATELIMIT_STORAGE_URI"] = environ.get("REDIS_URL", 'memory://').lstrip().rstrip()
app.config["RATELIMIT_KEY_PREFIX"] = "flask_limiting_"
app.config["RATELIMIT_ENABLED"] = not bool(int(environ.get("DISABLE_RATELIMIT", 0)))
app.config["RATELIMIT_DEFAULTS_DEDUCT_WHEN"]=lambda x:True
app.config["RATELIMIT_DEFAULTS_EXEMPT_WHEN"]=lambda:False
app.config["RATELIMIT_HEADERS_ENABLED"]=True

limiter = Limiter(
    lambda: request.remote_addr,
    app=app,
    application_limits=["60/minute"],
    headers_enabled=True,
    strategy="fixed-window",
    storage_uri=app.config["RATELIMIT_STORAGE_URI"]#,
    #on_breach=ban_ip
)

# setup db
                         
#engines = {
#    "leader": create_engine(app.config['DATABASE_URL'], pool_size=pool_size, pool_use_lifo=True),
#    "followers": [create_engine(x, pool_size=pool_size, pool_use_lifo=True) for x in app.config['SQLALCHEMY_READ_URIS'] if x] if any(i for i in app.config['SQLALCHEMY_READ_URIS']) else [create_engine(app.config['DATABASE_URL'], pool_size=pool_size, pool_use_lifo=True)]
#}

_engine=create_engine(
    app.config['DATABASE_URL'],
    poolclass=QueuePool,
    pool_size=int(environ.get("PG_POOL_SIZE",5)),
    pool_use_lifo=True
)


#These two classes monkey patch sqlalchemy for leader/follower

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


db_session=scoped_session(sessionmaker(bind=_engine))

Base = declarative_base()


#set the shared redis cache for misc stuff

# r=Redis(
#     host=app.config["CACHE_REDIS_URL"].split("://")[1], 
#     decode_responses=True,
#     ssl = app.config["CACHE_REDIS_URL"].startswith('rediss://'),
#     ssl_cert_reqs=None,
#     connection_pool = redispool
#     ) if app.config["CACHE_REDIS_URL"] else None

#debug function

def debug(text):
    if app.config["DEBUG"]:
        print(text)

# import and bind all routing functions
from syzitus.helpers.security import generate_hash
import syzitus.classes
from syzitus.routes import *
import syzitus.helpers.jinja2
from syzitus.helpers.get import *

#purge css from cache
cache.delete_memoized(syzitus.routes.main_css)

# def drop_connection():

#     g.db.rollback()
#     g.db.close()
#     gevent.getcurrent().kill()


# enforce https
@app.before_request
def before_request():

    if not session.get("session_id"):
        session["session_id"] = token_hex(16)

    g.timestamp = int(time.time())
    g.nonce=generate_hash(f'{g.timestamp}+{session.get("session_id")}')
    g.db = db_session()

    if request.method.lower() != "get" and app.config["READ_ONLY"] and request.path != "/login":
        return jsonify({"error":f"{app.config['SITE_NAME']} is currently in read-only mode."}), 400

    if app.config["BOT_DISABLE"] and request.headers.get("X-User-Type")=="Bot":
        abort(503)

    g.timestamp = int(time.time())

    g.db = db_session()
    g.ip=None
    g.ua=None
    g.is_archive=False
    g.is_tor=request.headers.get("cf-ipcountry")=="T1"

    ip_ban= get_ip(request.remote_addr)

    if ip_ban and ip_ban.unban_utc and ip_ban.unban_utc > g.timestamp:
        ip_ban.unban_utc = g.timestamp + 60*60
        g.db.add(ip_ban)
        g.db.commit()
        return jsonify({"error":"Your ban has been reset for another hour. Slow down."}), 429
    elif ip_ban and "archive" in ip_ban.reason:
        g.ip=ip_ban
        g.is_archive=True
    elif ip_ban and ip_ban.reason=="malicious scraper honeypot" and session.get("user_id"):
        pass

    elif ip_ban:
        return jsonify({"error":"Refused due to your previous malicious conduct"}), 424

    session.permanent = True

    useragent=request.headers.get("User-Agent", "NoAgent")

    ua_ban = g.db.query(
        syzitus.classes.Agent).filter(
            or_(
                syzitus.classes.Agent.kwd.in_(useragent.split()),
                syzitus.classes.Agent.kwd.ilike(useragent)
                )
            ).first()

    if ua_ban and ua_ban.instaban:
        existing_ban=get_ip(request.remote_addr)
        if not existing_ban:
            new_ip=syzitus.classes.IP(
                addr=request.remote_addr,
                unban_utc=None,
                reason="archive instaban",
                banned_by=1
                )
            g.db.add(new_ip)
            try:
                g.db.commit()
            except IntegrityError:
                pass    
    if ua_ban and "archive" in ua_ban.reason:
            g.db.ua=ua_ban
            g.is_archive=True
    elif ua_ban and request.path != "/robots.txt":
        return ua_ban.__dict__.get("mock",""), ua_ban.status_code

    if app.config["FORCE_HTTPS"] and request.url.startswith(
            "http://") and "localhost" not in app.config["SERVER_NAME"]:
        url = request.url.replace("http://", "https://", 1)
        return redirect(url, code=301)

    #default user to none
    g.user=None

    ua=request.headers.get("User-Agent","")
    if "CriOS/" in ua:
        g.system="ios/chrome"
    elif "iPhone" in ua:
        g.system="ios/safari"
    elif "Version/" in ua:
        g.system="android/webview"
    elif "Mobile Safari/" in ua:
        g.system="android/chrome"
    else:
        g.system="other/other"


@app.after_request
def after_request(response):

    try:
        debug([g.get('user'), request.method, request.path, request.url_rule])
    except:
        debug(["<detached>", request.method, request.path, request.url_rule])

        
    response.headers.add('Access-Control-Allow-Headers',
                         "Origin, X-Requested-With, Content-Type, Accept, x-auth")
    response.headers.add("Strict-Transport-Security", "max-age=31536000")
    response.headers.add("Referrer-Policy", "same-origin")
    response.headers.add("X-Content-Type-Options","nosniff")
    response.headers.add("Permissions-Policy",
        "geolocation=(), midi=(), notifications=(), push=(), sync-xhr=(), microphone=(), camera=(), magnetometer=(), gyroscope=(), vibrate=(), payment=()")

    if app.config["FORCE_HTTPS"]:
        response.headers.add("Content-Security-Policy", 
            f"default-src https:; form-action {app.config['SERVER_NAME']}; frame-src {app.config['SERVER_NAME']}  challenges.cloudflare.com *.hcaptcha.com *.youtube.com youtube.com platform.twitter.com; object-src none; style-src 'self' 'nonce-{g.nonce}' maxcdn.bootstrapcdn.com unpkg.com cdn.jsdelivr.net; script-src 'self' 'nonce-{g.nonce}' challenges.cloudflare.com *.hcaptcha.com hcaptcha.com code.jquery.com cdnjs.cloudflare.com stackpath.bootstrapcdn.com cdn.jsdelivr.net unpkg.com platform.twitter.com; img-src https: data:")


    if not request.path.startswith(("/embed/", "/assets/js/", "/assets/css/", "/logo/")):
        response.headers.add("X-Frame-Options", "deny")

    return response

@app.teardown_request
def teardown_request(resp):

    try:
        g.db.close()
    except:
        pass

    return True


@app.route("/<path:path>", subdomain="www")
def www_redirect(path):

    return redirect(f"https://{app.config['SERVER_NAME']}/{path}")


#Check for existence of +general and @system and image host db entries
try:
    db=db_session()
    system = db.query(syzitus.classes.User).filter_by(id=1).first()
    if not system:
        system = User(
            id=1,
            username=app.config['SITE_NAME'].lower(),
            created_utc = int(time.time()),
            admin_level=6,
            original_username=app.config['SITE_NAME'].lower()
            )

        db.add(system)
        db.commit()
        debug(f"@{app.config['SITE_NAME'].lower()} created")

    elif len(app.config["SERVER_NAME"].split('.'))==2 and system.username != app.config["SITE_NAME"].lower():
        system.username=app.config["SITE_NAME"].lower()
        db.add(system)
        db.commit()


    general = db.query(syzitus.classes.Board).filter_by(id=1).first()
    description_text=f"Catch-all zone for content rejected from elsewhere on {app.config['SITE_NAME']}. Not shown in All/Trending."

    if not general:

        general = Board(
            id=1,
            name="general",
            created_utc = int(time.time()),
            creator_id=1,
            is_siegable=False,
            all_opt_out=True,
            subcat_id=71,
            description=description_text,
            description_html=f"<p>{description_text}</p>"
            )
        db.add(general)
        db.commit()
        debug("+general created")
    elif len(app.config["SERVER_NAME"].split('.'))==2 and general.description != description_text:
        general.description=description_text
        general.description_html=f"<p>{description_text}</p>"
        db.add(general)
        db.commit()

    img = db.query(syzitus.classes.Domain).filter_by(domain=app.config["S3_BUCKET"]).first()

    if not img:

        img = Domain(
            id=1,
            domain=app.config["S3_BUCKET"],
            is_banned=False,
            show_thumbnail=True
            )
        db.add(img)
        db.commit()

    db.close()
except ProgrammingError:
    pass