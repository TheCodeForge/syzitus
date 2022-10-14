import time
from flask import *
from sqlalchemy import *

from ruqqus.helpers.wrappers import *
from ruqqus.helpers.get import *

from ruqqus.__main__ import app, cache
from ruqqus.classes.boards import Board


@app.route("/api/v1/guild/<boardname>", methods=["GET"])
@auth_desired
@api("read")
def guild_info(v, boardname):
    guild = get_guild(boardname)

    return jsonify(guild.json)


@app.route("/api/v1/user/<username>", methods=["GET"])
@auth_desired
@api("read")
def user_info(v, username):

    user = get_user(username, v=v)
    return jsonify(user.json)
