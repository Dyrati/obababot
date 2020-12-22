# ObabaBOT
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
```
## Syntax
**Arguments** are space-separated words
 - `$sort enemydata HP`
 
**Keyword** arguments have the form `key=value` (no spaces, unless value is in quotes)
 - `$sort enemydata HP range=30 fields="HP, PP, ATK, DEF"`
 
Some functions accept **python expressions** as arguments, which uses python syntax
| Input | Output |
|---|---|
|$math `e**pi > pi**e` | `True`|
|$filter `enemydata HP>5000`|  a list of all the enemies with HP>5000 |
|$filter `djinndata HP>10 and element=="Venus"` | a list of all djinn that satisfy the expression |
 
For convenience, the `$math` command may use an `=` sign in place of `$math `

## Setting up the Bot to run locally
 - Download the respository, and run `main.py`
 - Input the bot token, (may instead be input as the first argument to main.py)
 - To update the database, run `gatherdata.py` with the GS2 ROM as an argument
 
If things worked properly, you should see this:
```
Imported modules
Loaded Database
Bot is ready
>
```
From there you can access any global variables from main.py, including a `load_data()` function that lets you reload info from the database without having to restart.
