from flask import g, session, abort, render_template, jsonify, make_response, redirect
from urllib.parse import quote, urlencode
from werkzeug.security import safe_join

from syzitus.helpers.wrappers import *
from syzitus.helpers.session import *
from syzitus.classes.custom_errors import *

from syzitus.__main__ import app, cache

# Errors


@app.errorhandler(401)
@api()
def error_401(e):

    # path = request.path
    # qs = urlencode(dict(request.args))
    # argval = quote(f"{path}?{qs}", safe='')
    # output = f"/login?redirect={argval}"

    return{"html": lambda: (render_template('errors/401.html'), 401),
           "api": lambda: (jsonify({"error": "401 Not Authorized"}), 401)
           }

@app.errorhandler(PaymentRequired)
@api()
def error_402(e):
    return{"html": lambda: (render_template('errors/402.html'), 402),
           "api": lambda: (jsonify({"error": "402 Payment Required"}), 402)
           }

@app.errorhandler(403)
@api()
def error_403(e):
    return{"html": lambda: (render_template('errors/403.html'), 403),
           "api": lambda: (jsonify({"error": "403 Forbidden"}), 403)
           }


@app.errorhandler(404)
@auth_desired
@api()
def error_404(e):

    if request.args.get("from_ruqqus"):
        return{"html": lambda: (render_template('errors/410.html'), 410),
               "api": lambda: (jsonify({"error": "410 Gone"}), 410)
               }

    return{"html": lambda: (render_template('errors/404.html'), 404),
           "api": lambda: (jsonify({"error": "404 Not Found"}), 404)
           }


@app.errorhandler(405)
@api()
def error_405(e):
    return{"html": lambda: (render_template('errors/405.html'), 405),
           "api": lambda: (jsonify({"error": "405 Method Not Allowed"}), 405)
           }


@app.errorhandler(409)
@api()
def error_409(e):
    return{"html": lambda: (render_template('errors/409.html'), 409),
           "api": lambda: (jsonify({"error": "409 Conflict"}), 409)
           }


@app.errorhandler(410)
@api()
def error_410(e):
    return{"html": lambda: (render_template('errors/410.html'), 410),
           "api": lambda: (jsonify({"error": "410 Gone"}), 410)
           }


@app.errorhandler(413)
@api()
def error_413(e):
    return{"html": lambda: (render_template('errors/413.html'), 413),
           "api": lambda: (jsonify({"error": "413 Request Payload Too Large"}), 413)
           }

@app.errorhandler(418)
@api()
def error_418(e):
    return{"html": lambda: (render_template('errors/418.html'), 418),
           "api": lambda: (jsonify({"error": "418 I'm a teapot, and you're toast. Don't come back."}), 418)
           }


@app.errorhandler(422)
@api()
def error_422(e):
    return{"html": lambda: (render_template('errors/422.html'), 422),
           "api": lambda: (jsonify({"error": "422 Unprocessable Entity"}), 422)
           }


@app.errorhandler(429)
@api()
def error_429(e):

    ip=request.remote_addr

    #get recent violations
    # if r:
    #     count_429s = r.get(f"429_count_{ip}")
    #     if not count_429s:
    #         count_429s=0
    #     else:
    #         count_429s=int(count_429s)

    #     count_429s+=1

    #     r.set(f"429_count_{ip}", count_429s)
    #     r.expire(f"429_count_{ip}", 60)

    #     #if you exceed 30x 429 without a 60s break, you get IP banned for 1 hr:
    #     if count_429s>=30:
    #         try:
    #             print("triggering IP ban", request.remote_addr, session.get("user_id"), session.get("history"))
    #         except:
    #             pass
            
    #         r.set(f"ban_ip_{ip}", g.timestamp)
    #         r.expire(f"ban_ip_{ip}", 3600)
    #         return "", 429



    return{"html": lambda: (render_template('errors/429.html'), 429),
           "api": lambda: (jsonify({"error": "429 Too Many Requests"}), 429)
           }


@app.errorhandler(451)
@api()
def error_451(e):
    return{"html": lambda: (render_template('errors/451.html'), 451),
           "api": lambda: (jsonify({"error": "451 Unavailable For Legal Reasons"}), 451)
           }


@app.errorhandler(500)
@api()
def error_500(e):
    try:
        g.db.rollback()
    except AttributeError:
        pass

    return{"html": lambda: (render_template('errors/500.html'), 500),
           "api": lambda: (jsonify({"error": "500 Internal Server Error"}), 500)
           }

@app.errorhandler(503)
@api()
def error_503(e):
    try:
        g.db.rollback()
    except AttributeError:
        pass

    return{"html": lambda: (render_template('errors/503.html'), 503),
           "api": lambda: (jsonify({"error": "503 Service Unavailable"}), 503)
           }

@app.route("/allow_nsfw_logged_in/<bid>", methods=["POST"])
@auth_required
def allow_nsfw_logged_in(bid):

    cutoff = g.timestamp + 3600

    if not session.get("over_18", None):
        session["over_18"] = {}

    session["over_18"][bid] = cutoff

    return redirect(request.form.get("redir"))


@app.route("/allow_nsfw_logged_out/<bid>", methods=["POST"])
@auth_desired
def allow_nsfw_logged_out(bid):

    if g.user:
        return redirect('/')

    t = int(request.form.get('time'))

    if not session.get("over_18", None):
        session["over_18"] = {}

    cutoff = g.timestamp + 3600
    session["over_18"][bid] = cutoff

    return redirect(request.form.get("redir"))


@app.route("/allow_nsfl_logged_in/<bid>", methods=["POST"])
@auth_required
def allow_nsfl_logged_in(bid):

    cutoff = g.timestamp + 3600

    if not session.get("show_nsfl", None):
        session["show_nsfl"] = {}

    session["show_nsfl"][bid] = cutoff

    return redirect(request.form.get("redir"))


@app.route("/allow_nsfl_logged_out/<bid>", methods=["POST"])
@auth_desired
def allow_nsfl_logged_out(bid):

    if g.user:
        return redirect('/')

    t = int(request.form.get('time'))

    if not session.get("show_nsfl", None):
        session["show_nsfl"] = {}

    cutoff = g.timestamp + 3600
    session["show_nsfl"][bid] = cutoff

    return redirect(request.form.get("redir"))


@app.route("/error/<eid>", methods=["GET"])
@auth_desired
def error_all_preview(eid):
     return render_template(safe_join('errors', f"{eid}.html"))