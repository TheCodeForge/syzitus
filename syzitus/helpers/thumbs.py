from requests import get as requests_get
from os import remove
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from PIL import Image as PILimage
from flask import g
from io import BytesIO
from time import sleep

from .get import *
from .aws import upload_from_file
from syzitus.classes import Submission, SubmissionAux
from syzitus.__main__ import app, db_session, debug

def expand_url(post_url, fragment_url):

    # convert src into full url
    if fragment_url.startswith("https://"):
        return fragment_url
    elif fragment_url.startswith("http://"):
        return f"https://{fragment_url.split('http://')[1]}"
    elif fragment_url.startswith('//'):
        return f"https:{fragment_url}"
    elif fragment_url.startswith('/'):
        parsed_url = urlparse(post_url)
        return f"https://{parsed_url.netloc}{fragment_url}"
    else:
        return f"{post_url}{'/' if not post_url.endswith('/') else ''}{fragment_url}"

def thumbnail_thread(pid):

    db = db_session()

    post = db.query(Submission).filter_by(id=base36decode(pid)).first()
    if not post:
        # account for possible follower lag
        sleep(60)
        post = db.query(Submission).filter_by(id=base36decode(pid)).first()


    #First, determine the url to go off of
    #This is the embed url, if the post is allowed to be embedded, and the embedded url starts with http

    # if post.domain_obj and post.domain_obj.show_thumbnail:
    #     debug("Post is likely hosted image")
    #     fetch_url=post.url
    # elif post.embed_url and post.embed_url.startswith("https://"):
    #     debug("Post is likely embedded content")
    #     fetch_url=post.embed_url
    # else:
    #     debug("Post is article content")
    #     fetch_url=post.url

    fetch_url=post.url



    #get the content

    #mimic chrome browser agent
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 Safari/537.36"}

    try:
        debug(f"loading {fetch_url}")
        x=requests_get(fetch_url, headers=headers)
    except:
        debug(f"unable to connect to {fetch_url}")
        db.close()
        return False, "Unable to connect to source"

    if x.status_code != 200:
        db.close()
        return False, f"Source returned status {x.status_code}."
    
    #detect if there was a redirect
    # requested_domain = post.domain
    # fetched_domain = urlparse(x.url).netloc
    
    # if requested_domain.lower() != fetched_domain.lower() and not post.domain_obj:
    #     post.is_banned=True
    #     post.ban_reason="No redirection services"
    #     g.db.add(post)
    #     g.db.add(post.submission_aux)
    #     g.db.commit()
    #     return

    #if content is image, stick with that. Otherwise, parse html.

    if x.headers.get("Content-Type","").startswith("text/html"):
        #parse html, find image, load image
        soup=BeautifulSoup(x.content, 'html.parser')
        #parse html

        #first, set metadata
        try:
            meta_title=soup.find('title')
            if meta_title:
                post.submission_aux.meta_title=str(meta_title.string)[0:500]

            meta_desc = soup.find('meta', attrs={"name":"description"})
            if meta_desc:
                post.submission_aux.meta_description=meta_desc['content'][0:1000]

            if meta_title or meta_desc:
                db.add(post.submission_aux)
                db.commit()

        except Exception as e:
            print(f"Error while parsing for metadata: {e}")
            pass

        #create list of urls to check
        thumb_candidate_urls=[]

        #iterate through desired meta tags
        meta_tags = [
            f"{app.config['SITE_NAME'].lower()}:thumbnail",
            "twitter:image",
            "og:image",
            "thumbnail"
            ]

        for tag_name in meta_tags:
            
            debug(f"Looking for meta tag: {tag_name}")


            tag = soup.find(
                'meta', 
                attrs={
                    "name": tag_name, 
                    "content": True
                    }
                )
            if not tag:
                tag = soup.find(
                    'meta',
                    attrs={
                        'property': tag_name,
                        'content': True
                        }
                    )
            if tag:
                thumb_candidate_urls.append(expand_url(post.url, tag['content']))

        #parse html doc for <img> elements
        for tag in soup.find_all("img", attrs={'src':True}):
            thumb_candidate_urls.append(expand_url(post.url, tag['src']))


        #now we have a list of candidate urls to try
        for url in thumb_candidate_urls:
            debug(f"Trying url {url}")

            try:
                image_req=requests_get(url, headers=headers)
            except:
                debug(f"Unable to connect to candidate url {url}")
                continue

            if image_req.status_code >= 400:
                debug(f"status code {x.status_code}")
                continue

            if not image_req.headers.get("Content-Type","").startswith("image/"):
                debug(f'bad type {image_req.headers.get("Content-Type","")}, try next')
                continue

            if image_req.headers.get("Content-Type","").startswith("image/svg"):
                debug("svg, try next")
                continue

            image = PILimage.open(BytesIO(image_req.content))
            if image.width < 30 or image.height < 30:
                debug("image too small, next")
                continue

            debug("Image is good, upload it")
            break

        else:
            #getting here means we are out of candidate urls (or there never were any)
            debug("Unable to find image")
            db.close()
            return False, "No usable images"




    elif x.headers.get("Content-Type","").startswith("image/"):
        #image is originally loaded fetch_url
        debug("post url is direct image")
        image_req=x
        image = PILimage.open(BytesIO(x.content))

    else:

        debug(f'Unknown content type {x.headers.get("Content-Type")}')
        db.close()
        return False, f'Unknown content type {x.headers.get("Content-Type")} for submitted content'


    debug(f"Have image, uploading")

    name = f"posts/{post.base36id}/thumb.png"
    tempname = name.replace("/", "_")

    with open(tempname, "wb") as file:
        for chunk in image_req.iter_content(1024):
            file.write(chunk)

    upload_from_file(name, tempname, resize=(98, 68))
    post.has_thumb = True
    db.add(post)

    db.commit()

    db.close()

    try:
        remove(tempname)
    except FileNotFoundError:
        pass

    return True
