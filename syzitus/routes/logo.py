from flask import g, session, abort, jsonify, send_file, redirect
import PIL
from PIL import ImageFont, ImageDraw
from werkzeug.security import safe_join
from io import BytesIO

from syzitus.helpers.wrappers import *
from syzitus.classes import *
from syzitus.mail import *
from syzitus.__main__ import app, limiter, debug, cache

@app.get(f"/logo/jumbotron/<color>/{app.config['SITE_NAME'][0].lower()}")
@cf_cache
#@cache.memoize()
def get_logo_jumbotron(color):

    primary_r=int(color[0:2], 16)
    primary_g=int(color[2:4], 16)
    primary_b=int(color[4:6], 16)

    if (primary_r+primary_g+primary_b)//3 > 0xcf:
        primary=(
            (primary_r + 0xaf)//2,
            (primary_g + 0xaf)//2,
            (primary_b + 0xaf)//2,
            255
            )
    else:
        primary = (primary_r, primary_g, primary_b, 255)



    base_layer = PIL.Image.open(f"{app.config['RUQQUSPATH']}/assets/images/logo/logo_base.png")
    text_layer = PIL.Image.new("RGBA", base_layer.size, color=(255,255,255,0))

    #make base layer white with 50% opacity
    ImageDraw.floodfill(
        base_layer,
        (base_layer.size[0]//2, base_layer.size[1]//2),
        value=(255, 255, 255, 128)
        )

    #tilted letter layer
    font = ImageFont.truetype(
        f"{app.config['RUQQUSPATH']}/assets/fonts/Arial-bold.ttf", 
        size=base_layer.size[1]//2
    )

    letter = app.config["SITE_NAME"][0:1].lower()
    box = font.getbbox(letter)

    d = ImageDraw.Draw(text_layer)
    d.text(
        (
            base_layer.size[0] // 2 - box[2] // 2, 
            base_layer.size[0] // 2 - (box[3]+box[1]) // 2
            ),
        letter, 
        font=font,
        fill=primary
        )

    text_layer = text_layer.rotate(
        angle=20, 
        expand=False, 
        fillcolor=(255,255,255,0),
        center=(
            text_layer.size[0]//2,
            text_layer.size[0]//2
            ),
        resample=PIL.Image.BILINEAR)

    #put tilted letter on speech bubble
    base_layer = PIL.Image.alpha_composite(base_layer, text_layer)

    #put speech bubble on background
    background_layer = PIL.Image.new("RGBA", base_layer.size, color=primary)
    unit_block = PIL.Image.alpha_composite(background_layer, base_layer)

    #tilt and re-size unit block
    unit_block = unit_block.rotate(
        angle=25,
        expand=True,
        fillcolor=primary,
        resample=PIL.Image.BILINEAR
        )

    unit_block = unit_block.resize(
        (
            unit_block.size[0]//10,
            unit_block.size[1]//10
            ),
        resample=PIL.Image.BILINEAR
        )

    width_units=19
    height_units=11

    output=PIL.Image.new(
        "RGBA", 
        (
            unit_block.size[0]*width_units,
            unit_block.size[1]*height_units
            ), 
        color=(255,255,255,0)
        )


    for i in range(width_units):
        for j in range(height_units):

            output.paste(
                unit_block,
                (
                    unit_block.size[0]*i,
                    unit_block.size[1]*j
                    )
                )

    bytesout=BytesIO()
    output.save(bytesout, format="PNG")
    bytesout.seek(0)
    return send_file(bytesout, mimetype="image/png")

@app.get(app.config["IMG_URL_LOGO_MAIN"])
@cf_cache
#@cache.memoize()
def get_logo_main():

    primary_r=int(app.config["COLOR_PRIMARY"][0:2], 16)
    primary_g=int(app.config["COLOR_PRIMARY"][2:4], 16)
    primary_b=int(app.config["COLOR_PRIMARY"][4:6], 16)

    primary = (primary_r, primary_g, primary_b, 255)

    base_layer = PIL.Image.open(f"{app.config['RUQQUSPATH']}/assets/images/logo/logo_base.png")
    text_layer = PIL.Image.new("RGBA", base_layer.size, color=(255,255,255,0))

    #flood fill main logo shape
    ImageDraw.floodfill(
        base_layer,
        (base_layer.size[0]//2, base_layer.size[1]//2),
        value=primary
        )


    #tilted letter layer
    font = ImageFont.truetype(
        f"{app.config['RUQQUSPATH']}/assets/fonts/Arial-bold.ttf", 
        size=int(min(base_layer.size)//2)
    )

    letter = app.config["SITE_NAME"][0:1].lower()
    box = font.getbbox(letter)

    d = ImageDraw.Draw(text_layer)
    d.text(
        (
            base_layer.size[0] // 2 - box[2] // 2, 
            base_layer.size[0] // 2 - (box[3]+box[1]) // 2
            ),
        letter, 
        font=font,
        fill=(255,255,255,255)
        )

    text_layer = text_layer.rotate(
        angle=20, 
        expand=False, 
        fillcolor=(255,255,255,0),
        center=(
            text_layer.size[0]//2,
            text_layer.size[0]//2
            ),
        resample=PIL.Image.BILINEAR)

    output=PIL.Image.alpha_composite(base_layer, text_layer)

    bytesout=BytesIO()
    output.save(bytesout, format="PNG")
    bytesout.seek(0)
    return send_file(bytesout, mimetype="image/png")


@app.get(app.config["IMG_URL_LOGO_WHITE"])
@cf_cache
#@cache.memoize()
def get_logo_white():

    primary_r=int(app.config["COLOR_PRIMARY"][0:2], 16)
    primary_g=int(app.config["COLOR_PRIMARY"][2:4], 16)
    primary_b=int(app.config["COLOR_PRIMARY"][4:6], 16)

    primary = (primary_r, primary_g, primary_b, 255)

    base_layer = PIL.Image.open(f"{app.config['RUQQUSPATH']}/assets/images/logo/logo_base.png")
    text_layer = PIL.Image.new("RGBA", base_layer.size, color=(255,255,255,0))

    #tilted letter layer
    font = ImageFont.truetype(
        f"{app.config['RUQQUSPATH']}/assets/fonts/Arial-bold.ttf", 
        size=int(min(base_layer.size)//2)
    )

    letter = app.config["SITE_NAME"][0:1].lower()
    box = font.getbbox(letter)

    d = ImageDraw.Draw(text_layer)
    d.text(
        (
            base_layer.size[0] // 2 - box[2] // 2, 
            base_layer.size[0] // 2 - (box[3]+box[1]) // 2
            ),
        letter, 
        font=font,
        fill=primary
        )

    text_layer = text_layer.rotate(
        angle=20, 
        expand=False, 
        fillcolor=(255,255,255,0),
        center=(
            text_layer.size[0]//2,
            text_layer.size[0]//2
            ),
        resample=PIL.Image.BILINEAR)

    output=PIL.Image.alpha_composite(base_layer, text_layer)


    bytesout=BytesIO()
    output.save(bytesout, format="PNG")
    bytesout.seek(0)
    return send_file(bytesout, mimetype="image/png")

@app.get(f"/logo/<kind>/{app.config['COLOR_PRIMARY'].lower()}/{app.config['SITE_NAME'][0].lower()}/<width>/<height>")
@cf_cache
#@cache.memoize()
def get_assets_images_splash(kind, width, height, color=None, letter=None):

    try:
        width=int(width)
        height=int(height)
    except:
        abort(404)

    if max(width, height)>4500:
        abort(404)

    if kind not in ["splash", "thumb"]:
        abort(404)

    color = color or app.config["COLOR_PRIMARY"]

    primary_r=int(color[0:2], 16)
    primary_g=int(color[2:4], 16)
    primary_b=int(color[4:6], 16)

    primary = (primary_r, primary_g, primary_b, 255)

    base_layer = PIL.Image.new("RGBA", (width, height), color=primary)

    text_layer = PIL.Image.new("RGBA", (width, height), color=(255,255,255,0))

    size=int(min(height, width)//1.2)

    font = ImageFont.truetype(
        f"{app.config['RUQQUSPATH']}/assets/fonts/Arial-bold.ttf", 
        size=size
        )

    letter = app.config["SITE_NAME"][0:1].lower()
    box = font.getbbox(letter)

    d = ImageDraw.Draw(text_layer)
    d.text(
        (
            width // 2 - box[2] // 2, 
            height // 2 - (box[3]+box[1]) // 2
            ),
        letter, 
        font=font,
        fill=(255,255,255,255)
        )

    text_layer = text_layer.rotate(
        angle=20, 
        expand=False, 
        fillcolor=primary,
        resample=PIL.Image.BILINEAR)

    if kind=="thumb":
        font = ImageFont.truetype(
            f"{app.config['RUQQUSPATH']}/assets/fonts/Arial-bold.ttf", 
            size=int(size*0.6)
            )
        fullbox=font.getbbox(app.config["SITE_NAME"].lower())

        if fullbox[2]>width:
            abort(400)

        d = ImageDraw.Draw(text_layer)
        d.text(
            (
                width//2 - fullbox[2]//2,
                height//2 + (box[3]-box[1]) // 2 + int(size*0.2)
                ),
            app.config["SITE_NAME"].lower(),
            font=font,
            fill=(255,255,255,255)
            )

    output=PIL.Image.alpha_composite(base_layer, text_layer)

    bytesout=BytesIO()
    output.save(bytesout, format="PNG")
    bytesout.seek(0)
    return send_file(bytesout, mimetype="image/png")

@app.get("/logo/fontawesome/<style>/<icon>")
@app.get("/logo/fontawesome/<style>/<icon>/<color>")
@app.get("/logo/fontawesome/<style>/<icon>/<color>/<size>")
@cf_cache
def logo_fontawesome_icon(style, icon, color=None, size=500):

    size=int(size)

    if not color:
        color=app.config['COLOR_PRIMARY']

    primary_r=int(color[0:2], 16)
    primary_g=int(color[2:4], 16)
    primary_b=int(color[4:6], 16)

    primary = (primary_r, primary_g, primary_b, 255)

    base_layer = PIL.Image.new("RGBA", (size, size), color=primary)
    text_layer = PIL.Image.new("RGBA", (size, size), color=(255,255,255,0))

    filenames={
        'brands':'fa-brands-400',
        'light':'fa-light-300',
        'regular':'fa-regular-400',
        'sharp-regular':'fa-sharp-regular-400',
        'sharp-solid':'fa-sharp-solid-900',
        'solid':'fa-solid-900',
        'thin':'fa-thin-100'
    }
    if style not in filenames:
        abort(404)

    filename=filenames[style]

    font = ImageFont.truetype(
        f"{app.config['RUQQUSPATH']}/assets/fontawesome/webfonts/{filename}.ttf", 
        size=size * 3 // 5
        )

    icon=icon[0]

    box=font.getbbox(icon)

    d = ImageDraw.Draw(text_layer)
    d.text(
        (
            size // 2 - box[2] // 2 + 1, 
            size // 2 - (box[3]+box[1]) // 2 + 1
            ),
        icon, 
        font=font,
        fill=(255,255,255,255)
        )

    output=PIL.Image.alpha_composite(base_layer, text_layer)

    bytesout=BytesIO()
    output.save(bytesout, format="PNG")
    bytesout.seek(0)
    return send_file(bytesout, mimetype="image/png")

@app.get("/favicon.ico")
@cf_cache
def get_favicon_ico():
    return get_assets_images_splash("splash", 48, 48)

@app.get("/apple-touch-icon.png")
@app.get("/apple-touch-icon-precomposed.png")
@app.get("/apple-touch-icon-<width>x<height>-precomposed.png")
@app.get("/apple-touch-icon-<width>x<height>.png")
@cf_cache
def get_apple_touch_icon_sized_png(width=192, height=192):

    width=int(width)
    height=int(height)
    return get_assets_images_splash('splash', width, height)
