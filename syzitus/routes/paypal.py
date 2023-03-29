from flask import g, session, abort, render_template, jsonify, redirect

from syzitus.classes import *
from syzitus.helpers.wrappers import *
from syzitus.helpers.security import *
from syzitus.helpers.alerts import send_notification
from syzitus.helpers.base36 import *
from syzitus.helpers.get import *
from syzitus.__main__ import app, debug

CLIENT=PayPalClient()

def coins_to_price_cents(n, code=None):

    per_coin=100

    if n>=52:
        price= per_coin*(n-10)
    elif n>=26:
        price= per_coin*(n-4) 
    elif n>=12:
        price= per_coin*(n-1)
    elif n >=4:
        price= per_coin*n
    else:
        price= per_coin*n+50

    #drop one cent for the $X.99
    n -= 1

    if code:
        if isinstance(code, str):
            promo=get_promocode(code)
        else:
            promo=code

        if promo:
            price=promo.adjust_price(price)

    return price

@app.route("/shop/get_price", methods=["GET"])
def shop_get_price():

    coins=int(request.args.get("coins"))

    if coins < 1:
        return jsonify({"error": "Must attempt to buy at least one coin"}), 400

    code=request.args.get("promo","")
    promo=get_promocode(code)

    data={
        "price":coins_to_price_cents(coins, code=promo)/100,
        "promo": promo.promo_text if promo and promo.is_active else ''
        }

    return jsonify(data)

@app.route("/shop/coin_balance", methods=["GET"])
@auth_required
def shop_coin_balance():
    return jsonify({"balance":g.user.coin_balance})


@app.route("/shop/buy_coins", methods=["POST"])
@no_sanctions
@is_not_banned
@no_negative_balance("html")
@user_update_lock
def shop_buy_coins():

    coin_count=int(request.form.get("coin_count",1))

    code=request.form.get("promo","")
    promo=get_promocode(code)

    new_txn=PayPalTxn(
        user_id=g.user.id,
        created_utc=g.timestamp,
        coin_count=coin_count,
        usd_cents=coins_to_price_cents(coin_count, code=promo),
        promo_id= promo.id if promo else None
        )

    g.db.add(new_txn)
    g.db.flush()

    CLIENT.create(new_txn)

    g.db.add(new_txn)
    g.db.commit()

    return jsonify({'redirect':new_txn.approve_url}), 302


@app.route("/shop/negative_balance", methods=["POST"])
@no_sanctions
@is_not_banned
@user_update_lock
def shop_negative_balance():

    new_txn=PayPalTxn(
        user_id=g.user.id,
        created_utc=g.timestamp,
        coin_count=0,
        usd_cents=g.user.negative_balance_cents
        )

    g.db.add(new_txn)
    g.db.flush()

    CLIENT.create(new_txn)

    g.db.add(new_txn)
    g.db.commit()

    return redirect(new_txn.approve_url)

@app.route("/shop/buy_coins_completed", methods=["GET"])
@no_sanctions
@is_not_banned
@user_update_lock
def shop_buy_coins_completed():

    #look up the txn
    id=request.args.get("txid")
    if not id:
        abort(400)
    id=base36decode(id)
    txn=g.db.query(PayPalTxn
        #).with_for_update(
        ).filter_by(user_id=g.user.id, id=id, status=1).first()

    if not txn:
        abort(400)

    if txn.promo and not txn.promo.promo_is_active:
        return jsonfy({"error":f"The promo code `{txn.promo.code}` is not currently valid. Please begin a new transaction."}), 422

    if not CLIENT.capture(txn):
        abort(402)

    txn.created_utc=g.timestamp

    g.db.add(txn)
    g.db.flush()

    #successful payment - award coins

    if txn.coin_count:
        g.user.coin_balance += txn.coin_count
    else:
        g.user.negative_balance_cents -= txn.usd_cents

    g.db.add(g.user)
    g.db.commit()

    return render_template(
        "single_txn.html", 
        txns=[txn],
        msg="The Royal Bank has minted your Coins. Here is a copy of your order."
        )

@app.route("/shop/paypal_webhook", methods=["POST"])
def paypal_webhook_handler():
    
    #Verify paypal signature
    data={
        "auth_algo":request.headers.get("PAYPAL-AUTH-ALGO"),
        "cert_url":request.headers.get("PAYPAL-CERT-URL"),
        "transmission_id":request.headers.get("PAYPAL-TRANSMISSION-ID"),
        "transmission_sig":request.headers.get("PAYPAL-TRANSMISSION-SIG"),
        "transmission_time":request.headers.get("PAYPAL-TRANSMISSION-TIME"),
        "webhook_id":CLIENT.webhook_id,
        "webhook_event":request.json
        }


    x=CLIENT._post("/v1/notifications/verify-webhook-signature", data=data)

    if x.json().get("verification_status") != "SUCCESS":
        abort(403)
    
    data=request.json

    #Reversals
    if data["event_type"] in ["PAYMENT.SALE.REVERSED", "PAYMENT.SALE.REFUNDED"]:

        txn=get_txn(data["resource"]["id"])

        amount_cents=int(float(data["resource"]["amount"]["total"])*100)

    elif data["event_type"] in ["PAYMENT.CAPTURE.REVERSED", "PAYMENT.CAPTURE.REFUNDED"]:

        txn=get_txn(data["resource"]["id"])

        amount_cents=int(float(data["resource"]["amount"]["value"])*100)

    else:
        return "", 204


    #increase to cover extra round of paypal fees
    amount_cents += 30
    amount_cents /= (1-0.029)
    amount_cents = int(amount_cents)

    txn.user.negative_balance_cents+=amount_cents

    txn.status=-2

    g.db.add(txn)
    g.db.add(txn.user)

    g.db.commit()



    return "", 204


@app.route("/gift_post/<pid>", methods=["POST"])
#@no_sanctions
@is_not_banned
@no_negative_balance("toast")
@user_update_lock
def gift_post_pid(pid):

    post=get_post(pid)

    if post.author_id==g.user.id:
        return jsonify({"error":"You can't give awards to yourself."}), 403   

    if post.deleted_utc > 0:
        return jsonify({"error":"You can't give awards to deleted posts"}), 403

    if post.is_banned:
        return jsonify({"error":"You can't give awards to removed posts"}), 403

    if post.author.is_deleted:
        return jsonify({"error":"You can't give awards to deleted accounts"}), 403

    if post.author.is_banned and not post.author.unban_utc:
        return jsonify({"error":"You can't give awards to banned accounts"}), 403

    u=get_user(post.author.username)

    if u.is_blocking:
        return jsonify({"error":"You can't give awards to someone you're blocking."}), 403

    if u.is_blocked:
        return jsonify({"error":"You can't give awards to someone that's blocking you."}), 403


    coins=int(request.args.get("coins",1))

    if not coins:
        return jsonify({"error":"You need to actually give coins."}), 400

    if coins <0:
        return jsonify({"error":"What are you doing, trying to *charge* someone coins?."}), 400

    v=g.db.query(User).with_for_update().options(lazyload('*')).filter_by(id=g.user.id).first()
    u=g.db.query(User).with_for_update().options(lazyload('*')).filter_by(id=u.id).first()

    if not g.user.coin_balance>=coins:
        return jsonify({"error":"You don't have that many coins to give!"}), 403


    g.user.coin_balance -= coins
    u.coin_balance += coins

    g.db.add(g.user)
    g.db.add(u)
    g.db.flush()
    if g.user.coin_balance<0:
        g.db.rollback()
        return jsonify({"error":"You don't have that many coins to give!"}), 403

    if not g.db.query(AwardRelationship).filter_by(user_id=g.user.id, submission_id=post.id).first():
        text=f"Someone liked [your post]({post.permalink}) and has given you a Coin!\n\n"
        if u.premium_expires_utc < g.timestamp:
            text+=f"Your Coin has been automatically redeemed for one week of [{app.config['SITE_NAME']} Premium](/settings/premium)."
        else:
            text+=f"Since you already have {app.config['SITE_NAME']} Premium, the Coin has been added to your balance. You can keep it for yourself, or give it to someone else."
        send_notification(u, text)



    g.db.commit()

    #create record - uniqueness constraints prevent duplicate award counting
    new_rel = AwardRelationship(
        user_id=g.user.id,
        submission_id=post.id
        )
    try:
        g.db.add(new_rel)
        g.db.flush()
    except:
        pass
    
    g.db.commit()

    return jsonify({"redirect":post.permalink}), 301

@app.route("/gift_comment/<cid>", methods=["POST"])
#@no_sanctions
@is_not_banned
@no_negative_balance("toast")
@user_update_lock
def gift_comment_cid(cid):

    comment=get_comment(cid)

    if comment.author_id==g.user.id:
        return jsonify({"error":"You can't give awards to yourself."}), 403      

    if comment.deleted_utc > 0:
        return jsonify({"error":"You can't give awards to deleted posts"}), 403

    if comment.is_banned:
        return jsonify({"error":"You can't give awards to removed posts"}), 403

    if comment.author.is_deleted:
        return jsonify({"error":"You can't give awards to deleted accounts"}), 403

    if comment.author.is_banned and not comment.author.unban_utc:
        return jsonify({"error":"You can't give awards to banned accounts"}), 403

    u=get_user(comment.author.username)

    if u.is_blocking:
        return jsonify({"error":"You can't give awards to someone you're blocking."}), 403

    if u.is_blocked:
        return jsonify({"error":"You can't give awards to someone that's blocking you."}), 403

    coins=int(request.args.get("coins",1))

    if not coins:
        return jsonify({"error":"You need to actually give coins."}), 400

    if coins <0:
        return jsonify({"error":"What are you doing, trying to *charge* someone coins?."}), 400

    v=g.db.query(User).with_for_update().options(lazyload('*')).filter_by(id=g.user.id).first()
    u=g.db.query(User).with_for_update().options(lazyload('*')).filter_by(id=u.id).first()

    if not g.user.coin_balance>=coins:
        return jsonify({"error":"You don't have that many coins to give!"}), 403
        
    g.user.coin_balance -= coins
    u.coin_balance += coins
    g.db.add(g.user)
    g.db.add(u)
    g.db.flush()
    if g.user.coin_balance<0:
        g.db.rollback()
        return jsonify({"error":"You don't have that many coins to give!"}), 403

    if not g.db.query(AwardRelationship).filter_by(user_id=g.user.id, comment_id=comment.id).first():
        text=f"Someone liked [your comment]({comment.permalink}) and has given you a Coin!\n\n"
        if u.premium_expires_utc < g.timestamp:
            text+=f"Your Coin has been automatically redeemed for one week of [{app.config['SITE_NAME']} Premium](/settings/premium)."
        else:
            text+=f"Since you already have {app.config['SITE_NAME']} Premium, the Coin has been added to your balance. You can keep it for yourself, or give it to someone else."

        send_notification(u, text)



    g.db.commit()

    #create record - uniqe prevents duplicates
    new_rel = AwardRelationship(
        user_id=g.user.id,
        comment_id=comment.id
        )
    try:
        g.db.add(new_rel)
        g.db.flush()
    except:
        pass
    
    g.db.commit()

    return jsonify({"redirect":comment.permalink}), 301


@app.route("/paypaltxn/<txid>")
@auth_required
def paypaltxn_txid(txid):

    txn = get_txid(txid)

    if txn.user_id != g.user.id and g.user.admin_level<4:
        abort(403)

    return render_template(
        "single_txn.html", 
        txns=[txn]
        )
