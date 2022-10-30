import mistletoe

from ruqqus.classes import *
from flask import g
from .markdown import *
from .sanitize import *


def send_notification(user, text):

    with CustomRenderer() as renderer:
        text_html = renderer.render(mistletoe.Document(text))

    text_html = sanitize(text_html, linkgen=True)#, noimages=True)

    new_comment = Comment(author_id=1,
                          # body=text,
                          # body_html=text_html,
                          parent_submission=None,
                          distinguish_level=6,
                          is_offensive=False
                          )
    g.db.add(new_comment)

    g.db.flush()

    new_aux = CommentAux(id=new_comment.id,
                         body=text,
                         body_html=text_html
                         )
    g.db.add(new_aux)
    g.db.commit()
    # g.db.begin()

    notif = Notification(comment_id=new_comment.id,
                         user_id=user.id)
    g.db.add(notif)
    g.db.commit()
