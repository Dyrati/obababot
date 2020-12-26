import re
import io
import json
import utilities
from utilities import command, DataTables, UserData, namemaps, Text, reply


def readsav(data):
    f = io.BytesIO(data)
    def read(size):
        return int.from_bytes(f.read(size), "little")
    headers = []
    for i in range(0, 16, 3):
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

    filedata = []
    for i in range(3):
        if not slots.get(i): continue
        f.seek(slots[i]["addr"] + 0x10)
        data = f.read(0x2FF0)
        def read(addr, size):
            return int.from_bytes(data[addr:addr+size], "little")
        filedata.append({
            "slot": i,
            "party_members": read(0x40, 1),
            "framecount": read(0x244, 4),
            "summons": read(0x24C, 4),
            "coins": read(0x250, 4),
            "party_positions": [read(0x458+j, 1) for j in range(8)],
            "party": [{
                "name": [read(base+i, 1) for i in range(15)],
                "level": read(base+0xF, 1),
                "base_stats": {
                    "HP": read(base+0x10, 2),
                    "PP": read(base+0x12, 2),
                    "ATK": read(base+0x18, 2),
                    "DEF": read(base+0x1A, 2),
                    "AGI": read(base+0x1C, 2),
                    "LCK": read(base+0x1E, 1),
                    "venus_pow": read(base+0x24, 2),
                    "venus_res": read(base+0x26, 2),
                    "merc_pow": read(base+0x28, 2),
                    "merc_res": read(base+0x2A, 2),
                    "mars_pow": read(base+0x2C, 2),
                    "mars_res": read(base+0x2E, 2),
                    "jup_pow": read(base+0x30, 2),
                    "jup_res": read(base+0x32, 2),
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
                    "venus_pow": read(base+0x48, 2),
                    "venus_res": read(base+0x4a, 2),
                    "merc_pow": read(base+0x4c, 2),
                    "merc_res": read(base+0x4e, 2),
                    "mars_pow": read(base+0x50, 2),
                    "mars_res": read(base+0x52, 2),
                    "jup_pow": read(base+0x54, 2),
                    "jup_res": read(base+0x56, 2),
                },
                "inventory": [read(base+0xD8+j, 2) for j in range(0,30,2)],
                "djinn": [read(base+0xF8+j, 4) for j in range(0,16,4)],
            } for base in range(0x520, 0xF80, 0x14C)],
        })

    partysummons = 0
    partydjinn = 0
    display = []
    for f in filedata:
        f["party_members"] = [Text["pcnames"][i] for i in range(8) if f["party_members"] & 2**i]
        f["summons"] = [Text["summons"][i] for i in range(33) if f["summons"] & 2**i]
        djinncounts = [0, 0, 0, 0]
        for pc in f["party"]:
            pc["name"] = "".join([chr(c) for c in pc["name"] if c])
            pc["inventory"] = {Text["items"][i & 0x1FF]: i for i in pc["inventory"] if i & 0x1FF}
            for k, v in pc["inventory"].items():
                metadata = [(v>>11 & 0x1F) + 1]
                if v & 1<<9: metadata.append("equipped")
                if v & 1<<10: metadata.append("broken")
                pc["inventory"][k] = metadata
            for i, count in enumerate((sum((e>>i & 1 for i in range(20))) for e in pc["djinn"])):
                djinncounts[i] += count
            pc["djinn"] = sum((d<<20*i for i,d in enumerate(pc["djinn"])))
            pc["djinn"] = [Text["djinn"][i] for i in range(80) if pc["djinn"] & 2**i]

        display.append({
            "slot": f["slot"],
            "playtime": "{:02}:{:02}:{:02}".format(*(f["framecount"]//60**i % 60 for i in range(3,0,-1))),
            "coins": f["coins"],
            "djinn": djinncounts,
        })

    return filedata, display

@command
async def upload_save(message, *args, **kwargs):
    """Upload a battery file

    Battery files (.sav) are stored per-user, and will remain in the bot's
        memory until the bot is reset, which can happen at any time.  Some 
        functions require that you have already called this function within
        the most recent bot session.
    
    Arguments:
        link -- (optional) a link to a message with an attached .sav file
                if not included, you must attach a .sav file to the message
    """
    ID = str(message.author.id)
    if not UserData.get(ID): UserData[ID] = {}
    if message.attachments:
        data = await message.attachments[0].read()
    else:
        assert args and args[0].startswith("https://discord.com/channels/"), \
            "Expected an attachment or a link to a message with an attachment"
        ID_list = args[0].replace("https://discord.com/channels/","").split("/")
        serverID, channelID, messageID = (int(i) for i in ID_list)
        server = utilities.client.get_guild(serverID)
        channel = server.get_channel(channelID)
        m = await channel.fetch_message(messageID)
        data = await m.attachments[0].read()
    assert len(data) == 0x10000, "Expected a 64KB file"
    UserData[ID]["save"] = data
    await reply(message, "Upload successful.  Use $save_preview to view")

@command
async def save_preview(message, *args, **kwargs):
    """See a preview of your last uploaded save file"""
    ID = str(message.author.id)
    if not UserData.get(ID): UserData[ID] = {}
    data = UserData[ID].get("save")
    assert data, "Save file not found. Use $upload_save to store a save file"
    filedata, display = readsav(data)
    for f, d in zip(filedata, display):
        out = utilities.dictstr(d) + "\n"
        pcdict = f["party"]
        for pc in pcdict:
            pc.pop("inventory")
            pc.pop("base_stats")
            pc["stats"] = {k:v for k,v in pc["stats"].items() if not("res" in k or "pow" in k)}
            pc.update(**pc.pop("stats"))
            pc["djinn"] = pc.pop("djinn")
        out += "\n" + utilities.tableV(pcdict)
        await reply(message, f"```{out}```")

@command
async def getclass(message, *args, **kwargs):
    """Get the class of a character based on their djinn

    Arguments:
        name     -- Isaac, Garet, Ivan, Mia, Felix, Jenna, Sheba, Piers
        venus    -- djinn count
        mercury  -- djinn count
        mars     -- djinn count
        jupiter  -- djinn count
    
    Keyword Arguments:
        item -- name of class changing item
                may be "mysterious card", "trainer's whip", or "tomegathericon"
                or just "card/mc", "whip/tw", or "tome/tm" for short
    """
    name, elevels = args[0].lower(), [int(i) for i in args[1:5]]
    assert len(elevels) == 4, "Expected 4 elevel arguments: Venus, Mercury, Mars, Jupiter"
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
    elevels = [lvl+5 if e == element else lvl for e,lvl in zip(elements, elevels)]
    if kwargs.get("item"):
        item = kwargs["item"].lower()
        aliases = {
            "card": "mysterious card", "mc": "mysterious card",
            "whip": "trainer's whip", "tw": "trainer's whip",
            "tome": "tomegathericon", "tm": "tomegathericon",
        }
        item = aliases.get(item, item)
        if item in ("mysterious card", "trainer's whip", "tomegathericon"):
            table = item
        else:
            await reply(message, f"\"{item}\" not recognized")
            return
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
        requirement = (classdata[e] for e in elements)
        if all(e1 >= e2 for e1, e2 in zip(elevels, requirement)):
            bestmatch = i
    await reply(message, f"```{DataTables['classdata'][bestmatch]['name']}```")

@command
async def damage(message, *args, **kwargs):
    """Damage Calculator

    Arguments:
        ability -- the name of the attack
    
    Keyword Arguments:
        atk -- attack stat of attacker
        pow -- elemental power of the attacker (for the attack's element)
        target -- name of enemy.  auto-fills in kwargs for hp, def, and res
        hp  -- hp of target
        def -- defense stat of target
        res -- resistance of target (for the attack's element)
    """

    elements = ["Venus", "Mercury", "Mars", "Jupiter"]
    args = [arg.strip('"').lower() for arg in args]
    kwargs = {k:v.strip('"').lower() for k,v in kwargs.items()}
    abilityID = namemaps["abilitydata"][args[0]][0]
    ability = DataTables["abilitydata"][abilityID]
    for kw in ("atk","def","hp","pow","res","range"):
        if kwargs.get(kw) is not None: kwargs[kw] = int(kwargs[kw])
    ATK, DEF, HP, POW, RES, RANGE = [kwargs.get(kw) for kw in ("atk","def","hp","pow","res","range")]
    target = kwargs.get("target")
    if target:
        enemyID = namemaps["enemydata"][target][0]
        enemy = DataTables["enemydata"][enemyID]
        if HP is None: HP = enemy["HP"]
        if DEF is None: DEF = enemy["DEF"]
        estats = DataTables["elementdata"][enemy["elemental_stats_id"]]
        if RES is None: RES = estats.get(ability["element"] + "_Res")
    if ability["damage_type"] == "Healing":
        damage = ability["power"]*POW//100
    elif ability["damage_type"] == "Added Damage":
        damage = (ATK-DEF)/2 + ability["power"]
        if ability["element"] != "Neutral":
            damage *= 1 + (POW-RES)/400
    elif ability["damage_type"] == "Multiplier":
        damage = (ATK-DEF)/2*ability["power"]/10
        if ability["element"] != "Neutral":
            damage *= 1 + (POW-RES)/400
    elif ability["damage_type"] == "Base Damage":
        damage = ability["power"]*(1 + (POW-RES)/200)
        if RANGE: damage *= [1, .8, .6, .4, .2, .1][RANGE]
    elif ability["damage_type"] == "Base Damage (Diminishing)":
        damage = ability["power"]*(1 + (POW-RES)/200)
        if RANGE: damage *= [1, .5, .3, .1, .1, .1][RANGE]
    elif ability["damage_type"] == "Summon":
        summonID = namemaps["summondata"][args[0]][0]
        summon = DataTables["summondata"][summonID]
        damage = summon["power"] + summon["hp_multiplier"]*min(10000, HP)
        damage *= (1 + (POW-RES)/200)
        if RANGE: damage *= [1, .7, .4, .3, .2, .1][RANGE]
    if int(damage) == damage: damage = int(damage)
    await reply(message, f"```{damage}```")