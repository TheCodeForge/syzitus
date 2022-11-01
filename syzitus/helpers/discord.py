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
def discord_log_event(action, target_user, admin_user, reason=None):
    
    channel_id=CHANNELS['log']
    url=f"{DISCORD_ENDPOINT}/channels/{channel_id}/messages"
    headers={
        "Authorization": f"Bot {app.config['DISCORD_BOT_TOKEN']}"
    }
    data={
        "embeds":[
            {
                "title": f"{action} @{target_user.username}",
                "url": f"https://{app.config['SERVER_NAME']}{target_user.permalink}",
                "color": int(app.config["COLOR_PRIMARY"], 16),
                "author": {
                    "name": admin_user.username,
                    "icon_url": admin_user.profile_url
                    #"url": f"https://{app.config['SERVER_NAME']}{admin_user.permalink}"
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