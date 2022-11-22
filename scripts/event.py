from syzitus.__main__ import *
from syzitus.classes import *
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