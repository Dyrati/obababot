import discord
import re
import inspect
from copy import deepcopy
from . import utilities
from .utilities import \
    client, command, prefix, DataTables, UserData, Images, \
    reply, dictstr, mfuncs
from . import gsfuncs
from .safe_eval import safe_eval
from . import thumbasm


### Register functions below ###

@command
async def help(message, *args, **kwargs):
    """Provides information about the bot and its functions"""

    if not args:
        docs = {name: f.__doc__ for name, f in utilities.usercommands.items()}
        docs = {k:v.split("\n",1)[0] for k,v in docs.items() if v and k.startswith(prefix)}
        out = dictstr(docs)
        out += "\n\n" + inspect.cleandoc(f"""
        Type "{prefix}help" followed by a command name for detailed info about the command
        
        Function arguments are words separated by spaces
            ex. {prefix}sort enemydata HP

        Keyword arguments have the format: key=value
            value cannot have spaces, unless value is in quotes

        Python expressions may be used for some functions
            https://python-reference.readthedocs.io/en/latest/docs/operators/
            obaba bot accepts the following operation types:
                Arithmetic, Relational, Boolean, Membership, Bitwise, Indexing
        """)
        return await reply(message, f"```\n{out}\n```")
    else:
        func = (prefix if not args[0].startswith(prefix) else "") + args[0]
        func = utilities.usercommands[func]
        await reply(message, f"```\n{inspect.getdoc(func)}\n```")


@command
async def datatables(message, *args, **kwargs):
    """Display the names of all the data tables"""
    names = list(DataTables)
    for i, name in enumerate(names):
        if name == "enemydata-h":
            names[i] += " (hard mode stats)"
    out = "\n".join(names)
    await reply(message, f"```\n{out}\n```")


@command
async def info(message, *args, **kwargs):
    """Display info about something
    
    Arguments:
        name -- the name of the object to search for

    Keyword Arguments:
        i -- instance number.  If the query returns multiple results, 
             this argument selects one of them
        json -- set equal to 1 or "true" to format the output as json
    """
    name = " ".join(args)
    for table in DataTables:
        entries = DataTables.get_all(table, name)
        if entries:
            if kwargs.get("i"): entries = [entries[int(kwargs.get("i"))]]
            for entry in entries:
                await reply(message, f"```\n{dictstr(entry, js=kwargs.get('json'))}\n```")
            return
    else:
        await reply(message, f"\"{name}\" not found")


@command
async def display(message, *args, **kwargs):
    """Display an object or list of objects

    Arguments:
        object -- the object to display.  This must either be a python
                  dictionary or a list of python dictionaries
                  accepts python expressions as input

    Keyword Arguments:
        fields -- if displaying a table, this argument may be a list of 
                  comma-separated attributes to display in the output table
    """
    uvars = UserData[message.author.id].vars
    obj = safe_eval(" ".join(args), uvars)
    if isinstance(obj, dict):
        output = dictstr(obj)
    elif isinstance(obj, list) and obj and isinstance(obj[0], dict):
        fields = ["ID"]
        if "name" in obj[0]: fields.append("name")
        if kwargs.get("fields"):
            fields.extend((f.strip(" ") for f in kwargs["fields"].strip('"').split(",")))
        output = utilities.tableH(obj, fields=fields, border='=')
    else:
        raise AssertionError("Expected a python dictionary or a list of dictionaries")
    await reply(message, f"```\n{output}\n```")


@command(alias="=")
async def math(message, *args, **kwargs):
    """Evaluate a python expression

    Available functions/variables:
        abs, round, min, max, rand, pi, e, sin, cos, tan, sqrt, log, exp,
        int, sum, len, bin, hex, plus any tablenames from the database

    Keyword Arguments:
        f -- format string; uses python's format-specification-mini-language
             https://docs.python.org/3/library/string.html#formatspec

    Aliases:
        may use the "=" sign in place of "$math "
    """
    value = safe_eval(" ".join(args), UserData[message.author.id].vars)
    fspec = r"(.?[<>=^])?([+\- ])?(#)?(0)?(\d+)?([_,])?(.\d+)?([bcdeEfFgGnosxX%])?"
    frmt = re.match(fspec, kwargs.get("f", "")).groups()
    assert not frmt[4] or len(frmt[4]) <= 3, "width specifier too large"
    frmt = "".join([i for i in frmt if i]).strip('"')
    if frmt: value = f"{value:{frmt}}"
    await reply(message, f"`{value}`")


@command
async def var(message, *args, **kwargs):
    """Set a variable equal to a python expression
    
    Syntax:
        - $var [name] = [expression]
        - [name] must start with a letter or underscore, and remaining
          characters may only contain alphanumerics or underscores
        - [expression] has identical syntax to the $math command
    
    Keyword Arguments:
        clear -- set to true to reset all of your user variables
    
    Variables are stored per-user, and will be reset whenever the bot is 
    reset, which can happen at any time.  They may be used in any var or
    math commands.
    """
    ID = message.author.id
    if kwargs.get("clear"):
        UserData[ID].vars = dict(_=None, **mfuncs)
        await reply(message, "Variables reset to default")
        return
    m = re.match("\\" + prefix + r"var\s+([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*(.*)", message.content)
    varname, content = m.groups()
    args, kwargs = utilities.parse(content)
    value = safe_eval(" ".join(args), UserData[ID].vars)
    fspec = r"(.?[<>=^])?([+\- ])?(#)?(0)?(\d+)?([_,])?(.\d+)?([bcdeEfFgGnosxX%])?"
    frmt = re.match(fspec, kwargs.get("f", "")).groups()
    assert not frmt[4] or len(frmt[4]) <= 3, "width specifier too large"
    frmt = "".join([i for i in frmt if i]).strip('"')
    if frmt: value = f"{value:{frmt}}"
    UserData[ID].vars[varname] = value


@command
async def filter(message, *args, **kwargs):
    """Filter a data table based on a custom condition

    Automatically stores the result in the variable "_"

    Arguments:
        tablename  -- the table to filter. Accepts user variables
        *condition -- a python expression that may contain attribute names
                      example: HP>5000 and DEF<100
    
    Keyword Arguments:
        fields -- additional attributes to display in the output, separated by commas
    """
    uvars = UserData[message.author.id].vars
    table = safe_eval(args[0], uvars)
    condition = " ".join(args[1:])
    output = [e for e in table if safe_eval(condition, {**uvars, **e})]
    uvars["_"] = output
    fields = ["ID"]
    if "name" in table[0]: fields.append("name")
    if kwargs.get("fields"):
        fields.extend((f.strip(" ") for f in kwargs["fields"].strip('"').split(",")))
    if output: await reply(message, f"```\n{utilities.tableH(output, fields=fields, border='=')}\n```")
    else: await reply(message, "no match found")


@command
async def sort(message, *args, **kwargs):
    """Sort a data table based on an attribute (may also filter)

    Automatically stores the result in the user variable "_"

    Arguments:
        table -- the table to sort. Accepts user variables
        *key  -- a python expression to sort the objects by (ex: len(name))
                 to sort from highest to lowest, place a "-" sign in front

    Keyword Arguments:
        range  -- the number of entries to display.  Default is 20.
                  to display a section of the output, use the syntax: "start,end"
        fields -- additional attributes to display in the output, separated by commas
        filter -- a python expression that may contain attribute names
                  will only output entries that make the expression true
                  example: HP>5000 and DEF<100
    """
    uvars = UserData[message.author.id].vars
    data = safe_eval(args[0], uvars)
    key = " ".join(args[1:])
    condition = kwargs.get("filter")
    if condition:
        condition = condition.strip('"')
        data = (entry for entry in data if safe_eval(condition, {**uvars, **entry}))
    reverse = False
    if key.startswith("-"): key = key[1:]; reverse = True
    mapping = map(lambda x: dict(value=safe_eval(key, {**uvars, **x}), **x), data)
    output = list(sorted(mapping, key=lambda x: x["value"], reverse=reverse))
    range_ = list(map(int, kwargs.get("range", "20").strip('"').split(",")))
    if len(range_) == 1: range_.insert(0,0)
    uvars["_"] = output
    output = output[range_[0]:range_[1]]
    fields = ["ID"]
    reference = output[0]
    if "name" in reference: fields.append("name")
    if key in reference:
        if key not in fields: fields.append(key)
    else: fields.append("value")
    if kwargs.get("fields"):
        fields.extend((f.strip(" ") for f in kwargs["fields"].strip('"').split(",")))
    if output: await reply(message, f"```\n{utilities.tableH(output, fields=fields, border='=')}\n```")
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
    assert len(args[1:])==4, \
        "Expected a party member name followed by 4 djinn counts: Venus, Mercury, Mars, Jupiter"
    djinncounts = [int(arg) for arg in args[1:]]
    pc_class = gsfuncs.getclass(args[0], djinncounts, item=kwargs.get("item"))
    await reply(message, f"`{pc_class['name']}`")


@command
async def damage(message, *args, **kwargs):
    """Calculate damage

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
    abilityname = " ".join(args).strip('"')
    ability = DataTables.get("abilitydata", abilityname)
    if not ability:
        ability = DataTables.get("itemdata", abilityname)
        ability = DataTables["abilitydata"][ability["use_ability"]]
        kwargs["pow"] = "100"
    kwargs = {k:v.strip('"').lower() for k,v in kwargs.items()}
    for key in ("atk", "pow", "hp", "def", "res", "range"):
        if kwargs.get(key) is not None:
            kwargs[key.upper()] = int(kwargs.pop(key))
    for kw in {"user", "target"} & set(kwargs):
        user = UserData[message.author.id]
        names = {p.name.lower():p for p in user.party} if user.party else {}
        if kwargs[kw] in names: kwargs[kw] = names[kwargs[kw]]
        else: kwargs[kw] = gsfuncs.EnemyData(DataTables.get("enemydata", kwargs[kw]))
    damage = gsfuncs.battle_damage(ability, **kwargs)
    await reply(message, f"`{damage}-{damage+3}`")


@command
async def textbox(message, *args, **kwargs):
    """Generate a Golden sun Text Box
    
    Keyword Arguments:
        padding -- "top right bottom left"
    """
    from .textboxes import textbox, to_buffer, add_padding
    text = message.content[len(f"{prefix}textbox"):]
    padding = re.search(r"\s*padding *= *\"(.*?)\" *", text)
    if padding: text = text.replace(padding.group(), "", 1)
    im = textbox(re.sub(r"^ *\n", "", text))
    if padding: im = add_padding(im, [int(x) for x in padding.group(1).split(" ")])
    await message.channel.send(file=discord.File(to_buffer(im), "text.png"))


async def handlesav(message, data):
    headers = (data[addr:addr+16] for addr in range(0,0x10000,0x1000))
    assert any((h[:7] == b'CAMELOT' and h[7] <= 0xF for h in headers)), "No valid saves detected"
    user = UserData[message.author.id]
    filedata = gsfuncs.readsav(data)
    pages = gsfuncs.preview(filedata)
    user.filedata = filedata
    slots = [k for k in pages if isinstance(k, int)]
    slot = slots[0]
    page = 0
    async def on_react(message, user, button):
        nonlocal slot, page
        if button == "P":
            await message.edit(content=pages["preview"])
        elif button == "?":
            await message.edit(content=pages["help"])
        else:
            if button in slots: slot = button
            elif button == "<": page -= 1
            elif button == ">": page += 1
            else: return
            page %= len(pages[slot])
            await message.edit(content=pages[slot][page])
    buttons = {
        '\U0001f1f5':"P",'0\ufe0f\u20e3':0,'1\ufe0f\u20e3':1,'2\ufe0f\u20e3':2,
        '\u25c0\ufe0f':"<",'\u25b6\ufe0f':">",'\u2753':"?"}
    sent = await reply(message, pages["preview"])
    await utilities.set_buttons(sent, buttons, on_react)


@command
async def upload(message, *args, **kwargs):
    """Upload a file using an attachment or a link

    Uploads are stored per-user, and will remain in the bot's
    memory until the bot is reset, which can happen at any time.  Some 
    functions require that you have already called this function within
    the most recent bot session.

    Accepted File Types:
        .sav -- Battery files. Returns a multi-page message.
        .SaveRAM -- Bizhawk battery files (same as .sav)

    Arguments:
        link -- (optional) a link to a message with an attached file
                if not included, you must attach a file to the message
    """
    attachment = await utilities.get_attachment(message, *args)
    data = await attachment.read()
    if attachment.url.endswith(".sav") or attachment.url.endswith(".SaveRAM"):
        await handlesav(message, data)
    else:
        assert 0, "Unhandled file type"


@command
async def delete(message, *args, **kwargs):
    """Delete the last message(s) sent to you by obaba this session"""
    ID = message.author.id
    UserData[ID].responses.pop()
    try: responses = UserData[ID].responses.pop()
    except IndexError: return
    for message in responses:
        await message.delete()


@command
async def asm(message, *args, **kwargs):
    """Translate assembly instructions to hex code
    
    Arguments:
        instr -- the assembly instruction to convert
    
    Keyword Arguments:
        addr -- the address from which the instruction is executed
    """
    addr = int(kwargs.get("addr", "0"), 16)
    output = thumbasm.asm(" ".join(args).strip('"'), addr=addr)
    f = "04X" if output < 0x10000 else "08X"
    await reply(message, f"{output:{f}}")

@command
async def dasm(message, *args, **kwargs):
    """Translate hex code to assembly instructions
    
    Arguments:
        value  -- the hex code to convert
        value2 -- (optional) the second half of a bl instruction
    
    Keyword Arguments:
        addr -- the address of the hex code
    """
    addr = int(kwargs.get("addr", "0"), 16)
    args = [int(x,16) for x in args]
    await reply(message, thumbasm.disasm(*args, addr=addr))