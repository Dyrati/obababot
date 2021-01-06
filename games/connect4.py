import utilities
from utilities import command, reply


def diag_iter(array):
    up = lambda x,y: (x, y+1)
    down = lambda x,y: (x, y-1)
    left = lambda x,y: (x-1, y)
    right = lambda x,y: (x+1, y)
    upleft = lambda x,y: (x-1, y+1)
    upright = lambda x,y: (x+1, y+1)
    ismember = lambda x,y: 0 <= x < len(array) and 0 <= y < len(array[0])
    positions = ((0,0), (len(array)-1,1), (len(array)-1,0), (0,1))
    starts = (right, up, left, up)
    direction = (upleft, upleft, upright, upright)
    for pos, start, direction in zip(positions, starts, direction):
        while ismember(*pos):
            x, y = pos
            out = []
            while ismember(x,y):
                out.append((array[x][y], x, y))
                x,y = direction(x,y)
            yield out
            pos = start(*pos)

def v_iter(array):
    for x, col in enumerate(array):
        out = []
        for y, piece in enumerate(col):
            out.append((piece, x, y))
        yield out

def h_iter(array):
    array = zip(*array)
    for y, col in enumerate(array):
        out = []
        for x, piece in enumerate(col):
            out.append((piece, x, y))
        yield out


class ConnectFour():
    def __init__(self):
        self.current_player = 1
        self.board = [["   " for i in range(6)] for j in range(7)]
        self.pieces = [" X "," O "]
        self.count = 0
    
    def add_piece(self, col):
        if "   " not in self.board[col]: return
        height = self.board[col].index("   ")
        self.board[col][height] = self.pieces[self.current_player-1]
        self.count += 1
        if self.check_win(): return self.current_player
        if self.count == len(self.board)*len(self.board[0]): return 0
        self.current_player += 1
        if self.current_player > 2: self.current_player = 1

    def reset(self):
        for col in self.board:
            col[:] = ["   " for i in range(6)]

    def check_win(self):
        vertical = v_iter(self.board)
        horizontal = h_iter(self.board)
        diags = diag_iter(self.board)
        for generator in (vertical, horizontal, diags):
            for g in generator:
                pieces, xcoords, ycoords = zip(*g)
                s = "".join(pieces)
                for piece in self.pieces:
                    if piece*4 in s:
                        s = s.replace(piece*4, f"({piece[1:-1]})"*4)
                        new = [s[i:i+3] for i in range(0,len(s),3)]
                        for n,x,y in zip(new, xcoords, ycoords):
                            self.board[x][y] = n
                        return 1
    
    def __str__(self):
        rows = [f" |{'|'.join(row)}|" for row in zip(*self.board)]
        spacing = len(rows[0])-1
        border = " " + "="*spacing
        legs = " |/"+" "*(spacing-3)+"|/"
        feet = "//"+" "*(spacing-3)+"//"
        return "\n".join((border, "\n".join((reversed(rows))), border, legs, feet))


@command
async def connect4(message, *args, **kwargs):
    """Begins a game of connect 4"""

    game = ConnectFour()
    width = len(str(game).split("\n",1)[0])
    players = []

    def header():
        names = "{}  vs  {}".format(*(p.name for p in players))
        left, right = names.center(width+1).split(names)
        if game.current_player == 1: left = left[:-2] + "► "
        elif game.current_player == 2: right = " ◄" + right[2:]
        return left + names + right + "\n\n"

    async def mainphase(message, user, button):
        if user != players[game.current_player-1]: return
        wincheck = game.add_piece(button)
        player = players[game.current_player-1]
        if wincheck is not None:
            if wincheck == 0: content = "Tie Game".center(width+1) + f"\n\n{game}"
            else: content =  f"{player.name} wins!".center(width+1) + f"\n\n{game}"
            await message.edit(content=f"```\n{content}\n```")
            await utilities.end_interaction(message)
        else:
            content = header() + str(game)
            await message.edit(content=f"```\n{content}\n```")

    async def startphase(message, user, button):
        if button == True:
            players.append(user)
        elif button == False and user in players:
            players.remove(user)
        if len(players) < 2:
            content = "\n".join((player.name + " has joined!" for player in players))
            content += f"\nWaiting for Player {len(players)+1} to join\n\n{game}"
            await message.edit(content=f"```\n{content}\n```")
        else:
            await utilities.interactive_message(
                message = message,
                content = f"```\n{header()}{game}\n```",
                buttons = {f"{i}\ufe0f\u20e3": i for i in range(7)},
                func = mainphase)

    content = f"Waiting for Player {len(players)+1} to join\n\n{game}"
    await utilities.interactive_message(
        message = message,
        content = f"```\n{content}\n```",
        buttons = {"\u2705":True, "\u274c":False},
        func = startphase)

