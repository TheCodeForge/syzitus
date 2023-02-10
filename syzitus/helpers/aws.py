from boto3 import client as AWSClient
import requests
from os import environ, remove
from piexif import remove as exif_remove
import time
from urllib.parse import urlparse
from PIL import Image
from imagehash import phash
from sqlalchemy import func
from os import remove
from io import BytesIO

from .base36 import hex2bin

from syzitus.classes.images import BadPic
from syzitus.__main__ import app, db_session, debug

BUCKET = environ.get("S3_BUCKET_NAME",'i.syzitus.com').lstrip().rstrip()
CF_KEY = environ.get("CLOUDFLARE_KEY",'').lstrip().rstrip()
CF_ZONE = environ.get("CLOUDFLARE_ZONE",'').lstrip().rstrip()

# setup AWS connection
S3 = AWSClient("s3",
                  aws_access_key_id=environ.get(
                      "AWS_ACCESS_KEY_ID",'').lstrip().rstrip(),
                  aws_secret_access_key=environ.get(
                      "AWS_SECRET_ACCESS_KEY",'').lstrip().rstrip()
                  )

def check_phash(db, file):

    i=Image.open(file)

    return db.query(BadPic).filter(
        func.levenshtein(
            BadPic.phash,
            hex2bin(str(phash(i)))
            ) < 10
        ).first()


def upload_from_url(name, url):

    #print('upload from url')

    x = requests.get(url)

    #print('got content')

    tempname = name.replace("/", "_")

    with open(tempname, "wb") as file:
        for chunk in x.iter_content(1024):
            file.write(chunk)

    if tempname.split('.')[-1] in ['jpg', 'jpeg']:
        exif_remove(tempname)

    S3.upload_file(tempname,
                   Bucket=BUCKET,
                   Key=name,
                   ExtraArgs={'ACL': 'public-read',
                              "ContentType": "image/png",
                              "StorageClass": "INTELLIGENT_TIERING"
                              }
                   )

    remove(tempname)


def crop_and_resize(img, resize):

    i = img

    # get constraining dimension
    org_ratio = i.width / i.height
    new_ratio = resize[0] / resize[1]

    if new_ratio > org_ratio:
        crop_height = int(i.width / new_ratio)
        box = (0, (i.height // 2) - (crop_height // 2),
               i.width, (i.height // 2) + (crop_height // 2))
    else:
        crop_width = int(new_ratio * i.height)
        box = ((i.width // 2) - (crop_width // 2), 0,
               (i.width // 2) + (crop_width // 2), i.height)

    return i.resize(resize, box=box)


def upload_file(name, file, resize=None):

    # temp save for exif stripping
    tempname = name.replace("/", "_")

    file.save(tempname)

    if tempname.split('.')[-1] in ['jpg', 'jpeg']:
        exif_remove(tempname)

    if resize:
        i = Image.open(tempname)
        i = crop_and_resize(i, resize)
        i.save(tempname)

    S3.upload_file(tempname,
                   Bucket=BUCKET,
                   Key=name,
                   ExtraArgs={'ACL': 'public-read',
                              "ContentType": "image/png"
                              }
                   )

    remove(tempname)


def upload_from_file(name, filename, resize=None):

    tempname = name.replace("/", "_")

    if filename.split('.')[-1] in ['jpg', 'jpeg']:
        exif_remove(tempname)

    if resize:
        i = Image.open(tempname)
        i = crop_and_resize(i, resize)
        i.save(tempname)

    S3.upload_file(tempname,
                   Bucket=BUCKET,
                   Key=name,
                   ExtraArgs={'ACL': 'public-read',
                              "ContentType": "image/png"
                              }
                   )

    remove(filename)


def delete_file(name):

    S3.delete_object(Bucket=BUCKET,
                     Key=name)

    # After deleting a file from S3, dump CloudFlare cache

    headers = {"Authorization": f"Bearer {CF_KEY}",
               "Content-Type": "application/json"}
    data = {'files': [f"https://{BUCKET}/{name}"]}
    url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE}/purge_cache"

    x = requests.post(url, headers=headers, json=data)


def check_csam(post):

   debug("obsolete call to check_csam")
   return




def check_csam_url(url, v, delete_content_function):

    debug("obsolete call to check_csam_url")
    return
