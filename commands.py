import discord
import asyncio
import re
import inspect
import utilities
from utilities import \
    command, prefix, DataTables, UserData, MessageData,\
    Namemaps, reply, dictstr, mfuncs
import gsfuncs
from safe_eval import safe_eval


### Register functions below ###

@command
async def help(message, *args, **kwargs):
    """Provides information about the bot and its functions"""

    if not args:
        docs = {name: f.__doc__ for name, f in utilities.usercommands.items()}
        docs = {k:v.split("\n",1)[0] for k,v in docs.items() if v and k.startswith(prefix)}
        out = dictstr(docs)
        out += "\n\n" + inspect.cleandoc(f"""
        Type "{prefix}help [func]" for detailed information about [func]
        
        Function arguments are words separated by spaces
            ex. $sort enemydata HP

        Keyword arguments have the format: key=value
            value cannot have spaces, unless value is in quotes

        Python expressions may be used for some functions
            https://python-reference.readthedocs.io/en/latest/docs/operators/
            obaba bot accepts the following operation types:
                Arithmetic, Relational, Boolean, Membership, Bitwise, Indexing

        Multi-Page responses may be indexed using the {prefix}page command
        """)
        return await reply(message, f"```\n{out}\n```")
    else:
        func = utilities.usercommands['$'+args[0]]
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
    name = " ".join(args).lower()
    for table, mapping in Namemaps.items():
        if name in mapping:
            entries = mapping[name]
            if kwargs.get("i"): entries = [entries[int(kwargs.get("i"))]]
            for entry in entries:
                await reply(message, f"```\n{dictstr(entry, js=kwargs.get('json'))}\n```")
            return
    else:
        await reply(message, f"\"{name}\" not found")


@command
async def index(message, *args, **kwargs):
    """Index a data table
    
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
            if safe_eval(condition, {**mfuncs, **entry}):
                output = dictstr(entry, kwargs.get("json"))
                break
        else:
            output = "no match found"
    await reply(message, f"```\n{output}\n```")


@command(alias="=")
async def math(message, *args, **kwargs):
    """Evaluate a python expression

    Available functions/variables:
        abs, round, min, max, rand, pi, e, sin, cos, tan, sqrt, log, exp,
        int, sum, len, bin, hex, plus any tablenames from the database

    Keyword Arguments:
        f -- format string; uses python's format-specification-mini-language

    Aliases:
        may use the "=" sign in place of "$math "
    """
    ID = message.author.id
    value = safe_eval(" ".join(args), {**mfuncs, **DataTables, **UserData[ID].vars})
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
    
    Variables are stored per-user, and will be reset whenever the bot is 
    reset, which can happen at any time.  They may be used in any var or
    math commands.
    """
    ID = message.author.id
    m = re.match(r"\$var\s+([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*(.*)", message.content)
    varname, content = m.groups()
    args, kwargs = utilities.parse(content)
    value = safe_eval(" ".join(args), {**mfuncs, **DataTables, **UserData[ID].vars})
    fspec = r"(.?[<>=^])?([+\- ])?(#)?(0)?(\d+)?([_,])?(.\d+)?([bcdeEfFgGnosxX%])?"
    frmt = re.match(fspec, kwargs.get("f", "")).groups()
    assert not frmt[4] or len(frmt[4]) <= 3, "width specifier too large"
    frmt = "".join([i for i in frmt if i]).strip('"')
    if frmt: value = f"{value:{frmt}}"
    UserData[ID].vars[varname] = value


@command
async def filter(message, *args, **kwargs):
    """Filter a data table based on a custom condition

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
    else: output = [e for e in DataTables[table] if safe_eval(condition, {**mfuncs, **e})]
    fields = ["ID"]
    if "name" in DataTables[table][0]: fields.append("name")
    if kwargs.get("fields"):
        fields.extend((f.strip(" ") for f in kwargs["fields"].strip('"').split(",")))
    if output: await reply(message, f"```\n{utilities.tableH(output, fields=fields, border='=')}\n```")
    else: await reply(message, "no match found")


@command
async def sort(message, *args, **kwargs):
    """Sort a data table based on an attribute (may also filter)

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
        data = [entry for entry in data if safe_eval(condition, {**mfuncs, **entry})]
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
    """Upload a file using an attachment or a link

    Uploads are stored per-user, and will remain in the bot's
    memory until the bot is reset, which can happen at any time.  Some 
    functions require that you have already called this function within
    the most recent bot session.

    Accepted File Types:
        .sav -- Battery files. Sends a multi-page message.
            P -- view the preview page
            0,1,2 -- switch to the corresponding slot
            <,> -- scroll through the characters of the current slot
        .SaveRAM -- Bizhawk battery files (same as .sav)

    Arguments:
        link -- (optional) a link to a message with an attached file
                if not included, you must attach a file to the message
    """
    if message.attachments:
        attachment = message.attachments[0]
    else:
        assert args and args[0].startswith("https://discord.com/channels/"), \
            "Expected an attachment or a link to a message with an attachment"
        ID_list = args[0][len("https://discord.com/channels/"):].split("/")
        serverID, channelID, messageID = (int(i) for i in ID_list)
        server = utilities.client.get_guild(serverID)
        channel = server.get_channel(channelID)
        m = await channel.fetch_message(messageID)
        attachment = m.attachments[0]
    data = await attachment.read()
    url = attachment.url
    if url.endswith(".sav") or url.endswith(".SaveRAM"):
        for i in range(16):
            addr = 0x1000*i
            if data[addr:addr+7] == b'CAMELOT' and data[addr+7] < 0xF: break
        else:
            assert 0, "No valid saves detected"
        ID = message.author.id
        UserData[ID].save = data
        pages = gsfuncs.preview(data)
        sent = await reply(message, pages["preview"])
        async def medit(message, user, emoji):
            mdata = MessageData[message]
            try:
                if emoji == '\U0001f1f5':
                    await message.edit(content=mdata["pages"]["preview"])
                else:
                    if emoji.endswith('\ufe0f\u20e3'):
                        slot = int(emoji[0])
                        if slot in mdata["pages"]: mdata["slot"] = slot
                    elif emoji == "\u25c0\ufe0f":
                        mdata["page"] -= 1
                    elif emoji == "\u25b6\ufe0f":
                        mdata["page"] += 1
                    else: return
                    mdata["page"] %= len(mdata["pages"][mdata["slot"]])
                    content = mdata["pages"][mdata["slot"]][mdata["page"]]
                    await message.edit(content=content)
            except KeyError:
                pass
            finally:
                await message.remove_reaction(emoji, user)
        slots = [k for k in pages if isinstance(k, int)]
        MessageData[sent] = {"slot": slots[0], "page": 0, "pages": pages, "func":medit}
        buttons = ['\U0001f1f5','0\ufe0f\u20e3','1\ufe0f\u20e3',
                   '2\ufe0f\u20e3','\u25c0\ufe0f','\u25b6\ufe0f']
        tasks = [utilities.client.loop.create_task(sent.add_reaction(b)) for b in buttons]
        for t in tasks: await t
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