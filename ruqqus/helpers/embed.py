import re
from urllib.parse import *
import requests
from os import environ
from flask import *
from bs4 import BeautifulSoup
import json
from ruqqus.__main__ import app
from .get import *

youtube_regex = re.compile(
    "^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*")

ruqqus_regex = re.compile("^https?://.*ruqqus\.com/\+\w+/post/(\w+)(/[a-zA-Z0-9_-]+/(\w+))?")

twitter_regex=re.compile("/status/(\d+)")

rumble_regex=re.compile("/embed/(\w+)-/")

FACEBOOK_TOKEN=environ.get("FACEBOOK_TOKEN","").lstrip().rstrip()



def youtube_embed(url):

    try:
        yt_id = re.match(youtube_regex, url).group(2)
    except AttributeError:
        return "error"

    if not yt_id or len(yt_id) != 11:
        return "error"

    x = urlparse(url)
    params = parse_qs(x.query)
    t = params.get('t', params.get('start', [0]))[0]
    if t:
        return f"https://youtube.com/embed/{yt_id}?start={t}"
    else:
        return f"https://youtube.com/embed/{yt_id}"


# def ruqqus_embed(url):

#     print(f'embedding {url}')

#     matches = re.match(ruqqus_regex, url)

#     post_id = matches.group(1)
#     comment_id = matches.group(3)

#     print(post_id, comment_id)

#     if comment_id:
#         return f"https://{app.config['SERVER_NAME']}/embed/comment/{comment_id}"
#     else:
#         return render_template(
#             "site_embeds/ruqqus_post.html", 
#             b36id=post_id,
#             v=g.v
#             )


def bitchute_embed(url):

    return url.replace("/video/", "/embed/")

def twitter_embed(url):


    oembed_url=f"https://publish.twitter.com/oembed"
    params={
        "url":url,
        "omit_script":"t"
        }
    x=requests.get(oembed_url, params=params)

    return x.json()["html"]

def instagram_embed(url):

    oembed_url=f"https://graph.facebook.com/v9.0/instagram_oembed"
    params={
        "url":url,
        "access_token":FACEBOOK_TOKEN,
        "omitscript":'true'
    }

    headers={
        "User-Agent":"Instagram embedder for Ruqqus"
    }

    x=requests.get(oembed_url, params=params, headers=headers)

    return x.json()["html"]


def rumble_embed(url):
    
    #print(url)
    headers={
        "User-Agent":"Rumble embedder for Ruqqus"
    }
    r=requests.get(url, headers=headers)
    
    soup=BeautifulSoup(r.content, features="html.parser")
    
    script=soup.find("script", attrs={"type":"application/ld+json"})
    
    return json.loads(script.string)[0]['embedUrl']
