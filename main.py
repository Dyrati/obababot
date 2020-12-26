print("Importing modules...", end="\r")
import discord
import os
import sys
import time
import utilities
from utilities import reply, parse, load_data
import commands, gsfuncs
print("Imported modules    ")


terminal_mode = "-t" in sys.argv
if terminal_mode:
    sys.argv.pop(sys.argv.index("-t"))
else:
    TOKEN = os.getenv('TOKEN') or input("Input bot token: ").strip('"')
    if TOKEN == "terminal": terminal_mode = True


client = discord.Client()
utilities.client = client

@client.event
async def on_ready():
    print("Connected    ")
    print("Bot is ready ")

@client.event
async def on_message(message):
    timestamp = time.time()
    if message.author == client.user: return
    if message.guild.name == "Golden Sun Speedrunning" and message.channel.name != "botspam":
        return
    text = message.content
    for regex, command in utilities.aliases.items():
        m = regex.match(text)
        if not m: continue
        for k,v in m.groupdict().items():
            if v is None: continue
            text += f" {k}={v}"
        contents = text[m.end():]
        break
    else:
        command = text.split(" ",1)[0]
        if command in utilities.usercommands:
            contents = text[len(command)+1:]
        else: return
    args, kwargs = parse(contents.replace("`",""))
    try:
        await utilities.usercommands[command](message, *args, **kwargs)
    except Exception as e:
        args = f": {e.args[0]}" if e.args else ""
        await reply(message, e.__class__.__name__ + args)
    if kwargs.get("t"):
        await reply(message, f"response time: `{time.time()-timestamp}`")

load_data()
if terminal_mode:
    utilities.terminal(on_message)
else:
    print("Connecting...", end="\r")
    client.run(TOKEN)