import secrets

from ruqqus.helpers.wrappers import *
from ruqqus.helpers.get import *
from ruqqus.helpers.session import *
from ruqqus.helpers.base36 import *
from ruqqus.helpers.aws import *
from ruqqus.__main__ import app

##############
#            #
#  PICTURES  #
#            #
##############


@app.route("/chat_upload", methods=["POST"])
@is_not_banned
def chat_upload_image(v):

    if not v.has_premium:
        abort(403)


    file = request.files['image']
    if not file.content_type.startswith('image/'):
        abort(400)

    now=int(time.time())
    now=base36encode(now)
    name = f'chat/{now}/{secrets.token_urlsafe(8)}'
    upload_file(name, file)

    check_csam_url(f"https://{BUCKET}/{name}", v, lambda:delete_file(name))

    return jsonify({'url':f"https://{BUCKET}/{name}"})





##############
#            #
#   ROUTES   #
#            #
##############



@app.route("/+<guildname>/chat", methods=["GET"])
@is_not_banned
def guild_chat(guildname, v):



    board=get_guild(guildname)


    if board.over_18 and not (v and v.over_18) and not session_over18(board):
        t = int(time.time())
        return render_template(
            "errors/nsfw.html",
            v=v,
            t=t,
            lo_formkey=make_logged_out_formkey(t),
            board=board
            )

    return render_template(
        "chat/chat.html", 
        b=board, 
        v=v,
        is_subscribed=(v and board.has_subscriber(v))
        )

