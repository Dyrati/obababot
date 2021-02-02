from copy import deepcopy
from . import utilities
from .utilities import command, reply, DataTables, UserData, Text, Emojis
from .gsfuncs import \
    PlayerData, EnemyData, battle_damage, statuschance, readsav, \
    rn_iter, ability_effects, equipped_effects


def bound(*args):
    for char in args:
        for stat in ("HP","PP"):
            current = char.stats[stat+"_cur"]
            statmax = char.stats[stat+"_max"]
            char.stats[stat+"_cur"] = int(max(0, min(statmax, current)))

def live_party(party):
    return [i for i,p in enumerate(party) if p.stats["HP_cur"] > 0]

def execute_ability(ability, user, target, brn=None, grn=None, logs=None):
    center = target.position
    distance = ability["range"]
    lower, upper = center-distance+1, center+distance
    party = target.party
    if ability["name"] == "Defend": logs.append(f"{user.name} is defending")
    else: logs.append(f"{user.name} uses {ability['name']}!")
    for i in range(max(0, lower), min(len(party), upper)):
        target = party[i]
        if target.stats["HP_cur"] <= 0: continue
        RANGE = abs(i-center) if distance != 255 else 0
        bound(user, target)
        effect = ability_effects[Text.get("ability_effects", ability["effect"])]
        bonus_effects = {}
        if ability["name"] == "Defend": pass
        elif (100*next(brn)) >> 16 <= statuschance(ability, user, target, RANGE):
            bonus_effects = effect(ability=ability, user=user, target=target) or {}
        damage_type = ability["damage_type"]
        if damage_type == "Healing":
            damage = battle_damage(ability, user, target, RANGE=RANGE, **bonus_effects) + next(brn) & 3
            damage = min(target.stats["HP_max"]-target.stats["HP_cur"], max(1, damage))
            target.stats["HP_cur"] += damage
            logs.append(f"{target.name} recovered {damage} HP!")
        elif damage_type in ("Utility", "Effect Only", "Psynergy Drain", "Psynergy Recovery"):
            pass
        else:
            MULT = bonus_effects.get("MULT")
            if isinstance(MULT, list): bonus_effects["MULT"] = MULT[len(MULT)*next(brn) >> 16]
            HP_SAP, PP_SAP = bonus_effects.pop("HP_SAP",0), bonus_effects.pop("PP_SAP",0)
            SELFDESTRUCT = bonus_effects.pop("SELFDESTRUCT",0)
            damage = battle_damage(ability, user, target, RANGE=RANGE, **bonus_effects)
            if target.defending: damage >>= 1
            damage = max(1, int(damage*target.damage_mult) + (next(brn) & 3))
            prev, damage = damage, min(target.stats["HP_cur"], damage)
            target.stats["HP_cur"] -= damage
            if HP_SAP: user.stats["HP_cur"] += int(damage*HP_SAP)
            if PP_SAP: user.stats["PP_cur"] += int(damage*PP_SAP)
            logs.append(f"{target.name} took {prev} damage!")
        if user.status["poison"] or user.status["venom"]:
            damage = user.stats["HP_max"]//(10 if user.status["poison"] else 5)
            user.stats["HP_cur"] -= user.stats["HP_max"]//10
            logs.append(f"{user.name} took {user.stats['HP_max']//10} poison damage")
        bound(user, target)
        for char in (user, target):
            if char.stats["HP_cur"] == 0:
                logs.append(f"{char.name} was downed")


def execute_turn(inputs, party, enemies, brn=None, grn=None, logs=None):
    for move in sorted(inputs, key=lambda x: -x["AGI"]):
        if move["user"].stats["HP_cur"] <= 0 or move["user"].status["stun"]:
            continue
        ability = move["ability"]
        if move["user"].type == "enemy":
            lp = live_party(move["target_party"])
            center = lp[len(lp)*next(grn) >> 16]
            move["target"] = move["target_party"][center]
        execute_ability(ability, move["user"], move["target"], brn=brn, grn=grn, logs=logs)
        if not live_party(enemies): return 1
        if not live_party(party[:4]):
            if live_party(party[4:]): party = party[4:] + party[:4]
            else: return 2
    for char in party + enemies:
        for status in ("attack_buff","defense_buff","resist_buff","agility_buff"):
            turns, amt = char.status[status]
            if turns > 0: char.status[status][0] -= 1
            if turns == 1: char.status[status][1] = 0
        for status in (
                "delusion","confusion","charm","stun","sleep","psy_seal","hp_regen",
                "reflect","death_curse","counterstrike","kite","immobilize"):
            turns = char.status[status]
            if turns > 0: char.status[status] -= 1
        char.damage_mult = 1
        char.defending = 0
    inputs.clear()


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

@command
async def battle(message, *args, **kwargs):
    user = UserData[message.author.id]
    author = message.author
    assert user.party, "Please load a party using the $loadparty command"
    party = deepcopy(user.party)
    front, back = party[:4], party[4:]
    for i,p in enumerate(party):
        p.type = "human"
        p.position = i % 4
        p.party = party
        p.damage_mult = 1
        p.sprite = Emojis[("venus","mercury","mars","jupiter")[i%4] + "battle3"]
    enemies = [EnemyData(DataTables.get("enemydata", name.strip('"'))) for name in args]
    for i,e in enumerate(enemies):
        e.type = "enemy"
        e.position = i
        e.party = enemies
        e.damage_mult = 1
        e.sprite = Emojis["venusbattle2"]
    cursor = 0
    side = 0
    inputs = []
    logs = []
    brn = rn_iter(int(kwargs.get("brn", 0)))
    grn = rn_iter(int(kwargs.get("grn", 0)))
    mode = "move_select"

    def display():
        enemy_hp = "** **" + " "*2 \
                 + "     ".join((f"`{e.stats['HP_cur']}`" for e in enemies))
        sprites = "\n".join((e.sprite for e in enemies)) + "\n" + " "*10 \
                + "".join((p.sprite for p in party[:4]))
        party_hp = "** **" + " "*10 \
                 + "      ".join((f"`{p.stats['HP_cur']}`" for p in party[:4]))
        pc = party[:4][cursor]
        hud = utilities.Charmap()
        if mode == "move_select":
            x,y = -3,0
            abilities = list(pc.abilities)
            for i in range(0, len(abilities), 8):
                x,y = hud.addtext("\n".join(abilities[i:i+8]), (x+3, y))
        elif logs:
            hud.addtext("\n".join(logs), (2, 0))
            logs.clear()
        hud = f"```\n{hud}\n```"
        return enemy_hp, sprites, party_hp, hud

    enemy_hp, sprites, player_hp, hud = [await reply(message, s) for s in display()]

    async def main(message):
        nonlocal mode
        if message.author != author: return
        if message.content == "$quit" or mode == "end":
            utilities.register_remove(message.channel)
        elif mode == "move_select":
            prefix = utilities.prefix
            for line in message.content.split("\n"):
                if not line.startswith(prefix): continue
                content = line[len(prefix):]
                args, kwargs = utilities.parse(content)
                mode = move_select(*args, **kwargs)
            if mode == "battle":
                for enemy in enemies: inputs.extend(enemymoves(enemy))
                result = execute_turn(inputs, party, enemies, brn=brn, grn=grn, logs=logs)
                if result == 1: logs.append(f"Player party wins!"); mode = "end"
                elif result == 2: logs.append(f"Player was defeated"); mode = "end"
                else: mode = "move_select"
            for sent, s in zip((enemy_hp, sprites, player_hp, hud), display()):
                await sent.edit(content=s)

    def assigncursor(value):
        nonlocal cursor, party
        if value is None: cursor = None; return
        lp = live_party(party[:4])
        for i in lp:
            if i >= value: cursor = i; break
        else:
            cursor = lp[0] if lp else 0
            return True

    def move_select(*args, **kwargs):
        nonlocal mode, party, enemies
        ability = DataTables.get("abilitydata", args[0].strip('"'))
        pc = party[:4][cursor]
        if ability["range"] == 255: center = 0
        elif ability["target"] == "Self": center = pc.position
        else:
            if len(args) < 2:
                lp = live_party(enemies)
                center = lp[(len(lp)-1)//2]
            else: center = int(args[1])
        target_party = enemies if ability["target"] == "Enemies" else party[:4]
        AGI = (pc.stats["AGI"]*next(grn) >> 20) + pc.stats["AGI"]
        if ability["name"] == "Defend": pc.defending = 1
        inputs.append({
            "ability": ability,
            "user": pc,
            "target": target_party[center],
            "target_party": target_party,
            "AGI": AGI})
        check = assigncursor(cursor+1)
        if check: return "battle"
        else: return "move_select"

    def enemymoves(enemy):
        einputs = []
        attack_patterns = (
            [32, 32, 32, 32, 32, 32, 32, 32],
            [53, 47, 41, 35, 29, 23, 17, 11],
            [113, 56, 31, 20, 14, 10, 7, 5],
            [32, 32, 32, 32, 32, 32, 32, 32])
        defend = False
        for turn in range(enemy.stats["turns"]):
            pattern = attack_patterns[enemy.attack_pattern]
            dice_roll = next(brn) & 255
            for i,v in enumerate(pattern):
                dice_roll -= v
                if dice_roll < 0: break
            ability = DataTables.get("abilitydata", enemy.abilities[i])
            target_party = party[:4] if ability["target"] == "Enemies" else enemies
            AGI = enemy.stats["AGI"]*(1 - turn/(2*enemy.stats["turns"]))
            if ability["name"] == "Defend": enemy.defending = 1
            inputs.append({
                "ability": ability,
                "user": enemy,
                "target_party": target_party,
                "AGI": AGI})
        return einputs

    utilities.register_on_message(message.channel, main)