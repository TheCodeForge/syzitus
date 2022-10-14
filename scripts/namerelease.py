from ruqqus.__main__ import *
from ruqqus.classes import *
import time

db = db_session()

protected_terms = [
    "ruqqus",
    "captain",
    "meta4",
    "gabe",
    "sublime",
    "slime"
]

protected_terms = [i.lower() for i in protected_terms]

now = (int)

deleted_accounts = db.query(User).filter_by(is_deleted=True)

print()

displayed_post_owners = db.query(
    Submission.author_id).filter_by(
        is_deleted=False,
    is_banned=False).distinct().subquery()
displayed_comment_owners = db.query(
    Comment.author_id
    ).filter_by(
    is_deleted=False,
    is_banned=False).distinct().subquery()

modaction_owners = db.query(
	ModAction.user_id).distinct().subquery()

banned_accounts = db.query(User).filter(
        User.is_banned > 0,
        User.unban_utc==0,
        User.id.notin_(displayed_post_owners),
        User.id.notin_(displayed_comment_owners),
        User.id.notin_(modaction_owners)
        )


accounts = [x for x in deleted_accounts] + [y for y in banned_accounts]

accounts_to_release = []
accounts_to_hold = []
print(f"{len(accounts)} account names are eligible")

for u in accounts:
    if any([x in u.username.lower() for x in protected_terms]):
        accounts_to_hold.append(u)
    else:
        accounts_to_release.append(u)

accounts_to_release.sort(key=lambda x: x.username)
accounts_to_hold.sort(key=lambda x: x.username)

print(f"{len(accounts_to_release)} names to release")
#print(accounts_to_release)

print(f"{len(accounts_to_hold)} names to hold")
#print(accounts_to_hold)

i=0

for account in accounts_to_release:
    i+=1
    account.username=f"$Account_{account.base36id}"
    account.original_username=f"$Account_{account.base36id}"
    db.add(account)
    if not i%100:
        db.flush()

db.flush()
if input(f"{i} names changed. Commit? "):
    db.commit()
else:
    db.rollback()
