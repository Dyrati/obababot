import asyncio
import io
import re
from types import SimpleNamespace as SN
from utilities import client, parse, ReactMessages


def to_async(func):
    async def inner(*args, **kwargs):
        return func(*args, **kwargs)
    return inner

Users = {}
class TerminalUser:
    def __init__(self, name):
        self.name = name
        self.mention = "@" + name
        self.id = len(Users)
        Users[name] = self

class TerminalAttachment:
    def __init__(self, filename):
        with open(filename, "rb") as f:
            buffer = io.BytesIO(f.read())
            self.read = to_async(buffer.read)
            self.url = filename

class TerminalReaction:
    def __init__(self, target, emoji):
        self.message = target
        self.emoji = emoji

class TerminalMessage:
    def __init__(self, content="", user=None, attach=None):
        from types import SimpleNamespace as SN
        self.author = user
        self.content, self.attachments = self.get_attachments(content)
        self.attachments = [TerminalAttachment(attach.strip('"'))] if attach else []
        self.guild = SN(name=None)
        self.channel = SN(name=None, send=self.send)
        self.edit = self.send
        self.add_reaction = self.react
        self.remove_reaction = self.react
        self.clear_reactions = self.react
    
    async def send(self, content=""):
        print(content)
        return TerminalMessage(content)

    async def react(self, *args):
        pass
    
    async def delete(self):
        print(f"Deleted {self}")
    
    def get_attachments(self, text):
        import io
        attachments = []
        def msub(m):
            filename = m.group(1).strip('"')
            with open(filename, "rb") as f:
                buffer = io.BytesIO(f.read())
                buffer.read = to_async(buffer.read)
                buffer.url = filename
            attachments.append(buffer)
        text = re.sub(r"\sattach\s*=\s*(\".*?\"|\S+)", msub, text)
        return text, attachments


emojis = {
    "thumbsup": "\U0001f44d",
    "thumbsdown": "\U0001f44e",
    "cake": "\U0001f370",
    "poop": "\U0001f4a9",
    "up": "\U0001f53c",
    "down": "\U0001f53d",
    "left": "\u25c0\ufe0f",
    "right": "\u25b6\ufe0f",
    "?": "\u2753",
    "checkmark": "\u2705",
    "redX": "\u274c",
    "whiteflag": "\U0001f3f3\ufe0f",
}
for i in range(10):  # numbers
    emojis[str(i)] = f"{i}\ufe0f\u20e3"
for i in range(26):  # letters
    emojis[chr(0x61+i)] = f"\\U{0x1f1e6+i:08x}".encode().decode("unicode-escape")


def terminal(on_ready=None, on_message=None, on_react=None):
    import asyncio
    user = TerminalUser("admin")
    async def loop():
        client.loop = asyncio.get_running_loop()
        if on_ready: await on_ready()
        nonlocal user
        while True:
            try: text = input("> ")
            except KeyboardInterrupt: return
            args, kwargs = parse(text)
            if text in ("quit", "exit"): return
            elif text.startswith("setuser "):
                if args[1] in Users: user = Users[args[1]]
                else: user = TerminalUser(args[1])
            elif text.startswith("react ") and ReactMessages:
                target = next(reversed(ReactMessages))
                emoji = emojis[text[len("react "):]]
                await on_react(TerminalReaction(target, emoji), user)
            else:
                message = TerminalMessage(
                    content=text, user=user, attach=kwargs.get("attach"))
                if on_message: await on_message(message)
    asyncio.run(loop())