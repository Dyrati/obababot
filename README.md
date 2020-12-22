# Obaba BOT
A discord utility bot for Golden Sun.

## Commands
```
$help:     Provides information about the bot and its functions
$info:     Returns info on something, like a search engine
$index:    Indexes a data table
$math:     Evaluate a mathematical expression like a calculator
$getclass: Get the class of a character based on their djinn
$filter:   Filters a data table based on a custom condition
$sort:     Sorts a data table based on an attribute (may also filter)
$damage:   Damage Calculator
```
## Syntax
**Arguments** are space-separated words
 - `$sort enemydata HP`
 - arguments with spaces must be enclosed with quotation marks
 
**Keyword** arguments have the form `key=value` and are optional
 - `$sort enemydata HP range=30 fields="HP, PP, ATK, DEF"`
 - no spaces, unless value is in quotes
 - You may use the universal keyword argument `t=true` or `t=1` to view the response time
 
Some functions accept **python expressions** as arguments, which uses python syntax
| Input | Output |
|---|---|
|$math `e**pi > pi**e` | `True`|
|$filter `enemydata HP>5000`|  a list of all the enemies with HP>5000 |
|$filter `djinndata HP>10 and element=="Venus"` | a list of all djinn that satisfy the expression |
 
For convenience, the `$math` command may use an `=` sign in place of `$math `

## Setting up the bot to run on your system
 - To update the database, run `gatherdata.py` with the GS2 ROM as an argument
 - In cmd, set the environment variable TOKEN equal to the bot token using the command:
   - `set TOKEN=tokengoeshere`
 - Download the respository, navigate to it from cmd, and run `main.py`
 
If things worked properly, you should see this:
```
Imported modules
Loaded Database
Bot is ready
```
