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
@app.route("/api/vue/settings/profile", methods=["POST"])
@auth_required
@api()
@validate_formkey
def settings_profile_post(v):

    updated = False

    if request.values.get("over18", v.over_18) != v.over_18:
        updated = True
        v.over_18 = request.values.get("over18", None) == 'true'
        cache.delete_memoized(User.idlist, v)

    if request.values.get("hide_offensive",
                          v.hide_offensive) != v.hide_offensive:
        updated = True
        v.hide_offensive = request.values.get("hide_offensive", None) == 'true'
        cache.delete_memoized(User.idlist, v)
		
    if request.values.get("hide_bot",
                          v.hide_bot) != v.hide_bot:
        updated = True
        v.hide_bot = request.values.get("hide_bot", None) == 'true'
        cache.delete_memoized(User.idlist, v)

    if request.values.get("show_nsfl", v.show_nsfl) != v.show_nsfl:
        updated = True
        v.show_nsfl = request.values.get("show_nsfl", None) == 'true'
        cache.delete_memoized(User.idlist, v)

    if request.values.get("filter_nsfw", v.filter_nsfw) != v.filter_nsfw:
        updated = True
        v.filter_nsfw = not request.values.get("filter_nsfw", None) == 'true'
        cache.delete_memoized(User.idlist, v)

    if request.values.get("private", v.is_private) != v.is_private:
        updated = True
        v.is_private = request.values.get("private", None) == 'true'

    if request.values.get("nofollow", v.is_nofollow) != v.is_nofollow:
        updated = True
        v.is_nofollow = request.values.get("nofollow", None) == 'true'

    if request.values.get("join_chat", v.auto_join_chat) != v.auto_join_chat:
        updated = True
        v.auto_join_chat = request.values.get("join_chat", None) == 'true'

    if request.values.get("bio") is not None:
        bio = request.values.get("bio")[0:256]

        bio=preprocess(bio)

        if bio == v.bio:
            return {"html":lambda:render_template("settings_profile.html",
                                   v=v,
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
                v.ban(days=30, reason="Digitally malicious content is not allowed.")
            return jsonify({"error": reason}), 401

        v.bio = bio
        v.bio_html=bio_html
        g.db.add(v)
        
        #seo profile spam
        if int(time.time())-v.created_utc < 60*60*24 and not v.post_count and not v.comment_count and BeautifulSoup(bio_html).find('a'):
            v.ban(reason="seo spam")
        
        
        return {"html":lambda:render_template("settings_profile.html",
                               v=v,
                               msg="Your bio has been updated."),
		"api":lambda:jsonify({"message":"Your bio has been updated."})}

    if request.values.get("filters") is not None:

        filters=request.values.get("filters")[0:1000].lstrip().rstrip()

        if filters==v.custom_filter_list:
            return {"html":lambda:render_template("settings_profile.html",
                                   v=v,
                                   error="You didn't change anything"),
		    "api":lambda:jsonify({"error":"You didn't change anything"})
		   }

        v.custom_filter_list=filters
        g.db.add(v)
        return {"html":lambda:render_template("settings_profile.html",
                               v=v,
                               msg="Your custom filters have been updated."),
		"api":lambda:jsonify({"message":"Your custom filters have been updated"})}



    x = request.values.get("title_id", None)
    if x:
        x = int(x)
        if x == 0:
            v.title_id = None
            updated = True
        elif x > 0:
            title = get_title(x)
            if bool(eval(title.qualification_expr)):
                v.title_id = title.id
                updated = True
            else:
                return jsonify({"error": f"You don't meet the requirements for title `{title.text}`."}), 403
        else:
            abort(400)

    defaultsorting = request.values.get("defaultsorting")
    if defaultsorting:
        if defaultsorting in ["hot", "new", "old", "activity", "disputed", "top"]:
            v.defaultsorting = defaultsorting
            updated = True
        else:
            abort(400)

    defaulttime = request.values.get("defaulttime")
    if defaulttime:
        if defaulttime in ["day", "week", "month", "year", "all"]:
            v.defaulttime = defaulttime
            updated = True
        else:
            abort(400)

    if updated:
        g.db.add(v)

        return jsonify({"message": "Your settings have been updated."})

    else:
        return jsonify({"error": "You didn't change anything."}), 400


@app.route("/settings/security", methods=["POST"])
@auth_required
@validate_formkey
def settings_security_post(v):

    if request.form.get("new_password"):
        if request.form.get(
                "new_password") != request.form.get("cnf_password"):
            return redirect("/settings/security?error=" +
                            escape("Passwords do not match."))

        if not re.match(valid_password_regex, request.form.get("new_password")):
            #print(f"signup fail - {username } - invalid password")
            return redirect("/settings/security?error=" + 
                            escape("Password must be between 8 and 100 characters."))

        if not v.verifyPass(request.form.get("old_password")):
            return render_template(
                "settings_security.html", v=v, error="Incorrect password")

        v.passhash = v.hash_password(request.form.get("new_password"))

        g.db.add(v)

        return redirect("/settings/security?msg=" +
                        escape("Your password has been changed."))

    if request.form.get("new_email"):

        if not v.verifyPass(request.form.get('password')):
            return redirect("/settings/security?error=" +
                            escape("Invalid password."))

        new_email = request.form.get("new_email","").lstrip().rstrip()
        #counteract gmail username+2 and extra period tricks - convert submitted email to actual inbox
        if new_email.endswith("@gmail.com"):
            gmail_username=new_email.split('@')[0]
            gmail_username=gmail_username.split("+")[0]
            gmail_username=gmail_username.replace('.','')
            new_email=f"{gmail_username}@gmail.com"
        if new_email == v.email:
            return redirect("/settings/security?error=" +
                            escape("That email is already yours!"))

        # check to see if email is in use
        existing = g.db.query(User).filter(User.id != v.id,
                                           func.lower(User.email) == new_email.lower()).first()
        if existing:
            return redirect("/settings/security?error=" +
                            escape("That email address is already in use."))

        url = f"https://{app.config['SERVER_NAME']}/activate"

        now = int(time.time())

        token = generate_hash(f"{new_email}+{v.id}+{now}")
        params = f"?email={quote(new_email)}&id={v.id}&time={now}&token={token}"

        link = url + params

        send_mail(to_address=new_email,
                  subject="Verify your email address.",
                  html=render_template("email/email_change.html",
                                       action_url=link,
                                       v=v)
                  )

        return redirect("/settings/security?msg=" + escape(
            "Check your email and click the verification link to complete the email change."))

    if request.form.get("2fa_token", ""):

        if not v.verifyPass(request.form.get('password')):
            return redirect("/settings/security?error=" +
                            escape("Invalid password or token."))

        secret = request.form.get("2fa_secret")
        x = pyotp.TOTP(secret)
        if not x.verify(request.form.get("2fa_token"), valid_window=1):
            return redirect("/settings/security?error=" +
                            escape("Invalid password or token."))

        v.mfa_secret = secret
        g.db.add(v)

        return redirect("/settings/security?msg=" +
                        escape("Two-factor authentication enabled."))

    if request.form.get("2fa_remove", ""):

        if not v.verifyPass(request.form.get('password')):
            return redirect("/settings/security?error=" +
                            escape("Invalid password or token."))

        token = request.form.get("2fa_remove")

        if not v.validate_2fa(token) and not safe_compare(v.mfa_removal_code, token.lower().replace(' ','')):
            return redirect("/settings/security?error=" +
                            escape("Invalid password or token."))

        v.mfa_secret = None
        g.db.add(v)

        return redirect("/settings/security?msg=" +
                        escape("Two-factor authentication disabled."))


@app.route("/settings/dark_mode/<x>", methods=["POST"])
@auth_required
@validate_formkey
def settings_dark_mode(x, v):

    try:
        x = int(x)
    except BaseException:
        abort(400)

    if x not in [0, 1]:
        abort(400)

    if not v.can_use_darkmode:
        session["dark_mode_enabled"] = False
        abort(403)
    else:
        # print(f"current cookie is {session.get('dark_mode_enabled')}")
        session["dark_mode_enabled"] = x
        # print(f"set dark mode @{v.username} to {x}")
        # print(f"cookie is now {session.get('dark_mode_enabled')}")
        session.modified = True
        return "", 204


@app.route("/settings/log_out_all_others", methods=["POST"])
@auth_required
@validate_formkey
def settings_log_out_others(v):

    submitted_password = request.form.get("password", "")

    if not v.verifyPass(submitted_password):
        return render_template("settings_security.html",
                               v=v, error="Incorrect Password"), 401

    # increment account's nonce
    v.login_nonce += 1

    # update cookie accordingly
    session["login_nonce"] = v.login_nonce

    g.db.add(v)

    return render_template("settings_security.html", v=v,
                           msg="All other devices have been logged out")


@app.route("/settings/images/profile", methods=["POST"])
@is_not_banned
@validate_formkey
def settings_images_profile(v):
    if v.can_upload_avatar:
        v.set_profile(request.files["profile"])

        # anti csam
        new_thread = threading.Thread(target=check_csam_url,
                                      args=(v.profile_url,
                                            v,
                                            lambda: board.del_profile()
                                            )
                                      )
        new_thread.start()

        return render_template("settings_profile.html",
                               v=v, msg="Profile picture successfully updated.")

    return render_template("settings_profile.html", v=v,
                           msg="Avatars require 300 reputation.")


@app.route("/settings/images/banner", methods=["POST"])
@is_not_banned
@validate_formkey
def settings_images_banner(v):
    if v.can_upload_banner:
        v.set_banner(request.files["banner"])

        # anti csam
        new_thread = threading.Thread(target=check_csam_url,
                                      args=(v.banner_url,
                                            v,
                                            lambda: board.del_banner()
                                            )
                                      )
        new_thread.start()

        return render_template("settings_profile.html",
                               v=v, msg="Banner successfully updated.")

    return render_template("settings_profile.html", v=v,
                           msg="Banners require 500 reputation.")


@app.route("/settings/delete/profile", methods=["POST"])
@auth_required
@validate_formkey
def settings_delete_profile(v):

    v.del_profile()

    return render_template("settings_profile.html", v=v,
                           msg="Profile picture successfully removed.")


@app.route("/settings/new_feedkey", methods=["POST"])
@auth_required
@validate_formkey
def settings_new_feedkey(v):

    v.feed_nonce += 1
    g.db.add(v)

    return render_template("settings_profile.html", v=v,
                           msg="Your new custom RSS Feed Token has been generated.")


@app.route("/settings/delete/banner", methods=["POST"])
@auth_required
@validate_formkey
def settings_delete_banner(v):

    v.del_banner()

    return render_template("settings_profile.html", v=v,
                           msg="Banner successfully removed.")


@app.route("/settings/toggle_collapse", methods=["POST"])
@auth_required
@validate_formkey
def settings_toggle_collapse(v):

    session["sidebar_collapsed"] = not session.get("sidebar_collapsed", False)

    return "", 204


@app.route("/settings/read_announcement", methods=["POST"])
@auth_required
@validate_formkey
def update_announcement(v):

    v.read_announcement_utc = int(time.time())
    g.db.add(v)

    return "", 204


@app.route("/settings/delete_account", methods=["POST"])
@is_not_banned
@no_negative_balance("html")
@validate_formkey
def delete_account(v):

    if not v.verifyPass(request.form.get("password", "")) or (
            v.mfa_secret and not v.validate_2fa(request.form.get("twofactor", ""))):
        return render_template("settings_security.html", v=v,
                               error="Invalid password or token" if v.mfa_secret else "Invalid password")


    remove_user(v)

    v.discord_id=None
    v.is_deleted = True
    v.login_nonce += 1
    v.delete_reason = request.form.get("delete_reason", "")
    v.patreon_id=None
    v.patreon_pledge_cents=0
    v.del_banner()
    v.del_profile()
    g.db.add(v)

    mods = g.db.query(ModRelationship).filter_by(user_id=v.id).all()
    for mod in mods:
        g.db.delete(mod)

    bans = g.db.query(BanRelationship).filter_by(user_id=v.id).all()
    for ban in bans:
        g.db.delete(ban)

    contribs = g.db.query(ContributorRelationship).filter_by(
        user_id=v.id).all()
    for contrib in contribs:
        g.db.delete(contrib)

    blocks = g.db.query(UserBlock).filter_by(target_id=v.id).all()
    for block in blocks:
        g.db.delete(block)

    for b in v.boards_modded:
        if b.mods_count == 0:
            b.is_private = False
            b.restricted_posting = False
            b.all_opt_out = False
            g.db.add(b)

    session.pop("user_id", None)
    session.pop("session_id", None)

    #deal with throwaway spam - auto nuke content if account age below threshold
    if int(time.time()) - v.created_utc < 60*60*12:
        for post in v.submissions:
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

        for comment in v.comments:
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
def settings_blockedpage(v):

    #users=[x.target for x in v.blocked]

    return render_template("settings_blocks.html",
                           v=v)


@app.route("/settings/filters", methods=["GET"])
@auth_required
def settings_blockedguilds(v):

    #users=[x.target for x in v.blocked]

    return render_template("settings_guildfilter.html",
                           v=v)


@app.route("/settings/block", methods=["POST"])
@auth_required
@validate_formkey
def settings_block_user(v):

    user = get_user(request.values.get("username"), graceful=True)

    if not user:
        return jsonify({"error": "That user doesn't exist."}), 404

    if user.id == v.id:
        return jsonify({"error": "You can't block yourself."}), 409

    if v.has_block(user):
        return jsonify({"error": f"You have already blocked @{user.username}."}), 409

    if user.id == 1:
        return jsonify({"error": "You can't block @{user.username}."}), 409

    if user.is_deleted:
        return jsonify({"error": "That account has been deactivated"}), 410
    
    new_block = UserBlock(user_id=v.id,
                          target_id=user.id,
                          created_utc=int(time.time())
                          )
    g.db.add(new_block)

    cache.delete_memoized(v.idlist)
    #cache.delete_memoized(Board.idlist, v=v)
    cache.delete_memoized(frontlist, v=v)

    return jsonify({"message": f"@{user.username} blocked."})


@app.route("/settings/unblock", methods=["POST"])
@auth_required
@validate_formkey
def settings_unblock_user(v):

    user = get_user(request.values.get("username"))

    x = v.has_block(user)
    if not x:
        abort(409)

    g.db.delete(x)

    cache.delete_memoized(v.idlist)
    #cache.delete_memoized(Board.idlist, v=v)
    cache.delete_memoized(frontlist, v=v)

    return jsonify({"message": f"@{user.username} unblocked."})


@app.route("/settings/block_guild", methods=["POST"])
@auth_required
@validate_formkey
def settings_block_guild(v):

    board = get_guild(request.values.get("board"), graceful=True)

    if not board:
        return jsonify({"error": "That guild doesn't exist."}), 404

    if v.has_blocked_guild(board):
        return jsonify({"error": f"You have already blocked +{board.name}."}), 409

    new_block = BoardBlock(user_id=v.id,
                           board_id=board.id,
                           created_utc=int(time.time())
                           )
    g.db.add(new_block)
    g.db.commit()

    cache.delete_memoized(v.idlist)
    #cache.delete_memoized(Board.idlist, v=v)
    cache.delete_memoized(frontlist, v=v)

    return jsonify({"message": f"+{board.name} added to filter"})


@app.route("/settings/unblock_guild", methods=["POST"])
@auth_required
@validate_formkey
def settings_unblock_guild(v):

    board = get_guild(request.values.get("board"), graceful=True)

    x = v.has_blocked_guild(board)
    if not x:
        abort(409)

    g.db.delete(x)
    g.db.commit()

    cache.delete_memoized(v.idlist)
    #cache.delete_memoized(Board.idlist, v=v)
    cache.delete_memoized(frontlist, v=v)

    return jsonify({"message": f"+{board.name} removed from filter"})


@app.route("/settings/apps", methods=["GET"])
@auth_required
def settings_apps(v):

    return render_template("settings_apps.html", v=v)


@app.route("/settings/remove_discord", methods=["POST"])
@auth_required
@validate_formkey
def settings_remove_discord(v):

    if v.admin_level>1:
        return render_template("settings_filters.html", v=v, error="Admins can't disconnect Discord.")

    remove_user(v)

    v.discord_id=None
    g.db.add(v)
    g.db.commit()

    return redirect("/settings/profile")

@app.route("/settings/content", methods=["GET"])
@auth_required
def settings_content_get(v):

    return render_template("settings_filters.html", v=v)

@app.route("/settings/purchase_history", methods=["GET"])
@auth_required
def settings_purchase_history(v):

    return render_template("settings_txnlist.html", v=v)

@app.route("/settings/name_change", methods=["POST"])
@auth_required
@validate_formkey
def settings_name_change(v):

    if v.admin_level:
        return render_template("settings_profile.html",
                           v=v,
                           error="Admins can't change their name.")


    new_name=request.form.get("name").lstrip().rstrip()

    #make sure name is different
    if new_name==v.username:
        return render_template("settings_profile.html",
                           v=v,
                           error="You didn't change anything")

    #can't change name on verified ID accounts
    if v.real_id:
        return render_template("settings_profile.html",
                           v=v,
                           error="Your ID is verified so you can't change your username.")

    #7 day cooldown
    if v.name_changed_utc > int(time.time()) - 60*60*24*7:
        return render_template("settings_profile.html",
                           v=v,
                           error=f"You changed your name {(int(time.time()) - v.name_changed_utc)//(60*60*24)} days ago. You need to wait 7 days between name changes.")

    #costs 3 coins
    if v.coin_balance < 20:
        return render_template("settings_profile.html",
                           v=v,
                           error=f"Username changes cost 20 Coins. You only have a balance of {v.coin_balance} Coins")

    #verify acceptability
    if not re.match(valid_username_regex, new_name):
        return render_template("settings_profile.html",
                           v=v,
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

    if x and x.id != v.id:
        return render_template("settings_profile.html",
                           v=v,
                           error=f"Username `{new_name}` is already in use.")

    #all reqs passed

    #check user avatar/banner for rename if needed
    if v.has_profile and v.profile_url.startswith("https://i.ruqqus.com/users/"):
        upload_from_url(f"uid/{v.base36id}/profile-{v.profile_nonce}.png", f"{v.profile_url}")
        v.profile_set_utc=int(time.time())
        g.db.add(v)
        g.db.commit()

    if v.has_banner and v.banner_url.startswith("https://i.ruqqus.com/users/"):
        upload_from_url(f"uid/{v.base36id}/banner-{v.banner_nonce}.png", f"{v.banner_url}")
        v.banner_set_utc=int(time.time())
        g.db.add(v)
        g.db.commit()


    #do name change and deduct coins

    v=g.db.query(User).with_for_update().options(lazyload('*')).filter_by(id=v.id).first()

    v.username=new_name
    v.coin_balance-=20
    v.name_changed_utc=int(time.time())

    set_nick(v, new_name)

    g.db.add(v)
    g.db.commit()

    return render_template("settings_profile.html",
                       v=v,
                       msg=f"Username changed successfully. 20 Coins have been deducted from your balance.")



@app.route("/settings/badges", methods=["POST"])
@auth_required
@validate_formkey
def settings_badge_recheck(v):

    v.refresh_selfset_badges()

    return jsonify({"message":"Badges Refreshed"})
