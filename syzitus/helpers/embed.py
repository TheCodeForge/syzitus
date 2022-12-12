from re import compile as re_compile, match as re_match
from urllib.parse import urlparse, parse_qs
import requests
from os import environ
from bs4 import BeautifulSoup
#import json

from .get import *

from syzitus.__main__ import app

youtube_regex = re_compile("^.*(youtube\.com|youtu\.be)/(embed/|shorts/|watch\?v=)?([\w-]*)")

regexified_server_name=app.config['SERVER_NAME'].replace('.','\.')
ruqqus_regex = re_compile(f"^https?://.*{regexified_server_name}/\+\w+/post/(\w+)(/[a-zA-Z0-9_-]+/(\w+))?")

twitter_regex=re_compile("/status/(\d+)")

#rumble_regex=re_compile("/embed/(\w+)-/")

FACEBOOK_TOKEN=environ.get("FACEBOOK_TOKEN","").lstrip().rstrip()



def youtube_embed(url):

    yt_id = re_match(youtube_regex, url).group(3)

    # if not yt_id or len(yt_id) != 11:
    #     return "error"

    x = urlparse(url)
    params = parse_qs(x.query)
    t = params.get('t', params.get('start', [0]))[0]
    if t:
        return f"https://youtube.com/embed/{yt_id}?start={t}"
    else:
        return f"https://youtube.com/embed/{yt_id}"


def ruqqus_embed(url):

    matches = re_match(ruqqus_regex, url)

    post_id = matches.group(1)
    comment_id = matches.group(3)

    if comment_id:
        return f"/embed/comment/{comment_id}"
    else:
        return f"/embed/post/{post_id}"


# def bitchute_embed(url):

#     return url.replace("/video/", "/embed/")

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


# def rumble_embed(url):
    
#     #print(url)
#     headers={
#         "User-Agent":"Rumble embedder for Ruqqus"
#     }
#     r=requests.get(url, headers=headers)
    
#     soup=BeautifulSoup(r.content, features="html.parser")
    
#     script=soup.find("script", attrs={"type":"application/ld+json"})
    
#     return json.loads(script.string)[0]['embedUrl']
