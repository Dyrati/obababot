import re
import io
import json
import inspect
from copy import deepcopy
from random import randint
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
        ability, user=None, target=None, ATK=None, POW=None,
        HP=None, DEF=None, RES=None, RANGE=None, MULT=None):
    epos = Text["elements"].index(ability["element"])
    if user:
        if ATK is None: ATK = user.stats["ATK"]
        if POW is None: POW = user.stats["epow"][epos] if epos < 4 else 0
    if target:
        if HP is None: HP = target.stats["HP_max"]
        if DEF is None: DEF = target.stats["DEF"]
        if RES is None: RES = target.stats["eres"][epos] if epos < 4 else 0
    int_256 = lambda x: int(256*x)/256
    damage_type = ability["damage_type"]
    if damage_type == "Healing":
        damage = ability["power"]
        if ability["element"] != "Neutral":
            damage *= POW/100
    elif damage_type == "Added Damage":
        damage = (ATK-DEF)/2 + ability["power"]
        if ability["element"] != "Neutral":
            damage *= int_256(1 + (POW-RES)/400)
    elif damage_type == "Multiplier":
        if MULT is None: MULT = ability["power"]/10
        damage = (ATK-DEF)/2*MULT
        if ability["element"] != "Neutral":
            damage *= int_256(1 + (POW-RES)/400)
    elif damage_type == "Base Damage":
        damage = ability["power"]*int_256(1 + (POW-RES)/200)
        if RANGE: damage *= [1, .8, .6, .4, .2, .1][RANGE]
    elif damage_type == "Base Damage (Diminishing)":
        damage = ability["power"]*int_256(1 + (POW-RES)/200)
        if RANGE: damage *= [1, .5, .3, .1, .1, .1][RANGE]
    elif damage_type == "Summon":
        damage = ability["power"] + int(ability["hp_multiplier"]*min(10000, HP))
        damage *= int_256(1 + (POW-RES)/200)
        if RANGE: damage *= [1, .7, .4, .3, .2, .1][RANGE]
    else: damage = 0
    return max(0, int(damage))


base_chances = [
    60,60,100,100,70,70,100,100,75,75,55,55,65,35,30,40,45,55,
    25,20,60,100,100,65,60,100,35,50,100,100,100,100,100,100,100,
    100,100,100,100,100,100,100,100,100,100,100,100,100,60,90]

def statuschance(ability, user, target, RANGE=0):
    effect_index = Text.get("ability_effects", ability["effect"])
    if effect_index >= len(base_chances):
        base_chance = 100
    else:
        base_chance = base_chances[effect_index-8]
    if base_chance == 100: return 100
    epos = Text.get("elements", ability["element"])
    if epos < 4:
        elvldiff = user.elevels[epos] - target.elevels[epos]
    else: elvldiff = 0
    vulnerable = 25 if ability["effect"] in target.weaknesses else 0
    chance = base_chance + 3*(elvldiff - target.stats["LCK"]//2) + vulnerable
    return int([1, .6, .3, .3, .3, .3][RANGE]*chance)


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


def get_equipped_effects():
    def effect0(user, value): pass
    def effect1(user, value): user.stats["HP_max"] += value
    def effect2(user, value): user.stats["HP_regen"] += value
    def effect3(user, value): user.stats["PP_max"] += value
    def effect4(user, value): user.stats["PP_regen"] += value
    def effect5(user, value): user.stats["AGI"] += value
    def effect6(user, value): user.stats["LCK"] += value
    def effect7(user, value): user.stats["HP_max"] = int(user.stats["HP_max"]*value/10)
    def effect8(user, value): user.stats["HP_regen"] = int(user.stats["HP_regen"]*value/10)
    def effect9(user, value): user.stats["PP_max"] = int(user.stats["PP_max"]*value/10)
    def effect10(user, value): user.stats["PP_regen"] = int(user.stats["PP_regen"]*value/10)
    def effect11(user, value): user.stats["ATK"] = int(user.stats["ATK"]*value/10)
    def effect12(user, value): user.stats["DEF"] = int(user.stats["DEF"]*value/10)
    def effect13(user, value): user.stats["AGI"] = int(user.stats["AGI"]*value/10)
    def effect14(user, value): user.stats["LCK"] = int(user.stats["LCK"]*value/10)
    def effect15(user, value): user.stats["epow"][0] += value
    def effect16(user, value): user.stats["epow"][1] += value
    def effect17(user, value): user.stats["epow"][2] += value
    def effect18(user, value): user.stats["epow"][3] += value
    def effect19(user, value): user.stats["eres"][0] += value
    def effect20(user, value): user.stats["eres"][1] += value
    def effect21(user, value): user.stats["eres"][2] += value
    def effect22(user, value): user.stats["eres"][3] += value
    def effect23(user, value): user.status["critical_rate"] += value
    def effect24(user, value): user.status["counterstrike"] += value
    def effect25(user, value): pass # user.status["negate_curse"] = value
    def effect26(user, value): pass # user.status["turns"] = value
    def effect27(user, value): pass # user.status["encounters"] = value
    funcs = locals()
    return [funcs[f"effect{i}"] for i in range(28)]


def get_ability_effects():
    def effect0(**kwargs): pass
    def effect1(**kwargs): pass
    def effect2(**kwargs): pass
    def effect3(**kwargs):
        for status in ("poison", "venom"):
            kwargs["target"].status[status] = 0
    def effect4(**kwargs):
        for status in ("stun", "sleep", "delusion", "curse"):
            kwargs["target"].status[status] = 0
    def effect5(**kwargs): kwargs["target"].stats["HP_cur"] = kwargs["target"].stats["HP_max"]
    def effect6(**kwargs): kwargs["target"].status["attack_buff"][:] = [7,2]
    def effect7(**kwargs): kwargs["target"].status["attack_buff"][:] = [7,1]
    def effect8(**kwargs): kwargs["target"].status["attack_buff"][:] = [7,-2]
    def effect9(**kwargs): kwargs["target"].status["attack_buff"][:] = [7,-1]
    def effect10(**kwargs): kwargs["target"].status["defense_buff"][:] = [7,2]
    def effect11(**kwargs): kwargs["target"].status["defense_buff"][:] = [7,1]
    def effect12(**kwargs): kwargs["target"].status["defense_buff"][:] = [7,-2]
    def effect13(**kwargs): kwargs["target"].status["defense_buff"][:] = [7,-1]
    def effect14(**kwargs): kwargs["target"].status["resist_buff"][:] = [7,2]
    def effect15(**kwargs): kwargs["target"].status["resist_buff"][:] = [7,1]
    def effect16(**kwargs): kwargs["target"].status["resist_buff"][:] = [7,-2]
    def effect17(**kwargs): kwargs["target"].status["resist_buff"][:] = [7,-1]
    def effect18(**kwargs): kwargs["target"].status["poison"] = 1
    def effect19(**kwargs): kwargs["target"].status["venom"] = 1
    def effect20(**kwargs): kwargs["target"].status["delusion"] = 7
    def effect21(**kwargs): kwargs["target"].status["confusion"] = 7
    def effect22(**kwargs): kwargs["target"].status["charm"] = 7
    def effect23(**kwargs): kwargs["target"].status["stun"] = 7
    def effect24(**kwargs): kwargs["target"].status["sleep"] = 7
    def effect25(**kwargs): kwargs["target"].status["seal"] = 7
    def effect26(**kwargs): kwargs["target"].status["haunt"] = 7
    def effect27(**kwargs): kwargs["target"].stats["HP_cur"] = 0
    def effect28(**kwargs): kwargs["target"].status["death_curse"] = 7
    def effect29(**kwargs): pass
    def effect30(**kwargs): pass
    def effect31(**kwargs):
        kwargs["user"].stats["HP_cur"] += kwargs["ability"]["power"]
        kwargs["target"].stats["HP_cur"] -= kwargs["ability"]["power"]
    def effect32(**kwargs):
        kwargs["user"].stats["PP_cur"] += kwargs["ability"]["power"]
        kwargs["target"].stats["PP_cur"] -= kwargs["ability"]["power"]
    def effect33(**kwargs):
        for effect in ("summon_boosts", "attack_buff", "defense_buff", "resist_buff", "agility_buff"):
            if kwargs["target"].status[effect][1] > 0:
                kwargs["target"].status[effect][:] = [0, 0]
    def effect34(**kwargs): kwargs["target"].stats["HP_cur"] = 1
    def effect35(**kwargs): return {"DEF": kwargs["target"].stats["DEF"]//2}
    def effect36(**kwargs): pass
    def effect37(**kwargs): pass
    def effect38(**kwargs): pass
    def effect39(**kwargs): pass
    def effect40(**kwargs): pass
    def effect41(**kwargs): pass
    def effect42(**kwargs): return {"MULT": 2}
    def effect43(**kwargs): pass
    def effect44(**kwargs): return {"MULT": 3}
    def effect45(**kwargs): pass
    def effect46(**kwargs): kwargs["target"].damage_mult *= 0.5
    def effect47(**kwargs): kwargs["target"].damage_mult *= 0.1
    def effect48(**kwargs): pass
    def effect49(**kwargs): pass
    def effect50(**kwargs): pass
    def effect51(**kwargs): pass
    def effect52(**kwargs): pass
    def effect53(**kwargs): kwargs["target"].status["immobilize"] = 1
    def effect54(**kwargs): pass
    def effect55(**kwargs): kwargs["user"].stats["HP_cur"] = 0
    def effect56(**kwargs): kwargs["target"].stats["HP_cur"] = 0.5*kwargs["target"].stats["HP_max"]
    def effect57(**kwargs): kwargs["target"].stats["HP_cur"] = 0.8*kwargs["target"].stats["HP_max"]
    def effect58(**kwargs): kwargs["target"].status["agility_buff"][:] = [5,-4]
    def effect59(**kwargs): kwargs["target"].status["agility_buff"][:] = [5,8]
    def effect60(**kwargs): return {"HP_SAP": 0.5}
    def effect61(**kwargs): kwargs["target"].stats["HP_cur"] += 0.6*kwargs["target"].stats["HP_max"]
    def effect62(**kwargs): kwargs["target"].stats["HP_cur"] += 0.3*kwargs["target"].stats["HP_max"]
    def effect63(**kwargs): kwargs["target"].stats["PP_cur"] += 0.7*kwargs["target"].stats["PP_max"]
    def effect64(**kwargs):
        for effect in ("summon_boosts", "attack_buff", "defense_buff", "resist_buff", "agility_buff"):
            if kwargs["target"].status[effect][1] < 0:
                kwargs["target"].status[effect][:] = [0, 0]
        statuses = [
            "poison","venom","delusion","confusion","charm","stun","sleep",
            "psy_seal","haunt","death_curse","immobilize"]
        for effect in statuses:
            kwargs["target"].status[effect] = 0
    def effect65(**kwargs): return {"MULT": 2}
    def effect66(**kwargs): kwargs["target"].status["kite"] = 1
    def effect67(**kwargs): kwargs["target"].status["seal"] = 7
    def effect68(**kwargs): return {"MULT": 3}
    def effect69(**kwargs): return {"PP_SAP": 0.1}
    def effect70(**kwargs): kwargs["target"].stats["HP_cur"] += 0.5*kwargs["target"].stats["HP_max"]
    def effect71(**kwargs): kwargs["target"].stats["HP_cur"] += 0.7*kwargs["target"].stats["HP_max"]
    def effect72(**kwargs): kwargs["target"].damage_mult *= 0.4
    def effect73(**kwargs): kwargs["target"].stats["HP_cur"] = 0.6*kwargs["target"].stats["HP_max"]
    def effect74(**kwargs): kwargs["target"].status["reflux"] = 1
    def effect75(**kwargs): kwargs["target"].status["delusion"] = 7
    def effect76(**kwargs): kwargs["target"].stats["HP_cur"] += 0.4*kwargs["target"].stats["HP_max"]
    def effect77(**kwargs): kwargs["target"].stats["HP_cur"] += 0.1*kwargs["target"].stats["HP_max"]
    def effect78(**kwargs): kwargs["target"].stats["HP_cur"] += 0.3*kwargs["target"].stats["HP_max"]
    def effect79(**kwargs): kwargs["target"].status["haze"] = 1
    def effect80(**kwargs): kwargs["target"].status["death_curse"] = 1
    def effect81(**kwargs): pass
    def effect82(**kwargs): pass
    def effect83(**kwargs): kwargs["target"].immobilize = 1
    def effect84(**kwargs): kwargs["target"].stats["PP_cur"] *= 0.9
    def effect85(**kwargs): kwargs["target"].status["stun"] = 7
    def effect86(**kwargs): pass
    def effect87(**kwargs): pass
    def effect88(**kwargs): kwargs["target"].damage_mult *= 0.05
    def effect89(**kwargs): return {"MULT": [1,2,3]}
    def effect90(**kwargs): return {"DEF": 0}
    def effect91(**kwargs): pass
    funcs = locals()
    return [funcs[f"effect{i}"] for i in range(92)]


equipped_effects = get_equipped_effects()
ability_effects = get_ability_effects()


class PlayerData:

    def __init__(self, data=bytearray(0x14C)):
        self.extract(data)

    def extract(self, data):
        read = lambda addr, size: int.from_bytes(data[addr:addr+size], "little")
        readsigned = lambda addr, size: (read(addr, size) ^ 2**(8*size)) - 2**(8*size)
        string = lambda addr, size: data[addr:addr+size].replace(b"\x00",b"").decode()
        self.name = string(0, 15)
        self.level = read(0xF, 1)
        self.base_stats = {
            "HP_max": read(0x10, 2),
            "PP_max": read(0x12, 2),
            "HP_cur": read(0x14, 2),
            "PP_cur": read(0x16, 2),
            "ATK": read(0x18, 2),
            "DEF": read(0x1A, 2),
            "AGI": read(0x1C, 2),
            "LCK": read(0x1E, 1),
            "turns": read(0x1F, 1),
            "HP_regen": read(0x20, 1),
            "PP_regen": read(0x21, 1),
            "epow": [read(0x24+4*j, 2) for j in range(4)],
            "eres": [read(0x26+4*j, 2) for j in range(4)],
        }
        self.stats = {
            "HP_max": read(0x34, 2),
            "PP_max": read(0x36, 2),
            "HP_cur": read(0x38, 2),
            "PP_cur": read(0x3A, 2),
            "ATK": read(0x3c, 2),
            "DEF": read(0x3e, 2),
            "AGI": read(0x40, 2),
            "LCK": read(0x42, 1),
            "turns": read(0x43, 1),
            "HP_regen": read(0x44, 1),
            "PP_regen": read(0x45, 1),
            "epow": [read(0x48+4*j, 2) for j in range(4)],
            "eres": [read(0x4A+4*j, 2) for j in range(4)],
        }
        self.abilities = [read(0x58+4*j, 4) for j in range(32)]
        self.inventory = [read(0xD8+2*j, 2) for j in range(15)]
        self.djinn = [read(0xF8+4*j, 4) for j in range(4)]
        self.set_djinn = [read(0x108+4*j, 4) for j in range(4)]
        self.djinncounts = [read(0x118+j, 1) for j in range(4)]
        self.set_djinncounts = [read(0x11C+j, 1) for j in range(4)]
        self.exp = read(0x124, 4)
        self.class_ = read(0x129, 1)
        self.unknown = read(0x12A, 1)
        self.defending = read(0x12B, 1)
        self.status = {
            "summon_boosts": [read(0x12C+j, 1) for j in range(4)],
            "curse": read(0x130,1),
            "poison": int(read(0x131,1)==1),
            "venom": int(read(0x131,1)==2),
            "attack_buff": [read(0x132,1), readsigned(0x133,1)], #turns, amount
            "defense_buff": [read(0x134,1), readsigned(0x135,1)],
            "resist_buff": [read(0x136,1), readsigned(0x137,1)],
            "delusion": read(0x138,1),
            "confusion": read(0x139,1),
            "charm": read(0x13A,1),
            "stun": read(0x13B,1),
            "sleep": read(0x13C,1),
            "psy_seal": read(0x13D,1),
            "hp_regen": read(0x13E,1),
            "reflect": read(0x13F,1),
            "haunt": read(0x140,1),
            "death_curse": read(0x141,1),
            "critical_rate": read(0x142,1),
            "counterstrike": read(0x143,1),
            "kite": read(0x144,1),
            "immobilize": read(0x145,1),
            "agility_buff": [read(0x146,1), readsigned(0x147,1)],
        }
        self.ID = read(0x14A,2) or read(0x128,1)
        element = [0,2,3,1,0,2,3,1][self.ID]
        self.element = Text["elements"][element]
        self.abilities = {Text["abilities"][i & 0x3FF]: i for i in self.abilities if i & 0x3FF}
        for k, v in self.abilities.items():
            metadata = []
            if v & 1<<15: metadata.append("class")
            if v & 1<<14: metadata.append("item")
            self.abilities[k] = metadata
        self.inventory = {
            DataTables["itemdata"][i & 0x1FF]["name"]: i for i in self.inventory if i & 0x1FF}
        for k, v in self.inventory.items():
            metadata = [(v>>11 & 0x1F) + 1]
            if v & 1<<9: metadata.append("equipped")
            if v & 1<<10: metadata.append("broken")
            self.inventory[k] = metadata
        self.class_ = DataTables["classdata"][self.class_]["name"]
        self.weaknesses = DataTables.get("classdata", self.class_)["weaknesses"].copy()
        self.djinn = sum((d<<20*i for i,d in enumerate(self.djinn)))
        self.set_djinn = sum((d<<20*i for i,d in enumerate(self.set_djinn)))
        self.djinn = [Text["djinn"][i] for i in range(80) if self.djinn & 2**i]
        self.set_djinn = [Text["djinn"][i] for i in range(80) if self.set_djinn & 2**i]
        self.elevels = self.set_djinncounts.copy()
        self.elevels[element] += 5

    def get_byte_data(self):
        data = bytearray(0x14C)
        def write(addr,value,size): data[addr:addr+size] = value.to_bytes(size, "little")
        def string(addr,value,size): data[addr:addr+len(value)] = value.encode()

        string(0, self.name, 15)
        write(0xF, self.level, 1)
        
        write(0x10, self.base_stats["HP_max"], 2)
        write(0x12, self.base_stats["PP_max"], 2)
        write(0x14, self.base_stats["HP_cur"], 2)
        write(0x16, self.base_stats["PP_cur"], 2)
        write(0x18, self.base_stats["ATK"], 2)
        write(0x1A, self.base_stats["DEF"], 2)
        write(0x1C, self.base_stats["AGI"], 2)
        write(0x1E, self.base_stats["LCK"], 1)
        write(0x1F, self.base_stats["turns"], 1)
        [write(0x24+4*j, self.base_stats["epow"][j], 2) for j in range(4)]
        [write(0x26+4*j, self.base_stats["eres"][j], 2) for j in range(4)]
        
        write(0x34, self.stats["HP_max"], 2)
        write(0x36, self.stats["PP_max"], 2)
        write(0x38, self.stats["HP_cur"], 2)
        write(0x3A, self.stats["PP_cur"], 2)
        write(0x3C, self.stats["ATK"], 2)
        write(0x3E, self.stats["DEF"], 2)
        write(0x40, self.stats["AGI"], 2)
        write(0x42, self.stats["LCK"], 1)
        write(0x43, self.stats["turns"], 1)
        write(0x44, self.stats["HP_regen"], 1)
        write(0x45, self.stats["PP_regen"], 1)
        [write(0x48+4*j, self.stats["epow"][j], 2) for j in range(4)]
        [write(0x4A+4*j, self.stats["eres"][j], 2) for j in range(4)]

        ids = [DataTables.get("abilitydata", a)["ID"] for a in self.abilities]
        metadata = [("class" in m, "item" in m) for m in self.abilities.values()]
        abilities = [m[0]<<15 | m[1]<<14 | ID for ID,m in zip(ids, metadata)]
        [write(0x58+4*j, abilities[j], 4) for j in range(len(abilities))]
        ids = [DataTables.get("itemdata", a)["ID"] for a in self.inventory]
        metadata = [(m[0]-1, "broken" in m, "equipped" in m) for m in self.inventory.values()]
        items = [m[0]<<11 | m[1]<<10 | m[2]<<9 | ID for ID,m in zip(ids, metadata)]
        [write(0xD8+2*j, items[j], 2) for j in range(len(items))]
        ids = [DataTables.get("djinndata", a)["ID"] for a in self.djinn]
        djinn = [sum((1<<(i%20) for i in range(20*j, 20*j+20) if i in ids)) for j in range(4)]
        [write(0xF8+4*j, djinn[j], 4) for j in range(4)]
        ids = [DataTables.get("djinndata", a)["ID"] for a in self.set_djinn]
        set_djinn = [sum((1<<(i%20) for i in range(20*j, 20*j+20) if i in ids)) for j in range(4)]
        [write(0x108+4*j, set_djinn[j], 4) for j in range(4)]
        [write(0x118+j, self.djinncounts[j], 1) for j in range(4)]
        [write(0x11C+j, self.set_djinncounts[j], 1) for j in range(4)]
        write(0x124, self.exp, 4)
        write(0x129, DataTables.get("classdata", self.class_)["ID"], 1)
        write(0x12A, self.unknown, 1)

        write(0x130, self.status["curse"], 1)
        if self.status["poison"]: write(0x131, 1, 1)
        elif self.status["venom"]: write(0x131, 2, 1)
        write(0x140, self.status["haunt"], 1)
        write(0x142, self.status["critical_rate"], 1)
        write(0x14A, self.ID, 2)

        return data

    def equip(self, item):
        self.stats["ATK"] += item["attack"]
        self.stats["DEF"] += item["defense"]
        deferred = []
        for effect, value in item["equipped_effects"].items():
            effect_index = Text.get("equipped_effects", effect)
            effect_func = equipped_effects[effect_index]
            if effect_index in range(7,15):
                deferred.append((effect_func, value))
            else:
                effect_func(self, value)
        if item["use_type"] == "Bestows Ability":
            self.abilities.append(item["use_ability"])
        return deferred

    def add_djinn(self, djinn):
        self.stats["HP_max"] += djinn["HP"]
        self.stats["PP_max"] += djinn["PP"]
        for stat in ("ATK","DEF","AGI","LCK"):
            self.stats[stat] += djinn[stat]

    def update_stats(self):
        equipped = [item for item in self.inventory if "equipped" in self.inventory[item]]
        hp_percent = self.stats["HP_cur"]/self.stats["HP_max"]
        pp_percent = self.stats["PP_cur"]/self.stats["PP_max"]
        self.stats = deepcopy(self.base_stats)
        self.status["critical_rate"] = 0
        deferred = []
        self.abilities = []
        for item in equipped:
            deferred.extend(self.equip(DataTables.get("itemdata", item)))
        for djinn in self.set_djinn: self.add_djinn(DataTables.get("djinndata",djinn))
        class_items = set(equipped) & {"Mysterious Card", "Trainer's Whip", "Tomegathericon"}
        class_item = next(iter(class_items), None)
        name = Text["pcnames"][self.ID]
        class_ = getclass(name, self.set_djinncounts, class_item)
        self.class_ = class_["name"]
        self.weaknesses = class_["weaknesses"].copy()
        self.abilities.extend((a for a,l in class_["abilities"].items() if l <= self.level))
        self.stats["HP_max"] = int(self.stats["HP_max"]*class_["HP"])
        self.stats["HP_cur"] = int(self.stats["HP_max"]*hp_percent)
        self.stats["PP_max"] = int(self.stats["PP_max"]*class_["PP"])
        self.stats["PP_cur"] = int(self.stats["PP_max"]*hp_percent)
        for stat in ("ATK","DEF","AGI","LCK"):
            self.stats[stat] = int(self.stats[stat]*class_[stat])
        for func, value in deferred: func(self, value)
        for status, stat in zip(("attack","defense","agility"), ("ATK","DEF","AGI")):
            turns, amt = self.status[status+"_buff"]
            self.stats[stat] = int(self.stats[stat]*(1+12.5*amt))
        turns, amt = self.status["resist_buff"]
        boosts = [(0,10,30,60,100)[i] for i in self.status["summon_boosts"]]
        for i in range(4):
            self.stats["epow"][i] += boosts[i]
            self.stats["eres"][i] += 20*amt


class EnemyData:
    def __init__(self, obj):
        self.name = obj["name"]
        self.level = obj["level"]
        self.base_stats = {
            "HP_max": obj["HP"],
            "PP_max": obj["PP"],
            "HP_cur": obj["HP"],
            "PP_cur": obj["PP"],
            "ATK": obj["ATK"],
            "DEF": obj["DEF"],
            "AGI": obj["AGI"],
            "LCK": obj["LCK"],
            "turns": obj["turns"],
            "HP_regen": obj["HP_regen"],
            "PP_regen": obj["PP_regen"],
            "epow": obj["epow"].copy(),
            "eres": obj["eres"].copy(),
        }
        self.stats = deepcopy(self.base_stats)
        self.abilities = obj["abilities"]
        self.inventory = obj["inventory"]
        self.exp = obj["exp"]
        self.defending = 0
        self.status = {
            "summon_boosts": [0 for j in range(4)],
            "curse": 0,
            "poison": 0,
            "venom": 0,
            "attack_buff": [0, 0], #turns, amount
            "defense_buff": [0, 0],
            "resist_buff": [0, 0],
            "delusion": 0,
            "confusion": 0,
            "charm": 0,
            "stun": 0,
            "sleep": 0,
            "psy_seal": 0,
            "hp_regen": 0,
            "reflect": 0,
            "haunt": 0,
            "death_curse": 0,
            "critical_rate": 0,
            "counterstrike": 0,
            "kite": 0,
            "immobilize": 0,
            "agility_buff": [0, 0],
        }
        self.ID = obj["ID"]
        self.attack_pattern = obj["attack_pattern"]
        self.elevels = obj["elevels"]
        self.weaknesses = obj["weaknesses"]

    def update_stats(self):
        hp_cur, pp_cur = self.stats["HP_cur"], self.stats["PP_cur"]
        self.stats = deepcopy(self.base_stats)
        self.stats["HP_cur"], self.stats["PP_cur"] = hp_cur, pp_cur
        for status, stat in zip(("attack","defense","agility"), ("ATK","DEF","AGI")):
            turns, amt = self.status[status+"_buff"]
            self.stats[stat] = int(self.stats[stat]*(1+12.5*amt))
        turns, amt = self.status["resist_buff"]
        boosts = [(0,10,30,60,100)[i] for i in self.status["summon_boosts"]]
        for i in range(4):
            self.stats["epow"][i] += boosts[i]
            self.stats["eres"][i] += 20*amt


def get_save_data(data):
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
    valid_headers = [h for h in headers if h["header"] == b"CAMELOT" and h["slot"] <= 0xF]
    slots = {}
    for h in valid_headers:
        if h["priority"] > slots.get(h["slot"], -1):
            slots[h["slot"]] = h
    for slot, header in slots.items():
        f.seek(header["addr"] + 0x10)
        slots[slot] = f.read(0x2FF0)
    return slots


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


def readsav(data):
    slots = get_save_data(data)
    filedata = []
    for i in sorted(slots):
        data = slots[i]
        read = lambda addr, size: int.from_bytes(data[addr:addr+size], "little")
        string = lambda addr, size: data[addr:addr+size].replace(b"\x00",b"").decode()
        version = build_dates.get(read(0x26, 2) & ~0x8000)
        if version is None: continue
        if "The Lost Age" in version: GAME = 2; offset = 0x20
        else: GAME = 1; offset = 0
        party_size = sum((1 if read(0x40, 1) & 2**j else 0 for j in range(8)))
        positions = [read(0x438+offset + j, 1) for j in range(party_size)]
        addresses = [0x500+offset + 0x14C*p for p in positions]
        slot = {
            "version": version,
            "slot": i,
            "leader": string(0, 12),
            "framecount": read(0x244, 4),
            "summons": read(0x24C, 4),
            "coins": read(0x250, 4),
            "map_number": read(0x400+offset, 2),
            "door_number": read(0x402+offset, 2),
            "party_positions": positions,
            "party": [PlayerData(data[base:base+0x14C]) for base in addresses],
        }
        summons = [s["name"] for s in DataTables["summondata"]]
        summons[24:26] = ["Daedalus"]
        slot["summons"] = [summons[i] for i in range(33) if slot["summons"] & 2**i]
        slot["area"] = roomname(GAME, slot["map_number"], slot["door_number"])
        seconds, minutes, hours = (slot["framecount"]//60**i for i in range(1,4))
        slot["playtime"] = "{:02}:{:02}:{:02}".format(hours, minutes % 60, seconds % 60),
        slot["djinncounts"] = [sum((pc.djinncounts[i] for pc in slot["party"])) for i in range(4)]
        filedata.append(slot)
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
        maxlen = max(len(str(f["djinncounts"])), *(len(pc.name)+4 for pc in f["party"]))
        slot["PCs"] = [f"{pc.name:<{maxlen-4}}{pc.level:>4}" for pc in f["party"]]
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
            x,y = out.addtext(f"{pc.name}\n{pc.class_}", (0, 0))
            x,y = out.addtext(f"Lvl {pc.level}\nExp {pc.exp}", (x+3,0))
            x += 2
            perm_status = []
            if pc.stats["HP_cur"] == 0: perm_status.append("Downed")
            for status in ("Curse", "Poison", "Venom", "Haunt"):
                if pc.status[status.lower()]: perm_status.append(status)
            for i in range(0, len(perm_status), 2):
                x,y = out.addtext("\n".join(perm_status[i:i+2]), (x+1, 0))
            out.addtext("Stats", (0, 3))
            x,y = out.addtext(utilities.dictstr({
                "HP": f"{pc.stats['HP_cur']}/{pc.stats['HP_max']}",
                "PP": f"{pc.stats['PP_cur']}/{pc.stats['PP_max']}",
                "ATK": pc.stats["ATK"]}, sep=" "), (0, 4))
            x,y = out.addtext(utilities.dictstr({
                "DEF": pc.stats["DEF"],
                "AGI": pc.stats["AGI"],
                "LCK": pc.stats["LCK"]}, sep=" "), (x+2, 4))
            out.addtext("Base Stats", (x+3, 3))
            x,y = out.addtext(utilities.dictstr({
                "HP": pc.base_stats['HP_max'],
                "PP": pc.base_stats['PP_max'],
                "ATK": pc.base_stats["ATK"]}, sep=" "), (x+3, 4))
            x,y = out.addtext(utilities.dictstr({
                "DEF": pc.base_stats["DEF"],
                "AGI": pc.base_stats["AGI"],
                "LCK": pc.base_stats["LCK"]}, sep=" "), (x+2, 4))
            elementdata = []
            for i, name in enumerate(["ven", "merc", "mars", "jup"]):
                elementdata.append(
                    {"Estats": name.title(),
                    "Djinn": f"{pc.set_djinncounts[i]}/{pc.djinncounts[i]}",
                    "Level": pc.elevels[i],
                    "Power": pc.stats["epow"][i],
                    "Resist": pc.stats["eres"][i]})
            out.addtext(utilities.tableV(elementdata), (x+3,2))
            out.addtext("Items", (0, 8))
            inventory = []
            for k,v in pc.inventory.items():
                state = "B" if "broken" in v[1:] else "E" if "equipped" in v[1:] else "-"
                inventory.append({"item": k+" ", "amt": v[0], "state": state})
            x = -1
            ymax = 0
            for i in range(0, len(inventory), 5):
                x,y = out.addtext(utilities.tableH(inventory[i:i+5], headers=False), (x+3, 9))
                ymax = max(ymax, y)
            out.addtext("Djinn", (0, ymax+1))
            djinn = []
            for d in pc.djinn:
                djinn.append({"name": d, "state": "√" if d in pc.set_djinn else "-"})
            x,_ = out.addtext(utilities.tableH(djinn, headers=False), (2,ymax+2))
            x = max(x, 4)
            out.addtext("Abilities", (x+3, ymax+1))
            x += 2
            if pc.abilities:
                abilities = list(pc.abilities)
                height = max(len(abilities)/4, len(pc.djinn))
                height = int(height) + 1 if height != int(height) else int(height)
                for i in range(0, len(abilities), height):
                    x,_ = out.addtext("\n".join(abilities[i:i+height]), (x+3, ymax+2))
            pages[slot].append(f"```\n{out}\n```")
    return pages


def rn_value(count,initValue=0):
    for i in range(32):
        if (count >> i) & 1:
            initValue = (initValue*multipliers[i] + increments[i]) & 0xFFFFFFFF
    return initValue

def rn_count(value):
    advances = 0
    for i in range(32):
        if value & 2**i:
            value = (value*multipliers[i] + increments[i]) & 0xFFFFFFFF
            advances += 2**i
    return -advances & 0xFFFFFFFF

def rn_iter(init, u32=False):
    while True:
        init = (0x41C64E6D*init + 0x3039) % 2**32
        if u32: yield init
        else: yield (init >> 8) & 0xFFFF
