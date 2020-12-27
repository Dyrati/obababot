import re
import json
from copy import deepcopy


prefix = "$"
usercommands = {}
aliases = {}
client = None
def command(f=None, alias=None, prefix=prefix):
    def decorator(f):
        global usercommands
        if alias: aliases[re.compile(alias)] = prefix + f.__name__
        usercommands[prefix + f.__name__] = f
        async def inner(*args, **kwargs):
            f(*args, **kwargs)
        return inner
    if f: return decorator(f)
    else: return decorator


def to_async(func):
    async def inner(*args, **kwargs):
        return func(*args, **kwargs)
    return inner


async def reply(message, text):
    if len(str(text)) > 2000:
        await message.channel.send("output exceeded 2000 characters")
    else:
        await message.channel.send(text)


def namedict(jsonobj):
    out = {}
    for entry in jsonobj:
        if not entry.get("name"): continue
        name = entry["name"].lower()
        if out.get(name):
            out[name].append(entry["ID"])
        else:
            out[name] = [entry["ID"]]
        out[name.replace("'","")] = out[name]
        out[name.replace("-"," ")] = out[name]
    return out


def load_text():
    text = {}
    text["pcnames"] = ["Isaac", "Garet", "Ivan", "Mia", "Felix", "Jenna", "Sheba", "Piers"]
    text["elements"] = ["Venus", "Mercury", "Mars", "Jupiter", "Neutral"]
    with open(r"text/GStext.txt") as f:
        lines = f.read().splitlines()
        text["item_descriptions"] = lines[146:607]
        text["items"] = lines[607:1068]
        text["items"] = [re.search(r"[^{}]*$", s).group() for s in text["items"]]
        text["enemynames"] = lines[1068:1447]
        text["moves"] = lines[1447:2181]
        text["move_descriptions"] = lines[2181:2915]
        text["classes"] = lines[2915:3159]
        text["djinn"] = lines[1747:1827]
    with open(r"text/customtext.txt") as f:
        lines = f.read().splitlines()
        text["ability_effects"] = lines[0:92]
        text["equipped_effects"] = lines[92:120]
        text["summons"] = lines[120:149]
    return text


DataTables, namemaps, UserData, Text = {}, {}, {}, {}
def load_data():
    global DataTables, namemaps, UserData, Text
    print("Loading database...", end="\r")
    DataTables.clear(); namemaps.clear(); Text.clear()
    for name in [
            "djinndata", "summondata", "enemydata", "itemdata", "abilitydata", "pcdata",
            "classdata", "elementdata", "enemygroupdata", "encounterdata"]:
        with open(rf"data/{name}.json") as f:
            DataTables[name] = json.load(f)
            if name == "enemydata":
                DataTables["enemydata-h"] = deepcopy(DataTables["enemydata"])
                for entry in DataTables["enemydata-h"]:
                    entry["HP"] = min(0x3FFF, int(1.5*entry["HP"]))
                    entry["ATK"] = int(1.25*entry["ATK"])
                    entry["DEF"] = int(1.25*entry["DEF"])
    for k,v in DataTables.items():
        namemaps[k] = namedict(v)
    Text.update(**load_text())
    print("Loaded database    ")


mquote = re.compile(r"\".*?\"|\'.*?\'")
mkwarg = re.compile(r"([a-zA-Z_][a-zA-Z_0-9]*)=([^ =]\S*)")
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


def dictstr(dictionary, js=False, maxwidth=78):
    if js: return json.dumps(dictionary, indent=4)
    out = ""
    maxlen = len(max(dictionary.keys(), key=lambda x: len(x)))
    for k,v in dictionary.items():
        out += f"\n{k+'  ':<{maxlen+2}}"
        if hasattr(v, "__iter__") and not isinstance(v, (str, bytes)):
            out += wrap(v, maxwidth, maxlen+2)
        else:
            out += str(v)
    return out[1:]


def tableH(dictlist, fields=None, widths=None):
    fields = fields or dictlist[0].keys()
    for f in fields:
        for d in dictlist:
            d[f] = d.get(f, None)
    if not widths:
        widths = {k: len(k) for k in fields}
        for d in dictlist:
            for k in fields:
                widths[k] = max(widths[k], len(str(d[k])))
    elif not isinstance(widths, dict):
        widths = dict(zip(fields, widths))
    out = " ".join((f"{k:^{w}.{w}}" for k,w in widths.items()))  # Heading
    out += "\n" + " ".join(("="*w for w in widths.values()))  # Border
    template = " ".join((f"{{{k}:<{w}.{w}}}" for k,w in widths.items()))
    for d in dictlist:
        out += "\n" + template.format(**{k:str(v) for k,v in d.items()})
    return out


def tableV(dictlist):
    columns = [[]] + [[] for d in dictlist]
    for i,d in enumerate(dictlist):
        for k,v in d.items():
            if hasattr(v, "__iter__") and not isinstance(v, (str, bytes)):
                count = len(max(dictlist, key=lambda x:len(x[k]))[k])
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
    widths = [len(max(c, key=lambda x: len(x))) for c in columns]
    template = "  ".join((f"{{:{w}.{w}}}" for w in widths))
    return "\n".join(template.format(*row) for row in zip(*columns))


@command
async def upload(message, *args, **kwargs):
    """Upload a file

    Uploads are stored per-user, and will remain in the bot's
    memory until the bot is reset, which can happen at any time.  Some 
    functions require that you have already called this function within
    the most recent bot session.

    Accepted File Types:
        .sav -- Battery files. Enables save-related commands

    Arguments:
        link -- (optional) a link to a message with an attached file
                if not included, you must attach a file to the message
    """
    ID = str(message.author.id)
    if not UserData.get(ID): UserData[ID] = {}
    if message.attachments:
        attachment = message.attachments[0]
    else:
        assert args and args[0].startswith("https://discord.com/channels/"), \
            "Expected an attachment or a link to a message with an attachment"
        ID_list = args[0].replace("https://discord.com/channels/","").split("/")
        serverID, channelID, messageID = (int(i) for i in ID_list)
        server = client.get_guild(serverID)
        channel = server.get_channel(channelID)
        m = await channel.fetch_message(messageID)
        attachment = m.attachments[0]
    data = await attachment.read()
    if attachment.url.endswith(".sav"):
        for i in range(16):
            addr = 0x1000*i
            if data[addr:addr+7] == b'CAMELOT' and data[addr+7] < 0xF: break
        else:
            assert 0, "No valid saves detected"
        UserData[ID]["save"] = data
        await usercommands["$save_preview"](message, concise=True)
    else:
        assert 0, "Unhandled file type"


def terminal(callback):
    import asyncio
    import io
    from types import SimpleNamespace as SN
    async def send(text):
        print(text.replace("```","\n").replace("`",""))
    def get_attachments(text):
        attachments = []
        def msub(m):
            filename = m.group(1).strip('"')
            with open(filename, "rb") as f:
                buffer = io.BytesIO(f.read())
                buffer.read = to_async(buffer.read)
                buffer.url = filename
            attachments.append(buffer)
        text = re.sub(r"\sattach=(\".*?\"|\S+)", msub, text)
        return text, attachments
    ID = 0
    async def loop():
        nonlocal ID
        while True:
            try: text = input("> ")
            except KeyboardInterrupt: return
            if text in ("quit", "exit"): return
            if text.startswith("setid"): ID=int(text[len("setid"):])
            text, attachments = get_attachments(text)
            message = SN(
                author=SN(name="admin", id=ID), content=text, attachments=attachments,
                guild=SN(name=None), channel=SN(name=None, send=send))
            await callback(message)
    asyncio.run(loop())