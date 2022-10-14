from os import environ
import requests
import urllib
import hmac
import pprint
import time
import pprint

from flask import *

from ruqqus.classes import *
from ruqqus.helpers.wrappers import *
from ruqqus.helpers.security import *
from ruqqus.helpers.alerts import send_notification
from ruqqus.helpers.base36 import *
from ruqqus.helpers.get import *
from ruqqus.__main__ import app

CLIENT=PayPalClient()

def coins_to_price_cents(n, code=None):

    if n>=52:
        price= 100*n - 1001
    elif n>=26:
        price= 100*n-401
    elif n>=12:
        price= 100*n-101
    elif n >=4:
        price= 100*n-1
    else:
        price= 100*n+49

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

    if not coins>=1:
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
def shop_coin_balance(v):
    return jsonify({"balance":v.coin_balance})


@app.route("/shop/buy_coins", methods=["POST"])
@no_sanctions
@is_not_banned
@no_negative_balance("html")
@validate_formkey
def shop_buy_coins(v):

    coin_count=int(request.form.get("coin_count",1))

    code=request.form.get("promo","")
    promo=get_promocode(code)

    new_txn=PayPalTxn(
        user_id=v.id,
        created_utc=int(time.time()),
        coin_count=coin_count,
        usd_cents=coins_to_price_cents(coin_count, code=promo),
        promo_id= promo.id if promo else None
        )

    g.db.add(new_txn)
    g.db.flush()

    CLIENT.create(new_txn)

    g.db.add(new_txn)
    g.db.commit()

    return redirect(new_txn.approve_url)


@app.route("/shop/negative_balance", methods=["POST"])
@no_sanctions
@is_not_banned
@validate_formkey
def shop_negative_balance(v):

    new_txn=PayPalTxn(
        user_id=v.id,
        created_utc=int(time.time()),
        coin_count=0,
        usd_cents=v.negative_balance_cents
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
def shop_buy_coins_completed(v):

    #look up the txn
    id=request.args.get("txid")
    if not id:
        abort(400)
    id=base36decode(id)
    txn=g.db.query(PayPalTxn
        #).with_for_update(
        ).filter_by(user_id=v.id, id=id, status=1).first()
    #v=g.db.query(User).with_for_update().options(lazyload('*')).filter_by(id=v.id).first()

    if not txn:
        abort(400)

    if txn.promo and not txn.promo.promo_is_active:
        return jsonfy({"error":f"The promo code `{txn.promo.code}` is not currently valid. Please begin a new transaction."}), 422

    if not CLIENT.capture(txn):
        abort(402)

    txn.created_utc=int(time.time())

    g.db.add(txn)
    g.db.flush()

    #successful payment - award coins

    if txn.coin_count:
        v.coin_balance += txn.coin_count
    else:
        v.negative_balance_cents -= txn.usd_cents

    g.db.add(v)
    g.db.commit()

    return render_template(
        "single_txn.html", 
        v=v, 
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

    g.db.flush()



    return "", 204


@app.route("/gift_post/<pid>", methods=["POST"])
@no_sanctions
@is_not_banned
@no_negative_balance("toast")
@validate_formkey
def gift_post_pid(pid, v):

    post=get_post(pid, v=v)

    if post.author_id==v.id:
        return jsonify({"error":"You can't give awards to yourself."}), 403   

    if post.deleted_utc > 0:
        return jsonify({"error":"You can't give awards to deleted posts"}), 403

    if post.is_banned:
        return jsonify({"error":"You can't give awards to removed posts"}), 403

    if post.author.is_deleted:
        return jsonify({"error":"You can't give awards to deleted accounts"}), 403

    if post.author.is_banned and not post.author.unban_utc:
        return jsonify({"error":"You can't give awards to banned accounts"}), 403

    u=get_user(post.author.username, v=v)

    if u.is_blocking:
        return jsonify({"error":"You can't give awards to someone you're blocking."}), 403

    if u.is_blocked:
        return jsonify({"error":"You can't give awards to someone that's blocking you."}), 403


    coins=int(request.args.get("coins",1))

    if not coins:
        return jsonify({"error":"You need to actually give coins."}), 400

    if coins <0:
        return jsonify({"error":"What are you doing, trying to *charge* someone coins?."}), 400

    v=g.db.query(User).with_for_update().options(lazyload('*')).filter_by(id=v.id).first()
    u=g.db.query(User).with_for_update().options(lazyload('*')).filter_by(id=u.id).first()

    if not v.coin_balance>=coins:
        return jsonify({"error":"You don't have that many coins to give!"}), 403


    v.coin_balance -= coins
    u.coin_balance += coins

    g.db.add(v)
    g.db.add(u)
    g.db.flush()
    if v.coin_balance<0:
        g.db.rollback()
        return jsonify({"error":"You don't have that many coins to give!"}), 403

    if not g.db.query(AwardRelationship).filter_by(user_id=v.id, submission_id=post.id).first():
        text=f"Someone liked [your post]({post.permalink}) and has given you a Coin!\n\n"
        if u.premium_expires_utc < int(time.time()):
            text+="Your Coin has been automatically redeemed for one week of [Ruqqus Premium](/settings/premium)."
        else:
            text+="Since you already have Ruqqus Premium, the Coin has been added to your balance. You can keep it for yourself, or give it to someone else."
        send_notification(u, text)



    g.db.commit()

    #create record - uniqueness constraints prevent duplicate award counting
    new_rel = AwardRelationship(
        user_id=v.id,
        submission_id=post.id
        )
    try:
        g.db.add(new_rel)
        g.db.flush()
    except:
        pass
    
    g.db.commit()

    return jsonify({"message":"Tip Successful!"})

@app.route("/gift_comment/<cid>", methods=["POST"])
@no_sanctions
@is_not_banned
@no_negative_balance("toast")
@validate_formkey
def gift_comment_pid(cid, v):

    comment=get_comment(cid, v=v)

    if comment.author_id==v.id:
        return jsonify({"error":"You can't give awards to yourself."}), 403      

    if comment.deleted_utc > 0:
        return jsonify({"error":"You can't give awards to deleted posts"}), 403

    if comment.is_banned:
        return jsonify({"error":"You can't give awards to removed posts"}), 403

    if comment.author.is_deleted:
        return jsonify({"error":"You can't give awards to deleted accounts"}), 403

    if comment.author.is_banned and not comment.author.unban_utc:
        return jsonify({"error":"You can't give awards to banned accounts"}), 403

    u=get_user(comment.author.username, v=v)

    if u.is_blocking:
        return jsonify({"error":"You can't give awards to someone you're blocking."}), 403

    if u.is_blocked:
        return jsonify({"error":"You can't give awards to someone that's blocking you."}), 403

    coins=int(request.args.get("coins",1))

    if not coins:
        return jsonify({"error":"You need to actually give coins."}), 400

    if coins <0:
        return jsonify({"error":"What are you doing, trying to *charge* someone coins?."}), 400

    v=g.db.query(User).with_for_update().options(lazyload('*')).filter_by(id=v.id).first()
    u=g.db.query(User).with_for_update().options(lazyload('*')).filter_by(id=u.id).first()

    if not v.coin_balance>=coins:
        return jsonify({"error":"You don't have that many coins to give!"}), 403
        
    v.coin_balance -= coins
    u.coin_balance += coins
    g.db.add(v)
    g.db.add(u)
    g.db.flush()
    if v.coin_balance<0:
        g.db.rollback()
        return jsonify({"error":"You don't have that many coins to give!"}), 403

    if not g.db.query(AwardRelationship).filter_by(user_id=v.id, comment_id=comment.id).first():
        text=f"Someone liked [your comment]({comment.permalink}) and has given you a Coin!\n\n"
        if u.premium_expires_utc < int(time.time()):
            text+="Your Coin has been automatically redeemed for one week of [Ruqqus Premium](/settings/premium)."
        else:
            text+="Since you already have Ruqqus Premium, the Coin has been added to your balance. You can keep it for yourself, or give it to someone else."

        send_notification(u, text)



    g.db.commit()

    #create record - uniqe prevents duplicates
    new_rel = AwardRelationship(
        user_id=v.id,
        comment_id=comment.id
        )
    try:
        g.db.add(new_rel)
        g.db.flush()
    except:
        pass
    
    g.db.commit()

    return jsonify({"message":"Tip Successful!"})


@app.route("/paypaltxn/<txid>")
@auth_required
def paypaltxn_txid(txid, v):

    txn = get_txid(txid)

    if txn.user_id != v.id and v.admin_level<4:
        abort(403)

    return render_template(
        "single_txn.html", 
        v=v, 
        txns=[txn]
        )
