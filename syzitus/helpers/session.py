from flask import *
import time
from .security import *


def session_over18(board):

    now = int(time.time())

    return session.get('over_18', {}).get(board.base36id, 0) >= now


def session_isnsfl(board):

    now = int(time.time())

    return session.get('show_nsfl', {}).get(board.base36id, 0) >= now


def make_logged_out_formkey():

    s = f"{g.timestamp}+{session['session_id']}"

    return generate_hash(s)