import re
import json
from copy import deepcopy


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


DataTables, namemaps, UserData = {}, {}, {}
def load_data():
    global DataTables, namemaps, UserData
    print("Loading database...", end="\r")
    DataTables.clear(); namemaps.clear()
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
    with open("userdata/userdata.json") as f:
        UserData = json.load(f)
    print("Loaded database    ")


mquote = re.compile(r"\".*?\"|\'.*?\'")
mkwarg = re.compile(r"([a-zA-Z_][a-zA-Z_0-9]*)=([^ =]\S*)")
mtoken = re.compile(r"{(\d+)}")
def argparse(s):
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


def dictstr(dict_, js=False, indent=0, maxwidth=77):
    if js: return json.dumps(dict_, indent=4)
    out = ""
    maxlen = len(max(dict_.keys(), key=lambda x: len(x)))
    for k,v in dict_.items():
        if isinstance(v, dict):
            out += " "*indent + (k + ": ").ljust(maxlen+2)
            if not v:
                out += "{}\n"
            else:
                out += "\n" + dictstr(v, indent=indent+4)
            continue
        out += " "*indent + (k + ": ").ljust(maxlen+2)
        if isinstance(v, list):
            listiter = iter(v)
            xpos = indent + maxlen + 3
            out += "["
            if v:
                entry = str(next(listiter))
                out += entry; xpos += len(entry)
            for entry in listiter:
                entry = str(entry)
                xpos += len(entry) + 2
                if xpos >= maxwidth:
                    xpos = indent+maxlen+3
                    out += ",\n" + " "*xpos + entry
                    xpos += len(entry)
                else:
                    out += ", " + entry
            out += "]\n"
        else:
            out += str(v) + "\n"
    return out


def tablestr(dictlist, fields=None, widths=None):
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
