import json
import sys
import utilities


ROM1 = sys.argv[1]
ROM2 = sys.argv[2]
if __name__ == "__main__": utilities.Text = utilities.load_text()
globals().update(**utilities.Text)


with open(ROM1, "rb") as f:
    def read(size):
        return int.from_bytes(f.read(size), "little")

    room_references1 = []
    f.seek(0x09DDD8)  # room name reference table
    for i in range(126):
        room_references1.append({
            "ID": i,
            "room_or_area": read(2),
            "door": read(2),
            "name": areas1[read(2)],
            "unused": read(2),
        })

    f.seek(0x09F1A8)  # map data
    mapdata1 = []
    for i in range(201):
        mapdata1.append({
            "ID": i,
            "name": maps1[i],
            "file_index": read(2),
            "area": read(1),
            "type": read(1),
            "MFT_index": read(2),
            "outdoor": read(2),
        })

with open(ROM2, "rb") as f:
    def read(size):
        return int.from_bytes(f.read(size), "little")
    
    f.seek(0x0B2364)  # item data
    itemdata = []
    for i in range(461):
        itemdata.append({
            "ID": i,
            "name": items[i],
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
            "element": elements[read(4)],
            "equipped_effects": [[read(1), read(1), read(2)] for i in range(4)],
            "use_ability": read(2),
            "unused": read(2),
            "dropped_by": [],
            "description": item_descriptions[i],
        })

    f.seek(0x0B7C14)  # ability data
    abilitydata = []
    for i in range(734):
        abilitydata.append({
            "ID": i,
            "name": abilities[i],
            "target": read(1),
            "flags": read(1),
            "damage_type": None,
            "element": elements[read(1)],
            "ability_effect": ability_effects[read(1)],
            "icon": read(2),
            "utility": read(1),
            "unused": read(1),
            "range": read(1),
            "PP_cost": read(1),
            "power": read(2),
            "description": move_descriptions[i]
        })

    f.seek(0x0B9E7C)  # enemy data
    enemydata = []
    for i in range(379):
        enemydata.append({
            "ID": i,
            "name": enemynames[i],
            "unused": read(15),
            "level": read(1),
            "HP": read(2),
            "PP": read(2),
            "ATK": read(2),
            "DEF": read(2),
            "AGI": read(2),
            "LCK": read(1),
            "turns": read(1),
            "HP_regen": read(1),
            "PP_regen": read(1),
            "items": [read(2) for i in range(4)],
            "item_quantities": [read(1) for i in range(4)],
            "elemental_stats_id": read(1),
            "IQ": read(1),
            "attack_pattern": read(1),
            "item_priority_flags": read(1),
            "abilities": [abilities[read(2)] for i in range(8)],
            "weaknesses": [read(1) for i in range(3)],
            "unused": read(1),
            "coins": read(2),
            "item_drop": read(2),
            "item_chance_class": read(2),
            "exp": read(2),
            "unused": read(2),
        })

    f.seek(0x0C0F4C)  # pc data
    pcdata = []
    for i in range(8):
        pcdata.append({
            "ID": i,
            "name": pcnames[i],
            "element": elements[[0,2,3,1,0,2,3,1][i]],
            "unused": read(80),
            "HP_growths": [read(2) for i in range(6)],
            "PP_growths": [read(2) for i in range(6)],
            "ATK_growths": [read(2) for i in range(6)],
            "DEF_growths": [read(2) for i in range(6)],
            "AGI_growths": [read(2) for i in range(6)],
            "LCK_growths": [read(1) for i in range(6)],
            "elevels": [read(1)/10 for i in range(4)],
            "starting_level": read(2),
            "starting_items": [read(2) for i in range(14)],
        })

    f.seek(0x0C150C)  # summon data
    summondata = []
    for i in range(29):
        moveID = read(4)
        move = abilitydata[moveID]
        summondata.append({
            "ID": i,
            "name": move["name"],
            "element": move["element"],
            "Venus": read(1),
            "Mercury": read(1),
            "Mars": read(1),
            "Jupiter": read(1),
            "ability_effect": move["ability_effect"],
            "icon": move["icon"],
            "range": move["range"],
            "power": move["power"],
            "hp_multiplier": None,
            "description": move["description"],
        })

    f.seek(0x0C15F4)  # class data
    classdata = []
    for i in range(244):
        classdata.append({
            "ID": i,
            "name": classes[i],
            "class_group": read(4),
            "Venus": read(1),
            "Mercury": read(1),
            "Mars": read(1),
            "Jupiter": read(1),
            "HP": read(1),
            "PP": read(1),
            "ATK": read(1),
            "DEF": read(1),
            "AGI": read(1),
            "LCK": read(1),
            "unused": read(2),
            "abilities": [(read(2), read(2)) for i in range(16)],
            "weaknesses": [read(1) for i in range(3)],
            "unused": read(1),
        })

    f.seek(0x0C6684)  # elemental data
    elementdata = []
    for i in range(48):
        elementdata.append({
            "ID": i,
            "unused": read(4),
            "Venus_lvl": read(1),
            "Mercury_lvl": read(1),
            "Mars_lvl": read(1),
            "Jupiter_lvl": read(1),
            "Venus_Pow": read(2),
            "Venus_Res": read(2),
            "Mercury_Pow": read(2),
            "Mercury_Res": read(2),
            "Mars_Pow": read(2),
            "Mars_Res": read(2),
            "Jupiter_Pow": read(2),
            "Jupiter_Res": read(2),
        })
    
    f.seek(0x0C6BB0)  # djinn data
    djinndata = []
    for i in range(80):
        djinndata.append({
            "ID": i,
            "name": djinn[i],
            "element": elements[i//20],
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

    f.seek(0x0EDACC)  # encounter data
    encounterdata = []
    for i in range(110):
        encounterdata.append({
            "ID": i,
            "rate": read(2),
            "level": read(2),
            "enemy_groups": [read(2) for i in range(8)],
            "group_ratios": [read(1) for i in range(8)],
        })

    f.seek(0x0EE6D4)  # encounters by map
    map_encounters = []
    for i in range(325):
        map_encounters.append({
            "ID": i,
            "room": read(2),
            "door": read(2),
            "flag_id": read(2),
            "encounter_ids": [read(1), read(1)],
        })

    f.seek(0x0EEDBC)  # encounters on world map
    wmap_encounters = []
    for i in range(46):
        wmap_encounters.append({
            "ID": i,
            "area_type": read(2),
            "terrain": read(2),
            "flag_id": read(2),
            "encounter_ids": read(2),
        })

    room_references2 = []
    f.seek(0x0EF4A4)  # room references
    for i in range(110):
        room_references2.append({
            "ID": i,
            "room_or_area": read(2),
            "door": read(2),
            "name": areas2[read(2)],
            "unused": read(2),
        })

    f.seek(0x0F17A8)  # map data
    mapdata2 = []
    for i in range(325):
        mapdata2.append({
            "ID": i,
            "name": maps2[i],
            "file_index": read(2),
            "area": read(1),
            "type": read(1),
            "MFT_index": read(2),
            "outdoor": read(2),
        })

    f.seek(0x12CE7C)  # enemy group data
    enemygroupdata = []
    for i in range(660):
        enemygroupdata.append({
            "ID": i,
            "enemies": [enemynames[read(2)] for i in range(5)],
            "min_amounts": [read(1) for i in range(5)],
            "max_amounts": [read(1) for i in range(5)],
            "positioning": read(1),
            "unused": read(3),
        })

# Items
itemtypes = [
    "Other", "Weapon", "Armor", "Armgear", "Headgear", "Boots", "Psy-item", 
    "Trident", "Ring", "Shirt", "Class-item", "Elemental Star"]
flagdesc = ["Curses when equipped", "Can't be removed", "Rare item", "Important item",
        "Stackable", "Not transferable"]
usetypes = ["Multi-Use", "Consumable", "Can Break", "Bestows ability", "Item transforms when used"]
for item in itemdata:
    item.pop("unused")
    item["item_type"] = itemtypes[item["item_type"]]
    item["unleash_ability"] = abilitydata[item["unleash_ability"]]["name"]
    item["equipped_effects"] = {equipped_effects[e]: v for e,v,u in item["equipped_effects"] if e}
    item["equippable_by"] = [pcnames[i] for i in range(8) if item["equippable_by"] & 2**i]
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
    enemy["items"] = [items[i] for i in enemy["items"] if i]
    enemy["items"] = dict(zip(enemy["items"], enemy.pop("item_quantities")))
    if enemy["name"] in ("Dullahan", "Serpent"): enemy["HP_regen"] *= 10
    enemy["weaknesses"] = [ability_effects[i] for i in enemy["weaknesses"] if i]
    itemID = enemy["item_drop"]
    if itemID: itemdata[itemID]["dropped_by"].append(enemy["name"])
    enemy["item_drop"] = items[itemID]

# PCs
for pc in pcdata:
    pc.pop("unused")
    pc["starting_items"] = [items[i] for i in pc["starting_items"] if i]

# Summons
for summon in summondata:
    summon["hp_multiplier"] = sum(summon[k] for k in elements[0:4])*0.03
    if summon["name"] == "Daedalus":
        summon["hp_multiplier"] = 0.22
        summon["power"] = 350
    if summon["name"] == "Iris":
        summon["hp_multiplier"] = 0.40

# Classes
classgroups = [
    "", "Squire", "Guard", "Swordsman", "Brute",
    "Apprentice", "Water Seer", "Wind Seer", "Seer",
    "Pilgrim", "Hermit", "", "NPC", "Flame User",
    "Mariner", "Pierrot", "Tamer", "Dark Mage"]
for class_ in classdata:
    class_.pop("unused")
    class_["abilities"] = {abilities[k]: v for k,v in class_["abilities"] if k != 0}
    class_["class_group"] = classgroups[class_["class_group"]]
    class_["weaknesses"] = [ability_effects[i] for i in class_["weaknesses"] if i]
    for k in ["HP", "PP", "ATK", "DEF", "AGI", "LCK"]:
        class_[k] /= 10

# Element Presets
for entry in elementdata:
    entry.pop("unused")

# Djinn
for djinni in djinndata:
    djinni.pop("unused")
    move = abilitydata[djinni["ability"]]
    djinni["damage_type"] = move["damage_type"]
    djinni["effect"] = move["ability_effect"]
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


for name in [
        "djinndata", "enemydata", "itemdata", "abilitydata", "pcdata", "summondata",
        "classdata", "elementdata", "encounterdata", "mapdata1", "mapdata2",
        "room_references1", "room_references2", "enemygroupdata"
    ]:
    with open(f"data/{name}.json", "w") as f: json.dump(globals()[name], f, indent=4)
