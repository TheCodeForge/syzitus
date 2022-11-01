from os import environ
import requests
import pprint

from flask import *

from syzitus.classes import *
from syzitus.helpers.wrappers import *
from syzitus.helpers.security import *
from syzitus.helpers.discord import add_role, delete_role
from syzitus.__main__ import app


WELCOME_CHANNEL="775132151498407961"



@app.route("/guilded", methods=["GET"])
def guilded_server():
    return redirect("https://www.guilded.gg/i/VEvjaraE")


@app.route("/discord", methods=["GET"])
@auth_required
def join_discord():

    now=int(time.time())

    state=generate_hash(f"{now}+{g.user.id}+discord")

    state=f"{now}.{state}"

    return redirect(f"https://discord.com/api/oauth2/authorize?client_id={app.config['DISCORD_CLIENT_ID']}&redirect_uri=https%3A%2F%2F{app.config['SERVER_NAME']}%2Fdiscord_redirect&response_type=code&scope=identify%20guilds.join&state={state}")

@app.route("/discord_redirect", methods=["GET"])
@auth_required
def discord_redirect():


    #validate state
    now=int(time.time())
    state=request.args.get('state','').split('.')

    timestamp=state[0]

    state=state[1]

    if int(timestamp) < now-600:
        abort(400)

    if not validate_hash(f"{timestamp}+{g.user.id}+discord", state):
        abort(400)

    #get discord token
    code = request.args.get("code","")
    if not code:
        abort(400)

    data={
        "client_id":app.config['DISCORD_CLIENT_ID'],
        'client_secret': app.config['DISCORD_CLIENT_SECRET'],
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': f"https://{app.config['SERVER_NAME']}/discord_redirect",
        'scope': 'identify guilds.join'
    }
    headers={
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    url="https://discord.com/api/oauth2/token"

    x=requests.post(url, headers=headers, data=data)

    x=x.json()


    try:
        token=x["access_token"]
    except KeyError:
        abort(403)


    #get user ID
    url="https://discord.com/api/users/@me"
    headers={
        'Authorization': f"Bearer {token}"
    }
    x=requests.get(url, headers=headers)

    x=x.json()



    #add user to discord
    headers={
        'Authorization': f"Bot {app.config['DISCORD_BOT_TOKEN']}",
        'Content-Type': "application/json"
    }

    #remove existing user if applicable
    if g.user.discord_id and g.user.discord_id != x['id']:
        url=f"https://discord.com/api/guilds/{app.config['DISCORD_SERVER_ID']}/members/{g.user.discord_id}"
        requests.delete(url, headers=headers)

    if g.db.query(User).filter(User.id!=g.user.id, User.discord_id==x["id"]).first():
        return render_template("message.html", title="Discord account already linked.", error="That Discord account is already in use by another user.", v=v)

    g.user.discord_id=x["id"]
    g.db.add(v)
    g.db.commit()

    url=f"https://discord.com/api/guilds/{app.config['DISCORD_SERVER_ID']}/members/{x['id']}"

    name=g.user.username
    if g.user.real_id:
        name+= f" | {g.user.real_id}"

    data={
        "access_token":token,
        "nick":name,
    }

    x=requests.put(url, headers=headers, json=data)

    if x.status_code in [201, 204]:
                        
        if g.user.is_banned and g.user.unban_utc==0:
            add_role(g.user,"banned")

        if g.user.has_premium:
            add_role(g.user,"premium")

    else:
        return jsonify(x.json())

    #check on if they are already there
    #print(x.status_code)

    if x.status_code==204:

        if g.user.real_id:
            add_role(g.user, "realid")


        url=f"https://discord.com/api/guilds/{app.config['DISCORD_SERVER_ID']}/members/{g.user.discord_id}"
        data={
            "nick": name
        }

        req=requests.patch(url, headers=headers, json=data)

        #print(req.status_code)
        #print(url)

    return redirect(f"https://discord.com/channels/{app.config['DISCORD_SERVER_ID']}/{WELCOME_CHANNEL}")