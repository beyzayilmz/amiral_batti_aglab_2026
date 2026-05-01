BOARD_SIZE = 10

WATER = "water"
SHIP  = "ship"
HIT   = "hit"
MISS  = "miss"



SHIP_DEFS = [
    ("Uçak Gemisi", 5),
    ("Zırhlı",      4),
    ("Kruvazör",    3),
    ("Destroyer",   3),
    ("Denizaltı",   2),
]

class Board:
    def __init__(self):
        self.grid= [[WATER] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.ships = []
        
    
    def _get_cells(self, row, col, length, horizontal):
        cells = []
        for i in range(length):
            if horizontal:
                r = row
                c = col + i
            else:
                r = row + i
                c = col
            cells.append((r, c))
        return cells    


    def can_place(self, row, col, length, horizontal):
        cells= self._get_cells(row, col, length, horizontal)
          
            
        for r, c in cells:      # ← buraya ekle
            if r < 0 or r >= BOARD_SIZE or c < 0 or c >= BOARD_SIZE:
                return False
            
        for r, c in cells:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nr = r + dr
                    nc = c + dc
                    if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                        if self.grid[nr][nc] == SHIP:
                            return False    
        return True    
    
    
    def place_ship(self, name, row, col, length, horizontal):
        if not self.can_place(row,col, length, horizontal):
            return False
        
        cell= self._get_cells(row, col, length, horizontal)
        for r, c in cell:
            self.grid[r][c] = SHIP
        self.ships.append((name, cell))
        return True
    
    def receive_fire(self,row,col):
        state = self.grid[row][col]
        if state == SHIP:
            self.grid[row][col] = HIT
            return HIT
        elif state == WATER:
            self.grid[row][col] = MISS
            return MISS
        else:
            return state  # already hit or missed   
        
        
    def is_defeated(self):
        
        for name, cells in self.ships:
            for r, c in cells:
                if self.grid[r][c] != HIT:
                    return False
        return True
            
        
if __name__ == "__main__":
    board = Board()
    print(board.place_ship("Destroyer", 0, 0, 3, True))
    print(board.grid[0][0])
    print(board.grid[0][1])
    print(board.grid[0][2])

    print(board.place_ship("Kruvazör", 0, 3, 3, True))