import re
import inspect
import utilities
from utilities import command, prefix, DataTables, UserData, Namemaps, reply, dictstr
import gsfuncs
from safe_eval import safe_eval


### Register functions below ###

@command
async def help(message, *args, **kwargs):
    """Provides information about the bot and its functions"""

    if not args:
        docs = {name: f.__doc__ for name, f in utilities.usercommands.items()}
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
    await reply(message, f"```{inspect.getdoc(utilities.usercommands['$'+args[0]])}```")


@command
async def info(message, *args, **kwargs):
    """Returns info on something, like a search engine
    
    Arguments:
        name -- the name of the object to search for

    Keyword Arguments:
        i -- instance number.  If the query returns multiple results, 
             this argument selects one of them
        json -- set equal to 1 or "true" to format the output as json
    """
    name = " ".join(args).lower()
    for table, mapping in Namemaps.items():
        if name in mapping:
            entries = mapping[name]
            if kwargs.get("i"): entries = [entries[int(kwargs.get("i"))]]
            for entry in entries:
                await reply(message, f"```{dictstr(entry, js=kwargs.get('json'))}```")
            return
    else:
        await reply(message, f"\"{name}\" not found")


@command
async def index(message, *args, **kwargs):
    """Indexes a data table
    
    Arguments:
        tablename -- the name of the data table
        *condition -- grabs the *nth* element of a data table
                      may alternatively contain a python expression, and will
                      return the first object that satisfies the expression
    
    Keyword Arguments:
        json -- set equal to 1 or "true" to format the output as json
    """
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
@command(alias=r"(?P<set>[a-zA-Z_][a-zA-Z0-9_]*)?\s*=")
async def math(message, *args, **kwargs):
    """Evaluate a python expression

    Available functions/variables:
        abs, round, min, max, rand, pi, e, sin, cos, tan, sqrt, log, exp,
        int, sum, len, bin, hex, plus any tablenames from the database

    Keyword Arguments:
        f -- format string; uses python's format-specification-mini-language
        set -- a variable name to assign the output to.  Variables are stored
               per-user, and will be reset whenever the bot is reset, which
               can happen at any time.
    Aliases:
        may use the "=" sign in place of "$math "
        may use "varname = expression" to set variables as well
    """
    ID = message.author.id
    UserData[ID] = UserData.get(ID, {"vars":{}})
    value = safe_eval(" ".join(args), {**mfuncs, **DataTables, **UserData[ID]["vars"]})
    fspec = r"(.?[<>=^])?([+\- ])?(#)?(0)?(\d+)?([_,])?(.\d+)?([bcdeEfFgGnosxX%])?"
    frmt = re.match(fspec, kwargs.get("f", "")).groups()
    if frmt[4] and len(frmt[4]) > 3:
        await reply(message, "width specifier too large")
        return
    frmt = "".join([i for i in frmt if i]).strip('"')
    if frmt: value = f"{value:{frmt}}"
    if kwargs.get("set"):
        varname = kwargs["set"]
        UserData[ID]["vars"][varname] = value
    else:
        await reply(message, f"`{value}`")


@command
async def filter(message, *args, **kwargs):
    """Filters a data table based on a custom condition

    Arguments:
        tablename -- the table to search
        *condition -- a python expression that may contain attribute names
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
    if output: await reply(message, f"```{utilities.tableH(output, fields=fields)}```")
    else: await reply(message, "no match found")


@command
async def sort(message, *args, **kwargs):
    """Sorts a data table based on an attribute (may also filter)

    Arguments:
        tablename -- the table to search
        attribute -- the attribute to sort by
                     to sort from highest to lowest, place a "-" sign in front
        *filter -- a python expression that may contain attribute names
                   will only output entries that make the expression true
                   example: HP>5000 and DEF<100

    Keyword Arguments:
        range -- the number of entries to display.  Default is 20.
                 to display a section of the output, use the syntax: "start,end"
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
    range_ = list(map(int, kwargs.get("range", "20").strip('"').split(",")))
    if len(range_) == 1: range_.insert(0,0)
    output = list(output)[range_[0]:range_[1]]
    fields = ["ID"]
    if "name" in DataTables[table][0]: fields.append("name")
    if kwargs.get("fields"):
        fields.extend((f.strip(" ") for f in kwargs["fields"].strip('"').split(",")))
    else:
        fields.append(key)
    if output: await reply(message, f"```{utilities.tableH(output, fields=fields)}```")
    else: await reply(message, "no match found")


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
    assert len(args[1:])==4, "Expected 4 djinn counts: Venus, Mercury, Mars, Jupiter"
    djinncounts = [int(arg) for arg in args[1:]]
    pc_class = gsfuncs.getclass(args[0], djinncounts, item=kwargs.get("item"))
    await reply(message, f"`{pc_class['name']}`")


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
        range -- distance from primary target
    """
    ability = args[0].strip('"')
    kwargs = {k:v.strip('"').lower() for k,v in kwargs.items()}
    for key in ("atk", "pow", "hp", "def", "res", "range"):
        if kwargs.get(key) is not None:
            kwargs[key.upper()] = int(kwargs.pop(key))
    await reply(message, f"`{gsfuncs.damage(ability, **kwargs)}`")


@command
async def upload(message, *args, **kwargs):
    """Upload a file

    Uploads are stored per-user, and will remain in the bot's
    memory until the bot is reset, which can happen at any time.  Some 
    functions require that you have already called this function within
    the most recent bot session.

    Accepted File Types:
        .sav -- Battery files. Enables save-related commands

    Arguments:
        link -- (optional) a link to a message with an attached file
                if not included, you must attach a file to the message
    """
    ID = str(message.author.id)
    if not UserData.get(ID): UserData[ID] = {}
    if message.attachments:
        attachment = message.attachments[0]
    else:
        assert args and args[0].startswith("https://discord.com/channels/"), \
            "Expected an attachment or a link to a message with an attachment"
        ID_list = args[0].replace("https://discord.com/channels/","").split("/")
        serverID, channelID, messageID = (int(i) for i in ID_list)
        server = utilities.client.get_guild(serverID)
        channel = server.get_channel(channelID)
        m = await channel.fetch_message(messageID)
        attachment = m.attachments[0]
    data = await attachment.read()
    url = attachment.url
    if url.endswith(".sav") or url.endswith("SaveRAM"):
        for i in range(16):
            addr = 0x1000*i
            if data[addr:addr+7] == b'CAMELOT' and data[addr+7] < 0xF: break
        else:
            assert 0, "No valid saves detected"
        UserData[ID]["save"] = data
        sent = await utilities.usercommands["$save_preview"](message, concise=True)
        UserData[ID]["response"] = sent
    else:
        assert 0, "Unhandled file type"