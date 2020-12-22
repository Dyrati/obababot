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
        with open(f"data\\{name}.json") as f:
            DataTables[name] = json.load(f)
            if name == "enemydata":
                DataTables["enemydata-h"] = deepcopy(DataTables["enemydata"])
                for entry in DataTables["enemydata-h"]:
                    entry["HP"] = min(0x3FFF, int(1.5*entry["HP"]))
                    entry["ATK"] = int(1.25*entry["ATK"])
                    entry["DEF"] = int(1.25*entry["DEF"])
    for k,v in DataTables.items():
        namemaps[k] = namedict(v)
    with open("userdata\\userdata.json") as f:
        UserData = json.load(f)
    print("Loaded database    ")


def argparse(string):
    args = []
    kwargs = {}
    mquote = re.compile(r"(.*?)(\".*?\"|$)")
    mkwarg = re.compile(r"([a-zA-Z]\w*)=([^ =]\S*)")
    for m1, m2 in mquote.findall(string)[:-1]:
        for k,v in mkwarg.findall(m1):
            kwargs[k] = v
        m1 = mkwarg.sub("", m1)
        for arg in re.findall(r"\S+", m1):
            args.append(arg)
        if re.search(r"[a-zA-Z]\w*=$", m1) and m2:
            kwargs[args.pop()[:-1]] = m2
        elif m2:
            args.append(m2)
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
