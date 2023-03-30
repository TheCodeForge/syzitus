from syzitus.classes.comment import Comment, CommentAux, Notification

def send_notif(user, text):
    text_html = markdown(text)

    #text_html = sanitize(text_html, linkgen=True)#, noimages=True)

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

def per_page(f):

    #wrapper that adjusts the per-page qty depending on premium status and user settings

    def wrapper(*args, **kwargs):

        if g.user and g.user.has_premium:
            g.per_page=max(25, g.user.per_page_preference)
        else:
            g.per_page=25

        resp=f(*args, **kwargs)

        return resp

    wrapper.__name__=f.__name__
    wrapper.__doc__ = f.__doc__
    return wrapper