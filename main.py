print("Importing modules...", end="\r")
import discord
import os
import sys
import time
import traceback
import utilities
from utilities import UserData, MessageData, reply, parse, load_data
import commands, gsfuncs
from games import *
print("Imported modules    ")


terminal_mode = "-t" in sys.argv
TOKEN = os.getenv('TOKEN') or input("Input bot token: ").strip('"')
if TOKEN == "-t": terminal_mode = True
client = discord.Client()
utilities.client = client

@client.event
async def on_ready():
    print("Connected    ")
    print("Bot is ready ")

@client.event
async def on_message(message):
    timestamp = time.time()
    if not utilities.is_command(message): return
    command, args, kwargs = utilities.extractcommand(message.content)
    ID = message.author.id
    UserData.setdefault(ID, utilities.User(ID))
    UserData[ID].responses.append([])
    UserData[ID].temp["raw"] = kwargs.get("raw")
    try: await utilities.usercommands[command](message, *args, **kwargs)
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

@client.event
async def on_reaction_add(reaction, user):
    # print(reaction.emoji.encode("ascii", "backslashreplace").decode())
    if user == client.user: return
    if reaction.message in MessageData:
        func = MessageData[reaction.message].get("func")
        if func: await func(reaction.message, user, reaction.emoji)


load_data()
if terminal_mode:
    utilities.terminal(on_ready=on_ready, on_message=on_message)
else:
    print("Connecting...", end="\r")
    client.run(TOKEN)