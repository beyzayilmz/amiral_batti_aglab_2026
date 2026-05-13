"""sunucu "beyin " görevi görür. istemcilerden gelen istekleri alır, işler ve yanıt verir.
    oyun mantığını yönetir: kim kazanır, kim kaybeder, hangi hamleler geçerli, vb."""

#TODO: send() broadcast(), gemi verileri geçerli mi?, rakibin tüm gemileri battı mı?, her oyuncu için ayrı thread, gelen mesajı işle, start()

import socket
import threading
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import game_logic
import time

HOST = '0.0.0.0' # Tüm ağ arayüzlerinde dinle
PORT = 5555 # İstemcilerin bağlanacağı port numarası
MAX_PLAYERS = 2

class BattleshipServer:
    def __init__(self):
        self.clients = [] # Bağlı istemcilerin listesi
        self.current_turn = 0 #0 veya 1, hangi oyuncunun sırası olduğunu
        self.game_started = False #iki oyuncu da hazır mı
        self.lock = threading.Lock() #iki thread aynı anda shared resource'a erişmesin diye lock
        self.players = {}
        self.game_state = game_logic.GameState()
        self.buffers = [b"", b""] # Her oyuncu için gelen veriyi depolamak için buffer
        self.play_again_votes = [False, False] # Her oyuncunun tekrar oynamak isteyip istemediği bilgisi

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(MAX_PLAYERS)
        print(f"Server {HOST}:{PORT} üzerinde dinleniyor.")

        while True: #client bağlanırsa kabul edecek
            client_socket, address = server_socket.accept()
            print(f"Yeni bağlantı: {address}")

            if len(self.clients) >= MAX_PLAYERS:
                client_socket.send("FULL\n".encode()) #clienta oyun dolu mesajı gönder
                client_socket.close()
                continue

            self.clients.append(client_socket)
            player_id = len(self.clients) - 1
            print(f"Oyuncu {player_id} bağlandı.")

            thread = threading.Thread(target = self.handle_client, args = (client_socket, player_id))
            thread.daemon = True
            thread.start()

    def handle_client(self, client_socket, player_id):
        self.send(player_id, {"type": "welcome", "player_id": player_id}) #clienta player id'si gönder
        print(f"Oyuncu {player_id} e id gönderildi")

        #iki oyuncu bağlanana kadar bekle
        while len(self.clients) < MAX_PLAYERS:
            #pass düzeltme: cpu yorar sleep ile beklicez
            time.sleep(1)
        with self.lock:
            if not self.game_started and len(self.clients) == MAX_PLAYERS:
                self.game_started = True
                self.broadcast({"type": "start_placement"}) #oyun başladı mesajı gönder

        while True:
            try:
                message = self.recv_line(player_id) #clienttan mesaj al
                if not message:
                    break
                self.process_msg(player_id, message) 
            except: 
                break

        print(f"Oyuncu {player_id} bağlantısı kesildi.")
        if client_socket in self.clients:
            self.clients.remove(client_socket)
        client_socket.close()                          

    def broadcast(self, message):
        for pid in range(len(self.clients)):
            self.send(pid, message)

    def send(self, player_id, data):
        msg = json.dumps(data, ensure_ascii=False) + "\n"
        self.clients[player_id].sendall(msg.encode("utf-8")) 

    def process_msg(self, player_id, message):
        #parts = message.strip().split(":")
        #command = parts[0]
        # message artık string değil, dict olacak
        msg_type = message.get("type")
        if msg_type == "shoot":
            row = message.get("row")
            col = message.get("col")
            result = self.game_state.shoot(player_id, row, col)
            if result in ("not_your_turn", "not_battle_phase", "already_shot"):
                self.send(player_id, {"type": "shoot_error", "reason": result})
                return

            for pid in range(2):
                self.send(pid, {
                    "type": "shoot_result",
                    "shooter": player_id,
                    "row": row,
                    "col": col,
                    "result": result,
                    "current_turn": self.game_state.current_turn,
                    "my_board": self.game_state.boards[pid].get_visible_grid(False),
                    "opponent_board": self.game_state.boards[1 - pid].get_visible_grid(True),
                    "winner": self.game_state.winner,
                })

        elif msg_type == "place_ship":
            row = message.get("row")
            col = message.get("col")
            length = message.get("length")
            horizontal = message.get("horizontal")
            success = self.game_state.place_ship(player_id, row, col, length, horizontal)
            self.send(player_id, {
                "type": "place_result",
                "success": success,
                "my_board": self.game_state.boards[player_id].get_visible_grid(False),
            })

        elif msg_type == "confirm_placement":
            ok = self.game_state.confirm_placement(player_id)
            if not ok:
                self.send(player_id, {"type": "confirm_result", "success": False,
                                    "message": "Tüm gemileri yerleştirmediniz!"})
                return
            self.send(player_id, {"type": "confirm_result", "success": True})
            if self.game_state.phase == "battle":
                for pid in range(2):
                    self.send(pid, {
                        "type": "battle_start",
                        "current_turn": self.game_state.current_turn,
                        "my_board": self.game_state.boards[pid].get_visible_grid(False),
                        "opponent_board": self.game_state.boards[1 - pid].get_visible_grid(True),
                    })
            else:
                self.send(1 - player_id, {"type": "opponent_ready"})

        elif msg_type == "play_again":
            self.play_again_votes[player_id] = True
            if all(self.play_again_votes):
                self.play_again_votes = [False, False]
                self.game_state = game_logic.GameState()
                self.broadcast({"type": "start_placement"})
            else:
                self.send(1 - player_id, {"type": "opponent_wants_rematch"})   
            


    def recv_line(self, player_id):
        while b"\n" not in self.buffers[player_id]:
            data = self.clients[player_id].recv(1024)
            if not data:
                return None
            self.buffers[player_id] += data
        line, self.buffers[player_id] = self.buffers[player_id].split(b"\n", 1)
        return json.loads(line.decode("utf-8")) 

if __name__ == "__main__":
    server = BattleshipServer()
    server.start()