from ruqqus.__main__ import *
from ruqqus.classes import *
from ruqqus.helpers.thumbs import thumbnail_thread

from sqlalchemy.orm import *

db = db_session()

for post in db.query(Submission).options(lazyload('*'), joinedload(Submission.submission_aux)).filter_by(
        domain_ref=1, is_deleted=False, is_banned=False, has_thumb=False).order_by(Submission.id.asc()).all():
    try:
        thumbnail_thread(post.base36id)
        print(f"{post.base36id} - {post.title}")
    except BaseException:
        print(f"ERROR: {post.base36id} - {post.title}")

db.close()
