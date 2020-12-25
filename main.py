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
    for name in utilities.usercommands:
        if text.startswith(name):
            command, contents = name, text[len(name):]
            break
    else:
        return
    args, kwargs = parse(contents.replace("`",""))
    try:
        await utilities.usercommands[command](message, *args, **kwargs)
    except Exception as e:
        args = f": {e.args[0]}" if e.args else ""
        await reply(message, e.__class__.__name__ + args)
    if kwargs.get("t"):
        await reply(message, f"response time: `{time.time()-timestamp}`")

load_data()
if terminal_mode or True:
    utilities.terminal(on_message)
else:
    print("Connecting...", end="\r")
    client.run(TOKEN)