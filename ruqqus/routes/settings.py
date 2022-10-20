from flask import *
from sqlalchemy import func
import time
import threading
import mistletoe
import re
from ruqqus.classes import *
from ruqqus.helpers.wrappers import *
from ruqqus.helpers.security import *
from ruqqus.helpers.sanitize import *
from ruqqus.helpers.filters import filter_comment_html
from ruqqus.helpers.markdown import *
from ruqqus.helpers.discord import remove_user, set_nick
from ruqqus.helpers.aws import *
from ruqqus.mail import *
from .front import frontlist
from ruqqus.__main__ import app, cache


valid_username_regex = re.compile("^[a-zA-Z0-9_]{3,25}$")
valid_password_regex = re.compile("^.{8,100}$")


@app.route("/settings/profile", methods=["POST"])
@auth_required
@validate_formkey
def settings_profile_post():

    updated = False

    if request.values.get("over18", g.user.over_18) != g.user.over_18:
        updated = True
        g.user.over_18 = request.values.get("over18", None) == 'true'
        cache.delete_memoized(User.idlist, g.user)

    if request.values.get("hide_offensive",
                          g.user.hide_offensive) != g.user.hide_offensive:
        updated = True
        g.user.hide_offensive = request.values.get("hide_offensive", None) == 'true'
        cache.delete_memoized(User.idlist, g.user)
		
    if request.values.get("hide_bot",
                          g.user.hide_bot) != g.user.hide_bot:
        updated = True
        g.user.hide_bot = request.values.get("hide_bot", None) == 'true'
        cache.delete_memoized(User.idlist, g.user)

    if request.values.get("show_nsfl", g.user.show_nsfl) != g.user.show_nsfl:
        updated = True
        g.user.show_nsfl = request.values.get("show_nsfl", None) == 'true'
        cache.delete_memoized(User.idlist, g.user)

    if request.values.get("filter_nsfw", g.user.filter_nsfw) != g.user.filter_nsfw:
        updated = True
        g.user.filter_nsfw = not request.values.get("filter_nsfw", None) == 'true'
        cache.delete_memoized(User.idlist, g.user)

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
            return {"html":lambda:render_template("settings_profile.html",
                                   error="You didn't change anything"),
		    "api":lambda:jsonify({"error":"You didn't change anything"})
		   }


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
        
        #seo profile spam
        if int(time.time())-g.user.created_utc < 60*60*24 and not g.user.post_count and not g.user.comment_count and BeautifulSoup(bio_html).find('a'):
            g.user.ban(reason="seo spam")
        
        
        return {"html":lambda:render_template("settings_profile.html",
                               msg="Your bio has been updated."),
		"api":lambda:jsonify({"message":"Your bio has been updated."})}

    if request.values.get("filters") is not None:

        filters=request.values.get("filters")[0:1000].lstrip().rstrip()

        if filters==g.user.custom_filter_list:
            return {"html":lambda:render_template("settings_profile.html",
                                   error="You didn't change anything"),
		    "api":lambda:jsonify({"error":"You didn't change anything"})
		   }

        g.user.custom_filter_list=filters
        g.db.add(g.user)
        return {"html":lambda:render_template("settings_profile.html",
                               msg="Your custom filters have been updated."),
		"api":lambda:jsonify({"message":"Your custom filters have been updated"})}



    x = request.values.get("title_id", None)
    if x:
        x = int(x)
        if x == 0:
            g.user.title_id = None
            updated = True
        elif x > 0:
            title = get_title(x)
            if bool(eval(title.qualification_expr)):
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

        return jsonify({"message": "Your settings have been updated."})

    else:
        return jsonify({"error": "You didn't change anything."}), 400


@app.route("/settings/security", methods=["POST"])
@auth_required
@validate_formkey
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

        return redirect("/settings/security?msg=" +
                        escape("Your password has been changed."))

    if request.form.get("new_email"):

        if not g.user.verifyPass(request.form.get('password')):
            return redirect("/settings/security?error=" +
                            escape("Invalid password."))

        new_email = request.form.get("new_email","").lstrip().rstrip()
        #counteract gmail username+2 and extra period tricks - convert submitted email to actual inbox
        if new_email.endswith("@gmail.com"):
            gmail_username=new_email.split('@')[0]
            gmail_username=gmail_username.split("+")[0]
            gmail_username=gmail_username.replace('.','')
            new_email=f"{gmail_username}@gmail.com"
        if new_email == g.user.email:
            return redirect("/settings/security?error=" +
                            escape("That email is already yours!"))

        # check to see if email is in use
        existing = g.db.query(User).filter(User.id != g.user.id,
                                           func.lower(User.email) == new_email.lower()).first()
        if existing:
            return redirect("/settings/security?error=" +
                            escape("That email address is already in use."))

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

        return redirect("/settings/security?msg=" + escape(
            "Check your email and click the verification link to complete the email change."))

    if request.form.get("2fa_token", ""):

        if not g.user.verifyPass(request.form.get('password')):
            return redirect("/settings/security?error=" +
                            escape("Invalid password or token."))

        secret = request.form.get("2fa_secret")
        x = pyotp.TOTP(secret)
        if not x.verify(request.form.get("2fa_token"), valid_window=1):
            return redirect("/settings/security?error=" +
                            escape("Invalid password or token."))

        g.user.mfa_secret = secret
        g.db.add(g.user)

        return redirect("/settings/security?msg=" +
                        escape("Two-factor authentication enabled."))

    if request.form.get("2fa_remove", ""):

        if not g.user.verifyPass(request.form.get('password')):
            return redirect("/settings/security?error=" +
                            escape("Invalid password or token."))

        token = request.form.get("2fa_remove")

        if not g.user.validate_2fa(token) and not safe_compare(g.user.mfa_removal_code, token.lower().replace(' ','')):
            return redirect("/settings/security?error=" +
                            escape("Invalid password or token."))

        g.user.mfa_secret = None
        g.db.add(g.user)

        return redirect("/settings/security?msg=" +
                        escape("Two-factor authentication disabled."))


@app.route("/settings/dark_mode/<x>", methods=["POST"])
@auth_required
@validate_formkey
def settings_dark_mode(x):

    try:
        x = int(x)
    except BaseException:
        abort(400)

    if x not in [0, 1]:
        abort(400)

    if not g.user.can_use_darkmode:
        session["dark_mode_enabled"] = False
        abort(403)
    else:
        # print(f"current cookie is {session.get('dark_mode_enabled')}")
        session["dark_mode_enabled"] = x
        # print(f"set dark mode @{g.user.username} to {x}")
        # print(f"cookie is now {session.get('dark_mode_enabled')}")
        session.modified = True
        return "", 204


@app.route("/settings/log_out_all_others", methods=["POST"])
@auth_required
@validate_formkey
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

    return render_template(
        "settings_security.html",
        msg="All other devices have been logged out")


@app.route("/settings/images/profile", methods=["POST"])
@is_not_banned
@validate_formkey
def settings_images_profile():
    if g.user.can_upload_avatar:
        g.user.set_profile(request.files["profile"])

        # anti csam
        new_thread = threading.Thread(target=check_csam_url,
                                      args=(g.user.profile_url,
                                            v,
                                            lambda: board.del_profile()
                                            )
                                      )
        new_thread.start()

        return render_template(
            "settings_profile.html",
            msg="Profile picture successfully updated.")

    return render_template(
        "settings_profile.html",
        msg="Avatars require 300 reputation.")


@app.route("/settings/images/banner", methods=["POST"])
@is_not_banned
@validate_formkey
def settings_images_banner():
    if g.user.can_upload_banner:
        g.user.set_banner(request.files["banner"])

        # anti csam
        new_thread = threading.Thread(target=check_csam_url,
                                      args=(g.user.banner_url,
                                            v,
                                            lambda: board.del_banner()
                                            )
                                      )
        new_thread.start()

        return render_template(
            "settings_profile.html",
            msg="Banner successfully updated.")

    return render_template(
        "settings_profile.html",
        msg="Banners require 500 reputation.")


@app.route("/settings/delete/profile", methods=["POST"])
@auth_required
@validate_formkey
def settings_delete_profile():

    g.user.del_profile()

    return render_template(
        "settings_profile.html",
        msg="Profile picture successfully removed.")


@app.route("/settings/new_feedkey", methods=["POST"])
@auth_required
@validate_formkey
def settings_new_feedkey():

    g.user.feed_nonce += 1
    g.db.add(g.user)

    return render_template(
        "settings_profile.html",
        msg="Your new custom RSS Feed Token has been generated.")


@app.route("/settings/delete/banner", methods=["POST"])
@auth_required
@validate_formkey
def settings_delete_banner():

    g.user.del_banner()

    return render_template(
        "settings_profile.html",
        msg="Banner successfully removed.")


@app.route("/settings/toggle_collapse", methods=["POST"])
@auth_required
@validate_formkey
def settings_toggle_collapse():

    session["sidebar_collapsed"] = not session.get("sidebar_collapsed", False)

    return "", 204


@app.route("/settings/read_announcement", methods=["POST"])
@auth_required
@validate_formkey
def update_announcement():

    g.user.read_announcement_utc = int(time.time())
    g.db.add(g.user)

    return "", 204


@app.route("/settings/delete_account", methods=["POST"])
@is_not_banned
@no_negative_balance("html")
@validate_formkey
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
@validate_formkey
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

    cache.delete_memoized(g.user.idlist)
    #cache.delete_memoized(Board.idlist, v=g.user)
    cache.delete_memoized(frontlist, v=g.user)

    return jsonify({"message": f"@{user.username} blocked."})


@app.route("/settings/unblock", methods=["POST"])
@auth_required
@validate_formkey
def settings_unblock_user():

    user = get_user(request.values.get("username"))

    x = g.user.has_block(user)
    if not x:
        abort(409)

    g.db.delete(x)

    cache.delete_memoized(g.user.idlist)
    #cache.delete_memoized(Board.idlist, v=g.user)
    cache.delete_memoized(frontlist, v=g.user)

    return jsonify({"message": f"@{user.username} unblocked."})


@app.route("/settings/block_guild", methods=["POST"])
@auth_required
@validate_formkey
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

    cache.delete_memoized(g.user.idlist)
    #cache.delete_memoized(Board.idlist, v=g.user)
    cache.delete_memoized(frontlist, v=g.user)

    return jsonify({"message": f"+{board.name} added to filter"})


@app.route("/settings/unblock_guild", methods=["POST"])
@auth_required
@validate_formkey
def settings_unblock_guild():

    board = get_guild(request.values.get("board"), graceful=True)

    x = g.user.has_blocked_guild(board)
    if not x:
        abort(409)

    g.db.delete(x)
    g.db.commit()

    cache.delete_memoized(g.user.idlist)
    #cache.delete_memoized(Board.idlist, v=g.user)
    cache.delete_memoized(frontlist, v=g.user)

    return jsonify({"message": f"+{board.name} removed from filter"})


@app.route("/settings/apps", methods=["GET"])
@auth_required
def settings_apps():

    return render_template("settings_apps.html", v=g.user)


@app.route("/settings/remove_discord", methods=["POST"])
@auth_required
@validate_formkey
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
@auth_required
@validate_formkey
def settings_name_change():

    if g.user.admin_level:
        return render_template("settings_profile.html",
                           error="Admins can't change their name.")


    new_name=request.form.get("name").lstrip().rstrip()

    #make sure name is different
    if new_name==g.user.username:
        return render_template("settings_profile.html",
                           error="You didn't change anything")

    #can't change name on verified ID accounts
    if g.user.real_id:
        return render_template("settings_profile.html",
                           error="Your ID is verified so you can't change your username.")

    #7 day cooldown
    if g.user.name_changed_utc > int(time.time()) - 60*60*24*7:
        return render_template("settings_profile.html",
                           error=f"You changed your name {(int(time.time()) - g.user.name_changed_utc)//(60*60*24)} days ago. You need to wait 7 days between name changes.")

    #costs 3 coins
    if g.user.coin_balance < 20:
        return render_template("settings_profile.html",
                           error=f"Username changes cost 20 Coins. You only have a balance of {g.user.coin_balance} Coins")

    #verify acceptability
    if not re.match(valid_username_regex, new_name):
        return render_template("settings_profile.html",
                           error=f"That isn't a valid username.")

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
        return render_template("settings_profile.html",
                           error=f"Username `{new_name}` is already in use.")

    #all reqs passed

    #check user avatar/banner for rename if needed
    if g.user.has_profile and g.user.profile_url.startswith("https://i.ruqqus.com/users/"):
        upload_from_url(f"uid/{g.user.base36id}/profile-{g.user.profile_nonce}.png", f"{g.user.profile_url}")
        g.user.profile_set_utc=int(time.time())
        g.db.add(g.user)
        g.db.commit()

    if g.user.has_banner and g.user.banner_url.startswith("https://i.ruqqus.com/users/"):
        upload_from_url(f"uid/{g.user.base36id}/banner-{g.user.banner_nonce}.png", f"{g.user.banner_url}")
        g.user.banner_set_utc=int(time.time())
        g.db.add(g.user)
        g.db.commit()


    #do name change and deduct coins

    v=g.db.query(User).with_for_update().options(lazyload('*')).filter_by(id=g.user.id).first()

    g.user.username=new_name
    g.user.coin_balance-=20
    g.user.name_changed_utc=int(time.time())

    set_nick(v, new_name)

    g.db.add(g.user)
    g.db.commit()

    return render_template("settings_profile.html",
                       msg=f"Username changed successfully. 20 Coins have been deducted from your balance.")



@app.route("/settings/badges", methods=["POST"])
@auth_required
@validate_formkey
def settings_badge_recheck():

    g.user.refresh_selfset_badges()

    return jsonify({"message":"Badges Refreshed"})
