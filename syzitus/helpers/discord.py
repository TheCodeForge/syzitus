import requests
import threading
from syzitus.__main__ import app, debug

DISCORD_ENDPOINT = "https://discordapp.com/api"

def discord_wrap(f):

    def wrapper(*args, **kwargs):

        if not app.config['DISCORD_CLIENT_ID']:
            return

        user=args[0]
        if not user.discord_id:
            return


        thread=threading.Thread(target=f, args=args, kwargs=kwargs)
        thread.start()

    wrapper.__name__=f.__name__
    return wrapper

def req_wrap(f):

    def wrapper(*args, **kwargs):

        if not app.config['DISCORD_CLIENT_ID']:
            return

        thread=threading.Thread(target=f, args=args, kwargs=kwargs)
        thread.start()

    wrapper.__name__=f.__name__
    return wrapper

@req_wrap
def discord_log_event(action, target, user, reason=None, admin_action=False):

    
    channel_id=app.config["DISCORD_CHANNEL_IDS"]["log"]
    url=f"{DISCORD_ENDPOINT}/channels/{channel_id}/messages"
    headers={
        "Authorization": f"Bot {app.config['DISCORD_BOT_TOKEN']}"
    }

    if target.fullname.startswith("t1_"):
        title_text = f"{action} @{target.username}"
    elif target.fullname.startswith("t2_"):
        title_text = f"{action} Post"
    elif target.fullname.startswith("t3_"):
        title_text = f"{action} Comment"
    elif target.fullname.startsiwth("t4_"):
        title_text = f"{action} +{target.name}"


    if user:
        data={
            "embeds":[
                {
                    "title": title_text,
                    "url": f"https://{app.config['SERVER_NAME']}{target.permalink}",
                    "color": int(app.config["COLOR_PRIMARY"], 16),
                    "author": {
                        "name": user.username,
                        "icon_url": user.profile_url
                    },
                    "fields": [
                        {
                            "name": "Reason",
                            "value": reason or "null",
                            "inline": True
                        },
                        {
                            "name": "Admin" if admin_action else "User",
                            "value": f"@{user.username}",
                            "inline": True
                        }
                    ]
                }
            ]
        }
    else:
        data={
            "embeds":[
                {
                    "title": title_text,
                    "url": f"https://{app.config['SERVER_NAME']}{target.permalink}",
                    "color": int(app.config["COLOR_PRIMARY"], 16),
                    "author": {
                        "name": app.config['SITE_NAME'].lower(),
                        "icon_url": f"https://{app.config['SERVER_NAME']}{app.config['IMG_URL_FAVICON']}"
                    },
                    "fields": [
                        {
                            "name": "Reason",
                            "value": reason or "null",
                            "inline": True
                        },
                        {
                            "name": "Admin",
                            "value": f"@{app.config['SITE_NAME'].lower()}",
                            "inline": True
                        }
                    ]
                }
            ]
        }

    #debug(data)
    x=requests.post(url, headers=headers, json=data)
    #debug(x.status_code)
    #debug(x.content)


@discord_wrap
def add_role(user, role_name):
    role_id = app.config['DISCORD_ROLE_IDS'][role_name]
    url = f"{DISCORD_ENDPOINT}/guilds/{app.config['DISCORD_SERVER_ID']}/members/{user.discord_id}/roles/{role_id}"
    headers = {"Authorization": f"Bot {app.config['DISCORD_BOT_TOKEN']}"}
    requests.put(url, headers=headers)

@discord_wrap
def delete_role(user, role_name):
    role_id = app.config['DISCORD_ROLE_IDS'][role_name]
    url = f"{DISCORD_ENDPOINT}/guilds/{app.config['DISCORD_SERVER_ID']}/members/{user.discord_id}/roles/{role_id}"
    headers = {"Authorization": f"Bot {app.config['DISCORD_BOT_TOKEN']}"}
    requests.delete(url, headers=headers)

@discord_wrap
def remove_user(user):
    url=f"{DISCORD_ENDPOINT}/guilds/{app.config['DISCORD_SERVER_ID']}/members/{user.discord_id}"
    headers = {"Authorization": f"Bot {app.config['DISCORD_BOT_TOKEN']}"}
    requests.delete(url, headers=headers)

@discord_wrap
def set_nick(user, nick):
    url=f"{DISCORD_ENDPOINT}/guilds/{app.config['DISCORD_SERVER_ID']}/members/{user.discord_id}"
    headers = {"Authorization": f"Bot {app.config['DISCORD_BOT_TOKEN']}"}
    data={"nick": nick}
    requests.patch(url, headers=headers, json=data)