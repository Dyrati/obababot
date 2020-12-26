# Obaba BOT
A discord utility bot for Golden Sun.

## Commands
```
$help:         Provides information about the bot and its functions
$info:         Returns info on something, like a search engine
$index:        Indexes a data table
$math:         Evaluate a mathematical expression like a calculator
$filter:       Filters a data table based on a custom condition
$sort:         Sorts a data table based on an attribute (may also filter)
$upload_save:  Temporarily store a battery file by uploading an attachment
$save_preview: See a preview of your last uploaded save file
$getclass:     Get the class of a character based on their djinn
$damage:       Damage Calculator
```
## Syntax
**Arguments** are space-separated words
 - `$sort enemydata HP`
 - arguments with spaces must be enclosed with quotation marks
 - in help-strings, if you see `*argument`, that means that all of the remaining space-separated words  
   become a part of this argument
 
**Keyword** arguments have the form `key=value` and are optional
 - `$sort enemydata HP range=30 fields="HP, PP, ATK, DEF"`
 - no spaces, unless `value` is in quotes
 - You may use the universal keyword argument `t=true` or `t=1` to view the response time

### Python Expressions
Some functions accept **python expressions** as arguments, which uses python syntax.  
Depending on the context, you may use the attributes of objects by name.  

| Input | Output |
|---|---|
|$math `e**pi > pi**e` | `True`|
|$filter `enemydata HP>5000`|  a list of all the enemies with HP>5000 |
|$filter `djinndata HP>10 and element=="Venus"` | a list of all djinn that satisfy the expression |
 
An easy way to view the attributes of objects in a data table is to use `$index [table] 0`,  
which prints out all of the attributes and values of the first item in `[table]`.

## Running the bot on your system
 - If you need to update the database, run `gatherdata.py` with the GS2 ROM as an argument
 - In cmd, set the environment variable TOKEN equal to the bot token using the command:
   - `set TOKEN=tokengoeshere`
 - Download the respository, navigate to it from cmd, and run `main.py`
 
If things worked properly, you should see this:
```
Imported modules
Loaded Database
Connected
Bot is ready
```
### Terminal Mode
Terminal mode is an easy way to test out the bot, without connecting to discord.
 - Use the command `main.py -t` to start the bot in terminal mode
 - Messages you type will behave like messages in discord, and bot replies will be in the terminal
 - Does not require a token or internet access
 - Press ctrl+C to exit
