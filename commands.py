prefix = "$"
usercommands = {}
def command(f=None, alias=None, prefix=prefix):
    def decorator(f):
        global usercommands
        if alias: usercommands[alias] = f
        usercommands[prefix + f.__name__] = f
        async def inner(*args, **kwargs):
            f(*args, **kwargs)
        return inner
    if f: return decorator(f)
    else: return decorator


### Register functions and import modules below ###
import re
import inspect
from utilities import DataTables, UserData, namemaps, load_data, reply, dictstr, tablestr
from safe_eval import safe_eval


@command
async def help(message, *args, **kwargs):
    """Provides information about the bot and its functions"""

    if not args:
        docs = {name: f.__doc__ for name, f in usercommands.items()}
        docs = {k:v.split("\n",1)[0] for k,v in docs.items() if v and k.startswith(prefix)}
        output = dictstr(docs) + f"\nType \"{prefix}help func\" for detailed information about func"
        output += "\n\nFunction arguments are words separated by spaces\n    ex. $sort enemydata HP"
        output += "\nKeyword arguments have the format: key=value\n    no spaces, unless value is in quotes"
        output += "\n\nDataTables:"
        for name in DataTables:
            output += "\n    " + name
            if name == "enemydata-h": output += " (hard-mode stats)"
        await reply(message, f"```{output}```")
        return
    await reply(message, f"```{inspect.getdoc(usercommands['$'+args[0]])}```")


@command
async def info(message, *args, **kwargs):
    """Returns info on something, like a search engine
    
    Arguments:
        name -- the name of the object to search for

    Keyword Arguments:
        key -- an attribute of the returned object to view
        i -- instance number.  If the query returns multiple results, 
             this argument selects one of them
        json -- set equal to 1 or "true" to format the output as json
    """
    instance = kwargs.get("i")
    key = kwargs.get("key")
    name = " ".join(args).lower()
    for tablename, data in DataTables.items():
        if name in namemaps[tablename]:
            IDlist = namemaps[tablename][name]
            if instance:
                IDlist = [IDlist[int(instance)]]
            for ID in IDlist:
                if key:
                    output = str(data[ID][key])
                else:
                    output = dictstr(data[ID], kwargs.get("json"))
                await reply(message, "```\n" + output + "\n```")
            return
    else:
        await reply(message, f"\"{name}\" not found")


@command
async def index(message, *args, **kwargs):
    """Indexes a data table
    
    Arguments:
        tablename -- the name of the data table
        *condition -- searches data until condition is met
                      a mathematical expression that may contain object attribute names
                      set equal to a number to index normally
    
    Keyword Arguments:
        json -- set equal to 1 or "true" to format the output as json
    """
    if len(args) < 2:
        await reply(message,
            f"`{prefix}index` expects two arguments: `{prefix}index tablename condition`\n" +
            f"valid tablenames: `{', '.join(DataTables.keys())}`")
        return
    tablename = args[0]
    condition = " ".join(args[1:])
    if re.match(r"\d+$", condition):
        output = dictstr(DataTables[tablename][int(condition)], kwargs.get("json"))
    else:
        for entry in DataTables[tablename]:
            if safe_eval(condition, entry):
                output = dictstr(entry, kwargs.get("json"))
                break
        else:
            output = "no match found"
    await reply(message, f"```{output}```")


@command(alias="=")
async def math(message, *args, **kwargs):
    """Evaluate a mathematical expression like a calculator

    Available functions/variables:
        abs, round, min, max, rand, pi, e, sin, cos, tan, sqrt, log, exp,
        int, sum, len, bin, hex

    Keyword Arguments:
        f -- format string; uses python's format-specification-mini-language

    Alias: =[insert expression here]
    """
    import math
    import random

    def rand(*args):
        if len(args) == 1: return random.randint(1, *args)
        elif args: return random.randint(*args)
        else: return random.random()

    mfuncs = {
        'abs':abs, 'round':round, 'min':min, 'max':max, 'rand':rand,
        'bin':bin, 'hex':hex, 'len':len, 'sum': sum, 'int': int,
        'True':True, 'False':False, 'pi':math.pi, 'e': math.exp(1), 
        'sin':math.sin, 'cos':math.cos, 'tan':math.tan, 'sqrt':math.sqrt,
        'log':math.log, 'exp':math.exp,
    }

    value = safe_eval(" ".join(args), mfuncs)
    fspec = r"(.?[<>=^])?([+\- ])?(#)?(0)?(\d+)?([_,])?(.\d+)?([bcdeEfFgGnosxX%])?"
    frmt = re.match(fspec, kwargs.get("f", "")).groups()
    if frmt[4] and len(frmt[4]) > 3:
        await reply(message, "width specifier too large")
        return
    frmt = "".join([i for i in frmt if i]).strip('"')
    await reply(message, f"`{value:{frmt}}`")


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
async def filter(message, *args, **kwargs):
    """Filters a data table based on a custom condition

    Arguments:
        tablename -- the table to search
        *condition -- a mathematical expression that may contain attribute names
                      example: HP>5000 and DEF<100
    
    Keyword Arguments:
        fields -- additional attributes to display in the output, separated by commas
    """
    table = args[0]
    condition = " ".join(args[1:])
    if not condition: output = DataTables[table]
    else: output = [e for e in DataTables[table] if safe_eval(condition, e)]
    fields = ["ID"]
    if "name" in DataTables[table][0]: fields.append("name")
    if kwargs.get("fields"):
        fields.extend((f.strip(" ") for f in kwargs["fields"].strip('"').split(",")))
    if output: await reply(message, f"```{tablestr(output, fields=fields)}```")
    else: await reply(message, "no match found")


@command
async def sort(message, *args, **kwargs):
    """Sorts a data table based on an attribute (may also filter)

    Arguments:
        tablename -- the table to search
        attribute -- the attribute to sort by
                     to sort from highest to lowest, place a "-" sign in front
        *filter -- a mathematical expression that may contain attribute names
                   will only output entries that make the expression true
                   example: HP>5000 and DEF<100

    Keyword Arguments:
        range -- a section of the output to display.  Default is "0,20"
                 if you input only one number, it will display that many entries
        fields -- additional attributes to display in the output, separated by commas
    """
    table = args[0]
    key = args[1].strip('"')
    data = DataTables[table]
    condition = " ".join(args[2:])
    if condition:
        data = [entry for entry in data if safe_eval(condition, entry)]
    if key.startswith("-"):
        key = key[1:].strip(" ")
        output = sorted(data, key=lambda x: x[key], reverse=True)
    else:
        output = sorted(data, key=lambda x: x[key])
    range_ = list(map(int, kwargs.get("range", "0,20").strip('"').split(",")))
    if len(range_) == 1: range_.insert(0,0)
    output = list(output)[range_[0]:range_[1]]
    fields = ["ID"]
    if "name" in DataTables[table][0]: fields.append("name")
    if kwargs.get("fields"):
        fields.extend((f.strip(" ") for f in kwargs["fields"].strip('"').split(",")))
    else:
        fields.append(key)
    if output: await reply(message, f"```{tablestr(output, fields=fields)}```")
    else: await reply(message, "no match found")


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
    ATK, DEF, HP, POW, RES, RANGE = [kwargs.get(kw) for kw in ("atk","def","hp","pow","res","range")]
    if ATK is not None: ATK = int(ATK)
    if DEF is not None: DEF = int(DEF)
    if HP is not None: HP = int(HP)
    if POW is not None: POW = int(POW)
    if RES is not None: RES = int(RES)
    if RANGE is not None: RANGE = int(RANGE)
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
