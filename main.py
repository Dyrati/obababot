print("Importing modules...", end="\r")
import discord
import os
import sys
import time
import traceback
from obababot import utilities, commands, gsfuncs, battlesim, games
from obababot.utilities import \
    client, UserData, ReactMessages, RegisteredFuncs, reply, parse, load_data
print("Imported modules    ")


terminal_mode = "-t" in sys.argv
show_errors = "-e" in sys.argv
TOKEN = os.getenv('TOKEN') or input("Input bot token: ").strip('"')
if TOKEN == "t": terminal_mode = True

@client.event
async def on_ready():
    print("Connected    ")
    load_data()
    print("Bot is ready ")

@client.event
async def on_message(message):
    timestamp = time.time()
    if not utilities.is_command(message):
        if message.channel in RegisteredFuncs:
            await RegisteredFuncs[message.channel](message)
        return
    command, args, kwargs = utilities.extractcommand(message.content)
    ID = message.author.id
    if not UserData.get(ID): UserData[ID] = utilities.User(ID)
    UserData[ID].responses.append([])
    UserData[ID].temp["raw"] = kwargs.get("raw")
    try:
        await utilities.usercommands[command](message, *args, **kwargs)
    except Exception as e:
        args = f": {e.args[0]}" if e.args else ""
        if show_errors: await reply(message, traceback.format_exc())
        else: await reply(message, e.__class__.__name__ + args)
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
    message = reaction.message
    if message in ReactMessages:
        await ReactMessages[message](message, user, reaction.emoji)


if terminal_mode:
    from obababot.emulator import terminal
    terminal(on_ready=on_ready, on_message=on_message, on_react=on_reaction_add)
else:
    print("Connecting...", end="\r")
    client.run(TOKEN)