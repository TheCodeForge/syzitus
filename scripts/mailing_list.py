from sqlalchemy import *

from ruqqus.__main__ import app, db_session
from ruqqus.classes import *
from ruqqus.mail import send_mail
from ruqqus.helpers.get import get_user
from flask import render_template

db=db_session()

title = input("Title: ")
subject = input("Email subject: ")

x = db.query(User).filter(
    User.is_activated==True,
    #or_(
    #    classes.user.User.is_banned==0, 
    #    classes.user.User.unban_utc>0
    #    ),
    User.is_deleted==False,
    User.email!=None,
    User.mfa_secret != None)
total=x.count()
print(f"total mail to send: {total}")

input("press enter to continue")

i=0
unable=0
success=0

for user in x.order_by(User.id.asc()).all():
#for user in [get_user('captainmeta4', nSession=db)]:
    i+=1
    # for user in db.query(classes.user.User).filter_by(id=7).all():

    try:
        with app.app_context():
            html = render_template(
                "email/mailing.html",
                title=title,
                user=user
            )

        send_mail(
            to_address=user.email,
            subject=subject,
            html=html
        )

        print(f"{i}/{total} [{user.id}] @{user.username}")
        success+=1
    except BaseException:
        print(f"{i}/{total} unable - [{user.id}] @{user.username}")
        unable+=1

db.close()
        
print("all done")
print(f"attempt - {total}")
print(f"success - {success}")
print(f"failure - {unable}")
