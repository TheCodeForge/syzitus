from flask import g, session, abort, render_template, jsonify, redirect
from sqlalchemy import func
import time
import threading
import mistletoe
import re

from syzitus.classes import *
from syzitus.helpers.wrappers import *
from syzitus.helpers.security import *
from syzitus.helpers.sanitize import *
from syzitus.helpers.filters import filter_comment_html
from syzitus.helpers.markdown import *
from syzitus.helpers.discord import remove_user, set_nick
from syzitus.helpers.aws import *
from syzitus.mail import *
from .front import frontlist

from syzitus.__main__ import app, cache


valid_username_regex = re.compile("^[a-zA-Z0-9_]{3,25}$")
valid_password_regex = re.compile("^.{8,100}$")


@app.route("/settings/profile", methods=["POST"])
@is_not_banned
def settings_profile_post():

    updated = False

    if request.values.get("over18", g.user.over_18) != g.user.over_18:
        updated = True
        g.user.over_18 = request.values.get("over18", None) == 'true'
        #cache.delete_memoized(User.idlist, g.user)

    if request.values.get("hide_offensive",
                          g.user.hide_offensive) != g.user.hide_offensive:
        updated = True
        g.user.hide_offensive = request.values.get("hide_offensive", None) == 'true'
        #cache.delete_memoized(User.idlist, g.user)
		
    if request.values.get("hide_bot",
                          g.user.hide_bot) != g.user.hide_bot:
        updated = True
        g.user.hide_bot = request.values.get("hide_bot", None) == 'true'
        #cache.delete_memoized(User.idlist, g.user)

    if request.values.get("show_nsfl", g.user.show_nsfl) != g.user.show_nsfl:
        updated = True
        g.user.show_nsfl = request.values.get("show_nsfl", None) == 'true'
        #cache.delete_memoized(User.idlist, g.user)

    if request.values.get("filter_nsfw", g.user.filter_nsfw) != g.user.filter_nsfw:
        updated = True
        g.user.filter_nsfw = not request.values.get("filter_nsfw", None) == 'true'
        #cache.delete_memoized(User.idlist, g.user)

    if request.values.get("private", g.user.is_private) != g.user.is_private:
        updated = True
        g.user.is_private = request.values.get("private", None) == 'true'

    if request.values.get("nofollow", g.user.is_nofollow) != g.user.is_nofollow:
        updated = True
        g.user.is_nofollow = request.values.get("nofollow", None) == 'true'

    # if request.values.get("join_chat", g.user.auto_join_chat) != g.user.auto_join_chat:
    #     updated = True
    #     g.user.auto_join_chat = request.values.get("join_chat", None) == 'true'

    if request.values.get("bio") is not None:
        bio = request.values.get("bio")[0:256]

        bio=preprocess(bio)

        if bio == g.user.bio:
            return jsonify({"error":"You didn't change anything"}), 400


        with CustomRenderer() as renderer:
            bio_html = renderer.render(mistletoe.Document(bio))
        bio_html = sanitize(bio_html, linkgen=True)

        # Run safety filter
        bans = filter_comment_html(bio_html)

        if bans:
            ban = bans[0]
            reason = f"Remove the {ban.domain} link from your bio and try again."
            if ban.reason:
                reason += f" {ban.reason_text}"
                
            #auto ban for digitally malicious content
            if any([x.reason==4 for x in bans]):
                g.user.ban(days=30, reason="Digitally malicious content is not allowed.")
            return jsonify({"error": reason}), 401

        g.user.bio = bio
        g.user.bio_html=bio_html
        g.db.add(g.user)
        g.db.commit()
        
        #seo profile spam
        if g.timestamp-g.user.created_utc < 60*60*24 and not g.user.post_count and not g.user.comment_count and BeautifulSoup(bio_html).find('a'):
            g.user.ban(reason="seo spam")
        
        
        return jsonify({"message":"Your bio has been updated."})

    if request.values.get("filters") is not None:

        filters=request.values.get("filters")[0:1000].lstrip().rstrip()

        if filters==g.user.custom_filter_list:
            return jsonify({"error":"You didn't change anything"}), 400

        g.user.custom_filter_list=filters
        g.db.add(g.user)
        g.db.commit()
        return jsonify({"message":"Your filters have been updated."})



    x = request.values.get("title_id", None)
    if x:
        x = int(x)

        if x == 0:

            g.user.title_id = None
            updated = True

        elif x > 0:

            eval_env={
                "user": g.user,
                "db": g.db,
                "Board": Board,
                "Submission": Submission
            }
            title = TITLES[x]
            if eval(title.expr, eval_env):
                g.user.title_id = title.id
                updated = True
            else:
                return jsonify({"error": f"You don't meet the requirements for title `{title.text}`."}), 403
        else:
            abort(400)

    defaultsorting = request.values.get("defaultsorting")
    if defaultsorting:
        if defaultsorting in ["hot", "new", "old", "activity", "disputed", "top"]:
            g.user.defaultsorting = defaultsorting
            updated = True
        else:
            abort(400)

    defaulttime = request.values.get("defaulttime")
    if defaulttime:
        if defaulttime in ["day", "week", "month", "year", "all"]:
            g.user.defaulttime = defaulttime
            updated = True
        else:
            abort(400)

    if updated:
        g.db.add(g.user)
        g.db.commit()

        return jsonify({"message": "Your settings have been updated."})

    else:
        return jsonify({"error": "You didn't change anything."}), 400


@app.route("/settings/security", methods=["POST"])
@is_not_banned
def settings_security_post():

    if request.form.get("new_password"):
        if request.form.get(
                "new_password") != request.form.get("cnf_password"):
            return redirect("/settings/security?error=" +
                            escape("Passwords do not match."))

        if not re.match(valid_password_regex, request.form.get("new_password")):
            #print(f"signup fail - {username } - invalid password")
            return redirect("/settings/security?error=" + 
                            escape("Password must be between 8 and 100 characters."))

        if not g.user.verifyPass(request.form.get("old_password")):
            return render_template(
                "settings_security.html",
                error="Incorrect password")

        g.user.passhash = g.user.hash_password(request.form.get("new_password"))

        g.db.add(g.user)
        g.db.commit()

        return jsonify({"message":"Your password has been changed."})

    if request.form.get("new_email"):

        if not g.user.verifyPass(request.form.get('password')):
            return jsonify({"error": "Invalid password"}), 401

        new_email = request.form.get("new_email","").lstrip().rstrip()
        #counteract gmail username+2 and extra period tricks - convert submitted email to actual inbox
        if new_email.endswith("@gmail.com"):
            gmail_username=new_email.split('@')[0]
            gmail_username=gmail_username.split("+")[0]
            gmail_username=gmail_username.replace('.','')
            new_email=f"{gmail_username}@gmail.com"
        if new_email == g.user.email:
            return jsonify({"error": "That's already your email"}), 400

        # check to see if email is in use
        existing = g.db.query(User).filter(User.id != g.user.id,
                                           func.lower(User.email) == new_email.lower()).first()
        if existing:
            return jsonify({"error": "That email address is already in use"}), 409

        url = f"https://{app.config['SERVER_NAME']}/activate"

        now = int(time.time())

        token = generate_hash(f"{new_email}+{g.user.id}+{now}")
        params = f"?email={quote(new_email)}&id={g.user.id}&time={now}&token={token}"

        link = url + params

        send_mail(to_address=new_email,
                  subject="Verify your email address.",
                  html=render_template("email/email_change.html",
                                       action_url=link)
                  )

        return jsonify({"message":f"We sent a verification email to {new_email}. Click the link inside to complete the email change."})

    if request.form.get("2fa_token", ""):

        if not g.user.verifyPass(request.form.get('password')):
            return jsonify({"error": "Invalid password or token"}), 401

        secret = request.form.get("2fa_secret")
        x = pyotp.TOTP(secret)
        if not x.verify(request.form.get("2fa_token"), valid_window=1):
            return jsonify({"error": "Invalid password or token"}), 401

        g.user.mfa_secret = secret
        g.db.add(g.user)
        g.db.commit()

        return jsonify({"message":f"Two-factor authentication enabled."})

    if request.form.get("2fa_remove", ""):

        if not g.user.verifyPass(request.form.get('password')):
            return jsonify({"error": "Invalid password or token"}), 401

        token = request.form.get("2fa_remove")

        if not g.user.validate_2fa(token) and not safe_compare(g.user.mfa_removal_code, token.lower().replace(' ','')):
            return jsonify({"error": "Invalid password or token"}), 401

        g.user.mfa_secret = None
        g.db.add(g.user)
        g.db.commit()

        return jsonify({"message":f"Two-factor authentication disabled."})


@app.post("/settings/dark_mode/<x>")
@auth_desired
def settings_dark_mode(x):

    try:
        x = int(x)
    except:
        abort(400)

    if x not in [0, 1]:
        abort(400)

    session["dark_mode_enabled"] = x
    session.modified = True
    return "", 204


@app.route("/settings/log_out_all_others", methods=["POST"])
@auth_required
def settings_log_out_others():

    submitted_password = request.form.get("password", "")

    if not g.user.verifyPass(submitted_password):
        return render_template(
            "settings_security.html",
            error="Incorrect Password"
            ), 401

    # increment account's nonce
    g.user.login_nonce += 1

    # update cookie accordingly
    session["login_nonce"] = g.user.login_nonce

    g.db.add(g.user)
    g.db.commit()

    return jsonify({"message":"All other devices have been logged out"})


@app.route("/settings/images/profile", methods=["POST"])
@is_not_banned
def settings_images_profile():
    if not g.user.can_upload_avatar:
        return jsonify({"error":f"Profile pictures require {app.config['PROFILE_UPLOAD_REP']} Reputation"}), 401

    g.user.set_profile(request.files["profile"])

    # anti csam
    new_thread = threading.Thread(target=check_csam_url,
                                  args=(g.user.profile_url,
                                        lambda: board.del_profile()
                                        )
                                  )
    new_thread.start()

    return jsonify({"redirect":"/settings/profile?msg=Profile picture updated"}), 302

@app.route("/settings/images/banner", methods=["POST"])
@is_not_banned
def settings_images_banner():
    if not g.user.can_upload_banner:
        jsonify({"error":f"Profile banners require {app.config['BANNER_UPLOAD_REP']} Reputation."}), 401
    g.user.set_banner(request.files["banner"])

    # anti csam
    new_thread = threading.Thread(target=check_csam_url,
                                  args=(g.user.banner_url,
                                        lambda: board.del_banner()
                                        )
                                  )
    new_thread.start()

    return jsonify({"redirect":"/settings/profile?msg=Banner picture updated"}), 302


@app.route("/settings/delete/profile", methods=["POST"])
@is_not_banned
def settings_delete_profile():

    g.user.del_profile()

    return jsonify({"message":"Profile picture successfully removed."})


@app.route("/settings/delete/banner", methods=["POST"])
@is_not_banned
def settings_delete_banner():

    g.user.del_banner()

    return jsonify({"message":"Profile banner successfully removed."})


@app.route("/settings/toggle_collapse", methods=["POST"])
@auth_desired
def settings_toggle_collapse():

    session["sidebar_collapsed"] = not session.get("sidebar_collapsed", False)

    return "", 204


@app.route("/settings/read_announcement", methods=["POST"])
@auth_desired
def update_announcement():

    g.user.read_announcement_utc = int(time.time())
    g.db.add(g.user)
    g.db.commit()

    return "", 204


@app.route("/settings/delete_account", methods=["POST"])
@is_not_banned
@no_negative_balance("html")
def delete_account():

    if not g.user.verifyPass(request.form.get("password", "")) or (
            g.user.mfa_secret and not g.user.validate_2fa(request.form.get("twofactor", ""))):
        return render_template("settings_security.html", 
                               error="Invalid password or token" if g.user.mfa_secret else "Invalid password")


    remove_user(g.user)

    g.user.discord_id=None
    g.user.is_deleted = True
    g.user.login_nonce += 1
    g.user.delete_reason = request.form.get("delete_reason", "")
    g.user.patreon_id=None
    g.user.patreon_pledge_cents=0
    g.user.del_banner()
    g.user.del_profile()
    g.db.add(g.user)

    mods = g.db.query(ModRelationship).filter_by(user_id=g.user.id).all()
    for mod in mods:
        g.db.delete(mod)

    bans = g.db.query(BanRelationship).filter_by(user_id=g.user.id).all()
    for ban in bans:
        g.db.delete(ban)

    contribs = g.db.query(ContributorRelationship).filter_by(
        user_id=g.user.id).all()
    for contrib in contribs:
        g.db.delete(contrib)

    blocks = g.db.query(UserBlock).filter_by(target_id=g.user.id).all()
    for block in blocks:
        g.db.delete(block)

    for b in g.user.boards_modded:
        if b.mods_count == 0:
            b.is_private = False
            b.restricted_posting = False
            b.all_opt_out = False
            g.db.add(b)

    session.pop("user_id", None)
    session.pop("session_id", None)

    #deal with throwaway spam - auto nuke content if account age below threshold
    if int(time.time()) - g.user.created_utc < 60*60*12:
        for post in g.user.submissions:
            post.is_banned=True

            new_ma=ModAction(
                user_id=1,
                kind="ban_post",
                target_submission_id=post.id,
                note="spam",
		board_id=post.board_id
                )

            g.db.add(post)
            g.db.add(new_ma)

        for comment in g.user.comments:
            comment.is_banned=True
            new_ma=ModAction(
                user_id=1,
                kind="ban_comment",
                target_comment_id=comment.id,
                note="spam",
		board_id=comment.post.board_id
                )
            g.db.add(comment)
            g.db.add(new_ma)

    g.db.commit()

    return redirect('/')


@app.route("/settings/blocks", methods=["GET"])
@auth_required
def settings_blockedpage():

    #users=[x.target for x in g.user.blocked]

    return render_template("settings_blocks.html")


@app.route("/settings/filters", methods=["GET"])
@auth_required
def settings_blockedguilds():

    #users=[x.target for x in g.user.blocked]

    return render_template("settings_guildfilter.html")


@app.route("/settings/block", methods=["POST"])
@auth_required
def settings_block_user():

    user = get_user(request.values.get("username"), graceful=True)

    if not user:
        return jsonify({"error": "That user doesn't exist."}), 404

    if user.id == g.user.id:
        return jsonify({"error": "You can't block yourself."}), 409

    if g.user.has_block(user):
        return jsonify({"error": f"You have already blocked @{user.username}."}), 409

    if user.id == 1:
        return jsonify({"error": "You can't block @{user.username}."}), 409

    if user.is_deleted:
        return jsonify({"error": "That account has been deactivated"}), 410
    
    new_block = UserBlock(user_id=g.user.id,
                          target_id=user.id,
                          created_utc=int(time.time())
                          )
    g.db.add(new_block)
    g.db.commit()

    cache.delete_memoized(g.user.idlist)
    #cache.delete_memoized(Board.idlist, v=g.user)
    cache.delete_memoized(frontlist, v=g.user)

    return jsonify({"message": f"@{user.username} blocked."})


@app.route("/settings/unblock", methods=["POST"])
@auth_required
def settings_unblock_user():

    user = get_user(request.values.get("username"))

    x = g.user.has_block(user)
    if not x:
        abort(409)

    g.db.delete(x)
    g.db.commit()

    #cache.delete_memoized(g.user.idlist)
    #cache.delete_memoized(Board.idlist, v=g.user)
    #cache.delete_memoized(frontlist, v=g.user)

    return jsonify({"message": f"@{user.username} unblocked."})


@app.route("/settings/block_guild", methods=["POST"])
@auth_required
def settings_block_guild():

    board = get_guild(request.values.get("board"), graceful=True)

    if not board:
        return jsonify({"error": "That guild doesn't exist."}), 404

    if g.user.has_blocked_guild(board):
        return jsonify({"error": f"You have already blocked +{board.name}."}), 409

    new_block = BoardBlock(user_id=g.user.id,
                           board_id=board.id,
                           created_utc=int(time.time())
                           )
    g.db.add(new_block)
    g.db.commit()

    #cache.delete_memoized(g.user.idlist)
    #cache.delete_memoized(Board.idlist, v=g.user)
    #cache.delete_memoized(frontlist, v=g.user)

    return jsonify({"message": f"+{board.name} added to filter"})


@app.route("/settings/unblock_guild", methods=["POST"])
@auth_required
def settings_unblock_guild():

    board = get_guild(request.values.get("board"), graceful=True)

    x = g.user.has_blocked_guild(board)
    if not x:
        abort(409)

    g.db.delete(x)
    g.db.commit()

    #cache.delete_memoized(g.user.idlist)
    #cache.delete_memoized(Board.idlist, v=g.user)
    #cache.delete_memoized(frontlist, v=g.user)

    return jsonify({"message": f"+{board.name} removed from filter"})


@app.route("/settings/apps", methods=["GET"])
@auth_required
def settings_apps():

    return render_template("settings_apps.html", v=g.user)


@app.route("/settings/remove_discord", methods=["POST"])
@is_not_banned
def settings_remove_discord():

    if g.user.admin_level>1:
        return render_template("settings_filters.html",  error="Admins can't disconnect Discord.")

    remove_user(g.user)

    g.user.discord_id=None
    g.db.add(g.user)
    g.db.commit()

    return redirect("/settings/profile")

@app.route("/settings/content", methods=["GET"])
@auth_required
def settings_content_get():

    return render_template("settings_filters.html", v=g.user)

@app.route("/settings/purchase_history", methods=["GET"])
@auth_required
def settings_purchase_history():

    return render_template("settings_txnlist.html", v=g.user)

@app.route("/settings/name_change", methods=["POST"])
@is_not_banned
@user_update_lock
def settings_name_change():

    if g.user.admin_level:
        return jsonify({"error":"Admins can't change their name."}), 403

    new_name=request.form.get("name").lstrip().rstrip()

    #make sure name is different
    if new_name==g.user.username:
        return jsonify({"error":"You didn't change anything."}), 400

    #can't change name on verified ID accounts
    if g.user.real_id:
        return jsonify({"error":"Verified ID users can't change their name."}), 403

    #7 day cooldown
    if g.user.name_changed_utc > int(time.time()) - 60*60*24*app.config["COOLDOWN_DAYS_CHANGE_USERNAME"]:
        return jsonify({"error":f"You changed your name {(int(time.time()) - g.user.name_changed_utc)//(60*60*24)} days ago. You need to wait {app.config['COOLDOWN_DAYS_CHANGE_USERNAME']} days between name changes."}), 401

    #costs 20 coins
    if g.user.coin_balance < app.config["COINS_REQUIRED_CHANGE_USERNAME"]:
        return jsonify({"error":f"Username changes cost {app.config['COINS_REQUIRED_CHANGE_USERNAME']} coins. You only have a balance of {g.user.coin_balance} Coins"}), 402

    #verify acceptability
    if not re.match(valid_username_regex, new_name):
        return jsonify({"error":"That isn't a valid username."}), 400

    #verify availability
    name=new_name.replace('_','\_')

    x= g.db.query(User).options(
        lazyload('*')
        ).filter(
        or_(
            User.username.ilike(name),
            User.original_username.ilike(name)
            )
        ).first()

    if x and x.id != g.user.id:
        return jsonify({"error":f"The username `{name}` is already in use."}), 403

    #all reqs passed

    #do name change and deduct coins

    g.user.username=new_name
    g.user.coin_balance-=app.config['COINS_REQUIRED_CHANGE_USERNAME']
    g.user.name_changed_utc=int(time.time())

    set_nick(g.user, new_name)

    g.db.add(g.user)
    g.db.commit()
    
    return jsonify({"message":"Username changed successfully."})


@app.route("/settings/badges", methods=["POST"])
@auth_required
def settings_badge_recheck():

    g.user.refresh_selfset_badges()

    return jsonify({"message":"Badges Refreshed"})
