import json
import sys
from obababot import utilities

if len(sys.argv) == 3:
    ROM1 = sys.argv[1]
    ROM2 = sys.argv[2]
else:
    ROM1 = input("ROM1: ")
    ROM2 = input("ROM2: ")

if __name__ == "__main__": utilities.Text = utilities.load_text()
Text = utilities.Text


def instance_counts(array):
    namedict = {}
    for obj in array:
        namedict[obj["name"]] = namedict.get(obj["name"], 0) + 1
    return {k:v for k,v in namedict.items() if k != "?" and v > 1}

def add_instance_numbers(array):
    namedict = instance_counts(array)
    for obj in reversed(array):
        count = namedict.get(obj["name"])
        if count:
            namedict[obj["name"]] -= 1
            obj["name"] += f" ({count})"

def combined_lists(*lists):
    combined = []
    for group in lists:
        combined += group
    return list(sorted(set(combined)))


with open(ROM1, "rb") as f:
    def read(size):
        return int.from_bytes(f.read(size), "little")

    f.seek(0x07B6A8)  # item data (44 bytes per entry)
    itemdata = []
    for i in range(269):
        itemdata.append({
            "ID": i,
            "name": Text["GS1"]["items"][i],
            "price": read(2),
            "item_type": read(1),
            "flags": read(1),
            "equippable_by": read(1),
            "unused": read(1),
            "icon": read(2),
            "attack": read(2),
            "defense": read(1),
            "unleash_rate": read(1),
            "use_type": read(1),
            "unused": read(1),
            "unleash_ability": read(2),
            "unused": read(4),
            "element": Text["elements"][read(4)],
            "equipped_effects": [[read(1), read(1), read(2)] for j in range(4)],
            "use_ability": Text["GS1"]["abilities"][read(2)],
            "unused": read(2),
            "dropped_by": [],
            "description": Text["GS1"]["item_descriptions"][i],
        })
    add_instance_numbers(itemdata)

    f.seek(0x07EE58)  # ability data (16 bytes per entry)
    abilitydata = []
    for i in range(519):
        abilitydata.append({
            "ID": i,
            "name": Text["GS1"]["abilities"][i],
            "target": read(1),
            "flags": read(1),
            "damage_type": None,
            "element": Text["elements"][read(1)],
            "effect": Text["ability_effects"][read(1)],
            "icon": read(2),
            "utility": read(1),
            "unused": read(1),
            "range": read(1),
            "PP_cost": read(1),
            "power": read(2),
            "description": Text["GS1"]["move_descriptions"][i],
            "unused": read(4),
        })
    add_instance_numbers(abilitydata)

    f.seek(0x080EC8)  # enemy data (84 bytes per entry)
    enemydata = []
    for i in range(164):
        enemydata.append({
            "ID": i,
            "name": Text["GS1"]["enemynames"][i],
            "unused": read(15),
            "level": read(1),
            "HP": read(2),
            "PP": read(2),
            "ATK": read(2),
            "DEF": read(2),
            "AGI": read(2),
            "LCK": read(1),
            "elevels": None,
            "epow": None,
            "eres": None,
            "turns": read(1),
            "HP_regen": read(1),
            "PP_regen": read(1),
            "inventory": [read(2) for j in range(4)],
            "item_quantities": [read(1) for j in range(4)],
            "unused": read(10),
            "elemental_stats_id": read(1),
            "IQ": read(1),
            "attack_pattern": read(1),
            "item_priority_flags": read(1),
            "abilities": [Text["GS1"]["abilities"][read(2)] for j in range(8)],
            "weaknesses": [read(1) for j in range(3)],
            "unused": read(1),
            "coins": read(2),
            "item_drop": read(2),
            "item_chance_class": read(2),
            "exp": read(2),
        })
    add_instance_numbers(enemydata)

    f.seek(0x0844EC)  # pc data (180 bytes per entry)
    pcdata = []
    for i in range(8):
        pcdata.append({
            "ID": i,
            "name": Text["pcnames"][i],
            "element": Text["elements"][[0,2,3,1,0,2,3,1][i]],
            "unused": read(80),
            "HP_growths": [read(2) for j in range(6)],
            "PP_growths": [read(2) for j in range(6)],
            "ATK_growths": [read(2) for j in range(6)],
            "DEF_growths": [read(2) for j in range(6)],
            "AGI_growths": [read(2) for j in range(6)],
            "LCK_growths": [read(1) for j in range(6)],
            "elevels": [read(1)/10 for j in range(4)],
            "starting_level": read(2),
            "starting_items": [read(2) for j in range(14)],
        })

    f.seek(0x084A9C)  # summon data (8 bytes per entry)
    summondata = []
    for i in range(16):
        summondata.append({
            "ID": i,
            "ability": read(4),
            "djinn_cost": [read(1) for j in range(4)],
            "hp_multiplier": None,
        })

    f.seek(0x084B1C)  # class data (84 bytes per entry)
    classdata = []
    classdataset = {}
    for i in range(203):
        classdata.append({
            "ID": i,
            "name": Text["GS1"]["classes"][i],
            "class_group": read(4),
            "elevels": [read(1) for j in range(4)],
            "HP": read(1),
            "PP": read(1),
            "ATK": read(1),
            "DEF": read(1),
            "AGI": read(1),
            "LCK": read(1),
            "unused": read(2),
            "abilities": [(read(1), read(1), read(2)) for j in range(16)],
            "weaknesses": [read(1) for j in range(3)],
            "unused": read(1),
        })
        c1, c2 = classdataset.get(Text["GS1"]["classes"][i]), classdata[-1]
        if c1 and c1["name"] != "?" and not {c1["ID"], c2["ID"]} & {121, 122}:
            for suffix, e1, e2 in zip("EWFA", c1["elevels"], c2["elevels"]):
                if e1 > e2: c1["name"] += f" ({suffix})"
                if e2 > e1: c2["name"] += f" ({suffix})"
        classdataset[Text["GS1"]["classes"][i]] = c2

    f.seek(0x088E38)  # elemental data (24 bytes per entry)
    elementdata = []
    for i in range(44):
        elementdata.append({
            "ID": i,
            "unused": read(4),
            "elevels": [read(1) for j in range(4)],
            "epowres": [(read(2), read(2)) for j in range(4)],
        })
        entry = elementdata[-1]
        entry["epow"], entry["eres"] = zip(*entry.pop("epowres"))

    f.seek(0x08926C)  # djinn data (12 bytes per entry)
    djinndata = []
    for i in range(80):
        djinndata.append({
            "ID": i,
            "name": Text["GS1"]["djinn"][i],
            "element": Text["elements"][i//20],
            "ability": read(2),
            "damage_type": None,
            "effect": None,
            "target": None,
            "power": None,
            "unused": read(2),
            "HP": read(1),
            "PP": read(1),
            "ATK": read(1),
            "DEF": read(1),
            "AGI": read(1),
            "LCK": read(1),
            "description": None,
            "unused": read(2),
        })

    f.seek(0x09C610)  # encounter data (28 bytes per entry)
    encounterdata = []
    for i in range(104):
        encounterdata.append({
            "ID": i,
            "rate": read(2),
            "level": read(2),
            "enemygroups": [read(2) for j in range(8)],
            "group_ratios": [read(1) for j in range(8)],
        })

    f.seek(0x09D170)  # encounters by map (8 bytes per entry)
    map_encounters = []
    for i in range(198):
        map_encounters.append({
            "ID": i,
            "room": read(2),
            "door": read(2),
            "flag_id": read(2),
            "encounter_ids": [read(1), read(1)],
        })

    f.seek(0x09D7A8)  # encounters on world map (8 bytes per entry)
    wmap_encounters = []
    for i in range(32):
        wmap_encounters.append({
            "ID": i,
            "area_type": read(2),
            "terrain": read(2),
            "flag_id": read(2),
            "encounter_ids": read(2),
        })

    room_references = []
    f.seek(0x09DDD8)  # room name reference table (8 bytes per entry)
    for i in range(126):
        room_references.append({
            "ID": i,
            "room_or_area": read(2),
            "door": read(2),
            "name": Text["GS1"]["areas"][read(2)],
            "unused": read(2),
        })

    f.seek(0x09F1A8)  # map data (8 bytes per entry)
    mapdata = []
    for i in range(201):
        mapdata.append({
            "ID": i,
            "name": Text["GS1"]["maps"][i],
            "area_names": set(),
            "file_index": read(2),
            "area": read(1),
            "type": read(1),
            "MFT_index": read(2),
            "outdoor": read(2),
            "encounters": set(),
            "enemygroups": [],
            "enemies": [],
        })

    f.seek(0x0C5C38) # enemy group data (16 bytes per entry)
    enemygroupdata = []
    for i in range(380):
        enemygroupdata.append({
            "ID": i,
            "unused": read(1),
            "enemies": [Text["GS1"]["enemynames"][read(1)] for j in range(5)],
            "min_amounts": [read(1) for j in range(5)],
            "max_amounts": [read(1) for j in range(5)],
        })

# Items
itemtypes = [
    "Other", "Weapon", "Armor", "Armgear", "Headgear", "Boots", "Psy-item", 
    "Trident", "Ring", "Shirt", "Class-item", "Elemental Star"]
flagdesc = ["Cursed", "Not removable", "Rare item", "Important item", "Stackable", "Not transferable"]
usetypes = ["Multi-Use", "Consumable", "Can Break", "Bestows ability", "Transforms when used"]
for item in itemdata:
    item.pop("unused")
    item["item_type"] = itemtypes[item["item_type"]]
    item["unleash_ability"] = abilitydata[item["unleash_ability"]]["name"]
    item["equipped_effects"] = {Text["equipped_effects"][e]: v for e,v,u in item["equipped_effects"] if e}
    item["equippable_by"] = [Text["pcnames"][i] for i in range(8) if item["equippable_by"] & 2**i]
    item["flags"] = [flagdesc[i] for i in range(6) if item["flags"] & 2**i]
    item["use_type"] = usetypes[item["use_type"]]

# Abilities
targets = ["Utility", "Enemies", "Allies", "?", "Self"]
damagetypes = [
        "?", "Healing","Effect Only","Added Damage","Multiplier","Base Damage",
        "Base Damage (Diminishing)","Djinn Effect","Summon","Utility",
        "Psynergy Drain","Psynergy Recovery"]
flagdesc = ["", "", "usable out of battle", "usable in battle"]
for move in abilitydata:
    move.pop("unused")
    move["target"] = targets[move["target"]]
    move["damage_type"] = damagetypes[move["flags"] & 0xF]
    move["flags"] = move["flags"] >> 4
    move["flags"] = [flagdesc[i] for i in range(2, 4) if move["flags"] & 2**i]

# Enemies
for enemy in enemydata:
    enemy.pop("unused")
    for name in ("elevels", "epow", "eres"):
        enemy[name] = elementdata[enemy["elemental_stats_id"]][name]
    enemy["inventory"] = [Text["GS1"]["items"][i] for i in enemy["inventory"] if i]
    enemy["inventory"] = dict(zip(enemy["inventory"], enemy.pop("item_quantities")))
    if "Dullahan" in enemy["name"] or "Serpent" in enemy["name"]: enemy["HP_regen"] *= 10
    enemy["weaknesses"] = [Text["ability_effects"][i] for i in enemy["weaknesses"] if i]
    itemID = enemy["item_drop"]
    if itemID: itemdata[itemID]["dropped_by"].append(enemy["name"])
    enemy["item_drop"] = Text["GS1"]["items"][itemID]

# PCs
for pc in pcdata:
    pc.pop("unused")
    pc["starting_items"] = [Text["GS1"]["items"][i] for i in pc["starting_items"] if i]

# Summons
for summon in summondata:
    move = abilitydata[summon["ability"]]
    summon.update({**move, **summon})
    summon["name"] = abilitydata[summon["ability"]]["name"]
    if summon["hp_multiplier"] is None:
        summon["hp_multiplier"] = sum(summon["djinn_cost"])*0.03
    move["hp_multiplier"] = summon["hp_multiplier"]
    move["djinn_cost"] = summon["djinn_cost"]

# Classes
classgroups = [
    "", "Squire", "Guard", "Swordsman", "Brute",
    "Apprentice", "Water Seer", "Wind Seer", "Seer",
    "Pilgrim", "Hermit", "", "NPC", "Flame User",
    "Mariner", "Pierrot", "Tamer", "Dark Mage"]
for class_ in classdata:
    class_.pop("unused")
    class_["abilities"] = {Text["GS1"]["abilities"][k]: v for k,v,u in class_["abilities"] if k != 0}
    class_["class_group"] = classgroups[class_["class_group"]]
    class_["weaknesses"] = [Text["ability_effects"][i] for i in class_["weaknesses"] if i]
    for k in ["HP", "PP", "ATK", "DEF", "AGI", "LCK"]:
        class_[k] /= 10
classdata[121]["name"] += " (M)"
classdata[122]["name"] += " (M)"

# Element Table
for entry in elementdata:
    entry.pop("unused")

# Djinn
for djinni in djinndata:
    djinni.pop("unused")
    move = abilitydata[djinni["ability"]]
    djinni["damage_type"] = move["damage_type"]
    djinni["effect"] = move["effect"]
    djinni["target"] = move["target"]
    djinni["power"] = move["power"]
    djinni["description"] = move["description"]

# Enemy Groups
for group in enemygroupdata:
    group.pop("unused")
    entries = [i for i in range(5) if group["enemies"][i] != "???"]
    group["enemies"] = [group["enemies"][i] for i in entries]
    group["min_amounts"] = [group["min_amounts"][i] for i in entries]
    group["max_amounts"] = [group["max_amounts"][i] for i in entries]

# Enounter Data
for encounter in encounterdata:
    encounter["enemies"] = combined_lists(*(enemygroupdata[e]["enemies"] for e in encounter["enemygroups"]))

# Map Names
for encounter in map_encounters:
    room = mapdata[encounter["room"]]
    room["encounters"].update((e for e in encounter["encounter_ids"] if e))
mapdata[2]["encounters"] = set((e["encounter_ids"] for e in wmap_encounters if e))
temp_areas = {}
for room in room_references:
    flag = room["door"] >> 15
    roa = room["room_or_area"]
    if flag: mapdata[roa]["area_names"].add(room["name"])
    else: temp_areas[roa] = room["name"]
for map_ in mapdata:
    area = map_["area"]
    if area in temp_areas:
        map_["area_names"].add(temp_areas[area])
for map_ in mapdata:
    map_["area_names"] = list(sorted(map_["area_names"]))
    map_["encounters"] = list(sorted(map_["encounters"]))
    map_["enemygroups"] = combined_lists(*(encounterdata[e]["enemygroups"] for e in map_["encounters"]))
    map_["enemies"] = combined_lists(*(enemygroupdata[e]["enemies"] for e in map_["enemygroups"]))


for name in [
        "djinndata", "enemydata", "itemdata", "abilitydata", "pcdata",
        "summondata", "classdata", "elementdata", "encounterdata",
        "mapdata", "room_references", "enemygroupdata"]:
    with open(f"obababot/data/GS1/{name}.json", "w") as f:
        json.dump(globals()[name], f, indent=4)


with open(ROM2, "rb") as f:
    def read(size):
        return int.from_bytes(f.read(size), "little")
    
    f.seek(0x0B2364)  # item data (44 bytes per entry)
    itemdata = []
    for i in range(461):
        itemdata.append({
            "ID": i,
            "name": Text["GS2"]["items"][i],
            "price": read(2),
            "item_type": read(1),
            "flags": read(1),
            "equippable_by": read(1),
            "unused": read(1),
            "icon": read(2),
            "attack": read(2),
            "defense": read(1),
            "unleash_rate": read(1),
            "use_type": read(1),
            "unused": read(1),
            "unleash_ability": read(2),
            "unused": read(4),
            "element": Text["elements"][read(4)],
            "equipped_effects": [[read(1), read(1), read(2)] for j in range(4)],
            "use_ability": Text["GS2"]["abilities"][read(2)],
            "unused": read(2),
            "dropped_by": [],
            "description": Text["GS2"]["item_descriptions"][i],
        })
    add_instance_numbers(itemdata)

    f.seek(0x0B7C14)  # ability data (12 bytes per entry)
    abilitydata = []
    for i in range(734):
        abilitydata.append({
            "ID": i,
            "name": Text["GS2"]["abilities"][i],
            "target": read(1),
            "flags": read(1),
            "damage_type": None,
            "element": Text["elements"][read(1)],
            "effect": Text["ability_effects"][read(1)],
            "icon": read(2),
            "utility": read(1),
            "unused": read(1),
            "range": read(1),
            "PP_cost": read(1),
            "power": read(2),
            "description": Text["GS2"]["move_descriptions"][i]
        })
    add_instance_numbers(abilitydata)

    f.seek(0x0B9E7C)  # enemy data (76 bytes per entry)
    enemydata = []
    for i in range(379):
        enemydata.append({
            "ID": i,
            "name": Text["GS2"]["enemynames"][i],
            "unused": read(15),
            "level": read(1),
            "HP": read(2),
            "PP": read(2),
            "ATK": read(2),
            "DEF": read(2),
            "AGI": read(2),
            "LCK": read(1),
            "elevels": None,
            "epow": None,
            "eres": None,
            "turns": read(1),
            "HP_regen": read(1),
            "PP_regen": read(1),
            "inventory": [read(2) for j in range(4)],
            "item_quantities": [read(1) for j in range(4)],
            "elemental_stats_id": read(1),
            "IQ": read(1),
            "attack_pattern": read(1),
            "item_priority_flags": read(1),
            "abilities": [Text["GS2"]["abilities"][read(2)] for j in range(8)],
            "weaknesses": [read(1) for j in range(3)],
            "unused": read(1),
            "coins": read(2),
            "item_drop": read(2),
            "item_chance_class": read(2),
            "exp": read(2),
            "unused": read(2),
        })
    add_instance_numbers(enemydata)

    f.seek(0x0C0F4C)  # pc data (180 bytes per entry)
    pcdata = []
    for i in range(8):
        pcdata.append({
            "ID": i,
            "name": Text["pcnames"][i],
            "element": Text["elements"][[0,2,3,1,0,2,3,1][i]],
            "unused": read(80),
            "HP_growths": [read(2) for j in range(6)],
            "PP_growths": [read(2) for j in range(6)],
            "ATK_growths": [read(2) for j in range(6)],
            "DEF_growths": [read(2) for j in range(6)],
            "AGI_growths": [read(2) for j in range(6)],
            "LCK_growths": [read(1) for j in range(6)],
            "elevels": [read(1)/10 for j in range(4)],
            "starting_level": read(2),
            "starting_items": [read(2) for j in range(14)],
        })

    f.seek(0x0C150C)  # summon data (8 bytes per entry)
    summondata = []
    for i in range(29):
        summondata.append({
            "ID": i,
            "ability": read(4),
            "djinn_cost": [read(1) for j in range(4)],
            "hp_multiplier": None,
        })
    othersummons = [(24,403,0.15), (29,514,0), (30,515,0), (31,673,0.3), (32,683,0.35), (33,724,0.4)]
    for ID, ability, mult in othersummons:
        summondata.append({
            "ID": ID,
            "ability": ability,
            "djinn_cost": [0,0,0,0],
            "hp_multiplier": mult,
        })
    summondata.insert(25,summondata.pop(29))

    f.seek(0x0C15F4)  # class data (84 bytes per entry)
    classdata = []
    classdataset = {}
    for i in range(244):
        classdata.append({
            "ID": i,
            "name": Text["GS2"]["classes"][i],
            "class_group": read(4),
            "elevels": [read(1) for j in range(4)],
            "HP": read(1),
            "PP": read(1),
            "ATK": read(1),
            "DEF": read(1),
            "AGI": read(1),
            "LCK": read(1),
            "unused": read(2),
            "abilities": [(read(2), read(2)) for j in range(16)],
            "weaknesses": [read(1) for j in range(3)],
            "unused": read(1),
        })
        c1, c2 = classdataset.get(Text["GS2"]["classes"][i]), classdata[-1]
        if c1 and c1["name"] != "?" and not {c1["ID"], c2["ID"]} & {121, 122}:
            for suffix, e1, e2 in zip("EWFA", c1["elevels"], c2["elevels"]):
                if e1 > e2: c1["name"] += f" ({suffix})"
                if e2 > e1: c2["name"] += f" ({suffix})"
        classdataset[Text["GS2"]["classes"][i]] = c2

    f.seek(0x0C6684)  # elemental data (24 bytes per entry)
    elementdata = []
    for i in range(48):
        elementdata.append({
            "ID": i,
            "unused": read(4),
            "elevels": [read(1) for j in range(4)],
            "epowres": [(read(2), read(2)) for j in range(4)],
        })
        entry = elementdata[-1]
        entry["epow"], entry["eres"] = zip(*entry.pop("epowres"))

    f.seek(0x0C6BB0)  # djinn data (12 bytes per entry)
    djinndata = []
    for i in range(80):
        djinndata.append({
            "ID": i,
            "name": Text["GS2"]["djinn"][i],
            "element": Text["elements"][i//20],
            "ability": read(2),
            "damage_type": None,
            "effect": None,
            "target": None,
            "power": None,
            "unused": read(2),
            "HP": read(1),
            "PP": read(1),
            "ATK": read(1),
            "DEF": read(1),
            "AGI": read(1),
            "LCK": read(1),
            "description": None,
            "unused": read(2),
        })

    f.seek(0x0EDACC)  # encounter data (28 bytes per entry)
    encounterdata = []
    for i in range(110):
        encounterdata.append({
            "ID": i,
            "rate": read(2),
            "level": read(2),
            "enemygroups": [read(2) for j in range(8)],
            "group_ratios": [read(1) for j in range(8)],
        })

    f.seek(0x0EE6D4)  # encounters by map (8 bytes per entry)
    map_encounters = []
    for i in range(220):
        map_encounters.append({
            "ID": i,
            "room": read(2),
            "door": read(2),
            "flag_id": read(2),
            "encounter_ids": [read(1), read(1)],
        })

    f.seek(0x0EEDBC)  # encounters on world map (8 bytes per entry)
    wmap_encounters = []
    for i in range(46):
        wmap_encounters.append({
            "ID": i,
            "area_type": read(2),
            "terrain": read(2),
            "flag_id": read(2),
            "encounter_ids": read(2),
        })

    room_references = []
    f.seek(0x0EF4A4)  # room references (8 bytes per entry)
    for i in range(110):
        room_references.append({
            "ID": i,
            "room_or_area": read(2),
            "door": read(2),
            "name": Text["GS2"]["areas"][read(2)],
            "unused": read(2),
        })

    f.seek(0x0F17A8)  # map data (8 bytes per entry)
    mapdata = []
    for i in range(325):
        mapdata.append({
            "ID": i,
            "name": Text["GS2"]["maps"][i],
            "area_names": set(),
            "file_index": read(2),
            "area": read(1),
            "type": read(1),
            "MFT_index": read(2),
            "outdoor": read(2),
            "encounters": set(),
            "enemygroups": [],
            "enemies": [],
        })

    f.seek(0x12CE7C)  # enemy group data (24 bytes per entry)
    enemygroupdata = []
    for i in range(660):
        enemygroupdata.append({
            "ID": i,
            "enemies": [Text["GS2"]["enemynames"][read(2)] for j in range(5)],
            "min_amounts": [read(1) for j in range(5)],
            "max_amounts": [read(1) for j in range(5)],
            "positioning": read(1),
            "unused": read(3),
        })

# Items
itemtypes = [
    "Other", "Weapon", "Armor", "Armgear", "Headgear", "Boots", "Psy-item", 
    "Trident", "Ring", "Shirt", "Class-item", "Elemental Star"]
flagdesc = ["Cursed", "Not removable", "Rare item", "Important item", "Stackable", "Not transferable"]
usetypes = ["Multi-Use", "Consumable", "Can Break", "Bestows ability", "Transforms when used"]
for item in itemdata:
    item.pop("unused")
    item["item_type"] = itemtypes[item["item_type"]]
    item["unleash_ability"] = abilitydata[item["unleash_ability"]]["name"]
    item["equipped_effects"] = {Text["equipped_effects"][e]: v for e,v,u in item["equipped_effects"] if e}
    item["equippable_by"] = [Text["pcnames"][i] for i in range(8) if item["equippable_by"] & 2**i]
    item["flags"] = [flagdesc[i] for i in range(6) if item["flags"] & 2**i]
    item["use_type"] = usetypes[item["use_type"]]

# Abilities
targets = ["Utility", "Enemies", "Allies", "?", "Self"]
damagetypes = [
        "?", "Healing","Effect Only","Added Damage","Multiplier","Base Damage",
        "Base Damage (Diminishing)","Djinn Effect","Summon","Utility",
        "Psynergy Drain","Psynergy Recovery"]
flagdesc = ["", "", "usable out of battle", "usable in battle"]
for move in abilitydata:
    move.pop("unused")
    move["target"] = targets[move["target"]]
    move["damage_type"] = damagetypes[move["flags"] & 0xF]
    move["flags"] = move["flags"] >> 4
    move["flags"] = [flagdesc[i] for i in range(2, 4) if move["flags"] & 2**i]

# Enemies
for enemy in enemydata:
    enemy.pop("unused")
    for name in ("elevels", "epow", "eres"):
        enemy[name] = elementdata[enemy["elemental_stats_id"]][name]
    enemy["inventory"] = [Text["GS2"]["items"][i] for i in enemy["inventory"] if i]
    enemy["inventory"] = dict(zip(enemy["inventory"], enemy.pop("item_quantities")))
    if "Dullahan" in enemy["name"] or "Serpent" in enemy["name"]: enemy["HP_regen"] *= 10
    enemy["weaknesses"] = [Text["ability_effects"][i] for i in enemy["weaknesses"] if i]
    itemID = enemy["item_drop"]
    if itemID: itemdata[itemID]["dropped_by"].append(enemy["name"])
    enemy["item_drop"] = Text["GS2"]["items"][itemID]

# PCs
for pc in pcdata:
    pc.pop("unused")
    pc["starting_items"] = [Text["GS2"]["items"][i] for i in pc["starting_items"] if i]

# Summons
summondata[24]["hp_multiplier"] = 0.07
summondata[29]["hp_multiplier"] = 0.40
for summon in summondata:
    move = abilitydata[summon["ability"]]
    summon.update({**move, **summon})
    summon["name"] = abilitydata[summon["ability"]]["name"]
    if summon["hp_multiplier"] is None:
        summon["hp_multiplier"] = sum(summon["djinn_cost"])*0.03
    move["hp_multiplier"] = summon["hp_multiplier"]
    move["djinn_cost"] = summon["djinn_cost"]

# Classes
classgroups = [
    "", "Squire", "Guard", "Swordsman", "Brute",
    "Apprentice", "Water Seer", "Wind Seer", "Seer",
    "Pilgrim", "Hermit", "", "NPC", "Flame User",
    "Mariner", "Pierrot", "Tamer", "Dark Mage"]
for class_ in classdata:
    class_.pop("unused")
    class_["abilities"] = {Text["GS2"]["abilities"][k]: v for k,v in class_["abilities"] if k != 0}
    class_["class_group"] = classgroups[class_["class_group"]]
    class_["weaknesses"] = [Text["ability_effects"][i] for i in class_["weaknesses"] if i]
    for k in ["HP", "PP", "ATK", "DEF", "AGI", "LCK"]:
        class_[k] /= 10
classdata[121]["name"] += " (M)"
classdata[122]["name"] += " (M)"

# Element Table
for entry in elementdata:
    entry.pop("unused")

# Djinn
for djinni in djinndata:
    djinni.pop("unused")
    move = abilitydata[djinni["ability"]]
    djinni["damage_type"] = move["damage_type"]
    djinni["effect"] = move["effect"]
    djinni["target"] = move["target"]
    djinni["power"] = move["power"]
    djinni["description"] = move["description"]

# Enemy Groups
for group in enemygroupdata:
    group.pop("unused")
    entries = [i for i in range(5) if group["enemies"][i] != "???"]
    group["enemies"] = [group["enemies"][i] for i in entries]
    group["min_amounts"] = [group["min_amounts"][i] for i in entries]
    group["max_amounts"] = [group["max_amounts"][i] for i in entries]

# Enounter Data
for encounter in encounterdata:
    encounter["enemies"] = combined_lists(*(enemygroupdata[e]["enemies"] for e in encounter["enemygroups"]))

# Map Names
for encounter in map_encounters:
    room = mapdata[encounter["room"]]
    room["encounters"].update((e for e in encounter["encounter_ids"] if e))
mapdata[2]["encounters"] = set((e["encounter_ids"] for e in wmap_encounters if e))
temp_areas = {}
for room in room_references:
    flag = room["door"] >> 15
    roa = room["room_or_area"]
    if flag: mapdata[roa]["area_names"].add(room["name"])
    else: temp_areas[roa] = room["name"]
for map_ in mapdata:
    area = map_["area"]
    if area in temp_areas:
        map_["area_names"].add(temp_areas[area])
for map_ in mapdata:
    map_["area_names"] = list(sorted(map_["area_names"]))
    map_["encounters"] = list(sorted(map_["encounters"]))
    map_["enemygroups"] = combined_lists(*(encounterdata[e]["enemygroups"] for e in map_["encounters"]))
    map_["enemies"] = combined_lists(*(enemygroupdata[e]["enemies"] for e in map_["enemygroups"]))


for name in [
        "djinndata", "enemydata", "itemdata", "abilitydata", "pcdata",
        "summondata", "classdata", "elementdata", "encounterdata",
        "mapdata", "room_references", "enemygroupdata"]:
    with open(f"obababot/data/GS2/{name}.json", "w") as f:
        json.dump(globals()[name], f, indent=4)
