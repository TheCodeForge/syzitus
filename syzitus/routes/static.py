from jinja2.exceptions import TemplateNotFound
import pyotp
import sass
import mistletoe
from flask import g, session, abort, render_template, jsonify, make_response, request, send_file, Response, redirect
from werkzeug.security import safe_join
import PIL
import io
from PIL import ImageFont, ImageDraw

from syzitus.helpers.wrappers import *
from syzitus.helpers.markdown import *
from syzitus.classes import *
from syzitus.mail import *

from syzitus.__main__ import app, limiter, debug, cache

# take care of misc pages that never really change (much)

@app.route("/assets/style/<color>/<file>.css", methods=["GET"])
@cf_cache
@cache.memoize()
def main_css(color, file, n=None):

    #print(file, color)

    if file not in ["light", "dark"]:
        abort(404)

    name=f"{app.config['RUQQUSPATH']}/assets/style/{file}.scss"
    #print(name)
    with open(name, "r") as file:
        raw = file.read()

    # This doesn't use python's string formatting because
    # of some odd behavior with css files

    downvote_color = hex(0xFFFFFF - int(color,16))[2:]
    while len(downvote_color)<6:
        downvote_color=f"0{downvote_color}"
    scss = raw.replace("{primary}", color)

    scss = scss.replace("{secondary}", app.config["COLOR_SECONDARY"])
    scss = scss.replace("{main}", app.config["COLOR_PRIMARY"])
    scss = scss.replace("{downvote}", downvote_color)

    #compile the regular css
    output=sass.compile(string=scss)

    #add title classes

    output +="\n\n"

    colors=list(set([TITLES[x].color for x in TITLES]))

    output += "\n".join([f".title-color-{x}"+"{color: #"+x+";}" for x in colors])

    return resp

@app.get('/assets/<path:path>')
@cf_cache
@limiter.exempt
def static_service(path):

    try:
        resp = make_response(send_file(safe_join('./assets', path)))
    except FileNotFoundError:
           abort(404)

    if request.path.endswith('.css'):
        resp.headers.add("Content-Type", "text/css")
    elif request.path.endswith(".js"):
        resp.headers.add("Content-Type", "text/javascript")
    return resp


@app.route("/robots.txt", methods=["GET"])
def robots_txt():

    # banned_robot_uas = ["Mozilla", "Chrome", "Safari"]

    # if request.headers.get("User-Agent") and not any([x in request.headers["User-Agent"] for x in banned_robot_uas]):
    #     return make_response("User-Agent: *\nDisallow: /", mimetype="text/plain")

    return send_file("./assets/robots.txt")


@app.route("/slurs.txt", methods=["GET"])
def slurs():

    text='\n'.join(
        [x.keyword for x in g.db.query(
            BadWord
            ).order_by(
            BadWord.keyword.asc()
            ).all()
            ]
        )
    if text:
        resp = make_response(f"The following words, and variations of them, will cause {app.config['SITE_NAME']} content to be flagged as offensive:\n"+text)
    else:
        resp = make_response("<No keywords in the site slur list at this time>")
    resp.headers.add("Content-Type", "text/plain")
    return resp


@app.route("/settings", methods=["GET"])
@auth_required
def settings():
    return redirect("/settings/profile")


@app.route("/settings/profile", methods=["GET"])
@auth_required
def settings_profile():
    eval_env={
        "user": g.user,
        "db": g.db,
        "Board": Board,
        "Submission": Submission
    }

    titles= [TITLES[x] for x in TITLES if eval(TITLES[x].expr, eval_env)]
    return render_template(
        "settings_profile.html",
        titles=titles)


@app.route("/help/titles", methods=["GET"])
@auth_desired
def titles():
    return render_template("/help/titles.html",
                           titles=list(TITLES.values())
                           )


@app.route("/help/badges", methods=["GET"])
@auth_desired
def badges():
    return render_template("help/badges.html",
                           badges=sorted(list(BADGE_DEFS.values()), key=lambda x: x.id)
                           )


@app.route("/help/admins", methods=["GET"])
@auth_desired
def help_admins():

    admins = g.db.query(User).filter(
        User.admin_level > 1,
        User.id > 1).order_by(
        User.id.asc()).all()
    admins = [x for x in admins]

    exadmins = g.db.query(User).filter_by(
        admin_level=1).order_by(
        User.id.asc()).all()
    exadmins = [x for x in exadmins]

    return render_template("help/admins.html",
                           admins=admins,
                           exadmins=exadmins
                           )


@app.route("/settings/security", methods=["GET"])
@auth_required
def settings_security():

    mfa_secret=pyotp.random_base32() if not g.user.mfa_secret else None

    if mfa_secret:
        recovery=f"{mfa_secret}+{g.user.id}+{g.user.original_username}"
        recovery=generate_hash(recovery)
        recovery=base36encode(int(recovery,16) % 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)
        while len(recovery)<25:
            recovery="0"+recovery
        recovery=" ".join([recovery[i:i+5] for i in range(0,len(recovery),5)])
    else:
        recovery=None

    return render_template(
            "settings_security.html",
            mfa_secret=mfa_secret,
            recovery=recovery,
            error=request.args.get("error") or None,
            msg=request.args.get("msg") or None
        )

@app.route("/settings/premium", methods=["GET"])
@auth_required
def settings_premium():
    return render_template("settings_premium.html",
                           error=request.args.get("error") or None,
                           msg=request.args.get("msg") or None
                           )


#@app.route("/my_info", methods=["GET"])
#@auth_required
#def my_info():
#    return render_template("my_info.html")


@app.route("/about/<path:path>")
def about_path(path):
    return redirect(f"/help/{path}")


@app.route("/help/<path:path>", methods=["GET"])
@auth_desired
def help_path(path):
    try:
        to_render=safe_join("help/", f"{path}.html")
        #debug(to_render)
        return render_template(to_render)
    except TemplateNotFound:
       abort(404)


@app.route("/help", methods=["GET"])
@auth_desired
def help_home():
    return render_template("help.html")


@app.route("/help/submit_contact", methods=["POST"])
@is_not_banned
def press_inquiry():

    data = [(x, request.form[x]) for x in request.form if x != "formkey"]
    data.append(("username", g.user.username))
    data.append(("email", g.user.email))

    data = sorted(data, key=lambda x: x[0])

    if request.form.get("press"):
        email_template = "email/press.html"
    else:
        email_template = "email/contactform.html"

    try:
        send_mail(environ.get("admin_email"),
                  "Press Submission",
                  render_template(email_template,
                                  data=data
                                  ),
                  plaintext=str(data)
                  )
    except BaseException:
        return render_template(
            "message.html",
            title="Unable to save",
            error="Unable to save your inquiry. Please try again later.")

    return render_template(
        "message.html",
        title="Inquiry submitted",
        message=f"Your inquiry has been sent to {app.config['SITE_NAME']} staff.")


@app.route("/info/image_hosts", methods=["GET"])
def info_image_hosts():

    sites = g.db.query(Domain).filter_by(
        show_thumbnail=True).order_by(
        Domain.domain.asc()).all()

    sites = [x.domain for x in sites]

    text = "\n".join(sites)

    resp = make_response(text)
    resp.mimetype = "text/plain"
    return resp

@app.route("/dismiss_mobile_tip", methods=["POST"])
def dismiss_mobile_tip():

    session["tooltip_last_dismissed"]=g.timestamp
    session.modified=True

    return "", 204

@app.route("/help/docs")
@cache.memoize(10)
def docs():

    class Doc():

        def __init__(self, **kwargs):
            for entry in kwargs:
                self.__dict__[entry]=kwargs[entry]

        def __str__(self):

            return f"{self.method.upper()} {self.endpoint}\n\n{self.docstring}"

        @property
        def docstring(self):
            return self.target_function.__doc__ if self.target_function.__doc__ else "[doc pending]"

        @property
        def docstring_html(self):
            return mistletoe.markdown(self.docstring)

        @property
        def resource(self):
            return self.endpoint.split('/')[1]

        @property
        def frag(self):
            tail=self.endpoint.replace('/','_')
            tail=tail.replace("<","")
            tail=tail.replace(">","")
            return f"{self.method.lower()}{tail}"
        
        

    docs=[]

    for rule in app.url_map.iter_rules():

        if not rule.rule.startswith("/api/v2/"):
            continue

        endpoint=rule.rule.split("/api/v2")[1]

        for method in rule.methods:
            if method not in ["OPTIONS","HEAD"]:
                break

        new_doc=Doc(
            method=method,
            endpoint=endpoint,
            target_function=app.view_functions[rule.endpoint]
            )

        docs.append(new_doc)

    method_order=["POST", "GET", "PATCH", "PUT", "DELETE"]

    docs.sort(key=lambda x: (x.endpoint, method_order.index(x.method)))

    fulldocs={}

    for doc in docs:
        if doc.resource not in fulldocs:
            fulldocs[doc.resource]=[doc]
        else:
            fulldocs[doc.resource].append(doc)

    return render_template("docs.html", docs=fulldocs, v=None)


@app.get("/favicon.ico")
@cf_cache
def get_favicon_ico():
    return redirect(app.config["IMG_URL_FAVICON"])
