from os import environ
import requests
import threading

DOMAIN=environ.get("SERVER_NAME",'ruqqus.com').lstrip().rstrip()

SERVER_ID = environ.get("DISCORD_SERVER_ID",'').rstrip()
CLIENT_ID = environ.get("DISCORD_CLIENT_ID",'').rstrip()
CLIENT_SECRET = environ.get("DISCORD_CLIENT_SECRET",'').rstrip()
DISCORD_ENDPOINT = "https://discordapp.com/api"
BOT_TOKEN = environ.get("DISCORD_BOT_TOKEN",'').rstrip()


ROLES={
    "banned":  "700694275905814591",
    "member":  "727255602648186970",
    "nick":    "730493039176450170",
    "linked":  "779872346219610123",
    "realid":  "779904545194508290",
    "premium": "780084870176702484",
}

CHANNELS={
    "log": "599260022492495882"
}

def discord_wrap(f):

    def wrapper(*args, **kwargs):

        if not CLIENT_ID:
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

        if not CLIENT_ID:
            return

        thread=threading.Thread(target=f, args=args, kwargs=kwargs)
        thread.start()

    wrapper.__name__=f.__name__
    return wrapper

@req_wrap
def discord_log_event(action, target_user, admin_user, reason=None):
    
    channel_id=CHANNELS['log']
    url=f"{DISCORD_ENDPOINT}/channels/{channel_id}/messages"
    headers={
        "Authorization": f"Bot {BOT_TOKEN}"
    }
    data={
        "embeds":[
            {
                "title": f"{action} @{target_user.username}",
                "url": f"https://{DOMAIN}{target_user.permalink}",
                "color": 8415957,
                "author": {
                    "name": admin_user.username,
                    "icon_url": admin_user.profile_url
                    #"url": f"https://{DOMAIN}{admin_user.permalink}"
                },
                "fields": [
                    {
                        "name": "User",
                        "value": f"@{target_user.username}",
                        "inline": True
                    },
                    {
                        "name": "Reason",
                        "value": reason,
                        "inline": True
                    },
                    {
                        "name": "Admin",
                        "value": f"@{admin_user.username}",
                        "inline": True
                    }
                ]
            }
        ]
    }
    x=requests.post(url, headers=headers, json=data)
#    print(x.status_code, x.content)


@discord_wrap
def add_role(user, role_name):
    role_id = ROLES[role_name]
    url = f"{DISCORD_ENDPOINT}/guilds/{SERVER_ID}/members/{user.discord_id}/roles/{role_id}"
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    requests.put(url, headers=headers)

@discord_wrap
def delete_role(user, role_name):
    role_id = ROLES[role_name]
    url = f"{DISCORD_ENDPOINT}/guilds/{SERVER_ID}/members/{user.discord_id}/roles/{role_id}"
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    requests.delete(url, headers=headers)

@discord_wrap
def remove_user(user):
    url=f"{DISCORD_ENDPOINT}/guilds/{SERVER_ID}/members/{user.discord_id}"
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    requests.delete(url, headers=headers)

@discord_wrap
def set_nick(user, nick):
    url=f"{DISCORD_ENDPOINT}/guilds/{SERVER_ID}/members/{user.discord_id}"
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    data={"nick": nick}
    requests.patch(url, headers=headers, json=data)