from copy import deepcopy
from . import utilities
from .utilities import command, DataTables, UserData, Text, reply
from .gsfuncs import battle_damage, readsav, get_character_info, rn_iter

base_chances = [
    60,60,100,100,70,70,100,100,75,75,55,55,65,35,30,40,45,55,
    25,20,60,100,100,65,60,100,35,50,100,100,100,100,100,100,100,
    100,100,100,100,100,100,100,100,100,100,100,100,100,60,90]

class AbilityHandler:

    def __init__(self, brn=None, grn=None):
        self.brn = brn if brn is not None else rn_iter(0)
        self.grn = grn if grn is not None else rn_iter(0)
        self.logs = []
        self.effect_map = {v:k for k,v in enumerate(Text["ability_effects"])}
    
    def statuscheck(self, RANGE=0):
        effect_index = self.effect_map[self.ability["effect"]]
        if effect_index >= len(base_chances):
            base_chance = 100
        else:
            base_chance = base_chances[effect_index-8]
        if base_chance == 100: return True
        epos = Text["elements"].index(self.ability["element"])
        if epos < 4:
            elvldiff = self.user["elevels"][epos] - self.target["elevels"][epos]
        else: elvldiff = 0
        vulnerable = 25 if self.ability["effect"] in self.target["weaknesses"] else 0
        chance = base_chance + 3*(elvldiff - self.target["LCK"]//2) + vulnerable
        chance = int([1, .6, .3, .3, .3, .3][RANGE]*chance)
        return 100*next(self.brn) >> 16 <= chance

    def execute(self, ability, user, target):
        self.ability, self.user, self.target = ability, user, target
        center = target["position"]
        distance = ability["range"]
        lower, upper = center-distance+1, center+distance
        party = target["party"]
        self.logs.append(f"{user['name']} uses {ability['name']}!")
        for i in range(max(0, lower), min(len(party), upper)):
            target = party[i]
            if "Downed" in target["perm_status"]: continue
            effect_index = self.effect_map[ability["effect"]]
            RANGE = abs(i-center) if distance != 255 else 0
            effect = getattr(self, f"effect{effect_index}")
            kwargs = effect() if self.statuscheck(RANGE=RANGE) else None
            if kwargs == None: kwargs = {}
            self.hit(**kwargs, RANGE=RANGE)

    def battle_damage(
            self, ATK=None, POW=None, HP=None, 
            DEF=None, RES=None, RANGE=0, MULT=None):
        ability, user, target = self.ability, self.user, self.target
        epos = Text["elements"].index(ability["element"])
        if ATK is None: ATK = user["ATK"]
        if POW is None: POW = user["epow"][epos] if epos < 4 else 0
        if HP is None: HP = target.get("HP", target.get("HP_max"))
        if DEF is None: DEF = target["DEF"]
        if RES is None: RES = target["eres"][epos] if epos < 4 else 0
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
            ability = DataTables.get("summondata", ability["name"])
            damage = ability["power"] + int(ability["hp_multiplier"]*min(10000, HP))
            damage *= int_256(1 + (POW-RES)/200)
            if RANGE: damage *= [1, .7, .4, .3, .2, .1][RANGE]
        else: damage = 0
        return max(0, int(damage))

    def bound(self):
        for char in (self.user, self.target):
            for stat in ("HP","PP"):
                current, statmax = self.target[stat + "_cur"], self.target[stat + "_max"]
                self.target[stat+"_cur"] = int(max(0, min(statmax, current)))

    def hit(self, **kwargs):
        self.bound()
        uname, tname, aname = self.user["name"], self.target["name"], self.ability["name"]
        damage_type = self.ability["damage_type"]
        if damage_type == "Healing":
            damage = self.battle_damage(**kwargs) + (next(self.brn) & 3)
            damage = min(self.target["HP_max"]-self.target["HP_cur"], max(1, damage))
            self.target["HP_cur"] += damage
            self.logs.append(f"{tname} recovered {damage} HP!")
        elif damage_type in ("Utility", "Effect Only", "Psynergy Drain", "Psynergy Recovery"):
            pass
        else:
            MULT = kwargs.get("MULT")
            if isinstance(MULT, list): kwargs["MULT"] = MULT[len(MULT)*next(self.brn) >> 16]
            HP_SAP, PP_SAP = kwargs.pop("HP_SAP",0), kwargs.pop("PP_SAP",0)
            damage = self.battle_damage(**kwargs)
            damage = max(1, int(damage*self.target["damage_mult"]) + (next(self.brn) & 3))
            prev, damage = damage, min(self.target["HP_cur"], damage)
            self.target["HP_cur"] -= damage
            self.user["HP_cur"] += int(damage*HP_SAP)
            self.user["PP_cur"] += int(damage*PP_SAP)
            self.logs.append(f"{tname} took {prev} damage!")
        self.bound()
        for char in (self.user, self.target):
            statuses = char["perm_status"]
            if char["HP_cur"] == 0 and "Downed" not in statuses:
                self.logs.append(f"{char['name']} was downed")
                statuses.add("Downed")
            elif char["HP_cur"] > 0 and "Downed" in statuses:
                self.logs.append(f"{char['name']} was revived!")
                statuses.discard("Downed")

    def effect0(self): pass
    def effect1(self): pass
    def effect2(self): pass
    def effect3(self):
        for status in ("poison", "venom"):
            self.target["perm_status"].discard(status)
            self.target["status"][status] = 0
    def effect4(self):
        for status in ("stun", "sleep", "delusion", "curse"):
            self.target["status"][status] = 0
    def effect5(self): self.target["HP_cur"] = self.target["HP_max"]
    def effect6(self): self.target["status"]["attack_buff"][:] = [7,2]
    def effect7(self): self.target["status"]["attack_buff"][:] = [7,1]
    def effect8(self): self.target["status"]["attack_buff"][:] = [7,-2]
    def effect9(self): self.target["status"]["attack_buff"][:] = [7,-1]
    def effect10(self): self.target["status"]["defense_buff"][:] = [7,2]
    def effect11(self): self.target["status"]["defense_buff"][:] = [7,1]
    def effect12(self): self.target["status"]["defense_buff"][:] = [7,-2]
    def effect13(self): self.target["status"]["defense_buff"][:] = [7,-1]
    def effect14(self): self.target["status"]["resist_buff"][:] = [7,2]
    def effect15(self): self.target["status"]["resist_buff"][:] = [7,1]
    def effect16(self): self.target["status"]["resist_buff"][:] = [7,-2]
    def effect17(self): self.target["status"]["resist_buff"][:] = [7,-1]
    def effect18(self): self.target["status"]["poison"] = 1
    def effect19(self): self.target["status"]["venom"] = 1
    def effect20(self): self.target["status"]["delusion"] = 7
    def effect21(self): self.target["status"]["confusion"] = 7
    def effect22(self): self.target["status"]["charm"] = 7
    def effect23(self): self.target["status"]["stun"] = 7
    def effect24(self): self.target["status"]["sleep"] = 7
    def effect25(self): self.target["status"]["seal"] = 7
    def effect26(self): self.target["status"]["haunt"] = 7
    def effect27(self): self.target["HP_cur"] = 0
    def effect28(self): self.target["status"]["death_curse"] = 7
    def effect29(self): pass
    def effect30(self): pass
    def effect31(self):
        self.user["HP_cur"] += ability["power"]
        self.target["HP_cur"] -= ability["power"]
    def effect32(self):
        self.user["PP_cur"] += ability["power"]
        self.target["PP_cur"] -= ability["power"]
    def effect33(self):
        for effect in ("summon_boosts", "attack_buff", "defense_buff", "resist_buff", "agility_buff"):
            if self.target["status"][effect][1] > 0:
                self.target["status"][effect][:] = [0, 0]
    def effect34(self): self.target["HP_cur"] = 1
    def effect35(self): return {"DEF": self.target["DEF"]//2}
    def effect36(self): pass
    def effect37(self): pass
    def effect38(self): pass
    def effect39(self): pass
    def effect40(self): pass
    def effect41(self): pass
    def effect42(self): return {"MULT": 2}
    def effect43(self): pass
    def effect44(self): return {"MULT": 3}
    def effect45(self): pass
    def effect46(self): self.target["damage_mult"] *= 0.5
    def effect47(self): self.target["damage_mult"] *= 0.1
    def effect48(self): pass
    def effect49(self): pass
    def effect50(self): pass
    def effect51(self): pass
    def effect52(self): pass
    def effect53(self): self.target["status"]["immobilize"] = 1
    def effect54(self): pass
    def effect55(self): self.user["HP_cur"] = 0
    def effect56(self): self.target["HP_cur"] = 0.5*self.target["HP_max"]
    def effect57(self): self.target["HP_cur"] = 0.8*self.target["HP_max"]
    def effect58(self): self.target["status"]["agility_buff"][:] = [5,-4]
    def effect59(self): self.target["status"]["agility_buff"][:] = [5,8]
    def effect60(self): return {"HP_SAP": 0.5}
    def effect61(self): self.target["HP_cur"] += 0.6*self.target["HP_max"]
    def effect62(self): self.target["HP_cur"] += 0.3*self.target["HP_max"]
    def effect63(self): self.target["PP_cur"] += 0.7*self.target["PP_max"]
    def effect64(self):
        for effect in ("summon_boosts", "attack_buff", "defense_buff", "resist_buff", "agility_buff"):
            if self.target["status"][effect][1] < 0:
                self.target["status"][effect][:] = [0, 0]
        statuses = [
            "poison","venom","delusion","confusion","charm","stun","sleep",
            "psy_seal","haunt","death_curse","immobilize"]
        for effect in statuses:
            self.target["status"][effect] = 0
    def effect65(self): return {"MULT": 2}
    def effect66(self): self.target["status"]["kite"] = 1
    def effect67(self): self.target["status"]["seal"] = 7
    def effect68(self): return {"MULT": 3}
    def effect69(self): return {"PP_SAP": 0.1}
    def effect70(self): self.target["HP_cur"] += 0.5*self.target["HP_max"]
    def effect71(self): self.target["HP_cur"] += 0.7*self.target["HP_max"]
    def effect72(self): self.target["damage_mult"] *= 0.4
    def effect73(self): self.target["HP_cur"] = 0.6*self.target["HP_max"]
    def effect74(self): self.target["status"]["reflux"] = 1
    def effect75(self): self.target["status"]["delusion"] = 7
    def effect76(self): self.target["HP_cur"] += 0.4*self.target["HP_max"]
    def effect77(self): self.target["HP_cur"] += 0.1*self.target["HP_max"]
    def effect78(self): self.target["HP_cur"] += 0.3*self.target["HP_max"]
    def effect79(self): self.target["status"]["haze"] = 1
    def effect80(self): self.target["status"]["death_curse"] = 1
    def effect81(self): pass
    def effect82(self): pass
    def effect83(self): self.target["immobilize"] = 1
    def effect84(self): self.target["PP_cur"] *= 0.9
    def effect85(self): self.target["status"]["stun"] = 7
    def effect86(self): pass
    def effect87(self): pass
    def effect88(self): self.target["damage_mult"] *= 0.05
    def effect89(self): return {"MULT": [1,2,3]}
    def effect90(self): return {"DEF": 0}
    def effect91(self): pass


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
    for i,p in enumerate(party):
        p.update(**p.pop("stats"))
        p["perm_status"] = set(p["perm_status"])
        p["damage_mult"] = 1
        p["type"] = "human"
        p["position"] = i
        p["party"] = party
    front, back = party[:4], party[4:]
    enemies = [(name.strip('"'), get_character_info()) for name in args]
    enemies = [{**e, **deepcopy(DataTables.get("enemydata", name))} for name, e in enemies]
    for i,e in enumerate(enemies):
        e["HP_max"] = e["HP_cur"] = e.pop("HP")
        e["PP_max"] = e["PP_cur"] = e.pop("PP")
        e["perm_status"] = set(e["perm_status"])
        e["damage_mult"] = 1
        e["type"] = "enemy"
        e["position"] = i
        e["party"] = enemies
    cursor = 0
    side = 0
    inputs = []
    brn = rn_iter(int(kwargs.get("brn", 0)))
    grn = rn_iter(int(kwargs.get("grn", 0)))
    AbilityHandle = AbilityHandler(brn=brn, grn=grn)
    battle_log = []
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
        x,y1 = out.addtext("\n".join((p['name'] for p in front)), (2,0))
        x,y1 = out.addtext("\n".join((str(p['HP_cur']) for p in front)), (x+1,0))
        if cursor is not None:
            if side == 0: out.addtext("►", (0, cursor))
            elif side == 1: out.addtext("►", (x+3, cursor))
        x,y2 = out.addtext("\n".join((e['name'] for e in enemies)), (x+5,0))
        x,y2 = out.addtext("\n".join((str(e['HP_cur']) for e in enemies)), (x+1,0))
        if AbilityHandle.logs:
            out.addtext("\n".join(AbilityHandle.logs), (2, max(y1,y2)+1))
            AbilityHandle.logs.clear()
        return out

    def live_party(party):
        return [i for i,p in enumerate(party) if "Downed" not in p["perm_status"]]

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
            if user["HP_cur"] <= 0: user["perm_status"].add("Downed")
            elif user["HP_cur"] > 0 : user["perm_status"].discard("Downed")
        ability = DataTables.get("abilitydata", args[0].strip('"'))
        pc = front[cursor]
        if ability["range"] == 255: center = 0
        elif ability["target"] == "Self": center = pc["position"]
        else:
            if len(args) < 2:
                lp = live_party(enemies)
                center = lp[(len(lp)-1)//2]
            else: center = int(args[1])
        target_party = enemies if ability["target"] == "Enemies" else party
        AGI = (pc["AGI"]*next(grn) >> 20) + pc["AGI"]
        if ability["name"] == "Defend": AGI += 20000
        inputs.append({
            "ability": ability,
            "user": pc,
            "target": target_party[center],
            "AGI": AGI,
            })
        check = assigncursor(cursor+1)
        if check:
            for enemy in enemies: inputs.extend(enemymoves(enemy))
            result = battle_turn()
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
            [53, 47, 41, 35, 29, 23, 17, 11],
            [113, 56, 31, 20, 14, 10, 7, 5],
            [32, 32, 32, 32, 32, 32, 32, 32])
        defend = False
        for turn in range(enemy["turns"]):
            pattern = attack_patterns[enemy["attack_pattern"]]
            dice_roll = next(brn) & 255
            for i,v in enumerate(pattern):
                dice_roll -= v
                if dice_roll < 0: break
            ability = DataTables.get("abilitydata", enemy["abilities"][i])
            target_party = party if ability["target"] == "Enemies" else enemies
            AGI = enemy["AGI"]*(1 - turn/(2*enemy["turns"]))
            if ability["name"] == "Defend": AGI += 20000
            inputs.append({
                "ability": ability,
                "user": enemy,
                "target_party": target_party,
                "AGI": AGI})
        return einputs

    def battle_turn():
        nonlocal front, back, mode
        for move in sorted(inputs, key=lambda x: -x["AGI"]):
            if "Downed" in move["user"]["perm_status"]: continue
            ability = move["ability"]
            if move["user"]["type"] == "enemy":
                lp = live_party(move["target_party"])
                center = lp[len(lp)*next(grn) >> 16]
                move["target"] = move["target_party"][center]
            battle_log.append(f"{move['user']['name']} uses {ability['name']}!")
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
                turns, amt = char["status"][status]
                if turns > 0: char["status"][status][0] -= 1
                if turns == 1: char["status"][status][1] = 0
            for status in (
                    "delusion","confusion","charm","stun","sleep","psy_seal","hp_regen",
                    "reflect","death_curse","reflux","kite","immobilize"):
                turns = char["status"][status]
                if turns > 0: char["status"][status] -= 1
            char["damage_mult"] = 1
        inputs.clear()

    sent = await reply(message, f"```\n{display()}\n```")
    await utilities.live_message(sent, main)