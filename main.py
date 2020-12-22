print("Importing modules...", end="\r")
import discord
import sys
import re
import threading
import time
import traceback
from utilities import DataTables, UserData, reply, argparse, load_data
import commands
print("Imported modules    ")


if len(sys.argv) < 2:
    TOKEN = input("Input bot token: ").strip('"')
else:
    TOKEN = sys.argv[1]

# Terminal input
def command_input():
    import traceback
    while True:
        try:
            command = input("> ")
            temp = eval(command)
            if temp is not None: print(temp)
        except SyntaxError:
            try: exec(command)
            except Exception: print(traceback.format_exc())
        except EOFError:
            return
        except Exception as e:
            print(traceback.format_exc())
command_thread = threading.Thread(target=command_input, daemon=True)


client = discord.Client()

@client.event
async def on_ready():
    print('Bot is ready ')
    # command_thread.start()

@client.event
async def on_message(message):
    timestamp = time.time()
    if message.author == client.user: return
    if message.guild.name == "Golden Sun Speedrunning" and message.channel.name != "botspam":
        return
    text = message.content
    for name in commands.usercommands:
        if text.startswith(name):
            command, contents = name, text[len(name):]
            break
    else:
        return
    args, kwargs = argparse(contents.replace("`",""))
    try:
        await commands.usercommands[command](message, *args, **kwargs)
    except Exception as e:
        args = f": {e.args[0]}" if e.args else ""
        await reply(message, e.__class__.__name__ + args)
    if kwargs.get("t"):
        await reply(message, f"response time: `{time.time()-timestamp}`")


load_data()
print("Connecting...", end="\r")
client.run(TOKEN)