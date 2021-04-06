import re

op_map = {
    "00000": "lsl r{2-0}, r{5-3}, #{10-6}",
    "00001": "lsr r{2-0}, r{5-3}, #{10-6}",
    "00010": "asr r{2-0}, r{5-3}, #{10-6}",
    "0001100": "add r{2-0}, r{5-3}, r{8-6}",
    "0001101": "sub r{2-0}, r{5-3}, r{8-6}",
    "0001110": "add r{2-0}, r{5-3}, #{8-6}",
    "0001111": "sub r{2-0}, r{5-3}, #{8-6}",
    "00100": "mov r{10-8}, #{7-0}",
    "00101": "cmp r{10-8}, #{7-0}",
    "00110": "add r{10-8}, #{7-0}",
    "00111": "sub r{10-8}, #{7-0}",
    "0100000000": "and r{2-0}, r{5-3}",
    "0100000001": "eor r{2-0}, r{5-3}",
    "0100000010": "lsl r{2-0}, r{5-3}",
    "0100000011": "lsr r{2-0}, r{5-3}",
    "0100000100": "asr r{2-0}, r{5-3}",
    "0100000101": "adc r{2-0}, r{5-3}",
    "0100000110": "sbc r{2-0}, r{5-3}",
    "0100000111": "ror r{2-0}, r{5-3}",
    "0100001000": "tst r{2-0}, r{5-3}",
    "0100001001": "neg r{2-0}, r{5-3}",
    "0100001010": "cmp r{2-0}, r{5-3}",
    "0100001011": "cmn r{2-0}, r{5-3}",
    "0100001100": "orr r{2-0}, r{5-3}",
    "0100001101": "mul r{2-0}, r{5-3}",
    "0100001110": "bic r{2-0}, r{5-3}",
    "0100001111": "mvn r{2-0}, r{5-3}",
    "01000100": "add r{7.2-0}, r{6-3}",
    "01000101": "cmp r{7.2-0}, r{6-3}",
    "01000110": "mov r{7.2-0}, r{6-3}",
    "01000111": "bx r{6-3}",
    "01001": "ldr r{10-8}, [pc, #{pc.7-0}*4+4]",
    "0101000": "str r{2-0}, [r{5-3}, r{8-6}]",
    "0101010": "strb r{2-0}, [r{5-3}, r{8-6}]",
    "0101100": "ldr r{2-0}, [r{5-3}, r{8-6}]",
    "0101110": "ldrb r{2-0}, [r{5-3}, r{8-6}]",
    "0101001": "strh r{2-0}, [r{5-3}, r{8-6}]",
    "0101011": "ldsb r{2-0}, [r{5-3}, r{8-6}]",
    "0101101": "ldrh r{2-0}, [r{5-3}, r{8-6}]",
    "0101111": "ldsh r{2-0}, [r{5-3}, r{8-6}]",
    "01100": "str r{2-0}, [r{5-3}, #{10-6}*4]",
    "01101": "ldr r{2-0}, [r{5-3}, #{10-6}*4]",
    "01110": "strb r{2-0}, [r{5-3}, #{10-6}]",
    "01111": "ldrb r{2-0}, [r{5-3}, #{10-6}]",
    "10000": "strh r{2-0}, [r{5-3}, #{10-6}*2]",
    "10001": "ldrh r{2-0}, [r{5-3}, #{10-6}*2]",
    "10010": "str r{10-8}, [sp, #{7-0}*4]",
    "10011": "ldr r{10-8}, [sp, #{7-0}*4]",
    "10100": "add r{10-8}, pc, #{7-0}*4",
    "10101": "add r{10-8}, sp, #{7-0}*4",
    "101100000": "add sp, #{6-0}*4",
    "101100001": "sub sp, #{6-0}*4",
    "1011010": "push {rlist.lr.8-0}",
    "1011110": "pop {rlist.pc.8-0}",
    "11000": "stmia r{10-8}!, {rlist.7-0}",
    "11001": "ldmia r{10-8}!, {rlist.7-0}",
    "11010000": "beq +{branch.7-0}*2+4",
    "11010001": "bne +{branch.7-0}*2+4",
    "11010010": "bcs +{branch.7-0}*2+4",
    "11010011": "bcc +{branch.7-0}*2+4",
    "11010100": "bmi +{branch.7-0}*2+4",
    "11010101": "bpl +{branch.7-0}*2+4",
    "11010110": "bvs +{branch.7-0}*2+4",
    "11010111": "bvc +{branch.7-0}*2+4",
    "11011000": "bhi +{branch.7-0}*2+4",
    "11011001": "bls +{branch.7-0}*2+4",
    "11011010": "bge +{branch.7-0}*2+4",
    "11011011": "blt +{branch.7-0}*2+4",
    "11011100": "bgt +{branch.7-0}*2+4",
    "11011101": "ble +{branch.7-0}*2+4",
    "11100": "b +{branch.10-0}*2+4",
    "11101": "blx +{branch.10-0}*2+4",
    "11110": "bl +{branch.blh.10-0}*4096+4",
    "11111": "blh {branch.10-0}*2",
    "11011111": "swi #{7-0}",
    "10111110": "bkpt #{7-0}",
}

# Extracts fields of op_map and user inputs
mbitfield = re.compile(r"(\+)?\{(.+?)\}(?:\*(\d+))?([+\-]\d+)?")
margfield = re.compile(r"\{(.*?)\}|r?(-?\d+)")

# Replaces arguments of input string with argument types
re_argstrip = {
    re.compile(r"\{.*?\}"): "{}",
    re.compile(r"\br[0-7]\b"): "r",
    re.compile(r"\+|-"): "",
    re.compile(r"#?(?:\$|0x)[\da-f]+"): "#",
    re.compile(r"#?\b\d+"): "#",
    re.compile(r"\b(?:r\d+|sp|lr|pc)\b(?!, #)"): "rhi",
}

# Normalizes user input
re_normalize = {
    re.compile(r"\s{2,}"): " ", 
    re.compile(r"\$([+/-]?)"): r"\g<1>0x",
    re.compile(r"#"): r"",
    re.compile(r"[+\-]?0x[\da-f]+"): lambda x: str(int(x.group(), 16)),
    re.compile(r"(add|sub) (r[0-7]), (r[0-7])$"): r"\1 \2, \2, \3",
    re.compile(r"(lsl|lsr|asr) (r[0-7]), (#?-?\d+)$"): r"\1 \2, \2, \3",
    re.compile(r"mov (r[0-7]), (r[0-7])$"): r"add \1, \2, #0",
}

def get_bin_tree(op_map, s=""):
    group1 = {k:v for k,v in op_map.items() if k.startswith(s+"0")}
    group2 = {k:v for k,v in op_map.items() if k.startswith(s+"1")}
    if not (group1 or group2): return (op_map.get(s), 1)
    return (get_bin_tree(group1, s+"0"), get_bin_tree(group2, s+"1"))
bin_tree = get_bin_tree(op_map)

def get_op(value):
    current = bin_tree
    for pos in range(16):
        current = current[(value >> 15-pos) & 1]
        if current[1] == 1: return current[0]

def multi_sub(regex_map, s):
    s = s.lower()
    for regex, repl in regex_map.items():
        s = regex.sub(repl, s)
    return s

def field_iter(fields):
    for range_ in fields:
        range_ = range_.replace(" ","")
        if not range_[0].isdigit():
            continue
        args = range_.split("-")
        if len(args) == 1:
            yield int(range_), int(range_)+1
        else:
            args = tuple(map(int, args))
            yield min(args), max(args)+1

def get_id_map():
    def fill(m):
        fields = m.group(2).split(".")
        if "rlist" in fields: return "{}"
        bitcount = sum(high-low for low,high in field_iter(fields))
        return str(1<<bitcount-1)
    id_map = {}
    for k,v in op_map.items():
        identifier = multi_sub(re_argstrip, mbitfield.sub(fill, v))
        id_map[identifier] = k
    return id_map
id_map = get_id_map()

def get_err_map():
    err_map = {}
    for opcode, template in op_map.items():
        bitmask = 0
        for m in mbitfield.finditer(template):
            for low, high in field_iter(m.group(2).split(".")):
                bitmask |= (1<<high)-(1<<low)
        bitmask = (1<<16-len(opcode))-1 & ~bitmask
        err_map[template] = (bitmask, True)
    for opcode in ("01000100", "01000101", "01000110"):
        err_map[op_map[opcode]] = (0xC0, False)
    return err_map
err_map = get_err_map()

def errcheck(value):  # return True if no error
    operation = get_op(value)
    if not operation: return False
    bitmask, default = err_map.get(operation)
    return bitmask & value == 0 if default else bitmask & value != 0

def to_signed(value, bitcount):
    return (value ^ (1<<bitcount-1)) - (1<<bitcount-1)
def from_signed(value, bitcount):
    return (value + (1<<bitcount-1)) ^ (1<<bitcount-1)

def to_rlist(value):
    out = []
    state = 0
    for i in range(16):
        if value & 2**i:
            sep = ","
            if state > 1: out.pop(); sep = "-"
            out.append(f"{sep}r{i}")
            state += 1
        else: state = 0
    return "{" + "".join(out)[1:] + "}"

def from_rlist(s):
    if not s: return 0
    s = s.replace("sp","r13").replace("lr","r14").replace("pc","r15")
    rfields = s.replace("r","").split(",")
    value = 0
    for low, high in field_iter(rfields):
        value |= (1<<high)-(1<<low)
    return value

def disasm(value, blh=None, addr=None):
    assert errcheck(value), "unrecognized opcode"
    def sub(m):
        sign, fields, mult, added = m.groups()
        sign, fields, mult, added = bool(sign), fields.split("."), int(mult or 1), int(added or 0)
        bits = 0
        msb = 0
        for low, high in field_iter(fields):
            bits = bits << high-low | (value>>low) & (1<<high-low)-1
            msb += high-low
        if sign: bits = to_signed(bits, msb)
        if fields[0] == "branch":
            if "blh" in fields[1:]: added += 2*((blh or 0) & 0x7FF)
            return f"${(addr or 0) + bits*mult + added:{'08X' if addr else '+X'}}"
        elif fields[0] == "rlist":
            if "lr" in fields[1:]: bits = bits & ~0x100 | (bits & 0x100) << 6
            elif "pc" in fields[1:]: bits = bits & ~0x100 | (bits & 0x100) << 7
            return to_rlist(bits)
        else:
            if fields[0] == "pc" and addr: added += addr & ~2
            return str(bits*mult + added)
    s = mbitfield.sub(sub, get_op(value))
    if addr: s = re.sub(r"\[pc, #(\d+)\]", lambda x: f"[${int(x.group(1)):08X}]", s)
    return s.replace("r13","sp").replace("r14","lr").replace("r15","pc")

def asm(s, addr=None):
    s = multi_sub(re_normalize, s)
    identifier = multi_sub(re_argstrip, s)
    if addr: identifier = identifier.replace("[#]", "[pc, #]")
    if "rhi" in identifier or identifier == "bx r":
        s = s.replace("sp","r13").replace("lr","r14").replace("pc","r15")
        identifier = re.sub(r"\br\b","rhi",identifier)
    opcode = id_map[identifier]
    template_fields = mbitfield.finditer(op_map[opcode])
    input_fields = margfield.finditer(s)
    bits = int(f"{opcode:0<16}",2)
    for i, (m, mf) in enumerate(zip(input_fields, template_fields)):
        sign, fields, mult, added = mf.groups()
        sign, fields, mult, added = bool(sign), fields.split("."), int(mult or 1), int(added or 0)
        if fields[0] == "rlist":
            value = from_rlist(m.group(1))
            valid = 0xFF | 0x4000*("lr" in fields) | 0x8000*("pc" in fields)
            assert not value & ~valid, f'{to_rlist(value & ~valid)} not in range of "{identifier}"'
            if "lr" in fields: value = value & ~0x4000 | (value & 0x4000) >> 6
            if "pc" in fields: value = value & ~0x8000 | (value & 0x8000) >> 7
        else:
            if addr and fields[0] == "branch": added += addr
            elif addr and fields[0] == "pc": added += addr & ~2
            value, remainder = divmod(int(m.group(2))-added, mult)
            if identifier == "bl #":
                value2, remainder = divmod(remainder, 2)
                bits |= (0xF800 | value2) << 16
            assert not remainder, f'argument {i+1} of "{identifier}" is not aligned'
        msb = 0
        for low, high in field_iter(reversed(fields)):
            bits |= (value>>msb & (1<<high-low)-1) << low
            msb += high-low
        check = from_signed(value, msb) if mf.group(1) else value
        assert not check >> msb, f'"{m.group(0)}" not in range for argument {i+1} of "{identifier}"'
    return bits

def disp(rom, addr, count):
    addr &= 0xFFFFFF
    addresses = [addr+2*c for c in range(count)]
    values = [int.from_bytes(rom[a:a+2], "little") for a in addresses]
    iterable = zip(addresses, values)
    for a,v in iterable:
        a |= 0x08000000
        s = disasm(v, addr=a)
        if s.startswith("bl "):
            try: a2,v2 = next(iterable); s = disasm(v, blh=v2, addr=a)
            except StopIteration: pass
        print(f"{a:08X}  {v:04X}  {s}")