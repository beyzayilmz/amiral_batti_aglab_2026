"""
Amiral Battı - Oyun Mantığı
Her iki taraf (sunucu ve istemci) bu dosyayı kullanır.
"""

BOARD_SIZE = 10

# Gemi boyutları: isim -> uzunluk
SHIPS = {
    "Uçak Gemisi": 5,
    "Zırhlı": 4,
    "Kruvazör": 3,
    "Destroyer": 3,
    "Denizaltı": 2,
}

# Tahta hücre değerleri
EMPTY = 0
SHIP = 1
MISS = 2
HIT = 3


class Board:
    def __init__(self):
        # 10x10 tahta, başlangıçta hepsi boş
        self.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.ships = []  # yerleştirilen gemilerin hücre listesi [(r,c), ...]
        self.hit_cells = set()
        self.miss_cells = set()
        self.sunk_ships = []  # batmış gemilerin hücre listeleri

    def can_place(self, row, col, length, horizontal):
        """Gemi yerleştirilebilir mi kontrol et."""
        cells = self._get_cells(row, col, length, horizontal)
        if cells is None:
            return False
        for r, c in cells:
            # Komşu hücreler de boş olmalı (dokunma kuralı)
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                        if self.grid[nr][nc] == SHIP:
                            return False
        return True

    def place_ship(self, row, col, length, horizontal):
        """Gemi yerleştir. Başarılıysa True döner."""
        if not self.can_place(row, col, length, horizontal):
            return False
        cells = self._get_cells(row, col, length, horizontal)
        for r, c in cells:
            self.grid[r][c] = SHIP
        self.ships.append(cells)
        return True

    def _get_cells(self, row, col, length, horizontal):
        """Gemi hücrelerini hesapla, sınır dışıysa None döner."""
        cells = []
        for i in range(length):
            r = row + (0 if horizontal else i)
            c = col + (i if horizontal else 0)
            if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE):
                return None
            cells.append((r, c))
        return cells

    def receive_shot(self, row, col):
        """
        Atışı işle.
        Dönüş: "already_shot" | "miss" | "hit" | "sunk" | "win"
        """
        if (row, col) in self.hit_cells or (row, col) in self.miss_cells:
            return "already_shot"

        if self.grid[row][col] == SHIP:
            self.grid[row][col] = HIT
            self.hit_cells.add((row, col))

            # Bu gemiyi bul
            for ship_cells in self.ships:
                if (row, col) in ship_cells:
                    # Gemi tamamen batmış mı?
                    if all(self.grid[r][c] == HIT for r, c in ship_cells):
                        self.sunk_ships.append(ship_cells)
                        # Tüm gemiler battı mı?
                        if len(self.sunk_ships) == len(self.ships):
                            return "win"
                        return "sunk"
                    return "hit"
        else:
            self.grid[row][col] = MISS
            self.miss_cells.add((row, col))
            return "miss"

    def all_ships_placed(self, expected_count=None):
        """Tüm gemiler yerleştirildi mi?"""
        count = expected_count if expected_count else len(SHIPS)
        return len(self.ships) == count

    def get_visible_grid(self, hide_ships=False):
        """
        Tahtanın görüntülenecek halini döndür.
        hide_ships=True ise rakip tahtası gibi gösterir (gemiler gizli).
        """
        result = []
        for r in range(BOARD_SIZE):
            row = []
            for c in range(BOARD_SIZE):
                val = self.grid[r][c]
                if hide_ships and val == SHIP:
                    row.append(EMPTY)
                else:
                    row.append(val)
            result.append(row)
        return result


class GameState:
    """İki oyuncunun tahtasını ve sırayı yönetir."""

    def __init__(self):
        self.boards = [Board(), Board()]  # [player0_board, player1_board]
        self.current_turn = 0  # 0 veya 1
        self.phase = "placement"  # "placement" | "battle" | "gameover"
        self.placement_done = [False, False]
        self.winner = None

    def place_ship(self, player, row, col, length, horizontal):
        return self.boards[player].place_ship(row, col, length, horizontal)

    def confirm_placement(self, player):
        """Oyuncu gemi yerleştirmeyi tamamladı."""
        if self.boards[player].all_ships_placed():
            self.placement_done[player] = True
            if all(self.placement_done):
                self.phase = "battle"
            return True
        return False

    def shoot(self, player, row, col):
        """
        player sırası geldiyse rakibe ateş et.
        Dönüş: sonuç string veya "not_your_turn"
        """
        if self.phase != "battle":
            return "not_battle_phase"
        if self.current_turn != player:
            return "not_your_turn"

        opponent = 1 - player
        result = self.boards[opponent].receive_shot(row, col)

        if result == "already_shot":
            return "already_shot"

        if result == "win":
            self.phase = "gameover"
            self.winner = player
        elif result in ("miss",):
            # Iskalayınca sıra geçer
            self.current_turn = opponent

        # İsabet veya batırma durumunda sıra aynı oyuncuda kalır
        return result

    def get_state_for_player(self, player):
        """Oyuncuya gönderilecek durum bilgisi."""
        opponent = 1 - player
        return {
            "phase": self.phase,
            "current_turn": self.current_turn,
            "my_board": self.boards[player].get_visible_grid(hide_ships=False),
            "opponent_board": self.boards[opponent].get_visible_grid(hide_ships=True),
            "winner": self.winner,
            "placement_done": self.placement_done[:],
        }
