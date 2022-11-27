from syzitus.__main__ import *
from syzitus.classes import *
from syzitus.helpers.alerts import send_notification
import time

db = db_session()

#guild IDs
xmas_id = db.query(Board).filter_by(name="Team_Christmas").first().id
hwen_id = db.query(Board).filter_by(name="Team_Halloween").first().id

#assemble list of Christmas users
xmas_users = db.query(User).filter(
	User.id.op('%')(2)==1,
	or_(
		User.id.in_(
			select(Submission.author_id).filter(Submission.board_id==xmas_id)
			),
		User.id.in_(
			select(Comment.author_id).filter(
				Comment.parent_submission.in_(
					select(Submission.id).filter(Submission.board_id==xmas_id)
					)
				)
			)
		)
	)

print(list(xmas_users))

#assemble list of Christmas users
hwen_users = db.query(User).filter(
	User.id.op('%')(2)==0,
	or_(
		User.id.in_(
			select(Submission.author_id).filter(Submission.board_id==hwen_id)
			),
		User.id.in_(
			select(Comment.author_id).filter(
				Comment.parent_submission.in_(
					select(Submission.id).filter(Submission.board_id==hwen_id)
					)
				)
			)
		)
	)

print(list(hwen_users))


for user in xmas_users:
	if not user.has_badge(18):
		new_badge = Badge(
			user_id=user.id,
            badge_id=18,
            created_utc=int(time.time())
            )

	  	text = f"""
You have recieved the following badge for your participation in the defense of Christmas:
\n\n![]({new_badge.path})
\n\n{new_badge.name}
"""

    	send_notification(user, text)

for user in hwen_users:
	if not user.has_badge(17):
		new_badge = Badge(
			user_id=user.id,
            badge_id=17,
            created_utc=int(time.time())
            )

		text = f"""
You have recieved the following badge for your participation in the invasion by Halloween:
\n\n![]({new_badge.path})
\n\n{new_badge.name}
"""

    	send_notification(user, text)

