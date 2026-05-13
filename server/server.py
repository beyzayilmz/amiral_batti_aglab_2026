"""sunucu "beyin" görevi görür. istemcilerden gelen istekleri alır, işler ve yanıt verir.
    oyun mantığını yönetir: kim kazanır, kim kaybeder, hangi hamleler geçerli, vb."""

import socket
import threading
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import game_logic
import time

HOST = '0.0.0.0'
PORT = 5555

class BattleshipServer:
    def __init__(self):
        self.clients = {}           # player_id -> socket
        self.lock = threading.Lock()
        self.waiting_player = None  # Eşleşme bekleyen oyuncunun id'si
        self.rooms = {}             # room_id -> {"game_state": ..., "players": [id1, id2], "buffers": [b"", b""]}
        self.player_room = {}       # player_id -> room_id
        self.next_player_id = 0
        self.next_room_id = 0

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"Server {HOST}:{PORT} üzerinde dinleniyor.")

        while True:
            client_socket, address = server_socket.accept()
            print(f"Yeni bağlantı: {address}")
            client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)

            with self.lock:
                player_id = self.next_player_id
                self.next_player_id += 1
                self.clients[player_id] = client_socket

            thread = threading.Thread(target=self.handle_client, args=(client_socket, player_id))
            thread.daemon = True
            thread.start()

    def handle_client(self, client_socket, player_id):
        print(f"Oyuncu {player_id} bağlandı.")

        # Eşleştirme
        with self.lock:
            if self.waiting_player is None:
                # Bekleyen kimse yok, bu oyuncu bekleyecek
                self.waiting_player = player_id
                self.send(player_id, {"type": "waiting", "message": "Rakip bekleniyor..."})
            else:
                # Bekleyen oyuncu var, eşleştir
                partner_id = self.waiting_player
                self.waiting_player = None

                room_id = self.next_room_id
                self.next_room_id += 1

                self.rooms[room_id] = {
                    "game_state": game_logic.GameState(),
                    "players": [partner_id, player_id],
                    "buffers": [b"", b""]
                }
                self.player_room[partner_id] = room_id
                self.player_room[player_id] = room_id

                # Her iki oyuncuya da oda içindeki konumlarını bildir (0 veya 1)
                self.send(partner_id, {"type": "welcome", "player_id": 0})
                self.send(player_id,  {"type": "welcome", "player_id": 1})
                self.broadcast(room_id, {"type": "start_placement"})
                print(f"Oda {room_id} oluşturuldu: Oyuncu {partner_id} vs Oyuncu {player_id}")

        # Mesaj döngüsü
        while True:
            try:
                # Odaya atanana kadar bekle
                if player_id not in self.player_room:
                    time.sleep(0.1)
                    continue

                room_id = self.player_room[player_id]
                message = self.recv_line(player_id, room_id)
                if not message:
                    break
                self.process_msg(player_id, room_id, message)
            except:
                break

        print(f"Oyuncu {player_id} bağlantısı kesildi.")
        self.cleanup(player_id)

    def cleanup(self, player_id):
        with self.lock:
            # Odadan çıkar
            if player_id in self.player_room:
                room_id = self.player_room[player_id]
                room = self.rooms.get(room_id)
                if room:
                    # Tüm oyuncuların player_room kaydını sil (recv_line None dönmesin diye önce)
                    for pid in room["players"]:
                        self.player_room.pop(pid, None)
                    del self.rooms[room_id]
                    # Kalan oyuncuyu beklemeye al
                    for pid in room["players"]:
                        if pid != player_id and pid in self.clients:
                            try:
                                self.send(pid, {"type": "opponent_disconnected"})
                                self.waiting_player = pid
                                self.send(pid, {"type": "waiting", "message": "Rakip bekleniyor..."})
                            except:
                                pass
                else:
                    self.player_room.pop(player_id, None)

            # Bekleme listesinden çıkar
            if self.waiting_player == player_id:
                self.waiting_player = None

            # Client listesinden çıkar
            if player_id in self.clients:
                try:
                    self.clients[player_id].close()
                except:
                    pass
                del self.clients[player_id]

    def process_msg(self, player_id, room_id, message):
        room = self.rooms.get(room_id)
        if not room:
            return

        game_state = room["game_state"]
        # Odadaki konum: 0 veya 1
        local_id = room["players"].index(player_id)

        msg_type = message.get("type")

        if msg_type == "shoot":
            row = message.get("row")
            col = message.get("col")
            result = game_state.shoot(local_id, row, col)

            if result in ("not_your_turn", "not_battle_phase", "already_shot"):
                self.send(player_id, {"type": "shoot_error", "reason": result})
                return

            for i, pid in enumerate(room["players"]):
                self.send(pid, {
                    "type": "shoot_result",
                    "shooter": local_id,
                    "row": row,
                    "col": col,
                    "result": result,
                    "current_turn": game_state.current_turn,
                    "my_board": game_state.boards[i].get_visible_grid(False),
                    "opponent_board": game_state.boards[1 - i].get_visible_grid(True),
                    "winner": game_state.winner,
                })

        elif msg_type == "place_ship":
            row = message.get("row")
            col = message.get("col")
            length = message.get("length")
            horizontal = message.get("horizontal")
            success = game_state.place_ship(local_id, row, col, length, horizontal)
            self.send(player_id, {
                "type": "place_result",
                "success": success,
                "my_board": game_state.boards[local_id].get_visible_grid(False),
            })

        elif msg_type == "confirm_placement":
            ok = game_state.confirm_placement(local_id)
            if not ok:
                self.send(player_id, {"type": "confirm_result", "success": False,
                                      "message": "Tüm gemileri yerleştirmediniz!"})
                return
            self.send(player_id, {"type": "confirm_result", "success": True})
            if game_state.phase == "battle":
                for i, pid in enumerate(room["players"]):
                    self.send(pid, {
                        "type": "battle_start",
                        "current_turn": game_state.current_turn,
                        "my_board": game_state.boards[i].get_visible_grid(False),
                        "opponent_board": game_state.boards[1 - i].get_visible_grid(True),
                    })
            else:
                partner = room["players"][1 - local_id]
                self.send(partner, {"type": "opponent_ready"})

        elif msg_type == "play_again":
            if "play_again_votes" not in room:
                room["play_again_votes"] = [False, False]
            room["play_again_votes"][local_id] = True
            if all(room["play_again_votes"]):
                room["game_state"] = game_logic.GameState()
                room["play_again_votes"] = [False, False]
                self.broadcast(room_id, {"type": "start_placement"})
            else:
                partner = room["players"][1 - local_id]
                self.send(partner, {"type": "opponent_wants_rematch"})

    def send(self, player_id, data):
        try:
            msg = json.dumps(data, ensure_ascii=False) + "\n"
            self.clients[player_id].sendall(msg.encode("utf-8"))
        except Exception as e:
            print(f"Gönderme hatası (oyuncu {player_id}): {e}")

    def broadcast(self, room_id, data):
        room = self.rooms.get(room_id)
        if room:
            for pid in room["players"]:
                self.send(pid, data)

    def recv_line(self, player_id, room_id):
        room = self.rooms.get(room_id)
        if not room:
            return None
        local_id = room["players"].index(player_id)

        while b"\n" not in room["buffers"][local_id]:
            data = self.clients[player_id].recv(1024)
            if not data:
                return None
            room["buffers"][local_id] += data
        line, room["buffers"][local_id] = room["buffers"][local_id].split(b"\n", 1)
        return json.loads(line.decode("utf-8"))


if __name__ == "__main__":
    server = BattleshipServer()
    server.start()