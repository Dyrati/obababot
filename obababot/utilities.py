import discord
import re
import os
import json
from copy import deepcopy

prefix = os.getenv("PREFIX","$")
usercommands = {}
aliases = {}
client = discord.Client(intents=discord.Intents.default())
UserData = {}
ReactMessages = {}
RegisteredFuncs = {}
character_limit = 2000


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
        com = re.match("\S+", message.content)
        if com and com.group() in usercommands: return True
    return False


def split_multiline(text, maxlen=float("inf")):
    assert maxlen > 0, f"Cannot use length {maxlen}"
    lines = text.splitlines()
    response = []
    length = 0
    pos = 0
    for i,line in enumerate(lines):
        length += len(line) + 1
        if length > maxlen:
            response.append("\n".join(lines[pos:i]))
            pos = i
            length = len(line)
    if pos < len(lines):
        response.append("\n".join(lines[pos:]))
    return response


async def reply(message, text):
    ID = message.author.id
    if UserData[ID].temp.get("raw"):
        text = text.replace("`", "")
    if len(text) > character_limit:
        code_block = re.match(r"```\n?(.*?)\n?```$", text, re.DOTALL)
        if code_block:
            response = split_multiline(code_block.group(1), character_limit-8)
            response = [f"```\n{r}\n```" for r in response]
        else:
            response = split_multiline(text, character_limit)
        for msg in response:
            sent = await message.channel.send(msg)
            UserData[ID].responses[-1].append(sent)
    else:
        sent = await message.channel.send(text)
    UserData[ID].responses[-1].append(sent)
    return sent


async def from_url(url):
    ids = list(map(int, url[len("https://discord.com/channels/"):].split("/")))
    server = client.get_guild(ids[0])
    channel = server.get_channel(ids[1])
    if len(ids) == 3:
        message = await channel.fetch_message(ids[2])
        return server, channel, message
    else:
        return server, channel


async def get_attachment(message, *args):
    if not message.attachments:
        assert args and args[0].startswith("https://discord.com/channels/"), \
            "Expected an attachment or a link to a message with an attachment"
        server, channel, message = await from_url(args[0])
    return message.attachments[0]


def textparser(filename):
    with open(filename) as f:
        lines = filter(lambda x: x, f.read().splitlines())
    section = re.compile(r"^\[(.*?)\]$")
    groups = {}
    for line in lines:
        m = section.match(line)
        if m:
            current = []
            groups[m.group(1)] = current
        else:
            current.append(line)
    return groups

def load_text():
    text = {}
    text["pcnames"] = ["Isaac", "Garet", "Ivan", "Mia", "Felix", "Jenna", "Sheba", "Piers"]
    text["elements"] = ["Venus", "Mercury", "Mars", "Jupiter", "Neutral"]
    text["GS1"] = {}
    text["GS2"] = {}
    mtoken = re.compile(r"{\d*}")
    dirname = os.path.dirname(__file__)
    path = lambda f: os.path.join(dirname, f)
    with open(path("text/GS1text.txt")) as f:
        lines = f.read().splitlines()
        text["GS1"]["item_descriptions"] = lines[117:386]
        lines = list(map(lambda x: mtoken.sub("", x), lines))
        text["GS1"]["items"] = lines[386:655]
        text["GS1"]["abilities"] = lines[819:1338]
        text["GS1"]["move_descriptions"] = lines[1338:1857]
        text["GS1"]["classes"] = lines[1857:2060]
        text["GS1"]["enemynames"] = lines[655:819]
        text["GS1"]["areas"] = lines[2459:2567]
        text["GS1"]["maps"] = lines[2567:2768]
        text["GS1"]["djinn"] = lines[1119:1199]
    with open(path("text/GS2text.txt")) as f:
        lines = f.read().splitlines()
        text["GS2"]["item_descriptions"] = lines[146:607]
        lines = list(map(lambda x: mtoken.sub("", x), lines))
        text["GS2"]["items"] = lines[607:1068]
        text["GS2"]["enemynames"] = lines[1068:1447]
        text["GS2"]["abilities"] = lines[1447:2181]
        text["GS2"]["move_descriptions"] = lines[2181:2915]
        text["GS2"]["classes"] = lines[2915:3159]
        text["GS2"]["areas"] = lines[3672:3770]
        text["GS2"]["maps"] = lines[3770:4095]
        text["GS2"]["djinn"] = lines[1747:1827]
    text.update(**textparser(path("text/customtext.txt")))
    return text


class Database(dict):
    def __init__(self):
        self.namemap = {}
        self._mbracket = re.compile(r" \(.\)$")
    def new_table(self, tablename, table):
        self[tablename] = table
        self.namemap[tablename] = {}
        for obj in table: self.add_entry(tablename, obj)
    def add_entry(self, tablename, obj):
        if not obj.get("name"): return
        name = self.normalize(obj["name"])
        if name != self._mbracket.sub("", name):
            self.namemap[tablename][name] = [obj]
            name = self._mbracket.sub("", name)
        if name in self.namemap[tablename]:
            self.namemap[tablename][name].append(obj)
        else:
            self.namemap[tablename][name] = [obj]
    def get(self, tablename, name, instance=0):
        name = self.normalize(name)
        if name not in self.namemap[tablename]: return None
        else: return self.namemap[tablename][name][instance]
    def get_all(self, tablename, name):
        name = self.normalize(name)
        if name not in self.namemap[tablename]: return None
        else: return self.namemap[tablename][name]
    def normalize(self, name):
        return name.lower().replace("'","").replace("-"," ")

class TextMap(Database):
    def __init__(self):
        self.namemap = {}
        self.counts = {}
    def new_table(self, tablename, table):
        self[tablename] = table
        self.namemap[tablename] = {}
        self.counts[tablename] = 0
        for obj in table: self.add_entry(tablename, obj)
    def add_entry(self, tablename, name):
        name = self.normalize(name)
        self.namemap[tablename][name] = self.counts[tablename]
        self.counts[tablename] += 1
    def get(self, tablename, name):
        return self.namemap[tablename].get(self.normalize(name))


DataTables, Text, Emojis, Images = Database(), TextMap(), {}, {}
def load_data():
    global DataTables, Text, Emojis
    dirname = os.path.dirname(__file__)
    print("Loading database...", end="\r")
    DataTables.clear(); Text.clear(), Emojis.clear(), Images.clear()
    for name in [
        "djinndata", "enemydata", "itemdata", "abilitydata", "pcdata",
        "summondata", "classdata", "elementdata", "encounterdata",
        "mapdata", "room_references", "enemygroupdata"]:
        for i in [2,1]:
            with open(os.path.join(dirname, rf"data/GS{i}/{name}.json")) as f:
                DataTables.new_table(f"{name}{i}", json.load(f))
                if name == "enemydata":
                    hard_enemies = deepcopy(DataTables[f"enemydata{i}"])
                    for entry in hard_enemies:
                        entry["HP"] = min(0x3FFF, int(1.5*entry["HP"]))
                        entry["ATK"] = int(1.25*entry["ATK"])
                        entry["DEF"] = int(1.25*entry["DEF"])
                    DataTables.new_table(f"enemydata{i}-h", hard_enemies)
        DataTables.new_table(name, DataTables[f"{name}2"])
    text_data = load_text()
    for k,v in text_data.items(): Text.new_table(k,v)
    for k,v in text_data["GS1"].items(): Text.new_table(k+"1",v)
    for k,v in text_data["GS2"].items(): Text.new_table(k+"2",v)
    match_emoji = re.compile(r"<.*?:(.*?):(.*?)>")
    for emoji in client.emojis:
        m = match_emoji.match(str(emoji))
        Emojis[m.group(1)] = m.group()
    for path, dirs, files in os.walk(os.path.join(dirname, "sprites")):
        for f in files: Images[os.path.splitext(f)[0]] = os.path.join(path, f)
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
        command = re.match("\S+", text).group()
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
    'True':True, 'False':False, 'None':None, 'pi':math.pi, 'e': math.exp(1),
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
        self.pos = (0, 0)
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
        self.pos = max(xmax, x), y+1
        return self.pos
    def __str__(self):
        return "\n".join(("".join(row) for row in self.charmap))


class User:
    def __init__(self, ID):
        self.ID = ID
        self.temp = {}
        self.vars = dict(_=None, **mfuncs)
        self.responses = []
        self.filedata = None
        self.party = None


async def set_buttons(message, buttons, func):
    create_task = client.loop.create_task
    async def inner(message, user, emoji):
        if str(emoji) not in buttons: return
        task1 = create_task(func(message, user, buttons[str(emoji)]))
        task2 = create_task(message.remove_reaction(emoji, user))
        await task1, task2
    if message in ReactMessages:
        await message.clear_reactions()
    ReactMessages[message] = inner
    tasks = [create_task(message.add_reaction(b)) for b in buttons]
    for t in tasks: await t

async def clear_buttons(message):
    ReactMessages.pop(message)
    await message.clear_reactions()


def register_on_message(channel, callback):
    assert isinstance(channel, discord.TextChannel), "Expected a text channel"
    RegisteredFuncs[channel] = callback
def register_remove(channel):
    RegisteredFuncs.pop(channel)