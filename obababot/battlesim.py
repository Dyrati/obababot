from copy import deepcopy
from . import utilities
from .utilities import command, DataTables, UserData, Text, reply
from .gsfuncs import \
    PlayerData, EnemyData, battle_damage, statuschance, readsav, \
    rn_iter, ability_effects, equipped_effects


class AbilityHandler:

    def __init__(self, brn=None, grn=None):
        self.brn = brn if brn is not None else rn_iter(0)
        self.grn = grn if grn is not None else rn_iter(0)
        self.logs = []

    def execute(self, ability, user, target):
        center = target.position
        distance = ability["range"]
        lower, upper = center-distance+1, center+distance
        party = target.party
        self.logs.append(f"{user.name} uses {ability['name']}!")
        for i in range(max(0, lower), min(len(party), upper)):
            target = party[i]
            if "Downed" in target.perm_status: continue
            RANGE = abs(i-center) if distance != 255 else 0
            kwargs = dict(zip(("ability","user","target","RANGE"), (ability,user,target,RANGE)))
            self.hit(**kwargs)

    def bound(self, *args):
        for char in args:
            for stat in ("HP","PP"):
                current = char.stats[stat+"_cur"]
                statmax = char.stats[stat+"_max"]
                char.stats[stat+"_cur"] = int(max(0, min(statmax, current)))

    def hit(self, **kwargs):
        ability, user, target = kwargs["ability"], kwargs["user"], kwargs["target"]
        self.bound(user, target)
        effect = ability_effects[Text.get("ability_effects", ability["effect"])]
        bonus_effects = None
        if (100*next(self.brn)) >> 16 <= statuschance(**kwargs):
            bonus_effects = effect(ability=ability, user=user, target=target)
        if bonus_effects: kwargs.update(bonus_effects)
        damage_type = ability["damage_type"]
        if damage_type == "Healing":
            damage = battle_damage(**kwargs) + next(self.brn) & 3
            damage = min(target.stats["HP_max"]-target.stats["HP_cur"], max(1, damage))
            target.stats["HP_cur"] += damage
            self.logs.append(f"{target.name} recovered {damage} HP!")
        elif damage_type in ("Utility", "Effect Only", "Psynergy Drain", "Psynergy Recovery"):
            pass
        else:
            MULT = kwargs.get("MULT")
            if isinstance(MULT, list): kwargs["MULT"] = MULT[len(MULT)*next(self.brn) >> 16]
            HP_SAP, PP_SAP = kwargs.pop("HP_SAP",0), kwargs.pop("PP_SAP",0)
            SELFDESTRUCT = kwargs.pop("SELFDESTRUCT",0)
            damage = battle_damage(**kwargs)
            damage = max(1, int(damage*target.damage_mult) + (next(self.brn) & 3))
            prev, damage = damage, min(target.stats["HP_cur"], damage)
            target.stats["HP_cur"] -= damage
            if HP_SAP: user.stats["HP_cur"] += int(damage*HP_SAP)
            if PP_SAP: user.stats["PP_cur"] += int(damage*PP_SAP)
            self.logs.append(f"{target.name} took {prev} damage!")
        self.bound(user, target)
        for char in (user, target):
            statuses = char.perm_status
            if char.stats["HP_cur"] == 0 and "Downed" not in statuses:
                self.logs.append(f"{char.name} was downed")
                # char.stats["HP_cur"] = char.stats["HP_max"]
                statuses.add("Downed")
            elif char.stats["HP_cur"] > 0 and "Downed" in statuses:
                self.logs.append(f"{char.name} was revived!")
                statuses.discard("Downed")


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
        p.perm_status = set(p.perm_status)
        p.damage_mult = 1
        p.type = "human"
        p.position = i % 4
        p.party = front
    enemies = [EnemyData(DataTables.get("enemydata", name.strip('"'))) for name in args]
    for i,e in enumerate(enemies):
        e.perm_status = set(e.perm_status)
        e.damage_mult = 1
        e.type = "enemy"
        e.position = i
        e.party = enemies
    cursor = 0
    side = 0
    inputs = []
    brn = rn_iter(int(kwargs.get("brn", 0)))
    grn = rn_iter(int(kwargs.get("grn", 0)))
    AbilityHandle = AbilityHandler(brn=brn, grn=grn)
    mode = "battle"

    async def main(before, after):
        if after.author != author: return
        if after.content == "$quit" or mode == "end":
            await utilities.kill_message(before)
        elif mode == "battle":
            prefix = utilities.prefix
            for line in after.content.split("\n"):
                if not line.startswith(prefix): continue
                content = line[len(prefix):]
                args, kwargs = utilities.parse(content)
                move_select(*args, **kwargs)
                await before.edit(content=f"```\n{display()}\n```")

    def display():
        nonlocal front, enemies
        out = utilities.Charmap()
        x,y1 = out.addtext("\n".join((p.name for p in front)), (2,0))
        x,y1 = out.addtext("\n".join((str(p.stats['HP_cur']) for p in front)), (x+1,0))
        if cursor is not None:
            if side == 0: out.addtext("►", (0, cursor))
            elif side == 1: out.addtext("►", (x+3, cursor))
        x,y2 = out.addtext("\n".join((e.name for e in enemies)), (x+5,0))
        x,y2 = out.addtext("\n".join((str(e.stats['HP_cur']) for e in enemies)), (x+1,0))
        if AbilityHandle.logs:
            out.addtext("\n".join(AbilityHandle.logs), (2, max(y1,y2)+1))
            AbilityHandle.logs.clear()
        return out

    def live_party(party):
        return [i for i,p in enumerate(party) if "Downed" not in p.perm_status]

    def assigncursor(value):
        nonlocal cursor, front
        if value is None: cursor = None; return
        lp = live_party(front)
        for i in lp:
            if i >= value: cursor = i; break
        else:
            cursor = lp[0] if lp else 0
            return True

    def move_select(*args, **kwargs):
        nonlocal mode, front, back
        for user in party + enemies:
            if user.stats["HP_cur"] <= 0: user.perm_status.add("Downed")
            elif user.stats["HP_cur"] > 0 : user.perm_status.discard("Downed")
        ability = DataTables.get("abilitydata", args[0].strip('"'))
        pc = front[cursor]
        if ability["range"] == 255: center = 0
        elif ability["target"] == "Self": center = pc.position
        else:
            if len(args) < 2:
                lp = live_party(enemies)
                center = lp[(len(lp)-1)//2]
            else: center = int(args[1])
        target_party = enemies if ability["target"] == "Enemies" else party
        AGI = (pc.stats["AGI"]*next(grn) >> 20) + pc.stats["AGI"]
        if ability["name"] == "Defend": AGI += 20000
        inputs.append({
            "ability": ability,
            "user": pc,
            "target": target_party[center],
            "target_party": target_party,
            "AGI": AGI})
        check = assigncursor(cursor+1)
        if check:
            for enemy in enemies: inputs.extend(enemymoves(enemy))
            result = battle_turn()
            assigncursor(0)
            if result is not None:
                if result==1 and back and any(["Downed" not in pc.perm_status for pc in back]):
                    front, back = back, front
                else:
                    AbilityHandle.logs.append(f"Party {result} wins!")
                    mode = "end"; assigncursor(None)

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
            target_party = front if ability["target"] == "Enemies" else enemies
            AGI = enemy.stats["AGI"]*(1 - turn/(2*enemy.stats["turns"]))
            if ability["name"] == "Defend": AGI += 20000
            inputs.append({
                "ability": ability,
                "user": enemy,
                "target_party": target_party,
                "AGI": AGI})
        return einputs

    def battle_turn():
        nonlocal front, back, mode
        AbilityHandle.logs.clear()
        for move in sorted(inputs, key=lambda x: -x["AGI"]):
            if "Downed" in move["user"].perm_status: continue
            ability = move["ability"]
            if move["user"].type == "enemy":
                lp = live_party(move["target_party"])
                center = lp[len(lp)*next(grn) >> 16]
                move["target"] = move["target_party"][center]
            AbilityHandle.execute(ability, move["user"], move["target"])
            if not live_party(enemies):
                AbilityHandle.logs.append("Player wins!")
                mode = "end"
                break
            if not live_party(front):
                if live_party(back):
                    front, back = back, front
                else:
                    AbilityHandle.logs.append("Player party was defeated")
                    mode = "end"
                break
            
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
        inputs.clear()

    sent = await reply(message, f"```\n{display()}\n```")
    await utilities.live_message(sent, main)