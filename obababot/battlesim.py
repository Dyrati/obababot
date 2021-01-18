from copy import deepcopy
from . import utilities
from .utilities import command, DataTables, UserData, Text, reply
from .gsfuncs import battle_damage, readsav, rn_iter
from .safe_eval import safe_eval


def enemyparty(enemygroup, grn=0):
    grn = rn_iter(grn)
    enemies, mins, maxs = (enemygroup[attr] for attr in ["enemies", "min_amounts", "max_amounts"])
    quantities = [mn + ((mx-mn+1)*grn() >> 16) if mx > mn else mn for mn,mx in zip(mins, maxs)]
    def swap(array, pos1, pos2):
        temp = array[pos2]
        array[pos2] = array[pos1]
        array[pos1] = temp
    order = [0,1,2,3,4]
    for i in range(10):
        swap(order, 5*next(grn) >> 16, 5*next(grn) >> 16)
    order = [v for v in order if v < len(enemies)]
    party = []
    for pos in order:
        party.extend([enemies[pos]]*quantities[pos])
    party = [deepcopy(DataTables.get("enemydata", n)) for n in party]
    for e in party:
        e["HP_max"] = e["HP_cur"] = e.pop("HP")
        e["PP_cur"] = e["PP"]
        e["status"] = []
    return party

multipliers = [0x41c64e6d]
increments = [0x00003039]
for i in range(31):
    multipliers.append((multipliers[i]**2) & 0xFFFFFFFF)
    increments.append((multipliers[i]*increments[i]+increments[i]) & 0xFFFFFFFF)


@command
async def loadparty(message, *args, **kwargs):
    user = UserData[message.author.id]
    assert user.filedata, "use $upload to upload a save file"
    slots = {f["slot"]:f for f in user.filedata}
    if not args: slot = next(iter(slots))
    else: slot = int(args[0])
    assert slot in slots, "Slot not found"
    user.party = slots[slot]["party"]
    await reply(message, f"Loaded party from slot {slot}")

def abilityfunc(ability, party1, party2):
    def healing(**kwargs):
        damage = ability["power"]
        if ability["element"] != "Neutral":
            damage *= kwargs["POW"]/100
        return damage
    def additive(**kwargs):
        damage = (kwargs["ATK"]-kwargs["DEF"])/2 + ability["power"]
        if ability["element"] != "Neutral":
            damage *= int_256(1 + (POW-RES)/400)
        return damage
    def multiplier(**kwargs):
        damage = (kwargs["ATK"]-kwargs["DEF"])/2*ability["power"]/10
        if ability["element"] != "Neutral":
            damage *= int_256(1 + (kwargs["POW"]-kwargs["RES"])/400)
        return damage
    def basedmg(**kwargs):
        damage = ability["power"]*int_256(1 + (kwargs["POW"]-kwargs["RES"])/200)
        if kwargs["RANGE"]: damage *= [1, .8, .6, .4, .2, .1][kwargs["RANGE"]]
        return damage
    def basedmgdim(**kwargs):
        damage = ability["power"]*int_256(1 + (kwargs["POW"]-kwargs["RES"])/200)
        if kwargs["RANGE"]: damage *= [1, .5, .3, .1, .1, .1][kwargs["RANGE"]]
        return damage
    def summon(**kwargs):
        ability = DataTables.get("summondata", ability["name"])
        damage = ability["power"] + int(ability["hp_multiplier"]*min(10000, HP))
        damage *= int_256(1 + (kwargs["POW"]-kwargs["RES"])/200)
        if kwargs["RANGE"]: damage *= [1, .7, .4, .3, .2, .1][kwargs["RANGE"]]
        return damage
    def decorator(f):
        def inner(attacker, defender, brn=None):
            if brn == None: brn = rn_iter(0)
            POS = defender["position"]
            lower, upper = max(0, POS-RANGE), min(len(party2), POS+RANGE+1)
            out = []
            epos = Text["elements"].index(ability["element"])
            for i in range(lower, upper):
                defender = defender_party[i]
                kwargs = {
                    "ATK": attacker["ATK"],
                    "POW": attacker["epow"][epos] if epos < 5 else None,
                    "DEF": defender["DEF"],
                    "RES": defender["eres"][epos] if epos < 5 else None,
                    "HP": defender["HP_max"],
                    "RANGE": abs(i-POS)}
                damage = f(**kwargs)
                out.append((defender, damage))
            return out
        return inner
    damagetypes = {
        "Healing": healing,
        "Added Damage": additive,
        "Multiplier": multiplier,
        "Base Damage": basedmg,
        "Base Damage (Diminishing)": basedmgdim,
        "Summon": summon}
    return decorator(damagetypes[ability["damage_type"]])


@command
async def battle(message, *args, **kwargs):
    user = UserData[message.author.id]
    author = message.author
    assert user.party, "Please load a party using the $loadparty command"
    party = deepcopy(user.party)
    party = [{
        **p.pop("stats"), **p,
        "defending":False,
        "type":"human",
        "status":p.pop("perm_status"),
        } for p in party]
    front, back = party[:4], party[4:]
    enemies = [deepcopy(DataTables.get("enemydata", name.strip('"'))) for name in args]
    for e in enemies:
        e["HP_max"] = e["HP_cur"] = e.pop("HP")
        e["PP_cur"] = e["PP"]
        e["defending"] = False
        e["status"] = []
        e["type"] = "enemy"
    # abilityfunclist = []
    # for ability in DataTables["abilitydata"]:
    #     abilityfunclist.append(abilityfunc(ability, party, enemies))
    cursor = 0
    side = 0
    inputs = []
    brn = rn_iter(int(kwargs.get("brn", 0)))
    grn = rn_iter(int(kwargs.get("grn", 0)))
    battle_log = []
    mode = "battle"

    async def main(before, after):
        if after.author != author: return
        if after.content == "$quit" or mode == "end":
            await utilities.kill_message(before)
        elif mode == "battle":
            prefix = utilities.prefix + "ability "
            for line in after.content.split("\n"):
                if not line.startswith(prefix): continue
                content = line[len(prefix):]
                args, kwargs = utilities.parse(content)
                move_select(*args, **kwargs)
                await before.edit(content=f"```\n{display()}\n```")

    def display():
        nonlocal front, enemies
        out = utilities.Charmap()
        x,y1 = out.addtext("\n".join((p['name'] for p in front)), (2,0))
        x,y1 = out.addtext("\n".join((str(p['HP_cur']) for p in front)), (x+1,0))
        if cursor is not None:
            if side == 0: out.addtext("►", (0, cursor))
            elif side == 1: out.addtext("►", (x+3, cursor))
        x,y2 = out.addtext("\n".join((e['name'] for e in enemies)), (x+5,0))
        x,y2 = out.addtext("\n".join((str(e['HP_cur']) for e in enemies)), (x+1,0))
        if battle_log:
            out.addtext("\n".join(battle_log), (2, max(y1,y2)+1))
            battle_log.clear()
        return out

    def assigncursor(value):
        nonlocal cursor
        if value is None: cursor = None; return
        live_party = [i for i,p in enumerate(front) if "Downed" not in p["status"]]
        for i in live_party:
            if i >= value: cursor = i; break
        else:
            cursor = live_party[0] if live_party else 0
            return True

    def move_select(*args, **kwargs):
        nonlocal mode, front, back
        ability = DataTables.get("abilitydata", args[0].strip('"'))
        pc = front[cursor]
        if ability["range"] == 255 or ability["target"] == "Self": center = 0
        else: center = int(args[1])
        inputs.append({
            "ability": ability,
            "user": pc,
            "AGI": (pc["AGI"]*next(grn) >> 20) + pc["AGI"],
            "center": center})
        pc["defending"] = ability["name"] == "Defend"
        check = assigncursor(cursor+1)
        if check:
            einputs = []
            for enemy in enemies:
                einputs.extend(enemymoves(enemy))
            result = battle_turn(front, enemies, inputs, einputs)
            assigncursor(0)
            if result is not None:
                if result==1 and back and any(["Downed" not in pc["status"] for pc in back]):
                    front, back = back, front
                else:
                    battle_log.append(f"Party {result} wins!")
                    mode = "end"; assigncursor(None)

    def enemymoves(enemy):
        einputs = []
        attack_patterns = (
            [32, 32, 32, 32, 32, 32, 32, 32],
            [11, 17, 23, 29, 35, 41, 47, 53],
            [5, 7, 10, 14, 20, 31, 56, 113],
            [32, 32, 32, 32, 32, 32, 32, 32])
        defend = False
        for turn in range(enemy["turns"]):
            pattern = attack_patterns[enemy["attack_pattern"]]
            dice_roll = next(brn) & 255
            for i,v in enumerate(pattern):
                dice_roll -= v
                if dice_roll < 0: break
            ability = DataTables.get("abilitydata", enemy["abilities"][i])
            AGI = enemy["AGI"]*(1 - turn/(2*enemy["turns"]))
            einputs.append({
                "ability": ability,
                "user": enemy,
                "AGI": AGI})
            if ability["name"] == "Defend": defend = True
        enemy["defending"] = defend
        return einputs

    def battle_turn(party1, party2, moves1, moves2):
        moves = [(m, 0) for m in moves1] + [(m, 1) for m in moves2]
        for move, pnum in sorted(moves, key=lambda x: -x[0]["AGI"]):
            if "Downed" in move["user"]["status"]: continue
            ability = move["ability"]
            battle_log.append(f"{move['user']['name']} uses {ability['name']}!")
            if move["user"]["type"] == "enemy":
                live_party = [i for i,p in enumerate(front) if "Downed" not in p["status"]]
                center = live_party[len(live_party)*next(grn) >> 16]
            else: center = move["center"]
            distance = ability["range"] - 1
            lower, upper = center-distance, center+distance+1
            for i in range(lower, upper):
                if ability["target"] == "Enemies": party = (party1, party2)[not pnum]
                else: party = (party1, party2)[pnum]
                if i >= len(party) or i < 0: continue
                if "Downed" in party[i]["status"]: continue
                RANGE = abs(i-center)
                dealt = battle_damage(ability, user=move.get("user"), target=party[i], RANGE=RANGE)
                damage_type = ability["damage_type"]
                if damage_type not in [
                        "Healing","Added Damage","Multiplier","Base Damage",
                        "Base Damage (Diminishing)","Summon"]:
                    continue
                dealt += next(brn) & 3
                if party[i]["defending"]: dealt >>= 1
                dealt = max(1, dealt)
                if ability["damage_type"] == "Healing":
                    dealt = min(party[i]["HP_max"] - party[i]["HP_cur"], dealt)
                    party[i]["HP_cur"] += dealt
                    battle_log.append(f"{party[i]['name']} recovered {dealt} HP!")
                else:
                    party[i]["HP_cur"] = max(0, party[i]["HP_cur"] - dealt)
                    battle_log.append(f"{party[i]['name']} took {dealt} damage!")
                if party[i]["HP_cur"] <= 0:
                    party[i]["status"].insert(0, "Downed")
                    battle_log.append(f"{party[i]['name']} was downed")
                    if all(["Downed" in p["status"] for p in party]): return pnum
        moves1.clear(); moves2.clear()

    sent = await reply(message, f"```\n{display()}\n```")
    await utilities.live_message(sent, main)