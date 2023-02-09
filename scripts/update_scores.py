from syzitus.__main__ import *
from syzitus.classes import *
import time

db = db_session()

now=int(time.time())

for post in db.query(Submission).options(lazyload('*')).filter_by(scores_last_updated_utc=0).yield_per(100).all():
	post.update_scores()
	db.add(post)

db.commit()