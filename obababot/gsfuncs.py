import re
import io
import json
import inspect
from . import utilities
from .utilities import command, DataTables, UserData, Text, reply


def getclass(name, djinncounts, item=None):
    name = name.lower()
    pcelements = {
        "isaac":"Venus", "garet":"Mars", "ivan":"Jupiter", "mia":"Mercury",
        "felix":"Venus", "jenna":"Mars", "sheba":"Jupiter", "piers":"Mercury"}
    elements = ["Venus", "Mercury", "Mars", "Jupiter"]
    relations = {   # Affinity, Weakness, Neutral, Primary
        'Venus':    ['Mars', 'Jupiter', 'Mercury', 'Venus'],
        'Mercury':  ['Jupiter', 'Mars', 'Venus', 'Mercury'],
        'Mars':     ['Venus', 'Mercury', 'Jupiter', 'Mars'],
        'Jupiter':  ['Mercury', 'Venus', 'Mars', 'Jupiter'],
    }
    element = pcelements[name]
    elevels = [cnt+5 if e == element else cnt for e,cnt in zip(elements, djinncounts)]
    if item:
        item = item.lower()
        aliases = {
            "card": "mysterious card", "mc": "mysterious card",
            "whip": "trainer's whip", "tw": "trainer's whip",
            "tome": "tomegathericon", "tm": "tomegathericon",
        }
        item = aliases.get(item, item)
        assert item in ("mysterious card", "trainer's whip", "tomegathericon"), \
            f"\"{item}\" not recognized"
        table = item
    elif sum(elevels) == elevels[elements.index(element)]:  # if all djinn match pc element
        if name in ("jenna", "piers"):
            table = "primary2"
        else:
            table = "primary1"
    else:
        sort1 = {e:elevels[elements.index(e)] for e in relations[element]}  # sort by relation
        sort2 = sorted(sort1.items(), key=lambda x: x[1])  # sort by elevel
        dominance = [x[0] for x in reversed(sort2)] # highest priority to lowest
        if relations[element][0] in dominance[:2]:  # if affinity element is 1st or 2nd dominant
            if element in ("Venus", "Mars"):
                table = "earth/fire"
            elif element in ("Mercury", "Jupiter"):
                table = "wind/water"
        else:  # go to table of 2nd dominant
            table = ("earth", "water", "fire", "wind")[elements.index(dominance[1])]
    classtables = [
        "primary1", "water", "wind", "earth", "fire", "earth/fire", "wind/water",
        "primary2", "mysterious card", "trainer's whip", "tomegathericon"]
    offsets = [1,40,70,100,130,160,180,200,220,230,240,244]  # ID locations of class tables
    tableID = classtables.index(table)
    bestmatch = 0
    for i in range(offsets[tableID], offsets[tableID+1]):
        classdata = DataTables["classdata"][i]
        if classdata["name"] == "?": continue
        requirement = classdata["elevels"]
        if all(e1 >= e2 for e1, e2 in zip(elevels, requirement)):
            bestmatch = i
    return DataTables['classdata'][bestmatch]


def battle_damage(
        ability, ATK=None, POW=None, user=None, target=None,
        HP=None, DEF=None, RES=None, RANGE=None):
    epos = Text["elements"].index(ability["element"])
    if user:
        if ATK is None: ATK = user["ATK"]
        if POW is None and ability["element"] != "Neutral":
            POW = user["epow"][epos]
    if target:
        if HP is None: HP = target.get("HP", target.get("HP_max"))
        if DEF is None: DEF = target["DEF"]
        if RES is None and ability["element"] != "Neutral":
            RES = target["eres"][epos]
    int_256 = lambda x: int(256*x)/256
    damage_type = ability["damage_type"]
    if damage_type == "Healing":
        damage = ability["power"]*POW/100
    elif damage_type == "Added Damage":
        damage = (ATK-DEF)/2 + ability["power"]
        if ability["element"] != "Neutral":
            damage *= int_256(1 + (POW-RES)/400)
    elif damage_type == "Multiplier":
        damage = (ATK-DEF)/2*ability["power"]/10
        if ability["element"] != "Neutral":
            damage *= int_256(1 + (POW-RES)/400)
    elif damage_type == "Base Damage":
        damage = ability["power"]*int_256(1 + (POW-RES)/200)
        if RANGE: damage *= [1, .8, .6, .4, .2, .1][RANGE]
    elif damage_type == "Base Damage (Diminishing)":
        damage = ability["power"]*int_256(1 + (POW-RES)/200)
        if RANGE: damage *= [1, .5, .3, .1, .1, .1][RANGE]
    elif damage_type == "Summon":
        ability = DataTables.get("summondata", ability["name"])
        damage = ability["power"] + int(ability["hp_multiplier"]*min(10000, HP))
        damage *= int_256(1 + (POW-RES)/200)
        if RANGE: damage *= [1, .7, .4, .3, .2, .1][RANGE]
    return max(0, int(damage))


def roomname(gamenumber, mapnumber, doornumber):
    roomtable = DataTables[f"room_references{gamenumber}"]
    mapdata = DataTables[f"mapdata{gamenumber}"]
    for r in roomtable:
        door, check = r["door"], r["room_or_area"]
        flag, door = door & 0x8000, door & 0x7FFF
        area = mapdata[mapnumber]["area"]
        if (check==mapnumber if flag else check==area):
            if door in (0x7fff, doornumber): return r["name"]
    return roomtable[0]["name"]


def readsav(data):
    f = io.BytesIO(data)
    read = lambda size: int.from_bytes(f.read(size), "little")
    headers = []
    for i in range(16):
        f.seek(0x1000*i)
        headers.append({
            "addr": 0x1000*i,
            "header": f.read(7),
            "slot": read(1),
            "checksum": read(2),
            "priority": read(2),
        })
    valid_saves = [h for h in headers if h["header"] == b"CAMELOT" and h["slot"] < 0xF]
    slots = {}
    for save in valid_saves:
        if save["priority"] > slots.get(save["slot"], -1):
            slots[save["slot"]] = save
    build_dates = {
        0x1C85: "Golden Sun - The Lost Age (UE)",
        0x1D97: "Golden Sun - The Lost Age (G)",
        0x1DC7: "Golden Sun - The Lost Age (S)",
        0x1D98: "Golden Sun - The Lost Age (F)",
        0x1DC8: "Golden Sun - The Lost Age (I)",
        0x198A: "Golden Sun - The Lost Age (J)",
        0x1652: "Golden Sun (UE)",
        0x1849: "Golden Sun (G)",
        0x1885: "Golden Sun (S)",
        0x1713: "Golden Sun (F)",
        0x1886: "Golden Sun (I)",
        0x159C: "Golden Sun (J)"}
    filedata = []
    for i in range(3):
        if not slots.get(i): continue
        f.seek(slots[i]["addr"] + 0x10)
        data = f.read(0x2FF0)
        read = lambda addr, size: int.from_bytes(data[addr:addr+size], "little")
        string = lambda addr, size: data[addr:addr+size].replace(b"\x00",b"").decode()
        version = build_dates[read(0x26, 2) & ~0x8000]
        if "The Lost Age" in version: GAME = 2; offset = 0x20
        else: GAME = 1; offset = 0
        party_size = sum((1 if read(0x40, 1) & 2**j else 0 for j in range(8)))
        positions = [read(0x438+offset + j, 1) for j in range(party_size)]
        addresses = [0x500+offset + 0x14C*p for p in positions]
        filedata.append({
            "version": version,
            "slot": i,
            "leader": string(0, 12),
            "party_members": read(0x40, 1),
            "framecount": read(0x244, 4),
            "summons": read(0x24C, 4),
            "coins": read(0x250, 4),
            "map_number": read(0x400+offset, 2),
            "door_number": read(0x402+offset, 2),
            "party_positions": positions,
            "party": [{
                "name": string(base, 15),
                "level": read(base+0xF, 1),
                "element": [0,2,3,1,0,2,3,1][p],
                "base_stats": {
                    "HP": read(base+0x10, 2),
                    "PP": read(base+0x12, 2),
                    "ATK": read(base+0x18, 2),
                    "DEF": read(base+0x1A, 2),
                    "AGI": read(base+0x1C, 2),
                    "LCK": read(base+0x1E, 1),
                    "epow": [read(base+0x24+4*j, 2) for j in range(4)],
                    "eres": [read(base+0x26+4*j, 2) for j in range(4)],
                },
                "stats": {
                    "HP_max": read(base+0x34, 2),
                    "PP_max": read(base+0x36, 2),
                    "HP_cur": read(base+0x38, 2),
                    "PP_cur": read(base+0x3A, 2),
                    "ATK": read(base+0x3c, 2),
                    "DEF": read(base+0x3e, 2),
                    "AGI": read(base+0x40, 2),
                    "LCK": read(base+0x42, 1),
                    "epow": [read(base+0x48+4*j, 2) for j in range(4)],
                    "eres": [read(base+0x4A+4*j, 2) for j in range(4)],
                },
                "abilities": [read(base+0x58+4*j, 4) for j in range(32)],
                "inventory": [read(base+0xD8+2*j, 2) for j in range(15)],
                "djinn": [read(base+0xF8+4*j, 4) for j in range(4)],
                "set_djinn": [read(base+0x108+4*j, 4) for j in range(4)],
                "djinncounts": [read(base+0x118+j, 1) for j in range(4)],
                "set_djinncounts": [read(base+0x11C+j, 1) for j in range(4)],
                "exp": read(base+0x124, 4),
                "class": read(base+0x129, 1),
                "status": [read(base+j, 1) for j in (0x130, 0x131, 0x140)],
            } for p,base in zip(positions, addresses)],
        })
    for f in filedata:
        f["party_members"] = [Text["pcnames"][i] for i in range(8) if f["party_members"] & 2**i]
        f["summons"] = [DataTables["summondata"][i]["name"] for i in range(33) if f["summons"] & 2**i]
        f["area"] = roomname(GAME, f["map_number"], f["door_number"])
        djinncounts = [0, 0, 0, 0]
        for pc in f["party"]:
            pc["element"] = Text["elements"][pc["element"]]
            pc["abilities"] = [Text["abilities"][i & 0x3FF] for i in pc["abilities"] if i & 0x3FF]
            pc["inventory"] = {Text["items"][i & 0x1FF]: i for i in pc["inventory"] if i & 0x1FF}
            for k, v in pc["inventory"].items():
                metadata = [(v>>11 & 0x1F) + 1]
                if v & 1<<9: metadata.append("equipped")
                if v & 1<<10: metadata.append("broken")
                pc["inventory"][k] = metadata
            for i, count in enumerate(pc["djinncounts"]):
                djinncounts[i] += count
            pc["class"] = Text["classes"][pc["class"]]
            pc["djinn"] = sum((d<<20*i for i,d in enumerate(pc["djinn"])))
            pc["set_djinn"] = sum((d<<20*i for i,d in enumerate(pc["set_djinn"])))
            pc["djinn"] = [Text["djinn"][i] for i in range(80) if pc["djinn"] & 2**i]
            pc["set_djinn"] = [Text["djinn"][i] for i in range(80) if pc["set_djinn"] & 2**i]
            pc["elevels"] = pc["set_djinncounts"].copy()
            pc["elevels"][Text["elements"].index(pc["element"])] += 5
            pc["status"].insert(2, int(pc["status"][1]==2))
            pc["status"][1] = int(pc["status"][1]==1)
            pc["status"] = [n for s,n in zip(pc["status"], ("Curse","Poison","Venom","Haunt")) if s]
        seconds, minutes, hours = (f["framecount"]//60**i for i in range(1,4))
        seconds %= 60; minutes %= 60
        f["playtime"] = "{:02}:{:02}:{:02}".format(hours, minutes, seconds),
        f["djinncounts"] = djinncounts
    return filedata


def preview(filedata):
    pages = {}
    slots = []
    used_slots = [f["slot"] for f in filedata]
    preview = utilities.Charmap()
    preview.addtext(filedata[0]["version"], (0,0))
    leaders, areas = [], []
    maxname = max((len(f["leader"]) for f in filedata))
    maxarea = max((len(f["area"]) for f in filedata))
    for i in range(3):
        if i not in used_slots:
            preview.addtext(f"{i}  {'':-<{maxname}}  {'':-<{maxarea}}", (0, 2+i))
        else:
            f = next(filter(lambda x: x["slot"]==i, filedata))
            preview.addtext(f"{i}  {f['leader']:<{maxname}}  {f['area']:<{maxarea}}", (0, 2+i))
    for f in filedata:
        slot = {}
        slot["slot"] = f["slot"]
        slot["time"] = f["playtime"]
        slot["coins"] = f["coins"]
        slot["djinn"] = [f["djinncounts"]]
        slot[""] = ""
        maxlen = max(len(str(f["djinncounts"])), *(len(pc["name"])+4 for pc in f["party"]))
        slot["PCs"] = [f"{pc['name']:<{maxlen-4}}{pc['level']:>4}" for pc in f["party"]]
        slots.append(slot)
    preview.addtext(utilities.tableV(slots), (0,6))
    pages["preview"] = f"```\n{preview}\n```"
    pages["help"] = inspect.cleandoc("""```
        Click emotes to view other pages of this message

        P     - Go to preview page
        0,1,2 - Select a save slot
        <,>   - Scroll through characters of current save slot
        ?     - Show this help page
        ```""")
    for f in filedata:
        slot = f["slot"]
        pages[slot] = []
        for pc in f["party"]:
            out = utilities.Charmap()
            x,y = out.addtext(f"{pc['name']}\n{pc['class']}", (0, 0))
            x,y = out.addtext(f"Lvl {pc['level']}\nExp {pc['exp']}", (x+3,0))
            x += 2
            for i in range(0, len(pc["status"]), 2):
                x,y = out.addtext("\n".join(pc["status"][i:i+2]), (x+1, 0))
            base = pc["base_stats"]
            stats = pc["stats"]
            out.addtext("Stats", (0, 3))
            x,y = out.addtext(utilities.dictstr({
                "HP": f"{stats['HP_cur']}/{stats['HP_max']}",
                "PP": f"{stats['PP_cur']}/{stats['PP_max']}",
                "ATK": stats["ATK"]}, sep=" "), (0, 4))
            x,y = out.addtext(utilities.dictstr({
                "DEF": stats["DEF"],
                "AGI": stats["AGI"],
                "LCK": stats["LCK"]}, sep=" "), (x+2, 4))
            out.addtext("Base Stats", (x+3, 3))
            x,y = out.addtext(utilities.dictstr({
                "HP": base['HP'],
                "PP": base['PP'],
                "ATK": base["ATK"]}, sep=" "), (x+3, 4))
            x,y = out.addtext(utilities.dictstr({
                "DEF": base["DEF"],
                "AGI": base["AGI"],
                "LCK": base["LCK"]}, sep=" "), (x+2, 4))
            elementdata = []
            for i, name in enumerate(["ven", "merc", "mars", "jup"]):
                elementdata.append(
                    {"Estats": name.title(),
                    "Djinn": f"{pc['set_djinncounts'][i]}/{pc['djinncounts'][i]}",
                    "Level": pc["elevels"][i],
                    "Power": pc["stats"]["epow"][i],
                    "Resist": pc["stats"]["eres"][i]})
            out.addtext(utilities.tableV(elementdata), (x+3,2))
            out.addtext("Items", (0, 8))
            inventory = []
            for k,v in pc["inventory"].items():
                state = "B" if "broken" in v[1:] else "E" if "equipped" in v[1:] else "-"
                inventory.append({"item": k+" ", "amt": v[0], "state": state})
            x = -1
            ymax = 0
            for i in range(0, len(inventory), 5):
                x,y = out.addtext(utilities.tableH(inventory[i:i+5], headers=False), (x+3, 9))
                ymax = max(ymax, y)
            out.addtext("Djinn", (0, ymax+1))
            djinn = []
            for d in pc["djinn"]:
                djinn.append({"name": d, "state": "√" if d in pc["set_djinn"] else "-"})
            x,_ = out.addtext(utilities.tableH(djinn, headers=False), (2,ymax+2))
            x = max(x, 4)
            out.addtext("Abilities", (x+3, ymax+1))
            x += 2
            if pc["abilities"]:
                height = max(len(pc["abilities"])/4, len(pc["djinn"]))
                height = int(height) + 1 if height != int(height) else int(height)
                for i in range(0, len(pc["abilities"]), height):
                    x,_ = out.addtext("\n".join(pc["abilities"][i:i+height]), (x+3, ymax+2))
            pages[slot].append(f"```\n{out}\n```")
    return pages


def rn(init):
    def inner():
        nonlocal init
        init = (0x41C64E6D*init + 0x3039) % 2**32
        return (init >> 8) & 0xFFFF
    return inner

def enemyparty(enemygroup, grn=0):
    grn = rn(grn)
    enemies, mins, maxs = (enemygroup[attr] for attr in ["enemies", "min_amounts", "max_amounts"])
    quantities = [mn + ((mx-mn+1)*grn() >> 16) if mx > mn else mn for mn,mx in zip(mins, maxs)]
    def swap(array, pos1, pos2):
        temp = array[pos2]
        array[pos2] = array[pos1]
        array[pos1] = temp
    order = [0,1,2,3,4]
    for i in range(10):
        swap(order, 5*grn() >> 16, 5*grn() >> 16)
    order = [v for v in order if v < len(enemies)]
    party = []
    for pos in order:
        party.extend([enemies[pos]]*quantities[pos])
    party = [DataTables.get("enemydata", n).copy() for n in party]
    for e in party:
        e["HP_cur"] = e["HP"]
        e["PP_cur"] = e["PP"]
    return party


# @command
async def loadparty(message, *args, **kwargs):
    attachment = await utilities.get_attachment(message, *args[1:])
    data = await attachment.read()
    url = attachment.url
    assert url.endswith(".sav") or url.endswith(".SaveRAM"), "Invalid file extension"
    filedata = readsav(data)
    slot = int(args[0]) if args else 0
    for f in filedata:
        if f["slot"] == slot: break
    else: assert 0, "Slot not found"
    UserData[message.author.id].party = f["party"]
    await reply(message, f"Loaded party from slot {slot}")


# @command
async def battle(message, *args, **kwargs):
    user = UserData[message.author.id]
    assert user.party, "Please load a party using the $loadparty command"
    
    party = user.party.copy()
    for p in party: p.update(**p.pop("stats"))
    enemies = enemyparty(DataTables["enemygroupdata"][int(args[0])], 0)
    cursor = 0
    side = 0
    inputs = []
    brn = rn(int(kwargs.get("brn", 0)))
    grn = rn(int(kwargs.get("grn", 0)))

    async def main(before, after):
        for line in after.content.split("\n"):
            if not line.startswith(utilities.prefix): continue
            content = line[len(utilities.prefix):]
            args, kwargs = utilities.parse(content)
            move_select(*args, **kwargs)
            await before.edit(content=display())

    def display():
        out = utilities.Charmap()
        x,y = out.addtext(
            "\n".join((f"{p['name']} {p['HP_cur']}" for p in party[:4])), (2,0))
        if side == 0: out.addtext("►", (0, cursor))
        elif side == 1: out.addtext("►", (x+3, cursor))
        out.addtext(
            "\n".join((f"{e['name']} {e['HP_cur']}" for e in enemies[:4])), (x+5,0))
        return f"```\n{out}\n```"

    def move_select(*args, **kwargs):
        nonlocal cursor
        ability = DataTables.get("abilitydata", args[0])
        pc = party[cursor]
        inputs.append({
            "ability": ability,
            "user": pc,
            "AGI": (pc["AGI"]*grn() >> 20) + pc["AGI"],
            "center": int(args[1]),
        })
        if cursor == 3:
            einputs = []
            for enemy in enemies:
                ability = DataTables.get("abilitydata", enemy["abilities"][brn() & 7])
                einputs.append({
                    "ability": ability,
                    "user": enemy,
                    "AGI": enemy["AGI"],
                    "center": grn() & 3,
                })
            battle_turn(party, enemies, inputs, einputs)
        cursor = (cursor + 1) % 4

    def battle_turn(party1, party2, moves1, moves2):
        moves = [(m, 0) for m in moves1] + [(m, 1) for m in moves2]
        for move, p in sorted(moves, key=lambda x: -x[0]["AGI"]):
            ability = move["ability"]
            lower, upper = move["center"]-ability["range"]+1, move["center"]+ability["range"]
            for i in range(lower, upper):
                if ability["target"] == "Enemies": party = (party1, party2)[not p]
                else: party = (party1, party2)[p]
                if i >= len(party) or i < 0: continue
                if ability["damage_type"] not in ("Added Damage", "Multiplier", "Base Damage", "Summon"):
                    break
                RANGE = abs(i-move["center"])
                dealt = battle_damage(
                    ability,
                    user=move.get("user"),
                    target=party[i],
                    RANGE=RANGE)
                party[i]["HP_cur"] -= dealt
                print(f"{party[i]['name']} took {dealt} damage!")
        moves1.clear(); moves2.clear()

    sent = await reply(message, display())
    await utilities.live_message(sent, main)