from flask import g

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