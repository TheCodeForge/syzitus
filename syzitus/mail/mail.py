from os import environ
import requests
from flask import g, render_template, jsonify, abort
from urllib.parse import quote

from syzitus.helpers.security import generate_hash, validate_hash
from syzitus.helpers.wrappers import *
from syzitus.classes import *
from syzitus.__main__ import app


def send_mail(to_address, subject, html, plaintext=None, files={},
              from_address=f"{app.config['SITE_NAME']} <noreply@mail.{app.config['SERVER_NAME']}>"):

    if not environ.get("MAILGUN_KEY"):
        debug("Cannot send mail - no mailgun key")
        return


    url = f"https://api.mailgun.net/v3/mail.{app.config['SERVER_NAME']}/messages"

    data = {"from": from_address,
            "to": [to_address],
            "subject": subject,
            "text": plaintext,
            "html": html,
            }

    x= requests.post(
        url,
        auth=(
            "api", environ.get("MAILGUN_KEY").lstrip().rstrip()
            ),
        data=data,
        files=[("attachment", (k, files[k])) for k in files]
        )

   # debug([g.user.username, url, x.status_code, x.content])
    return x


def send_verification_email(user, email=None):

    email = email or user.email

    url = f"https://{app.config['SERVER_NAME']}/activate"

    token = generate_hash(f"{email}+{user.id}+{g.timestamp}")
    params = f"?email={quote(email)}&id={user.id}&time={g.timestamp}&token={token}"

    link = url + params

    send_mail(to_address=email,
              html=render_template(
                "email/email_verify.html",
                action_url=link
                ),
              subject=f"Verify your {app.config['SITE_NAME']} account email."
              )


@app.route("/api/verify_email", methods=["POST"])
@is_not_banned
def api_verify_email():

    send_verification_email(g.user)

    return jsonify({"message":"Verification email sent! Please check your inbox."})


@app.route("/activate", methods=["GET"])
@auth_desired
def activate():

    email = request.args.get("email", "")
    id = request.args.get("id", "")
    timestamp = int(request.args.get("time", "0"))
    token = request.args.get("token", "")

    if g.timestamp - timestamp > 3600:
        return render_template(
            "message.html", 
            title="Verification link expired.",
            message="That link has expired. Visit your settings to send yourself another verification email.",
            icon="fa-hourglass-end"
            ), 410

    if not validate_hash(f"{email}+{id}+{timestamp}", token):
        abort(403)

    user = g.db.query(User).filter_by(id=id).first()
    if not user:
        abort(404)

    if user.is_activated and user.email == email:
        return render_template(
            "message_success.html",
            title="Email already verified.", 
            message="Email already verified."
            ), 404

    user.email = email
    user.is_activated = True

    user.refresh_selfset_badges()

    g.db.add(user)
    g.db.commit()

    return render_template(
        "message.html", 
        title="Email verified.", 
        message=f"Your email {email} has been verified. Thank you.",
        icon="fa-envelope-open")
