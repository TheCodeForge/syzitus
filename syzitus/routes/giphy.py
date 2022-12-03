from flask import g, session, abort, render_template, jsonify
from os import environ
import requests

from syzitus.helpers.wrappers import *

from syzitus.__main__ import app, debug


@app.post("/giphy")
@is_not_banned
def giphy():

    if not app.config["GIPHY_KEY"]:

        return jsonify({"error":"GIPHY not currently configured"}), 501

    url="https://api.giphy.com/v1/gifs/search"

    params={
        "q": request.form.get("searchTerm"),
        "limit": request.form.get("limit", 48),
        'api_key': app.config['GIPHY_KEY']
    }

    debug([url, params])

    return jsonify(requests.get(url, params=params).json())
