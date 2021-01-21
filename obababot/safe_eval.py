import re

ops = {
    "**": lambda a, b: a ** b,
    "~" : lambda a: ~a,
    "/" : lambda a, b: a / b,
    "//": lambda a, b: a // b,
    "%" : lambda a, b: a % b,
    "*" : lambda a, b: a * b,
    "+" : lambda a, b: a + b,
    "-" : lambda a, b: a - b,
    ">>": lambda a, b: a >> b,
    "<<": lambda a, b: a << b,
    "&" : lambda a, b: a & b,
    "^" : lambda a, b: a ^ b,
    "|" : lambda a, b: a | b,
    "<" : lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">" : lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "!=": lambda a, b: a != b,
    "==": lambda a, b: a == b,
    "in": lambda a, b: a in b,
    "not in": lambda a, b: a not in b,
    "not": lambda a: not a,
    "and": lambda a, b: a and b,
    "or": lambda a, b: a or b,
}

op_regex = [
    re.compile(r"^.*?(\*\*).*"),
    re.compile(r"(~).*"),
    re.compile(r".*(//|(?<!/)/(?!/)|%|(?<!\*)\*(?!\*)).*"),
    re.compile(r".*(?<![+\-])([+\-]).*"),
    re.compile(r".*(<<|>>).*"),
    re.compile(r".*(&).*"),
    re.compile(r".*(\^).*"),
    re.compile(r".*(\|).*"),
    re.compile(r".*((?<!<)<(?![<=])|<=|(?<!>)>(?![>=])|>=|!=|==|(?<!not\s)in|not in).*"),
    re.compile(r"\b(not)\s(?!in\b).*"),
    re.compile(r".*\s(and)\s.*"),
    re.compile(r".*\s(or)\s.*"),
]

mquote = re.compile(r"(\".*?\"|\'.*?\')")
varmatch = r"\b(?!(?:in|not|and|or)\b)[a-zA-Z_]\w*"
mgroup = re.compile(rf"[^)\]]*(?<![\w}}])(({varmatch}|{{\d+}})?(?:\((.*?)\)|\[(.*?)\]))")
mvar = re.compile(rf"({varmatch})")
mtoken = re.compile(r"^\s*{(\d+)}\s*$")


def tokensub(regex, s, func, groups):
    m = regex.search(s)
    while m:
        groups.append(func(m))
        s = f"{s[:m.start(1)]}{{{len(groups)-1}}}{s[m.end(1):]}"
        m = regex.search(s)
    return s

def groupeval(m, v, groups):
    group, name, parens, brackets = m.groups()
    if name is not None:
        if mtoken.match(name): var = groups[int(name[1:-1])]
        else: var = v[name]
        if parens is not None:
            args = (safe_eval(arg, v, groups) for arg in parens.split(","))
            return var(*args)
        elif brackets is not None:
            args = [arg.strip(" ") for arg in brackets.split(":")]
            args = [safe_eval(arg, v, groups) if arg else None for arg in args]
            if len(args) == 1: return var[args[0]]
            else: return var[slice(*args)]
    else:
        if parens is not None:
            return safe_eval(parens, v, groups)
        elif brackets is not None:
            return [safe_eval(arg, v, groups) for arg in brackets.split(",")]

def safe_eval(s, v={}, groups=None):
    if groups is None: groups = []
    s = tokensub(mquote, s, lambda x: x.group()[1:-1], groups)
    s = re.sub(r"\b0x[0-9a-fA-F]+\b", lambda x: str(int(x.group(),16)), s)
    s = tokensub(mgroup, s, lambda x: groupeval(x, v, groups), groups)
    s = tokensub(mvar, s, lambda x: v[x.group(1)], groups)
    token = mtoken.match(s)
    if token: return groups[int(token.group(1))]
    for regex in reversed(op_regex):
        m = regex.search(s)
        if not m: continue
        op = m.group(1)
        args = [s[:m.start(1)], s[m.end(1):]]
        args = [safe_eval(arg.strip(" "), v, groups) for arg in args if arg]
        if "*" in op and all((isinstance(arg, (int, float)) for arg in args)):
            args = list(map(float, args))
        elif op == "<<" and float(args[0]) and args[1]>1023:
            raise OverflowError("Result too large")
        elif op in "-+" and len(args) == 1:
            args.insert(0, 0)
        out = ops[op](*args)
        if isinstance(out, float) and out == int(out): return int(out)
        else: return out
    else:
        s = float(s)
        if s == int(s): return int(s)
        else: return s