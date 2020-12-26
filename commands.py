import re
import inspect
import utilities
from utilities import command, prefix, DataTables, UserData, namemaps, reply, dictstr
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
                await reply(message, f"```{output}```")
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


@command(alias="=")
async def math(message, *args, **kwargs):
    """Evaluate a python expression

    Available functions/variables:
        abs, round, min, max, rand, pi, e, sin, cos, tan, sqrt, log, exp,
        int, sum, len, bin, hex

    Keyword Arguments:
        f -- format string; uses python's format-specification-mini-language

    Alias:
        may use the "=" sign in place of "$math "
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
