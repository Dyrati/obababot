import os
import io
import string
import re
from PIL import Image

tiles = {}
for s in string.ascii_lowercase: tiles[s] = "lower_" + s
for s in string.ascii_uppercase: tiles[s] = "upper_" + s
for s in string.digits: tiles[s] = s
tiles.update(**{
    "!": "exclamationmark",
    ".": "period",
    ",": "comma",
    "'": "apostrophe",
    "?": "questionmark",
    "&": "and",
    "^": "caret",
    "@": "at",
    "[": "bracket1",
    "]": "bracket2",
    ":": "colon",
    "-": "dash",
    "$": "dollar",
    "=": "equals",
    ">": "greaterthan",
    "<": "lessthan",
    "|": "verticalline",
    "#": "number",
    "(": "parentheses1",
    ")": "parentheses2",
    "%": "percent",
    "+": "plus",
    '"': "quote",
    ";": "semicolon",
    "/": "slash",
    "~": "tilde",
    "_": "underscore",
    "\\": "backslash",
    "{": "curlybrace1",
    "}": "curlybrace2",
    "*": "asterisk",
})

maxchar = (8,8)
dirname = "obababot/sprites/text/"
for k,v in tiles.items():
    tiles[k] = Image.open(dirname + f"default/{v}.gif").convert("RGBA")
for filename in os.listdir(dirname + "edges/"):
    name, ext = os.path.splitext(filename)
    tiles[name] = Image.open(dirname + "edges/" + filename).convert("RGBA")

def get_vectors(im):
    w,h = im.size
    check = lambda x,y: im.getpixel((x,y))[3] > 0
    return [(x,y) for y in range(h) for x in range(w) if check(x,y)]

def check_collision(im, vectors, coords=(0,0)):
    x,y = coords
    check = lambda v: im.getpixel((v[0]+x, v[1]+y))[3] > 0
    return any(map(check, vectors))

def kerning_paste(target, src, coords):
    coords = list(coords)
    vectors = get_vectors(src)
    coords[1] += maxchar[1]-src.height
    x,y = coords
    for i in range(maxchar[0]):
        if check_collision(target, vectors, coords=(x+i, y)) \
                or check_collision(target, vectors, coords=(x+i, y+1)):
            coords[0] = x+i+2
    target.paste(src, coords.copy(), mask=src)  # mutates the coords argument
    endpos = [coords[i] + max(v[i] for v in vectors) + 1 for i in range(2)]
    return coords + endpos

def text_to_img_kerning(text):
    w, h = maxchar
    width = max(map(len, text.splitlines()))
    height = len(text.splitlines())
    out = Image.new("RGBA", ((width+2)*w, (height+2)*(h*3//2)))
    y, xmax = 0, 0
    for line in text.splitlines():
        box = [0,0,0,0]
        checkv = False
        for char in line:
            if char not in tiles:
                box[0] += w; box[2] += w; checkv = True; continue
            x = box[2]+1 if checkv else box[0]
            box = kerning_paste(out, tiles[char], (x, y))
            checkv = box[3]-box[1] <= h//2
        xmax = max(xmax, box[2])
        y += h*3//2
    return out.crop((0, 0, xmax, y-h//2))

def text_to_img(text):
    w, h = maxchar
    width = max(map(len, text.splitlines()))
    height = len(text.splitlines())
    out = Image.new("RGBA", ((width+2)*w, (height+2)*(h*3//2)))
    y, xmax = 0, 0
    for line in text.splitlines():
        x = 0
        for char in line:
            if char not in tiles: x += w; continue
            tile = tiles[char]
            out.paste(tile, (x, y + h-tile.height), mask=tile)
            x += max(v[0] for v in get_vectors(tile)) + 2
        xmax = max(xmax, x-1)
        y += h*3//2
    return out.crop((0, 0, xmax, y-h//2))

def add_background(im):
    w, h = maxchar
    bg = Image.new("RGBA", (2*w+im.size[0], 2*w+im.size[1]), color=(0,96,128,255))
    for x in range(w, bg.width, w):
        bg.paste(tiles["up"], (x,0))
        bg.paste(tiles["down"], (x,bg.height-h))
    for y in range(h, bg.height, h):
        bg.paste(tiles["left"], (0,y))
        bg.paste(tiles["right"], (bg.width-w,y))
    bg.paste(tiles["upleft"], (0,0))
    bg.paste(tiles["upright"], (bg.width-w,0))
    bg.paste(tiles["downleft"], (0, bg.height-h))
    bg.paste(tiles["downright"], (bg.width-w, bg.height-h))
    bg.paste(im, maxchar, mask=im)
    return bg

def textbox(text):
    out = text_to_img(text)
    out = add_background(out)
    out = out.resize((out.width*2, out.height*2), resample=Image.BOX)
    return out

def to_buffer(im):
    b = io.BytesIO()
    im.save(b, format="PNG")
    b.seek(0)
    return b
