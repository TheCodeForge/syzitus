import time
from flask import *
from sqlalchemy import *

from syzitus.helpers.wrappers import *
from syzitus.helpers.get import *

from syzitus.__main__ import app, cache
from syzitus.classes.boards import Board


@app.route("/api/v1/guild/<boardname>", methods=["GET"])
@auth_desired
@api("read")
def guild_info(boardname):
    guild = get_guild(boardname)

    return jsonify(guild.json)


@app.route("/api/v1/user/<username>", methods=["GET"])
@auth_desired
@api("read")
def user_info(username):

    user = get_user(username)
    return jsonify(user.json)
