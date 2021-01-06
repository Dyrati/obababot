import utilities
from utilities import command, reply, MessageData

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
                out.append(array[x][y])
                x,y = direction(x,y)
            yield "".join(out)
            pos = start(*pos)

class ConnectFour():
    def __init__(self):
        self.current_player = 1
        self.board = [[" " for i in range(6)] for j in range(7)]
        self.pieces = ["X","O"]
    
    def add_piece(self, col):
        if " " not in self.board[col]: return
        height = self.board[col].index(" ")
        self.board[col][height] = self.pieces[self.current_player-1]
        if self.check_win():
            return self.current_player
        else:
            self.current_player += 1
            if self.current_player > 2: self.current_player = 1

    def reset(self):
        for col in self.board:
            col[:] = [" " for i in range(6)]

    def check_win(self):
        vertical = ("".join(col) for col in self.board)
        horizontal = ("".join(row) for row in zip(*self.board))
        diags = (s for s in diag_iter(self.board))
        for generator in (vertical, horizontal, diags):
            for s in generator:
                for piece in self.pieces:
                    if piece*4 in s: return True
        return False
    
    def __str__(self):
        return "\n".join(reversed([f"| {' | '.join(row)} |" for row in zip(*self.board)]))


@command
async def connect_four(message, *args, **kwargs):
    game = ConnectFour()
    response = f"Player {game.current_player}'s move\n\n{game}"
    async def inputhandle(message, user, button):
        wincheck = game.add_piece(button)
        if wincheck is not None:
            content = f"Player {game.current_player} wins!\n\n{game}"
            await message.edit(content=f"```{content}```")
            await utilities.end_interaction(message)
        else:
            content = f"Player {game.current_player}'s move\n\n{game}"
            await message.edit(content=f"```{content}```")
    await utilities.interactive_message(
        message = message,
        response = f"```{response}```",
        buttons = {f"{i}\ufe0f\u20e3": i for i in range(7)},
        func = inputhandle)
