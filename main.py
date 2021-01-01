print("Importing modules...", end="\r")
import discord
import os
import sys
import time
import traceback
import utilities
from utilities import UserData, reply, parse, load_data
import commands, gsfuncs
print("Imported modules    ")


terminal_mode = "-t" in sys.argv
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
    extrakwargs = {}
    for regex, command in utilities.aliases.items():
        m = regex.match(text)
        if not m: continue
        args, kwargs = parse(text[m.end():].replace("`",""))
        kwargs.update(**{k:v for k,v in m.groupdict().items() if v is not None})
        break
    else:
        command = text.split(" ",1)[0]
        if command not in utilities.usercommands: return
        args, kwargs = parse(text[len(command)+1:].replace("`",""))
    ID = message.author.id
    UserData[ID] = UserData.get(ID, utilities.User(ID))
    UserData[ID].responses.append([])
    if kwargs.get("raw"): UserData[ID].temp["raw"] = True
    try:
        await utilities.usercommands[command](message, *args, **kwargs)
    except Exception as e:
        # await reply(message, traceback.format_exc())
        args = f": {e.args[0]}" if e.args else ""
        await reply(message, e.__class__.__name__ + args)
    UserData[ID].temp.clear()
    if kwargs.get("t"):
        await reply(message, f"response time: `{time.time()-timestamp}`")
    if UserData[ID].responses and not UserData[ID].responses[-1]:
        UserData[ID].responses.pop()

@client.event
async def on_message_edit(before, after):
    await on_message(after)


load_data()
if terminal_mode:
    utilities.terminal(on_message)
else:
    print("Connecting...", end="\r")
    client.run(TOKEN)