import discord
import re
import os
import json

prefix = os.getenv("PREFIX","$")
usercommands = {}
aliases = {}
client = discord.Client()
UserData = {}
ReactMessages = {}


def command(f=None, alias=None, prefix=prefix):
    def decorator(f):
        global usercommands
        name = prefix + f.__name__.strip("_")
        if alias: aliases[alias] = name
        usercommands[name] = f
        async def inner(*args, **kwargs):
            f(*args, **kwargs)
        return inner
    if f: return decorator(f)
    else: return decorator


def is_command(message):
    if message.author == client.user: return False
    if message.guild.name == "Golden Sun Speedrunning" and message.channel.name != "botspam":
        return False
    for alias in aliases:
        if message.content.startswith(alias): return True
    else:
        if message.content.split(" ",1)[0] in usercommands: return True
    return False


async def reply(message, text):
    ID = message.author.id
    if UserData[ID].temp.get("raw"):
        text = text.replace("`", "")
    if len(str(text)) > 2000:
        sent = await message.channel.send("output exceeded 2000 characters")
    else:
        sent = await message.channel.send(text)
    UserData[ID].responses[-1].append(sent)
    return sent


async def send(url, text):
    ID_list = url[len("https://discord.com/channels/"):].split("/")
    serverID, channelID = (int(i) for i in ID_list)
    channel = client.get_guild(serverID).get_channel(channelID)
    await channel.send(text)


def load_text():
    text = {}
    text["pcnames"] = ["Isaac", "Garet", "Ivan", "Mia", "Felix", "Jenna", "Sheba", "Piers"]
    text["elements"] = ["Venus", "Mercury", "Mars", "Jupiter", "Neutral"]
    mtoken = re.compile(r"{\d*}")
    with open(r"text/GS1text.txt") as f:
        lines = f.read().splitlines()
        lines = list(map(lambda x: mtoken.sub("", x), lines))
        text["areas1"] = lines[2459:2567]
        text["maps1"] = lines[2567:2768]
    with open(r"text/GS2text.txt") as f:
        lines = f.read().splitlines()
        text["item_descriptions"] = lines[146:607]
        lines = list(map(lambda x: mtoken.sub("", x), lines))
        text["items"] = lines[607:1068]
        text["enemynames"] = lines[1068:1447]
        text["abilities"] = lines[1447:2181]
        text["move_descriptions"] = lines[2181:2915]
        text["classes"] = lines[2915:3159]
        text["areas2"] = lines[3672:3770]
        text["maps2"] = lines[3770:4095]
        text["djinn"] = lines[1747:1827]
    with open(r"text/customtext.txt") as f:
        lines = f.read().splitlines()
        text["ability_effects"] = lines[0:92]
        text["equipped_effects"] = lines[92:120]
    return text


def namedict(jsonobj):
    out = {}
    for entry in jsonobj:
        if not entry.get("name"): continue
        name = entry["name"].lower()
        if out.get(name):
            out[name].append(entry)
        else:
            out[name] = [entry]
        out[name.replace("'","")] = out[name]
        out[name.replace("-"," ")] = out[name]
    return out


DataTables, Namemaps, Text = {}, {}, {}
def load_data():
    global DataTables, Namemaps, Text
    from copy import deepcopy
    print("Loading database...", end="\r")
    DataTables.clear(); Namemaps.clear(); Text.clear()
    for name in [
            "djinndata", "summondata", "enemydata", "itemdata", "abilitydata", "pcdata",
            "classdata", "elementdata", "encounterdata", "mapdata1", "mapdata2",
            "room_references1", "room_references2", "enemygroupdata"]:
        with open(rf"data/{name}.json") as f:
            DataTables[name] = json.load(f)
            if name == "enemydata":
                DataTables["enemydata-h"] = deepcopy(DataTables["enemydata"])
                for entry in DataTables["enemydata-h"]:
                    entry["HP"] = min(0x3FFF, int(1.5*entry["HP"]))
                    entry["ATK"] = int(1.25*entry["ATK"])
                    entry["DEF"] = int(1.25*entry["DEF"])
    for k,v in DataTables.items():
        Namemaps[k] = namedict(v)
    Text.update(**load_text())
    mfuncs.update(**DataTables)
    print("Loaded database    ")


mquote = re.compile(r"\".*?\"|\'.*?\'")
mkwarg = re.compile(r"([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*([^ =]\S*)")
mtoken = re.compile(r"{(\d+)}")
def parse(s):
    groups = []
    args, kwargs = [], {}
    def addtoken(m):
        groups.append(m.group())
        return f"{{{len(groups)-1}}}"
    def addkwarg(m):
        kwargs[m.group(1)] = m.group(2)
    def gettoken(m):
        return groups[int(m.group(1))]
    s = mquote.sub(addtoken, s)
    s = mkwarg.sub(addkwarg, s)
    args = re.findall(r"\S+", s)
    for i, arg in enumerate(args):
        args[i] = mtoken.sub(gettoken, arg)
    for k,v in kwargs.items():
        kwargs[k] = mtoken.sub(gettoken, v)
    return args, kwargs


def extractcommand(text):
    extrakwargs = {}
    for alias, command in aliases.items():
        if text.startswith(alias):
            args, kwargs = parse(text[len(alias):].replace("`",""))
            return command, args, kwargs
    else:
        command = text.split(" ",1)[0]
        if command not in usercommands: return
        args, kwargs = parse(text[len(command)+1:].replace("`",""))
        return command, args, kwargs


import math
import random
def rand(*args):
    if len(args) == 1: return random.randint(1, *args)
    elif args: return random.randint(*args)
    else: return random.random()
mfuncs = {
    'abs':abs, 'round':round, 'min':min, 'max':max, 'rand':rand,
    'bin':bin, 'hex':hex, 'len':len, 'sum': sum, 'int': int, 'str': str,
    'True':True, 'False':False, 'pi':math.pi, 'e': math.exp(1),
    'sin':math.sin, 'cos':math.cos, 'tan':math.tan, 'sqrt':math.sqrt,
    'log':math.log, 'exp':math.exp,
}


def wrap(iterable, maxwidth, pos=0):
    group = "{}" if isinstance(iterable, (dict, set)) else "[]"
    if not iterable: return group
    out = group[0]; pos += 1
    initpos = pos
    if isinstance(iterable, dict):
        iterable = (f"{k}: {v}" for k,v in iterable.items())
    else:
        iterable = iter(iterable)
    entry = str(next(iterable))
    out += entry; pos += len(entry)
    for entry in iterable:
        entry = str(entry)
        pos += len(entry) + 2
        if pos >= maxwidth-1:
            pos = initpos
            out += ",\n" + " "*pos + entry
            pos += len(entry)
        else:
            out += ", " + entry
    out += group[1]
    return out


def dictstr(dictionary, js=False, maxwidth=77, sep="  "):
    if js: return json.dumps(dictionary, indent=4)
    out = ""
    maxlen = len(max(dictionary.keys(), key=lambda x: len(x)))
    for k,v in dictionary.items():
        out += f"\n{k+sep:<{maxlen+len(sep)}}"
        if hasattr(v, "__iter__") and not isinstance(v, (str, bytes)):
            out += wrap(v, maxwidth, maxlen+2)
        else:
            out += str(v)
    return out[1:]


def tableH(dictlist, fields=None, spacing=1, border=None, headers=True):
    if not dictlist: return ""
    fields = fields or dictlist[0].keys()
    for f in fields:
        for d in dictlist:
            d[f] = d.get(f, None)
    widths = {k: 0 for k in fields}
    if headers: widths = {k: len(k) for k in fields}
    for d in dictlist:
        for k in fields:
            widths[k] = max(widths[k], len(str(d[k])))
    out = []
    spacing = " "*spacing
    if headers:
        out.append(spacing.join((f"{k:^{w}.{w}}" for k,w in widths.items())))
    if border:
        out.append(spacing.join((border*w for w in widths.values())))
    template = spacing.join((f"{{{k}:<{w}.{w}}}" for k,w in widths.items()))
    for d in dictlist:
        out.append(template.format(**{k:str(v) for k,v in d.items()}))
    return "\n".join(out)


def tableV(dictlist, spacing=2):
    columns = [[]] + [[] for d in dictlist]
    for i,d in enumerate(dictlist):
        for k,v in d.items():
            if hasattr(v, "__iter__") and not isinstance(v, (str, bytes)):
                count = max((len(x[k]) for x in dictlist))
                v = iter(v)
                start = True
                for j in range(count):
                    if start: columns[0].append(k); start = False
                    else: columns[0].append("")
                    try: columns[i+1].append(str(next(v)))
                    except StopIteration: columns[i+1].append("")
            else:
                columns[0].append(k)
                columns[i+1].append(str(v))
    widths = [len(max(c, key=len)) for c in columns]
    spacing = " "*spacing
    template = spacing.join((f"{{:{w}.{w}}}" for w in widths))
    return "\n".join(template.format(*row) for row in zip(*columns))


class Charmap:
    def __init__(self):
        self.charmap = []
    def addtext(self, text, coords):
        x,y = coords
        xmax = x
        cm = self.charmap
        cm.extend(([] for i in range(y-len(cm)+1)))
        for char in text:
            if char == "\n":
                xmax = max(xmax, x)
                x = coords[0]
                y += 1
            else:
                if y >= len(cm):
                    cm.extend(([] for i in range(y-len(cm)+1)))
                if x >= len(cm[y]):
                    cm[y].extend((" " for i in range(x-len(cm[y])+1)))
                cm[y][x] = char
                x += 1
        return max(xmax, x), y+1
    def __str__(self):
        return "\n".join(("".join(row) for row in self.charmap))


class User:
    def __init__(self, ID):
        self.ID = ID
        self.temp = {}
        self.vars = {}
        self.responses = []
        self.live_response = {}
        self.save = None


async def add_buttons(message, buttons, func):
    create_task = client.loop.create_task
    async def newfunc(message, user, emoji):
        if emoji not in buttons: return
        task1 = create_task(func(message, user, buttons[emoji]))
        task2 = create_task(message.remove_reaction(emoji, user))
        await task1, task2
    if message in ReactMessages:
        await message.clear_reactions()
    ReactMessages[message] = newfunc
    tasks = [create_task(message.add_reaction(b)) for b in buttons]
    for t in tasks: await t


async def clear_buttons(message):
    ReactMessages.pop(message)
    await message.clear_reactions()
